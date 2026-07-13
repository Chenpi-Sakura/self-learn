import './App.css';
import { useEffect } from 'react';
import { Backdrop } from './components/Backdrop';
import { TopBar } from './components/TopBar';
import { Dock } from './components/Dock';
import { Window } from './components/Window';
import { TreasureMap } from './components/TreasureMap';
import { TaskList } from './components/TaskList';
import { ProfileRadar } from './components/ProfileRadar';
import { ChatFloat } from './components/ChatFloat';
import { useWorkspace } from './store/useWorkspace';
import { shortcutManager, parseKeyEvent, registerSystemShortcuts } from './lib/shortcuts';
import { DockPositionsProvider } from './lib/dockPositions';
import type { WindowState } from './types/window';
import type { ReactNode } from 'react';

type WinDef = { title: string; isKey?: boolean };

const WIN_CONTENT: Record<string, WinDef> = {
  treasure_map: { title: '深度学习路径', isKey: true },
  task_list:    { title: '今日学习' },
  profile:      { title: '六维画像' },
  chat:         { title: '小书' },
};

function renderBody(appId: string, win: WindowState): ReactNode {
  switch (appId) {
    case 'treasure_map': return <TreasureMap />;
    case 'task_list':    return <TaskList />;
    case 'profile':      return <ProfileRadar />;
    case 'chat':         return <ChatFloat win={win} />;
    default:             return null;
  }
}

export default function App() {
  const windows = useWorkspace((s) => s.windows);

  useEffect(() => {
    registerSystemShortcuts();
    const handler = (e: KeyboardEvent) => {
      // 忽略输入框/文本域内按键（避免与文字输入冲突）
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA') return;
      const combo = parseKeyEvent(e);
      if (shortcutManager.fire(combo)) {
        e.preventDefault();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const entries: [WindowState, WinDef][] = [];
  for (const w of Object.values(windows)) {
    const def = WIN_CONTENT[w.appId];
    if (def) entries.push([w, def]);
  }

  return (
    <DockPositionsProvider>
      <div className="app">
        <Backdrop />
        <TopBar />
        <div className="windows-layer">
          {entries.map(([win, def]) => (
            <Window key={win.id} win={win} title={def.title} isKey={def.isKey}>
              {renderBody(win.appId, win)}
            </Window>
          ))}
        </div>
        <Dock />
      </div>
    </DockPositionsProvider>
  );
}