import { useEffect, useState, type ReactNode } from 'react';
import { MapPanel } from './MapPanel';
import { ProfilePanel } from './ProfilePanel';
import { CalendarPanel } from './CalendarPanel';
import { LecturePane } from '../panes/LecturePane';
import { ExercisePane } from '../panes/ExercisePane';
import { ChatPane } from '../panes/ChatPane';
import { ResetButton } from '../reset/ResetButton';
import { useSession } from '../store/session';
import { useProfile } from '../store/profile';
import { getProfile } from '../api/profile';

type PaneKey = 'lecture' | 'exercise' | 'chat';

function PaneOpener({ name, paneKey, open, onOpen }: {
  name: string; paneKey: PaneKey; open: boolean; onOpen: (k: PaneKey) => void;
}): ReactNode {
  return (
    <button
      onClick={() => onOpen(paneKey)}
      style={{
        padding: '8px 12px', background: open ? '#1B3B6F' : '#fff',
        color: open ? '#fff' : '#1A1A1A', border: '1px solid #E4E4E0',
        borderRadius: 4, cursor: 'pointer', fontFamily: 'HedvigLettersSerif, serif',
      }}
    >
      {name}
    </button>
  );
}

export function Desktop() {
  const sid = useSession((s) => s.studentId);
  const setDims = useProfile((s) => s.setDimensions);
  const [activePane, setActivePane] = useState<PaneKey | null>(null);

  // 启动时拉画像
  useEffect(() => {
    getProfile(sid).then((p) => setDims(p.dimensions)).catch(() => {/* 等 SSE */});
  }, [sid, setDims]);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', height: '100vh', background: '#F7F5EF', position: 'relative' }}>
      <div style={{ display: 'grid', gridTemplateRows: '2fr 1fr', borderRight: '1px solid #E4E4E0', overflow: 'hidden' }}>
        <MapPanel />
        <ProfilePanel />
      </div>
      <CalendarPanel />
      <div style={{ position: 'absolute', bottom: 16, left: '50%', transform: 'translateX(-50%)', display: 'flex', gap: 8, background: 'rgba(255,255,255,0.9)', padding: 8, borderRadius: 8, border: '1px solid #E4E4E0' }}>
        <PaneOpener name="讲义" paneKey="lecture" open={activePane === 'lecture'} onOpen={setActivePane} />
        <PaneOpener name="习题" paneKey="exercise" open={activePane === 'exercise'} onOpen={setActivePane} />
        <PaneOpener name="AI 对话" paneKey="chat" open={activePane === 'chat'} onOpen={setActivePane} />
      </div>
      <ResetButton />
      {activePane === 'lecture' && <LecturePane levelId="" onClose={() => setActivePane(null)} />}
      {activePane === 'exercise' && <ExercisePane levelId="" onClose={() => setActivePane(null)} />}
      {activePane === 'chat' && <ChatPane onClose={() => setActivePane(null)} />}
    </div>
  );
}