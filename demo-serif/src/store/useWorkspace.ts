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
}

interface ChatMsg { role: 'user' | 'ai'; text: string }

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
  toggleTask: (id: string) => void;
  sendChat: (text: string) => void;
}

const initialWindows: Record<string, WindowState> = {
  map:      { id: 'map',      appId: 'treasure_map', x: 80,  y: 80,  w: 720, h: 360, z: 1000 },
  today:    { id: 'today',    appId: 'today',        x: 820, y: 80,  w: 420, h: 360, z: 1001 },
  profile:  { id: 'profile',  appId: 'profile',      x: 80,  y: 460, w: 720, h: 300, z: 1002 },
  calendar: { id: 'calendar', appId: 'calendar',     x: 820, y: 460, w: 420, h: 300, z: 1003 }
};

let replyIdx = 0;

export const useWorkspace = create<WorkspaceState>((set) => ({
  mode: 'proficiency',
  layout: 'reading',
  windows: initialWindows,
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
      next.forEach((w) => { windows[w.id] = w; });
      return { windows };
    }),

  moveWindow: (id, x, y) =>
    set((s) => ({
      windows: { ...s.windows, [id]: { ...s.windows[id], x, y } }
    })),

  focusWindow: (id) =>
    set((s) => {
      const maxZ = Math.max(...Object.values(s.windows).map((w) => w.z));
      return {
        windows: { ...s.windows, [id]: { ...s.windows[id], z: maxZ + 1 } },
        focusedId: id
      };
    }),

  toggleMinimize: (id) =>
    set((s) => ({
      windows: { ...s.windows, [id]: { ...s.windows[id], minimized: !s.windows[id].minimized } }
    })),

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
