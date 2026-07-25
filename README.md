# 🎓 Chatbot Quy chế Đào tạo – ĐHBK Hà Nội

Dự án này xây dựng một chatbot RAG (Retrieval-Augmented Generation) để hỗ trợ sinh viên tra cứu quy chế đào tạo, học phí, ngoại ngữ, cảnh báo học tập và các nội dung liên quan đến đào tạo tại Đại học Bách khoa Hà Nội. Hệ thống dùng Gemini để tiền xử lý tài liệu, tạo embedding và trả lời dựa trên các chunk đã được lập chỉ mục trong PostgreSQL + pgvector.

**Live demo:** [chatbot.duongcoder.me](https://chatbot.duongcoder.me)
**REST API:** [api.duongcoder.me](https://api.duongcoder.me) — xem các endpoint GET /health, POST /query, POST /retrieve
**Admin panel:** [admin.duongcoder.me](https://admin.duongcoder.me) (yêu cầu đăng nhập)

Dự án được deploy trên VPS riêng bằng Docker, phục vụ qua HTTPS với domain thực tế.

---

## ✨ Tính năng chính

- Trả lời câu hỏi dựa trên tài liệu quy chế đã được lập chỉ mục, thay vì trả lời từ kiến thức tổng quát.
- Tự động trích xuất nguồn tham khảo và trả về các parent_doc_id liên quan.
- Hỗ trợ query rewriting dựa trên lịch sử hội thoại.
- Cung cấp REST API độc lập để các client khác có thể gọi lại logic RAG.
- Có admin panel riêng để quản lý pipeline tiền xử lý tài liệu và theo dõi tiến trình xử lý.

---

## 🏗️ Kiến trúc hệ thống

Luồng dữ liệu chính như sau:

1. Tài liệu gốc (PDF, DOCX, TXT) nằm trong thư mục Data.
2. Pipeline tiền xử lý trong Script/unified_pipeline.py sẽ:
   - đọc tài liệu,
   - chia thành các chunk logic,
   - gọi Gemini để chuẩn hóa và enrich metadata,
   - tạo embedding và lưu vào Supabase/PostgreSQL + pgvector.
3. Logic RAG trong Script/chatbot.py thực hiện:
   - rewrite query dựa trên lịch sử hội thoại,
   - retrieval các chunk phù hợp,
   - gọi Gemini để sinh câu trả lời.
4. FastAPI service trong Script/api.py expose các endpoint cho client gọi.
5. Giao diện người dùng là Streamlit trong Script/app.py, gọi sang API qua HTTP.
6. Admin panel trong Script/admin_server.py dùng để quản lý dữ liệu và chạy pipeline riêng.

### Vai trò từng thành phần

- Script/app.py: giao diện chat bằng Streamlit, là frontend chính cho người dùng.
- Script/chatbot.py: module logic cốt lõi của hệ thống RAG (retrieve + generate_answer).
- Script/api.py: backend FastAPI, đóng vai trò service trung gian giữa UI và logic RAG.
- Script/admin_server.py: backend admin panel, dùng cho quản lý pipeline tiền xử lý tài liệu.
- Script/unified_pipeline.py: pipeline chuẩn bị dữ liệu cho retrieval.

---

## 🛠️ Tech stack

| Layer | Công nghệ |
|---|---|
| LLM & Embedding | Google Gemini Flash, gemini-embedding-001 |
| Vector Database | PostgreSQL + pgvector trên Supabase |
| Backend / API | FastAPI, Uvicorn |
| Frontend | Streamlit |
| Reverse Proxy / HTTPS | Caddy 2 |
| Document Processing | PyMuPDF, python-docx, docx2pdf |
| Containerization | Docker, Docker Compose |
| Hosting | DigitalOcean Droplet (Ubuntu 24.04) |

---

## 📁 Cấu trúc project

```text
.
├── Data/                       # Tài liệu gốc PDF/DOCX/TXT phân theo category
├── Preprocessed_Data/          # Output sau khi tiền xử lý và chunking
├── Script/
│   ├── app.py                  # Streamlit UI — giao diện chat cho người dùng
│   ├── chatbot.py              # Logic RAG chính: retrieve + generate_answer
│   ├── api.py                  # FastAPI service: /query, /retrieve, /health
│   ├── admin_server.py         # FastAPI admin backend
│   ├── admin.html              # Giao diện admin panel
│   ├── unified_pipeline.py     # Pipeline preprocess → chunk → embed → store
│   └── pipeline_log.json       # Log trạng thái xử lý từng tài liệu
├── Citation.csv                # Mapping parent_doc_id -> URL tài liệu gốc
├── Dockerfile                  # Image dùng cho service api và chatbot
├── Dockerfile.admin            # Image dùng cho service admin
├── docker-compose.yml          # Điều phối 4 service: api, chatbot, admin, caddy
├── Caddyfile                   # Cấu hình reverse proxy + routing theo subdomain
├── .env                        # Secrets cho API/admin (không commit)
├── .streamlit/secrets.toml     # Secrets cho Streamlit frontend (không commit)
├── requirements.txt            # Dependencies cho chatbot + api
├── requirements-admin.txt      # Dependencies riêng cho admin panel
└── README.md
```

---

## 🚀 Chạy local bằng Docker Compose

Yêu cầu:
- Cài Docker Desktop
- Tạo file .env ở thư mục gốc
- Tạo file .streamlit/secrets.toml cho frontend

### 1. Cấu hình credentials

Tạo file .env:

```env
GOOGLE_API_KEY=your_google_api_key
SUPABASE_DB_HOST=your_supabase_host
SUPABASE_DB_PORT=5432
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=your_supabase_user
SUPABASE_DB_PASSWORD=your_supabase_password
```

Tạo file .streamlit/secrets.toml:

```toml
GOOGLE_API_KEY = "your_google_api_key"
SUPABASE_DB_HOST = "your_supabase_host"
SUPABASE_DB_PORT = "5432"
SUPABASE_DB_NAME = "postgres"
SUPABASE_DB_USER = "your_supabase_user"
SUPABASE_DB_PASSWORD = "your_supabase_password"
```

> Lưu ý: Supabase có thể dùng pooler host cụ thể cho từng project. Nếu dùng sai host, hệ thống sẽ báo lỗi liên quan đến kết nối dù username/password đúng.

### 2. Setup database

Trong Supabase SQL Editor, chạy:

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    chunk_id TEXT UNIQUE NOT NULL,
    parent_doc_id TEXT NOT NULL,
    source TEXT,
    category TEXT,
    year TEXT,
    chunk_index INTEGER,
    chunk_title TEXT,
    topic_tags TEXT,
    summary TEXT,
    content TEXT NOT NULL,
    embedding vector(3072),
    url TEXT DEFAULT ''
);
```

### 3. Chạy ứng dụng

```bash
docker compose up --build
```

Các service sẽ chạy tại:

| Service | Cổng local | Mô tả |
|---|---|---|
| chatbot | localhost:8501 | Giao diện Streamlit cho người dùng |
| api | localhost:8000 | FastAPI service cho /query, /retrieve, /health |
| admin | localhost:8001 | Admin panel quản lý pipeline |
| caddy | localhost:80 / 443 | Reverse proxy, chỉ dùng khi có domain thực tế |

Chạy nền:

```bash
docker compose up -d
```

Dừng toàn bộ:

```bash
docker compose down
```

### 4. Chạy thủ công không dùng Docker

Cài dependency:

```bash
pip install -r requirements.txt
pip install -r requirements-admin.txt
```

Chạy API:

```bash
uvicorn api:app --app-dir Script --host 0.0.0.0 --port 8000
```

Chạy Streamlit UI:

```bash
streamlit run Script/app.py
```

Chạy admin panel:

```bash
python Script/admin_server.py
```

---

## 📊 Pipeline xử lý dữ liệu

Pipeline gồm 3 bước chính:

1. Preprocessing và chunking: đọc tài liệu PDF/DOCX/TXT, chia thành các chunk logic phù hợp.
2. Embedding: mỗi chunk được chuyển thành vector bằng Gemini embedding model.
3. Storage: vector và metadata được lưu vào PostgreSQL + pgvector trên Supabase để retrieval.

Admin panel dùng để theo dõi trạng thái xử lý từng file và chạy lại pipeline nếu cần.

---

## ⚠️ Một số lưu ý

- File Script/pipeline_log.json phải tồn tại dưới dạng file trước khi chạy Docker lần đầu. Nếu thiếu, Docker có thể tạo thư mục thay thế và gây lỗi khi admin đọc file.
- Preprocessed_Data và pipeline_log.json được mount vào container, nên dữ liệu sẽ được giữ lại khi container bị rebuild hoặc xoá.
- Hệ thống hiện tại chưa có hybrid search (BM25 + dense), nên với một số query cụ thể có thể chưa tối ưu.
- Admin panel đang bảo vệ bằng Basic Auth ở layer reverse proxy, chưa có hệ thống phân quyền phức tạp.

---

## 🔮 Hướng phát triển

- Thêm hybrid search để tăng độ chính xác cho các query cụ thể.
- Cải thiện entity resolution cho các thuật ngữ như mã ngành, mã học phần.
- Tối ưu caching và latency cho API.
- Tách dependency admin khỏi image api/chatbot để giảm kích thước image.
- Migrate frontend sang React hoặc Next.js cho production trải nghiệm tốt hơn.