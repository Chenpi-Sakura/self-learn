import { create } from 'zustand';

interface LevelState {
  levelId: string | null;
  nodeId: string | null;
  /** nodeId → levelId 缓存（用于切回节点时显示原关卡） */
  byNode: Record<string, string>;

  setActive: (levelId: string, nodeId: string) => void;
  clear: () => void;
}

export const useLevel = create<LevelState>((set) => ({
  levelId: null,
  nodeId: null,
  byNode: {},

  setActive: (levelId, nodeId) =>
    set((s) => ({
      levelId,
      nodeId,
      byNode: { ...s.byNode, [nodeId]: levelId },
    })),

  clear: () => set({ levelId: null, nodeId: null }),
}));
