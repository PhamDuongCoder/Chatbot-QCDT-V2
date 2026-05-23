#!/usr/bin/env python3
"""Test citation loading directly"""

import csv
from pathlib import Path

print("=" * 70)
print("CITATION LOADING TEST (No Database Required)")
print("=" * 70)

# Test 1: Load citations like unified_pipeline.py does
print("\n[TEST 1] Loading citations from unified_pipeline style...")
citation_path = Path(__file__).parent / "Citation.csv"
citation_dict = {}

try:
    with open(citation_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            citation_dict[row["parent_doc_id"].strip()] = row["url"].strip()
    print(f"[OK] Loaded {len(citation_dict)} citations")
except Exception as e:
    print(f"[ERROR] {e}")
    exit(1)

# Test 2: Test citation lookup
print("\n[TEST 2] Testing citation lookups...")
test_cases = [
    "Hoc_phi_2025_DHCQ_KSCS_VLVH_SDH",
    "QCDT_2025",
    "Ngoai_ngu_2024_K68",
    "NonExistent_Doc_ID"
]

for doc_id in test_cases:
    url = citation_dict.get(doc_id, "")
    status = "[FOUND]" if url else "[NOT FOUND]"
    print(f"  {status} {doc_id}")
    if url:
        print(f"         URL: {url[:60]}...")

# Test 3: Verify all citations have URLs
print("\n[TEST 3] Verifying all citations have URLs...")
empty_count = sum(1 for url in citation_dict.values() if not url)
print(f"  Total citations: {len(citation_dict)}")
print(f"  Citations with URLs: {len(citation_dict) - empty_count}")
print(f"  Citations without URLs: {empty_count}")

if empty_count == 0:
    print("\n[SUCCESS] All citation loading tests passed!")
else:
    print(f"\n[WARNING] {empty_count} citations are missing URLs")

print("=" * 70)
