#!/usr/bin/env python3
"""
Admin Server for RAG Chatbot Data Pipeline
FastAPI backend for managing preprocessing, chunking, and embedding
"""

import os
import sys
import json
import tomllib
import asyncio
import threading
import time
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
from collections import defaultdict

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import psycopg2
from pgvector.psycopg2 import register_vector
from contextlib import contextmanager

# ============================================================================
# CONFIGURATION
# ============================================================================

# Thread lock for safe pipeline_log access
log_lock = threading.Lock()

PROJECT_ROOT = Path(__file__).parent
SCRIPT_DIR = PROJECT_ROOT / "Script"
DATA_DIR = PROJECT_ROOT / "Data"
PREPROCESSED_DIR = PROJECT_ROOT / "Preprocessed_Data"
PIPELINE_LOG_FILE = PROJECT_ROOT / "pipeline_log.json"
SECRETS_FILE = PROJECT_ROOT / ".streamlit" / "secrets.toml"

# Import unified_pipeline module
sys.path.insert(0, str(SCRIPT_DIR))

# Try to import functions from unified_pipeline
unified_pipeline_func = None
try:
    from unified_pipeline import unified_pipeline
    unified_pipeline_func = unified_pipeline
    print("[✓] Successfully imported unified_pipeline from Script/unified_pipeline.py")
except (ImportError, AttributeError) as e:
    print(f"[!] Warning: Could not import unified_pipeline: {e}")

# Load database configuration
def load_db_config():
    """Load database config from .streamlit/secrets.toml"""
    if not SECRETS_FILE.exists():
        # Fallback to environment variables
        return {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "database": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD")
        }
    
    with open(SECRETS_FILE, "rb") as f:
        secrets = tomllib.load(f)
    
    return {
        "host": secrets.get("SUPABASE_DB_HOST", "localhost"),
        "port": int(secrets.get("SUPABASE_DB_PORT", "5432")),
        "database": secrets.get("SUPABASE_DB_NAME"),
        "user": secrets.get("SUPABASE_DB_USER"),
        "password": secrets.get("SUPABASE_DB_PASSWORD")
    }

DB_CONFIG = load_db_config()

def setup_database():
    """Setup or verify database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.close()
        print("[✓] Database connection verified")
    except Exception as e:
        print(f"[!] Warning: Database connection failed: {e}")

def process_single_file(file_path_str: str):
    """
    Process a single file through the unified pipeline
    Wrapper around unified_pipeline() from Script/unified_pipeline.py
    """
    if not unified_pipeline_func:
        raise RuntimeError("unified_pipeline not available - check Script/unified_pipeline.py")
    
    print(f"[PROCESS_FUNC] Calling unified_pipeline('{file_path_str}')")
    unified_pipeline_func(file_path_str)
    print(f"[PROCESS_FUNC] Completed unified_pipeline for '{file_path_str}'")

# FastAPI app
app = FastAPI(title="Admin Panel - RAG Chatbot Pipeline")

# Serve static HTML
@app.get("/")
async def serve_admin_panel():
    """Serve admin.html"""
    admin_html = PROJECT_ROOT / "admin.html"
    if admin_html.exists():
        return FileResponse(admin_html, media_type="text/html")
    return {"error": "admin.html not found"}

# ============================================================================
# DATABASE HELPERS
# ============================================================================

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = psycopg2.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        database=DB_CONFIG["database"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"]
    )
    register_vector(conn)
    try:
        yield conn
    finally:
        conn.close()

def get_embedding_counts(doc_ids: List[str] = None) -> Dict[str, int]:
    """Get embedding counts for multiple documents (batch query for efficiency)"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                if doc_ids is None or not doc_ids:
                    # Get all counts
                    cur.execute("SELECT parent_doc_id, COUNT(*) FROM chunks GROUP BY parent_doc_id")
                else:
                    # Get counts for specific doc_ids
                    placeholders = ','.join(['%s'] * len(doc_ids))
                    cur.execute(
                        f"SELECT parent_doc_id, COUNT(*) FROM chunks WHERE parent_doc_id IN ({placeholders}) GROUP BY parent_doc_id",
                        doc_ids
                    )
                
                result = {}
                for row in cur.fetchall():
                    result[row[0]] = row[1]
                
                # Fill in zeros for doc_ids not found
                if doc_ids:
                    for doc_id in doc_ids:
                        if doc_id not in result:
                            result[doc_id] = 0
                
                return result
    except Exception as e:
        print(f"Error querying embedding counts: {e}")
        return {}

def get_embedding_count(parent_doc_id: str) -> int:
    """Get number of chunks for a parent document (single query)"""
    counts = get_embedding_counts([parent_doc_id])
    return counts.get(parent_doc_id, 0)

# ============================================================================
# PIPELINE LOG MANAGEMENT
# ============================================================================

def load_pipeline_log() -> Dict:
    """Load pipeline_log.json (thread-safe)"""
    with log_lock:
        if PIPELINE_LOG_FILE.exists():
            with open(PIPELINE_LOG_FILE, "r") as f:
                return json.load(f)
        return {}

def save_pipeline_log(log_data: Dict):
    """Save pipeline_log.json (thread-safe)"""
    with log_lock:
        PIPELINE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PIPELINE_LOG_FILE, "w") as f:
            json.dump(log_data, f, indent=2)

def update_log_status(doc_id: str, status: str, error: Optional[str] = None, attempts: int = 1, embedding_count: Optional[int] = None):
    """Update status for a document in pipeline log (thread-safe)"""
    with log_lock:
        log_data = load_pipeline_log()
        
        if doc_id not in log_data:
            log_data[doc_id] = {}
        
        update_dict = {
            "status": status,
            "last_processed": datetime.now().isoformat(),
            "attempts": attempts,
            "error": error
        }
        
        # Update embedding_count if provided
        if embedding_count is not None:
            update_dict["embedding_count"] = embedding_count
        
        log_data[doc_id].update(update_dict)
        save_pipeline_log(log_data)

# ============================================================================
# FILE DISCOVERY & UTILITIES
# ============================================================================

def find_file_path(filename: str) -> Optional[Path]:
    """Find actual file path from filename (tries .pdf, .docx, and .txt)"""
    print(f"[DEBUG] find_file_path: searching for '{filename}'")
    
    # Try to find in Data directory recursively
    for file_path in DATA_DIR.rglob("*"):
        if file_path.is_file() and file_path.stem == filename and file_path.suffix.lower() in {".pdf", ".docx", ".txt"}:
            print(f"[DEBUG] find_file_path: found at {file_path}")
            return file_path
    
    # Try both .pdf, .docx, and .txt if not found by stem
    for ext in [".pdf", ".docx", ".txt"]:
        for cat_folder in DATA_DIR.iterdir():
            if cat_folder.is_dir() and not cat_folder.name.startswith("_"):
                candidate = cat_folder / f"{filename}{ext}"
                if candidate.exists():
                    print(f"[DEBUG] find_file_path: found at {candidate}")
                    return candidate
    
    print(f"[WARNING] find_file_path: file '{filename}' not found in Data directory")
    return None

def discover_files() -> Dict[str, List[Dict]]:
    """Discover all files and their statuses - shows ALL files from Data directory"""
    files_by_category = defaultdict(list)
    pipeline_log = load_pipeline_log()
    seen_files = set()  # Track which files we've already added
    
    # Build a map of parent_doc_id to part names from pipeline_log
    part_map = {}  # {parent_doc_id: [part_name1, part_name2, ...]}
    all_files_in_data = {}  # {doc_id: category} - all files found in Data folder
    
    for doc_id in pipeline_log.keys():
        # Check if this is a part file: pattern "parent_doc_id_XX"
        match = re.match(r'^(.+?)_(\d{2})$', doc_id)
        if match:
            parent = match.group(1)
            if parent not in part_map:
                part_map[parent] = []
            part_map[parent].append(doc_id)
    
    # First pass: Scan Data directory and collect ALL files
    for category_folder in DATA_DIR.iterdir():
        if not category_folder.is_dir() or category_folder.name.startswith("_"):
            continue
        
        category_name = category_folder.name
        
        # Collect all files in this category (including partitioned folders)
        for file_path in category_folder.glob("*"):
            if file_path.suffix.lower() in {".pdf", ".docx", ".txt"}:
                filename = file_path.stem
                all_files_in_data[filename] = category_name
        
        # Also detect partitioned folders: {parent_doc_id}_partitioned
        for partitioned_folder in category_folder.glob("*_partitioned"):
            if partitioned_folder.is_dir():
                parent_doc_id = partitioned_folder.name.replace("_partitioned", "")
                # If parent file doesn't exist, register it anyway
                if parent_doc_id not in all_files_in_data:
                    all_files_in_data[parent_doc_id] = category_name
    
    # Batch query all embedding counts at once
    all_doc_ids = list(all_files_in_data.keys())
    embedding_counts = get_embedding_counts(all_doc_ids) if all_doc_ids else {}
    
    # Second pass: Process parent files and their parts
    for category_name in sorted(set(all_files_in_data.values())):
        category_files = [f for f, c in all_files_in_data.items() if c == category_name]
        
        for doc_id in sorted(category_files):
            if doc_id in seen_files:
                continue
            
            # Check if this file is a part file
            match = re.match(r'^(.+?)_(\d{2})$', doc_id)
            is_part_file = match is not None
            
            if is_part_file:
                parent = match.group(1)
                # Skip if we'll show it as part of parent
                if parent in all_files_in_data:
                    continue
                # If parent doesn't exist, show this part file as standalone
            
            # Check if this file is partitioned (has parts in part_map)
            is_partitioned = doc_id in part_map and len(part_map[doc_id]) > 0
            
            # Get log entry
            log_entry = pipeline_log.get(doc_id, {})
            status = log_entry.get("status", "pending")
            last_processed = log_entry.get("last_processed", "")
            
            # Get embedding count from batch query
            embedding_count = embedding_counts.get(doc_id, 0)
            
            if is_partitioned:
                # Handle partitioned file - gather all parts
                parts_info = []
                for part_doc_id in sorted(part_map[doc_id]):
                    part_log = pipeline_log.get(part_doc_id, {})
                    part_status = part_log.get("status", "pending")
                    part_embedding_count = embedding_counts.get(part_doc_id, 0)
                    part_last_processed = part_log.get("last_processed", "")
                    
                    parts_info.append({
                        "filename": part_doc_id,
                        "preprocessing_status": part_status,
                        "embedding_count": part_embedding_count,
                        "last_processed": part_last_processed
                    })
                    seen_files.add(part_doc_id)  # Mark part as seen
                
                # Aggregate status from parts
                part_statuses = [p["preprocessing_status"] for p in parts_info]
                if all(s == "completed" for s in part_statuses):
                    agg_status = "completed"
                elif any(s == "failed" for s in part_statuses):
                    agg_status = "partial_failed" if any(s == "completed" for s in part_statuses) else "failed"
                elif any(s == "processing" for s in part_statuses):
                    agg_status = "processing"
                else:
                    agg_status = "pending"
                
                total_embedding_count = sum(p["embedding_count"] for p in parts_info)
                
                files_by_category[category_name].append({
                    "category": category_name,
                    "filename": doc_id,
                    "type": "partitioned",
                    "parts": parts_info,
                    "preprocessing_status": agg_status,
                    "embedding_count": total_embedding_count,
                    "last_processed": last_processed
                })
            else:
                # Handle original or standalone file
                files_by_category[category_name].append({
                    "category": category_name,
                    "filename": doc_id,
                    "type": "partitioned" if is_part_file else "original",
                    "parts": [],
                    "preprocessing_status": status,
                    "embedding_count": embedding_count,
                    "last_processed": last_processed
                })
            
            seen_files.add(doc_id)
    
    return dict(files_by_category)

# ============================================================================
# PROCESSING WITH RETRY LOGIC
# ============================================================================

class ProcessRequest(BaseModel):
    path: str

class CategoryRequest(BaseModel):
    category: str

def process_with_retry(doc_id: str, process_func, max_retries: int = 3):
    """Execute processing function with exponential backoff retry logic"""
    backoff_times = [30, 60, 120]
    print(f"[RETRY] Starting process_with_retry for {doc_id} (max_retries={max_retries})")
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[ATTEMPT {attempt}] Processing {doc_id}...")
            update_log_status(doc_id, "processing", attempts=attempt)
            process_func()
            # After successful processing, refresh embedding count from DB
            updated_count = get_embedding_count(doc_id)
            update_log_status(doc_id, "completed", attempts=attempt, embedding_count=updated_count)
            print(f"[OK] {doc_id} processed successfully on attempt {attempt} (chunks: {updated_count})")
            return True
        except Exception as e:
            error_msg = str(e)
            print(f"[ATTEMPT {attempt}] {doc_id} failed: {error_msg}")
            import traceback
            traceback.print_exc()
            
            # Check if error is retryable (503, 429)
            is_retryable = "503" in error_msg or "429" in error_msg
            
            if attempt < max_retries and is_retryable:
                backoff = backoff_times[attempt - 1]
                print(f"[RETRY] Waiting {backoff}s before retry {attempt + 1}/{max_retries}...")
                time.sleep(backoff)
            else:
                error_for_log = error_msg[:500]  # Truncate long errors
                try:
                    updated_count = get_embedding_count(doc_id)
                except:
                    updated_count = 0
                update_log_status(doc_id, "failed", error=error_for_log, attempts=attempt, embedding_count=updated_count)
                print(f"[FAILED] {doc_id} after {attempt} attempts: {error_msg}")
                return False
    
    return False

@app.post("/process/file")
async def process_file(request: ProcessRequest, background_tasks: BackgroundTasks):
    """Process a single file"""
    print(f"\n[API] POST /process/file - request.path={request.path}")
    
    # Try to find the actual file path
    filename = Path(request.path).stem  # Remove extension if present
    file_path = find_file_path(filename)
    
    if not file_path:
        error_msg = f"File '{filename}' not found in Data directory"
        print(f"[ERROR] {error_msg}")
        raise HTTPException(status_code=404, detail=error_msg)
    
    if not file_path.exists():
        error_msg = f"File path exists in discovery but not in filesystem: {file_path}"
        print(f"[ERROR] {error_msg}")
        raise HTTPException(status_code=404, detail=error_msg)
    
    doc_id = file_path.stem
    print(f"[API] Found file: {file_path} (doc_id={doc_id})")
    
    def bg_process():
        print(f"\n[PROCESS] Starting processing for {doc_id}...")
        try:
            process_with_retry(
                doc_id,
                lambda: process_single_file(str(file_path))
            )
        except Exception as e:
            error_msg = f"Processing failed: {str(e)}"
            print(f"[ERROR] {error_msg}")
            import traceback
            traceback.print_exc()
            update_log_status(doc_id, "failed", error=error_msg)
    
    background_tasks.add_task(bg_process)
    print(f"[API] Queued background task for {doc_id}")
    return {"status": "processing", "file": filename, "doc_id": doc_id}

@app.post("/process/category")
async def process_category(request: CategoryRequest, background_tasks: BackgroundTasks):
    """Process all files in a category"""
    category_path = DATA_DIR / request.category
    
    if not category_path.is_dir():
        raise HTTPException(status_code=404, detail="Category not found")
    
    def bg_process():
        """Process all files in category with retry per file"""
        files_to_process = []
        
        # Collect all files (including .txt)
        for file_path in category_path.glob("*.pdf"):
            if not (file_path.parent / f"{file_path.stem}_partitioned" / "partitioned").exists():
                files_to_process.append(file_path)
        for file_path in category_path.glob("*.docx"):
            if not (file_path.parent / f"{file_path.stem}_partitioned" / "partitioned").exists():
                files_to_process.append(file_path)
        for file_path in category_path.glob("*.txt"):
            files_to_process.append(file_path)
        
        # Process each file with retry
        print(f"[CATEGORY] Processing {len(files_to_process)} files in category {request.category}")
        for file_path in sorted(files_to_process):
            doc_id = file_path.stem
            print(f"\n[CATEGORY] Processing file: {doc_id}")
            process_with_retry(
                doc_id,
                lambda fp=str(file_path): process_single_file(fp)
            )
    
    background_tasks.add_task(bg_process)
    return {"status": "processing", "category": request.category}

@app.post("/process/all")
async def process_all_files(background_tasks: BackgroundTasks):
    """Process all files in Data directory"""
    
    def bg_process():
        """Process all files with retry per file"""
        files_to_process = []
        
        # Collect all files (including .txt)
        for category_folder in DATA_DIR.iterdir():
            if not category_folder.is_dir() or category_folder.name.startswith("_"):
                continue
            
            for file_path in category_folder.glob("*.pdf"):
                if not (file_path.parent / f"{file_path.stem}_partitioned" / "partitioned").exists():
                    files_to_process.append(file_path)
            for file_path in category_folder.glob("*.docx"):
                if not (file_path.parent / f"{file_path.stem}_partitioned" / "partitioned").exists():
                    files_to_process.append(file_path)
            for file_path in category_folder.glob("*.txt"):
                files_to_process.append(file_path)
        
        # Process each file with retry
        print(f"[ALL] Processing {len(files_to_process)} files across all categories")
        for file_path in sorted(files_to_process):
            doc_id = file_path.stem
            print(f"\n[ALL] Processing file: {doc_id}")
            process_with_retry(
                doc_id,
                lambda fp=str(file_path): process_single_file(fp)
            )
    
    background_tasks.add_task(bg_process)
    return {"status": "processing"}

@app.post("/retry/failed")
async def retry_failed(background_tasks: BackgroundTasks):
    """Retry all failed files"""
    pipeline_log = load_pipeline_log()
    failed_docs = [
        doc_id for doc_id, entry in pipeline_log.items()
        if entry.get("status") in {"failed", "partial_failed"}
    ]
    
    print(f"[RETRY] Found {len(failed_docs)} failed/partial_failed files to retry: {failed_docs}")
    
    def bg_process():
        for doc_id in failed_docs:
            print(f"\n[RETRY] Processing failed file: {doc_id}")
            # Use find_file_path to locate the actual file
            file_path = find_file_path(doc_id)
            
            if not file_path:
                print(f"[RETRY] [ERROR] Could not find file for doc_id: {doc_id}")
                error_msg = f"File not found during retry: {doc_id}"
                update_log_status(doc_id, "failed", error=error_msg)
                continue
            
            if not file_path.exists():
                print(f"[RETRY] [ERROR] File exists in search but not on disk: {file_path}")
                error_msg = f"File not on disk: {file_path}"
                update_log_status(doc_id, "failed", error=error_msg)
                continue
            
            print(f"[RETRY] Found file at: {file_path}")
            process_with_retry(
                doc_id,
                lambda fp=str(file_path): process_single_file(fp)
            )
    
    background_tasks.add_task(bg_process)
    print(f"[API] Queued retry task for {len(failed_docs)} files")
    return {"status": "retrying", "count": len(failed_docs)}

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/files")
async def get_files():
    """Get all files grouped by category with their statuses"""
    files_by_category = discover_files()
    
    # Convert to list format
    categories = []
    for category_name, files in sorted(files_by_category.items()):
        categories.append({
            "category": category_name,
            "files": files
        })
    
    return {"categories": categories}

@app.get("/logs")
async def get_logs():
    """Get pipeline log"""
    return load_pipeline_log()

@app.get("/stats")
async def get_stats():
    """Get summary statistics"""
    files_by_category = discover_files()
    
    total_files = 0
    completed = 0
    failed = 0
    pending = 0
    processing = 0
    
    for files in files_by_category.values():
        for file in files:
            total_files += 1
            status = file["preprocessing_status"]
            if status == "completed":
                completed += 1
            elif status in {"failed", "partial_failed"}:
                failed += 1
            elif status == "processing":
                processing += 1
            else:
                pending += 1
    
    return {
        "total_files": total_files,
        "completed": completed,
        "failed": failed,
        "pending": pending,
        "processing": processing
    }

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Setup database on startup
    try:
        setup_database()
    except Exception as e:
        print(f"Warning: Could not setup database: {e}")
    
    print(f"Starting Admin Server...")
    print(f"Database: {DB_CONFIG['database']}")
    print(f"Visit: http://localhost:8000")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
