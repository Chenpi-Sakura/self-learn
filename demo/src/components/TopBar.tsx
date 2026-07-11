import { ModeToggle } from './ModeToggle';
import { LayoutIcons } from './LayoutIcons';

export function TopBar() {
  return (
    <header className="topbar">
      {/* 左：logo + 标题 */}
      <div className="tb-left">
        <div className="tb-logo" aria-hidden>
          <svg width="22" height="22" viewBox="0 0 22 22">
            <circle cx="11" cy="11" r="9" fill="none" stroke="currentColor" strokeWidth="1.2" />
            <path d="M11 2 L11 20 M2 11 L20 11" stroke="currentColor" strokeWidth="0.8" />
            <circle cx="11" cy="11" r="2" fill="var(--vermilion)" />
          </svg>
        </div>
        <div className="tb-title">
          <span className="mono" style={{ fontSize: 12, letterSpacing: '0.18em' }}>SELFLEARN</span>
          <span className="tiny" style={{ marginLeft: 8 }}>·  制图院 · v0.1</span>
        </div>
      </div>

      {/* 中：模式 + 布局 */}
      <div className="tb-mid">
        <ModeToggle />
        <span className="tb-divider" aria-hidden />
        <LayoutIcons />
      </div>

      {/* 右：搜索 + 时间 + 用户 */}
      <div className="tb-right">
        <div className="tb-search">
          <span className="tiny">⌕</span>
          <input placeholder="搜索节点 / 文档 / 习题" />
          <span className="tiny num">⌘K</span>
        </div>
        <span className="tb-clock num mono">14 : 32 : 08</span>
        <button className="tb-user" aria-label="用户菜单">
          <span className="tb-avatar">小</span>
          <span className="mono" style={{ fontSize: 11 }}>xiaoming</span>
        </button>
      </div>

      <style>{`
        .topbar {
          position: relative;
          z-index: 200;
          height: var(--topbar-h);
          display: grid;
          grid-template-columns: 280px 1fr 480px;
          align-items: center;
          padding: 0 16px;
          gap: 16px;
          background: var(--paper);
          border-bottom: var(--border);
        }
        .tb-left { display: flex; align-items: center; gap: 10px; }
        .tb-logo { color: var(--ink); display: inline-flex; }
        .tb-title { display: flex; align-items: baseline; gap: 4px; }
        .tb-mid {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 12px;
        }
        .tb-divider {
          display: inline-block;
          width: 1px;
          height: 20px;
          background: var(--border-fade);
        }
        .tb-right {
          display: flex;
          align-items: center;
          justify-content: flex-end;
          gap: 12px;
        }
        .tb-search {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          height: 32px;
          padding: 0 10px;
          border: var(--border);
          background: var(--paper-card);
          width: 280px;
          color: var(--ink-mute);
        }
        .tb-search input {
          flex: 1;
          font-size: 12px;
          color: var(--ink);
        }
        .tb-search input::placeholder { color: var(--faded); }
        .tb-clock {
          font-size: 12px;
          color: var(--ink-mute);
          letter-spacing: 0.08em;
        }
        .tb-user {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 0 8px;
          height: 32px;
          border: var(--border);
          background: var(--paper-card);
        }
        .tb-user:hover { background: var(--paper-deep); }
        .tb-avatar {
          width: 22px;
          height: 22px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          background: var(--ink);
          color: var(--paper);
          font-family: var(--font-mono);
          font-size: 12px;
          border-radius: 50%;
        }
      `}</style>
    </header>
  );
}