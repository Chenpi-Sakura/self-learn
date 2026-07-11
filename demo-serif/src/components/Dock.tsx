import { useWorkspace } from '../store/useWorkspace';
import './Dock.css';

interface DockItem {
  appId: string;
  ic: string;
  lb: string;
}

const items: DockItem[] = [
  { appId: 'treasure_map', ic: '◇', lb: 'Map' },
  { appId: 'chat',         ic: '✦', lb: 'AI' },
  { appId: 'doc',          ic: '□', lb: 'Doc' },
  { appId: 'exercise',     ic: '≡', lb: 'Ex' },
  { appId: 'code_editor',  ic: '⌨', lb: 'Code' },
  { appId: 'note',         ic: '✎', lb: 'Note' },
  { appId: 'mind_map',     ic: '◈', lb: 'Mind' },
  { appId: 'resource_library', ic: '❐', lb: 'Res' },
  { appId: 'dashboard',    ic: '▣', lb: 'Dash' },
];

// 当前已映射的窗口 id → appId
const WIN_APP_IDS = new Set(['treasure_map', 'today', 'profile', 'calendar']);

export function Dock() {
  const windows = useWorkspace((s) => s.windows);
  const focusedId = useWorkspace((s) => s.focusedId);
  const openWindow = useWorkspace((s) => s.openWindow);
  const focusWindow = useWorkspace((s) => s.focusWindow);

  const openAppIds = new Set(Object.values(windows).map((w) => w.appId));
  const focusedAppId = focusedId ? windows[focusedId]?.appId : null;

  return (
    <nav className="dock">
      {items.map((it) => {
        const isOpen = openAppIds.has(it.appId as any);
        const isFocused = focusedAppId === it.appId;
        const active = isOpen || isFocused;
        return (
          <button
            key={it.appId}
            className={`dock-item${active ? ' active' : ''}`}
            onClick={() => {
              if (WIN_APP_IDS.has(it.appId)) {
                // 已映射的窗口 → 聚焦/取消最小化
                const winEntry = Object.entries(windows).find(
                  ([, v]) => v.appId === it.appId
                );
                if (winEntry) {
                  focusWindow(winEntry[0]);
                } else {
                  openWindow(it.appId as any);
                }
              } else {
                openWindow(it.appId as any);
              }
            }}
            title={it.lb}
          >
            <span className="ic">{it.ic}</span>
            <span className="lb">{it.lb}</span>
          </button>
        );
      })}
    </nav>
  );
}
