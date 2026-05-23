#!/usr/bin/env python3
"""
Database Migration Script: Add URL field to chunks table
This script loads citations from Citation.csv and updates the chunks table
with corresponding URLs based on parent_doc_id.
"""

import os
import csv
import tomllib
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from pgvector.psycopg2 import register_vector

# Load environment variables
load_dotenv()

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

with open(".streamlit/secrets.toml", "rb") as f:
    secrets = tomllib.load(f)

DB_CONFIG = {
    "host": secrets.get("SUPABASE_DB_HOST", "localhost"),
    "port": secrets.get("SUPABASE_DB_PORT", "5432"),
    "database": secrets.get("SUPABASE_DB_NAME"),
    "user": secrets.get("SUPABASE_DB_USER"),
    "password": secrets.get("SUPABASE_DB_PASSWORD")
}


def get_connection():
    """Get a database connection"""
    conn = psycopg2.connect(**DB_CONFIG)
    register_vector(conn)
    return conn


def load_citations():
    """Load Citation.csv as a dict {parent_doc_id: url}"""
    citation_path = Path(__file__).parent.parent / "Citation.csv"
    citation_dict = {}
    try:
        with open(citation_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                citation_dict[row["parent_doc_id"].strip()] = row["url"].strip()
        print(f"[✓] Loaded {len(citation_dict)} citations from Citation.csv")
    except Exception as e:
        print(f"[!] Error loading Citation.csv: {e}")
        return {}
    return citation_dict


def add_url_column():
    """Add url column to chunks table if it doesn't exist"""
    sql = "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS url TEXT DEFAULT '';"
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
        print("[✓] URL column ready (added or already exists)")
    except Exception as e:
        print(f"[!] Error adding url column: {e}")
        return False
    return True


def update_urls(citations: dict):
    """Update chunks table with URLs from Citation.csv"""
    if not citations:
        print("[!] No citations to process")
        return
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                total_updated = 0
                for parent_doc_id, url in citations.items():
                    sql = "UPDATE chunks SET url = %s WHERE parent_doc_id = %s;"
                    cur.execute(sql, (url, parent_doc_id))
                    rows_updated = cur.rowcount
                    if rows_updated > 0:
                        print(f"  [{parent_doc_id}] Updated {rows_updated} chunk(s)")
                        total_updated += rows_updated
                    else:
                        print(f"  [{parent_doc_id}] No chunks found (skipped)")
            conn.commit()
        
        print(f"\n[✓] Migration complete! Total chunks updated: {total_updated}")
    except Exception as e:
        print(f"[!] Error during migration: {e}")


def main():
    """Main entry point"""
    print("=" * 70)
    print("DATABASE MIGRATION: Add URLs to chunks table")
    print("=" * 70)
    
    # Step 1: Add url column if needed
    print("\n[STEP 1] Preparing database schema...")
    if not add_url_column():
        print("[!] Failed to prepare schema. Aborting.")
        return
    
    # Step 2: Load citations
    print("\n[STEP 2] Loading citations...")
    citations = load_citations()
    if not citations:
        print("[!] No citations loaded. Aborting.")
        return
    
    # Step 3: Update database
    print("\n[STEP 3] Updating chunks table...")
    update_urls(citations)
    
    print("\n" + "=" * 70)
    print("[✓] MIGRATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
