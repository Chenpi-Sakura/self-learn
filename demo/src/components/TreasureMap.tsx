import { useRef, useState, useCallback, useMemo } from 'react';
import { useWorkspace } from '../store/useWorkspace';
import { mapEdges } from '../data/sample';
import type { MapNode, NodeKind } from '../data/sample';

const NODE_R = 18;

/** 罗盘式节点：圆 + 十字 + 中心点 */
function CompassNode({
  n,
  hovered,
  selected,
  onPointerDown,
  onPointerEnter,
  onPointerLeave,
}: {
  n: MapNode;
  hovered: boolean;
  selected: boolean;
  onPointerDown: (e: React.PointerEvent) => void;
  onPointerEnter: () => void;
  onPointerLeave: () => void;
}) {
  const isDormant = n.kind === 'dormant';
  const isDone = n.kind === 'done';
  const isCurrent = n.kind === 'current';
  const isKey = n.kind === 'key';
  const isLocked = n.kind === 'locked';

  const ringColor = isKey ? 'var(--vermilion)' : 'var(--ink)';
  const fill = isDormant ? 'transparent' : isDone ? 'var(--mint-soft)' : isCurrent ? 'var(--paper-deep)' : 'var(--paper-card)';
  const strokeDash = isDormant ? '2 2' : undefined;
  const opacity = isDormant ? 0.55 : isLocked ? 0.5 : 1;

  const showHover = hovered || selected;

  return (
    <g
      transform={`translate(${n.x}, ${n.y})`}
      opacity={opacity}
      onPointerDown={onPointerDown}
      onPointerEnter={onPointerEnter}
      onPointerLeave={onPointerLeave}
      style={{ cursor: 'grab', touchAction: 'none' }}
    >
      {/* hover 外晕 */}
      {showHover && !isDormant && (
        <circle r={NODE_R + 8} fill="none" stroke="var(--vermilion)" strokeWidth={0.8} strokeDasharray="2 3" opacity={0.6} />
      )}

      {/* 主圆 */}
      <circle
        r={showHover ? NODE_R + 1.5 : NODE_R}
        fill={fill}
        stroke={showHover ? 'var(--vermilion)' : ringColor}
        strokeWidth={isKey ? 1.6 : 1}
        strokeDasharray={strokeDash}
        className={isCurrent ? 'pulse' : ''}
      />

      {/* 十字刻度（罗盘标记） */}
      <line x1={-NODE_R} y1={0} x2={-NODE_R - 4} y2={0} stroke={ringColor} strokeWidth={1} />
      <line x1={NODE_R} y1={0} x2={NODE_R + 4} y2={0} stroke={ringColor} strokeWidth={1} />
      <line x1={0} y1={-NODE_R} x2={0} y2={-NODE_R - 4} stroke={ringColor} strokeWidth={1} />
      <line x1={0} y1={NODE_R} x2={0} y2={NODE_R + 4} stroke={ringColor} strokeWidth={1} />

      {/* 中心点 */}
      {isKey ? (
        <circle r={3.5} fill="var(--vermilion)" />
      ) : isDone ? (
        <path d="M -4 0 L -1 3 L 4 -3" fill="none" stroke="var(--mint)" strokeWidth={1.5} />
      ) : isLocked ? (
        <rect x={-2} y={-3} width={4} height={5} fill="var(--faded)" />
      ) : isDormant ? (
        <text textAnchor="middle" y={3} fontSize={10} fill="var(--faded)">z</text>
      ) : (
        <circle r={2} fill={ringColor} />
      )}

      {/* 关卡编号 / 形式徽章 */}
      {n.no && (
        <text
          x={NODE_R + 8}
          y={-NODE_R + 2}
          fontFamily="var(--font-mono)"
          fontSize={9}
          fill="var(--ink-mute)"
          style={{ letterSpacing: '0.08em' }}
        >
          {n.no}
        </text>
      )}

      {/* 标签 */}
      <text
        x={0}
        y={NODE_R + 14}
        textAnchor="middle"
        fontFamily="var(--font-mono)"
        fontSize={11}
        fill={isDormant ? 'var(--faded)' : 'var(--ink)'}
        style={{ letterSpacing: '0.04em' }}
      >
        {n.label}
      </text>

      {/* 形式徽章 */}
      {n.form && (
        <text
          x={-NODE_R - 8}
          y={-NODE_R + 2}
          textAnchor="end"
          fontSize={9}
          fill={isKey ? 'var(--vermilion)' : 'var(--ink-mute)'}
        >
          {n.form}
        </text>
      )}
    </g>
  );
}

interface DragState {
  nodeId: string;
  startX: number;       // 屏幕 px
  startY: number;
  origX: number;        // SVG 坐标
  origY: number;
  moved: boolean;
  holdTimer: number | null;
}

export function TreasureMap() {
  const nodes = useWorkspace((s) => s.nodes);
  const moveNode = useWorkspace((s) => s.moveNode);
  const hoverNode = useWorkspace((s) => s.hoverNode);
  const selectNode = useWorkspace((s) => s.selectNode);
  const hovered = useWorkspace((s) => s.hoveredNode);
  const selected = useWorkspace((s) => s.selectedNode);

  const svgRef = useRef<SVGSVGElement>(null);
  const dragRef = useRef<DragState | null>(null);
  const [activeDragId, setActiveDragId] = useState<string | null>(null);

  // 边：实际渲染时根据当前 nodes 位置计算
  const edgePaths = useMemo(() => {
    const byId = new Map(nodes.map((n) => [n.id, n]));
    return mapEdges
      .map(([a, b]) => {
        const A = byId.get(a), B = byId.get(b);
        if (!A || !B) return null;
        const dormant = A.kind === 'dormant' || B.kind === 'dormant';
        return {
          d: `M ${A.x} ${A.y} L ${B.x} ${B.y}`,
          dormant,
          key: `${a}-${b}`,
        };
      })
      .filter(Boolean) as Array<{ d: string; dormant: boolean; key: string }>;
  }, [nodes]);

  const screenToSvg = useCallback((clientX: number, clientY: number) => {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0 };
    const pt = svg.createSVGPoint();
    pt.x = clientX;
    pt.y = clientY;
    const ctm = svg.getScreenCTM();
    if (!ctm) return { x: 0, y: 0 };
    const p = pt.matrixTransform(ctm.inverse());
    return { x: p.x, y: p.y };
  }, []);

  const onPointerDownNode = useCallback(
    (n: MapNode, e: React.PointerEvent) => {
      e.preventDefault();
      (e.target as Element).setPointerCapture?.(e.pointerId);
      const timer = window.setTimeout(() => {
        setActiveDragId(n.id);
      }, 500);
      dragRef.current = {
        nodeId: n.id,
        startX: e.clientX,
        startY: e.clientY,
        origX: n.x,
        origY: n.y,
        moved: false,
        holdTimer: timer,
      };
    },
    [],
  );

  const onPointerMove = useCallback(
    (e: React.PointerEvent) => {
      const d = dragRef.current;
      if (!d) return;
      if (!activeDragId) {
        // 还没进入可拖拽状态时：若移动超过 4px 视为取消长按（保持为 click）
        if (Math.hypot(e.clientX - d.startX, e.clientY - d.startY) > 4) {
          if (d.holdTimer) window.clearTimeout(d.holdTimer);
          dragRef.current = null;
        }
        return;
      }
      d.moved = true;
      const p = screenToSvg(e.clientX, e.clientY);
      const dx = p.x - screenToSvg(d.startX, d.startY).x;
      const dy = p.y - screenToSvg(d.startX, d.startY).y;
      const nx = Math.max(20, Math.min(980, d.origX + dx));
      const ny = Math.max(20, Math.min(560, d.origY + dy));
      moveNode(d.nodeId, nx, ny);
    },
    [activeDragId, moveNode, screenToSvg],
  );

  const onPointerUp = useCallback(() => {
    const d = dragRef.current;
    if (!d) return;
    if (d.holdTimer) window.clearTimeout(d.holdTimer);
    if (!d.moved && !activeDragId) {
      // 视为单击：选中
      selectNode(d.nodeId);
    } else {
      selectNode(d.nodeId);
    }
    dragRef.current = null;
    setActiveDragId(null);
  }, [activeDragId, selectNode]);

  const dormantCount = nodes.filter((n) => n.kind === 'dormant').length;

  return (
    <div className="treasure-card">
      <div className="card-head">
        <span className="card-title mono">藏宝图 · LEARNING MAP</span>
        <span className="card-meta num mono">
          {String(nodes.length).padStart(2, '0')} 关卡
          <span style={{ margin: '0 6px', color: 'var(--faded)' }}>·</span>
          {dormantCount} 休眠
        </span>
        <button className="card-act" title="收起">⤢</button>
      </div>

      <div className="map-wrap">
        <svg
          ref={svgRef}
          viewBox="0 0 1000 580"
          preserveAspectRatio="xMidYMid meet"
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerLeave={onPointerUp}
          style={{ width: '100%', height: '100%', display: 'block' }}
        >
          {/* 刻度网格（蓝图感） */}
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(26,26,24,0.08)" strokeWidth="0.5" />
            </pattern>
            <pattern id="grid-major" width="200" height="200" patternUnits="userSpaceOnUse">
              <path d="M 200 0 L 0 0 0 200" fill="none" stroke="rgba(26,26,24,0.18)" strokeWidth="0.8" />
            </pattern>
          </defs>
          <rect width="1000" height="580" fill="url(#grid)" />
          <rect width="1000" height="580" fill="url(#grid-major)" />

          {/* 边框刻度 */}
          {[0, 200, 400, 600, 800, 1000].map((x) => (
            <g key={`tx-${x}`}>
              <line x1={x} y1={0} x2={x} y2={6} stroke="var(--ink-soft)" strokeWidth={0.8} />
              <text x={x + 2} y={14} fontFamily="var(--font-mono)" fontSize={8} fill="var(--faded)">{x}</text>
            </g>
          ))}
          {[0, 100, 200, 300, 400, 500].map((y) => (
            <g key={`ty-${y}`}>
              <line x1={0} y1={y} x2={6} y2={y} stroke="var(--ink-soft)" strokeWidth={0.8} />
              <text x={8} y={y - 2} fontFamily="var(--font-mono)" fontSize={8} fill="var(--faded)">{y}</text>
            </g>
          ))}

          {/* 边 */}
          {edgePaths.map((e) => (
            <path
              key={e.key}
              d={e.d}
              stroke={e.dormant ? 'var(--faded)' : 'var(--ink-soft)'}
              strokeWidth={e.dormant ? 0.8 : 1}
              strokeDasharray={e.dormant ? '3 3' : undefined}
              fill="none"
              opacity={e.dormant ? 0.6 : 1}
            />
          ))}

          {/* 节点 */}
          {nodes.map((n) => (
            <CompassNode
              key={n.id}
              n={n}
              hovered={hovered === n.id}
              selected={selected === n.id}
              onPointerDown={(e) => onPointerDownNode(n, e)}
              onPointerEnter={() => hoverNode(n.id)}
              onPointerLeave={() => hoverNode(null)}
            />
          ))}
        </svg>
      </div>

      <div className="card-foot">
        <span className="tiny">长按节点 ≥0.5s 可拖动 ·  Ctrl 多选 ·  右键菜单</span>
        <span className="tiny num" style={{ color: 'var(--ink-mute)' }}>
          {activeDragId ? '◉ DRAGGING' : '○ IDLE'}
        </span>
      </div>

      <style>{`
        .treasure-card {
          display: flex;
          flex-direction: column;
          background: var(--paper-card);
          border: var(--border);
          height: 100%;
          min-height: 0;
        }
        .card-head {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 8px 10px;
          border-bottom: var(--border-fade);
          background: var(--paper-deep);
        }
        .card-title {
          font-size: 11px;
          letter-spacing: 0.16em;
          color: var(--ink);
        }
        .card-meta {
          margin-left: auto;
          font-size: 10px;
          color: var(--ink-mute);
          letter-spacing: 0.08em;
        }
        .card-act {
          font-size: 13px;
          color: var(--ink-mute);
          padding: 0 4px;
        }
        .card-act:hover { color: var(--vermilion); }
        .map-wrap {
          flex: 1;
          min-height: 0;
          padding: 8px;
          background: var(--paper);
          position: relative;
        }
        .card-foot {
          display: flex;
          justify-content: space-between;
          padding: 6px 10px;
          border-top: var(--border-fade);
          background: var(--paper-deep);
        }
      `}</style>
    </div>
  );
}