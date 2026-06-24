# 🎓 Chatbot Quy chế Đào tạo – ĐHBK Hà Nội

Chatbot RAG (Retrieval-Augmented Generation) hỗ trợ sinh viên tra cứu quy chế đào tạo của Trường Đại học Bách khoa Hà Nội. Hệ thống tự động tiền xử lý tài liệu, tạo vector embeddings và trả lời câu hỏi dựa trên nội dung tài liệu chính thức.

**Live demo:** [chatbot-qcdt-v2.streamlit.app](https://chatbot-qcdt-v2-anozbuwhpnrszcjzbshwsi.streamlit.app/)

---

## ✨ Tính năng

- **Trả lời chính xác** dựa hoàn toàn trên tài liệu quy chế — không hallucinate
- **Trích dẫn nguồn** kèm link tài liệu gốc từ ctt.hust.edu.vn
- **Query rewriting** tự động làm rõ câu hỏi dựa trên lịch sử hội thoại
- **Pipeline tự động** từ PDF/DOCX → chunking → embedding → database
- **Admin panel** quản lý và theo dõi trạng thái xử lý tài liệu

---

## 🏗️ Kiến trúc

```
Tài liệu PDF/DOCX
        ↓
[Agentic Preprocessing]     Gemini Flash — semantic chunking theo Điều/Khoản
        ↓
[Embedding Pipeline]        gemini-embedding-001 (RETRIEVAL_DOCUMENT)
        ↓
[PostgreSQL + pgvector]     Supabase — lưu trữ vector 3072 chiều
        ↓
[RAG Chatbot]               Query rewriting → Dense retrieval → Gemini generation
        ↓
[Streamlit App]             Giao diện chat + citation
```

---

## 🛠️ Tech Stack

| Layer | Công nghệ |
|---|---|
| LLM & Embedding | Google Gemini Flash, gemini-embedding-001 |
| Vector Database | PostgreSQL 18 + pgvector (Supabase) |
| Backend | FastAPI (admin server) |
| Frontend | Streamlit |
| Document Processing | PyMuPDF, docx2pdf |

---

## 📁 Cấu trúc project

```
├── .streamlit/
│   └── secrets.toml          # Credentials (không commit)
├── Data/                     # Tài liệu gốc PDF/DOCX, phân theo category
├── Preprocessed_Data/        # Output sau khi chunk
├── Script/
│   ├── unified_pipeline.py   # Pipeline end-to-end: preprocess → embed → store
│   ├── chatbot.py            # Retrieve + generate answer
│   ├── app.py                # Streamlit chatbot UI
│   ├── admin_server.py       # FastAPI admin backend
│   └── admin.html            # Admin panel UI
├── Citation.csv              # Mapping tài liệu → URL gốc
├── requirements.txt
└── README.md
```

---

## 🚀 Setup & Chạy

### 1. Cài dependencies

```bash
pip install -r requirements.txt
```

### 2. Cấu hình credentials

Tạo file `.env` ở thư mục gốc:

```env
GOOGLE_API_KEY=your_google_api_key
SUPABASE_DB_HOST=aws-1-ap-south-1.pooler.supabase.com
SUPABASE_DB_PORT=5432
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres.your_project_ref
SUPABASE_DB_PASSWORD=your_password
```

Tạo file `.streamlit/secrets.toml` với các key tương tự cho Streamlit.

### 3. Setup database

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

### 4. Chạy Chatbot

```bash
streamlit run Script/app.py
```

### 5. Chạy Admin Panel

```bash
python Script/admin_server.py
# Mở http://localhost:8000
```

Từ admin panel, upload tài liệu vào thư mục `Data/{category}/` rồi bấm **Xử lý** để chạy pipeline tự động.

---

## 📊 Data Pipeline

Pipeline xử lý tài liệu gồm 3 bước tự động:

**Bước 1 — Agentic Chunking:** Gửi PDF/DOCX lên Gemini, model tự phân tích và chia thành các chunk logic theo Điều/Khoản. File lớn (> 10 trang) được tự động split thành các part trước khi xử lý.

**Bước 2 — Embedding:** Mỗi chunk được embed bằng `gemini-embedding-001` với strategy `summary + content` để tối ưu semantic retrieval.

**Bước 3 — Storage:** Vector và metadata được lưu vào PostgreSQL + pgvector trên Supabase.

---

## ⚠️ Limitations

- Chưa có hybrid search (BM25 + dense) — query bằng mã học phần cụ thể (BF4792) có thể kém chính xác hơn
- Entity resolution chưa được implement — query "học phí IT1" không map được sang "Khoa học máy tính"
- Dữ liệu giới hạn trong phạm vi tài liệu đã được index

---

## 🔮 Hướng phát triển

- Hybrid search với BM25 và Vietnamese tokenizer
- Entity mapping (mã ngành ↔ tên ngành)
- Tự động cập nhật khi có văn bản mới từ ctt.hust.edu.vn
- Migrate sang FastAPI + React cho production deployment