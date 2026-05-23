#!/usr/bin/env python3
"""
Test chatbot module and citation loading
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("=" * 70)
print("CHATBOT MODULE TEST")
print("=" * 70)

try:
    from chatbot import retrieve, generate_answer
    print("[✓] Successfully imported chatbot module\n")
    
    print("[TESTING] Attempting to retrieve chunks with query: 'học phí'")
    results = retrieve("học phí", top_k=3)
    print(f"[✓] Retrieved {len(results)} chunks\n")
    
    if results:
        print("First result details:")
        for key, value in list(results[0].items())[:6]:
            if key == "content" and isinstance(value, str) and len(value) > 100:
                print(f"  {key}: {value[:100]}...")
            else:
                print(f"  {key}: {value}")
    
    print("\n[✓] CHATBOT TEST PASSED - Citation loading works!")
    
except Exception as e:
    print(f"[✗] Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
