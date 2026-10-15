import { useCallback, useEffect, useRef, useState } from 'react';
import { createReplyPresentation, prefersReducedMotion } from './replyPresentation';

const API = (import.meta.env.VITE_API_URL || (import.meta.env.DEV ? '/api' : '')).replace(/\/$/, '');

async function request(path, options = {}, timeout = 85000) {
  if (!API && import.meta.env.PROD) throw new Error('서버 주소가 설정되지 않았습니다. 배포 환경에 VITE_API_URL을 설정해 주세요.');
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const res = await fetch(`${API}${path}`, { ...options, signal: controller.signal });
    const body = await res.json().catch(() => null);
    if (!res.ok) {
      const detail = body?.detail;
      throw new Error(typeof detail === 'string' ? detail : res.status === 422 ? '입력 내용을 확인해 주세요. 메시지는 12,000자까지 보낼 수 있습니다.' : `서버 요청에 실패했습니다. (${res.status})`);
    }
    if (!body) throw new Error('서버가 올바른 응답을 보내지 않았습니다. 서버 주소를 확인해 주세요.');
    return body;
  } catch (err) {
    if (err.name === 'AbortError') throw new Error('응답 시간이 초과되었습니다. 잠시 뒤 다시 시도해 주세요.', { cause: err });
    if (err instanceof TypeError) throw new Error('서버에 연결하지 못했습니다. 인터넷 연결과 서버 주소를 확인해 주세요.', { cause: err });
    throw err;
  } finally { clearTimeout(timer); }
}
const json = (method, body) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

function BrandMark({ className = '' }) {
  return <img className={`brand-mark ${className}`} src="/yoonjaept.svg?v=2" alt="" aria-hidden="true" width="32" height="32" />;
}

function Icon({ name, className = '' }) {
  const paths = {
    search: 'm20 20-4-4M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0Z',
    edit: 'M12 4H5a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h13a2 2 0 0 0 2-2v-7M16 3l5 5M9 15l1-5L18 2l5 5-8 8-6 1Z',
    menu: 'M4 6h16M4 12h11M4 18h16',
    close: 'm6 6 12 12M6 18 18 6',
    arrow: 'M12 20V4m-7 7 7-7 7 7',
    download: 'M12 3v12m-5-5 5 5 5-5M4 16v4h16v-4',
    copy: 'M8 8h12v13H8V8Zm8-4V2H3v14h2',
    book: 'M3 4h6c2 0 3 1 3 2 0-1 1-2 3-2h6v15h-6c-2 0-3 1-3 2 0-1-1-2-3-2H3V4Zm9 2v15',
    calculator: 'M5 2h14v20H5V2Zm3 4h8M8 11h1m6 0h1m-8 4h1m6 0h1m-8 4h1m6 0h1',
    calendar: 'M4 5h16v16H4V5Zm0 5h16M8 2v6m8-6v6M8 14h2m4 0h2',
    note: 'M5 3h14v18H5V3Zm3 5h8m-8 4h8m-8 4h5',
    grid: 'M4 4h6v6H4V4Zm10 0h6v6h-6V4ZM4 14h6v6H4v-6Zm10 0h6v6h-6v-6Z',
  };
  return <svg className={`icon ${className}`} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name] || paths.note} /></svg>;
}

function Answer({ text }) {
  return text.split(/(```[\s\S]*?```)/g).map((part, i) => {
    if (!part.startsWith('```')) return <div key={i} className="prose">{part}</div>;
    const code = part.slice(3, -3);
    const newline = code.indexOf('\n');
    return <div className="code" key={i}><div className="code-label">{newline >= 0 ? code.slice(0, newline) || 'code' : 'code'}</div><pre><code>{newline >= 0 ? code.slice(newline + 1) : code}</code></pre></div>;
  });
}

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [connection, setConnection] = useState('connecting');
  const [model, setModel] = useState('');
  const [mode, setMode] = useState('');
  const [error, setError] = useState('');
  const [pending, setPending] = useState(null);
  const [failed, setFailed] = useState(null);
  const [reading, setReading] = useState(false);
  const [query, setQuery] = useState('');
  const [menuOpen, setMenuOpen] = useState(false);
  const [editId, setEditId] = useState(null);
  const [title, setTitle] = useState('');
  const [deleting, setDeleting] = useState(null);
  const [notice, setNotice] = useState('');
  const active = useRef(null);
  const sequence = useRef(0);
  const busy = useRef(false);
  const bottom = useRef(null);
  const textarea = useRef(null);
  const initialized = useRef(false);
  const mounted = useRef(false);
  const presentation = useRef(null);

  const refreshSessions = useCallback(async () => {
    const data = await request('/sessions');
    if (!Array.isArray(data.sessions)) throw new Error('대화 목록 응답이 올바르지 않습니다.');
    if (mounted.current) setSessions(data.sessions);
    return data.sessions;
  }, []);

  const readMessages = useCallback(async (id, { completeRequestId = null } = {}) => {
    if (active.current !== id) return;
    const version = ++sequence.current;
    if (!completeRequestId) setReading(true);
    try {
      const data = await request(`/sessions/${id}/messages`);
      if (!Array.isArray(data.messages)) throw new Error('대화 내용 응답이 올바르지 않습니다.');
      if (mounted.current && active.current === id && sequence.current === version) {
        setMessages(data.messages);
        // Swap the optimistic pair and saved history in one React batch.
        if (completeRequestId) setPending(previous => previous?.requestId === completeRequestId ? null : previous);
      }
    } finally {
      if (!completeRequestId && mounted.current && sequence.current === version) setReading(false);
    }
  }, []);

  const selectSession = useCallback((id, keepPresentation = false) => {
    if (!keepPresentation) {
      presentation.current?.cancel();
      setPending(previous => previous ? { ...previous, display: false } : previous);
    }
    active.current = id;
    sequence.current += 1;
    setSessionId(id);
    setMessages([]);
    setReading(false);
    setError('');
    setInput('');
    setMenuOpen(false);
  }, []);

  const connect = useCallback(async () => {
    setConnection('connecting');
    setError('');
    try {
      const health = await request('/health', {}, 120000);
      if (!mounted.current) return;
      setModel(health.model || 'AI');
      setMode(health.mode || 'huggingface');
      const list = await refreshSessions();
      if (!mounted.current) return;
      setConnection('ready');
      if (health.mode !== 'basic' && health.ai_configured === false) setError('AI 토큰이 설정되지 않았습니다. 서버의 HF_TOKEN 설정이 필요합니다.');
      if (!initialized.current && list.length && active.current === null) {
        initialized.current = true;
        selectSession(list[0].id);
        await readMessages(list[0].id);
      }
      initialized.current = true;
    } catch (err) {
      if (mounted.current) { setConnection('error'); setError(err.message); }
    }
  }, [refreshSessions, selectSession, readMessages]);

  useEffect(() => {
    mounted.current = true;
    const timer = setTimeout(() => { void connect(); }, 0);
    return () => {
      clearTimeout(timer);
      mounted.current = false;
      presentation.current?.cancel();
    };
  }, [connect]);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: pending?.phase === 'typing' || prefersReducedMotion() ? 'auto' : 'smooth', block: 'end' });
  }, [messages, pending, failed]);
  useEffect(() => {
    if (textarea.current) {
      textarea.current.style.height = 'auto';
      textarea.current.style.height = `${Math.min(textarea.current.scrollHeight, 180)}px`;
    }
  }, [input]);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(''), 2500);
    return () => clearTimeout(timer);
  }, [notice]);

  const openSession = async (id) => {
    selectSession(id);
    try { await readMessages(id); }
    catch (err) { if (active.current === id) setError(err.message); }
  };

  const send = async (retry = null) => {
    const text = retry?.text || input.trim();
    if (!text || busy.current || reading || connection !== 'ready') return;
    if (text.length > 12000) { setError('메시지는 12,000자까지 입력할 수 있습니다.'); return; }
    busy.current = true;
    setError('');
    let id = retry?.sessionId ?? active.current;
    const requestId = retry?.requestId || crypto.randomUUID();
    const pendingMessage = { sessionId: id, text, requestId, phase: 'waiting', visibleText: '', display: true };
    setPending(pendingMessage);
    const animation = createReplyPresentation({
      onUpdate(update) {
        if (mounted.current && active.current === id) {
          setPending(previous => previous?.requestId === requestId && previous.display
            ? { ...previous, ...update } : previous);
        }
      },
    });
    presentation.current = animation;
    if (!retry) setInput('');
    setFailed(null);
    try {
      if (!id) {
        const created = await request('/sessions', { method: 'POST' });
        id = created.id;
        // 사용자가 생성 도중 다른 대화를 열었다면 선택을 덮어쓰지 않는다.
        if (!mounted.current) return;
        if (active.current === null && !animation.cancelled) selectSession(id, true);
        setPending(previous => previous?.requestId === requestId ? { ...previous, sessionId: id } : previous);
      }
      const response = await request(`/sessions/${id}/messages`, json('POST', { text, request_id: requestId }));
      if (!mounted.current) return;
      if (typeof response.reply !== 'string' || !response.reply.trim()) throw new Error('올바른 답변을 받지 못했습니다. 다시 시도해 주세요.');
      await animation.present(response.reply);
      if (!mounted.current) return;
      // 목록 갱신 실패가 성공한 메시지를 재전송하게 만들지 않는다.
      await readMessages(id, { completeRequestId: requestId });
      await refreshSessions().catch(() => {});
    } catch (err) {
      if (!mounted.current) return;
      setFailed({ sessionId: id, text, requestId, error: err.message });
      if (active.current === id || (!id && active.current === null)) setError(err.message);
      await refreshSessions().catch(() => {});
    } finally {
      animation.cancel();
      if (presentation.current === animation) presentation.current = null;
      busy.current = false;
      if (mounted.current) {
        setPending(null);
        if (active.current === id) textarea.current?.focus();
      }
    }
  };

  const rename = async (id) => {
    if (!title.trim()) return;
    try {
      await request(`/sessions/${id}`, json('PUT', { title: title.trim() }));
      setEditId(null);
      await refreshSessions();
    } catch (err) { setError(err.message); }
  };
  const remove = async () => {
    const id = deleting;
    setDeleting(null);
    try {
      await request(`/sessions/${id}`, { method: 'DELETE' });
      if (active.current === id) selectSession(null);
      if (failed?.sessionId === id) setFailed(null);
      await refreshSessions();
    } catch (err) { setError(err.message); }
  };
  const copy = async (text) => {
    try { await navigator.clipboard.writeText(text); setNotice('복사했습니다.'); }
    catch { setNotice('복사하지 못했습니다. 텍스트를 선택해 복사해 주세요.'); }
  };
  const download = () => {
    const content = messages.map(m => `${m.role === 'user' ? '나' : 'AI'}\n${m.text}`).join('\n\n---\n\n');
    const url = URL.createObjectURL(new Blob([content], { type: 'text/plain;charset=utf-8' }));
    const a = document.createElement('a'); a.href = url; a.download = `chat-${sessionId}.txt`; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  const currentPending = pending && pending.display && pending.sessionId === sessionId ? pending : null;
  const currentFailed = failed && failed.sessionId === sessionId ? failed : null;
  const isEmpty = !messages.length && !currentPending && !currentFailed && !reading;
  const currentTitle = sessions.find(s => s.id === sessionId)?.title || '새로운 대화';
  const suggestions = mode === 'basic'
    ? [['grid', '질문 예시', '질문 예시'], ['book', '함께 공부하기', '리스트가 뭐야?'], ['calculator', '계산하기', '평균: 10, 20, 30'], ['calendar', '날짜 알아보기', '날짜 더하기: 2026-10-15, 7'], ['edit', '글쓰기 시작', '자기소개 작성: 이름=윤재; 분야=웹 개발; 경험=챗봇 제작; 목표=개발자'], ['note', '메모하기', '메모: 내일 오후 3시 회의']]
    : [['edit', '글쓰기 도와줘', '자연스러운 자기소개 글을 쓰고 싶어. 먼저 필요한 정보를 질문해 줘.'], ['book', '코드 함께 풀기', '파이썬을 처음 배우려고 해. 간단한 예제와 함께 학습 순서를 알려줘.'], ['note', '내용 정리하기', '긴 글을 핵심만 남겨 정리하려고 해. 글을 보내면 요약해 줄 수 있어?'], ['grid', '아이디어 떠올리기', '매일 실천할 수 있는 작은 사이드 프로젝트 아이디어를 5개 제안해 줘.']];

  return <div className="app">
    {menuOpen && <button className="backdrop" aria-label="대화 목록 닫기" onClick={() => setMenuOpen(false)} />}
    <aside className={`side ${menuOpen ? 'is-open' : ''}`} aria-label="대화 목록">
      <div className="brand"><BrandMark /><div>윤재피티<span>YoonjaePT</span></div><button className="mobile-close icon-button" aria-label="목록 닫기" onClick={() => setMenuOpen(false)}><Icon name="close" /></button></div>
      <button className="new" onClick={() => selectSession(null)}><Icon name="edit" />새 대화<span className="shortcut">＋</span></button>
      <label className="search"><Icon name="search" /><input aria-label="대화 검색" placeholder="대화 검색" value={query} onChange={e => setQuery(e.target.value)} /></label>
      <p className="side-label">대화 기록</p>
      <ul className="session-list">{sessions.filter(s => s.title.toLowerCase().includes(query.toLowerCase())).map(s => <li key={s.id} className={`session ${s.id === sessionId ? 'on' : ''}`}>
        {editId === s.id ? <form className="rename" onSubmit={e => { e.preventDefault(); void rename(s.id); }}><input aria-label="대화 제목" autoFocus maxLength={100} value={title} onChange={e => setTitle(e.target.value)} onKeyDown={e => { if (e.key === 'Escape') setEditId(null); }} /><button aria-label="제목 저장">✓</button><button type="button" aria-label="제목 수정 취소" onClick={() => setEditId(null)}>×</button></form> : <><button className="session-title" onClick={() => void openSession(s.id)} title={s.title}>{s.title}</button><div className="session-tools"><button aria-label={`${s.title} 제목 수정`} onClick={() => { setEditId(s.id); setTitle(s.title); }}>✎</button><button aria-label={`${s.title} 삭제`} disabled={pending?.sessionId === s.id} onClick={() => setDeleting(s.id)}>×</button></div></>}
      </li>)}</ul>
      {!sessions.length && <p className="side-empty">첫 질문을 보내면<br />대화가 여기에 저장돼요.</p>}
      <div className="side-bottom"><span className={`status-dot ${connection}`} />{connection === 'ready' ? '서버 연결됨' : connection === 'connecting' ? '서버에 연결하는 중' : '연결 확인 필요'}<small>대화는 이 서버에 저장됩니다.</small></div>
    </aside>
    <main className={`chat ${isEmpty ? 'is-empty' : ''}`}>
      <header className="chat-header"><button className="menu-button icon-button" aria-label="대화 목록 열기" onClick={() => setMenuOpen(true)}><Icon name="menu" /></button><div className="header-title"><strong>윤재피티</strong><span className="conversation-title">{currentTitle}</span></div><span className="mode-badge" title={model}>{mode === 'basic' ? '무료 기본 모드' : 'AI 모드'}</span><button className="text-button export" disabled={!messages.length} onClick={download}><Icon name="download" />대화 저장</button></header>
      <div className="conversation" role="log" aria-label="대화 내용" aria-busy={!!currentPending || reading}>
        {isEmpty && <section className="welcome"><BrandMark className="welcome-mark" /><h1>무엇을 도와드릴까요?</h1><p>궁금한 것부터 오늘의 할 일까지, 윤재피티와 함께.</p><div className="suggestions">{suggestions.map(([icon,label,prompt]) => <button key={label} onClick={() => { setInput(prompt); textarea.current?.focus(); }}><Icon name={icon} />{label}</button>)}</div></section>}
        {reading && <p className="loading" role="status">대화를 불러오는 중…</p>}
        {messages.map(m => <article className={`message ${m.role === 'user' ? 'user' : 'bot'}`} key={m.id}><div className="avatar">{m.role === 'user' ? '나' : <BrandMark />}</div><div className="message-body"><span className="sender">{m.role === 'user' ? '나' : '윤재피티'}</span><Answer text={m.text} /><button className="copy" aria-label="메시지 복사" onClick={() => void copy(m.text)}><Icon name="copy" />복사</button></div></article>)}
        {(currentPending || currentFailed) && <article className="message user"><div className="avatar">나</div><div className="message-body"><span className="sender">나</span><div className="prose">{(currentPending || currentFailed).text}</div></div></article>}
        {currentPending?.phase === 'waiting' && <div className="thinking" role="status"><BrandMark /><div className="thinking-dots"><i /><i /><i /></div><span>답변을 준비하고 있어요</span></div>}
        {currentPending?.phase === 'typing' && <article className="message bot typing-reply"><div className="avatar"><BrandMark /></div><div className="message-body"><div className="typing-heading"><span className="sender">윤재피티</span>{!currentPending.complete && <button type="button" className="show-reply" onClick={() => presentation.current?.skip()}>바로 보기</button>}</div><div aria-hidden="true"><Answer text={currentPending.visibleText} />{!currentPending.complete && <span className="typing-cursor" />}</div><span className="sr-only" role="status">{currentPending.complete ? '답변 표시가 완료되었습니다.' : '답변을 작성하고 있어요.'}</span></div></article>}
        {currentFailed && <div className="retry"><span>전송을 완료하지 못했어요.</span><button disabled={!!pending || connection !== 'ready'} onClick={() => void send(currentFailed)}>다시 시도 ↻</button><button onClick={() => { setInput(currentFailed.text); setFailed(null); setError(''); textarea.current?.focus(); }}>수정하기</button></div>}
        <div ref={bottom} />
      </div>
      <div className="composer-area">
        {connection === 'connecting' && <div className="notice" role="status">서버에 연결하고 있어요. 서버가 쉬고 있었다면 최대 2분 정도 걸릴 수 있습니다.</div>}
        {error && <div className="notice error" role="alert"><span>{error}</span><button onClick={() => setError('')} aria-label="오류 안내 닫기">×</button></div>}
        {connection === 'error' && <button className="reconnect" onClick={() => void connect()}>서버 다시 연결 ↻</button>}
        {pending && !currentPending && <p className="background-status" role="status">답변 요청을 처리하고 있습니다.</p>}
        <form className="composer" onSubmit={e => { e.preventDefault(); void send(); }}><textarea ref={textarea} aria-label="메시지 입력" placeholder="윤재피티에게 물어보세요" rows={1} maxLength={12000} value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing && e.keyCode !== 229) { e.preventDefault(); if (!e.repeat) void send(); } }} /><div className="composer-bottom"><span>Enter로 전송 · Shift + Enter로 줄바꿈</span><button aria-label="메시지 전송" type="submit" disabled={!input.trim() || !!pending || reading || connection !== 'ready'}><Icon name="arrow" /></button></div></form>
        <p className="footnote">{mode === 'basic' ? '무료 기본 모드 · 등록된 설명과 계산 기능으로 답해요. 자유로운 AI 대화는 지원하지 않아요.' : 'AI의 답변에는 오류가 있을 수 있어요. 중요한 정보는 확인해 주세요.'}</p>
      </div>
    </main>
    {notice && <div className="toast" role="status">{notice}</div>}
    {deleting !== null && <div className="dialog-backdrop"><section role="dialog" aria-modal="true" aria-labelledby="delete-title" className="dialog"><h2 id="delete-title">대화를 삭제할까요?</h2><p>이 대화의 메시지가 함께 삭제되며 되돌릴 수 없어요.</p><div><button autoFocus onClick={() => setDeleting(null)}>취소</button><button className="danger" onClick={() => void remove()}>삭제</button></div></section></div>}
  </div>;
}
