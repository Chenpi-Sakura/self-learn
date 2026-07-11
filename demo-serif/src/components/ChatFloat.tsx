import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { useWorkspace } from '../store/useWorkspace';
import './ChatFloat.css';

export function ChatFloat() {
  const chat = useWorkspace((s) => s.chat);
  const sendChat = useWorkspace((s) => s.sendChat);
  const [draft, setDraft] = useState('');
  const bodyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [chat]);

  const submit = () => {
    const v = draft.trim();
    if (!v) return;
    sendChat(v);
    setDraft('');
  };

  return (
    <aside className="chat">
      <div className="chat-head">
        <span className="av">书</span>
        <span className="name">小书</span>
        <span className="sub">Always on</span>
      </div>
      <div className="chat-body" ref={bodyRef}>
        {chat.map((m, i) => (
          <div key={i} className={`bubble ${m.role}`}>{m.text}</div>
        ))}
      </div>
      <div className="chat-input">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e: KeyboardEvent<HTMLInputElement>) => e.key === 'Enter' && submit()}
          placeholder="Ask anything…"
        />
        <button onClick={submit}>↑</button>
      </div>
    </aside>
  );
}