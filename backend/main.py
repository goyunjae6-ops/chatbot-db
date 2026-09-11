from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests, os
from dotenv import load_dotenv
import db

load_dotenv()  # .env의 키를 추출하는 함수
app = FastAPI()
db.init_db()
print(app)
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
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Msg(BaseModel):
    text: str


class Title(BaseModel):
    title: str


HF_URL = "https://router.huggingface.co/v1/chat/completions"
HF_MODEL = "Qwen/Qwen3-4B-Instruct-2507"


def ask_ai(history):
    token = os.getenv("HF_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "model": HF_MODEL,
        "messages": history,
        "max_tokens": 1000,
    }
    res = requests.post(HF_URL, headers=headers, json=payload)
    data = res.json()
    return data["choices"][0]["message"]["content"]


def build_history(session_id):
    rows = db.read_message(session_id)
    return [
        {"role": "user" if r["role"] == "user" else "assistant", "content": r["text"]}
        for r in rows
    ]


@app.get("/health")
def health():
    return {"status": "ok"}


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
    return {"messages": db.read_message(session_id)}


@app.post("/sessions/{session_id}/messages")
def send_message(session_id: int, msg: Msg):
    first = db.count_message(session_id) == 0
    db.create_message(session_id, "user", msg.text)
    if first:
        db.update_session(session_id, msg.text[:20])
    reply = ask_ai(build_history(session_id))
    db.create_message(session_id, "bot", reply)
    return {"reply": reply}


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
    if db.delete_session(session_id) == 0:
        raise HTTPException(status_code=404, detail="해당 대화가 없습니다.")
    return {"delete": session_id}
