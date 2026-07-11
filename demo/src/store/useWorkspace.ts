import { create } from 'zustand';
import type { WindowBox } from '../lib/layouts';
import { layouts, layoutOrder } from '../lib/layouts';
import type { MapNode } from '../data/sample';
import { mapNodes } from '../data/sample';

export type LearningMode = 'master' | 'explore';
export type LayoutId = 'reading' | 'practice' | 'coding';

interface OpenWin {
  appId: WindowBox['appId'];
  x: number;
  y: number;
  w: number;
  h: number;
  z: number;
}

interface WorkspaceState {
  mode: LearningMode;
  layout: LayoutId;
  windows: OpenWin[];
  topZ: number;
  nodes: MapNode[];                       // 节点位置（可拖拽改变）
  checkedIn: boolean;
  selectedNode: string | null;
  hoveredNode: string | null;

  setMode: (m: LearningMode) => void;
  setLayout: (id: LayoutId) => void;
  moveWindow: (appId: OpenWin['appId'], x: number, y: number) => void;
  focusWindow: (appId: OpenWin['appId']) => void;
  moveNode: (id: string, x: number, y: number) => void;
  toggleCheckIn: () => void;
  selectNode: (id: string | null) => void;
  hoverNode: (id: string | null) => void;
}

const initialLayout = layoutOrder[0];

function snapshotToWindows(id: LayoutId): OpenWin[] {
  const preset = layouts[id];
  return preset.windows.map((w, i) => ({
    appId: w.appId,
    x: w.x,
    y: w.y,
    w: w.w,
    h: w.h,
    z: 1000 + i,
  }));
}

export const useWorkspace = create<WorkspaceState>((set, get) => ({
  mode: 'master',
  layout: initialLayout,
  windows: snapshotToWindows(initialLayout),
  topZ: 1003,
  nodes: mapNodes.map((n) => ({ ...n })),
  checkedIn: false,
  selectedNode: null,
  hoveredNode: null,

  setMode: (m) => set({ mode: m }),

  setLayout: (id) =>
    set({
      layout: id,
      windows: snapshotToWindows(id).map((w, i) => ({
        ...w,
        z: Math.max(get().topZ + 1, 1000 + i),
      })),
      topZ: get().topZ + 100,
    }),

  moveWindow: (appId, x, y) =>
    set((s) => ({
      windows: s.windows.map((w) =>
        w.appId === appId ? { ...w, x, y } : w,
      ),
    })),

  focusWindow: (appId) =>
    set((s) => {
      const next = s.topZ + 1;
      return {
        topZ: next,
        windows: s.windows.map((w) =>
          w.appId === appId ? { ...w, z: next } : w,
        ),
      };
    }),

  moveNode: (id, x, y) =>
    set((s) => ({
      nodes: s.nodes.map((n) => (n.id === id ? { ...n, x, y } : n)),
    })),

  toggleCheckIn: () => set((s) => ({ checkedIn: !s.checkedIn })),

  selectNode: (id) => set({ selectedNode: id }),
  hoverNode: (id) => set({ hoveredNode: id }),
}));