import { useState, useEffect } from "react";

//const API = "http://localhost:8000/chat";
const API = "https://chatbot-db-back-bfxv.onrender.com";
//const API = "http://127.0.0.1:8000";

export default function App() {
  const [sessions, setSession] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [editId, setEditId] = useState(null);
  const [editTitle, setEditTitle] = useState("");

  const [msgs, setMsgs] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  // func
  // 세션데이터 로드
  const loadSessions = async () => {
    const res = await fetch(`${API}/sessions`);
    const data = await res.json();
    setSession(data.sessions);
    return data.sessions;
  };

  //세션의 채팅기록 로드
  const loadMsg = async (id) => {
    if (!id) {
      setMsgs([]);
      return;
    }
    const res = await fetch(`${API}/sessions/${id}/messages`);
    const data = await res.json();
    console.log(res);
    setMsgs(data.messages);
  };
  //선택된 세션 아이디 저장
  const openSession = (id) => {
    setSessionId(id);
    loadMsg(id);
  };

  //새로운 세션 추가
  const newSession = async () => {
    const res = await fetch(`${API}/sessions`, { method: "POST" });
    const data = await res.json();
    await loadSessions();
    setSessionId(data.id);
    setMsgs([]);
  };

  // 리액트 컴포넌트 상태에 따라 함수실행을 제어
  useEffect(() => {
    loadSessions().then((list) => {
      if (list.length > 0) {
        console.log(list[0].id);
        setSessionId(list[0].id);
        loadMsg(list[0].id);
      }
    });
  }, []);

  // 수정할 세션의 아이디, 타이틀로 선택
  const startRename = (s) => {
    setEditId(s.id);
    setEditTitle(s.title);
  };
  // 세션 타이틀 수정
  const saveTitle = async (id) => {
    await fetch(`${API}/sessions/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: editTitle }),
    });
    setEditId(null);
    await loadSessions();
  };
  // 세션삭제
  const removeSession = async (id) => {
    if (!id) return;

    const res = await fetch(`${API}/sessions/${id}`, { method: "DELETE" });
    if (!res.ok) {
      console.error("삭제 실패", await res.text());
      return;
    }

    const list = await loadSessions();
    const next = list.length > 0 ? list[0].id : null;
    setSessionId(next);
    await loadMsg(next);
  };
  //사용자의 메시지를 서버로 전달후 응답결과 반환
  const send = async () => {
    if (!input.trim() || !sessionId) return;
    const text = input;
    setInput("");
    setLoading(true);
    await fetch(`${API}/sessions/${sessionId}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    await loadMsg(sessionId);
    await loadSessions();
    setLoading(false);
  };

  //엔터키 입력시 메시지 전송
  const onKey = (e) => {
    if (e.key === "Enter") send();
  };

  return (
    <div className="app">
      <aside className="side">
        <button type="button" className="new" onClick={newSession}>
          + 새 대화
        </button>
        <ul className="session-list">
          {sessions.map((s) => (
            <li key={s.id} className={s.id === sessionId ? "session on" : "session"}>
              {editId === s.id ? (
                <span className="rename">
                  <input value={editTitle} onChange={(e) => setEditTitle(e.target.value)} />
                  <button type="button" onClick={() => saveTitle(s.id)}>저장</button>
                </span>
              ) : (
                <>
                  <button type="button" className="session-title" onClick={() => openSession(s.id)}>
                    {s.title}
                  </button>
                  <span className="session-tools">
                    <button type="button" onClick={() => startRename(s)}>이름</button>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        removeSession(s.id);
                      }}
                    >
                      삭제
                    </button>
                  </span>
                </>
              )}
            </li>
          ))}
        </ul>
      </aside>

      <main className="chat">
        <div className="box">
          {msgs.map((m) => (
            <div key={m.id} className={m.role}>
              <p>{m.text}</p>
            </div>
          ))}
          {loading && <p className="loading">생각 중...</p>}
        </div>
        <div className="input-row">
          <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={onKey} placeholder="메시지를 입력하세요" />
          <button type="button" onClick={send}>전송</button>
        </div>
      </main>
    </div>
  );
}
