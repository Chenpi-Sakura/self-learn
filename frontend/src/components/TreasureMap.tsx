import { useEffect, useState } from 'react';
import { getMapNodes } from '../api/map';
import type { MapNode as ApiMapNode } from '../api/types';
import './TreasureMap.css';

interface InternalNode {
  id: string;
  x: number;
  y: number;
  label: string;
  status: string;
  minutes: number;
  visual?: { badge?: 'key' | null };
  branchStatus?: string;
}

const STATUS_FILL: Record<string, string> = {
  completed:   '#F4F4F0',
  in_progress: '#DBEAFE',
  unlocked:    '#FFFFFF',
  locked:      '#F4F4F0',
  mastered:    '#D1FAE5',
  current:     '#1B3B6F',
  key:         '#BC4749',
  interest:    '#FFFFFF',
  sleeping:    'transparent',
};
const STATUS_TEXT: Record<string, string> = {
  completed:   '#1A1A1A',
  in_progress: '#1A1A1A',
  unlocked:    '#1A1A1A',
  locked:      '#A1A1AA',
  mastered:    '#1A1A1A',
  current:     '#FFFFFF',
  key:         '#FFFFFF',
  interest:    '#1B3B6F',
  sleeping:    '#A1A1AA',
};

function mapApiNode(n: ApiMapNode): InternalNode {
  return {
    id: n.node_id,
    x: n.position.x,
    y: n.position.y,
    label: n.title,
    status: n.status,
    minutes: 0,
  };
}

interface Props {
  studentId?: string;
}

export function TreasureMap({ studentId }: Props) {
  const [nodes, setNodes] = useState<InternalNode[]>([]);
  const [edges] = useState<{ from: string; to: string; kind: string }[]>([]);

  useEffect(() => {
    if (!studentId) return;
    getMapNodes(studentId)
      .then((r) => setNodes(r.nodes.map(mapApiNode)))
      .catch(() => setNodes([]));
  }, [studentId]);

  return (
    <div className="tm">
      <div className="tm-head">
        <div className="h">深度学习路径</div>
        <div className="s">{nodes.length} 站</div>
      </div>
      <svg className="tm-svg" viewBox="0 0 760 240" preserveAspectRatio="xMidYMid meet">
        {edges.map((e, i) => {
          const a = nodes.find((n) => n.id === e.from);
          const b = nodes.find((n) => n.id === e.to);
          if (!a || !b) return null;
          const dash = e.kind === 'interest' ? '5 4' : e.kind === 'sleeping' ? '2 4' : '';
          const stroke = e.kind === 'interest' ? 'var(--indigo)' :
            e.kind === 'sleeping' ? 'var(--mute)' : 'var(--ink)';
          const op = e.kind === 'sleeping' ? 0.4 : e.kind === 'interest' ? 0.5 : 0.7;
          return (
            <line key={i} x1={a.x + 50} y1={a.y + 20} x2={b.x + 50} y2={b.y + 20}
                  stroke={stroke} strokeWidth={e.kind === 'main' ? 1.5 : 1}
                  strokeDasharray={dash} opacity={op} />
          );
        })}
        {nodes.map((n) => {
          const fill = STATUS_FILL[n.status];
          const txt = STATUS_TEXT[n.status];
          const isKey = n.visual?.badge === 'key';
          const stroke = isKey ? 'var(--vermilion)' :
            n.branchStatus === 'sleeping' ? 'var(--mute)' :
            n.status === 'unlocked' ? 'var(--indigo)' :
            n.status === 'in_progress' ? 'var(--indigo)' : 'var(--border)';
          const strokeDash = n.branchStatus === 'sleeping' ? '3 3' : n.branchStatus === 'active' ? '4 3' : '';
          const op = n.branchStatus === 'sleeping' ? 0.55 : 1;
          return (
            <g key={n.id} className="node-g" transform={`translate(${n.x}, ${n.y})`} opacity={op}>
              <rect className="node-rect" x="0" y="0" width="100" height="40" rx="6"
                    fill={fill} stroke={stroke}
                    strokeWidth={isKey || n.status === 'in_progress' ? 1.5 : 1}
                    strokeDasharray={strokeDash} />
              <text className="node-num" x="8" y="14" fill={txt}>№{n.id.slice(1)} · {n.minutes}min</text>
              <text className="node-lbl" x="50" y="30" textAnchor="middle" fill={txt}>{n.label}</text>
              {n.status === 'in_progress' && (
                <circle cx="100" cy="0" r="6" fill="var(--indigo)">
                  <animate attributeName="r" values="4;9;4" dur="2s" repeatCount="indefinite" />
                  <animate attributeName="opacity" values="0.6;0;0.6" dur="2s" repeatCount="indefinite" />
                </circle>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
