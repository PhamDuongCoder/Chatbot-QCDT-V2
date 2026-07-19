"""
FastAPI service layer cho chatbot QCDT.

Expose các REST endpoint để bất kỳ client nào (Streamlit app.py, Postman,
frontend khác, ...) đều có thể gọi tới thay vì import trực tiếp module
chatbot.py trong cùng process. Đây là service đứng độc lập, chạy bằng:

    uvicorn api:app --host 0.0.0.0 --port 8000

Streamlit app (app.py) sẽ gọi sang các endpoint này qua HTTP.
"""

import os
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from chatbot import retrieve, generate_answer

# ── App setup ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Chatbot QCDT API",
    description="REST API cho chatbot quy chế đào tạo ĐHBK Hà Nội (RAG).",
    version="1.0.0",
)

# Cho phép Streamlit (hoặc frontend khác) gọi sang từ domain khác.
# Trong production nên giới hạn allow_origins về đúng domain của Streamlit app.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / response schemas ──────────────────────────────────────────────
class Message(BaseModel):
    role: str = Field(..., description="'user' hoặc 'assistant'")
    content: str


class QueryRequest(BaseModel):
    query: str
    conversation_history: List[Message] = Field(default_factory=list)
    top_k: int = 5


class QueryResponse(BaseModel):
    answer: str
    sources: List[str] = Field(default_factory=list)


class RetrieveRequest(BaseModel):
    query: str
    top_k: int = 5
    category: Optional[str] = None


class Chunk(BaseModel):
    chunk_id: Optional[str] = None
    parent_doc_id: Optional[str] = None
    category: Optional[str] = None
    chunk_title: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    similarity: Optional[float] = None


class RetrieveResponse(BaseModel):
    chunks: List[Chunk]


# ── Helper: tách JSON sources line ra khỏi câu trả lời (giống app.py cũ) ─────
def _extract_sources(raw_response: str):
    import json

    lines = raw_response.split("\n", 1)
    first_line = lines[0].strip() if lines else ""
    rest = lines[1] if len(lines) > 1 else ""

    try:
        obj = json.loads(first_line)
        if "sources" in obj and isinstance(obj["sources"], list):
            return rest.strip(), obj["sources"]
    except Exception:
        pass

    return raw_response, []


# ── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    """
    Nhận câu hỏi + lịch sử hội thoại, chạy toàn bộ pipeline RAG
    (query rewriting -> retrieval -> generation) và trả về câu trả lời
    đã tách sẵn phần nguồn tham khảo.
    """
    try:
        history = [{"role": m.role, "content": m.content} for m in req.conversation_history]
        raw = generate_answer(
            query=req.query,
            conversation_history=history,
            top_k=req.top_k,
        )
        answer, sources = _extract_sources(raw)
        return QueryResponse(answer=answer, sources=sources)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/retrieve", response_model=RetrieveResponse)
def retrieve_chunks(req: RetrieveRequest):
    """
    Chỉ chạy bước retrieval (không generate câu trả lời) — hữu ích để
    debug hoặc để client tự xử lý context theo cách riêng.
    """
    try:
        rows = retrieve(req.query, top_k=req.top_k, category=req.category)
        chunks = [
            Chunk(
                chunk_id=r.get("chunk_id"),
                parent_doc_id=r.get("parent_doc_id"),
                category=r.get("category"),
                chunk_title=r.get("chunk_title"),
                summary=r.get("summary"),
                content=r.get("content"),
                similarity=r.get("similarity") or r.get("SIMILARITY"),
            )
            for r in rows
        ]
        return RetrieveResponse(chunks=chunks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
