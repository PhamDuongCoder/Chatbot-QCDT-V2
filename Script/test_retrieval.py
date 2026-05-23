#!/usr/bin/env python3
"""Test chatbot retrieval with citation data"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Set working directory to Script folder
sys.path.insert(0, str(Path(__file__).parent))
os.chdir(Path(__file__).parent)

load_dotenv()

print("=" * 70)
print("CHATBOT RETRIEVAL TEST")
print("=" * 70)

try:
    from chatbot import retrieve
    print("\n[OK] Imported chatbot module")
    
    print("\n[TEST] Retrieving chunks for: 'học phí'\n")
    results = retrieve("học phí", top_k=3)
    
    print(f"[OK] Retrieved {len(results)} chunks\n")
    
    for i, result in enumerate(results, 1):
        print(f"Result {i}:")
        print(f"  parent_doc_id: {result.get('parent_doc_id')}")
        print(f"  chunk_id: {result.get('chunk_id')}")
        print(f"  chunk_title: {result.get('chunk_title')}")
        print(f"  similarity: {result.get('similarity'):.4f}")
        print()
    
    print("=" * 70)
    print("[SUCCESS] Chatbot retrieval and citations working!")
    print("=" * 70)
    
except Exception as e:
    print(f"\n[ERROR] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
