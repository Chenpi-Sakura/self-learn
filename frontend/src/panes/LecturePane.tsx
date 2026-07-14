import { useEffect, useState } from 'react';
import { Rnd } from 'react-rnd';
import { getLevel } from '../api/level';

export function LecturePane({ levelId, onClose }: { levelId: string; onClose: () => void }) {
  const [content, setContent] = useState<string>('加载讲义...');

  useEffect(() => {
    if (!levelId) {
      setContent('请先启动关卡');
      return;
    }
    getLevel(levelId)
      .then((lv) => {
        const first = lv.exercises[0];
        setContent(first ? `[${lv.exercises.length} 题] ${first.prompt}` : '关卡无题目');
      })
      .catch(() => setContent('加载失败'));
  }, [levelId]);

  return (
    <Rnd default={{ x: 100, y: 100, width: 500, height: 400 }}>
      <div style={{ background: '#fff', padding: 16, borderRadius: 8, border: '1px solid #E4E4E0', height: '100%', overflow: 'auto', fontFamily: 'HedvigLettersSerif, serif' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h4 style={{ margin: 0, color: '#1B3B6F' }}>讲义</h4>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#BC4749' }}>×</button>
        </div>
        <div style={{ marginTop: 12 }}>{content}</div>
      </div>
    </Rnd>
  );
}