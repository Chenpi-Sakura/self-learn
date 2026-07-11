import { create } from 'zustand';
import { mapNodes, mapEdges, profile, calendar, tasks, initialChat, mockAiReplies } from '../data/sample';

export type Mode = 'proficiency' | 'exploration';
export type LayoutId = 'reading' | 'practice' | 'coding';

export interface WindowState {
  id: string;
  appId: 'treasure_map' | 'today' | 'profile' | 'calendar' | 'doc' | 'exercise' | 'note';
  x: number; y: number;
  w: number; h: number;
  z: number;
  minimized?: boolean;
  maximized?: boolean;
  pinLevel: 'none' | 'normal' | 'always';
  /** 保存最大化前的位置大小，用于还原 */
  _prev?: { x: number; y: number; w: number; h: number };
}

interface ChatMsg { role: 'user' | 'ai'; text: string }

const DEFAULT_WIN: Record<string, Omit<WindowState, 'pinLevel'>> = {
  map:      { id: 'map',      appId: 'treasure_map', x: 80,  y: 80,  w: 720, h: 360, z: 1000 },
  today:    { id: 'today',    appId: 'today',        x: 820, y: 80,  w: 420, h: 360, z: 1001 },
  profile:  { id: 'profile',  appId: 'profile',      x: 80,  y: 460, w: 720, h: 300, z: 1002 },
  calendar: { id: 'calendar', appId: 'calendar',     x: 820, y: 460, w: 420, h: 300, z: 1003 }
};

/** 同一个 appId→id 的映射 */
const APP_TO_ID: Record<string, string> = {
  treasure_map: 'map',
  today: 'today',
  profile: 'profile',
  calendar: 'calendar',
};

function initWindows(): Record<string, WindowState> {
  const w: Record<string, WindowState> = {};
  for (const [k, v] of Object.entries(DEFAULT_WIN)) {
    w[k] = { ...v, pinLevel: 'none' };
  }
  return w;
}

let replyIdx = 0;

interface WorkspaceState {
  mode: Mode;
  layout: LayoutId;
  windows: Record<string, WindowState>;
  nodes: typeof mapNodes;
  edges: typeof mapEdges;
  profile: typeof profile;
  calendar: typeof calendar;
  tasks: typeof tasks;
  chat: ChatMsg[];
  focusedId: string | null;

  setMode: (m: Mode) => void;
  setLayout: (l: LayoutId, next: WindowState[]) => void;
  moveWindow: (id: string, x: number, y: number) => void;
  focusWindow: (id: string) => void;
  toggleMinimize: (id: string) => void;
  toggleMaximize: (id: string) => void;
  togglePin: (id: string) => void;
  closeWindow: (id: string) => void;
  openWindow: (appId: WindowState['appId']) => void;
  toggleTask: (id: string) => void;
  sendChat: (text: string) => void;
}

export const useWorkspace = create<WorkspaceState>((set, get) => ({
  mode: 'proficiency',
  layout: 'reading',
  windows: initWindows(),
  nodes: mapNodes,
  edges: mapEdges,
  profile,
  calendar,
  tasks,
  chat: initialChat,
  focusedId: 'map',

  setMode: (m) => set({ mode: m }),

  setLayout: (_l, next) =>
    set((s) => {
      const windows = { ...s.windows };
      next.forEach((w) => { windows[w.id] = { ...w, pinLevel: windows[w.id]?.pinLevel ?? 'none' }; });
      return { windows };
    }),

  moveWindow: (id, x, y) =>
    set((s) => ({
      windows: { ...s.windows, [id]: { ...s.windows[id], x, y } }
    })),

  focusWindow: (id) =>
    set((s) => {
      const maxZ = Math.max(...Object.values(s.windows).map((w) => w.z));
      const w = s.windows[id];
      if (!w) return s;
      return {
        windows: {
          ...s.windows,
          [id]: { ...w, z: maxZ + 1, minimized: false }
        },
        focusedId: id
      };
    }),

  toggleMinimize: (id) =>
    set((s) => {
      const w = s.windows[id];
      if (!w) return s;
      // 如果当前是最大化，先取消最大化再最小化
      if (w.maximized) {
        const prev = w._prev;
        return {
          windows: {
            ...s.windows,
            [id]: { ...w, maximized: false, _prev: undefined, x: prev?.x ?? w.x, y: prev?.y ?? w.y, w: prev?.w ?? w.w, h: prev?.h ?? w.h, minimized: true }
          }
        };
      }
      return {
        windows: { ...s.windows, [id]: { ...w, minimized: !w.minimized } }
      };
    }),

  toggleMaximize: (id) =>
    set((s) => {
      const w = s.windows[id];
      if (!w) return s;
      if (w.maximized) {
        // 还原
        const prev = w._prev;
        return {
          windows: {
            ...s.windows,
            [id]: { ...w, maximized: false, _prev: undefined, x: prev?.x ?? w.x, y: prev?.y ?? w.y, w: prev?.w ?? w.w, h: prev?.h ?? w.h }
          }
        };
      } else {
        // 最大化：保存当前位置大小
        return {
          windows: {
            ...s.windows,
            [id]: { ...w, maximized: true, _prev: { x: w.x, y: w.y, w: w.w, h: w.h } }
          }
        };
      }
    }),

  togglePin: (id) =>
    set((s) => {
      const w = s.windows[id];
      if (!w) return s;
      const nextPin: 'none' | 'normal' = w.pinLevel === 'none' ? 'normal' : 'none';
      const windows: Record<string, WindowState> = { ...s.windows, [id]: { ...w, pinLevel: nextPin } };
      // 重新分配 z-index：桶排序
      const always: Record<string, WindowState> = {};
      const normal: Record<string, WindowState> = {};
      const rest: Record<string, WindowState> = {};
      for (const [k, v] of Object.entries(windows)) {
        if (v.pinLevel === 'always') always[k] = v;
        else if (v.pinLevel === 'normal') normal[k] = v;
        else rest[k] = v;
      }
      const sorted: Array<[string, WindowState]> = [
        ...Object.entries(rest).sort(([, a], [, b]) => a.z - b.z),
        ...Object.entries(normal).sort(([, a], [, b]) => a.z - b.z),
        ...Object.entries(always),
      ];
      let base = 1000;
      for (const [k, v] of sorted) {
        const pin = v.pinLevel;
        const zBase: number = pin === 'always' ? 11000 : pin === 'normal' ? 5100 : base++;
        windows[k] = { ...v, z: zBase };
      }
      return { windows };
    }),

  closeWindow: (id) =>
    set((s) => {
      const remaining = Object.keys(s.windows).filter((k) => k !== id);
      if (remaining.length === 0) return s; // 至少保留一个窗口
      const windows: Record<string, WindowState> = {};
      for (const k of remaining) {
        windows[k] = s.windows[k];
      }
      const focusedId = s.focusedId === id ? remaining[0] : s.focusedId;
      return { windows, focusedId };
    }),

  openWindow: (appId) =>
    set((s) => {
      // 检查该 appId 是否已打开
      const existingKey = APP_TO_ID[appId];
      if (existingKey && s.windows[existingKey]) {
        // 已存在 → 聚焦 + 取消最小化
        const maxZ = Math.max(...Object.values(s.windows).map((w) => w.z));
        return {
          windows: { ...s.windows, [existingKey]: { ...s.windows[existingKey], minimized: false, z: maxZ + 1 } },
          focusedId: existingKey
        };
      }
      // 不存在 → 新建
      const key = existingKey || `win_${appId}_${Date.now()}`;
      const maxZ = Math.max(...Object.values(s.windows).map((w) => w.z));
      const def = DEFAULT_WIN[key];
      const newWin: WindowState = {
        id: key,
        appId,
        x: def?.x ?? 100,
        y: def?.y ?? 100,
        w: def?.w ?? 600,
        h: def?.h ?? 400,
        z: maxZ + 1,
        pinLevel: 'none'
      };
      return {
        windows: { ...s.windows, [key]: newWin },
        focusedId: key
      };
    }),

  toggleTask: (id) =>
    set((s) => ({
      tasks: s.tasks.map((t) =>
        t.id === id
          ? { ...t, status: t.status === 'done' ? 'todo' : 'done' }
          : t
      )
    })),

  sendChat: (text) => {
    const userMsg: ChatMsg = { role: 'user', text };
    set((s) => ({ chat: [...s.chat, userMsg] }));
    setTimeout(() => {
      const reply = mockAiReplies[replyIdx % mockAiReplies.length];
      replyIdx++;
      const aiMsg: ChatMsg = { role: 'ai', text: reply };
      set((s) => ({ chat: [...s.chat, aiMsg] }));
    }, 500);
  }
}));
