import './App.css';
import { useEffect, useState } from 'react';
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
import { Onboarding } from './components/Onboarding';
import { triggerExtractTopics } from './api/extractTopics';
import { getProfile } from './api/profile';
import { useProfile } from './store/profile';
import { useWorkspace } from './store/useWorkspace';
import { useSession } from './store/session';
import { useLevel } from './store/levelStore';
import { isProfileInitialized } from './utils/profile';
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
  const [profileLoading, setProfileLoading] = useState(true);
  const dimensions = useProfile((s) => s.dimensions);

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

  useEffect(() => {
    if (!studentId) return;
    getProfile(studentId)
      .then((res) => {
        useProfile.getState().setDimensions(res.dimensions);
      })
      .catch(() => {
        // Profile doesn't exist yet — dimensions stays null, onboarding will show
      })
      .finally(() => setProfileLoading(false));
  }, [studentId]);

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
            win={win}
            onOpenExtractDialog={(ids) =>
              openWindow('extract_topics_dialog', { preselected: ids })
            }
          />
        );
      case 'extract_topics_dialog':
        return (
          <ExtractTopicsDialog
            preSelectedIds={(win.metadata?.preselected as string[] | undefined) ?? []}
            onConfirm={async (ids) => {
              try {
                const { task_id } = await triggerExtractTopics(ids);
                closeWindow(appId);
                openWindow('resource_library', { extractTaskId: task_id } as any);
              } catch {
                // 提炼触发失败，留在对话窗让用户重试
              }
            }}
            onCancel={() => closeWindow(appId)}
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

  if (profileLoading) {
    return <div style={{ padding: 40, fontFamily: 'HedvigLettersSerif, serif' }}>加载中...</div>;
  }

  if (!isProfileInitialized(dimensions)) {
    return (
      <Onboarding
        studentId={studentId}
        onDone={() => window.location.reload()}
      />
    );
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
