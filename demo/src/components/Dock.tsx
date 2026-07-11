import { motion } from 'framer-motion';
import { dockApps } from '../data/sample';

/**
 * Dock：9 个应用入口
 * - 当前打开的窗口对应的 app 有高亮（这里简化为"藏宝图" + 当前布局图标对应的几个）
 * - hover 上浮
 */
export function Dock() {
  // demo 简化：根据当前布局，让对应 app 高亮
  // 实际工程应该用 store.windows 推算
  const activeIds = new Set<string>(['map', 'doc', 'ex']);

  return (
    <nav className="dock" aria-label="应用 Dock">
      <div className="dock-strip">
        {dockApps.map((app, i) => {
          const active = activeIds.has(app.id);
          return (
            <motion.button
              key={app.id}
              className={`dock-item ${active ? 'is-active' : ''}`}
              whileHover={{ y: -4 }}
              transition={{ type: 'spring', stiffness: 400, damping: 22 }}
              title={`${app.name} · ⌘${i + 1}`}
            >
              <div className="dock-icon">
                <span className="dock-glyph mono">{app.glyph}</span>
                {app.badge ? (
                  <span className="dock-badge num mono">{app.badge}</span>
                ) : null}
              </div>
              <span className="dock-name tiny">{app.name}</span>
              {active && <span className="dock-active-bar" />}
              <div className="dock-tip mono">{app.name} · ⌘{i + 1}</div>
            </motion.button>
          );
        })}
      </div>

      <div className="dock-right">
        <span className="tiny" style={{ color: 'var(--ink-mute)' }}>当前布局</span>
        <span className="dock-current mono">阅读模式</span>
        <button className="dock-save">保存布局</button>
      </div>

      <style>{`
        .dock {
          position: fixed;
          left: 0; right: 0; bottom: 0;
          height: var(--dock-h);
          background: var(--paper);
          border-top: var(--border);
          display: flex;
          align-items: center;
          padding: 0 12px;
          gap: 12px;
          z-index: 5000;
        }
        .dock-strip {
          display: flex;
          gap: 4px;
          flex: 1;
          overflow-x: auto;
        }
        .dock-item {
          position: relative;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 2px;
          padding: 6px 8px;
          min-width: 56px;
          color: var(--ink-mute);
          transition: color .15s;
        }
        .dock-item:hover { color: var(--ink); }
        .dock-item.is-active { color: var(--ink); }
        .dock-icon {
          position: relative;
          width: 36px;
          height: 36px;
          display: flex;
          align-items: center;
          justify-content: center;
          border: var(--border);
          background: var(--paper-card);
          font-family: var(--font-mono);
          font-size: 16px;
        }
        .dock-item.is-active .dock-icon {
          background: var(--vermilion);
          color: var(--paper);
          border-color: var(--vermilion);
        }
        .dock-glyph { position: relative; z-index: 1; }
        .dock-badge {
          position: absolute;
          top: -4px;
          right: -4px;
          min-width: 14px;
          height: 14px;
          padding: 0 3px;
          background: var(--vermilion);
          color: var(--paper);
          font-size: 9px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          z-index: 2;
        }
        .dock-name {
          font-size: 9px;
          letter-spacing: 0.04em;
          white-space: nowrap;
        }
        .dock-active-bar {
          position: absolute;
          bottom: 0;
          left: 30%;
          right: 30%;
          height: 2px;
          background: var(--vermilion);
        }
        .dock-tip {
          position: absolute;
          bottom: calc(100% + 6px);
          left: 50%;
          transform: translateX(-50%);
          background: var(--ink);
          color: var(--paper);
          padding: 4px 8px;
          font-size: 10px;
          white-space: nowrap;
          opacity: 0;
          pointer-events: none;
          transition: opacity .15s;
        }
        .dock-item:hover .dock-tip { opacity: 1; }
        .dock-right {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 0 8px;
          border-left: var(--border-fade);
          padding-left: 14px;
        }
        .dock-current {
          font-size: 11px;
          letter-spacing: 0.06em;
          padding: 4px 8px;
          background: var(--paper-card);
          border: var(--border);
        }
        .dock-save {
          padding: 4px 10px;
          font-family: var(--font-mono);
          font-size: 10px;
          letter-spacing: 0.06em;
          border: var(--border);
          background: var(--paper-card);
          color: var(--ink);
        }
        .dock-save:hover { background: var(--ink); color: var(--paper); }
      `}</style>
    </nav>
  );
}