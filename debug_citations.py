#!/usr/bin/env python3
"""
Debug script to test citation loading
"""

import csv
from pathlib import Path

citation_path = Path(__file__).parent / "Citation.csv"

print(f"Reading from: {citation_path}")
print(f"File exists: {citation_path.exists()}\n")

print("=" * 70)
print("TESTING CSV PARSING")
print("=" * 70)

citation_dict = {}
try:
    with open(citation_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        print(f"Header: {reader.fieldnames}\n")
        
        for i, row in enumerate(reader, 1):
            # Raw values
            parent_doc_id_raw = row["parent_doc_id"]
            url_raw = row["url"]
            
            # Stripped values
            parent_doc_id = parent_doc_id_raw.strip()
            url = url_raw.strip()
            
            citation_dict[parent_doc_id] = url
            
            if i <= 5:  # Print first 5 for inspection
                print(f"Row {i}:")
                print(f"  parent_doc_id (raw):    '{parent_doc_id_raw}'")
                print(f"  parent_doc_id (strip):  '{parent_doc_id}'")
                print(f"  url (raw):              '{url_raw[:50]}...'")
                print(f"  url (strip):            '{url[:50]}...'")
                print()

    print(f"\n✓ Total citations loaded: {len(citation_dict)}")
    print(f"\nAll parent_doc_ids:")
    for key in sorted(citation_dict.keys()):
        print(f"  - {key}")
        
except Exception as e:
    print(f"✗ Error loading citations: {e}")
    import traceback
    traceback.print_exc()
