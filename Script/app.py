import streamlit as st
import os
import csv
import json
from pathlib import Path

st.set_page_config(
    page_title="Chatbot QCDT - ĐHBK Hà Nội",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@300;400;500;600;700&family=Playfair+Display:wght@700&display=swap');

/* ── Root variables ── */
:root {
    --navy:      #0f172a;
    --navy-mid:  #1e293b;
    --navy-soft: #334155;
    --gold:      #f59e0b;
    --gold-soft: #fbbf24;
    --cream:     #fefce8;
    --text:      #e2e8f0;
    --text-muted:#94a3b8;
    --user-bg:   #1d4ed8;
    --bot-bg:    #1e293b;
    --border:    rgba(245,158,11,0.2);
}

/* ── Global ── */
html, body, [class*="css"] {
    font-family: 'Be Vietnam Pro', sans-serif !important;
}

.stApp {
    background: linear-gradient(135deg, #0f172a 0%, #1a2744 50%, #0f172a 100%);
    min-height: 100vh;
}

/* Noise texture overlay */
.stApp::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E");
    pointer-events: none;
    z-index: 0;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #162032 100%) !important;
    border-right: 1px solid var(--border) !important;
}

[data-testid="stSidebar"] * {
    color: var(--text) !important;
}

/* ── Main content area ── */
.main .block-container {
    padding-top: 2rem;
    max-width: 900px;
    margin: 0 auto;
}

/* ── Header ── */
.chat-header {
    text-align: center;
    padding: 2.5rem 1rem 1.5rem;
    margin-bottom: 1.5rem;
    position: relative;
}

.chat-header::after {
    content: '';
    display: block;
    width: 80px;
    height: 3px;
    background: linear-gradient(90deg, var(--gold), transparent);
    margin: 1rem auto 0;
    border-radius: 2px;
}

.chat-header h1 {
    font-family: 'Playfair Display', serif !important;
    font-size: 2.2rem !important;
    font-weight: 700 !important;
    color: #f8fafc !important;
    letter-spacing: -0.5px;
    margin-bottom: 0.5rem;
    line-height: 1.2;
}

.chat-header h1 span {
    color: var(--gold);
}

.chat-header p {
    color: var(--text-muted) !important;
    font-size: 0.95rem;
    font-weight: 300;
    margin: 0;
}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background: transparent !important;
    border: none !important;
    padding: 0.4rem 0 !important;
}

/* User bubble */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) .stMarkdown {
    background: linear-gradient(135deg, #1d4ed8, #1e40af) !important;
    color: #f0f9ff !important;
    border-radius: 18px 18px 4px 18px !important;
    padding: 0.85rem 1.2rem !important;
    max-width: 80% !important;
    margin-left: auto !important;
    box-shadow: 0 4px 15px rgba(29,78,216,0.3);
    border: 1px solid rgba(96,165,250,0.2);
}

/* Assistant bubble */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) .stMarkdown {
    background: var(--bot-bg) !important;
    color: var(--text) !important;
    border-radius: 18px 18px 18px 4px !important;
    padding: 0.85rem 1.2rem !important;
    max-width: 85% !important;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    border: 1px solid var(--border);
}

/* Avatar icons */
[data-testid="chatAvatarIcon-user"] {
    background: var(--gold) !important;
    color: var(--navy) !important;
}

[data-testid="chatAvatarIcon-assistant"] {
    background: linear-gradient(135deg, #1d4ed8, #7c3aed) !important;
}

/* ── Chat input ── */
[data-testid="stChatInput"] {
    background: var(--navy-mid) !important;
    border: 1px solid var(--border) !important;
    border-radius: 16px !important;
    color: var(--text) !important;
    box-shadow: 0 0 30px rgba(245,158,11,0.05), 0 4px 20px rgba(0,0,0,0.4) !important;
    transition: border-color 0.2s, box-shadow 0.2s;
}

[data-testid="stChatInput"]:focus-within {
    border-color: var(--gold) !important;
    box-shadow: 0 0 30px rgba(245,158,11,0.15), 0 4px 20px rgba(0,0,0,0.4) !important;
}

[data-testid="stChatInput"] textarea {
    color: var(--text) !important;
    font-family: 'Be Vietnam Pro', sans-serif !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: var(--text-muted) !important;
}

/* Submit button */
[data-testid="stChatInput"] button {
    background: var(--gold) !important;
    color: var(--navy) !important;
    border-radius: 10px !important;
}

/* ── Spinner ── */
[data-testid="stSpinner"] {
    color: var(--gold) !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--navy); }
::-webkit-scrollbar-thumb { background: var(--navy-soft); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--gold); }

/* ── Markdown text colors in chat ── */
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] h1,
[data-testid="stChatMessage"] h2,
[data-testid="stChatMessage"] h3 {
    color: inherit !important;
}

[data-testid="stChatMessage"] strong {
    color: var(--gold-soft) !important;
}

/* ── Sidebar info cards ── */
.info-card {
    background: rgba(245,158,11,0.08);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 0.8rem;
    font-size: 0.85rem;
    color: var(--text-muted);
    line-height: 1.6;
}

.info-card-title {
    color: var(--gold) !important;
    font-weight: 600;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.5rem;
}

/* ── Error messages ── */
[data-testid="stAlert"] {
    background: rgba(239,68,68,0.1) !important;
    border: 1px solid rgba(239,68,68,0.3) !important;
    border-radius: 12px !important;
    color: #fca5a5 !important;
}
            
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] ol,
[data-testid="stChatMessage"] ul,
[data-testid="stChatMessage"] h1,
[data-testid="stChatMessage"] h2,
[data-testid="stChatMessage"] h3,
[data-testid="stChatMessage"] span,
[data-testid="stChatMessage"] div {
    color: #e2e8f0 !important;
}

[data-testid="stChatMessage"] strong,
[data-testid="stChatMessage"] b {
    color: #fbbf24 !important;
}

/* User bubble text stays white */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) p,
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) li,
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) span {
    color: #f0f9ff !important;
}
            
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) *  {
    color: #f0f9ff !important;
}

/* Force all text in assistant bubble to light */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) * {
    color: #e2e8f0 !important;
}

/* Gold for bold in assistant bubble */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) strong,
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) b {
    color: #fbbf24 !important;
}
            
[data-testid="stChatInput"] textarea {
    color: #0f172a !important;
    background: #ffffff !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #94a3b8 !important;
}
            
/* Citation links */
[data-testid="stChatMessage"] a {
    color: #e2e8f0 !important;
    text-decoration: underline !important;
}

[data-testid="stChatMessage"] a:hover {
    color: var(--gold) !important;
}

</style>
""", unsafe_allow_html=True)

# ── Load secrets ─────────────────────────────────────────────────────────────
try:
    os.environ["SUPABASE_DB_HOST"]     = st.secrets.get("SUPABASE_DB_HOST", "")
    os.environ["SUPABASE_DB_PORT"]     = st.secrets.get("SUPABASE_DB_PORT", "5432")
    os.environ["SUPABASE_DB_NAME"]     = st.secrets.get("SUPABASE_DB_NAME", "")
    os.environ["SUPABASE_DB_USER"]     = st.secrets.get("SUPABASE_DB_USER", "")
    os.environ["SUPABASE_DB_PASSWORD"] = st.secrets.get("SUPABASE_DB_PASSWORD", "")
    os.environ["GOOGLE_API_KEY"]       = st.secrets.get("GOOGLE_API_KEY", "")
except Exception as e:
    st.error(f"❌ Lỗi tải cấu hình: {str(e)}")
    st.stop()

from chatbot import retrieve, generate_answer

# ── Load citations mapping ────────────────────────────────────────────────────
@st.cache_resource
def load_citations():
    """Load Citation.csv as a dict {parent_doc_id: url}"""
    citation_path = Path(__file__).parent.parent / "Citation.csv"
    citation_dict = {}
    try:
        with open(citation_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                citation_dict[row["parent_doc_id"].strip()] = row["url"].strip()
    except Exception as e:
        st.warning(f"Could not load citations: {e}")
    return citation_dict

CITATIONS = load_citations()

def extract_sources_from_response(response_text: str) -> tuple[str, list[str]]:
    """
    Extract JSON sources line and clean response.
    
    Returns:
        (clean_response, source_ids)
    """
    lines = response_text.split('\n', 1)
    first_line = lines[0].strip() if lines else ""
    rest = lines[1] if len(lines) > 1 else ""
    
    try:
        # Try to parse first line as JSON
        json_obj = json.loads(first_line)
        if "sources" in json_obj and isinstance(json_obj["sources"], list):
            return rest.strip(), json_obj["sources"]
    except json.JSONDecodeError:
        pass
    
    # If not valid JSON or no sources key, return full response
    return response_text, []

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🎓 ĐHBK Hà Nội")
    st.markdown("**Chatbot Quy chế Đào tạo**")
    st.divider()

    st.markdown("""
    <div class='info-card'>
        <div class='info-card-title'>📚 Phạm vi</div>
        Trả lời các câu hỏi về quy chế đào tạo, học phí, ngoại ngữ, cảnh báo học tập và các quy định liên quan.
    </div>
    <div class='info-card'>
        <div class='info-card-title'>💡 Gợi ý câu hỏi</div>
        • Điều kiện tốt nghiệp là gì?<br>
        • Học phí chương trình ELITECH?<br>
        • Cảnh báo học tập xử lý thế nào?<br>
        • Chuẩn ngoại ngữ đầu ra K68?
    </div>
    <div class='info-card'>
        <div class='info-card-title'>⚠️ Lưu ý</div>
        Thông tin dựa trên tài liệu quy chế đã được lập chỉ mục. Vui lòng kiểm tra văn bản gốc cho các quyết định quan trọng.
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    if st.button("🗑️ Xóa lịch sử chat", use_container_width=True):
        st.session_state.conversation_history = []
        st.rerun()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class='chat-header'>
    <h1>🎓 Chatbot Quy chế Đào tạo<br><span>ĐHBK Hà Nội</span></h1>
    <p>Hỏi bất cứ điều gì về quy chế đào tạo — tôi sẽ tìm kiếm thông tin từ tài liệu chính thức của trường.</p>
</div>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

MAX_HISTORY = 10

# ── Display history ───────────────────────────────────────────────────────────
for message in st.session_state.conversation_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ── Chat input ────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Nhập câu hỏi của bạn..."):
    st.session_state.conversation_history.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Đang tìm kiếm thông tin..."):
            try:
                raw_response = generate_answer(
                    query=prompt,
                    conversation_history=st.session_state.conversation_history,
                    top_k=5
                )
                
                # Extract sources and clean response
                clean_response, source_ids = extract_sources_from_response(raw_response)
                
                # Display the clean response
                st.markdown(clean_response)
                
                # Display sources if found
                if source_ids:
                    st.divider()
                    st.markdown("**📄 Nguồn tham khảo:**")
                    for doc_id in source_ids:
                        url = CITATIONS.get(doc_id, "")
                        if url:
                            st.markdown(f"- [{doc_id}]({url})")
                        else:
                            st.markdown(f"- {doc_id}")
                
                # Store clean response in history (without JSON line)
                st.session_state.conversation_history.append({"role": "assistant", "content": clean_response})

                if len(st.session_state.conversation_history) > MAX_HISTORY:
                    st.session_state.conversation_history = st.session_state.conversation_history[-MAX_HISTORY:]

            except Exception as e:
                st.error(f"❌ Đã xảy ra lỗi: {str(e)}")