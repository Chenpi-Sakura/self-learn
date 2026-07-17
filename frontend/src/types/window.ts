// src/types/window.ts
// 窗口、关卡等核心类型统一定义（v4 § 3.2.1 + § 3.14.1 + § 3.15）

export type AppId =
  | 'treasure_map'
  | 'chat'
  | 'document'
  | 'exercise'
  | 'code_editor'
  | 'notebook'
  | 'mind_map'
  | 'resource_library'
  | 'extract_topics_dialog'
  | 'md_browser'
  | 'dashboard'
  | 'settings'
  | 'task_list'
  | 'profile';

export type PinLevel = 'none' | 'normal' | 'always';

export interface WindowState {
  id: string;
  appId: AppId;
  title?: string;
  x: number;
  y: number;
  w: number;
  h: number;
  z: number;
  minimized?: boolean;
  maximized?: boolean;
  pinLevel: PinLevel;
  /** 内部字段：max/minimize 前的位置尺寸，用于还原动画 */
  _prev?: { x: number; y: number; w: number; h: number };
  /** 窗口内部状态：滚动位置、当前页码等（v4 § 3.2.1） */
  contentState?: Record<string, unknown>;
  /** 窗口关联元信息（v4 § 3.2.1） */
  metadata?: {
    levelId?: string;
    resourceId?: string;
    preselected?: string[];
    transient?: boolean;
  };
}

export type LevelStatus = 'locked' | 'unlocked' | 'in_progress' | 'completed' | 'mastered';
export type BranchStatus = 'active' | 'sleeping';
export type LevelSubtype = 'reading_practice' | 'reading_tutor' | 'coding_lab' | 'task_challenge';

export interface LevelVisualBadge {
  badge?: 'star' | 'sprint' | 'new' | 'key' | null;
}

export const SINGLETON_APP_IDS: ReadonlySet<AppId> = new Set<AppId>([
  'treasure_map',
  'notebook',
  'resource_library',
  'extract_topics_dialog',
  'md_browser',
  'dashboard',
  'settings',
  'task_list',
]);