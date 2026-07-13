import { useWorkspace } from '../store/useWorkspace';
import { useDockRef, useDockPositions } from '../lib/dockPositions';
import type { AppId } from '../types/window';
import './Dock.css';

interface DockItem {
  appId: string;
  ic: string;
  lb: string;
}

const items: DockItem[] = [
  { appId: 'treasure_map', ic: '◇', lb: 'Map' },
  { appId: 'chat',         ic: '✦', lb: 'AI' },
  { appId: 'document',     ic: '□', lb: 'Doc' },
  { appId: 'exercise',     ic: '≡', lb: 'Ex' },
  { appId: 'code_editor',  ic: '⌨', lb: 'Code' },
  { appId: 'notebook',     ic: '✎', lb: 'Note' },
  { appId: 'mind_map',     ic: '◈', lb: 'Mind' },
  { appId: 'resource_library', ic: '❐', lb: 'Res' },
  { appId: 'dashboard',    ic: '▣', lb: 'Dash' },
  { appId: 'settings',     ic: '⚙', lb: 'Set' },
  { appId: 'task_list',    ic: '✓', lb: 'Today' },
  { appId: 'profile',      ic: '◉', lb: 'Profile' },
];

export function Dock() {
  const windows = useWorkspace((s) => s.windows);
  const focusedId = useWorkspace((s) => s.focusedId);
  const openWindow = useWorkspace((s) => s.openWindow);
  const focusWindow = useWorkspace((s) => s.focusWindow);
  const dockApi = useDockPositions();

  const openAppIds = new Set(Object.values(windows).map((w) => w.appId));
  const focusedAppId = focusedId ? windows[focusedId]?.appId ?? null : null;

  return (
    <nav className="dock">
      {items.map((it) => (
        <DockButton
          key={it.appId}
          item={it}
          openAppIds={openAppIds}
          focusedAppId={focusedAppId}
          windows={windows}
          openWindow={openWindow}
          focusWindow={focusWindow}
          dockApi={dockApi}
        />
      ))}
    </nav>
  );
}

function DockButton({
  item,
  openAppIds,
  focusedAppId,
  windows,
  openWindow,
  focusWindow,
  dockApi,
}: {
  item: DockItem;
  openAppIds: Set<string>;
  focusedAppId: string | null;
  windows: any;
  openWindow: (appId: AppId) => void;
  focusWindow: (id: string) => void;
  dockApi: ReturnType<typeof useDockPositions>;
}) {
  const setRef = useDockRef(item.appId as AppId);
  const isOpen = openAppIds.has(item.appId);
  const isFocused = focusedAppId === item.appId;
  const active = isOpen || isFocused;
  const isHighlight = dockApi.highlightAppId === item.appId;
  return (
    <button
      ref={setRef}
      className={`dock-item${active ? ' active' : ''}${isHighlight ? ' highlight' : ''}`}
      onClick={() => {
        if (isOpen) {
          const winEntry = Object.entries(windows).find(([, v]) => (v as any).appId === item.appId);
          if (winEntry) focusWindow(winEntry[0]);
        } else {
          openWindow(item.appId as AppId);
        }
      }}
      title={item.lb}
    >
      <span className="ic">{item.ic}</span>
      <span className="lb">{item.lb}</span>
    </button>
  );
}