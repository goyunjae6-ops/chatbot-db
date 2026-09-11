import { useState, useEffect } from "react";

// 배포할 때는 VITE_API_URL에 렌더 주소를 넣는다.
// 값이 없으면 로컬 서버를 쓴다.
// 예) VITE_API_URL=https://chatbot-db-back-f4ut.onrender.com
const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

/* ────────────────────────────────────────────────────────────
   렌더(Render) 무료 플랜 방어 코드

   무료 플랜 서버는 15분 동안 요청이 없으면 잠든다(슬립).
   잠든 서버는 첫 요청에서 30~60초를 그냥 기다리게 만든다.
   기본 fetch는 이때 무한정 매달리거나 그냥 실패해 버린다.

   그래서 아래 여섯 가지를 넣는다.
   1. 요청마다 제한 시간을 둔다(AbortController).
   2. 실패하면 잠깐 쉬었다 다시 시도한다.
   3. 오래 걸리면 "서버 깨우는 중"이라고 화면에 알린다.
   4. AI 요청은 원래 느리다. 이 요청만 제한 시간을 길게 준다.
   5. 화면이 열려 있는 동안 주기적으로 두드려 슬립 자체를 막는다.
   6. 끊긴 메시지는 함부로 다시 보내지 않는다. 먼저 저장됐는지 확인한다.
   ──────────────────────────────────────────────────────────── */

// 일반 요청 1회당 최대 대기 시간(밀리초)
const REQ_TIMEOUT = 20000;
// AI 응답 요청 1회당 최대 대기 시간(밀리초).
// 백엔드가 AI를 기다리는 시간보다 넉넉해야 한다.
const AI_TIMEOUT = 100000;
// 일반 요청 재시도 횟수
const REQ_RETRY = 2;
// 첫 접속 때 서버를 깨우며 기다리는 최대 시간(밀리초)
const WAKE_TIMEOUT = 120000;
// "깨우는 중" 안내를 띄우기 시작하는 시점(밀리초)
const WAKE_NOTICE_AFTER = 3000;
// 슬립을 막으려고 서버를 두드리는 간격(밀리초).
// 렌더는 15분 동안 요청이 없으면 잠든다. 그보다 짧게 잡는다.
const KEEPALIVE_INTERVAL = 600000;
// 깨우기·keep-alive 두드림 1회당 대기 시간(밀리초)
const PING_TIMEOUT = 10000;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// 제한 시간이 있는 fetch. 시간이 지나면 요청을 취소한다.
async function fetchWithTimeout(url, options = {}, timeout = REQ_TIMEOUT) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeout);
  try {
    return await fetch(url, { ...options, signal: ctrl.signal });
  } finally {
    clearTimeout(timer);
  }
}

export default function App() {
  const [sessions, setSession] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [editId, setEditId] = useState(null);
  const [editTitle, setEditTitle] = useState("");

  const [msgs, setMsgs] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  // 서버가 자고 있어 깨우는 중인지
  const [waking, setWaking] = useState(false);
  // 사용자에게 보여줄 오류 문구
  const [error, setError] = useState("");

  /* 공통 API 호출기.
     실패하면 재시도하고, 오래 걸리면 waking 표시를 켠다. */
  const api = async (
    path,
    options = {},
    retry = REQ_RETRY,
    timeout = REQ_TIMEOUT
  ) => {
    setError("");
    // 응답이 늦으면 "깨우는 중" 안내를 켠다.
    const notice = setTimeout(() => setWaking(true), WAKE_NOTICE_AFTER);

    try {
      let lastErr = null;

      for (let i = 0; i <= retry; i++) {
        try {
          const res = await fetchWithTimeout(`${API}${path}`, options, timeout);

          // 5xx는 서버 쪽 일시 장애다. 다시 시도한다.
          if (res.status >= 500) {
            lastErr = new Error(`서버 오류 (${res.status})`);
          } else if (!res.ok) {
            // 4xx는 다시 보내도 결과가 같다. 바로 끝낸다.
            let detail = `요청 실패 (${res.status})`;
            try {
              const body = await res.json();
              if (body?.detail) detail = body.detail;
            } catch {
              // 본문이 JSON이 아니면 기본 문구를 쓴다.
            }
            const fatal = new Error(detail);
            fatal.noRetry = true;
            throw fatal;
          } else {
            return await res.json();
          }
        } catch (e) {
          // 4xx로 우리가 직접 만든 오류는 재시도하지 않는다.
          if (e.noRetry) throw e;
          lastErr =
            e.name === "AbortError"
              ? new Error("서버 응답이 없습니다. (시간 초과)")
              : e;
        }

        // 마지막 시도가 아니면 잠깐 쉬었다 다시 건다. 2초 → 4초
        if (i < retry) await sleep(2000 * 2 ** i);
      }

      throw lastErr ?? new Error("알 수 없는 오류");
    } catch (e) {
      setError(e.message);
      throw e;
    } finally {
      clearTimeout(notice);
      setWaking(false);
    }
  };

  /* 첫 접속 때 서버를 깨운다.
     /health는 DB도 AI도 건드리지 않는 가장 가벼운 요청이다. */
  const wakeServer = async () => {
    const deadline = Date.now() + WAKE_TIMEOUT;
    let wait = 2000;

    while (Date.now() < deadline) {
      try {
        const res = await fetchWithTimeout(`${API}/health`, {}, PING_TIMEOUT);
        if (res.ok) return true;
      } catch {
        // 아직 안 깨어났다. 아래에서 기다렸다 다시 두드린다.
      }
      setWaking(true);
      await sleep(wait);
      // 대기 시간을 늘리되 8초를 넘기지 않는다.
      wait = Math.min(wait * 1.5, 8000);
    }
    return false;
  };

  /* 화면이 열려 있는 동안 서버가 잠들지 않게 주기적으로 두드린다.
     실패해도 그냥 넘어간다. 화면에 오류를 띄우지 않는다. */
  useEffect(() => {
    const ping = () => {
      // 숨겨진 탭은 두드리지 않는다. 쓸데없는 요청을 줄인다.
      if (document.hidden) return;
      fetchWithTimeout(`${API}/health`, {}, PING_TIMEOUT).catch(() => {});
    };

    const timer = setInterval(ping, KEEPALIVE_INTERVAL);
    // 다른 탭에 갔다가 돌아오면 곧바로 한 번 두드린다.
    document.addEventListener("visibilitychange", ping);

    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", ping);
    };
  }, []);

  // func
  // 세션데이터 로드
  const loadSessions = async () => {
    const data = await api(`/sessions`);
    setSession(data.sessions);
    return data.sessions;
  };

  //세션의 채팅기록 로드
  const loadMsg = async (id) => {
    if (!id) {
      setMsgs([]);
      return;
    }
    const data = await api(`/sessions/${id}/messages`);
    setMsgs(data.messages);
  };
  //선택된 세션 아이디 저장
  const openSession = (id) => {
    setSessionId(id);
    loadMsg(id).catch(() => {});
  };

  //새로운 세션 추가
  const newSession = async () => {
    try {
      const data = await api(`/sessions`, { method: "POST" });
      await loadSessions();
      setSessionId(data.id);
      setMsgs([]);
    } catch {
      // 오류 문구는 api 안에서 이미 상태에 담았다.
    }
  };

  // 리액트 컴포넌트 상태에 따라 함수실행을 제어
  useEffect(() => {
    // 먼저 서버를 깨우고, 깨어난 뒤에 데이터를 부른다.
    (async () => {
      const awake = await wakeServer();
      setWaking(false);
      if (!awake) {
        setError("서버를 깨우지 못했습니다. 잠시 뒤 새로고침해 주세요.");
        return;
      }
      try {
        const list = await loadSessions();
        if (list.length > 0) {
          setSessionId(list[0].id);
          await loadMsg(list[0].id);
        }
      } catch {
        // 오류 문구는 api 안에서 이미 상태에 담았다.
      }
    })();
  }, []);

  // 수정할 세션의 아이디, 타이틀로 선택
  const startRename = (s) => {
    setEditId(s.id);
    setEditTitle(s.title);
  };
  // 세션 타이틀 수정
  const saveTitle = async (id) => {
    try {
      await api(`/sessions/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: editTitle }),
      });
      setEditId(null);
      await loadSessions();
    } catch {
      // 오류 문구는 api 안에서 이미 상태에 담았다.
    }
  };
  // 세션삭제
  const removeSession = async (id) => {
    try {
      await api(`/sessions/${id}`, { method: "DELETE" });
      const list = await loadSessions();
      const next = list.length > 0 ? list[0].id : null;
      setSessionId(next);
      await loadMsg(next);
    } catch {
      // 오류 문구는 api 안에서 이미 상태에 담았다.
    }
  };
  /* 요청이 끊겼을 때, 서버에 실제로 저장됐는지 확인한다.
     저장돼 있으면 다시 보내지 않는다. 같은 말이 두 번 들어가는 걸 막는다. */
  const isSaved = async (id, text) => {
    try {
      const data = await api(`/sessions/${id}/messages`);
      setMsgs(data.messages);
      return data.messages.some((m) => m.role === "user" && m.text === text);
    } catch {
      // 확인조차 못 했다. 저장 안 된 것으로 본다.
      return false;
    }
  };

  //사용자의 메시지를 서버로 전달후 응답결과 반환
  const send = async () => {
    if (!input.trim() || !sessionId || loading) return;
    const text = input;
    setInput("");
    setLoading(true);
    try {
      /* AI 응답은 원래 오래 걸린다. 제한 시간을 길게 준다.
         그리고 재시도는 하지 않는다.
         이 요청은 DB에 글을 쓴다. 다시 보내면 같은 말이 두 번 저장된다. */
      await api(
        `/sessions/${sessionId}/messages`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        },
        0,
        AI_TIMEOUT
      );
      await loadMsg(sessionId);
      await loadSessions();
    } catch {
      // 끊겼어도 서버에는 저장됐을 수 있다. 먼저 확인한다.
      if (await isSaved(sessionId, text)) {
        await loadSessions();
        // api 안에서 오류 문구를 지우므로, 안내는 맨 마지막에 세운다.
        setError("답변을 받지 못했습니다. 잠시 뒤 다시 열어 보세요.");
      } else {
        // 정말 안 갔다. 입력한 글을 돌려줘서 다시 보낼 수 있게 한다.
        setInput(text);
      }
    } finally {
      setLoading(false);
    }
  };

  //엔터키 입력시 메시지 전송
  const onKey = (e) => {
    if (e.key === "Enter") send();
  };

  return (
    <div className="app">
      <aside className="side">
        <button className="new" onClick={newSession}>
          + 새 대화
        </button>
        <ul className="session-list">
          {sessions.map((s) => (
            <li key={s.id} className={s.id === sessionId ? "session on" : "session"}>
              {editId === s.id ? (
                <span className="rename">
                  <input value={editTitle} onChange={(e) => setEditTitle(e.target.value)} />
                  <button onClick={() => saveTitle(s.id)}>✓ 저장</button>
                </span>
              ) : (
                <>
                  <button className="session-title" onClick={() => openSession(s.id)}>
                    {s.title}
                  </button>
                  <span className="session-tools">
                    <button onClick={() => startRename(s)} aria-label="수정" title="수정">
                      ✏️
                    </button>
                    <button onClick={() => removeSession(s.id)} aria-label="삭제" title="삭제">
                      🗑️
                    </button>
                  </span>
                </>
              )}
            </li>
          ))}
        </ul>
      </aside>

      <main className="chat">
        {waking && (
          <p className="notice">서버를 깨우는 중입니다. 최대 1분 정도 걸립니다.</p>
        )}
        {error && <p className="notice error">{error}</p>}
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
          <button onClick={send} disabled={loading}>전송</button>
        </div>
      </main>
    </div>
  );
}
