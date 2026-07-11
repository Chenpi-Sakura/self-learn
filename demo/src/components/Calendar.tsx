import { useState } from 'react';
import { useWorkspace } from '../store/useWorkspace';
import { heatMap, todayIndex, tasks } from '../data/sample';

const DAYS = ['一', '二', '三', '四', '五', '六', '日'];

// 热力档位：4 档字符 + 颜色
const HEAT_GLYPH = ['·', '░', '▒', '▓', '█'];
const HEAT_COLOR = ['var(--faded-soft)', '#C9C2B5', '#A8C9B5', '#5C9A7E', 'var(--mint)'];

export function Calendar() {
  const checkedIn = useWorkspace((s) => s.checkedIn);
  const toggle = useWorkspace((s) => s.toggleCheckIn);
  const [hovered, setHovered] = useState<{ r: number; c: number } | null>(null);

  // 把热力转换为行
  return (
    <div className="cal-card">
      <div className="card-head">
        <span className="card-title mono">学习日历 · CALENDAR</span>
        <span className="card-meta num mono">2026 / 07 · ★ 32d</span>
        <button className="card-act" title="最小化">—</button>
      </div>

      <div className="cal-grid-wrap">
        {/* 表头 */}
        <div className="cal-grid">
          <div className="cal-row cal-head-row">
            {DAYS.map((d) => (
              <div key={d} className="cal-day-head mono">{d}</div>
            ))}
          </div>
          {heatMap.map((row, r) => (
            <div key={r} className="cal-row">
              {row.map((h, c) => {
                const isToday = r === todayIndex.row && c === todayIndex.col;
                const isFuture = r < todayIndex.row || (r === todayIndex.row && c > todayIndex.col);
                const isHover = hovered && hovered.r === r && hovered.c === c;
                const dayNum = r * 7 + c - 5; // 2026/7/1 是周三，第一格补 2 个空
                return (
                  <div
                    key={c}
                    className={`cal-cell ${isToday ? 'is-today' : ''} ${isFuture ? 'is-future' : ''}`}
                    onMouseEnter={() => setHovered({ r, c })}
                    onMouseLeave={() => setHovered(null)}
                  >
                    {dayNum > 0 && dayNum <= 31 && (
                      <span className="cal-day num mono">{dayNum}</span>
                    )}
                    {h > 0 && dayNum > 0 && dayNum <= 31 && (
                      <span
                        className="cal-heat"
                        style={{ color: HEAT_COLOR[h] }}
                      >
                        {HEAT_GLYPH[h]}
                      </span>
                    )}
                    {isToday && <span className="cal-today-mark" />}
                    {isHover && (
                      <div className="cal-tip">
                        <span className="mono">07 / {String(dayNum).padStart(2, '0')}</span>
                        <span className="num mono">{h * 18} min</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>

        {/* 右侧：打卡 + 统计 */}
        <div className="cal-side">
          <div className="cal-stat-block">
            <div className="tiny">本月累计</div>
            <div className="num mono cal-big">Σ 4 h 32 m</div>
            <div className="tiny" style={{ marginTop: 8 }}>连续打卡</div>
            <div className="num mono cal-big" style={{ color: 'var(--vermilion)' }}>× 32 d</div>
          </div>

          <button
            className={`cal-checkin ${checkedIn ? 'is-checked' : ''}`}
            onClick={toggle}
          >
            <span className="ci-mark" aria-hidden>
              <svg viewBox="0 0 16 16" width="14" height="14">
                <circle cx="8" cy="8" r="6.5" fill="none" stroke="currentColor" strokeWidth="1.2" />
                {checkedIn && <path d="M 5 8 L 7 10 L 11 6" fill="none" stroke="currentColor" strokeWidth="1.5" />}
              </svg>
            </span>
            <span className="ci-text">
              <span className="mono">{checkedIn ? '已打卡' : '今日打卡'}</span>
              <span className="num mono">{checkedIn ? '23 min' : '未开始'}</span>
            </span>
          </button>

          <div className="cal-legend">
            <div className="tiny" style={{ marginBottom: 4 }}>热力档位</div>
            <div className="legend-row">
              {HEAT_GLYPH.map((g, i) => (
                <span key={i} className="legend-cell" style={{ color: HEAT_COLOR[i] }}>{g}</span>
              ))}
              <span className="tiny" style={{ marginLeft: 4 }}>0 → 4</span>
            </div>
          </div>
        </div>
      </div>

      {/* 任务列表（叠在日历底部） */}
      <div className="cal-tasks">
        <div className="card-head" style={{ borderBottom: 'var(--border-fade)', borderTop: 'var(--border)' }}>
          <span className="card-title mono">今日任务 · TASKS</span>
          <span className="card-meta num mono">{tasks.filter(t => t.status !== 'todo').length} / {tasks.length}</span>
        </div>
        <div className="task-list">
          {tasks.map((t) => (
            <div key={t.id} className={`task-row task-${t.status}`}>
              <span className="task-mark">
                <svg viewBox="0 0 14 14" width="12" height="12">
                  <rect x="1" y="1" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1" />
                  {t.status === 'done' && <path d="M 3 7 L 6 10 L 11 4" fill="none" stroke="currentColor" strokeWidth="1.5" />}
                  {t.status === 'doing' && <rect x="3" y="6" width="3" height="3" fill="currentColor" />}
                </svg>
              </span>
              <span className="task-form" title={t.form}>{t.form}</span>
              <span className="task-title">{t.title}</span>
              <div className="task-bar">
                <div className="task-bar-fill" style={{ width: `${t.progress * 100}%` }} />
              </div>
              <span className="task-eta num mono">{t.eta}</span>
            </div>
          ))}
        </div>
      </div>

      <style>{`
        .cal-card {
          display: flex;
          flex-direction: column;
          background: var(--paper-card);
          border: var(--border);
          height: 100%;
          min-height: 0;
        }
        .cal-grid-wrap {
          flex: 1;
          min-height: 0;
          display: grid;
          grid-template-columns: 1fr 220px;
          gap: 0;
        }
        .cal-grid {
          padding: 10px;
          display: flex;
          flex-direction: column;
          gap: 2px;
          border-right: var(--border-fade);
          min-width: 0;
        }
        .cal-row {
          display: grid;
          grid-template-columns: repeat(7, 1fr);
          gap: 2px;
          flex: 1;
        }
        .cal-head-row {
          flex: 0 0 22px;
          border-bottom: var(--border-fade);
          margin-bottom: 4px;
        }
        .cal-day-head {
          font-size: 10px;
          color: var(--ink-mute);
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .cal-cell {
          position: relative;
          border: 1px solid transparent;
          background: var(--paper);
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 2px;
          cursor: crosshair;
          min-height: 32px;
        }
        .cal-cell:hover {
          border-color: var(--ink-soft);
        }
        .cal-cell.is-future { opacity: 0.55; }
        .cal-cell.is-today {
          border-color: var(--vermilion);
          background: rgba(200, 52, 28, 0.06);
        }
        .cal-day {
          font-size: 10px;
          color: var(--ink-mute);
        }
        .cal-heat {
          font-size: 14px;
          line-height: 1;
        }
        .cal-today-mark {
          position: absolute;
          top: 2px;
          right: 2px;
          width: 5px;
          height: 5px;
          background: var(--vermilion);
        }
        .cal-tip {
          position: absolute;
          bottom: calc(100% + 4px);
          left: 50%;
          transform: translateX(-50%);
          background: var(--ink);
          color: var(--paper);
          padding: 4px 8px;
          font-size: 10px;
          white-space: nowrap;
          z-index: 50;
          display: flex;
          gap: 8px;
        }
        .cal-side {
          display: flex;
          flex-direction: column;
          padding: 12px;
          gap: 14px;
        }
        .cal-stat-block .cal-big {
          font-size: 22px;
          font-weight: 500;
          margin-top: 4px;
          letter-spacing: 0.02em;
        }
        .cal-checkin {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 10px;
          border: 1.5px solid var(--ink);
          background: var(--paper);
          transition: all .15s;
          text-align: left;
        }
        .cal-checkin:hover {
          background: var(--ink);
          color: var(--paper);
        }
        .cal-checkin.is-checked {
          background: var(--vermilion);
          border-color: var(--vermilion);
          color: var(--paper);
        }
        .ci-text {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }
        .ci-text .mono { font-size: 12px; }
        .ci-text .num  { font-size: 10px; opacity: 0.75; }
        .cal-legend { padding-top: 4px; border-top: var(--border-fade); }
        .legend-row {
          display: flex;
          gap: 6px;
          align-items: center;
          font-size: 14px;
        }
        .cal-tasks {
          border-top: var(--border);
          background: var(--paper);
          flex: 0 0 auto;
          max-height: 200px;
          display: flex;
          flex-direction: column;
        }
        .task-list {
          padding: 4px 10px 10px;
          display: flex;
          flex-direction: column;
          gap: 4px;
          overflow-y: auto;
        }
        .task-row {
          display: grid;
          grid-template-columns: 18px 22px 1fr 120px 60px;
          align-items: center;
          gap: 8px;
          padding: 6px 4px;
          border-bottom: var(--border-fade);
          font-size: 12px;
        }
        .task-row:last-child { border-bottom: none; }
        .task-mark { color: var(--ink-mute); display: inline-flex; }
        .task-done .task-mark { color: var(--mint); }
        .task-doing .task-mark { color: var(--vermilion); }
        .task-done .task-title { text-decoration: line-through; color: var(--ink-mute); }
        .task-form { font-size: 13px; }
        .task-title { color: var(--ink); }
        .task-bar {
          height: 4px;
          background: var(--paper-deep);
          position: relative;
        }
        .task-bar-fill {
          position: absolute;
          inset: 0;
          background: var(--ink);
          height: 100%;
        }
        .task-doing .task-bar-fill { background: var(--vermilion); }
        .task-eta { font-size: 10px; color: var(--ink-mute); text-align: right; }
      `}</style>
    </div>
  );
}