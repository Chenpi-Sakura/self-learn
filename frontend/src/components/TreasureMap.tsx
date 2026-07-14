import { useEffect, useState, useCallback } from 'react';
import { getMapNodes } from '../api/map';
import { useSession } from '../store/session';
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
  // T13-fix: 后端 PlanAgent 写入的 status="active"（main 分支第一站）
  active:      '#FFFFFF',
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
  active:      '#1A1A1A',
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
  // T13-fix: edges 由 nodes 自动派生（按当前 y,x 顺序串成 main 主干），不再硬编码空数组
  const edges: { from: string; to: string; kind: string }[] = (() => {
    const sorted = [...nodes].sort((a, b) => (a.y - b.y) || (a.x - b.x));
    const out: { from: string; to: string; kind: string }[] = [];
    for (let i = 0; i < sorted.length - 1; i++) {
      out.push({ from: sorted[i].id, to: sorted[i + 1].id, kind: 'main' });
    }
    return out;
  })();
  const [generating, setGenerating] = useState(false);
  const [starting, setStarting] = useState<string | null>(null); // node.id being started
  const [msg, setMsg] = useState<string | null>(null);

  const loadNodes = useCallback(() => {
    if (!studentId) return;
    getMapNodes(studentId)
      .then((r) => setNodes(r.nodes.map(mapApiNode)))
      .catch(() => setNodes([]));
  }, [studentId]);

  useEffect(() => {
    loadNodes();
  }, [loadNodes]);

  const handleGenerate = async () => {
    if (!studentId || generating) return;
    setGenerating(true);
    setMsg('正在生成地图...');
    try {
      const res = await fetch('http://localhost:8000/api/map/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_id: studentId }),
      });
      const data = await res.json();
      setMsg(`已提交，2 秒后刷新`);
      setTimeout(() => {
        loadNodes();
        setMsg(null);
        setGenerating(false);
      }, 2500);
    } catch (e) {
      setMsg(`生成失败：${String(e)}`);
      setGenerating(false);
    }
  };

  const handleNodeClick = async (node: InternalNode) => {
    if (!studentId || starting) return;
    setStarting(node.id);
    setMsg(`启动 ${node.label}...`);
    try {
      // 调 DirectorAgent 生成关卡
      const res = await fetch('http://localhost:8000/api/level/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_id: studentId }),
      });
      const data = await res.json();
      setMsg(`${node.label} 已启动（trace: ${data.trace_id.slice(0, 8)}…），3 秒后加载`);
      // 等 Worker 处理完，再刷新节点（状态会变 in_progress）
      setTimeout(() => {
        loadNodes();
        setMsg(null);
        setStarting(null);
      }, 3500);
    } catch (e) {
      setMsg(`启动失败：${String(e)}`);
      setStarting(null);
    }
  };

  return (
    <div className="tm">
      <div className="tm-head">
        <div className="h">深度学习路径</div>
        <div className="s">{nodes.length} 站</div>
        <button
          onClick={handleGenerate}
          disabled={generating}
          style={{
            marginLeft: 'auto',
            padding: '4px 10px',
            fontSize: 12,
            background: generating ? '#ccc' : '#1B3B6F',
            color: '#fff',
            border: 'none',
            borderRadius: 4,
            cursor: generating ? 'not-allowed' : 'pointer',
          }}
        >
          {generating ? '生成中…' : '生成地图'}
        </button>
      </div>
      {msg && <p style={{ margin: '4px 0 0 16px', fontSize: 12, color: '#6B6B70' }}>{msg}</p>}
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
            <g
              key={n.id}
              className={`node-g${starting === n.id ? ' starting' : ''}`}
              transform={`translate(${n.x}, ${n.y})`}
              opacity={op}
              onClick={() => handleNodeClick(n)}
              style={{ cursor: starting ? 'wait' : 'pointer' }}
            >
              <rect className="node-rect" x="0" y="0" width="100" height="40" rx="6"
                    fill={fill} stroke={stroke}
                    strokeWidth={isKey || n.status === 'in_progress' ? 1.5 : 1}
                    strokeDasharray={strokeDash} />
              <text className="node-num" x="8" y="14" fill={txt}>{n.label}</text>
              <text className="node-lbl" x="50" y="30" textAnchor="middle" fill={txt}>
                {n.status === 'locked' ? '🔒' : n.status === 'completed' ? '✅' : starting === n.id ? '⏳' : '▶'}
              </text>
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
