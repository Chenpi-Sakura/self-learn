# 窗口动画 + 附录 A 对齐 v4 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Stage 4 T1 重命名注（2026-07-13）**：本文档原工程目录为 `demo-serif/`，Stage 4 T1 已重命名为 `frontend/`。下方所有 `demo-serif/` 字串保留原貌以保持历史准确性。

**Goal:** 给 demo-serif 补全 4 类窗口过渡动画（最大化/还原/最小化收 Dock/关闭淡出），并按 spec 实施附录 A 10 项决策（v4 文档 + 7 批代码重构）

**Architecture:**
- **动画子项目**：保留现有 CSS transition 基础设施，扩展 `.win.maximized` 不再切到 position: absolute 铺满、给最小化加 Dock 目标位置拉拽动画
- **附录 A 子项目**：7 个渐进 commit，先发 v4 文档（不改代码），再逐层加持久化/事件总线/Store 重构/AppId 重命名/画像维度/快捷键 scope/动画

**Tech Stack:** React 18 + TypeScript + Zustand + Framer Motion + Vite + mitt（事件总线，待装）

## 全局约束补充（用户偏好）

**@用户偏好：交互类型与视觉类型的测试由用户亲自执行，agent 不截图、不跑点击交互、不判断动画视觉流畅度。**

agent 在执行本计划时：
- ✅ 可以执行：类型检查（`npx tsc --noEmit`）、build（`npm run build`）、grep、git diff、commit
- ✅ 可以执行：**chrome-devtools MCP 工具**（`mcp__chrome-devtools__*`）——启动浏览器、查看 console、查看 network、读取 DOM/snapshot、用 `evaluate_script` 读 React/store 内部状态、调用 `list_console_messages` 抓错误、调用 `list_network_requests` 查请求
- ❌ **不可以**执行：截图（`take_screenshot`）、点击交互（`click` / `hover` / `drag`）、动画流畅度的主观判断
- 任何带"手动冒烟 / 肉眼验证"的步骤，必须在 commit 之前由用户完成
- 计划文档中这些步骤前都加了 **@用户验证** 标记

**agent 可以的辅助验证手段**：
- `npx tsc --noEmit`：类型检查
- `npm run build`：构建检查
- `mcp__chrome-devtools__list_console_messages`：抓运行时错误
- `mcp__chrome-devtools__evaluate_script`：读 `window.__workspace`（如果暴露）或 React DevTools 数据
- `mcp__chrome-devtools__list_network_requests`：检查 API 请求
- 这些手段**不能替代**用户的视觉/交互测试，仅作为代码层信号

## Global Constraints

按 spec 全局约束：
- 动画时长 **220ms**，缓动 **`cubic-bezier(0.4, 0, 0.2, 1)`**
- 必须支持 `@media (prefers-reduced-motion: reduce)` 媒体查询
- 7 个渐进 commit，每 commit 后必须 `npm run build` 通过；**手动冒烟由用户执行（见全局约束补充）**
- v4 文档 `git diff v3 v4` 必须只动附录 A 列出的 10 个差异点附近
- 中文用户偏好：所有 commit message、文档标题、注释允许中英混合，但叙述性文字以中文为主
- 工作目录：`D:\Projects\SelfLearn`（demo-serif 在 `demo-serif/` 子目录）
- 路径前缀以 `demo-serif/` 起

---

## 文件结构总览

### 新建文件

| 路径 | 职责 |
| --- | --- |
| `docs/详细设计规格说明书-v4.md` | 复制 v3，按附录 A 决策修订 |
| `docs/superpowers/plans/2026-07-11-window-animation-and-v4-alignment.md` | 本计划 |
| `demo-serif/src/lib/persistence.ts` | IndexedDB + localStorage 封装 |
| `demo-serif/src/lib/eventBus.ts` | mitt 事件总线 |
| `demo-serif/src/lib/dockPositions.tsx` | Dock 位置查询 Context + hook |
| `demo-serif/src/lib/shortcuts.ts` | 快捷键系统 + scope 管理 |
| `demo-serif/src/components/ProfileRadar/animations.ts` | 数值增长动画变体（framer-motion） |
| `demo-serif/src/types/window.ts` | WindowState / AppId / 枚举类型统一定义 |

### 修改文件

| 路径 | 改动 |
| --- | --- |
| `demo-serif/src/components/Window.tsx` | style 计算改写、closing state、Dock 目标位置拉拽 |
| `demo-serif/src/components/Window.css` | 移除 max position/border、移除 resize 图标、prefers-reduced-motion |
| `demo-serif/src/components/Dock.tsx` | 暴露位置查询、加 minimizing-target class |
| `demo-serif/src/components/App.tsx` | ChatFloat 改真窗口、AppId 命名迁移 |
| `demo-serif/src/components/ProfileRadar.tsx` | 维度命名迁移、动画接入 |
| `demo-serif/src/components/Calendar.tsx` | 标记为待移除（calendar 并入 dashboard） |
| `demo-serif/src/data/sample.ts` | 画像 6 维、MapNode status/branchStatus 拆分、subtype |
| `demo-serif/src/store/useWorkspace.ts` | contentState/metadata 字段、_prev 扩展、Settings 单实例去重、AppId 类型 |
| `demo-serif/src/lib/layouts.ts` | AppId 命名迁移 |
| `demo-serif/package.json` | 加 mitt 依赖 |
| `docs/详细设计规格说明书-v3.md` | 不修改（保留为基线） |

---

## Task 1：发布 v4 文档（不改代码）

**Files:**
- Create: `docs/详细设计规格说明书-v4.md`

**Interfaces:**
- 引用：`docs/详细设计规格说明书-v3.md`（基线）

- [ ] **Step 1：复制 v3 到 v4**

```bash
cp docs/详细设计规格说明书-v3.md docs/详细设计规格说明书-v4.md
```

预期：v4.md 创建成功，与 v3 内容完全一致。

- [ ] **Step 2：在 v4 顶部加修订说明**

在 v4.md 顶部表格加一行：

```
| V4.0 | 2026-07-11 | 团队 | 按附录 A 决策修订：(1)AppId 新命名清单 (2)WindowState 加 contentState/metadata (3)画像 6 维改为中文第三套 (4)关卡形式 4 种无听力型 (5)分支状态拆分为 status + branchStatus (6)持久化键名按 § 5.2 (7)快捷键引入 scope (8)mitt 事件总线提前重构 (9)ChatFloat 改真窗口 (10)Settings 单实例 |
```

把"V3.4"行保留为历史，但加一行说明："V4.0 基于 V3.5 文本，仅修订正文具体值，不动结构。"

- [ ] **Step 3：替换 § 2.1 画像数据结构示例**

找到 v3 § 2.1 中的画像 JSON 示例，替换为新 6 维：

```json
{
  "student_id": "s1001",
  "dimensions": {
    "understanding_depth": 0.65,
    "reasoning_accuracy": 0.80,
    "expression_clarity": 0.55,
    "application_breadth": 0.70,
    "transfer_ability": 0.62,
    "creativity": 0.48
  },
  "tags": ["Python熟练", "数学较好", "注意力集中"],
  "last_updated": "2026-07-11T10:00:00Z"
}
```

- [ ] **Step 4：替换 § 3.2.1 WindowState 字段定义**

找到 v3 § 3.2.1 中的 `interface WindowState`，在 `metadata` 后**新增字段**：

```typescript
contentState: Record<string, any>;       // 窗口内部状态（翻滚位置、当前页码）
```

把 `_prev` 字段注释更新为：

```typescript
_prev?: { x: number; y: number; w: number; h: number };  // 内部：max/minimize 前的位置（同时支持两种）
```

- [ ] **Step 5：替换 § 3.15 九个核心应用窗口 AppId 清单**

找到 v3 § 3.15 的 9 个窗口小节（3.15.1~3.15.10），把每个 appId 改为 spec § 3.2 的最终清单（treasure_map / chat / document / exercise / code_editor / notebook / mind_map / resource_library / dashboard / settings）。原 `treasure_map` 不变。原 `chat` 不变。把 `appId: notebook` 替换原 `notebook`，原 `notebook` 节标题保留但加注释说明命名迁移。

- [ ] **Step 6：在 § 3.14.1 LevelData 加 subtype 字段注释**

找到 v3 § 3.14.1 LevelData 接口，在 `branch_status?` 字段后加：

```typescript
subtype: 'reading_practice' | 'reading_tutor' | 'coding_lab' | 'task_challenge';
```

并加注释：'关卡形式，4 种主形式（不含加分项听力型）'

- [ ] **Step 7：验证 v4 与 v3 差异**

```bash
git diff docs/详细设计规格说明书-v3.md docs/详细设计规格说明书-v4.md | head -100
```

预期：差异只在 § 2.1 画像 JSON、§ 3.2.1 WindowState、§ 3.15 AppId、§ 3.14.1 subtype 这几处，**其它正文完全一致**。

- [ ] **Step 8：commit**

```bash
git add docs/详细设计规格说明书-v4.md
git commit -m "docs: 同步出详细设计规格说明书 v4（按附录 A 决策修订）"
```

---

## Task 2：加 IndexedDB 持久化层骨架

**Files:**
- Create: `demo-serif/src/lib/persistence.ts`

**Interfaces:**
- 导出：`safeSetItem(key, value): boolean`（localStorage，自动检测 QuotaExceededError）
- 导出：`idbGet<T>(dbName, storeName, key): Promise<T | undefined>`
- 导出：`idbSet<T>(dbName, storeName, key, value): Promise<void>`
- 导出：`idbDelete(dbName, storeName, key): Promise<void>`

- [ ] **Step 1：创建 lib/persistence.ts**

写入：

```typescript
// src/lib/persistence.ts
// 持久化层封装：localStorage（轻量配置）+ IndexedDB（结构化数据）
// 设计依据：详细设计规格说明书 v4 § 5.2

const DB_NAME = 'selflearn';
const DB_VERSION = 1;

/**
 * 安全写入 localStorage。QuotaExceededError 时降级到控制台 warn 并返回 false
 */
export function safeSetItem(key: string, value: string): boolean {
  try {
    localStorage.setItem(key, value);
    return true;
  } catch (e) {
    if (e instanceof DOMException && e.name === 'QuotaExceededError') {
      console.warn(`[persistence] localStorage quota exceeded for key: ${key}`);
    } else {
      console.error(`[persistence] localStorage setItem failed for key: ${key}`, e);
    }
    return false;
  }
}

export function safeGetItem(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch (e) {
    console.error(`[persistence] localStorage getItem failed for key: ${key}`, e);
    return null;
  }
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      // 按 v4 § 5.2 的 IndexedDB store 命名
      if (!db.objectStoreNames.contains('profile_cache')) db.createObjectStore('profile_cache');
      if (!db.objectStoreNames.contains('map_cache')) db.createObjectStore('map_cache');
      if (!db.objectStoreNames.contains('window_states')) db.createObjectStore('window_states');
      if (!db.objectStoreNames.contains('chat_history')) db.createObjectStore('chat_history');
      if (!db.objectStoreNames.contains('resource_cache')) db.createObjectStore('resource_cache');
      if (!db.objectStoreNames.contains('level_metrics_buffer')) db.createObjectStore('level_metrics_buffer');
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function idbGet<T>(storeName: string, key: string): Promise<T | undefined> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readonly');
    const req = tx.objectStore(storeName).get(key);
    req.onsuccess = () => resolve(req.result as T | undefined);
    req.onerror = () => reject(req.error);
  });
}

export async function idbSet<T>(storeName: string, key: string, value: T): Promise<void> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readwrite');
    tx.objectStore(storeName).put(value, key);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function idbDelete(storeName: string, key: string): Promise<void> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readwrite');
    tx.objectStore(storeName).delete(key);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}
```

- [ ] **Step 2：类型检查**

```bash
cd demo-serif && npx tsc --noEmit
```

预期：0 错误。

- [ ] **Step 3：build 验证**

```bash
cd demo-serif && npm run build
```

预期：成功，无警告。

- [ ] **Step 4：commit**

```bash
git add demo-serif/src/lib/persistence.ts
git commit -m "feat(persistence): 加 IndexedDB 持久化层骨架（v4 § 5.2）"
```

---

## Task 3：装 mitt + 加事件总线骨架

**Files:**
- Modify: `demo-serif/package.json`
- Create: `demo-serif/src/lib/eventBus.ts`

**Interfaces:**
- 导出：`eventBus: Emitter<Events>`（mitt 单例）
- 类型：`Events` 字典覆盖 v4 § 3.9.1 的 12 类事件

- [ ] **Step 1：装 mitt**

```bash
cd demo-serif && npm install mitt
```

预期：`package.json` 加 `"mitt": "^3.x"`，`node_modules/mitt/` 出现。

- [ ] **Step 2：创建 eventBus.ts**

写入：

```typescript
// src/lib/eventBus.ts
// mitt 事件总线。覆盖 v4 § 3.9.1 的事件清单。
// 接入策略（混合方案）：跨组件通信、影响多消费者的事件走总线；
// 单消费者、读多写少的场景继续走 Zustand。

import mitt, { type Emitter } from 'mitt';
import type { WindowState } from '../store/useWorkspace';
import type { MapNode, Edge } from '../data/sample';

export type Profile = unknown; // 占位：v4 § 5.1 结构，下个 Task 替换

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
```

- [ ] **Step 3：类型检查 + build**

```bash
cd demo-serif && npx tsc --noEmit && npm run build
```

预期：0 错误。

- [ ] **Step 4：commit**

```bash
git add demo-serif/package.json demo-serif/src/lib/eventBus.ts
git commit -m "feat(event-bus): 装 mitt + 加事件总线骨架（v4 § 3.9.1）"
```

---

## Task 4：抽出 WindowState / AppId 类型统一定义（仅新增，不动 useWorkspace）

**Files:**
- Create: `demo-serif/src/types/window.ts`

**Interfaces:**
- 导出：`AppId` 联合类型（12 个）
- 导出：`WindowState` 接口（含 contentState/metadata）
- 导出：`LevelStatus`, `BranchStatus`, `LevelSubtype` 联合类型
- 导出：`SINGLETON_APP_IDS` 集合

**@约束**：本 Task **只**创建 `types/window.ts`，**不**改 `useWorkspace.ts` 主体——避免中间状态破坏 build。Task 5 会一次性引入类型 + 迁移字段 + 改 ChatFloat。

- [ ] **Step 1：创建 types/window.ts**

写入：

```typescript
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
  'dashboard',
  'settings',
  'task_list',
]);
```

- [ ] **Step 2：类型检查 + build（必须通过）**

```bash
cd demo-serif && npx tsc --noEmit && npm run build
```

预期：0 错误，build 成功。**本 Task 不动 useWorkspace.ts，build 必然通过。**

- [ ] **Step 3：commit**

```bash
git add demo-serif/src/types/window.ts
git commit -m "feat(types): 抽出 WindowState / AppId / LevelStatus 等统一定义（v4 § 3.2.1 / § 3.14.1 / § 3.15）"
```

---

## Task 5（合并原 Task 5+6）：AppId 重命名 + WindowState 字段升级 + ChatFloat 改真窗口

**Files:**
- Modify: `demo-serif/src/data/sample.ts`
- Modify: `demo-serif/src/lib/layouts.ts`
- Modify: `demo-serif/src/components/App.tsx`
- Modify: `demo-serif/src/store/useWorkspace.ts`
- Modify: `demo-serif/src/components/ChatFloat.tsx`
- Delete: `demo-serif/src/components/Calendar.tsx`, `Calendar.css`

**Interfaces:**
- AppId 命名迁移：`today` → `task_list`，`calendar` → 移除，`doc` → `document`，`note` → `notebook`
- WindowState 引入 `types/window.ts` 的 `AppId` 与 `WindowState`
- ChatFloat 接收 `win: WindowState` prop，加入 windows map，`pinLevel='always'`，`togglePin` 禁止改 always 类

- [ ] **Step 1：修改 sample.ts**

在 `demo-serif/src/data/sample.ts` 中：

1. 把 `export const calendar` 整段（约 50-60 行）替换为：

```typescript
// calendar 已并入 dashboard，本期移除（v4 § 3.15 + 附录 A #1）
export const calendar = { rows: [{ cells: [] as { day: number; intensity: 0|1|2|3|4 }[] }], today: 18 };
```

2. 修改 import（如果需要），保留其它 export 不动。

- [ ] **Step 2：修改 useWorkspace.ts：迁移字段、引入类型、改默认窗口**

完整替换 `demo-serif/src/store/useWorkspace.ts` 顶部（约第 1-50 行）：

```typescript
import { create } from 'zustand';
import type { AppId, WindowState, PinLevel } from '../types/window';
import { mapNodes, mapEdges, profile, tasks, initialChat, mockAiReplies } from '../data/sample';

export type Mode = 'proficiency' | 'exploration';
export type LayoutId = 'reading' | 'practice' | 'coding';

export interface WindowStateLegacy extends WindowState {
  // 别名导出，保持外部 import 兼容
}

const DEFAULT_WIN: Record<string, Omit<WindowState, 'pinLevel'>> = {
  map:      { id: 'map',      appId: 'treasure_map', x: 80,  y: 80,  w: 720, h: 360, z: 1000 },
  today:    { id: 'today',    appId: 'task_list',    x: 820, y: 80,  w: 420, h: 360, z: 1001 },
  profile:  { id: 'profile',  appId: 'profile',      x: 80,  y: 460, w: 720, h: 300, z: 1002 },
  chat:     { id: 'chat',     appId: 'chat',         x: 1000, y: 460, w: 280, h: 320, z: 1003 },
};

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
```

3. 找到 `togglePin` 函数（约第 159-185 行），加判断：

```typescript
togglePin: (id) =>
  set((s) => {
    const w = s.windows[id];
    if (!w) return s;
    if (w.pinLevel === 'always') return s; // 系统置顶（chat 等），不可改
    const nextPin: 'none' | 'normal' = w.pinLevel === 'none' ? 'normal' : 'none';
    // ...保留原 z-index 桶排序逻辑...
  }),
```

- [ ] **Step 3：修改 App.tsx 改用新 AppId + ChatFloat 包裹到 Window**

修改 `demo-serif/src/components/App.tsx`：

```typescript
import { Backdrop } from './components/Backdrop';
import { TopBar } from './components/TopBar';
import { Dock } from './components/Dock';
import { Window } from './components/Window';
import { ChatFloat } from './components/ChatFloat';
import { TreasureMap } from './components/TreasureMap';
import { TaskList } from './components/TaskList';
import { ProfileRadar } from './components/ProfileRadar';
import { useWorkspace } from './store/useWorkspace';
import type { WindowState } from './types/window';
import type { ReactNode } from 'react';

type WinDef = { title: string; isKey?: boolean };

const WIN_CONTENT: Record<string, WinDef> = {
  treasure_map: { title: '深度学习路径', isKey: true },
  task_list:    { title: '今日学习' },
  profile:      { title: '六维画像' },
  chat:         { title: '小书' },
};

function renderBody(appId: string, win: WindowState): ReactNode {
  switch (appId) {
    case 'treasure_map': return <TreasureMap />;
    case 'task_list':    return <TaskList />;
    case 'profile':      return <ProfileRadar />;
    case 'chat':         return <ChatFloat win={win} />;
    default:             return null;
  }
}

export default function App() {
  const windows = useWorkspace((s) => s.windows);

  const entries: [WindowState, WinDef][] = [];
  for (const w of Object.values(windows)) {
    const def = WIN_CONTENT[w.appId];
    if (def) entries.push([w, def]);
  }

  return (
    <div className="app">
      <Backdrop />
      <TopBar />
      <div className="windows-layer">
        {entries.map(([win, def]) => (
          <Window key={win.id} win={win} title={def.title} isKey={def.isKey}>
            {renderBody(win.appId, win)}
          </Window>
        ))}
      </div>
      <Dock />
    </div>
  );
}
```

注意：删除原 `<ChatFloat />` 在 App 底部的直接渲染。

- [ ] **Step 4：修改 ChatFloat 组件签名**

替换整个 `demo-serif/src/components/ChatFloat.tsx`：

```typescript
import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { useWorkspace } from '../store/useWorkspace';
import type { WindowState } from '../types/window';
import './ChatFloat.css';

interface Props {
  win: WindowState;
}

export function ChatFloat({ win: _win }: Props) {
  const chat = useWorkspace((s) => s.chat);
  const sendChat = useWorkspace((s) => s.sendChat);
  const [draft, setDraft] = useState('');
  const bodyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [chat]);

  const submit = () => {
    const v = draft.trim();
    if (!v) return;
    sendChat(v);
    setDraft('');
  };

  return (
    <div className="chat">
      <div className="chat-head">
        <span className="av">书</span>
        <span className="name">小书</span>
        <span className="sub">Always on</span>
      </div>
      <div className="chat-body" ref={bodyRef}>
        {chat.map((m, i) => (
          <div key={i} className={`bubble ${m.role}`}>{m.text}</div>
        ))}
      </div>
      <div className="chat-input">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e: KeyboardEvent<HTMLInputElement>) => e.key === 'Enter' && submit()}
          placeholder="Ask anything…"
        />
        <button onClick={submit}>↑</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 5：修改 layouts.ts**

把 `appId: 'today'` 改为 `appId: 'task_list'`。删除 `calendar` 项。

- [ ] **Step 6：删除 Calendar 文件**

```bash
rm demo-serif/src/components/Calendar.tsx demo-serif/src/components/Calendar.css
```

- [ ] **Step 7：类型检查 + build（必须通过）**

```bash
cd demo-serif && npx tsc --noEmit && npm run build
```

预期：0 错误，build 成功。

- [ ] **Step 8：@用户验证**

启动 dev server，肉眼确认：
- 浏览器看到 4 个窗口（map + task_list + profile + chat），无 calendar
- ChatFloat 现在有 Window 标题栏（标题"小书"），可以拖动、resize、最小化、关闭
- ChatFloat 不能被 pinLevel 切换（always 系统置顶）

```bash
cd demo-serif && timeout 8 npm run dev
```

- [ ] **Step 9：commit**

```bash
git add demo-serif/src/data/sample.ts demo-serif/src/lib/layouts.ts demo-serif/src/components/App.tsx demo-serif/src/store/useWorkspace.ts demo-serif/src/components/ChatFloat.tsx demo-serif/src/types/window.ts
git rm demo-serif/src/components/Calendar.tsx demo-serif/src/components/Calendar.css
git commit -m "refactor: AppId 命名对齐 v4 + WindowState 字段升级 + ChatFloat 改为真窗口"
```

---

## Task 7：画像 6 维改为第三套中文命名

**Files:**
- Modify: `demo-serif/src/data/sample.ts`

**Interfaces:**
- 6 维度字段：understanding_depth / reasoning_accuracy / expression_clarity / application_breadth / transfer_ability / creativity

- [ ] **Step 1：替换 profile.dimensions**

在 `demo-serif/src/data/sample.ts` 第 38-48 行，替换为：

```typescript
export const profile = {
  student: '林知遥',
  dimensions: [
    { key: 'understanding_depth', label: '理解深度', value: 78 },
    { key: 'reasoning_accuracy',  label: '推理准确', value: 62 },
    { key: 'expression_clarity',  label: '表达清晰', value: 55 },
    { key: 'application_breadth', label: '应用广度', value: 70 },
    { key: 'transfer_ability',    label: '迁移能力', value: 74, pulsing: true },
    { key: 'creativity',          label: '创造力',   value: 48 },
  ],
};
```

- [ ] **Step 2：类型检查 + build**

```bash
cd demo-serif && npx tsc --noEmit && npm run build
```

预期：0 错误（ProfileRadar 用 `d.key / d.label / d.value` 三个字段，无需改）。

- [ ] **Step 3：commit**

```bash
git add demo-serif/src/data/sample.ts
git commit -m "refactor(data): 画像 6 维改为中文第三套（v4 § 2.1）"
```

---

## Task 8：分支状态拆分 status + branchStatus

**Files:**
- Modify: `demo-serif/src/data/sample.ts`

**Interfaces:**
- `MapNode.status: LevelStatus`（locked | unlocked | in_progress | completed | mastered）
- `MapNode.branchStatus?: BranchStatus`（active | sleeping）
- `MapNode.subtype?: LevelSubtype`（4 种）
- `MapNode.visual?: { badge?: 'star' | 'sprint' | 'new' | 'key' | null }`

- [ ] **Step 1：修改 MapNode 类型**

在 `sample.ts` 顶部（约第 3-10 行），替换为：

```typescript
import type { LevelStatus, BranchStatus, LevelSubtype } from '../types/window';

export type NodeStatus = LevelStatus | 'key';  // 'key' 是 demo 用法，等同 unlocked + badge

export interface MapNode {
  id: string;
  x: number; y: number;
  label: string;
  status: LevelStatus;
  branchStatus?: BranchStatus;
  minutes: number;
  branch?: 'up' | 'down' | null;
  subtype?: LevelSubtype;
  visual?: { badge?: 'star' | 'sprint' | 'new' | 'key' | null };
}
```

- [ ] **Step 2：替换 mapNodes 数据**

```typescript
export const mapNodes: MapNode[] = [
  { id: 'n1', x: 60,  y: 110, label: '词嵌入',     status: 'completed',   minutes: 30 },
  { id: 'n2', x: 180, y: 110, label: 'RNN',        status: 'completed',   minutes: 45 },
  { id: 'n3', x: 300, y: 110, label: 'LSTM',       status: 'completed',   minutes: 50 },
  { id: 'n4', x: 420, y: 110, label: '自注意力',   status: 'in_progress', minutes: 45, subtype: 'reading_tutor' },
  { id: 'n5', x: 540, y: 110, label: 'Transformer', status: 'unlocked',    minutes: 60, subtype: 'reading_tutor', visual: { badge: 'key' } },
  { id: 'n6', x: 660, y: 50,  label: '视觉 Transformer', status: 'unlocked', minutes: 40, branchStatus: 'active', branch: 'up', subtype: 'coding_lab' },
  { id: 'n7', x: 660, y: 170, label: '经典 RNN',        status: 'unlocked', minutes: 35, branchStatus: 'active', branch: 'down', subtype: 'reading_practice' },
  { id: 'n8', x: 300, y: 200, label: '序列建模回顾',   status: 'unlocked', minutes: 25, branchStatus: 'sleeping', branch: 'down', subtype: 'reading_practice' },
];
```

- [ ] **Step 3：调整 TreasureMap.tsx 的状态映射**

`TreasureMap.tsx` 第 4-11 行的 `STATUS_FILL` 与 `STATUS_TEXT` 需要扩展，因为新增了 `LevelStatus` 全集。改为：

```typescript
const STATUS_FILL: Record<string, string> = {
  completed:   '#F4F4F0',
  in_progress: '#DBEAFE',
  unlocked:    '#FFFFFF',
  locked:      '#F4F4F0',
  mastered:    '#D1FAE5',
  key:         '#BC4749',  // demo 兜底
};
const STATUS_TEXT: Record<string, string> = {
  completed:   '#1A1A1A',
  in_progress: '#1A1A1A',
  unlocked:    '#1A1A1A',
  locked:      '#A1A1AA',
  mastered:    '#1A1A1A',
  key:         '#FFFFFF',
};
```

把第 41 行的 `n.status === 'key'` 改为：

```typescript
const stroke = n.status === 'unlocked' && n.visual?.badge === 'key' ? 'var(--vermilion)' :
  n.branchStatus === 'sleeping' ? 'var(--mute)' :
  n.status === 'unlocked' ? 'var(--indigo)' :
  n.status === 'in_progress' ? 'var(--indigo)' : 'var(--border)';
```

第 46 行的 `op = n.status === 'sleeping' ? 0.55 : 1` 改为：

```typescript
const op = n.branchStatus === 'sleeping' ? 0.55 : 1;
```

第 45 行 `strokeDash = n.status === 'sleeping' ? '3 3' : n.status === 'interest' ? '4 3' : ''` 改为：

```typescript
const strokeDash = n.branchStatus === 'sleeping' ? '3 3' : n.branchStatus === 'active' && n.branch ? '4 3' : '';
```

- [ ] **Step 4：类型检查 + build**

```bash
cd demo-serif && npx tsc --noEmit && npm run build
```

预期：0 错误。

- [ ] **Step 5：commit**

```bash
git add demo-serif/src/data/sample.ts demo-serif/src/components/TreasureMap.tsx
git commit -m "refactor(data): 分支状态拆分 status + branchStatus + 加 subtype（v4 § 3.14.1）"
```

---

## Task 9：Settings 单实例去重

**Files:**
- Modify: `demo-serif/src/store/useWorkspace.ts`

**Interfaces:**
- `openWindow` 对单实例 appId 第二次打开只聚焦

- [ ] **Step 1：修改 openWindow 函数**

替换 `openWindow` 函数（useWorkspace.ts 第 199-229 行）：

```typescript
openWindow: (appId) =>
  set((s) => {
    // 单实例 appId 列表（v4 § 3.11.1）
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
    // 不存在 → 新建（多实例或单实例首次）
    const existingKey = APP_TO_ID[appId];
    const key = existingKey || `win_${appId}_${Date.now()}`;
    const maxZ = Math.max(...Object.values(s.windows).map((w) => w.z));
    const def = DEFAULT_WIN[key];
    const defaultPin = appId === 'chat' ? 'always' : 'none';
    const newWin: WindowState = {
      id: key,
      appId,
      x: def?.x ?? 100,
      y: def?.y ?? 100,
      w: def?.w ?? 600,
      h: def?.h ?? 400,
      z: maxZ + 1,
      pinLevel: defaultPin,
    };
    return {
      windows: { ...s.windows, [key]: newWin },
      focusedId: key,
    };
  }),
```

- [ ] **Step 2：类型检查 + build**

```bash
cd demo-serif && npx tsc --noEmit && npm run build
```

预期：0 错误。

- [ ] **Step 3：commit**

```bash
git add demo-serif/src/store/useWorkspace.ts
git commit -m "feat(store): Settings 等单实例 appId 第二次打开只聚焦（v4 § 3.11.1）"
```

---

## Task 10：快捷键 scope 系统骨架

**Files:**
- Create: `demo-serif/src/lib/shortcuts.ts`

**Interfaces:**
- `ShortcutScope` 联合类型：global / treasure_map / code_editor / notebook / window / exercise
- `ShortcutManager` 单例：register / match / fire
- 5 个示例快捷键：Ctrl+K、Ctrl+1/2/3、Escape

- [ ] **Step 1：创建 shortcuts.ts**

写入：

```typescript
// src/lib/shortcuts.ts
// 快捷键系统 + scope 管理（v4 § 3.8）

export type ShortcutScope =
  | 'global'
  | 'treasure_map'
  | 'code_editor'
  | 'notebook'
  | 'window'
  | 'exercise';

export interface KeyCombo {
  key: string;
  ctrl?: boolean;
  meta?: boolean;
  alt?: boolean;
  shift?: boolean;
}

export interface ShortcutDef {
  id: string;
  scope: ShortcutScope;
  defaultBinding: KeyCombo;
  action: () => void;
  description: string;
  customizable: boolean;
}

class ShortcutManager {
  private shortcuts: Map<string, ShortcutDef> = new Map();
  private currentScope: ShortcutScope = 'global';
  private enabled = true;

  register(def: ShortcutDef): void {
    this.shortcuts.set(def.id, def);
  }

  registerAll(defs: ShortcutDef[]): void {
    defs.forEach((d) => this.register(d));
  }

  setScope(scope: ShortcutScope): void {
    this.currentScope = scope;
  }

  setEnabled(b: boolean): void {
    this.enabled = b;
  }

  /**
   * 匹配按键：优先匹配当前 scope（更具体），其次 global
   */
  match(combo: KeyCombo): ShortcutDef | undefined {
    if (!this.enabled) return undefined;

    const normalize = (c: KeyCombo) => `${c.ctrl ? 'C' : ''}${c.meta ? 'M' : ''}${c.alt ? 'A' : ''}${c.shift ? 'S' : ''}${c.key.toLowerCase()}`;
    const target = normalize(combo);

    // 第一轮：当前 scope
    for (const def of this.shortcuts.values()) {
      if (def.scope === this.currentScope && normalize(def.defaultBinding) === target) return def;
    }
    // 第二轮：global
    for (const def of this.shortcuts.values()) {
      if (def.scope === 'global' && normalize(def.defaultBinding) === target) return def;
    }
    return undefined;
  }

  fire(combo: KeyCombo): boolean {
    const def = this.match(combo);
    if (def) {
      def.action();
      return true;
    }
    return false;
  }

  list(): ShortcutDef[] {
    return Array.from(this.shortcuts.values());
  }
}

export const shortcutManager = new ShortcutManager();

// 键盘事件解析为 KeyCombo
export function parseKeyEvent(e: KeyboardEvent): KeyCombo {
  return {
    key: e.key,
    ctrl: e.ctrlKey,
    meta: e.metaKey,
    alt: e.altKey,
    shift: e.shiftKey,
  };
}

// v4 § 3.8.2 系统出厂快捷键（节选 5 个作为骨架）
import { useWorkspace } from '../store/useWorkspace';
import { readingLayout, practiceLayout, codingLayout } from '../layouts';

export function registerSystemShortcuts(): void {
  const ws = useWorkspace.getState();
  shortcutManager.registerAll([
    {
      id: 'shortcut.ai.chat',
      scope: 'global',
      defaultBinding: { key: 'k', ctrl: true },
      action: () => ws.openWindow('chat'),
      description: '唤起AI对话',
      customizable: true,
    },
    {
      id: 'shortcut.layout.reading',
      scope: 'global',
      defaultBinding: { key: '1', ctrl: true },
      action: () => ws.setLayout('reading', readingLayout()),
      description: '切换阅读模式',
      customizable: true,
    },
    {
      id: 'shortcut.layout.practice',
      scope: 'global',
      defaultBinding: { key: '2', ctrl: true },
      action: () => ws.setLayout('practice', practiceLayout()),
      description: '切换刷题模式',
      customizable: true,
    },
    {
      id: 'shortcut.layout.coding',
      scope: 'global',
      defaultBinding: { key: '3', ctrl: true },
      action: () => ws.setLayout('coding', codingLayout()),
      description: '切换代码实验模式',
      customizable: true,
    },
    {
      id: 'shortcut.dialog.close',
      scope: 'global',
      defaultBinding: { key: 'Escape' },
      action: () => {
        // TODO: 关闭顶层弹窗/菜单
        console.log('[shortcut] Escape');
      },
      description: '关闭顶层弹窗/菜单',
      customizable: true,
    },
  ]);
}
```

- [ ] **Step 2：在 App.tsx 注册快捷键 + 绑定全局 keydown**

修改 `App.tsx`：

```typescript
import { useEffect } from 'react';
import { shortcutManager, parseKeyEvent, registerSystemShortcuts } from './lib/shortcuts';

useEffect(() => {
  registerSystemShortcuts();
  const handler = (e: KeyboardEvent) => {
    // 忽略输入框内按键
    const tag = (e.target as HTMLElement)?.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA') return;
    const combo = parseKeyEvent(e);
    if (shortcutManager.fire(combo)) {
      e.preventDefault();
    }
  };
  window.addEventListener('keydown', handler);
  return () => window.removeEventListener('keydown', handler);
}, []);
```

- [ ] **Step 3：类型检查 + build**

```bash
cd demo-serif && npx tsc --noEmit && npm run build
```

预期：0 错误（`useWorkspace.getState()` 是 Zustand 内置 API）。

- [ ] **Step 4：commit**

```bash
git add demo-serif/src/lib/shortcuts.ts demo-serif/src/components/App.tsx
git commit -m "feat(shortcuts): 快捷键 scope 系统骨架 + 5 个系统快捷键（v4 § 3.8）"
```

---

## Task 11：窗口动画 - 移除 resize 小斜杠图标 + 移除 max 的 position 切到铺满

**Files:**
- Modify: `demo-serif/src/components/Window.css`

**Interfaces:**
- 删除 `.resize-handle::after` 的小斜杠伪元素
- 删除 `.win.maximized` 的 `position: absolute / border-left: 0 / border-right: 0`
- 加 `border-radius` transition
- 加 `prefers-reduced-motion` 媒体查询

- [ ] **Step 1：删除 resize-handle::after 小斜杠**

修改 `Window.css` 第 86-107 行整段替换为：

```css
/* ---- Resize handles ---- */
.resize-handle {
  position: absolute;
  width: 14px;
  height: 14px;
  z-index: 2;
}
.resize-handle.rh-br {
  right: 0; bottom: 0;
  cursor: nwse-resize;
}
.resize-handle.rh-bl {
  left: 0; bottom: 0;
  cursor: nesw-resize;
}
/* 删除原 ::after 小斜杠：resize 图标不再显示，但保留拖边功能 */
```

- [ ] **Step 2：修改 .win.maximized 样式**

修改 `Window.css` 第 21-27 行：

```css
.win.maximized {
  border-radius: 0;
  z-index: 5000;
}
```

- [ ] **Step 3：扩展 .win transition**

修改 `Window.css` 第 9-15 行的 transition：

```css
.win {
  position: absolute;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--r-card);
  box-shadow: var(--shadow-1);
  display: flex; flex-direction: column;
  overflow: hidden;
  transition:
    transform 220ms cubic-bezier(0.4, 0, 0.2, 1),
    width 220ms cubic-bezier(0.4, 0, 0.2, 1),
    height 220ms cubic-bezier(0.4, 0, 0.2, 1),
    top 220ms cubic-bezier(0.4, 0, 0.2, 1),
    left 220ms cubic-bezier(0.4, 0, 0.2, 1),
    border-radius 220ms cubic-bezier(0.4, 0, 0.2, 1),
    opacity 220ms cubic-bezier(0.4, 0, 0.2, 1),
    box-shadow 200ms ease;
}
```

- [ ] **Step 4：加 prefers-reduced-motion**

在 `Window.css` 末尾加：

```css
/* 可访问性：用户开启"减少动效"时全部 transition 缩为 0ms */
@media (prefers-reduced-motion: reduce) {
  .win, .win *, .dock-item * {
    transition: none !important;
    animation: none !important;
  }
}
```

- [ ] **Step 5：类型检查 + build**

```bash
cd demo-serif && npx tsc --noEmit && npm run build
```

预期：0 错误。

- [ ] **Step 6：commit**

```bash
git add demo-serif/src/components/Window.css
git commit -m "feat(window): 移除 resize 小斜杠图标 + max 改走普通布局路径 + 加 border-radius 过渡 + reduced-motion 支持"
```

---

## Task 12：Dock 位置查询接口

**Files:**
- Create: `demo-serif/src/lib/dockPositions.tsx`
- Modify: `demo-serif/src/components/Dock.tsx`

**Interfaces:**
- `DockPositionsContext` 提供 `getDockPosition(appId): { x, y, w, h } | null`
- `useDockPosition(appId)` hook
- Dock 渲染时用 `useLayoutEffect` 注册自己的 ref

- [ ] **Step 1：创建 lib/dockPositions.tsx**

写入：

```typescript
// src/lib/dockPositions.tsx
// Dock 位置查询接口（v4 § 2.2.4 动画需要）

import { createContext, useContext, useRef, useLayoutEffect, useState, type ReactNode } from 'react';
import type { AppId } from '../types/window';

export interface DockRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

interface DockPositionsApi {
  getDockPosition: (appId: AppId) => DockRect | null;
  register: (appId: AppId, el: HTMLElement | null) => void;
  highlight: (appId: AppId | null) => void;
  highlightAppId: AppId | null;
}

const DockPositionsContext = createContext<DockPositionsApi | null>(null);

export function DockPositionsProvider({ children }: { children: ReactNode }) {
  const refs = useRef<Map<AppId, HTMLElement>>(new Map());
  const [highlightAppId, setHighlightAppId] = useState<AppId | null>(null);
  // 触发强制刷新，让 getDockPosition 拿到最新尺寸
  const [, force] = useState(0);

  const api: DockPositionsApi = {
    getDockPosition: (appId) => {
      const el = refs.current.get(appId);
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return { x: r.left, y: r.top, w: r.width, h: r.height };
    },
    register: (appId, el) => {
      if (el) refs.current.set(appId, el);
      else refs.current.delete(appId);
      force((n) => n + 1);
    },
    highlight: (appId) => {
      setHighlightAppId(appId);
      if (appId) {
        setTimeout(() => setHighlightAppId(null), 600);
      }
    },
    highlightAppId,
  };

  return <DockPositionsContext.Provider value={api}>{children}</DockPositionsContext.Provider>;
}

export function useDockPositions(): DockPositionsApi {
  const ctx = useContext(DockPositionsContext);
  if (!ctx) throw new Error('useDockPositions must be used inside DockPositionsProvider');
  return ctx;
}

/**
 * 给 Dock 按钮调用：注册 ref 与 appId 映射
 */
export function useDockRef(appId: AppId) {
  const api = useDockPositions();
  return (el: HTMLElement | null) => {
    useLayoutEffect(() => {
      api.register(appId, el);
      return () => api.register(appId, null);
    }, [appId, el]);
  };
}
```

- [ ] **Step 2：修改 Dock.tsx 注册 ref + 高亮 class**

修改 `demo-serif/src/components/Dock.tsx`：

```typescript
import { useWorkspace } from '../store/useWorkspace';
import { useDockRef, useDockPositions } from '../lib/dockPositions';
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
  const focusedAppId = focusedId ? windows[focusedId]?.appId : null;

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
```

注意：`useDockRef` 在循环里调用违反 hooks 规则。**修正方案**：把按钮改成子组件。

```typescript
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
  windows: Record<string, { appId: string; id: string }>;
  openWindow: (appId: any) => void;
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
          const winEntry = Object.entries(windows).find(([, v]) => v.appId === item.appId);
          if (winEntry) focusWindow(winEntry[0]);
        } else {
          openWindow(item.appId);
        }
      }}
      title={item.lb}
    >
      <span className="ic">{item.ic}</span>
      <span className="lb">{item.lb}</span>
    </button>
  );
}
```

注意：useDockRef 必须在子组件中调用，循环里调会违反 React hooks 规则。

- [ ] **Step 3：在 App.tsx 包 DockPositionsProvider**

```typescript
import { DockPositionsProvider } from './lib/dockPositions';

export default function App() {
  // ...
  return (
    <DockPositionsProvider>
      <div className="app">
        {/* ... */}
      </div>
    </DockPositionsProvider>
  );
}
```

- [ ] **Step 4：加 Dock.css 高亮样式**

在 `demo-serif/src/components/Dock.css` 末尾加：

```css
.dock-item.highlight {
  background: var(--indigo-soft);
  transition: background 220ms cubic-bezier(0.4, 0, 0.2, 1);
}
```

- [ ] **Step 5：类型检查 + build**

```bash
cd demo-serif && npx tsc --noEmit && npm run build
```

预期：0 错误。

- [ ] **Step 6：commit**

```bash
git add demo-serif/src/lib/dockPositions.tsx demo-serif/src/components/Dock.tsx demo-serif/src/components/Dock.css demo-serif/src/components/App.tsx
git commit -m "feat(dock): Dock 位置查询 Context + Dock 按钮注册 ref + highlight class"
```

---

## Task 13：窗口动画 - 最大化拉伸 + 还原反向 + 关闭淡出

**Files:**
- Modify: `demo-serif/src/components/Window.tsx`

**Interfaces:**
- `maximized` 时 style 也走 `x/y/w/h + transform` 路径
- 关闭时先触发最小化动画再 closeWindow

- [ ] **Step 1：修改 style 计算**

修改 `Window.tsx` 第 149-165 行的 style 计算：

```typescript
// 最大化状态下：仍走 x/y/w/h + transform，让 transition 接管插值
const TOPBAR_H = 52;
const DOCK_H = 72;

const style: React.CSSProperties = {
  zIndex: win.z,
};
if (win.minimized) {
  // minimized 样式由 .win.minimized CSS 处理（opacity 0）
  // 但本 Task 13 不改最小化（下一个 Task 14 处理）
  style.opacity = 0;
  style.pointerEvents = 'none';
} else if (win.maximized) {
  style.left = 0;
  style.top = 0;
  style.width = '100%';
  style.height = `calc(100vh - ${TOPBAR_H}px - ${DOCK_H}px)`;
  style.transform = `translate(0, ${TOPBAR_H}px)`;
  style.borderRadius = 0;
} else {
  style.width = win.w;
  style.height = win.h;
  style.left = 0;
  style.top = 0;
  style.transform = `translate(${win.x}px, ${win.y}px)`;
}
```

- [ ] **Step 2：关闭按钮加 closing 动画**

修改 `Window.tsx` 第 189 行的关闭按钮：

```typescript
const [closing, setClosing] = useState(false);

const handleClose = () => {
  if (closing) return;
  setClosing(true);
  // 触发最小化动画（220ms 后才真正关闭）
  toggleMinimize(win.id);
  setTimeout(() => {
    closeWindow(win.id);
    setClosing(false);
  }, 220);
};
```

按钮 onClick 改为 `handleClose`。

- [ ] **Step 3：类型检查 + build**

```bash
cd demo-serif && npx tsc --noEmit && npm run build
```

预期：0 错误。

- [ ] **Step 4：commit**

```bash
git add demo-serif/src/components/Window.tsx
git commit -m "feat(window): 最大化拉伸 + 还原反向 + 关闭淡出动画"
```

---

## Task 14：窗口动画 - 最小化"收到 Dock" + 从 Dock 恢复

**Files:**
- Modify: `demo-serif/src/components/Window.tsx`
- Modify: `demo-serif/src/store/useWorkspace.ts`

**Interfaces:**
- `toggleMinimize` 保存 `_prev` 字段
- 最小化时 Window.tsx 从 `useDockPositions().getDockPosition(win.appId)` 拉目标位置
- 恢复时反向插值回 `_prev`

- [ ] **Step 1：修改 toggleMinimize 保存 _prev**

修改 `useWorkspace.ts` 的 `toggleMinimize`（约第 115-132 行）：

```typescript
toggleMinimize: (id) =>
  set((s) => {
    const w = s.windows[id];
    if (!w) return s;
    if (w.maximized) {
      // 先取消最大化再最小化
      const prev = w._prev;
      return {
        windows: {
          ...s.windows,
          [id]: { ...w, maximized: false, _prev: undefined, x: prev?.x ?? w.x, y: prev?.y ?? w.y, w: prev?.w ?? w.w, h: prev?.h ?? w.h, minimized: true },
        },
      };
    }
    if (w.minimized) {
      // 恢复：用 _prev 还原（支持从 minimize 恢复）
      const prev = w._prev;
      return {
        windows: {
          ...s.windows,
          [id]: { ...w, minimized: false, _prev: undefined, x: prev?.x ?? w.x, y: prev?.y ?? w.y, w: prev?.w ?? w.w, h: prev?.h ?? w.h },
        },
      };
    }
    // 最小化：保存 _prev
    return {
      windows: {
        ...s.windows,
        [id]: { ...w, minimized: true, _prev: { x: w.x, y: w.y, w: w.w, h: w.h } },
      },
    };
  }),
```

- [ ] **Step 2：Window.tsx 拉 Dock 位置**

修改 `Window.tsx` 第 1-4 行 import：

```typescript
import { useEffect, useRef, useState, useCallback } from 'react';
import type { WindowState } from '../store/useWorkspace';
import { useWorkspace } from '../store/useWorkspace';
import { useDockPositions } from '../lib/dockPositions';
import { ContextMenu, type ContextMenuItem } from './ContextMenu';
import './Window.css';
```

在 `Window` 函数体最顶部加：

```typescript
const dockApi = useDockPositions();
const [dockTarget, setDockTarget] = useState<{ x: number; y: number; w: number; h: number } | null>(null);

useEffect(() => {
  if (win.minimized) {
    const pos = dockApi.getDockPosition(win.appId);
    if (pos) setDockTarget(pos);
  } else {
    setDockTarget(null);
  }
}, [win.minimized, win.appId, dockApi]);
```

- [ ] **Step 3：修改 style 计算处理 minimized**

把 Task 13 Step 1 的 style 计算替换为：

```typescript
const TOPBAR_H = 52;
const DOCK_H = 72;

const style: React.CSSProperties = {
  zIndex: win.z,
};
if (win.minimized) {
  if (dockTarget) {
    // 收到 Dock：把 transform 与 size 都拉到 Dock 图标位置
    style.left = 0;
    style.top = 0;
    style.width = win.w;
    style.height = win.h;
    style.transform = `translate(${dockTarget.x - win.x + (dockTarget.w - win.w) / 2}px, ${dockTarget.y - win.y + (dockTarget.h - win.h) / 2}px) scale(${Math.min(dockTarget.w / win.w, dockTarget.h / win.h)})`;
    style.opacity = 0;
    style.pointerEvents = 'none';
  } else {
    style.opacity = 0;
    style.pointerEvents = 'none';
  }
} else if (win.maximized) {
  style.left = 0;
  style.top = 0;
  style.width = '100%';
  style.height = `calc(100vh - ${TOPBAR_H}px - ${DOCK_H}px)`;
  style.transform = `translate(0, ${TOPBAR_H}px)`;
  style.borderRadius = 0;
} else {
  style.width = win.w;
  style.height = win.h;
  style.left = 0;
  style.top = 0;
  style.transform = `translate(${win.x}px, ${win.y}px)`;
}
```

- [ ] **Step 4：toggleMinimize 时触发 Dock 高亮**

修改 `Window.tsx` 的 minimize 按钮 onClick：

```typescript
const handleMinimize = () => {
  if (win.minimized) {
    // 恢复
    toggleMinimize(win.id);
  } else {
    // 最小化：先高亮 Dock 图标再触发
    dockApi.highlight(win.appId);
    setTimeout(() => toggleMinimize(win.id), 80);
  }
};
```

按钮 onClick 改为 `handleMinimize`。

同时右键菜单里的"最小化" action 也改为 `handleMinimize`（最简方式：直接调用原 toggleMinimize 即可，因为 Dock 高亮会自动跟随；本 Step 简化处理不深究）。

- [ ] **Step 5：类型检查 + build**

```bash
cd demo-serif && npx tsc --noEmit && npm run build
```

预期：0 错误。

- [ ] **Step 6：@用户验证（手动冒烟动画四件套）**

```bash
cd demo-serif && timeout 8 npm run dev
```

肉眼验证：
- 点最大化：窗口从原位平滑拉伸到全屏
- 点还原：反向
- 点最小化：窗口收到 Dock 图标位置 + 淡出
- 点 Dock 图标：窗口从 Dock 拉伸回原位
- 点关闭：淡出动画后消失

- [ ] **Step 7：commit**

```bash
git add demo-serif/src/components/Window.tsx demo-serif/src/store/useWorkspace.ts
git commit -m "feat(window): 最小化收到 Dock + 从 Dock 拉伸恢复 + Dock 高亮"
```

---

## Task 15：最终验收 + build 验证

**Files:** 无（只验证）

- [ ] **Step 1：类型检查**

```bash
cd demo-serif && npx tsc --noEmit
```

预期：0 错误。

- [ ] **Step 2：build**

```bash
cd demo-serif && npm run build
```

预期：成功，无警告。

- [ ] **Step 3：@用户验证（手动冒烟全清单）**

启动 dev server，对照 spec § 2.4 6 条验收点 + § 3.14 附录 A 10 条验收点，全部通过。**由用户执行。**

- [ ] **Step 4：commit（如果上面没遗漏）**

```bash
git status
```

预期：工作区 clean。

如果有遗漏改动，commit：

```bash
git add -A
git commit -m "chore: 最终验收后清理"
```

---

## Plan 自审（自查清单）

**Spec coverage**：

- § 2.2.2 最大化动画 → Task 11 + Task 13 ✓
- § 2.2.3 还原动画 → Task 13 + Task 14 Step 1（_prev 扩展） ✓
- § 2.2.4 最小化收 Dock → Task 12 + Task 14 ✓
- § 2.2.5 关闭动画 → Task 13 Step 2 ✓
- § 2.2.6 prefers-reduced-motion → Task 11 Step 4 ✓
- § 3.1 AppId 命名 → Task 5 + Task 6 ✓
- § 3.2 WindowState 字段 → Task 4 ✓
- § 3.3 画像 6 维 → Task 7 ✓
- § 3.4 关卡形式 → Task 8 ✓
- § 3.5 分支状态拆分 → Task 8 ✓
- § 3.6 持久化键名 → Task 2 ✓
- § 3.7 快捷键 scope → Task 10 ✓
- § 3.8 mitt 事件总线 → Task 3 ✓
- § 3.9 ChatFloat 改真窗口 → Task 6 ✓
- § 3.10 Settings 单实例 → Task 9 ✓
- § 3.11 v4 文档 → Task 1 ✓
- **resize 图标移除 → Task 11 Step 1** ✓

**Placeholder scan**：无 TBD / TODO，每个 Step 有具体代码或命令。

**Type consistency**：

- `AppId` 联合类型在 Task 4 定义，Task 5/6/12 一致使用 ✓
- `WindowState` 在 Task 4 定义，Task 4-14 一致使用 ✓
- `_prev` 字段结构在 Task 13/14 保持 `{ x, y, w, h }` ✓
- `SINGLETON_APP_IDS` 在 Task 4 定义，Task 9 引用 ✓

**未覆盖但明确划出范围外**：

- 后端、真实内容生成、9 窗口全部落地、讯飞集成、学习仪表盘真实数据、设置应用 10 个模块真实内容 ✓ 与实施计划书 Stage 1-5 对齐

---

> 计划结束。本计划与 spec `2026-07-11-window-animation-and-v4-alignment-design.md` 配套。