# sync_log.py — chạy một lần để sync trạng thái của tất cả files (gốc + partitioned)
import json
import psycopg2
import tomllib
import re
from pathlib import Path

with open(".streamlit/secrets.toml", "rb") as f:
    secrets = tomllib.load(f)

conn = psycopg2.connect(host=secrets["SUPABASE_DB_HOST"],
                        port=secrets["SUPABASE_DB_PORT"],
                        database=secrets["SUPABASE_DB_NAME"],
                        user=secrets["SUPABASE_DB_USER"],
                        password=secrets["SUPABASE_DB_PASSWORD"])
cur = conn.cursor()

# Lấy tất cả parent_doc_id và chunk_id để detect partitioned files
cur.execute("SELECT DISTINCT parent_doc_id, chunk_id FROM chunks ORDER BY parent_doc_id")
rows = cur.fetchall()

log = {}
part_names = set()

for parent_doc_id, chunk_id in rows:
    # Thêm parent_doc_id nếu chưa có
    if parent_doc_id not in log:
        log[parent_doc_id] = {
            "status": "completed",
            "last_processed": "unknown",
            "attempts": 1,
            "error": None
        }
    
    # Detect partitioned files: chunk_id format = "parent_doc_id_XX_YYY"
    # Ví dụ: "Ngoai_ngu_2022_Quy_doi_CCTA_01_001" -> part_name = "Ngoai_ngu_2022_Quy_doi_CCTA_01"
    match = re.match(r'^(.+?)_(\d{2})_(\d{3})$', chunk_id)
    if match:
        part_parent = match.group(1)
        part_num = match.group(2)
        
        # Kiểm tra xem có phải partitioned file không
        if part_parent == parent_doc_id:
            part_name = f"{parent_doc_id}_{part_num}"
            part_names.add(part_name)
            
            # Thêm part file vào log
            if part_name not in log:
                log[part_name] = {
                    "status": "completed",
                    "last_processed": "unknown",
                    "attempts": 1,
                    "error": None
                }

conn.close()

with open("pipeline_log.json", "w") as f:
    json.dump(log, f, indent=2)

print(f"Synced {len(log)} entries ({len(part_names)} partitioned files)")
print(f"Entry samples:")
for key in sorted(log.keys())[:5]:
    print(f"  - {key}")