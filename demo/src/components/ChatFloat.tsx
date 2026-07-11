import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface Msg {
  who: 'user' | 'ai';
  text: string;
}

const initial: Msg[] = [
  { who: 'ai', text: '你好，我是你的学习助手「小书」。看完讲义后，有没有哪个公式想再展开聊聊？' },
];

/** AI 对话浮窗：右下角 always 置顶 */
export function ChatFloat() {
  const [msgs, setMsgs] = useState<Msg[]>(initial);
  const [draft, setDraft] = useState('');
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const send = () => {
    if (!draft.trim() || streaming) return;
    const u: Msg = { who: 'user', text: draft };
    setMsgs((m) => [...m, u]);
    setDraft('');
    setStreaming(true);

    // 假"AI 正在思考"
    window.setTimeout(() => {
      const full = '理解 ✓。给你一个直觉：把 Q 想成"我要找什么"，K 想成"我手里有什么"，V 是"找到后交付什么"。';
      let i = 0;
      const id = window.setInterval(() => {
        i++;
        setMsgs((m) => {
          const last = m[m.length - 1];
          if (last.who === 'ai' && streaming) {
            return [...m.slice(0, -1), { ...last, text: full.slice(0, i) }];
          }
          return [...m, { who: 'ai', text: full.slice(0, i) }];
        });
        if (i >= full.length) {
          window.clearInterval(id);
          setStreaming(false);
        }
      }, 28);
    }, 600);
  };

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [msgs]);

  return (
    <motion.div
      className="chat"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.6, duration: 0.5 }}
    >
      <div className="chat-title">
        <span className="chat-pin">
          <svg width="11" height="11" viewBox="0 0 11 11"><path d="M 5.5 1 L 5.5 7 M 3 5 L 8 5 M 2.5 9 L 8.5 9" fill="none" stroke="currentColor" strokeWidth="1" /></svg>
        </span>
        <span className="mono chat-name">AI · 小书</span>
        <span className="tiny" style={{ marginLeft: 'auto' }}>always-on</span>
        <button className="chat-btn">▾</button>
      </div>

      <div className="chat-list" ref={scrollRef}>
        {msgs.map((m, i) => (
          <div key={i} className={`chat-bubble chat-${m.who}`}>
            <div className="chat-who tiny">
              {m.who === 'user' ? '你' : '小书'}
            </div>
            <div className="chat-text">{m.text}</div>
          </div>
        ))}
        {streaming && <span className="chat-typing num mono">小书正在输入 ▍</span>}
      </div>

      <div className="chat-input">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder="问点什么…   ⌘K 全局唤起"
        />
        <button onClick={send} disabled={!draft.trim() || streaming}>
          <span className="mono">↵</span>
        </button>
      </div>

      <style>{`
        .chat {
          position: fixed;
          right: 16px;
          bottom: calc(var(--dock-h) + 16px);
          width: 360px;
          height: 460px;
          background: var(--paper-card);
          border: var(--border);
          display: flex;
          flex-direction: column;
          z-index: 11000;
          box-shadow: 2px 2px 0 0 var(--ink-soft);
        }
        .chat-title {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 0 10px;
          height: 30px;
          background: var(--ink);
          color: var(--paper);
          border-bottom: var(--border);
        }
        .chat-pin { color: var(--paper); display: inline-flex; }
        .chat-name { font-size: 11px; letter-spacing: 0.08em; }
        .chat-btn { color: var(--paper); padding: 0 4px; font-size: 11px; }
        .chat-list {
          flex: 1;
          min-height: 0;
          padding: 12px;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 10px;
          background: var(--paper);
        }
        .chat-bubble {
          display: flex;
          flex-direction: column;
          gap: 2px;
          max-width: 85%;
        }
        .chat-user {
          align-self: flex-end;
          background: var(--ink);
          color: var(--paper);
          padding: 8px 12px;
        }
        .chat-ai {
          align-self: flex-start;
          background: var(--paper-card);
          color: var(--ink);
          padding: 8px 12px;
          border: var(--border);
        }
        .chat-who { font-size: 9px; opacity: 0.6; margin-bottom: 2px; }
        .chat-text { font-size: 12px; line-height: 1.6; }
        .chat-typing {
          font-size: 10px;
          color: var(--ink-mute);
          padding-left: 4px;
        }
        .chat-input {
          display: flex;
          align-items: center;
          gap: 0;
          padding: 8px;
          border-top: var(--border);
          background: var(--paper-deep);
        }
        .chat-input input {
          flex: 1;
          padding: 6px 8px;
          font-size: 12px;
          background: var(--paper);
          border: var(--border);
        }
        .chat-input button {
          width: 32px;
          height: 28px;
          background: var(--ink);
          color: var(--paper);
          font-size: 14px;
          margin-left: 4px;
        }
        .chat-input button:disabled {
          background: var(--faded);
          cursor: not-allowed;
        }
      `}</style>
    </motion.div>
  );
}