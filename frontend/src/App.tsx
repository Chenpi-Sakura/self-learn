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
import { CalendarPanel } from './desk/CalendarPanel';
import { LecturePane } from './panes/LecturePane';
import { ExercisePane } from './panes/ExercisePane';
import { ResourceLibrary } from './components/ResourceLibrary';
import { ExtractTopicsDialog } from './components/ExtractTopicsDialog';
import { MDBrowser } from './components/MDBrowser';
import { EmptyStateOverlay } from './components/EmptyStateOverlay';
import { useWorkspace } from './store/useWorkspace';
import { useSession } from './store/session';
import { useLevel } from './store/levelStore';
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
  dashboard:    { title: '日历' },
  document:     { title: '讲义' },
  exercise:     { title: '习题' },
  resource_library: { title: '资源管理器' },
  extract_topics_dialog: { title: '生成地图对话框' },
  md_browser: { title: 'MD 浏览器' },
};

export default function App() {
  const windows = useWorkspace((s) => s.windows);
  const openWindow = useWorkspace((s) => s.openWindow);
  const closeWindow = useWorkspace((s) => s.closeWindow);
  const studentId = useSession((s) => s.studentId);
  const levelId = useLevel((s) => s.levelId) ?? '';

  useEffect(() => {
    registerSystemShortcuts();
    const handler = (e: KeyboardEvent) => {
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

  function renderBody(appId: string, win: WindowState): ReactNode {
    switch (appId) {
      case 'treasure_map':
        return <TreasureMap studentId={studentId} />;
      case 'task_list':
        return <TaskList />;
      case 'profile':
        return <ProfileRadar studentId={studentId} />;
      case 'chat':
        return <ChatFloat win={win} />;
      case 'dashboard':
        return <CalendarPanel />;
      case 'document':
        return <LecturePane levelId={levelId} />;
      case 'exercise':
        return <ExercisePane levelId={levelId} />;
      case 'resource_library':
        return (
          <ResourceLibrary
            onOpenExtractDialog={(ids) =>
              openWindow('extract_topics_dialog', { preselected: ids })
            }
          />
        );
      case 'extract_topics_dialog':
        return (
          <ExtractTopicsDialog
            preSelectedIds={(win.metadata?.preselected as string[] | undefined) ?? []}
            onConfirm={() => {
              // ResourceLibrary 在本任务中通过 refresh 逻辑接管 ProgressOverlay
              // 这里简单关掉；ResourceLibrary 在 confirm 后会触发额外 UI 更新。
              closeWindow('extract_topics_dialog');
            }}
            onCancel={() => closeWindow('extract_topics_dialog')}
          />
        );
      case 'md_browser':
        return (
          <MDBrowser
            resourceId={
              (win.metadata?.resourceId as string | undefined) ?? ''
            }
          />
        );
      default:
        return null;
    }
  }

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
        <EmptyStateOverlay />
      </div>
    </DockPositionsProvider>
  );
}
