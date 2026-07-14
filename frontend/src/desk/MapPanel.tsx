import { useEffect, useState } from 'react';
import { useSession } from '../store/session';
import { getMapNodes } from '../api/map';
import type { MapNode } from '../api/types';

export function MapPanel() {
  const sid = useSession((s) => s.studentId);
  const [nodes, setNodes] = useState<MapNode[]>([]);

  useEffect(() => {
    getMapNodes(sid).then((r) => setNodes(r.nodes)).catch(() => setNodes([]));
  }, [sid]);

  return (
    <div style={{ padding: 12, overflow: 'auto', height: '100%', background: '#fff' }}>
      <h3 style={{ fontFamily: 'HedvigLettersSerif, serif', color: '#1B3B6F', margin: '0 0 8px 0' }}>藏宝图</h3>
      {nodes.length === 0 ? (
        <div style={{ color: '#6B6B70' }}>暂无节点（请后端先生成地图）</div>
      ) : (
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {nodes.map((n) => (
            <li key={n.node_id} style={{ padding: 8, borderBottom: '1px solid #E4E4E0' }}>
              <span style={{ fontWeight: 600 }}>{n.title}</span>
              <span style={{ marginLeft: 8, color: n.status === 'completed' ? '#BC4749' : '#6B6B70', fontSize: 12 }}>
                {n.status}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}