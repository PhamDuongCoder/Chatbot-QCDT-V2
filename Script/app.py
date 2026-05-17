import streamlit as st
import os

# Set page configuration FIRST, before any other Streamlit calls
st.set_page_config(
    page_title="Chatbot QCDT - ĐHBK Hà Nội",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load secrets from Streamlit and set as environment variables
# This must be done BEFORE importing chatbot module
try:
    os.environ["SUPABASE_DB_HOST"] = st.secrets.get("SUPABASE_DB_HOST", "")
    os.environ["SUPABASE_DB_PORT"] = st.secrets.get("SUPABASE_DB_PORT", "5432")
    os.environ["SUPABASE_DB_NAME"] = st.secrets.get("SUPABASE_DB_NAME", "")
    os.environ["SUPABASE_DB_USER"] = st.secrets.get("SUPABASE_DB_USER", "")
    os.environ["SUPABASE_DB_PASSWORD"] = st.secrets.get("SUPABASE_DB_PASSWORD", "")
    os.environ["GOOGLE_API_KEY"] = st.secrets.get("GOOGLE_API_KEY", "")
except Exception as e:
    st.error(f"❌ Error loading secrets: {str(e)}")
    st.stop()

# Now import chatbot module after environment variables are set
from chatbot import retrieve, generate_answer

# Add title and description
st.title("🤖 Chatbot Quy chế Đào tạo - ĐHBK Hà Nội")
st.markdown(
    "Hỏi bất cứ điều gì về quy chế đào tạo của trường. Tôi sẽ giúp bạn tìm kiếm thông tin cần thiết."
)

# Initialize session state
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

MAX_HISTORY = 10

# Display conversation history
for message in st.session_state.conversation_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Nhập câu hỏi của bạn..."):
    # Add user message to history
    st.session_state.conversation_history.append({
        "role": "user",
        "content": prompt
    })
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate and display assistant response
    with st.chat_message("assistant"):
        with st.spinner("Đang tìm kiếm thông tin..."):
            try:
                response = generate_answer(
                    query=prompt,
                    conversation_history=st.session_state.conversation_history,
                    top_k=5
                )
                st.markdown(response)
                
                # Add assistant response to history
                st.session_state.conversation_history.append({
                    "role": "assistant",
                    "content": response
                })
                
                # Trim conversation history if exceeds MAX_HISTORY
                if len(st.session_state.conversation_history) > MAX_HISTORY:
                    st.session_state.conversation_history = st.session_state.conversation_history[-MAX_HISTORY:]
                    
            except Exception as e:
                st.error(f"❌ Đã xảy ra lỗi khi xử lý câu hỏi: {str(e)}")
