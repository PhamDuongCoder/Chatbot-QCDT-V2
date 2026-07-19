FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY Script/ ./Script/

COPY Citation.csv .

EXPOSE 8501
EXPOSE 8000

# Mặc định chạy Streamlit; service "api" trong docker-compose sẽ override
# lệnh này để chạy uvicorn thay vì streamlit.
CMD ["streamlit", "run", "Script/app.py", "--server.port=8501", "--server.address=0.0.0.0"]