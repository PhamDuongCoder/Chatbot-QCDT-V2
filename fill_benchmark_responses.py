import csv
import os
import sys
import time
from pathlib import Path
import tomllib

os.chdir(Path(__file__).resolve().parent)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

DELAY_SECONDS = 1.5
MAX_RATE_LIMIT_RETRIES = 3
BENCHMARK_DIR = Path(__file__).resolve().parent / "Benchmark"
QUESTION_COLUMN = "Question"
RESPONSE_COLUMN = "Chatbot's response"


def load_runtime_config() -> None:
    secrets_path = Path(__file__).resolve().parent / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        with secrets_path.open("rb") as file:
            secrets = tomllib.load(file)

        for key in (
            "SUPABASE_DB_HOST",
            "SUPABASE_DB_PORT",
            "SUPABASE_DB_NAME",
            "SUPABASE_DB_USER",
            "SUPABASE_DB_PASSWORD",
            "GOOGLE_API_KEY",
        ):
            value = secrets.get(key)
            if value:
                os.environ[key] = str(value)


load_runtime_config()

SCRIPT_DIR = Path(__file__).resolve().parent / "Script"
sys.path.insert(0, str(SCRIPT_DIR))

import chatbot  # noqa: E402


chatbot.SYSTEM_INSTRUCTION = """
Bạn là chuyên gia về quy chế đào tạo của Trường Đại học Bách khoa Hà Nội.
Vai trò của bạn là trả lời các câu hỏi của sinh viên dựa trên các chunk thông tin được cung cấp dưới dạng {title, summary, content, parent_doc_id}.
Chỉ sử dụng thông tin trong các chunk được cung cấp; không bịa và không dựa vào nguồn ngoài.

Bạn PHẢI xuất dòng JSON đầu tiên của mọi phản hồi theo đúng định dạng:
{"sources": ["parent_doc_id_1", "parent_doc_id_2", ...]}
Dòng JSON này chỉ chứa các parent_doc_id của các chunk thực sự được dùng để trả lời.

Sau dòng JSON, trả lời bằng tiếng Việt, đi thẳng vào vấn đề, tối đa 2-3 câu.
Nếu có điều/khoản/quy định liên quan, hãy trích rõ số điều, khoản hoặc tên quy định nếu thông tin đó có trong chunk.
Không chào hỏi, không dùng câu dẫn, không thêm cụm từ đệm hoặc thông tin không cần thiết.
Nếu không đủ thông tin để trả lời, nói ngắn gọn rằng không có đủ thông tin trong dữ liệu được cung cấp.
Nếu các chunk có thông tin mâu thuẫn giữa các năm, ưu tiên văn bản mới hơn với quy định áp dụng chung; nếu áp dụng theo khóa tuyển sinh thì trả lời theo đúng khóa được hỏi.
"""


def truncate(text: str, max_length: int = 60) -> str:
    text = " ".join((text or "").split())
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def is_empty(value: str) -> bool:
    if value is None or not str(value).strip():
        return True
    return str(value).strip().startswith("ERROR:")

def extract_answer(response: str) -> str:
    lines = response.strip().splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("{") and "sources" in stripped:
            continue
        return "\n".join(lines[i:]).strip()
    return response

def is_rate_limit_error(exc: Exception) -> bool:
    values = [
        getattr(exc, "code", None),
        getattr(exc, "status_code", None),
        getattr(exc, "grpc_status_code", None),
        getattr(getattr(exc, "response", None), "status_code", None),
        exc.__class__.__name__,
        str(exc),
    ]
    haystack = " ".join(str(value) for value in values if value is not None).lower()
    return (
        "429" in haystack
        or "resourceexhausted" in haystack
        or "resource exhausted" in haystack
    )


def generate_with_retries(question: str) -> str:
    for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
        try:
            return extract_answer(chatbot.generate_answer(question, conversation_history=[]))
        except Exception as exc:
            if not is_rate_limit_error(exc):
                return f"ERROR: {exc}"

            if attempt >= MAX_RATE_LIMIT_RETRIES:
                return "ERROR: rate limit exceeded"

            time.sleep(DELAY_SECONDS * 3)

    return "ERROR: rate limit exceeded"


def save_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp_path, path)


def process_file(path: Path) -> None:
    print(f"File: {path.name}", flush=True)

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    missing_columns = [
        column
        for column in (QUESTION_COLUMN, RESPONSE_COLUMN)
        if column not in fieldnames
    ]
    if missing_columns:
        print(f"  Skipping: missing columns {missing_columns}", flush=True)
        return

    changed = False
    for row_index, row in enumerate(rows, start=1):
        if not is_empty(row.get(RESPONSE_COLUMN)):
            continue

        question = row.get(QUESTION_COLUMN, "")
        print(f"  Row {row_index}: {truncate(question)}", flush=True)
        row[RESPONSE_COLUMN] = generate_with_retries(question)
        changed = True
        save_csv(path, fieldnames, rows)
        time.sleep(DELAY_SECONDS)

    if changed:
        print(f"  Saved: {path.name}", flush=True)
    else:
        print("  No empty responses found", flush=True)


def main() -> None:
    csv_paths = sorted(BENCHMARK_DIR.glob("*.csv"))
    if not csv_paths:
        print(f"No CSV files found in {BENCHMARK_DIR}", flush=True)
        return

    for path in csv_paths:
        process_file(path)


if __name__ == "__main__":
    main()
