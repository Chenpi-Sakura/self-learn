# Demo 设计规格 · Notion × UKIYO · 学习工作站（衬线版）

| 文档版本 | 日期 | 说明 |
|---|---|---|
| V1.0 | 2026-07-11 | 初稿 |

---

## 1. 背景与目标

用户已经在 `D:\Projects\SelfLearn\demo/` 下完成了一个**制图院蓝图风格**的 React demo（深墨 + 米白纸 + 朱印 + IBM Plex + 罗盘节点）。在此基础上用户希望做第二个 demo，**专门验证「Notion 骨架 + UKIYO 色彩 + 全衬线字体」**这条方向是否更适合长期落地。

**目的**：产出独立的 Vite + React 工程 `demo-serif/`，与原 `demo/` 并存可对比。聚焦**视觉效果 + 轻交互**，不接 API。

**为什么独立工程**（用户已确认）：便于横向对比风格方向，且原 `demo/` 的制图院蓝图风是另一条路。

---

## 2. 美学基线

### 2.1 骨架（Notion 风）

- 中性白底 + 1px 灰边框 + **8px 圆角**（卡片）/ 4px（按钮、tag）/ 999px（pill）
- 顶部栏 / Dock：**白底 + `rgba(255,255,255,0.85)` + `backdrop-filter: blur(20px)`**
- 卡片阴影：`0 1px 2px rgba(27,59,111,0.04)`（用靛蓝阴影替代纯黑，更有书卷气）
- 间距栅格：`4 / 8 / 12 / 16 / 24 / 32 / 48`
- 图标描边：1.5px（衬线字体环境里更协调）
- 主色调：**靛蓝 `#1B3B6F`**（UKIYO 原色，替代 Notion 蓝 `#2563EB`）

### 2.2 强调色（UKIYO 双色）

| 角色 | 色值 | 用途 |
|---|---|---|
| 靛蓝 | `#1B3B6F` | 主强调：选中态、当前节点、链接、强调按钮 |
| 朱红 | `#BC4749` | 关键节点、印章、「今日」标记、危险动作 |
| 米白纸 | `#F7F5EF` | 桌面底（比卡片略深一档） |
| 卡片底 | `#FFFFFF` | 浮窗、卡片 |
| 边框 | `#E4E4E0` | 1px 唯一档（暖灰调） |
| 次级文字 | `#6B6B70` | 标签、说明 |
| 墨字 | `#1A1A1A` | 正文 |

### 2.3 字体（全衬线）

**本地字体文件**（位于 `D:\Projects\SelfLearn\fonts/`，需复制到 `demo-serif/public/fonts/`）：

- **FlyFlowerSong**（飞扬宋，14MB OTF/TTF）—— 中文衬线
- **HedvigLettersSerif**（125KB OTF/TTF）—— 拉丁字符 / 数字

加载方式（`src/styles/fonts.css`）：

```css
@font-face {
  font-family: 'FlyFlower';
  src: url('/fonts/FlyFlowerSong-OTF.otf') format('opentype'),
       url('/fonts/FlyFlowerSong-TTF.ttf') format('truetype');
  font-display: swap;
  unicode-range: U+4E00-9FFF;  /* 仅中文 */
}
@font-face {
  font-family: 'Hedvig';
  src: url('/fonts/HedvigLettersSerif-Regular.otf') format('opentype'),
       url('/fonts/HedvigLettersSerif-Regular.ttf') format('truetype');
  font-display: swap;
}
:root {
  --font-serif-cn: 'FlyFlower', 'Songti SC', 'STSong', serif;
  --font-serif-en: 'Hedvig', 'Iowan Old Style', 'Georgia', serif;
}
body { font-family: var(--font-serif-cn), var(--font-serif-en); }
```

**回退**：浏览器不支持时 → 系统 `Songti SC`（macOS）/ `STSong`（Windows）→ 通用 `serif`。

**数字处理**：因为 Hedvig 是衬线字体，**数字也走 Hedvig**（贯彻全衬线美学），不再单独配 JetBrains Mono。

### 2.4 几何与节奏

- 圆角：`8px` 卡片 / `4px` 按钮 / `999px` pill 头像
- 边框：`1px solid var(--border)` 唯一档
- 阴影：仅卡片一层极轻靛蓝阴影，hover 时加深到 `0 2px 8px rgba(27,59,111,0.08)`
- 间距栅格：`8 / 12 / 16 / 24 / 32 / 48`

---

## 3. 桌面工作台结构

整体是**类桌面系统**形态：多个可独立拖动的浮窗 + 顶部栏 + Dock + AI 浮窗，**不是单页文档站**。

```
┌─ 桌面层 (米白底 + 极淡纸张纹) ───────────────────────────────────┐
│                                                                   │
│  ┌─ TopBar (h=44px, fixed, blur 白) ─────────────────────────┐   │
│  │ ◆ SelfLearn  │ Map · Today · Resources · Profile │ ⌘K  M.  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─ Window: 藏宝图 (x=80 y=100 w=580 h=420, 可拖) ─────────┐    │
│  │ ⋯⋯  深度学习路径                  [—][□][×]              │    │
│  │ ┌──────────────────────────────────────┐                 │    │
│  │ │   SVG 节点网络 (朱红/靛蓝)           │                 │    │
│  │ └──────────────────────────────────────┘                 │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─ Window: 今日 (x=720 y=100 w=460 h=420) ────────────────┐    │
│  │ ⋯⋯  今日学习                       [—][□][×]              │    │
│  │  □ 讲解 Attention 机制                                   │    │
│  │  □ 习题 1.2: Self-Attention                              │    │
│  │  □ 笔记: Q/K/V 三元组                                    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─ Window: 学习画像 (x=80 y=560 w=580 h=320) ──────────────┐    │
│  │ ⋯⋯  六维画像                         [—][□][×]             │    │
│  │  ┌─ 雷达图 (靛蓝) ─┐  理解 78  推理 62 ...                │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─ Window: 日历 (x=720 y=560 w=460 h=320) ─────────────────┐    │
│  │ ⋯⋯  本月打卡                         [—][□][×]             │    │
│  │  7×6 月历 + ░▒▓█ 靛蓝色阶热力                              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─ ChatFloat: AI (右下角, fixed, z=9999) ──────────────────┐    │
│  │  书  小书 · Always on                                      │    │
│  │  [气泡对话...]                                              │    │
│  │  [Ask anything…                                   ↑]       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─ Dock (bottom-center, pill, blur 白, 64px) ───────────────┐    │
│  │  9 图标 + 衬线短标签 (Map/AI/Doc/Ex/Code/Note/Mind/Res/   │    │
│  │   Dash)                                                    │    │
│  └─────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

### 3.1 桌面背景（Backdrop）

- 米白 `#F7F5EF` 底
- 极淡靛蓝细网格（4% 不透明），20px 间距
- 左下角淡淡的抽象山形 SVG 装饰（呼应藏宝图与宣纸）

### 3.2 顶部栏 TopBar

- 高 44px，`rgba(255,255,255,0.85)` + `backdrop-filter: blur(20px)`，底 1px 边框
- 左：◆ logo + 站点名
- 中：Map · Today · Resources · Profile 导航（衬线短标签）
- 右：⌘K 搜索 + 用户头像

### 3.3 模式切换 ModeToggle（顶部栏内）

- 🎯 精通 / 🔭 探索 两段切换
- 选中段：靛蓝填充 + 米白文字
- 滑动指示器用 framer-motion `layoutId` 实现

### 3.4 布局图标 LayoutIcons（顶部栏内）

- 📖 阅读 / ✏️ 习题 / 💻 代码 三个图标
- 选中态：靛蓝边框 + 浅靛蓝底
- 点击触发 4 个浮窗的位置/尺寸过渡

### 3.5 浮窗系统 Window

通用 `Window.tsx`：

- 标题栏：拖动区 + ⋯ 菜单图标 + 窗口名 + [—][□][×]
- 内容区：占位高度由子组件决定
- 用 framer-motion `drag` 实现拖动，仅在标题栏响应
- z-index：默认 1000-5000，聚焦时 +10
- 边界约束：窗口至少保留标题栏在屏幕可见范围

### 3.6 3 套窗口布局预设

| 布局 | 藏宝图 | 今日 | 画像 | 日历 |
|---|---|---|---|---|
| 📖 阅读 | 左上 (580×420) | 右上 (460×420) | 左下 (580×320) | 右下 (460×320) |
| ✏️ 习题 | 左上缩 (380×280) | 居中放大 (640×500) | 左下 (380×320) | 右下 (380×320) |
| 💻 代码 | 左上缩 (380×280) | 右上 (460×280) | 左下 (380×320) | 隐藏 (最小化) |

切换时用 framer-motion 的 `layoutId` 让 4 个 Window 共享过渡动画（300ms spring）。

### 3.7 藏宝图（TreasureMap）

SVG 节点网络：

- 主轴从左到右 5 个核心节点：词嵌入 → RNN → LSTM → **自注意力**（当前，靛蓝）→ Transformer（关键，朱红）
- 上方挂 2 个兴趣分支（视觉 Transformer、经典 RNN，虚线连接，60% 透明）
- 下方挂 1 个休眠分支（细虚线边框 + 灰色 50% 透明 + ⌒ 标记）
- 节点形状：圆角矩形 80×60
  - 当前：靛蓝填充 + 米白文字 + 靛蓝脉冲外圈
  - 关键：朱红填充 + 米白文字 + 朱红 1.5px 虚线边框
  - 已完成：浅绿底 + 墨字 + ✓
  - 未解锁：浅灰底 + 灰字 + 🔒
- 连线：主线 1.5px 实线 + 兴趣分支 1px 虚线 + 休眠分支 0.8px 点线

### 3.8 学习画像（ProfileRadar）

- 6 维度：理解 / 推理 / 表达 / 应用 / 迁移 / 创造
- 雷达图：靛蓝填充 + 靛蓝 1.5px 描边
- 右侧 6 条进度条，数字衬线字体
- 「迁移」维度每 4s 在 73-76 之间脉动 + 旁注「+12% 月环比」

### 3.9 日历（Calendar）

- 7×6 紧凑月历
- 单元格用 ░ / ▒ / ▓ / █ 四档密度字符，颜色是靛蓝色阶
- 今日：朱红描边 + 实心填充
- hover → tooltip 气泡显示「X 月 Y 日 耗时 X 分钟」

### 3.10 任务列表（TaskList）

- Notion 风 checkbox + 衬线标题
- 已完成：浅靛蓝底 + ✓ + 删除线
- 进行中：靛蓝填充 checkbox

### 3.11 讲义 / 习题 / 笔记 内容

- 讲义：衬线大字标题 + 段落 + 代码块（衬线字体）+ 重点高亮（朱红下划线）
- 习题：题号 + 衬线题干 + 选项列表（衬线）+ 提交按钮
- 笔记：双栏（左侧标题列表，右侧富文本）

### 3.12 AI 浮窗 ChatFloat

- 右下角固定，宽 360px，z-index 9999
- 头部：靛蓝圆形头像 + 小书名 + 「Always on」副标题
- 对话区：AI 气泡（米白底 + 靛蓝边） + 用户气泡（靛蓝底 + 米白字）
- 输入框：底部一行，圆角输入 + ↑ 圆形提交按钮（朱红）

### 3.13 Dock

- 底部居中 pill，高 64px
- 白底 + blur + 8px 圆角 + 1px 边框
- 9 个图标 + 衬线短标签（hover 显示 tooltip）
- 激活态：靛蓝底色

---

## 4. 轻交互清单（明确范围）

### 4.1 必须做（视觉+轻交互）

- 节点 hover → 微缩放 1.05 + 边框变朱红
- 窗口标题栏拖动 → 浮窗跟随移动（framer-motion `drag`）
- 3 个布局图标点击 → 4 个浮窗位置/大小 300ms 过渡
- ModeToggle 切换 → 指示器滑动 + 当前模式文字颜色变化
- Dock 图标点击 → 激活态切换（视觉反馈）
- AI 浮窗输入框打字 → 回车加用户气泡 + 500ms 后加假 AI 回复气泡
- 顶部栏导航 hover → 文字颜色平滑过渡到靛蓝

### 4.2 明确不做

- 真实 AI 流式输出（用假回复 `"这是一条模拟回复"`）
- localStorage 持久化（刷新即重置）
- 真实文件上传/OCR
- 真实键盘快捷键系统（不响应快捷键，只展示标签）
- 多窗口层级精细计算（用简单 z-index 数组）
- 突击模式、布局自定义保存长按 2s 流程
- 右键菜单、命令面板
- 移动端响应式（PC only，1440×900 起步）

---

## 5. 技术栈

| 项 | 选择 | 说明 |
|---|---|---|
| 构建 | Vite 5 | 与原 demo 一致 |
| 框架 | React 18 + TypeScript | 强类型、与原 demo 一致 |
| 状态 | Zustand | 单一 store，扁平结构 |
| 动画 | framer-motion | 窗口拖拽 + 布局过渡 + 节点 hover |
| 样式 | CSS Modules / 单文件 CSS | 不用 Tailwind，避免和 Notion 主题色冲突 |
| 字体 | 本地 OTF/TTF @font-face | 见 2.3 |
| 端口 | 5174 | 原 demo 用 5173，避免冲突 |

### 5.1 数据结构

```typescript
// Zustand store 关键字段
type WorkspaceState = {
  mode: 'proficiency' | 'exploration';
  layout: 'reading' | 'practice' | 'coding';
  windows: Record<string, WindowState>;
  nodes: MapNode[];
  edges: Edge[];
  profile: { dimensions: { understanding: number; reasoning: number; ... } };
  calendar: CalendarCell[][];
  tasks: Task[];
  chatMessages: { role: 'user' | 'ai'; text: string }[];
};

interface WindowState {
  id: string;
  appId: 'treasure_map' | 'today' | 'profile' | 'calendar' | 'chat';
  position: { x: number; y: number };
  size: { width: number; height: number };
  zIndex: number;
}
```

### 5.2 关键依赖

```json
{
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "framer-motion": "^11.0.0",
    "zustand": "^4.5.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.5.0",
    "vite": "^5.4.0"
  }
}
```

---

## 6. 文件结构

```
D:\Projects\SelfLearn\demo-serif\
├── package.json
├── vite.config.ts                  (port 5174)
├── tsconfig.json
├── tsconfig.node.json
├── index.html
├── README.md
├── public/
│   └── fonts/                      ← 拷贝自 D:\Projects\SelfLearn\fonts\
│       ├── FlyFlowerSong-OTF.otf
│       ├── FlyFlowerSong-TTF.ttf
│       ├── HedvigLettersSerif-Regular.otf
│       └── HedvigLettersSerif-Regular.ttf
└── src/
    ├── main.tsx
    ├── App.tsx                     顶层：Backdrop + TopBar + 浮窗区 + Dock + ChatFloat
    ├── styles/
    │   ├── tokens.css              色板、字体、间距、阴影、圆角
    │   ├── fonts.css               @font-face + unicode-range
    │   └── globals.css             reset + body 字体栈 + 桌面底纹
    ├── components/
    │   ├── Backdrop.tsx            桌面底
    │   ├── TopBar.tsx              顶部栏
    │   ├── ModeToggle.tsx          精通/探索 切换
    │   ├── LayoutIcons.tsx         阅读/习题/代码 图标
    │   ├── Window.tsx              通用浮窗（拖动）
    │   ├── TreasureMap.tsx         藏宝图窗口内容
    │   ├── ProfileRadar.tsx        六维画像
    │   ├── Calendar.tsx            月历 + 热力
    │   ├── TaskList.tsx            今日任务
    │   ├── DocContent.tsx          讲义内容
    │   ├── ExerciseContent.tsx     习题内容
    │   ├── NoteContent.tsx         笔记内容
    │   ├── ChatFloat.tsx           AI 浮窗
    │   └── Dock.tsx                底部 9 图标 Dock
    ├── data/
    │   └── sample.ts               假数据
    ├── store/
    │   └── useWorkspace.ts         Zustand store
    └── lib/
        └── layouts.ts              3 套布局预设的窗口位置
```

---

## 7. 验收清单

### 7.1 视觉（必过）

- [ ] 桌面底色 = 米白纸 `#F7F5EF`，背景有极淡靛蓝网格 + 极淡山形纹
- [ ] 字体全站衬线（FlyFlower + Hedvig），没有 sans-serif 出现；数字也是衬线
- [ ] 强调色 = 靛蓝 `#1B3B6F` + 朱红 `#BC4749`，没有 Notion 蓝紫
- [ ] 圆角统一 8px（卡片）/ 4px（按钮）/ 999px（pill）
- [ ] 顶部栏白底 + blur + 1px 底边
- [ ] Dock 白底 + blur + pill 形状 + 居中
- [ ] 至少 4 个浮窗（藏宝图 / 今日 / 画像 / 日历）独立可见
- [ ] 至少 1 个朱红节点（关键节点）和 1 个靛蓝节点（当前节点）
- [ ] 至少 1 个休眠分支（细虚线 + 50% 透明）
- [ ] AI 浮窗在右下角、永远在最前（z-index 9999）
- [ ] Dock 9 个图标，每个下面有衬线短标签

### 7.2 交互（必过）

- [ ] 鼠标悬停藏宝图节点 → 节点边框变朱红 + 微缩放 1.05
- [ ] 拖动任意浮窗的标题栏 → 浮窗跟随移动（不卡顿）
- [ ] 点击 [📖 阅读] 布局图标 → 4 个浮窗在 300ms 内过渡到阅读布局
- [ ] 点击 [✏️ 习题] → 过渡到习题布局
- [ ] 点击 [💻 代码] → 日历窗口最小化（淡出 + 收到底部）
- [ ] ModeToggle 点击「🔭 探索」→ 指示器滑动到右侧
- [ ] Dock 点击任一图标 → 该图标背景变靛蓝（激活态）
- [ ] AI 浮窗输入框打字 + 回车 → 用户气泡出现 + 500ms 后假 AI 回复气泡
- [ ] 顶部栏「Map / Today / Resources / Profile」hover → 文字颜色平滑过渡到靛蓝

### 7.3 启动（必过）

```bash
cd D:\Projects\SelfLearn\demo-serif
npm install
npm run dev
# 浏览器打开 http://localhost:5174
# 不报错，页面正常渲染
```

### 7.4 字体加载验证

DevTools → Network → 字体 4 个文件全部 200：
- FlyFlowerSong-OTF.otf
- FlyFlowerSong-TTF.ttf
- HedvigLettersSerif-Regular.otf
- HedvigLettersSerif-Regular.ttf

---

## 8. 不在 demo 范围（再次明确）

- 真实 AI 流式输出
- localStorage / IndexedDB 持久化
- 移动端响应式
- 右键菜单 / 命令面板 / 快捷键系统
- 多窗口层级精细管理（z-index 重排算法）
- 突击模式 / 长按 2s 保存布局
- 真实文件上传 / OCR / 知识库检索
- 与后端 API 的任何对接
- 用户偏好持久化
- 设置应用（10 个设置模块）

---

## 9. 与原 demo 的关系

```
D:\Projects\SelfLearn\
├── demo/                  ← 原制图院蓝图风（保留，作为对照）
│   ├── package.json
│   ├── vite.config.ts (port 5173)
│   └── src/...
└── demo-serif/            ← 新 Notion × UKIYO 衬线版（本设计文档）
    ├── package.json
    ├── vite.config.ts (port 5174)
    └── src/...
```

两个 demo 完全独立，可以并存 npm run dev。

---

## 10. 后续扩展路径（不在本期实现）

- 接入 dnd-kit 替换 framer-motion 自带 drag（性能更好）
- 接入 @xyflow/react 替换 SVG 自绘节点图
- 真实接 WebSocket 流式 AI 对话
- localStorage 持久化窗口位置
- 移动端响应式 + 触屏拖动
- 暗色模式预览（同样配色，仅底色翻转）
- 命令面板（Ctrl+Shift+P）
- 真实资源生成 + mermaid 渲染