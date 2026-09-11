import { useState, useEffect } from "react";

const API = "https://chatbot-db-back-bfxv.onrender.com";

// 렌더 무료 티어는 일정 시간 요청이 없으면 서버가 슬립 상태로 전환되고,
// 슬립 상태에서 깨어날 때 첫 요청이 30~60초 이상 걸릴 수 있다.
// fetch에 타임아웃을 걸고, 실패하면 잠시 대기 후 재시도한다.
async function fetchWithRetry(url, options = {}, { timeout = 20000, retries = 3, retryDelay = 3000 } = {}) {
  for (let attempt = 0; attempt <= retries; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    try {
      const res = await fetch(url, { ...options, signal: controller.signal });
      clearTimeout(timer);
      return res;
    } catch (err) {
      clearTimeout(timer);
      if (attempt === retries) throw err;
      await new Promise((r) => setTimeout(r, retryDelay));
    }
  }
}

// 서버가 응답할 때까지 /health를 반복 호출해 슬립 상태를 깨운다.
async function wakeServer({ timeout = 20000, interval = 3000, maxWait = 90000 } = {}) {
  const start = Date.now();
  while (Date.now() - start < maxWait) {
    try {
      const res = await fetchWithRetry(`${API}/health`, {}, { timeout, retries: 0 });
      if (res.ok) return true;
    } catch {
      // 무시하고 재시도
    }
    await new Promise((r) => setTimeout(r, interval));
  }
  return false;
}

export default function App() {
  const [sessions, setSession] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [editId, setEditId] = useState(null);
  const [editTitle, setEditTitle] = useState("");

  const [msgs, setMsgs] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [waking, setWaking] = useState(true);
  const [wakeFailed, setWakeFailed] = useState(false);
  const [error, setError] = useState("");

  // func
  // 세션데이터 로드
  const loadSessions = async () => {
    const res = await fetchWithRetry(`${API}/sessions`);
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
    const res = await fetchWithRetry(`${API}/sessions/${id}/messages`);
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
    const res = await fetchWithRetry(`${API}/sessions`, { method: "POST" }, { retries: 0 });
    const data = await res.json();
    await loadSessions();
    setSessionId(data.id);
    setMsgs([]);
  };

  // 렌더 서버를 깨운 뒤 세션 목록을 불러온다
  const connect = () => {
    setWaking(true);
    setWakeFailed(false);
    wakeServer()
      .then((awake) => {
        setWaking(false);
        setWakeFailed(!awake);
        return loadSessions();
      })
      .then((list) => {
        if (list && list.length > 0) {
          setSessionId(list[0].id);
          loadMsg(list[0].id);
        }
      })
      .catch(() => {
        setWaking(false);
        setWakeFailed(true);
      });
  };

  // 앱 시작 시 1회 실행
  useEffect(() => {
    connect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 수정할 세션의 아이디, 타이틀로 선택
  const startRename = (s) => {
    setEditId(s.id);
    setEditTitle(s.title);
  };
  // 세션 타이틀 수정
  const saveTitle = async (id) => {
    try {
      await fetchWithRetry(
        `${API}/sessions/${id}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: editTitle }),
        },
        { retries: 0 }
      );
      setEditId(null);
      await loadSessions();
    } catch {
      setError("서버 응답이 없습니다. 잠시 후 다시 시도해주세요.");
    }
  };
  // 세션삭제
  const removeSession = async (id) => {
    if (!id) return;

    try {
      const res = await fetchWithRetry(`${API}/sessions/${id}`, { method: "DELETE" }, { retries: 0 });
      if (!res.ok) {
        console.error("삭제 실패", await res.text());
        return;
      }
    } catch {
      setError("서버 응답이 없습니다. 잠시 후 다시 시도해주세요.");
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
    setError("");
    try {
      // 서버가 슬립 상태였다가 깨어나는 경우 + AI 응답 생성 시간을 고려해 넉넉한 타임아웃을 둔다.
      await fetchWithRetry(
        `${API}/sessions/${sessionId}/messages`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        },
        { timeout: 60000, retries: 0 }
      );
      await loadMsg(sessionId);
      await loadSessions();
    } catch {
      setError("서버 응답이 없습니다. 잠시 후 다시 시도해주세요.");
      setInput(text);
    } finally {
      setLoading(false);
    }
  };

  //엔터키 입력시 메시지 전송
  const onKey = (e) => {
    if (e.key === "Enter") send();
  };

  if (waking) {
    return (
      <div className="app-waking">
        <p>서버를 깨우는 중입니다...</p>
        <p className="hint">무료 서버가 잠자기 상태였다면 최대 1분 정도 걸릴 수 있어요.</p>
      </div>
    );
  }

  return (
    <div className="app">
      {wakeFailed && (
        <div className="wake-banner">
          서버에 연결할 수 없습니다.
          <button type="button" onClick={connect}>다시 시도</button>
        </div>
      )}
      {error && <div className="error-banner">{error}</div>}
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
