import { useEffect, useState } from 'react';
import { buildProfile, getProfile } from '../api/profile';
import { subscribeProfileProgress } from '../api/sse';
import type { ProfileDimensions as ApiDim } from '../api/types';
import './ProfileRadar.css';

interface DimItem {
  key: string;
  label: string;
  value: number;
  pulsing?: boolean;
}

const SIZE = 180;
const R = 70;

const DIM_MAP: { key: keyof ApiDim; label: string }[] = [
  { key: 'kb', label: '知识基础' },
  { key: 'vp', label: '视觉偏好' },
  { key: 'as', label: '分析风格' },
  { key: 'ge', label: '求职目标' },
  { key: 'ept', label: '易错类型' },
  { key: 'fd', label: '专注时长' },
];

// 默认初始维度（6 个键全 0.5；重新生成时让 LLM 用这些作为基线）
const DEFAULT_DIMS: Record<string, number> = {
  kb: 0.5, vp: 0.5, as: 0.5, ge: 0.5, ept: 0.5, fd: 0.5,
};

function polar(i: number, total: number, value: number) {
  const angle = (Math.PI * 2 * i) / total - Math.PI / 2;
  const r = (R * value) / 100;
  return { x: Math.cos(angle) * r, y: Math.sin(angle) * r };
}

interface Props {
  studentId?: string;
}

type RebuildStatus = 'idle' | 'submitting' | 'running' | 'completed' | 'failed';

export function ProfileRadar({ studentId }: Props) {
  const [dims, setDims] = useState<DimItem[]>([]);
  const [studentLabel, setStudentLabel] = useState('加载中...');
  const [rebuildStatus, setRebuildStatus] = useState<RebuildStatus>('idle');
  const [rebuildMsg, setRebuildMsg] = useState<string>('');

  const loadProfile = (sid: string) => {
    getProfile(sid)
      .then((p) => {
        setStudentLabel(p.student_id);
        setDims(
          DIM_MAP.map((m) => ({
            key: m.key,
            label: m.label,
            value: Math.round(p.dimensions[m.key] * 100) / 100,
          }))
        );
      })
      .catch(() => {
        setStudentLabel('（加载失败）');
        setDims([]);
      });
  };

  useEffect(() => {
    if (!studentId) return;
    loadProfile(studentId);
  }, [studentId]);

  const handleRebuild = async () => {
    if (!studentId) return;
    setRebuildStatus('submitting');
    setRebuildMsg('提交...');
    try {
      const res = await buildProfile(studentId, DEFAULT_DIMS, ['manual-rebuild']);
      const traceId = res.trace_id;
      setRebuildStatus('running');
      setRebuildMsg(`trace=${traceId.slice(0, 8)}… 后端出题中`);
      const close = subscribeProfileProgress(traceId, (e) => {
        if (e.event === 'progress') {
          setRebuildMsg(`进行中：${(e.data as { stage?: string }).stage ?? '…'}`);
        } else if (e.event === 'completed') {
          setRebuildStatus('completed');
          setRebuildMsg('完成！刷新中...');
          close();
          // 1 秒后重新拉画像（让 LLM 生成已落库）
          setTimeout(() => loadProfile(studentId), 1000);
          setTimeout(() => {
            setRebuildStatus('idle');
            setRebuildMsg('');
          }, 4000);
        } else if (e.event === 'error') {
          setRebuildStatus('failed');
          setRebuildMsg('失败');
          close();
        }
      });
    } catch (e) {
      setRebuildStatus('failed');
      setRebuildMsg(`提交失败：${String(e)}`);
    }
  };

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
        <div className="h">{studentLabel} · 六维画像</div>
        <div className="s">最近 30 天 · 综合</div>
        <button
          className="pr-rebuild"
          onClick={handleRebuild}
          disabled={!studentId || rebuildStatus === 'submitting' || rebuildStatus === 'running'}
          style={{
            marginLeft: 'auto',
            padding: '4px 10px',
            fontSize: 12,
            background:
              rebuildStatus === 'running' || rebuildStatus === 'submitting'
                ? '#ccc'
                : rebuildStatus === 'failed'
                  ? '#BC4749'
                  : '#1B3B6F',
            color: '#fff',
            border: 'none',
            borderRadius: 4,
            cursor:
              rebuildStatus === 'submitting' || rebuildStatus === 'running'
                ? 'wait'
                : 'pointer',
          }}
        >
          {rebuildStatus === 'idle' && '重新生成'}
          {rebuildStatus === 'submitting' && '提交中…'}
          {rebuildStatus === 'running' && '生成中…'}
          {rebuildStatus === 'completed' && '✓ 已完成'}
          {rebuildStatus === 'failed' && '✗ 重试'}
        </button>
      </div>
      {rebuildMsg && (
        <div style={{ fontSize: 11, color: '#6B6B70', padding: '4px 0', marginLeft: 0 }}>
          {rebuildMsg}
        </div>
      )}
      {dims.length === 0 ? (
        <div style={{ padding: 20, color: '#6B6B70' }}>暂无画像数据</div>
      ) : (
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
      )}
    </div>
  );
}
