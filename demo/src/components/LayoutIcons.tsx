import { motion } from 'framer-motion';
import { useWorkspace, type LayoutId } from '../store/useWorkspace';
import { layoutOrder, layouts } from '../lib/layouts';

export function LayoutIcons() {
  const layout = useWorkspace((s) => s.layout);
  const setLayout = useWorkspace((s) => s.setLayout);

  return (
    <div className="layout-icons" role="tablist" aria-label="工作区布局">
      {layoutOrder.map((id: LayoutId) => {
        const p = layouts[id];
        const active = layout === id;
        return (
          <button
            key={id}
            role="tab"
            aria-selected={active}
            className="layout-btn"
            title={`切换到${p.label}（长按 2s 可保存当前布局为此预设）`}
            onClick={() => setLayout(id)}
          >
            {active && (
              <motion.span
                layoutId="layout-indicator"
                className="layout-indicator"
                transition={{ type: 'spring', stiffness: 380, damping: 32 }}
              />
            )}
            <span className="layout-glyph">{p.glyph}</span>
            <span className="layout-label">{p.label.replace('模式', '')}</span>
          </button>
        );
      })}

      <style>{`
        .layout-icons {
          display: inline-flex;
          gap: 0;
          height: 32px;
          border: var(--border);
          background: var(--paper-card);
        }
        .layout-btn {
          position: relative;
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 0 12px;
          font-family: var(--font-mono);
          font-size: 11px;
          letter-spacing: 0.04em;
          color: var(--ink-mute);
          border-right: var(--border-fade);
          transition: color .18s;
        }
        .layout-btn:last-child { border-right: none; }
        .layout-btn:hover { color: var(--ink); }
        .layout-btn[aria-selected="true"] { color: var(--paper); }
        .layout-indicator {
          position: absolute;
          inset: 0;
          background: var(--ink);
          z-index: 0;
        }
        .layout-glyph, .layout-label { position: relative; z-index: 1; }
        .layout-glyph { font-size: 13px; }
      `}</style>
    </div>
  );
}