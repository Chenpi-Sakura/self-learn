import { useWorkspace } from '../store/useWorkspace';
import './ProfileRadar.css';

const SIZE = 180;
const R = 70;

function polar(i: number, total: number, value: number) {
  const angle = (Math.PI * 2 * i) / total - Math.PI / 2;
  const r = (R * value) / 100;
  return { x: Math.cos(angle) * r, y: Math.sin(angle) * r };
}

export function ProfileRadar() {
  const profile = useWorkspace((s) => s.profile);
  const dims = profile.dimensions;
  const total = dims.length;

  const points = dims
    .map((d, i) => {
      const p = polar(i, total, d.value);
      return `${p.x.toFixed(1)},${p.y.toFixed(1)}`;
    })
    .join(' ');

  return (
    <div className="pr">
      <div className="pr-head">
        <div className="h">{profile.student} · 六维画像</div>
        <div className="s">最近 30 天 · 综合</div>
      </div>
      <div className="pr-body">
        <svg className="pr-svg" viewBox={`${-SIZE/2} ${-SIZE/2} ${SIZE} ${SIZE}`}>
          {[0.25, 0.5, 0.75, 1].map((s, i) => (
            <circle key={i} cx="0" cy="0" r={R * s} fill="none" stroke="var(--border)" strokeWidth="0.8" />
          ))}
          {dims.map((_, i) => {
            const a = (Math.PI * 2 * i) / total - Math.PI / 2;
            return (
              <line key={i} x1="0" y1="0"
                    x2={Math.cos(a) * R} y2={Math.sin(a) * R}
                    stroke="var(--border)" strokeWidth="0.6" />
            );
          })}
          <polygon points={points} fill="var(--indigo)" fillOpacity="0.18"
                   stroke="var(--indigo)" strokeWidth="1.5" />
          {dims.map((d, i) => {
            const p = polar(i, total, d.value);
            return <circle key={d.key} cx={p.x} cy={p.y} r="3" fill="var(--indigo)" />;
          })}
          {dims.map((d, i) => {
            const a = (Math.PI * 2 * i) / total - Math.PI / 2;
            const lx = Math.cos(a) * (R + 14);
            const ly = Math.sin(a) * (R + 14);
            return (
              <text key={d.key} x={lx} y={ly} textAnchor="middle"
                    dominantBaseline="middle" fontSize="10" fill="var(--mute)">{d.label}</text>
            );
          })}
        </svg>
        <div className="pr-list">
          {dims.map((d) => (
            <div key={d.key} className={`pr-row ${d.pulsing ? 'pulse' : ''}`}>
              <span className="lb">{d.label}</span>
              <span className="bar" style={{ ['--w' as string]: `${d.value}%` }} />
              <span className="v">{d.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
