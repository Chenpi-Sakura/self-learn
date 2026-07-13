# Spec：窗口 max/min 动画过渡 + 附录 A 决策对齐 v4 设计文档

| 文档版本 | 修订日期 | 修订人 | 修订说明 |
| --- | --- | --- | --- |
| V1.0 | 2026-07-11 | 团队 | 初稿。包含两个子项目：(1) 窗口最大化/最小化/还原/关闭四类过渡动画；(2) 附录 A 10 个不一致点决策的实施 + 同步发布《详细设计规格说明书 v4》 |
| V1.1 | 2026-07-13 | **Stage 4 T1 重命名注**：本文档描述的工程目录原文为 `demo-serif/`，Stage 4 T1 已重命名为 `frontend/`。下方所有 `demo-serif/` 字串保留原貌以保持历史准确性。 |

---

## **1. 背景与目标**

### 1.1 触发原因

2026-07-11 完成《实施计划书 V1.0》后，发现两个未解决项：

1. **窗口动画缺失**：当前 demo-serif 在最大化/最小化窗口时**没有动画过渡**——其他场景（拖动、resize）已有 220ms cubic-bezier 过渡，唯独 max/min 缺。
2. **附录 A 10 个不一致点未收口**：实施计划书 § 2.3 列出了 demo-serif 与 v3 详细设计文档的 10 个不一致点，需要逐个决策并同步更新文档。

### 1.2 目标

#### 子项目 A：窗口动画

让所有窗口状态变更（最大化、还原、最小化、恢复、关闭）都有 220ms 平滑过渡，且支持 `prefers-reduced-motion` 可访问性偏好。

#### 子项目 B：附录 A 决策 + v4 文档

- 解决 10 个不一致点，给出最终决策
- 复制《详细设计规格说明书 v3》生成 v4，**只改正文具体值，不动文档结构**
- 按 v4 实施 demo-serif 的代码改动，分 7 个 commit 渐进推进

### 1.3 范围

**包含**：

- Window.tsx + Window.css + Dock.tsx（最小改动）+ useWorkspace（`_prev` 字段扩展）
- 持久化层（IndexedDB 封装 + 接入 store）
- mitt 事件总线（接入关键组件）
- WindowState 字段重构（contentState/metadata）
- AppId 命名迁移（today → task_list，profile → profile，calendar 移除）
- 画像 6 维度（中文第三套）
- 关卡 4 种形式 subtype 字段
- 分支状态拆分为 `status` + `branchStatus`
- ChatFloat 改为真窗口（加入 windows map）
- 快捷键 scope 系统骨架
- Settings 单实例去重
- 同步出 v4 设计文档

**不包含**（明确划出范围外）：

- 后端实现（多智能体、API、数据层）—— 实施计划书 Stage 2 才动
- 真实内容生成（讲义/习题/导图/代码）—— Stage 4 才动
- 9 窗口全部落地 —— Stage 4
- 讯飞集成 —— Stage 5

---

## **2. 子项目 A：窗口动画设计**

### 2.1 现状分析

**已存在的动画**（Window.css 第 9-15 行）：

```css
.win {
  transition:
    transform 220ms cubic-bezier(0.4, 0, 0.2, 1),
    width 220ms cubic-bezier(0.4, 0, 0.2, 1),
    height 220ms cubic-bezier(0.4, 0, 0.2, 1),
    top 220ms cubic-bezier(0.4, 0, 0.2, 1),
    left 220ms cubic-bezier(0.4, 0, 0.2, 1),
    box-shadow 200ms ease;
}
```

**已存在的过渡路径**：

- 拖拽：`transition: none`（拖动期间关闭，松手后**没有惯性动画**）
- resize：右下/左下把手 `transition: none`
- 聚焦：box-shadow 200ms ease

**缺失的过渡路径**：

| 操作 | 当前行为 | 问题 |
| --- | --- | --- |
| 最大化 | `.win.maximized { position: absolute; border-radius: 0; border-left/right: 0 }` 切换 + `width: undefined` + `top/left/right/bottom: 0` | width 跳变，border 跳变，圆角跳变。无插值起点 |
| 还原（max→normal） | 反向同上 | 同上 |
| 最小化 | `.win.minimized { opacity: 0; pointer-events: none }` | **只是淡出凭空消失**，没有"收到 Dock"的运动路径 |
| 恢复（min→normal） | 反向淡入 | 没有"从 Dock 拉伸回来"的运动路径 |
| 关闭 | `closeWindow` 直接从 store 删除，React 卸载元素 | 无任何动画 |

### 2.2 设计方案

#### 2.2.1 动画规范

| 项 | 值 |
| --- | --- |
| 时长 | 220ms |
| 缓动 | `cubic-bezier(0.4, 0, 0.2, 1)` |
| 涉及属性 | transform / width / height / top / left / border-radius / opacity / box-shadow |
| 可访问性 | `@media (prefers-reduced-motion: reduce)` 下所有 transition 缩为 0ms |

#### 2.2.2 最大化动画

**核心**：让 `.win.maximized` **仍然走普通的 x/y/w/h + transform 路径**，而不是切到 position: absolute 铺满。

具体改动：

1. `Window.css` 中删除 `.win.maximized` 的 `position: absolute / border-left: 0 / border-right: 0`，只保留 `border-radius: 0` 和必要的样式覆盖
2. `.win.maximized` 加 `transition: ... border-radius 220ms ...`，让圆角平滑变方
3. `Window.tsx` 的 `style` 计算逻辑：当 `maximized && !minimized` 时：
   - `x = 0, y = 0`
   - `w = window.innerWidth, h = window.innerHeight - topbarHeight - dockHeight`
   - 不使用 top/left/right/bottom 铺满

这样 React 重新渲染时只是把 width/height/transform 数值切到新值，CSS transition 自动接管插值。

#### 2.2.3 还原动画（max→normal）

通过 `_prev` 字段保存最大化前的 `x/y/w/h`（**当前 store 已有 `_prev`，但只用于 maximized，需要扩展为同时支持 minimize**）。

切换 `maximized: false` 时套回 `_prev` 即可。CSS transition 反向插值。

#### 2.2.4 最小化"收到 Dock"

**关键观察**：Dock 当前不是真窗口。要"收到 Dock"，需要给 Dock 加上**目标位置查询接口**。

实现路径：

1. `Dock.tsx` 暴露**获取某 appId 对应图标位置**的接口
   - 方案：用 React Context 或 ref 集合
   - 每个 Dock 图标按钮渲染时把自己的 DOM ref 注册到一个 `dockPositions: Map<string, DOMRect>` 中
   - 提供 `getDockPosition(appId)` 函数
2. `Window.tsx` 在 `minimized` 状态下，**不卸载元素**，而是把 `transform/width/height/opacity` 都改到 Dock 目标位置
   - `transform: translate(dockX - winX, dockY - winY) scale(0.05)`
   - `width: dockW, height: dockH`（或 0）
   - `opacity: 0`
3. CSS：`transition` 增加 `transform, opacity`（width/height 已在）
4. 从 Dock 恢复时**反向插值**——store 里通过 `_prev` 保存最小化前的 x/y/w/h

**Dock 高亮**：Dock 中对应 appId 图标在动画期间加 `.dock-item.minimizing-target` class（短暂高亮：背景变 indigo-soft 100ms → 淡出 220ms）。

#### 2.2.5 关闭动画

复用最小化动画路径：

1. 点击 × 时，先触发"收到 Dock"动画（220ms）
2. 动画结束后调用 `closeWindow`（从 store 删除）

实现：用一个临时 local state `closing: boolean` —— 触发时同时设 `minimized: true` 并开始计时，220ms 后才真正 close。

#### 2.2.6 可访问性

CSS 顶端加：

```css
@media (prefers-reduced-motion: reduce) {
  .win, .win *, .dock-item * { transition: none !important; animation: none !important; }
}
```

### 2.3 文件改动清单

| 文件 | 改动 |
| --- | --- |
| `src/components/Window.css` | 删 `.win.maximized` 的 `position/border`；加 `border-radius` transition；加 `prefers-reduced-motion` 媒体查询；**删除 `.resize-handle::after` 的小斜杠伪元素（视觉移除左下/右下 resize 图标），保留 handle 区域本身与 cursor 提示以维持拖边 resize 功能** |
| `src/components/Window.tsx` | `style` 计算改为：maximized 时也用 x/y/w/h；minimized 时从 Dock 拉目标位置；closing 临时 state |
| `src/components/Dock.tsx` | 暴露 `getDockPosition(appId)`；加 `minimizing-target` class；提供 Context |
| `src/store/useWorkspace.ts` | 扩展 `_prev` 字段同时支持 minimize；`toggleMinimize` 改为保存 `_prev` |
| `src/lib/dockPositions.ts` (新) | Context + hook `useDockPosition(appId)` |

### 2.4 验收点

- [ ] 点最大化按钮：窗口从原位平滑拉伸到全屏，圆角 8px → 0，220ms
- [ ] 点还原：反向收缩回原位
- [ ] 点最小化：窗口缩小+淡出，移动到 Dock 中对应 appId 图标位置，Dock 图标轻微高亮
- [ ] 点 Dock 图标恢复：反向动画回到原位（位置不丢失——通过 `_prev` 保存）
- [ ] 点关闭：复用最小化动画 + 之后从 store 删除
- [ ] 系统设置开启"减少动效"时，所有动画 0ms 直接跳变
- [ ] 动画期间拖动/点击其他窗口不卡顿
- [ ] 窗口左下角和右下角不再显示 resize 小斜杠图标，但拖边 resize 功能仍可用

---

## **3. 子项目 B：附录 A 决策对齐 v4**

### 3.1 10 项决策汇总

| # | 决策点 | 决议 |
| --- | --- | --- |
| 1 | AppId 命名 | 用更合适的命名（具体清单见 § 3.2） |
| 2 | WindowState 字段 | 兼收：嵌套 `{position, size}` 对外 + 扁平 `x/y/w/h` 内部 + 加 `contentState/metadata` |
| 3 | 画像 6 维 | 第三套（中文、中性、跨场景）：理解深度 / 推理准确 / 表达清晰 / 应用广度 / 迁移能力 / 创造力 |
| 4 | 关卡形式 subtype | 4 种：`reading_practice / reading_tutor / coding_lab / task_challenge` |
| 5 | 分支状态枚举 | 按设计文档拆分：`status: LevelStatus` + `branchStatus?: BranchStatus` |
| 6 | 持久化键名 | 按设计文档 § 5.2（IndexedDB 5 类） |
| 7 | 快捷键作用域 | 引入 scope：global / treasure_map / code_editor / notebook / window / exercise |
| 8 | 消息总线 mitt | 提前重构，仅关键场景使用（map.updated / profile.updated / level.ready / notification） |
| 9 | ChatFloat | 改为真窗口，pinLevel='always'，加入 windows map，参与 z-index 桶排序 |
| 10 | Settings 单实例 | 单实例（同 appId 第二次打开聚焦现有） |

### 3.2 附录 A 第 1 项：AppId 新命名清单

v4 设计文档 § 3.15 将规定的最终 AppId：

| AppId | 唯一性 | 入口 | 用途 |
| --- | --- | --- | --- |
| `treasure_map` | 单实例 | 初始化自动打开 | 藏宝图 |
| `chat` | 多实例 | Ctrl+K / Dock AI 图标 | AI 对话悬浮窗 |
| `document` | 多实例 | 右键节点 / Dock | 讲义阅读器 |
| `exercise` | 多实例 | 右键节点 / Dock | 习题练习面板 |
| `code_editor` | 多实例 | 实践型关卡 / Dock | 代码编辑器 + 运行终端 |
| `notebook` | 单实例 | Dock | 笔记本/批注工具 |
| `mind_map` | 多实例 | 右键节点 / Dock | 思维导图查看器 |
| `resource_library` | 单实例 | Dock | 我的资源库 |
| `dashboard` | 单实例 | Dock | 学习仪表盘 |
| `settings` | 单实例 | Ctrl+, / Dock | 设置应用 |
| `task_list` | 单实例 | Dock | 今日学习（任务列表） |
| `profile` | 多实例（按关卡） | Dock | 学生画像雷达卡 |

**说明**：

- demo-serif 当前的 `today` 改名为 `task_list`
- demo-serif 当前的 `profile` 保留并扩展
- demo-serif 当前的 `calendar` **移除**（并入 dashboard）
- demo-serif 当前的 `doc` 改名为 `document`
- demo-serif 当前的 `note` 改名为 `notebook`

### 3.3 附录 A 第 2 项：WindowState 字段重构

**对外 API**（v4 § 3.2.1）：

```typescript
interface WindowState {
  id: string;                              // 唯一 ID: 'window_doc_001'
  appId: AppId;                            // 应用标识
  title: string;                           // 窗口标题
  position: { x: number; y: number };      // 嵌套对象（对外）
  size: { width: number; height: number }; // 嵌套对象（对外）
  zIndex: number;
  minimized: boolean;
  maximized: boolean;
  contentState: Record<string, any>;       // 窗口内部状态（翻滚位置、当前页码）
  metadata: {
    levelId?: string;
    resourceId?: string;
    transient?: boolean;
  };
  pinLevel: 'none' | 'normal' | 'always';
  _prev?: { position: {x,y}; size: {width,height} }; // 内部：max/minimize 前的位置（扩展为同时支持两种）
}
```

**内部存储**：Zustand store 内部为性能考虑，**仍保留扁平字段** `x/y/w/h`，但 getter/setter 对外暴露 `position/size` 嵌套对象。

实现：通过 Proxy 或者在每个组件读取时转换。最简单方案：**保留扁平字段为 source of truth，文档示例写嵌套对象**。组件层用 `win.x` 直接读，写操作通过 action 改扁平字段。这样类型上能匹配两种写法，且改动最小。

具体落地：demo-serif 现有字段保留 `x/y/w/h/z/minimized/maximized/pinLevel/_prev`，**新增** `contentState/metadata` 两个字段。`_prev` 扩展为 `{x, y, w, h}` 同时支持 maximize 和 minimize。

### 3.4 附录 A 第 3 项：画像 6 维新命名

v4 § 2.1 数据结构示例替换为：

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

中文标签映射：

| 字段 key | 中文标签 | 含义 |
| --- | --- | --- |
| `understanding_depth` | 理解深度 | 对概念本质的把握程度 |
| `reasoning_accuracy` | 推理准确 | 逻辑推导的正确率 |
| `expression_clarity` | 表达清晰 | 表述与输出条理性 |
| `application_breadth` | 应用广度 | 跨场景迁移与综合 |
| `transfer_ability` | 迁移能力 | 把已学用到新场景 |
| `creativity` | 创造力 | 提出新颖解法的能力 |

demo-serif `sample.ts` 的 `profile.dimensions` 同步改为这套标签。

### 3.5 附录 A 第 4 项：关卡形式 4 种

v4 § 3.14.1 LevelData 已定义 `subtype: 'reading_practice' | 'reading_tutor' | 'coding_lab' | 'task_challenge'`，无需大改文档。demo-serif 的 LevelData 接口补 `subtype` 字段（当前缺失）。

### 3.6 附录 A 第 5 项：分支状态拆分

v4 § 3.14.1 已定义：

```typescript
type LevelStatus = 'locked' | 'unlocked' | 'in_progress' | 'completed' | 'mastered';
type BranchStatus = 'active' | 'sleeping';  // 仅 interest 节点
```

demo-serif `MapNode` 改为：

```typescript
interface MapNode {
  id: string;
  x: number; y: number;
  label: string;
  status: LevelStatus;          // 节点通用状态
  branchStatus?: BranchStatus;  // 仅 interest 节点有
  minutes: number;
  branch?: 'up' | 'down' | null;
  subtype?: LevelSubtype;       // 关卡形式（4 种）
}
```

demo-serif 当前 demo 数据的 status（如 `completed / current / key / interest / sleeping`）需要拆分映射：
- `completed` → `status: 'completed'`
- `current` → `status: 'in_progress'`
- `key` → `status: 'unlocked', visual.badge: 'key'`
- `locked` → `status: 'locked'`
- `interest` → `status: 'unlocked', branchStatus: 'active', branch: 'up'/'down'`
- `sleeping` → `status: 'unlocked', branchStatus: 'sleeping'`

新增 `visual` 字段用于徽章。

### 3.7 附录 A 第 6 项：持久化键名

按 v4 § 5.2 实施：

| 存储键 | 位置 | 内容 |
| --- | --- | --- |
| `user_preferences` | localStorage | 用户偏好（轻量） |
| `shortcut_prefs` | localStorage | 快捷键用户覆盖 |
| `ui_pins` | localStorage | 窗口置顶状态（轻量枚举） |
| `profile_cache` | IndexedDB | 最新画像快照 |
| `map_cache_{course_id}` | IndexedDB | 藏宝图数据 |
| `window_states_{layout_id}` | IndexedDB | 窗口位置/尺寸/层级快照 |
| `chat_history_{session_id}` | IndexedDB | AI 对话历史 |
| `resource_cache_{level_id}` | IndexedDB | 关卡资源内容 |
| `level_metrics_buffer` | IndexedDB | 关卡完成指标（断网缓存） |

实现：`src/lib/persistence.ts` 提供 `safeSetItem(localStorage)`、`idbGet/Set/Delete(IndexedDB)` 两个工具。所有 store action 后挂持久化钩子。

### 3.8 附录 A 第 7 项：快捷键 scope

v4 § 3.8.3 实施：

```typescript
type ShortcutScope = 'global' | 'treasure_map' | 'code_editor' | 'notebook' | 'window' | 'exercise';

interface SystemShortcut {
  id: string;
  defaultBinding: KeyCombo;
  scope: ShortcutScope;          // 新增字段
  action: string;
  customizable: boolean;
}
```

事件处理时按"更具体优先"取用：聚焦窗口的 scope 比 global 优先。

`src/lib/shortcuts.ts` 提供 `useShortcut(id)` hook 和 `ShortcutManager` 单例。

### 3.9 附录 A 第 8 项：mitt 事件总线

`src/lib/eventBus.ts`：

```typescript
import mitt from 'mitt';
type Events = {
  'window.opened': WindowState;
  'window.closed': { windowId: string };
  'window.focused': { windowId: string };
  'layout.changed': LayoutSnapshot;
  'level.started': { levelId: string };
  'level.progress': { levelId: string; item: string; percent: number };
  'level.ready': { levelId: string; resources: any[] };
  'level.completed': { levelId: string; metrics: LevelCompletionMetrics };
  'profile.updated': Profile;
  'map.updated': { nodes: MapNode[]; edges: Edge[] };
  'mode.changed': 'exploration' | 'proficiency';
  'resource.bound': { fileId: string; levelId: string };
};
export const eventBus = mitt<Events>();
```

接入策略（混合方案）：
- **走事件总线**：跨组件通信、影响多消费者的场景（map.updated → 藏宝图重绘；profile.updated → 画像卡片动画 + 仪表盘 + 演变图表；level.ready → 窗口填充；notification → Toast）
- **走 Zustand**：单消费者、读多写少的场景（窗口位置、表单输入值）

需要先安装 mitt：`npm install mitt`。

### 3.10 附录 A 第 9 项：ChatFloat 改真窗口

删除 `App.tsx` 里的 `<ChatFloat />` 直接渲染，改为：

1. `ChatFloat` 组件签名改为 `Window` 的子组件（接收 `win: WindowState` prop）
2. `App.tsx` 改为从 `windows` map 读取 `chat` 类型的窗口并用 `<Window>` 包裹
3. `useWorkspace` 初始化时给 `chat` 创建默认窗口（如果不存在）
4. Dock 的 AI 图标调用 `openWindow('chat')` 即可开/关/聚焦
5. `pinLevel: 'always'` 是 chat 的默认值，**用户不能改为 normal/none**

### 3.11 附录 A 第 10 项：Settings 单实例

`useWorkspace.openWindow` 增加去重逻辑：

```typescript
openWindow: (appId) => set((s) => {
  // 单实例 appId 列表
  const SINGLETON_APPS = new Set(['treasure_map', 'notebook', 'resource_library', 'dashboard', 'settings', 'task_list']);
  if (SINGLETON_APPS.has(appId)) {
    const existing = Object.values(s.windows).find(w => w.appId === appId);
    if (existing) {
      // 已存在 → 聚焦
      const maxZ = Math.max(...Object.values(s.windows).map(w => w.z));
      return { windows: { ...s.windows, [existing.id]: { ...existing, minimized: false, z: maxZ + 1 } }, focusedId: existing.id };
    }
  }
  // 多实例或不存在 → 走原逻辑
  ...
});
```

### 3.12 v4 文档改动原则

- **不动结构**：目录、章节号、引用关系全部保留
- **只改正文里的具体值**：AppId 清单（§ 3.15）、字段名（§ 3.2.1）、画像维度示例（§ 2.1）、subtype 枚举值（§ 3.14.1）
- **加修订说明**：v4.0 修订说明（按 v3.4 / v3.5 的修订说明格式），列出 10 项差异
- **不动章节**：详细业务逻辑、Agent 设计、API、数据库全部沿用 v3
- **不重复**：保留 v3 的大部分，只覆盖差异点

### 3.13 实施分批

| 批次 | 内容 | commit 信息 | 验证 |
| --- | --- | --- | --- |
| 1 | v4 文档发布（不动代码） | `docs: 同步出详细设计规格说明书 v4（按附录 A 决策修订）` | `git diff v3 v4` 只在指定位置有差异 |
| 2 | 数据层（持久化 + 事件总线） | `feat: 加 IndexedDB 持久化层 + mitt 事件总线` | 刷新后窗口位置恢复；map.updated 触发 |
| 3 | Store 重构（contentState/metadata/branchStatus） | `refactor(store): WindowState 字段对齐 v4 + 加 contentState/metadata` | 类型检查通过，已有功能不退化 |
| 4 | AppId 命名迁移 + ChatFloat 改真窗口 | `refactor: AppId 命名对齐 v4 + ChatFloat 改为真窗口` | Dock/Dock 数据全部能开 |
| 5 | 画像维度 + 关卡形式 + 分支状态 | `refactor(data): 画像 6 维 + 关卡 4 形式 + 分支状态拆分对齐 v4` | sample.ts 类型与新枚举匹配 |
| 6 | 快捷键 scope + Settings 单实例 | `feat(shortcuts): 快捷键 scope 系统 + Settings 单实例去重` | 18 个快捷键能跑通 5 个即可 |
| 7 | **窗口动画** | `feat(window): 最大化拉伸 + 最小化收 Dock + 还原反向 + 关闭淡出动画` | 6 条验收清单全过 |

### 3.14 验收点

- [ ] `docs/详细设计规格说明书-v4.md` 存在，且只修订了 10 个决策点附近
- [ ] demo-serif 类型检查通过（`npx tsc --noEmit`）
- [ ] 持久化：刷新页面后窗口位置/选中状态/画像数据全部恢复
- [ ] 事件总线：map.updated/profile.updated 能跨组件触发
- [ ] ChatFloat 改为真窗口：Dock 点击 AI 图标能开/关，能置顶/还原
- [ ] Settings 单实例：Ctrl+, 第二次按只聚焦，不开第二个
- [ ] **窗口动画 6 条验收点全过**
- [ ] 全部改动通过 `npm run build` 无警告

---

## **4. 风险与缓解**

| 风险 | 概率 | 影响 | 缓解 |
| --- | --- | --- | --- |
| 7 批重构引入回归 | 中 | 已有功能失效 | 每批 commit 后 `npm run dev` + 手动冒烟；每批 ≤ 200 行净增删 |
| v4 文档局部修订写歪 | 中 | 改了不该改的地方 | 用 `diff v3 v4` 验证只动了 10 个点附近 |
| Dock 位置查询时机不对 | 中 | 收到 Dock 动画位置错 | 用 `useLayoutEffect` 而非 `useEffect`，或 ResizeObserver |
| store 重构影响所有组件 | 中 | 编译失败 | 用 grep 全量搜索 `win.x / win.y / win.w / win.h` 确认 |
| 持久化层兼容性 | 低 | Safari 隐私模式失败 | 检测 + 降级到内存（带 Toast 提示） |
| mitt 类型与事件清单不匹配 | 低 | 类型检查失败 | 严格定义 `Events` 字典 |

---

## **5. 不在本期范围（明确划出）**

- 后端实现 —— 实施计划书 Stage 2
- 真实内容生成 —— Stage 4
- 9 窗口全部落地 —— Stage 4
- 讯飞集成 —— Stage 5
- 学习仪表盘真实数据 —— Stage 4
- 设置应用 10 个模块的真实内容 —— Stage 1 已有骨架，本期不深入

---

## **附录 A：附录 A 决策登记表（最终版）**

| # | 决策点 | 最终决策 | 决策人 | 日期 |
| --- | --- | --- | --- | --- |
| 1 | AppId 命名 | 见 § 3.2 | 团队 | 2026-07-11 |
| 2 | WindowState 字段 | 见 § 3.3 | 团队 | 2026-07-11 |
| 3 | 画像 6 维 | 见 § 3.4 | 团队 | 2026-07-11 |
| 4 | 关卡形式 | 4 种（无听力型） | 团队 | 2026-07-11 |
| 5 | 分支状态枚举 | 拆分 status + branchStatus | 团队 | 2026-07-11 |
| 6 | 持久化键名 | 按 v4 § 5.2 | 团队 | 2026-07-11 |
| 7 | 快捷键作用域 | 引入 scope | 团队 | 2026-07-11 |
| 8 | 消息总线 mitt | 提前重构（混合方案） | 团队 | 2026-07-11 |
| 9 | ChatFloat | 改为真窗口 | 团队 | 2026-07-11 |
| 10 | Settings 单实例 | 单实例去重 | 团队 | 2026-07-11 |

---

> 文档结束。本 spec 与《详细设计规格说明书 v4》《实施计划书 V1.0》配套使用。