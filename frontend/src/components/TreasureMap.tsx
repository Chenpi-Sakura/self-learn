import { useEffect, useState, useCallback } from 'react';
import { getMapNodes } from '../api/map';
import { useWorkspace } from '../store/useWorkspace';
import { useSession } from '../store/session';
import { useLevel } from '../store/levelStore';
import type { MapNode as ApiMapNode } from '../api/types';
import { LevelStartProgress } from './LevelStartProgress';
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
  // 浅米色 + indigo 边让"可点击"和 locked (#F4F4F0) 区分开
  active:      '#FFF8E7',
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

// extract_topics 写入的 position 是网格坐标 col/row (1 cell = 1 unit),
// TreasureMap viewBox 760x240 期望每节点宽 100 + 间距 60, 这里按 160 缩放
// 让 4 节点横排时 [0,1,2,3] → [0,160,320,480] 落在 760 viewBox 内
const POSITION_SCALE = 160;

function mapApiNode(n: ApiMapNode): InternalNode {
  return {
    id: n.node_id,
    x: n.position.x * POSITION_SCALE,
    y: n.position.y * POSITION_SCALE,
    label: n.title,
    status: n.status,
    minutes: 0,
  };
}

interface Props {
  studentId?: string;
}

export function TreasureMap({ studentId }: Props) {
  const openWindow = useWorkspace((s) => s.openWindow);
  const [nodes, setNodes] = useState<InternalNode[]>([]);
  const setActiveLevel = useLevel((s) => s.setActive);
  // T13-fix: edges 由 nodes 自动派生（按当前 y,x 顺序串成 main 主干），不再硬编码空数组
  const edges: { from: string; to: string; kind: string }[] = (() => {
    const sorted = [...nodes].sort((a, b) => (a.y - b.y) || (a.x - b.x));
    const out: { from: string; to: string; kind: string }[] = [];
    for (let i = 0; i < sorted.length - 1; i++) {
      out.push({ from: sorted[i].id, to: sorted[i + 1].id, kind: 'main' });
    }
    return out;
  })();
  const [starting, setStarting] = useState<string | null>(null); // node.id being started
  const [msg, setMsg] = useState<string | null>(null);
  // 关卡启动进度条：reused=false 时显示等 SSE，reused=true 直接关掉
  const [pendingLevel, setPendingLevel] = useState<{ levelId: string; traceId: string; label: string } | null>(null);

  const loadNodes = useCallback(() => {
    if (!studentId) return;
    getMapNodes(studentId)
      .then((r) => setNodes(r.nodes.map(mapApiNode)))
      .catch(() => setNodes([]));
  }, [studentId]);

  useEffect(() => {
    loadNodes();
    // 监听 ResourceLibrary 完成提炼后的全局事件，刷新地图
    const onRefresh = () => loadNodes();
    window.addEventListener('selflearn:refresh-map', onRefresh);
    return () => window.removeEventListener('selflearn:refresh-map', onRefresh);
  }, [loadNodes]);

  // Q2 fix: "生成地图" 不再直接 POST /api/map/generate（那是 demo 路径，
  // 不接 md 资源），而是 **打开 ResourceLibrary** 让用户先勾选资源再走
  // ResourceLibrary → ExtractTopicsDialog → 真正触发提炼。
  const handleOpenResourceLibrary = () => {
    openWindow('resource_library');
    setMsg(null);
  };

  const handleNodeClick = async (node: InternalNode) => {
    if (!studentId || starting) return;
    setStarting(node.id);
    setMsg(`启动 ${node.label}...`);
    try {
      // 调 DirectorAgent 生成关卡（后端幂等：复用 in-flight 关卡则不调 LLM）
      const res = await fetch('http://localhost:8000/api/level/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_id: studentId, node_id: node.id }),
      });
      const data = (await res.json()) as {
        level_id?: string;
        trace_id?: string;
        reused?: boolean;
      };
      if (data.level_id) {
        // 立即把 levelId 推入 store，LecturePane/ExercisePane 就能拉题
        setActiveLevel(data.level_id, node.id, data.trace_id);
        setMsg(
          `${node.label} ${data.reused ? '已就绪（复用）' : '已启动'}（${data.level_id.slice(0, 8)}…）`
        );
        if (data.reused) {
          // 已就绪的关卡不需要进度条，直接清 starting
          setStarting(null);
          setMsg(null);
        } else if (data.trace_id) {
          // 等待 director chain 跑完，打开进度浮层
          setPendingLevel({ levelId: data.level_id, traceId: data.trace_id, label: node.label });
        }
      } else if (data.trace_id) {
        // 后端走 async dispatch（envelope 入队），没有 level_id 立即返回
        // 但 progress_consume SSE 还是 trace_id 维度, 借用一个占位 levelId 等 onDone
        setPendingLevel({ levelId: 'pending', traceId: data.trace_id, label: node.label });
        setMsg(`启动中：trace=${data.trace_id.slice(0, 8)}…`);
      }
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
          onClick={handleOpenResourceLibrary}
          style={{
            marginLeft: 'auto',
            padding: '4px 10px',
            fontSize: 12,
            background: '#1B3B6F',
            color: '#fff',
            border: 'none',
            borderRadius: 4,
            cursor: 'pointer',
          }}
        >
          生成地图
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
            n.status === 'in_progress' ? 'var(--indigo)' :
            n.status === 'active' ? 'var(--indigo)' : 'var(--border)';
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
      {pendingLevel && (
        <LevelStartProgress
          levelId={pendingLevel.levelId}
          traceId={pendingLevel.traceId}
          onDone={() => {
            // SSE completed: 关卡生成完, 重新拉地图刷新状态
            loadNodes();
            setPendingLevel(null);
            setStarting(null);
            setMsg(`${pendingLevel.label} 已就绪`);
          }}
          onClose={() => {
            setPendingLevel(null);
            setStarting(null);
          }}
        />
      )}
    </div>
  );
}
