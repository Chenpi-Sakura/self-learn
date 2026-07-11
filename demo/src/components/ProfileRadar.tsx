import { useEffect, useState } from 'react';
import { profile } from '../data/sample';

const SIZE = 220;
const CX = SIZE / 2;
const CY = SIZE / 2;
const R = 78;

/** 6 维雷达图：SVG polygon + 顶点数显 */
export function ProfileRadar() {
  // 加载动画：从 0 增长到目标值
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    let raf: number;
    const start = performance.now();
    const dur = 900;
    const tick = (t: number) => {
      const k = Math.min(1, (t - start) / dur);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - k, 3);
      setProgress(eased);
      if (k < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  // "迁移"维度每 4s 在 73-76 之间脉动
  const [pulseTick, setPulseTick] = useState(0);
  useEffect(() => {
    const id = window.setInterval(() => setPulseTick((t) => t + 1), 80);
    return () => window.clearInterval(id);
  }, []);
  const pulseOffset = profile.find((p) => p.pulsing)
    ? Math.sin((pulseTick / 80) * Math.PI * 0.6) * 0.018
    : 0;

  // 计算顶点（angle 从 12 点钟方向开始，顺时针）
  const angleAt = (i: number) => -Math.PI / 2 + (i * 2 * Math.PI) / profile.length;
  const pointAt = (i: number, value: number) => {
    const a = angleAt(i);
    return {
      x: CX + Math.cos(a) * R * value,
      y: CY + Math.sin(a) * R * value,
    };
  };

  const points = profile.map((p, i) => {
    const v = p.pulsing ? p.value + pulseOffset : p.value;
    return { ...pointAt(i, Math.min(1, v * progress)), label: p.label, value: p.value, key: p.key, pulsing: p.pulsing };
  });
  const polygon = points.map((p) => `${p.x},${p.y}`).join(' ');

  // 网格层（5 圈）
  const gridLevels = [0.25, 0.5, 0.75, 1];

  return (
    <div className="radar-card">
      <div className="card-head">
        <span className="card-title mono">学习画像 · PROFILE</span>
        <span className="card-meta num mono">v3.2 · 2min ago</span>
      </div>

      <div className="radar-body">
        <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="radar-svg">
          {/* 网格圈 */}
          {gridLevels.map((lv) => {
            const pts = profile.map((_, i) => {
              const p = pointAt(i, lv);
              return `${p.x},${p.y}`;
            }).join(' ');
            return (
              <polygon
                key={lv}
                points={pts}
                fill="none"
                stroke="var(--ink-soft)"
                strokeOpacity={0.18}
                strokeWidth={0.6}
                strokeDasharray={lv === 1 ? undefined : '2 3'}
              />
            );
          })}

          {/* 6 条轴 */}
          {profile.map((_, i) => {
            const a = angleAt(i);
            return (
              <line
                key={`ax-${i}`}
                x1={CX}
                y1={CY}
                x2={CX + Math.cos(a) * R}
                y2={CY + Math.sin(a) * R}
                stroke="var(--ink-soft)"
                strokeOpacity={0.18}
                strokeWidth={0.6}
              />
            );
          })}

          {/* 数据多边形 */}
          <polygon
            points={polygon}
            fill="var(--vermilion)"
            fillOpacity={0.12}
            stroke="var(--vermilion)"
            strokeWidth={1.2}
          />

          {/* 顶点 */}
          {points.map((p, i) => (
            <g key={p.key}>
              <circle cx={p.x} cy={p.y} r={2.5} fill="var(--vermilion)" />
              {p.pulsing && (
                <circle cx={p.x} cy={p.y} r={6} fill="none" stroke="var(--vermilion)" strokeWidth={0.8} className="pulse" />
              )}
            </g>
          ))}

          {/* 维度标签 */}
          {profile.map((p, i) => {
            const a = angleAt(i);
            const lr = R + 18;
            const x = CX + Math.cos(a) * lr;
            const y = CY + Math.sin(a) * lr;
            const anchor = Math.cos(a) > 0.3 ? 'start' : Math.cos(a) < -0.3 ? 'end' : 'middle';
            return (
              <g key={`lb-${p.key}`}>
                <text
                  x={x}
                  y={y - 2}
                  textAnchor={anchor}
                  fontFamily="var(--font-mono)"
                  fontSize={10}
                  fill={p.pulsing ? 'var(--vermilion)' : 'var(--ink)'}
                  style={{ letterSpacing: '0.06em' }}
                >
                  {p.label}
                </text>
                <text
                  x={x}
                  y={y + 10}
                  textAnchor={anchor}
                  fontFamily="var(--font-num)"
                  fontSize={9}
                  fill="var(--ink-mute)"
                >
                  {Math.round(p.value * 100)}
                </text>
              </g>
            );
          })}

          {/* 中心十字 */}
          <line x1={CX - 4} y1={CY} x2={CX + 4} y2={CY} stroke="var(--ink-mute)" strokeWidth={0.6} />
          <line x1={CX} y1={CY - 4} x2={CX} y2={CY + 4} stroke="var(--ink-mute)" strokeWidth={0.6} />
        </svg>

        <div className="radar-side">
          <div className="rs-row">
            <span className="tiny">迁移</span>
            <span className="num mono rs-val">+12%</span>
          </div>
          <div className="rs-row">
            <span className="tiny">推理</span>
            <span className="num mono rs-val" style={{ color: 'var(--faded)' }}>—</span>
          </div>
          <div className="rs-row">
            <span className="tiny">应用</span>
            <span className="num mono rs-val" style={{ color: 'var(--faded)' }}>—</span>
          </div>
          <div className="rs-sep" />
          <div className="rs-row">
            <span className="tiny">Σ</span>
            <span className="num mono rs-val">4h 32m</span>
          </div>
          <div className="rs-row">
            <span className="tiny">×</span>
            <span className="num mono rs-val">32d</span>
          </div>
        </div>
      </div>

      <style>{`
        .radar-card {
          display: flex;
          flex-direction: column;
          background: var(--paper-card);
          border: var(--border);
          height: 100%;
          min-height: 0;
        }
        .radar-body {
          flex: 1;
          min-height: 0;
          display: grid;
          grid-template-columns: 1fr 70px;
          align-items: center;
          padding: 6px;
        }
        .radar-svg {
          width: 100%;
          height: 100%;
          max-height: 200px;
        }
        .radar-side {
          display: flex;
          flex-direction: column;
          gap: 6px;
          padding: 6px 4px 6px 0;
          border-left: var(--border-fade);
          padding-left: 8px;
        }
        .rs-row {
          display: flex;
          justify-content: space-between;
          gap: 6px;
          font-size: 10px;
        }
        .rs-val { font-size: 11px; color: var(--ink); }
        .rs-sep {
          height: 1px;
          background: var(--border-fade);
          margin: 2px 0;
        }
      `}</style>
    </div>
  );
}