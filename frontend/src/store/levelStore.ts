import { create } from 'zustand';

interface LevelState {
  levelId: string | null;
  nodeId: string | null;
  /** nodeId → levelId 缓存（用于切回节点时显示原关卡） */
  byNode: Record<string, string>;
  /** levelId → traceId（director chain 任务标识，供 SSE 进度订阅） */
  byLevel: Record<string, string>;

  setActive: (levelId: string, nodeId: string, traceId?: string) => void;
  clear: () => void;
}

export const useLevel = create<LevelState>((set) => ({
  levelId: null,
  nodeId: null,
  byNode: {},
  byLevel: {},

  setActive: (levelId, nodeId, traceId) =>
    set((s) => ({
      levelId,
      nodeId,
      byNode: { ...s.byNode, [nodeId]: levelId },
      byLevel: traceId ? { ...s.byLevel, [levelId]: traceId } : s.byLevel,
    })),

  clear: () =>
    set({ levelId: null, nodeId: null, byNode: {}, byLevel: {} }),
}));
