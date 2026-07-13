import { create } from 'zustand';
import type { AppId, WindowState, PinLevel } from '../types/window';
import { SINGLETON_APP_IDS } from '../types/window';
import { mapNodes, mapEdges, profile, tasks, initialChat, mockAiReplies } from '../data/sample';

export type Mode = 'proficiency' | 'exploration';
export type LayoutId = 'reading' | 'practice' | 'coding';
export type { AppId, WindowState, PinLevel };

interface ChatMsg { role: 'user' | 'ai'; text: string }

const DEFAULT_WIN: Record<string, Omit<WindowState, 'pinLevel'>> = {
  map:      { id: 'map',      appId: 'treasure_map', x: 80,  y: 80,  w: 720, h: 360, z: 1000 },
  today:    { id: 'today',    appId: 'task_list',    x: 820, y: 80,  w: 420, h: 360, z: 1001 },
  profile:  { id: 'profile',  appId: 'profile',      x: 80,  y: 460, w: 720, h: 300, z: 1002 },
  chat:     { id: 'chat',     appId: 'chat',         x: 1000, y: 460, w: 280, h: 320, z: 1003 },
};

/** 同一个 appId→id 的映射 */
const APP_TO_ID: Record<string, string> = {
  treasure_map: 'map',
  task_list: 'today',
  profile: 'profile',
  chat: 'chat',
};

function initWindows(): Record<string, WindowState> {
  const w: Record<string, WindowState> = {};
  for (const [k, v] of Object.entries(DEFAULT_WIN)) {
    const pinLevel: PinLevel = k === 'chat' ? 'always' : 'none';
    w[k] = { ...v, pinLevel };
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
  resizeWindow: (id: string, size: { w?: number; h?: number; x?: number; y?: number }) => void;
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
      const w = s.windows[id];
      if (!w) return s;
      const all = Object.values(s.windows);
      const sameTier = all.filter((x) => x.pinLevel === w.pinLevel && x.id !== id);
      const maxZ = sameTier.length > 0 ? Math.max(...sameTier.map((x) => x.z)) : w.z;
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
            [id]: { ...w, maximized: false, x: prev?.x ?? w.x, y: prev?.y ?? w.y, w: prev?.w ?? w.w, h: prev?.h ?? w.h, minimized: true, _prev: { x: prev?.x ?? w.x, y: prev?.y ?? w.y, w: prev?.w ?? w.w, h: prev?.h ?? w.h } }
          }
        };
      }
      if (w.minimized) {
        // 恢复：用 _prev 还原（v4 § 2.2.4）
        const prev = w._prev;
        return {
          windows: {
            ...s.windows,
            [id]: { ...w, minimized: false, _prev: undefined, x: prev?.x ?? w.x, y: prev?.y ?? w.y, w: prev?.w ?? w.w, h: prev?.h ?? w.h }
          }
        };
      }
      // 最小化：保存 _prev 以便恢复
      return {
        windows: { ...s.windows, [id]: { ...w, minimized: true, _prev: { x: w.x, y: w.y, w: w.w, h: w.h } } }
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
      if (w.pinLevel === 'always') return s; // 系统置顶（chat 等），用户不可改
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
      // 单实例 appId 列表（v4 § 3.11.1）：第二次打开只聚焦
      if (SINGLETON_APP_IDS.has(appId)) {
        const existing = Object.values(s.windows).find((w) => w.appId === appId);
        if (existing) {
          const maxZ = Math.max(...Object.values(s.windows).map((w) => w.z));
          return {
            windows: { ...s.windows, [existing.id]: { ...existing, minimized: false, z: maxZ + 1 } },
            focusedId: existing.id,
          };
        }
      }
      // 检查该 appId 是否已打开（多实例）
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
      const TOPBAR_H = 52;
      const initW = def?.w ?? 600;
      const initH = def?.h ?? 400;
      const newWin: WindowState = {
        id: key,
        appId,
        x: Math.max(0, (window.innerWidth - initW) / 2),
        y: Math.max(0, (window.innerHeight - TOPBAR_H - initH) / 2),
        w: initW,
        h: initH,
        z: maxZ + 1,
        pinLevel: appId === 'chat' ? 'always' : 'none'
      };
      return {
        windows: { ...s.windows, [key]: newWin },
        focusedId: key
      };
    }),

  resizeWindow: (id, size) =>
    set((s) => {
      const w = s.windows[id];
      if (!w) return s;
      const MIN_W = 240, MIN_H = 160;
      const MAX_W = 1280, MAX_H = 900;
      // 对 w/h 单独钳制
      const reqW = size.w !== undefined ? Math.max(MIN_W, Math.min(MAX_W, size.w)) : w.w;
      const reqH = size.h !== undefined ? Math.max(MIN_H, Math.min(MAX_H, size.h)) : w.h;
      // x/y 与 w/h 联动钳制：
      // 调用方传入的 size.x/y 是"想要的目标左边沿位置"，
      // 当 w 被钳制变化时，同步补偿 x，使右/下边沿保持不变。
      const newX = size.x !== undefined ? size.x + (size.w! - reqW) : w.x;
      const newY = size.y !== undefined ? size.y + (size.h! - reqH) : w.y;
      return {
        windows: { ...s.windows, [id]: { ...w, w: reqW, h: reqH, x: newX, y: newY } }
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
