import { useWorkspace } from '../store/useWorkspace';
import './Calendar.css';

const HEAT_GLYPH = ['·', '░', '▒', '▓', '█'];
const WEEK = ['日', '一', '二', '三', '四', '五', '六'];

export function Calendar() {
  const cal = useWorkspace((s) => s.calendar);

  return (
    <div className="cal">
      <div className="cal-head">
        <div className="h">七月 · 本月打卡</div>
        <div className="s">今天 {cal.today} 日</div>
      </div>
      <div className="cal-grid">
        <div className="cal-week">{WEEK.map((w) => <span key={w}>{w}</span>)}</div>
        {cal.rows.map((row, ri) => (
          <div key={ri} className="cal-row">
            {row.cells.map((c, ci) => (
              <div key={ci}
                   className={`cal-c h${c.intensity} ${c.day === cal.today ? 'today' : ''}`}
                   title={`${c.day} 日`}>
                <span className="d">{c.day}</span>
                <span className="h">{HEAT_GLYPH[c.intensity]}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
