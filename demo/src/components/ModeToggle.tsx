import { motion } from 'framer-motion';
import { useWorkspace, type LearningMode } from '../store/useWorkspace';
import { useState } from 'react';

const modes: Array<{ id: LearningMode; label: string; sub: string }> = [
  { id: 'master',  label: '精通模式', sub: '🎯' },
  { id: 'explore', label: '探索模式', sub: '🔭' },
];

export function ModeToggle() {
  const mode = useWorkspace((s) => s.mode);
  const setMode = useWorkspace((s) => s.setMode);
  const [stamping, setStamping] = useState<LearningMode | null>(null);

  return (
    <div
      className="mode-toggle"
      role="tablist"
      aria-label="学习模式"
    >
      {modes.map((m) => {
        const active = mode === m.id;
        return (
          <button
            key={m.id}
            role="tab"
            aria-selected={active}
            className={`mode-btn ${stamping === m.id ? 'stamp-anim' : ''}`}
            onMouseEnter={() => {
              setStamping(m.id);
              window.setTimeout(() => setStamping(null), 450);
            }}
            onClick={() => setMode(m.id)}
          >
            {active && (
              <motion.span
                layoutId="mode-indicator"
                className="mode-indicator"
                transition={{ type: 'spring', stiffness: 380, damping: 32 }}
              />
            )}
            <span className="mode-sub">{m.sub}</span>
            <span className="mode-label">{m.label}</span>
          </button>
        );
      })}

      <style>{`
        .mode-toggle {
          display: inline-flex;
          align-items: stretch;
          gap: 0;
          height: 32px;
          border: var(--border);
          background: var(--paper-card);
          position: relative;
        }
        .mode-btn {
          position: relative;
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 0 14px;
          font-family: var(--font-mono);
          font-size: 11px;
          letter-spacing: 0.04em;
          color: var(--ink-mute);
          border-right: var(--border-fade);
          transition: color .18s;
          overflow: hidden;
        }
        .mode-btn:last-child { border-right: none; }
        .mode-btn:hover { color: var(--ink); }
        .mode-btn[aria-selected="true"] { color: var(--paper); }
        .mode-sub { font-size: 12px; }
        .mode-indicator {
          position: absolute;
          inset: 0;
          background: var(--vermilion);
          z-index: 0;
        }
        .mode-sub, .mode-label { position: relative; z-index: 1; }
      `}</style>
    </div>
  );
}