import './App.css';
import { Backdrop } from './components/Backdrop';
import { TopBar } from './components/TopBar';
import { Dock } from './components/Dock';
import { ChatFloat } from './components/ChatFloat';
import { Window } from './components/Window';
import { TreasureMap } from './components/TreasureMap';
import { TaskList } from './components/TaskList';
import { ProfileRadar } from './components/ProfileRadar';
import { Calendar } from './components/Calendar';
import { useWorkspace } from './store/useWorkspace';
import type { WindowState } from './store/useWorkspace';

const WIN_CONTENT: Record<string, { title: string; isKey?: boolean; comp: React.ReactNode }> = {
  treasure_map: { title: '深度学习路径', isKey: true, comp: <TreasureMap /> },
  today:        { title: '今日学习',                  comp: <TaskList /> },
  profile:      { title: '六维画像',                  comp: <ProfileRadar /> },
  calendar:     { title: '本月打卡',                  comp: <Calendar /> },
};

export default function App() {
  const windows = useWorkspace((s) => s.windows);

  const entries: [WindowState, typeof WIN_CONTENT[string]][] = [];
  for (const w of Object.values(windows)) {
    const def = WIN_CONTENT[w.appId];
    if (def) entries.push([w, def]);
  }

  return (
    <div className="app">
      <Backdrop />
      <TopBar />
      <div className="windows-layer">
        {entries.map(([win, def]) => (
          <Window key={win.id} win={win} title={def.title} isKey={def.isKey}>
            {def.comp}
          </Window>
        ))}
      </div>
      <Dock />
      <ChatFloat />
    </div>
  );
}
