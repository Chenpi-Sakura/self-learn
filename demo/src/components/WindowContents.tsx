import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { docSample, exSample } from '../data/sample';

/** 讲义窗口内容 */
export function DocContent() {
  return (
    <div className="doc">
      <div className="doc-head">
        <span className="tiny">{docSample.chapter}</span>
        <span className="num mono" style={{ fontSize: 10, color: 'var(--ink-mute)' }}>进度 38%</span>
      </div>
      <h2 className="doc-title">{docSample.title}</h2>
      <div className="doc-body">
        {docSample.body.map((p, i) => (
          <p key={i} className={i === 2 || i === 3 ? 'doc-p doc-code' : 'doc-p'}>
            {p}
          </p>
        ))}
      </div>
      <div className="doc-foot">
        <span className="tiny">{docSample.footnote}</span>
      </div>

      <style>{`
        .doc { padding: 16px 20px; font-size: 13px; line-height: 1.75; color: var(--ink); }
        .doc-head { display: flex; justify-content: space-between; margin-bottom: 8px; }
        .doc-title { font-family: var(--font-mono); font-size: 18px; margin-bottom: 14px; letter-spacing: 0.02em; }
        .doc-body { display: flex; flex-direction: column; gap: 10px; }
        .doc-p { font-family: var(--font-sans); }
        .doc-code {
          font-family: var(--font-num);
          background: var(--paper-deep);
          padding: 8px 12px;
          border-left: 2px solid var(--vermilion);
          font-size: 12px;
          color: var(--ink-soft);
          letter-spacing: 0.02em;
        }
        .doc-foot {
          margin-top: 18px;
          padding-top: 10px;
          border-top: var(--border-fade);
          color: var(--ink-mute);
        }
      `}</style>
    </div>
  );
}

/** 习题窗口内容 */
export function ExContent() {
  const [picked, setPicked] = useState(0);
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState('');

  useEffect(() => {
    if (!streaming) return;
    const text = '  计算公式：Attention(Q,K,V) = softmax(QKᵀ / √d_k) · V';
    let i = 0;
    const id = window.setInterval(() => {
      i++;
      setStreamText(text.slice(0, i));
      if (i >= text.length) {
        window.clearInterval(id);
        window.setTimeout(() => {
          setStreaming(false);
          setStreamText('');
        }, 1200);
      }
    }, 22);
    return () => window.clearInterval(id);
  }, [streaming]);

  return (
    <div className="ex">
      <div className="ex-head">
        <span className="tiny">Q 03 / 12 · 难度 ★★★</span>
        <span className="num mono" style={{ fontSize: 10, color: 'var(--mint)' }}>剩 23:14</span>
      </div>
      <div className="ex-q">{exSample.q}</div>
      <div className="ex-opts">
        {exSample.options.map((o, i) => (
          <button
            key={i}
            className={`ex-opt ${picked === i ? 'is-pick' : ''}`}
            onClick={() => setPicked(i)}
          >
            <span className="ex-opt-mark">
              {picked === i ? '●' : '○'}
            </span>
            <span>{o}</span>
          </button>
        ))}
      </div>

      <div className="ex-ai-bar">
        <button className="ex-ai-btn" onClick={() => setStreaming(true)} disabled={streaming}>
          <span className="mono">▶  AI 讲解</span>
        </button>
        <span className="tiny" style={{ color: 'var(--ink-mute)' }}>{exSample.hint}</span>
      </div>

      {streaming && (
        <motion.div
          className="ex-stream num mono"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          {streamText}
          <span className="ex-caret">▍</span>
        </motion.div>
      )}

      <style>{`
        .ex { padding: 18px 20px; font-size: 13px; color: var(--ink); display: flex; flex-direction: column; gap: 14px; }
        .ex-head { display: flex; justify-content: space-between; }
        .ex-q { font-family: var(--font-sans); line-height: 1.7; font-size: 14px; }
        .ex-opts { display: flex; flex-direction: column; gap: 6px; }
        .ex-opt {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 10px 12px;
          border: var(--border);
          background: var(--paper);
          text-align: left;
          transition: all .15s;
        }
        .ex-opt:hover { background: var(--paper-deep); }
        .ex-opt.is-pick {
          background: var(--ink);
          color: var(--paper);
          border-color: var(--ink);
        }
        .ex-opt-mark { font-family: var(--font-mono); width: 14px; display: inline-block; }
        .ex-ai-bar { display: flex; justify-content: space-between; align-items: center; padding-top: 8px; border-top: var(--border-fade); }
        .ex-ai-btn {
          padding: 6px 12px;
          border: var(--border);
          background: var(--paper-deep);
          color: var(--ink);
        }
        .ex-ai-btn:hover:not(:disabled) {
          background: var(--vermilion);
          color: var(--paper);
          border-color: var(--vermilion);
        }
        .ex-stream {
          background: var(--ink);
          color: var(--paper);
          padding: 10px 12px;
          font-size: 12px;
          letter-spacing: 0.02em;
        }
        .ex-caret {
          display: inline-block;
          animation: blink 1s steps(2) infinite;
        }
        @keyframes blink { 50% { opacity: 0; } }
      `}</style>
    </div>
  );
}

/** 笔记窗口内容 */
export function NoteContent() {
  return (
    <div className="note">
      <div className="tiny" style={{ marginBottom: 8 }}>2026 / 07 / 10 · 14:21</div>
      <p className="note-p">
        <span className="note-hl">自注意力</span>的关键在于<span className="note-hl">序列内部的相关性</span>——
        每个位置都能看到所有其他位置。
      </p>
      <p className="note-p">
        区别于 RNN 的串行依赖，自注意力是 O(1) 路径长度，长距离依赖不衰减。
      </p>
      <p className="note-p">
        下一节：<span className="note-link">多头注意力为什么是 8？→</span>
      </p>

      <style>{`
        .note { padding: 16px 20px; font-size: 13px; line-height: 1.8; color: var(--ink); }
        .note-p { margin-bottom: 10px; }
        .note-hl { background: linear-gradient(transparent 60%, rgba(200, 52, 28, 0.25) 60%); padding: 0 2px; }
        .note-link { color: var(--vermilion); font-family: var(--font-mono); font-size: 12px; }
      `}</style>
    </div>
  );
}

/** 导图窗口内容 */
export function MindContent() {
  return (
    <div className="mind">
      <svg viewBox="0 0 380 200" width="100%" height="100%">
        <line x1="190" y1="100" x2="80"  y2="40"  stroke="var(--ink-soft)" />
        <line x1="190" y1="100" x2="80"  y2="160" stroke="var(--ink-soft)" />
        <line x1="190" y1="100" x2="300" y2="40"  stroke="var(--ink-soft)" />
        <line x1="190" y1="100" x2="300" y2="100" stroke="var(--ink-soft)" />
        <line x1="190" y1="100" x2="300" y2="160" stroke="var(--ink-soft)" />

        <rect x="140" y="80" width="100" height="40" fill="var(--vermilion)" />
        <text x="190" y="105" textAnchor="middle" fill="var(--paper)" fontFamily="var(--font-mono)" fontSize="11">自注意力</text>

        {[
          { x: 30,  y: 30,  t: 'Q / K / V' },
          { x: 30,  y: 150, t: 'Scaled Dot' },
          { x: 270, y: 30,  t: 'Mask' },
          { x: 270, y: 90,  t: 'Softmax' },
          { x: 270, y: 150, t: 'Multi-Head' },
        ].map((n, i) => (
          <g key={i}>
            <rect x={n.x} y={n.y} width="80" height="28" fill="var(--paper-card)" stroke="var(--ink-soft)" />
            <text x={n.x + 40} y={n.y + 18} textAnchor="middle" fill="var(--ink)" fontFamily="var(--font-mono)" fontSize="10">{n.t}</text>
          </g>
        ))}
      </svg>

      <style>{`
        .mind { padding: 0; height: 100%; background: var(--paper); }
        .mind svg { display: block; }
      `}</style>
    </div>
  );
}