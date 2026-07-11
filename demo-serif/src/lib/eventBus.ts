// src/lib/eventBus.ts
// mitt 事件总线。覆盖 v4 § 3.9.1 的事件清单。
// 接入策略（混合方案）：跨组件通信、影响多消费者的事件走总线；
// 单消费者、读多写少的场景继续走 Zustand。

import mitt, { type Emitter } from 'mitt';
import type { MapNode, Edge } from '../data/sample';
import type { WindowState } from '../types/window';

export type Profile = unknown; // 占位：v4 § 5.1 结构

export interface LayoutSnapshot {
  id: string;
  label: string;
  windows: WindowState[];
}

export interface LevelCompletionMetrics {
  levelId: string;
  score: number;
  durationSeconds: number;
}

type Events = {
  // window
  'window.opened': WindowState;
  'window.closed': { windowId: string };
  'window.focused': { windowId: string; pinLevel: string };
  'layout.changed': LayoutSnapshot;

  // level
  'level.started': { levelId: string };
  'level.progress': { levelId: string; item: string; percent: number };
  'level.ready': { levelId: string; resources: unknown[] };
  'level.completed': { levelId: string; metrics: LevelCompletionMetrics };

  // profile / map
  'profile.updated': Profile;
  'map.updated': { nodes: MapNode[]; edges: Edge[] };
  'mode.changed': 'exploration' | 'proficiency';

  // resource
  'resource.bound': { fileId: string; levelId: string };

  // shortcut
  'shortcut.triggered': { shortcutId: string };
};

export const eventBus: Emitter<Events> = mitt<Events>();