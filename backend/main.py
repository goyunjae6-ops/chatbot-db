from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
import requests, os
from pathlib import Path
from threading import Lock
from dotenv import load_dotenv
import db
from basic_bot import basic_reply

load_dotenv(Path(__file__).resolve().with_name(".env"))  # .env의 키를 추출하는 함수
app = FastAPI()
db.init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://0.0.0.0:5173",
        "http://0.0.0.0:5174",
        "http://0.0.0.0:5175",
        "https://two026-chatbot-frontend.onrender.com",
        "https://chatbot-db-front-x8gl.onrender.com",
        *[origin.strip().rstrip("/") for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()],
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Msg(BaseModel):
    text: str = Field(min_length=1, max_length=12000)
    request_id: str | None = Field(default=None, max_length=100)

    @field_validator("text")
    @classmethod
    def nonblank(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("메시지를 입력해 주세요.")
        return value


class Title(BaseModel):
    title: str = Field(min_length=1, max_length=100)


HF_URL = "https://router.huggingface.co/v1/chat/completions"
HF_MODEL = os.getenv("HF_MODEL", "Qwen/Qwen3-4B-Instruct-2507")
REPLY_MODE = os.getenv("CHAT_MODE", "basic").strip().lower()
if REPLY_MODE not in ("basic", "huggingface"):
    raise RuntimeError("CHAT_MODE must be basic or huggingface")
SYSTEM_PROMPT = """당신은 친절하고 유능한 AI 도우미입니다. 사용자의 언어로 답하고, 한국어 질문에는 자연스러운 한국어로 답하세요.
이전 대화의 맥락을 참고하고 질문의 의도를 정확히 파악하세요. 결론부터 말하고 필요에 따라 단계, 예시, 코드를 제공하세요.
모르는 내용은 추측을 사실처럼 말하지 마세요. 실시간 검색이나 파일 접근을 했다고 주장하지 마세요.
코드는 언어 이름이 붙은 마크다운 코드 블록으로 작성하세요. 불필요한 장황함을 피하고 사용자의 요청에 집중하세요."""
_session_locks = [Lock() for _ in range(128)]


def require_session(session_id):
    if not db.get_session(session_id):
        raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다. 새 대화를 시작해 주세요.")


def ask_ai(history):
    if REPLY_MODE == "basic":
        return basic_reply(history)
    token = os.getenv("HF_TOKEN")
    if not token:
        raise HTTPException(status_code=503, detail="AI 서비스 설정을 확인해 주세요.")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "model": HF_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *history],
        "max_tokens": 2048,
    }
    try:
        res = requests.post(HF_URL, headers=headers, json=payload, timeout=(10, 60))
        res.raise_for_status()
    except requests.Timeout:
        raise HTTPException(status_code=504, detail="AI 응답 시간이 초과되었습니다.") from None
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else 502
        detail = {
            400: "AI 모델을 사용할 수 없습니다. 서버의 HF_MODEL 설정을 확인해 주세요.",
            401: "AI 인증 토큰이 유효하지 않습니다. 서버의 HF_TOKEN을 확인해 주세요.",
            402: "AI 사용 크레딧이 부족합니다. Hugging Face 계정의 사용량을 확인해 주세요.",
            403: "AI 접근 권한이 없습니다. Hugging Face 토큰의 추론 권한을 확인해 주세요.",
            429: "AI 요청 한도를 초과했습니다. 잠시 뒤 다시 시도해 주세요.",
        }.get(status, "AI 서비스에 일시적인 문제가 있습니다. 잠시 뒤 다시 시도해 주세요.")
        raise HTTPException(status_code=503 if status in (401, 402, 403) else 502, detail=detail) from None
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="AI 서비스에 연결하지 못했습니다. 잠시 뒤 다시 시도해 주세요.") from None
    try:
        reply = res.json()["choices"][0]["message"]["content"]
        if not isinstance(reply, str) or not reply.strip():
            raise ValueError("Empty reply")
        return reply
    except (ValueError, KeyError, IndexError, TypeError):
        raise HTTPException(status_code=502, detail="AI 서비스에서 올바른 답변을 받지 못했습니다.") from None


def build_history(session_id):
    rows = db.read_message(session_id)[-30:]
    budget = 24000
    selected = []
    for row in reversed(rows):
        if selected and budget < len(row["text"]):
            break
        selected.append(row)
        budget -= len(row["text"])
    rows = list(reversed(selected))
    while rows and rows[0]["role"] != "user":
        rows.pop(0)
    return [
        {"role": "user" if r["role"] == "user" else "assistant", "content": r["text"]}
        for r in rows
    ]


@app.get("/health")
def health():
    return {
        "status": "ok", "ai_configured": bool(os.getenv("HF_TOKEN")),
        "mode": REPLY_MODE,
        "model": "기본 답변 모드 · 외부 AI 미사용" if REPLY_MODE == "basic" else HF_MODEL,
    }


@app.post("/chat")
def chat(msg: Msg):
    reply = ask_ai([{"role": "user", "content": msg.text}])
    return {"reply": reply}


# Create  # Delete
@app.post("/sessions")
def new_session():
    session_id = db.create_session()
    return {"id": session_id, "title": "새 대화"}


# Read
@app.get("/sessions")
def list_sessions():
    return {"sessions": db.read_sessions()}


@app.get("/sessions/{session_id}/messages")
def list_messages(session_id: int):
    require_session(session_id)
    return {"messages": db.read_message(session_id)}


@app.post("/sessions/{session_id}/messages")
def send_message(session_id: int, msg: Msg):
    lock = _session_locks[session_id % len(_session_locks)]
    if not lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="이 대화의 답변을 생성 중입니다. 잠시 기다려 주세요.")
    try:
        require_session(session_id)
        if msg.request_id:
            saved = db.get_request(msg.request_id)
            if saved:
                if saved["session_id"] != session_id or saved["text"] != msg.text:
                    raise HTTPException(status_code=409, detail="요청 식별자가 중복되었습니다.")
                return {"reply": saved["reply"]}
        history = build_history(session_id)
        reply = ask_ai([*history, {"role": "user", "content": msg.text}])
        require_session(session_id)
        db.save_exchange(session_id, msg.text, reply, msg.request_id)
        return {"reply": reply}
    finally:
        lock.release()


# Update
@app.put("/sessions/{session_id}")
def rename_session(session_id: int, body: Title):
    title = body.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="제목이 비어 있습니다.")
    if (
        db.update_session(session_id, title) == 0
    ):  # update_session 전달인자가 0이면 true
        raise HTTPException(status_code=404, detail="해당 대화가 없습니다.")
    return {"id": session_id, "title": title}

# Delete
@app.delete("/sessions/{session_id}")
def remove_session(session_id:int):
    lock = _session_locks[session_id % len(_session_locks)]
    if not lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="답변 생성 중에는 대화를 삭제할 수 없습니다.")
    try:
        if db.delete_session(session_id) == 0:
            raise HTTPException(status_code=404, detail="해당 대화가 없습니다.")
        return {"delete": session_id}
    finally:
        lock.release()
