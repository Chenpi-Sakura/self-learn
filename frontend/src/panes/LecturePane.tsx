import { useEffect, useState } from 'react';
import { getLevel } from '../api/level';

export function LecturePane({ levelId }: { levelId: string }) {
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

  return <div style={{ padding: 16, height: '100%', overflow: 'auto', fontFamily: 'HedvigLettersSerif, serif' }}>{content}</div>;
}
