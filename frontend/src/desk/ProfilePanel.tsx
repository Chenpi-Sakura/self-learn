import { useEffect, useState } from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer } from 'recharts';
import { useProfile } from '../store/profile';
import { useSession } from '../store/session';
import { getProfileHistory } from '../api/profile';
import type { ProfileDimensions } from '../api/types';

const LABELS: readonly string[] = ['知识基础', '视觉偏好', '分析风格', '求职目标', '易错类型', '专注时长'];

/** 6 维顺序必须与 ProfileDimensions 字段顺序一致（kb vp as ge ept fd）。 */
const KEYS: readonly (keyof ProfileDimensions)[] = ['kb', 'vp', 'as', 'ge', 'ept', 'fd'];

export function ProfilePanel() {
  const dims = useProfile((s) => s.dimensions);
  const sid = useSession((s) => s.studentId);
  const [history, setHistory] = useState<{ kb: number }[]>([]);

  useEffect(() => {
    if (!dims) return;
    getProfileHistory(sid, 10)
      .then((r) => setHistory(r.snapshots.map((s) => ({ kb: s.profile.kb ?? 0.5 }))))
      .catch(() => setHistory([]));
  }, [sid, dims]);

  if (!dims) {
    return <div style={{ padding: 16, fontFamily: 'HedvigLettersSerif, serif' }}>加载画像...</div>;
  }

  const data = LABELS.map((label, i) => ({ label, value: dims[KEYS[i]] ?? 0.5 }));

  return (
    <div style={{ padding: 12, background: '#fff', borderRadius: 8, height: '100%', overflow: 'auto' }}>
      <h3 style={{ fontFamily: 'HedvigLettersSerif, serif', color: '#1B3B6F', margin: '0 0 8px 0' }}>六维画像</h3>
      <ResponsiveContainer width="100%" height={250}>
        <RadarChart data={data}>
          <PolarGrid stroke="#E4E4E0" />
          <PolarAngleAxis dataKey="label" tick={{ fill: '#1A1A1A', fontFamily: 'HedvigLettersSerif' }} />
          <Radar name="profile" dataKey="value" stroke="#1B3B6F" fill="#1B3B6F" fillOpacity={0.3} />
        </RadarChart>
      </ResponsiveContainer>
      {history.length > 0 && (
        <div style={{ marginTop: 8, fontSize: 12, color: '#6B6B70' }}>
          最近 {history.length} 次快照（kb 演变）：{history.map((h) => h.kb.toFixed(2)).join(' → ')}
        </div>
      )}
    </div>
  );
}