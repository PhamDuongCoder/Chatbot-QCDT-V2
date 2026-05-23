import socket
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_only

import os
import time
from google import genai
from google.genai import types
import psycopg2
from pgvector.psycopg2 import register_vector

# Configuration loaded from environment variables (app.py will populate these from st.secrets)
DB_CONFIG = {
    "host": os.getenv("SUPABASE_DB_HOST", "localhost"),
    "port": os.getenv("SUPABASE_DB_PORT", "5432"),
    "database": os.getenv("SUPABASE_DB_NAME"),
    "user": os.getenv("SUPABASE_DB_USER"),
    "password": os.getenv("SUPABASE_DB_PASSWORD")
}

API_KEY = os.getenv("GOOGLE_API_KEY")

# Initialize client - will use API_KEY from environment
if API_KEY:
    client = genai.Client(api_key=API_KEY)
else:
    client = None

EMBEDDING_MODEL = "gemini-embedding-001"
GENERATION_MODEL = "gemini-3.1-flash-lite"

# System prompts and instructions
SYSTEM_INSTRUCTION = """
Bạn là chuyên gia về quy chế đào tạo của trường đại học bách khoa hà nội.
Vai trò của bạn là trả lời các câu hỏi của sinh viên.
Với mỗi câu hỏi của sinh viên, bạn sẽ được cung cấp các chunk thông tin liên quan đến câu hỏi đó dưới dạng các bộ {title, summary, content, parent_doc_id}.
Bạn phải dựa trên các chunk thông tin đó để trả lời câu hỏi của sinh viên.

⚠️ QUAN TRỌNG - ĐỊNH DẠNG CẬP NHẬT:
Bạn PHẢI xuất dòng JSON đầu tiên của mọi phản hồi, theo định dạng chính xác:
{"sources": ["parent_doc_id_1", "parent_doc_id_2", ...]}

Dòng JSON này phải chứa CHỈ các parent_doc_ids của các chunks bạn thực sự sử dụng để trả lời câu hỏi.
Không bao gồm những chunks không được sử dụng.

Sau dòng JSON, tiếp theo là phần trả lời bình thường.

VÍ DỤ FORMAT:
{"sources": ["Hoc_phi_2025_DHCQ_KSCS_VLVH_SDH", "QCDT_2025"]}

Quy tắc trả lời:
- Nếu chunk trả lời trực tiếp được câu hỏi, hãy trả lời câu hỏi dựa trên thông tin trong chunk
- Nếu chunk có liên quan nhưng không trả lời trực tiếp, hãy nói với người dùng rằng dựa trên thông tin được cung cấp, bạn không có đủ thông tin để trả lời; sau đó cung cấp thông tin liên quan
- Nếu chunk không liên quan, hãy trả lời rằng bạn không có đủ thông tin
- Tuyệt đối không được bịa câu trả lời, không trả lời dựa trên nguồn khác ngoài chunks được cung cấp
- Trả lời bằng tiếng Việt, thân thiện và dễ hiểu
- Khi trả lời, ghi rõ nguồn bằng cách trích dẫn tên chunk_title tương ứng
"""

QUERY_REWRITING_INSTRUCTION = """
Hãy viết lại query dựa trên conversation_history để phục vụ cho quá trình 
retrieval của chatbot RAG.
Yêu cầu: retrieval_query cần chứa tất cả các từ khóa quan trọng
Output: chỉ trả về DUY NHẤT query, không chào hỏi, không có lời kết. 
"""

MAX_HISTORY = 10


def get_connection():
    conn = psycopg2.connect(
        f"postgresql://{os.getenv('SUPABASE_DB_USER')}:{os.getenv('SUPABASE_DB_PASSWORD')}@{os.getenv('SUPABASE_DB_HOST')}/{os.getenv('SUPABASE_DB_NAME')}?sslmode=require&gssencmode=disable"
    )
    register_vector(conn)
    return conn


def retrieve(query: str, top_k: int = 5, category: str = None) -> list[dict]:
    """
    Retrieve relevant chunks from the database using semantic search.
    
    Args:
        query: The search query string
        top_k: Number of top results to return
        category: Optional category filter
        
    Returns:
        List of dictionaries containing chunk information
    """
    # Embed query
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
    )
    query_vector = response.embeddings[0].values

    # Query database
    with get_connection() as conn:
        with conn.cursor() as cur:
            if category:
                sql = """
                    SELECT chunk_id, parent_doc_id, category, 
                           chunk_title, summary, content,
                           1 - (embedding <=> %s::vector) AS SIMILARITY
                    FROM chunks
                    WHERE category = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """
                cur.execute(sql, (query_vector, category, query_vector, top_k))
            else:
                sql = """
                    SELECT chunk_id, parent_doc_id, category,
                            chunk_title, summary, content,
                            1 - (embedding <=> %s::vector) AS SIMILARITY
                    FROM chunks
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """
                cur.execute(sql, (query_vector, query_vector, top_k))

            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]

    return [dict(zip(columns, row)) for row in rows]


def generate_answer(query: str, 
                    conversation_history: list, 
                    top_k: int = 5) -> str:
    """
    Generate an answer based on the query and conversation history.
    
    Args:
        query: The user's question
        conversation_history: List of previous messages in format [{"role": "user"/"assistant", "content": "..."}]
        top_k: Number of relevant chunks to retrieve
        
    Returns:
        The generated answer as a string
    """
    # Query rewriting based on conversation history
    history_str = "\n".join([f"{m['role']}: {m['content']}" for m in conversation_history])
    retrieval_query = client.models.generate_content(
        model=GENERATION_MODEL,
        contents=f"Lịch sử hội thoại:\n{history_str}\n\nCâu hỏi hiện tại: {query}",
        config=types.GenerateContentConfig(
            system_instruction=QUERY_REWRITING_INSTRUCTION,
            temperature=0.1
        )
    ).text.strip()

    # Retrieve relevant chunks
    chunks = retrieve(retrieval_query, top_k)

    # Build context from chunks
    context = "Các chunk liên quan đến query:\n"
    for i, chunk in enumerate(chunks, start=1):
        context += f"Chunk {i}:\n"
        for column, value in chunk.items():
            context += f"{column}: {value}\n"
        context += "\n"

    # Generate answer
    response = client.models.generate_content(
        model=GENERATION_MODEL,
        contents=f"Query:\n {query}\n Conversation_history:\n {history_str}\n {context}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.1
        )
    ).text.strip()

    return response
