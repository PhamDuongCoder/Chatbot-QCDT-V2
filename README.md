# 🎓 Chatbot Quy chế Đào tạo – ĐHBK Hà Nội

Chatbot RAG (Retrieval-Augmented Generation) hỗ trợ sinh viên tra cứu quy chế đào tạo của Trường Đại học Bách khoa Hà Nội. Hệ thống tự động tiền xử lý tài liệu, tạo vector embeddings và trả lời câu hỏi dựa trên nội dung tài liệu chính thức.

**Live demo:** [chatbot.duongcoder.me](https://chatbot.duongcoder.me)
**REST API:** [api.duongcoder.me](https://api.duongcoder.me) — xem `GET /health`, `POST /query`, `POST /retrieve`
**Admin panel:** [admin.duongcoder.me](https://admin.duongcoder.me) (yêu cầu đăng nhập)

Deploy trên VPS riêng (DigitalOcean Droplet), phục vụ qua HTTPS với domain thật, không dùng Streamlit Community Cloud.

---

## ✨ Tính năng

- **Trả lời chính xác** dựa hoàn toàn trên tài liệu quy chế — không hallucinate
- **Trích dẫn nguồn** kèm link tài liệu gốc từ ctt.hust.edu.vn
- **Query rewriting** tự động làm rõ câu hỏi dựa trên lịch sử hội thoại
- **REST API độc lập** — logic RAG được expose qua FastAPI, tách khỏi giao diện, có thể tái sử dụng cho client khác ngoài Streamlit
- **Pipeline tự động** từ PDF/DOCX → chunking → embedding → database
- **Admin panel** quản lý và theo dõi trạng thái xử lý tài liệu, bảo vệ bằng Basic Auth

---

## 🏗️ Kiến trúc

```
Tài liệu PDF/DOCX
        ↓
[LLM-assisted Chunking]     Gemini Flash — semantic chunking theo Điều/Khoản
        ↓
[Embedding Pipeline]        gemini-embedding-001 (RETRIEVAL_DOCUMENT)
        ↓
[PostgreSQL + pgvector]     Supabase — lưu trữ vector 3072 chiều
        ↓
[FastAPI service]           Query rewriting → Dense retrieval → Gemini generation
        ↓                   REST endpoints: /query, /retrieve, /health
        ↓
[Streamlit App]              Giao diện chat + citation, gọi sang FastAPI qua HTTP
```

Hệ thống gồm 4 service độc lập, mỗi service 1 container Docker riêng, điều phối bằng `docker-compose.yml`:

- **`api`** (FastAPI) — chứa toàn bộ logic RAG (`chatbot.py`), expose REST endpoints `POST /query`, `POST /retrieve`, `GET /health`. Đây là service duy nhất nói chuyện trực tiếp với Supabase và Gemini API.
- **`chatbot`** (Streamlit) — giao diện hỏi đáp chính. Không còn import trực tiếp logic RAG — gọi sang `api` qua HTTP nội bộ (`http://api:8000`).
- **`admin`** (FastAPI) — quản lý pipeline tiền xử lý tài liệu, chạy tách biệt hoàn toàn khỏi luồng chatbot, có UI riêng (`admin.html`).
- **`caddy`** — reverse proxy, route traffic theo subdomain (`chatbot.`, `api.`, `admin.duongcoder.me`) và tự động cấp/renew chứng chỉ HTTPS (Let's Encrypt). Đây là service duy nhất publish port ra internet (80/443) — 3 service còn lại chỉ giao tiếp qua Docker network nội bộ, không lộ port thẳng ra ngoài.

---

## 🛠️ Tech Stack

| Layer | Công nghệ |
|---|---|
| LLM & Embedding | Google Gemini Flash, gemini-embedding-001 |
| Vector Database | PostgreSQL 18 + pgvector (Supabase) |
| Backend / REST API | FastAPI, Uvicorn |
| Frontend | Streamlit |
| Reverse Proxy / HTTPS | Caddy 2 |
| Document Processing | PyMuPDF, docx2pdf |
| Containerization | Docker, Docker Compose |
| Hosting | DigitalOcean Droplet (Ubuntu 24.04) |

---

## 📁 Cấu trúc project

```
├── .streamlit/
│   └── secrets.toml          # Credentials cho Streamlit (không commit)
├── Data/                     # Tài liệu gốc PDF/DOCX, phân theo category
├── Preprocessed_Data/        # Output sau khi chunk
├── Script/
│   ├── unified_pipeline.py   # Pipeline end-to-end: preprocess → embed → store
│   ├── chatbot.py            # Retrieve + generate answer (dùng chung bởi api)
│   ├── api.py                # FastAPI service — REST endpoints /query /retrieve /health
│   ├── app.py                # Streamlit chatbot UI — gọi sang api.py qua HTTP
│   ├── admin_server.py       # FastAPI admin backend
│   ├── admin.html            # Admin panel UI
│   └── pipeline_log.json     # Trạng thái xử lý từng tài liệu (được track trong git)
├── Citation.csv               # Mapping tài liệu → URL gốc
├── Dockerfile                 # Image dùng chung cho service chatbot và api
├── Dockerfile.admin           # Image cho admin panel
├── docker-compose.yml         # Điều phối 4 service: api, chatbot, admin, caddy
├── Caddyfile                  # Cấu hình reverse proxy + routing theo subdomain
├── .env                       # Credentials cho api/admin (không commit)
├── .dockerignore
├── requirements.txt            # Dependencies chung cho chatbot + api
├── requirements-admin.txt      # Dependencies riêng cho admin panel
└── README.md
```

---

## 🚀 Setup & Chạy

### 1. Cấu hình credentials

Tạo file `.env` ở thư mục gốc (dùng cho service `api` và `admin`):

```env
GOOGLE_API_KEY=your_google_api_key
SUPABASE_DB_HOST=aws-1-ap-south-1.pooler.supabase.com
SUPABASE_DB_PORT=5432
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres.your_project_ref
SUPABASE_DB_PASSWORD=your_password
```

Tạo file `.streamlit/secrets.toml` với các key tương tự (dùng cho service `chatbot`):

```toml
GOOGLE_API_KEY = "your_google_api_key"
SUPABASE_DB_HOST = "aws-1-ap-south-1.pooler.supabase.com"
SUPABASE_DB_PORT = "5432"
SUPABASE_DB_NAME = "postgres"
SUPABASE_DB_USER = "postgres.your_project_ref"
SUPABASE_DB_PASSWORD = "your_password"
```

> Lưu ý host pooler Supabase: mỗi project được route qua 1 node cụ thể (`aws-0`, `aws-1`...) — dùng đúng host hiển thị trong Supabase Dashboard, sai node sẽ báo lỗi `tenant/user not found` dù user/password đúng.

> Cả `.env` và `.streamlit/secrets.toml` đã nằm trong `.gitignore` — không được commit lên Git. Người dùng khác clone repo cần tự tạo 2 file này với credentials của riêng họ.

### 2. Setup database

Chạy trong Supabase SQL Editor:

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunks (
    id              SERIAL PRIMARY KEY,
    chunk_id        TEXT UNIQUE NOT NULL,
    parent_doc_id   TEXT NOT NULL,
    source          TEXT,
    category        TEXT,
    year            TEXT,
    chunk_index     INTEGER,
    chunk_title     TEXT,
    topic_tags      TEXT,
    summary         TEXT,
    content         TEXT NOT NULL,
    embedding       vector(3072),
    url             TEXT
);
```

### 3. Chạy local bằng Docker Compose (khuyến nghị cho development)

Yêu cầu: đã cài [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
docker compose up --build
```

Lệnh này build và chạy 4 container:

| Service | Cổng local | Mô tả |
|---|---|---|
| `chatbot` | `localhost:8501` | Giao diện chatbot Streamlit |
| `api` | `localhost:8000` | REST API (`/query`, `/retrieve`, `/health`) |
| `admin` | `localhost:8001` | Admin panel quản lý pipeline |
| `caddy` | `localhost:80` / `:443` | Reverse proxy — chỉ có tác dụng khi chạy trên server có domain trỏ vào |

Chạy nền (không chiếm terminal):
```bash
docker compose up -d
```

Dừng toàn bộ:
```bash
docker compose down
```

Build lại sau khi sửa code (bắt buộc mỗi khi đổi `requirements.txt` hoặc Dockerfile):
```bash
docker compose up --build
```

Nếu chỉ sửa code Python mà build cache bị lỗi (ví dụ đổi volume mount), build không cache riêng 1 service:
```bash
docker compose build --no-cache <tên-service>
docker compose up -d <tên-service>
```

**Lưu ý về dữ liệu:** `Preprocessed_Data/` và `Script/pipeline_log.json` được mount dưới dạng volume — dữ liệu ghi ra trong lúc admin panel chạy sẽ lưu thẳng vào máy thật, không mất khi container bị xoá hoặc build lại. `pipeline_log.json` phải tồn tại sẵn dưới dạng **file** (không phải thư mục) trước khi `docker compose up` lần đầu — nếu thiếu, Docker sẽ tự tạo một thư mục rỗng thay thế và gây lỗi `IsADirectoryError` khi admin panel đọc file.

### 4. Deploy production (VPS + domain + HTTPS)

Production chạy trên DigitalOcean Droplet (Ubuntu 24.04), dùng Caddy làm reverse proxy tự động cấp HTTPS qua Let's Encrypt.

```bash
git clone -b vps-deploy https://github.com/PhamDuongCoder/Chatbot-QCDT-V2.git
cd Chatbot-QCDT-V2
# Tạo .env và .streamlit/secrets.toml như bước 1
# Tạo Caddyfile trỏ đúng domain của bạn (xem mẫu bên dưới)
docker compose up -d --build
```

Mẫu `Caddyfile`:

```
chatbot.yourdomain.com {
    reverse_proxy chatbot:8501
}

api.yourdomain.com {
    reverse_proxy api:8000
}

admin.yourdomain.com {
    basicauth {
        admin <bcrypt_hash_password>
    }
    reverse_proxy admin:8001
}
```

Tạo password hash cho Basic Auth:
```bash
docker compose exec caddy caddy hash-password --plaintext '<mật khẩu>'
```

DNS: thêm 3 A record (`chatbot`, `api`, `admin`) trỏ về IP của droplet.

Firewall: chỉ mở port 22 (SSH), 80, 443 qua UFW — port của từng service (8000/8001/8501) **không** publish ra host, chỉ giao tiếp nội bộ qua Docker network, Caddy là cửa ngõ duy nhất ra internet.

### 5. Chạy thủ công không qua Docker (thay thế)

Chatbot + API:
```bash
pip install -r requirements.txt
uvicorn api:app --app-dir Script --host 0.0.0.0 --port 8000 &
streamlit run Script/app.py
```

Admin panel (cần thêm dependency FastAPI/uvicorn, xem `requirements-admin.txt`):
```bash
pip install -r requirements-admin.txt
python Script/admin_server.py
# Mở http://localhost:8001
```

Từ admin panel, upload tài liệu vào thư mục `Data/{category}/` rồi bấm **Xử lý** để chạy pipeline tự động.

---

## 📊 Data Pipeline

Pipeline xử lý tài liệu gồm 3 bước tự động:

**Bước 1 — LLM-assisted Chunking:** Gửi PDF/DOCX lên Gemini, model tự phân tích và chia thành các chunk logic theo Điều/Khoản. File lớn (> 10 trang) được tự động split thành các part trước khi xử lý.

**Bước 2 — Embedding:** Mỗi chunk được embed bằng `gemini-embedding-001` với strategy `summary + content` để tối ưu semantic retrieval.

**Bước 3 — Storage:** Vector và metadata được lưu vào PostgreSQL + pgvector trên Supabase.

---

## ⚠️ Limitations

- Chưa có hybrid search (BM25 + dense) — query bằng mã học phần cụ thể (BF4792) có thể kém chính xác hơn
- Entity resolution chưa được implement — query "học phí IT1" không map được sang "Khoa học máy tính"
- Dữ liệu giới hạn trong phạm vi tài liệu đã được index
- Admin panel bảo vệ bằng Basic Auth đơn giản — chưa có phân quyền nhiều user hay audit log

---

## 🔮 Hướng phát triển

- Hybrid search với BM25 và Vietnamese tokenizer
- Entity mapping (mã ngành ↔ tên ngành)
- Tự động cập nhật khi có văn bản mới từ ctt.hust.edu.vn
- Tách `requirements-admin.txt` khỏi image `api`/`chatbot` để giảm kích thước image
- Migrate frontend sang React cho production deployment