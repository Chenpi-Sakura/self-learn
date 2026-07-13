# Notion × UKIYO Serif Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Stage 4 T1 重命名注（2026-07-13）**：本文档原 Working directory 为 `D:\Projects\SelfLearn\demo-serif\`，Stage 4 T1 已将工程目录重命名为 `D:\Projects\SelfLearn\frontend\`。下方所有 `demo-serif/` 路径串保留原貌以保持历史准确性；实际后续 Stage 文档使用 `frontend/`。

**Goal:** Build `D:\Projects\SelfLearn\demo-serif\` — a Vite + React + TS desktop-style workspace demo combining Notion structural language with UKIYO indigo+vermilion palette and all-serif fonts (FlyFlower Song + Hedvig Letters Serif), with light drag/hover/layout-switch interactions.

**Architecture:** Single Zustand store drives 4 floating Windows on a backdrop, plus fixed TopBar/Dock/ChatFloat. framer-motion `drag` on Window title bar; `layoutId` for layout-switch transitions between 3 presets (reading/practice/coding). Local fonts loaded via `@font-face` with `unicode-range` split.

**Tech Stack:** Vite 5 · React 18 · TypeScript · Zustand 4 · framer-motion 11 · CSS Modules · local OTF/TTF fonts.

---

## Global Constraints

- Working directory: `D:\Projects\SelfLearn\demo-serif\` (create fresh, do not touch existing `demo/`).
- Vite port: **5174** (5173 is taken by original `demo/`).
- Color tokens (only these, no others):
  - `--indigo: #1B3B6F` (primary accent)
  - `--vermilion: #BC4749` (critical/highlight)
  - `--paper: #F7F5EF` (desktop backdrop)
  - `--card: #FFFFFF` (windows)
  - `--border: #E4E4E0` (only border shade, 1px)
  - `--ink: #1A1A1A` (body text)
  - `--mute: #6B6B70` (secondary text)
  - `--hover: #F4F4F0` (hover surface)
- Fonts (only these two families):
  - Chinese: `FlyFlower` (FlyFlowerSong-OTF.otf + TTF fallback) with `unicode-range: U+4E00-9FFF`
  - Latin / digits: `Hedvig` (HedvigLettersSerif-Regular.otf + TTF fallback)
  - Body font stack: `var(--font-serif-cn), var(--font-serif-en)` — **never** use sans-serif anywhere.
- Border radius: cards 8px / buttons 4px / pills 999px. Nothing else.
- Box shadow: only one tier — `0 1px 2px rgba(27,59,111,0.04)`, deepening on hover to `0 2px 8px rgba(27,59,111,0.08)`. **No other shadows.**
- Window z-index tiers: backdrop 0 / dock 100 / windows 1000-5000 (focus +10) / chat 9999.
- Window drag boundary: title bar must stay within viewport.
- Demo scope (do NOT build): real AI streaming, localStorage persistence, mobile responsive, right-click menus, command palette, keyboard shortcuts, real file upload, API integration.
- Light interactions to implement: node hover scale+border, window title-bar drag, layout-icon click → window reposition, mode toggle slide, dock icon active state, chat input + mock reply, nav hover color transition.

---

## File Map

Files to create (none modified — greenfield project):

| File | Responsibility |
|---|---|
| `package.json` | deps + scripts |
| `vite.config.ts` | port 5174, react plugin |
| `tsconfig.json` | strict TS for app |
| `tsconfig.node.json` | TS for vite config |
| `index.html` | root HTML, viewport meta |
| `README.md` | how to run |
| `public/fonts/FlyFlowerSong-OTF.otf` | copy from `D:\Projects\SelfLearn\fonts\` |
| `public/fonts/FlyFlowerSong-TTF.ttf` | copy |
| `public/fonts/HedvigLettersSerif-Regular.otf` | copy |
| `public/fonts/HedvigLettersSerif-Regular.ttf` | copy |
| `src/main.tsx` | React entry, mount App |
| `src/App.tsx` | composes Backdrop + TopBar + Windows + Dock + ChatFloat |
| `src/styles/tokens.css` | color/spacing/radius variables |
| `src/styles/fonts.css` | @font-face + body font stack |
| `src/styles/globals.css` | reset + body backdrop + link/button defaults |
| `src/data/sample.ts` | mock nodes, edges, profile, calendar, tasks, chat |
| `src/store/useWorkspace.ts` | Zustand store (mode, layout, windows, nodes, profile, tasks, chat) |
| `src/lib/layouts.ts` | 3 layout preset functions returning WindowState[] |
| `src/components/Backdrop.tsx` | paper backdrop + faint indigo grid + faint mountain SVG |
| `src/components/TopBar.tsx` | sticky top bar with logo/nav/ModeToggle/LayoutIcons/user |
| `src/components/ModeToggle.tsx` | proficiency/exploration segmented control with layoutId |
| `src/components/LayoutIcons.tsx` | reading/practice/coding icon row, click triggers layout switch |
| `src/components/Window.tsx` | generic draggable window shell |
| `src/components/Dock.tsx` | bottom-center pill with 9 icon+label entries |
| `src/components/ChatFloat.tsx` | bottom-right AI chat, z=9999 |
| `src/components/TreasureMap.tsx` | SVG node map (5 main + 2 interest + 1 sleeping branch) |
| `src/components/ProfileRadar.tsx` | 6-axis radar + 6 progress bars |
| `src/components/Calendar.tsx` | 7×6 month grid with 4-step heat density |
| `src/components/TaskList.tsx` | today's 3-task checkbox list |
| `src/components/DocContent.tsx` | sample lecture markdown-ish content |
| `src/components/ExerciseContent.tsx` | sample exercise question |
| `src/components/NoteContent.tsx` | sample note content |

---

## Task 1: Scaffold project + copy fonts + install deps

**Files:**
- Create: `D:\Projects\SelfLearn\demo-serif\package.json`
- Create: `D:\Projects\SelfLearn\demo-serif\vite.config.ts`
- Create: `D:\Projects\SelfLearn\demo-serif\tsconfig.json`
- Create: `D:\Projects\SelfLearn\demo-serif\tsconfig.node.json`
- Create: `D:\Projects\SelfLearn\demo-serif\index.html`
- Create: `D:\Projects\SelfLearn\demo-serif\README.md`
- Create: `D:\Projects\SelfLearn\demo-serif\public\fonts\FlyFlowerSong-OTF.otf` (copy)
- Create: `D:\Projects\SelfLearn\demo-serif\public\fonts\FlyFlowerSong-TTF.ttf` (copy)
- Create: `D:\Projects\SelfLearn\demo-serif\public\fonts\HedvigLettersSerif-Regular.otf` (copy)
- Create: `D:\Projects\SelfLearn\demo-serif\public\fonts\HedvigLettersSerif-Regular.ttf` (copy)

- [ ] **Step 1: Create project root + copy fonts**

```bash
mkdir -p D:/Projects/SelfLearn/demo-serif/public/fonts
cp "D:/Projects/SelfLearn/fonts/FlyFlowerSong-OTF.otf"        "D:/Projects/SelfLearn/demo-serif/public/fonts/"
cp "D:/Projects/SelfLearn/fonts/FlyFlowerSong-TTF.ttf"        "D:/Projects/SelfLearn/demo-serif/public/fonts/"
cp "D:/Projects/SelfLearn/fonts/HedvigLettersSerif-Regular.otf" "D:/Projects/SelfLearn/demo-serif/public/fonts/"
cp "D:/Projects/SelfLearn/fonts/HedvigLettersSerif-Regular.ttf" "D:/Projects/SelfLearn/demo-serif/public/fonts/"
ls D:/Projects/SelfLearn/demo-serif/public/fonts/
```

Expected: 4 files listed.

- [ ] **Step 2: Write package.json**

`D:\Projects\SelfLearn\demo-serif\package.json`:

```json
{
  "name": "demo-serif",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "framer-motion": "^11.3.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "zustand": "^4.5.4"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "typescript": "^5.5.3",
    "vite": "^5.4.1"
  }
}
```

- [ ] **Step 3: Write vite.config.ts (port 5174)**

`D:\Projects\SelfLearn\demo-serif\vite.config.ts`:

```ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: { port: 5174, strictPort: false }
});
```

- [ ] **Step 4: Write tsconfig.json**

`D:\Projects\SelfLearn\demo-serif\tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "isolatedModules": true,
    "resolveJsonModule": true,
    "allowSyntheticDefaultImports": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 5: Write tsconfig.node.json**

`D:\Projects\SelfLearn\demo-serif\tsconfig.node.json`:

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 6: Write index.html**

`D:\Projects\SelfLearn\demo-serif\index.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1280" />
    <title>SelfLearn · Notion × UKIYO Serif Demo</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 7: Write README.md**

`D:\Projects\SelfLearn\demo-serif\README.md`:

```markdown
# SelfLearn Serif Demo (Notion × UKIYO)

Visual + light-interaction demo. Standalone Vite + React + TS project.

## Run

\`\`\`bash
npm install
npm run dev
# open http://localhost:5174
\`\`\`

Fonts are served from `public/fonts/`. No external CDN.
```

- [ ] **Step 8: Install dependencies**

```bash
cd D:/Projects/SelfLearn/demo-serif
npm install
```

Expected: completes without errors, `node_modules/` created, no peer-dep warnings about React.

- [ ] **Step 9: Commit (skip — project is not under git, leave for later)**

(no git in this repo; skip commit step)

---

## Task 2: Styles — tokens, fonts, globals

**Files:**
- Create: `D:\Projects\SelfLearn\demo-serif\src\styles\tokens.css`
- Create: `D:\Projects\SelfLearn\demo-serif\src\styles\fonts.css`
- Create: `D:\Projects\SelfLearn\demo-serif\src\styles\globals.css`

- [ ] **Step 1: Write tokens.css**

`D:\Projects\SelfLearn\demo-serif\src\styles\tokens.css`:

```css
:root {
  /* UKIYO × Notion palette */
  --indigo: #1B3B6F;
  --vermilion: #BC4749;
  --paper: #F7F5EF;
  --card: #FFFFFF;
  --border: #E4E4E0;
  --ink: #1A1A1A;
  --mute: #6B6B70;
  --hover: #F4F4F0;
  --ink-soft: rgba(27, 59, 111, 0.08);
  --indigo-soft: rgba(27, 59, 111, 0.06);
  --vermilion-soft: rgba(188, 71, 73, 0.10);
  --grid-line: rgba(27, 59, 111, 0.04);

  /* Radii */
  --r-card: 8px;
  --r-btn: 4px;
  --r-pill: 999px;

  /* Shadows */
  --shadow-1: 0 1px 2px rgba(27, 59, 111, 0.04);
  --shadow-2: 0 2px 8px rgba(27, 59, 111, 0.08);

  /* Spacing scale */
  --s-1: 4px;
  --s-2: 8px;
  --s-3: 12px;
  --s-4: 16px;
  --s-5: 24px;
  --s-6: 32px;
  --s-7: 48px;

  /* Heights */
  --topbar-h: 44px;
  --dock-h: 64px;
}
```

- [ ] **Step 2: Write fonts.css**

`D:\Projects\SelfLearn\demo-serif\src\styles\fonts.css`:

```css
@font-face {
  font-family: 'FlyFlower';
  src:
    url('/fonts/FlyFlowerSong-OTF.otf') format('opentype'),
    url('/fonts/FlyFlowerSong-TTF.ttf') format('truetype');
  font-display: swap;
  unicode-range: U+4E00-9FFF;
}

@font-face {
  font-family: 'Hedvig';
  src:
    url('/fonts/HedvigLettersSerif-Regular.otf') format('opentype'),
    url('/fonts/HedvigLettersSerif-Regular.ttf') format('truetype');
  font-display: swap;
}

:root {
  --font-serif-cn: 'FlyFlower', 'Songti SC', 'STSong', serif;
  --font-serif-en: 'Hedvig', 'Iowan Old Style', 'Georgia', serif;
}
```

- [ ] **Step 3: Write globals.css**

`D:\Projects\SelfLearn\demo-serif\src\styles\globals.css`:

```css
*, *::before, *::after { box-sizing: border-box; }
html, body, #root { height: 100%; margin: 0; padding: 0; }
body {
  font-family: var(--font-serif-cn), var(--font-serif-en);
  color: var(--ink);
  background: var(--paper);
  font-size: 14px;
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  overflow: hidden; /* demo: fixed viewport */
}
button { font: inherit; color: inherit; background: none; border: 0; padding: 0; cursor: pointer; }
a { color: var(--indigo); text-decoration: none; }
a:hover { color: var(--vermilion); }
input, textarea { font: inherit; color: inherit; }

/* faint indigo grid backdrop — applied at app shell, not body, so windows can sit above */
.grid-backdrop {
  background-image:
    linear-gradient(to right, var(--grid-line) 1px, transparent 1px),
    linear-gradient(to bottom, var(--grid-line) 1px, transparent 1px);
  background-size: 24px 24px;
}
```

- [ ] **Step 4: Verify CSS files compile (no syntax errors)**

Open each file in any editor; the tokens/fonts/globals load via `main.tsx` later. No JS check needed at this step.

---

## Task 3: Sample data + Zustand store

**Files:**
- Create: `D:\Projects\SelfLearn\demo-serif\src\data\sample.ts`
- Create: `D:\Projects\SelfLearn\demo-serif\src\store\useWorkspace.ts`

- [ ] **Step 1: Write sample.ts (mock nodes, edges, profile, calendar, tasks, chat)**

`D:\Projects\SelfLearn\demo-serif\src\data\sample.ts`:

```ts
export type NodeStatus = 'completed' | 'current' | 'key' | 'locked' | 'interest' | 'sleeping';

export interface MapNode {
  id: string;
  x: number; y: number;
  label: string;
  status: NodeStatus;
  minutes: number;
  branch?: 'up' | 'down' | null;
}

export interface Edge {
  from: string; to: string;
  kind: 'main' | 'interest' | 'sleeping';
}

export const mapNodes: MapNode[] = [
  { id: 'n1', x: 60,  y: 110, label: '词嵌入',     status: 'completed', minutes: 30 },
  { id: 'n2', x: 180, y: 110, label: 'RNN',        status: 'completed', minutes: 45 },
  { id: 'n3', x: 300, y: 110, label: 'LSTM',       status: 'completed', minutes: 50 },
  { id: 'n4', x: 420, y: 110, label: '自注意力',   status: 'current',   minutes: 45 },
  { id: 'n5', x: 540, y: 110, label: 'Transformer', status: 'key',      minutes: 60 },
  { id: 'n6', x: 660, y: 50,  label: '视觉 Transformer', status: 'interest', minutes: 40, branch: 'up' },
  { id: 'n7', x: 660, y: 170, label: '经典 RNN',       status: 'interest', minutes: 35, branch: 'down' },
  { id: 'n8', x: 300, y: 200, label: '序列建模回顾',  status: 'sleeping', minutes: 25, branch: 'down' }
];

export const mapEdges: Edge[] = [
  { from: 'n1', to: 'n2', kind: 'main' },
  { from: 'n2', to: 'n3', kind: 'main' },
  { from: 'n3', to: 'n4', kind: 'main' },
  { from: 'n4', to: 'n5', kind: 'main' },
  { from: 'n4', to: 'n6', kind: 'interest' },
  { from: 'n4', to: 'n7', kind: 'interest' },
  { from: 'n3', to: 'n8', kind: 'sleeping' }
];

export const profile = {
  student: '林知遥',
  dimensions: [
    { key: 'understanding', label: '理解', value: 78 },
    { key: 'reasoning',     label: '推理', value: 62 },
    { key: 'expression',    label: '表达', value: 55 },
    { key: 'application',   label: '应用', value: 70 },
    { key: 'transfer',      label: '迁移', value: 74, pulsing: true },
    { key: 'creation',      label: '创造', value: 48 }
  ]
};

const cell = (day: number, intensity: 0|1|2|3|4) => ({ day, intensity });
export const calendar: { rows: { cells: ReturnType<typeof cell>[] }[]; today: number } = {
  today: 18,
  rows: [
    { cells: [cell(1,0),cell(2,0),cell(3,2),cell(4,1),cell(5,3),cell(6,2),cell(7,0)] },
    { cells: [cell(8,1),cell(9,3),cell(10,4),cell(11,3),cell(12,2),cell(13,0),cell(14,1)] },
    { cells: [cell(15,2),cell(16,3),cell(17,4),cell(18,4),cell(19,3),cell(20,1),cell(21,0)] },
    { cells: [cell(22,0),cell(23,2),cell(24,3),cell(25,4),cell(26,2),cell(27,1),cell(28,0)] },
    { cells: [cell(29,0),cell(30,1),cell(31,2),cell(1,0),cell(2,0),cell(3,0),cell(4,0)] }
  ]
};

export const tasks = [
  { id: 't1', title: '讲解 Attention 机制',         status: 'doing'   as const, minutes: 15 },
  { id: 't2', title: '习题 1.2：Self-Attention',     status: 'todo'    as const, minutes: 25 },
  { id: 't3', title: '笔记：Q / K / V 三元组',       status: 'todo'    as const, minutes: 10 },
  { id: 't4', title: '回顾：LSTM 门控结构',          status: 'done'    as const, minutes: 12 }
];

export const initialChat = [
  { role: 'ai' as const, text: '你已经阅读了三十分钟。要不要快速过一道 Q/K/V 的小问题？' }
];

export const mockAiReplies = [
  '把 Q 想象成"我想找什么"，K 是"我能提供什么"，V 是"我实际给出的内容"。',
  '想象你在一间图书馆。Q 是你的提问，K 是每本书的索引卡，V 是书的内容。',
  '所谓 self-attention，就是让序列里的每个位置都和序列里所有位置互相"对一下眼神"。'
];
```

- [ ] **Step 2: Write useWorkspace.ts (Zustand store)**

`D:\Projects\SelfLearn\demo-serif\src\store\useWorkspace.ts`:

```ts
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
```

- [ ] **Step 3: Write layouts.ts (3 presets)**

`D:\Projects\SelfLearn\demo-serif\src\lib\layouts.ts`:

```ts
import type { WindowState } from '../store/useWorkspace';

const z = (base: number, i: number) => base + i;

export const readingLayout = (): WindowState[] => [
  { id: 'map',      appId: 'treasure_map', x: 60,  y: 70,  w: 720, h: 380, z: z(1000, 0) },
  { id: 'today',    appId: 'today',        x: 800, y: 70,  w: 460, h: 380, z: z(1000, 1) },
  { id: 'profile',  appId: 'profile',      x: 60,  y: 470, w: 720, h: 290, z: z(1000, 2) },
  { id: 'calendar', appId: 'calendar',     x: 800, y: 470, w: 460, h: 290, z: z(1000, 3) }
];

export const practiceLayout = (): WindowState[] => [
  { id: 'map',      appId: 'treasure_map', x: 40,  y: 70,  w: 400, h: 260, z: z(1000, 0) },
  { id: 'today',    appId: 'today',        x: 460, y: 70,  w: 800, h: 480, z: z(1000, 1) },
  { id: 'profile',  appId: 'profile',      x: 40,  y: 350, w: 400, h: 410, z: z(1000, 2) },
  { id: 'calendar', appId: 'calendar',     x: 460, y: 570, w: 400, h: 190, z: z(1000, 3) }
];

export const codingLayout = (): WindowState[] => [
  { id: 'map',      appId: 'treasure_map', x: 40,  y: 70,  w: 380, h: 260, z: z(1000, 0) },
  { id: 'today',    appId: 'today',        x: 440, y: 70,  w: 820, h: 260, z: z(1000, 1) },
  { id: 'profile',  appId: 'profile',      x: 40,  y: 350, w: 380, h: 410, z: z(1000, 2) },
  { id: 'calendar', appId: 'calendar',     x: 440, y: 350, w: 820, h: 410, z: z(1000, 3), minimized: true }
];
```

---

## Task 4: App shell + Backdrop + Window + TopBar + Dock + ChatFloat

**Files:**
- Create: `D:\Projects\SelfLearn\demo-serif\src\main.tsx`
- Create: `D:\Projects\SelfLearn\demo-serif\src\App.tsx`
- Create: `D:\Projects\SelfLearn\demo-serif\src\App.css`
- Create: `D:\Projects\SelfLearn\demo-serif\src\components\Backdrop.tsx`
- Create: `D:\Projects\SelfLearn\demo-serif\src\components\Backdrop.css`
- Create: `D:\Projects\SelfLearn\demo-serif\src\components\Window.tsx`
- Create: `D:\Projects\SelfLearn\demo-serif\src\components\Window.css`
- Create: `D:\Projects\SelfLearn\demo-serif\src\components\TopBar.tsx`
- Create: `D:\Projects\SelfLearn\demo-serif\src\components\TopBar.css`
- Create: `D:\Projects\SelfLearn\demo-serif\src\components\Dock.tsx`
- Create: `D:\Projects\SelfLearn\demo-serif\src\components\Dock.css`
- Create: `D:\Projects\SelfLearn\demo-serif\src\components\ChatFloat.tsx`
- Create: `D:\Projects\SelfLearn\demo-serif\src\components\ChatFloat.css`

- [ ] **Step 1: Write main.tsx**

`D:\Projects\SelfLearn\demo-serif\src\main.tsx`:

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles/fonts.css';
import './styles/tokens.css';
import './styles/globals.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

- [ ] **Step 2: Write Backdrop.tsx + Backdrop.css**

`D:\Projects\SelfLearn\demo-serif\src\components\Backdrop.css`:

```css
.backdrop {
  position: fixed; inset: 0;
  background: var(--paper);
  z-index: 0;
  overflow: hidden;
}
.backdrop-grid {
  position: absolute; inset: 0;
  background-image:
    linear-gradient(to right, var(--grid-line) 1px, transparent 1px),
    linear-gradient(to bottom, var(--grid-line) 1px, transparent 1px);
  background-size: 24px 24px;
  pointer-events: none;
}
.backdrop-mountain {
  position: absolute;
  left: 0; bottom: 0;
  width: 540px; height: 220px;
  opacity: 0.08;
  pointer-events: none;
}
.backdrop-seal {
  position: absolute;
  right: 60px; top: 120px;
  width: 92px; height: 92px;
  border: 2px solid var(--vermilion);
  border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  color: var(--vermilion);
  font-size: 14px;
  letter-spacing: 0.2em;
  transform: rotate(-6deg);
  opacity: 0.65;
  pointer-events: none;
  font-family: var(--font-serif-cn);
}
```

`D:\Projects\SelfLearn\demo-serif\src\components\Backdrop.tsx`:

```tsx
import './Backdrop.css';

export function Backdrop() {
  return (
    <div className="backdrop" aria-hidden>
      <div className="backdrop-grid" />
      <svg className="backdrop-mountain" viewBox="0 0 540 220" preserveAspectRatio="none">
        <path d="M0 200 L120 90 L200 150 L300 60 L420 140 L540 100 L540 220 L0 220 Z"
              fill="var(--indigo)" opacity="0.5" />
        <path d="M0 220 L80 170 L180 190 L300 160 L420 195 L540 175 L540 220 L0 220 Z"
              fill="var(--indigo)" opacity="0.7" />
      </svg>
      <div className="backdrop-seal">藏 宝 图</div>
    </div>
  );
}
```

- [ ] **Step 3: Write Window.tsx + Window.css**

`D:\Projects\SelfLearn\demo-serif\src\components\Window.css`:

```css
.win {
  position: absolute;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--r-card);
  box-shadow: var(--shadow-1);
  display: flex; flex-direction: column;
  overflow: hidden;
  transition: box-shadow 200ms ease;
}
.win.focused { box-shadow: var(--shadow-2); }
.win.minimized { opacity: 0; pointer-events: none; transform: scale(0.95); }
.win-title {
  height: 36px;
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center;
  padding: 0 12px;
  gap: 8px;
  cursor: grab;
  user-select: none;
  background: var(--card);
}
.win-title:active { cursor: grabbing; }
.win-title .dot {
  width: 10px; height: 10px; border-radius: 50%;
  background: var(--border);
}
.win-title .dot.key { background: var(--vermilion); }
.win-title .name {
  flex: 1;
  font-size: 13px;
  color: var(--ink);
  letter-spacing: 0.02em;
}
.win-title .ctrls { display: flex; gap: 6px; }
.win-title .ctrl {
  width: 22px; height: 22px;
  display: flex; align-items: center; justify-content: center;
  border-radius: var(--r-btn);
  color: var(--mute);
  font-size: 12px;
}
.win-title .ctrl:hover { background: var(--hover); color: var(--ink); }
.win-title .ctrl.close:hover { background: var(--vermilion); color: var(--card); }
.win-body { flex: 1; overflow: auto; padding: 16px; }
```

`D:\Projects\SelfLearn\demo-serif\src\components\Window.tsx`:

```tsx
import { motion, type PanInfo } from 'framer-motion';
import { ReactNode, useRef } from 'react';
import type { WindowState } from '../store/useWorkspace';
import { useWorkspace } from '../store/useWorkspace';
import './Window.css';

interface Props {
  win: WindowState;
  title: string;
  isKey?: boolean;
  children: ReactNode;
}

export function Window({ win, title, isKey, children }: Props) {
  const moveWindow = useWorkspace((s) => s.moveWindow);
  const focusWindow = useWorkspace((s) => s.focusWindow);
  const focusedId = useWorkspace((s) => s.focusedId);
  const wrapRef = useRef<HTMLDivElement>(null);

  const onDragEnd = (_: unknown, info: PanInfo) => {
    moveWindow(win.id, win.x + info.offset.x, win.y + info.offset.y);
  };

  const focused = focusedId === win.id;

  return (
    <motion.div
      ref={wrapRef}
      className={`win ${focused ? 'focused' : ''} ${win.minimized ? 'minimized' : ''}`}
      style={{ zIndex: win.z, width: win.w, height: win.h, left: 0, top: 0 }}
      initial={false}
      animate={{ x: win.x, y: win.y }}
      transition={{ type: 'spring', stiffness: 240, damping: 28 }}
      onMouseDown={() => focusWindow(win.id)}
    >
      <motion.div
        className="win-title"
        drag
        dragMomentum={false}
        dragElastic={0}
        onDragEnd={onDragEnd}
        whileTap={{ cursor: 'grabbing' }}
      >
        <span className={`dot ${isKey ? 'key' : ''}`} />
        <span className="name">{title}</span>
        <div className="ctrls">
          <button className="ctrl" title="最小化">—</button>
          <button className="ctrl" title="最大化">□</button>
          <button className="ctrl close" title="关闭">×</button>
        </div>
      </motion.div>
      <div className="win-body">{children}</div>
    </motion.div>
  );
}
```

- [ ] **Step 4: Write TopBar.tsx + TopBar.css**

`D:\Projects\SelfLearn\demo-serif\src\components\TopBar.css`:

```css
.topbar {
  position: fixed; left: 0; right: 0; top: 0;
  height: var(--topbar-h);
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center;
  padding: 0 24px;
  gap: 24px;
  z-index: 5000;
}
.topbar .logo {
  font-size: 16px; font-weight: 600;
  color: var(--indigo);
  letter-spacing: 0.04em;
}
.topbar nav { display: flex; gap: 20px; }
.topbar nav a {
  font-size: 13px;
  color: var(--ink);
  transition: color 180ms ease;
}
.topbar nav a:hover { color: var(--indigo); }
.topbar nav a.active { color: var(--indigo); border-bottom: 1px solid var(--indigo); padding-bottom: 2px; }
.topbar .right { margin-left: auto; display: flex; align-items: center; gap: 14px; }
.topbar .cmdk {
  font-size: 12px; color: var(--mute);
  border: 1px solid var(--border);
  padding: 4px 10px; border-radius: var(--r-btn);
  background: var(--card);
}
.topbar .avatar {
  width: 28px; height: 28px;
  border-radius: var(--r-pill);
  background: var(--indigo);
  color: var(--card);
  display: flex; align-items: center; justify-content: center;
  font-size: 13px;
}
```

`D:\Projects\SelfLearn\demo-serif\src\components\TopBar.tsx`:

```tsx
import './TopBar.css';
import { ModeToggle } from './ModeToggle';
import { LayoutIcons } from './LayoutIcons';

export function TopBar() {
  return (
    <header className="topbar">
      <span className="logo">◆ SelfLearn</span>
      <nav>
        <a href="#" className="active">Map</a>
        <a href="#">Today</a>
        <a href="#">Resources</a>
        <a href="#">Profile</a>
      </nav>
      <ModeToggle />
      <LayoutIcons />
      <div className="right">
        <span className="cmdk">⌘K</span>
        <span className="avatar">林</span>
      </div>
    </header>
  );
}
```

- [ ] **Step 5: Write Dock.tsx + Dock.css**

`D:\Projects\SelfLearn\demo-serif\src\components\Dock.css`:

```css
.dock {
  position: fixed;
  left: 50%; bottom: 20px;
  transform: translateX(-50%);
  height: var(--dock-h);
  padding: 0 14px;
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border);
  border-radius: var(--r-pill);
  box-shadow: var(--shadow-2);
  display: flex; align-items: center;
  gap: 4px;
  z-index: 100;
}
.dock-item {
  width: 52px; height: 56px;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 2px;
  border-radius: var(--r-card);
  cursor: pointer;
  transition: background 160ms ease;
  color: var(--mute);
}
.dock-item:hover { background: var(--hover); color: var(--ink); }
.dock-item.active { background: var(--indigo-soft); color: var(--indigo); }
.dock-item .ic { font-size: 18px; line-height: 1; }
.dock-item .lb { font-size: 10px; letter-spacing: 0.06em; }
```

`D:\Projects\SelfLearn\demo-serif\src\components\Dock.tsx`:

```tsx
import { useState } from 'react';
import './Dock.css';

const items = [
  { ic: '◇', lb: 'Map' },
  { ic: '✦', lb: 'AI' },
  { ic: '□', lb: 'Doc' },
  { ic: '≡', lb: 'Ex' },
  { ic: '⌨', lb: 'Code' },
  { ic: '✎', lb: 'Note' },
  { ic: '◈', lb: 'Mind' },
  { ic: '❐', lb: 'Res' },
  { ic: '▣', lb: 'Dash' }
];

export function Dock() {
  const [active, setActive] = useState(0);
  return (
    <nav className="dock">
      {items.map((it, i) => (
        <button
          key={it.lb}
          className={`dock-item ${active === i ? 'active' : ''}`}
          onClick={() => setActive(i)}
        >
          <span className="ic">{it.ic}</span>
          <span className="lb">{it.lb}</span>
        </button>
      ))}
    </nav>
  );
}
```

- [ ] **Step 6: Write ChatFloat.tsx + ChatFloat.css**

`D:\Projects\SelfLearn\demo-serif\src\components\ChatFloat.css`:

```css
.chat {
  position: fixed; right: 24px; bottom: 100px;
  width: 360px; height: 460px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--r-card);
  box-shadow: var(--shadow-2);
  display: flex; flex-direction: column;
  z-index: 9999;
  overflow: hidden;
}
.chat-head {
  padding: 12px 14px;
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 10px;
}
.chat-head .av {
  width: 32px; height: 32px;
  border-radius: var(--r-pill);
  background: var(--indigo);
  color: var(--card);
  display: flex; align-items: center; justify-content: center;
  font-size: 14px;
}
.chat-head .name { font-size: 14px; color: var(--ink); }
.chat-head .sub  { font-size: 11px; color: var(--mute); margin-left: auto; }
.chat-body {
  flex: 1; overflow-y: auto;
  padding: 12px 14px;
  display: flex; flex-direction: column; gap: 8px;
}
.bubble {
  max-width: 80%;
  padding: 8px 12px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.55;
}
.bubble.ai  { background: var(--paper); color: var(--ink); align-self: flex-start; border: 1px solid var(--border); }
.bubble.user { background: var(--indigo); color: var(--card); align-self: flex-end; }
.chat-input {
  border-top: 1px solid var(--border);
  padding: 8px;
  display: flex; gap: 6px;
}
.chat-input input {
  flex: 1;
  border: 1px solid var(--border);
  border-radius: var(--r-pill);
  padding: 6px 12px;
  outline: none;
  background: var(--card);
}
.chat-input input:focus { border-color: var(--indigo); }
.chat-input button {
  width: 32px; height: 32px;
  border-radius: var(--r-pill);
  background: var(--vermilion);
  color: var(--card);
  font-size: 14px;
}
```

`D:\Projects\SelfLearn\demo-serif\src\components\ChatFloat.tsx`:

```tsx
import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { useWorkspace } from '../store/useWorkspace';
import './ChatFloat.css';

export function ChatFloat() {
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
    <aside className="chat">
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
    </aside>
  );
}
```

- [ ] **Step 7: Write App.tsx + App.css**

`D:\Projects\SelfLearn\demo-serif\src\App.css`:

```css
.app {
  position: relative;
  width: 100vw; height: 100vh;
  overflow: hidden;
}
.app-pad-top   { padding-top: var(--topbar-h); }
.app-pad-bottom { padding-bottom: 88px; }
.windows-layer {
  position: absolute;
  inset: var(--topbar-h) 0 0 0;
}
```

`D:\Projects\SelfLearn\demo-serif\src\App.tsx`:

```tsx
import './App.css';
import { Backdrop } from './components/Backdrop';
import { TopBar } from './components/TopBar';
import { Dock } from './components/Dock';
import { ChatFloat } from './components/ChatFloat';
import { Window } from './components/Window';
import { TreasureMap } from './components/TreasureMap';
import { TaskList } from './components/TaskList';
import { ProfileRadar } from './components/ProfileRadar';
import { Calendar } from './components/Calendar';
import { useWorkspace } from './store/useWorkspace';

export default function App() {
  const windows = useWorkspace((s) => s.windows);

  return (
    <div className="app">
      <Backdrop />
      <TopBar />
      <div className="windows-layer">
        <Window win={windows.map}      title="深度学习路径"  isKey><TreasureMap /></Window>
        <Window win={windows.today}    title="今日学习"><TaskList /></Window>
        <Window win={windows.profile}  title="六维画像"><ProfileRadar /></Window>
        <Window win={windows.calendar} title="本月打卡"><Calendar /></Window>
      </div>
      <Dock />
      <ChatFloat />
    </div>
  );
}
```

---

## Task 5: ModeToggle + LayoutIcons (referenced by TopBar)

**Files:**
- Create: `D:\Projects\SelfLearn\demo-serif\src\components\ModeToggle.tsx`
- Create: `D:\Projects\SelfLearn\demo-serif\src\components\ModeToggle.css`
- Create: `D:\Projects\SelfLearn\demo-serif\src\components\LayoutIcons.tsx`
- Create: `D:\Projects\SelfLearn\demo-serif\src\components\LayoutIcons.css`

- [ ] **Step 1: Write ModeToggle.tsx + .css**

`D:\Projects\SelfLearn\demo-serif\src\components\ModeToggle.css`:

```css
.mode {
  display: inline-flex;
  background: var(--paper);
  border: 1px solid var(--border);
  border-radius: var(--r-pill);
  padding: 2px;
  position: relative;
  margin-left: 16px;
}
.mode button {
  position: relative;
  z-index: 1;
  padding: 4px 14px;
  font-size: 12px;
  border-radius: var(--r-pill);
  color: var(--mute);
  transition: color 180ms ease;
}
.mode button.on { color: var(--card); }
.mode .pill {
  position: absolute;
  top: 2px; bottom: 2px;
  background: var(--indigo);
  border-radius: var(--r-pill);
  z-index: 0;
}
```

`D:\Projects\SelfLearn\demo-serif\src\components\ModeToggle.tsx`:

```tsx
import { motion } from 'framer-motion';
import { useWorkspace } from '../store/useWorkspace';
import './ModeToggle.css';

export function ModeToggle() {
  const mode = useWorkspace((s) => s.mode);
  const setMode = useWorkspace((s) => s.setMode);

  return (
    <div className="mode" role="tablist" aria-label="学习模式">
      {mode === 'proficiency' && (
        <motion.span
          layoutId="mode-pill"
          className="pill"
          initial={false}
          transition={{ type: 'spring', stiffness: 380, damping: 30 }}
          style={{ left: 2, right: '50%' }}
        />
      )}
      {mode === 'exploration' && (
        <motion.span
          layoutId="mode-pill"
          className="pill"
          initial={false}
          transition={{ type: 'spring', stiffness: 380, damping: 30 }}
          style={{ left: '50%', right: 2 }}
        />
      )}
      <button className={mode === 'proficiency' ? 'on' : ''} onClick={() => setMode('proficiency')}>🎯 精通</button>
      <button className={mode === 'exploration' ? 'on' : ''} onClick={() => setMode('exploration')}>🔭 探索</button>
    </div>
  );
}
```

- [ ] **Step 2: Write LayoutIcons.tsx + .css**

`D:\Projects\SelfLearn\demo-serif\src\components\LayoutIcons.css`:

```css
.layout-icons {
  display: inline-flex; gap: 6px;
  margin-left: 8px;
}
.layout-icons button {
  width: 30px; height: 30px;
  display: flex; align-items: center; justify-content: center;
  border: 1px solid var(--border);
  border-radius: var(--r-btn);
  background: var(--card);
  color: var(--mute);
  font-size: 14px;
  transition: all 160ms ease;
}
.layout-icons button:hover { color: var(--indigo); border-color: var(--indigo); }
.layout-icons button.on { background: var(--indigo-soft); border-color: var(--indigo); color: var(--indigo); }
```

`D:\Projects\SelfLearn\demo-serif\src\components\LayoutIcons.tsx`:

```tsx
import { useWorkspace, type LayoutId } from '../store/useWorkspace';
import { readingLayout, practiceLayout, codingLayout } from '../lib/layouts';
import './LayoutIcons.css';

const opts: { id: LayoutId; ic: string; label: string; fn: () => ReturnType<typeof readingLayout> }[] = [
  { id: 'reading',  ic: '📖', label: '阅读', fn: readingLayout },
  { id: 'practice', ic: '✏️', label: '习题', fn: practiceLayout },
  { id: 'coding',   ic: '💻', label: '代码', fn: codingLayout }
];

export function LayoutIcons() {
  const layout = useWorkspace((s) => s.layout);
  const setLayout = useWorkspace((s) => s.setLayout);

  return (
    <div className="layout-icons" role="group" aria-label="布局">
      {opts.map((o) => (
        <button
          key={o.id}
          className={layout === o.id ? 'on' : ''}
          title={o.label}
          onClick={() => setLayout(o.id, o.fn())}
        >
          {o.ic}
        </button>
      ))}
    </div>
  );
}
```

---

## Task 6: Window contents — TreasureMap, ProfileRadar, Calendar, TaskList

**Files:**
- Create: `D:\Projects\SelfLearn\demo-serif\src\components\TreasureMap.tsx`
- Create: `D:\Projects\SelfLearn\demo-serif\src\components\TreasureMap.css`
- Create: `D:\Projects\SelfLearn\demo-serif\src\components\ProfileRadar.tsx`
- Create: `D:\Projects\SelfLearn\demo-serif\src\components\ProfileRadar.css`
- Create: `D:\Projects\SelfLearn\demo-serif\src\components\Calendar.tsx`
- Create: `D:\Projects\SelfLearn\demo-serif\src\components\Calendar.css`
- Create: `D:\Projects\SelfLearn\demo-serif\src\components\TaskList.tsx`
- Create: `D:\Projects\SelfLearn\demo-serif\src\components\TaskList.css`

- [ ] **Step 1: Write TreasureMap.tsx + .css**

`D:\Projects\SelfLearn\demo-serif\src\components\TreasureMap.css`:

```css
.tm {
  width: 100%; height: 100%;
  display: flex; flex-direction: column;
}
.tm-head {
  display: flex; justify-content: space-between; align-items: baseline;
  margin-bottom: 8px;
}
.tm-head .h { font-size: 18px; color: var(--ink); }
.tm-head .s { font-size: 12px; color: var(--mute); }
.tm-svg { flex: 1; min-height: 0; }
.tm .node-g { transition: transform 200ms ease; }
.tm .node-g:hover { transform: scale(1.05); }
.tm .node-rect { transition: stroke 160ms ease; }
.tm .node-g:hover .node-rect { stroke: var(--vermilion); stroke-width: 2; }
.tm .node-lbl { font-size: 12px; fill: var(--ink); pointer-events: none; }
.tm .node-num { font-size: 10px; fill: var(--mute); pointer-events: none; }
```

`D:\Projects\SelfLearn\demo-serif\src\components\TreasureMap.tsx`:

```tsx
import { useWorkspace } from '../store/useWorkspace';
import './TreasureMap.css';

const STATUS_FILL: Record<string, string> = {
  completed: '#F4F4F0',
  current:   '#1B3B6F',
  key:       '#BC4749',
  locked:    '#F4F4F0',
  interest:  '#FFFFFF',
  sleeping:  'transparent'
};
const STATUS_TEXT: Record<string, string> = {
  completed: '#1A1A1A',
  current:   '#FFFFFF',
  key:       '#FFFFFF',
  locked:    '#A1A1AA',
  interest:  '#1B3B6F',
  sleeping:  '#A1A1AA'
};

export function TreasureMap() {
  const nodes = useWorkspace((s) => s.nodes);
  const edges = useWorkspace((s) => s.edges);

  return (
    <div className="tm">
      <div className="tm-head">
        <div className="h">深度学习路径</div>
        <div className="s">8 站 · 3 已完成 · 1 进行中</div>
      </div>
      <svg className="tm-svg" viewBox="0 0 760 240" preserveAspectRatio="xMidYMid meet">
        {edges.map((e, i) => {
          const a = nodes.find((n) => n.id === e.from);
          const b = nodes.find((n) => n.id === e.to);
          if (!a || !b) return null;
          const dash =
            e.kind === 'interest' ? '5 4' :
            e.kind === 'sleeping' ? '2 4' : '';
          const stroke =
            e.kind === 'interest' ? 'var(--indigo)' :
            e.kind === 'sleeping' ? 'var(--mute)' : 'var(--ink)';
          const op = e.kind === 'sleeping' ? 0.4 : e.kind === 'interest' ? 0.5 : 0.7;
          return (
            <line key={i} x1={a.x + 50} y1={a.y + 20} x2={b.x + 50} y2={b.y + 20}
                  stroke={stroke} strokeWidth={e.kind === 'main' ? 1.5 : 1}
                  strokeDasharray={dash} opacity={op} />
          );
        })}
        {nodes.map((n) => {
          const fill = STATUS_FILL[n.status];
          const txt = STATUS_TEXT[n.status];
          const stroke =
            n.status === 'key' ? 'var(--vermilion)' :
            n.status === 'sleeping' ? 'var(--mute)' :
            n.status === 'interest' ? 'var(--indigo)' :
            n.status === 'current' ? 'var(--indigo)' : 'var(--border)';
          const strokeDash = n.status === 'sleeping' ? '3 3' : n.status === 'interest' ? '4 3' : '';
          const op = n.status === 'sleeping' ? 0.55 : 1;
          return (
            <g key={n.id} className="node-g" transform={`translate(${n.x}, ${n.y})`} opacity={op}>
              <rect className="node-rect" x="0" y="0" width="100" height="40" rx="6"
                    fill={fill} stroke={stroke} strokeWidth={n.status === 'key' || n.status === 'current' ? 1.5 : 1}
                    strokeDasharray={strokeDash} />
              <text className="node-num" x="8" y="14" fill={txt}>№{n.id.slice(1)} · {n.minutes}min</text>
              <text className="node-lbl" x="50" y="30" textAnchor="middle" fill={txt}>{n.label}</text>
              {n.status === 'current' && (
                <circle cx="100" cy="0" r="6" fill="var(--indigo)">
                  <animate attributeName="r" values="4;9;4" dur="2s" repeatCount="indefinite" />
                  <animate attributeName="opacity" values="0.6;0;0.6" dur="2s" repeatCount="indefinite" />
                </circle>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
```

- [ ] **Step 2: Write ProfileRadar.tsx + .css**

`D:\Projects\SelfLearn\demo-serif\src\components\ProfileRadar.css`:

```css
.pr { display: flex; flex-direction: column; height: 100%; }
.pr-head { margin-bottom: 4px; }
.pr-head .h { font-size: 16px; color: var(--ink); }
.pr-head .s { font-size: 12px; color: var(--mute); }
.pr-body { flex: 1; display: grid; grid-template-columns: 200px 1fr; gap: 16px; align-items: center; min-height: 0; }
.pr-svg { width: 100%; height: 100%; max-height: 220px; }
.pr-list { display: flex; flex-direction: column; gap: 6px; }
.pr-row { display: grid; grid-template-columns: 56px 1fr 36px; align-items: center; gap: 8px; font-size: 12px; }
.pr-row .lb { color: var(--ink); }
.pr-row .bar { height: 6px; background: var(--hover); border-radius: var(--r-pill); overflow: hidden; }
.pr-row .bar::before { content: ''; display: block; height: 100%; background: var(--indigo); border-radius: var(--r-pill); }
.pr-row .v { text-align: right; color: var(--ink); font-variant-numeric: tabular-nums; }
.pr-row.pulse .lb::after { content: '  +12%'; color: var(--vermilion); font-size: 10px; }
```

`D:\Projects\SelfLearn\demo-serif\src\components\ProfileRadar.tsx`:

```tsx
import { useWorkspace } from '../store/useWorkspace';
import './ProfileRadar.css';

const SIZE = 180;
const R = 70;

function polar(i: number, total: number, value: number) {
  const angle = (Math.PI * 2 * i) / total - Math.PI / 2;
  const r = (R * value) / 100;
  return { x: Math.cos(angle) * r, y: Math.sin(angle) * r, angle };
}

export function ProfileRadar() {
  const profile = useWorkspace((s) => s.profile);
  const dims = profile.dimensions;
  const total = dims.length;

  const points = dims
    .map((d, i) => {
      const p = polar(i, total, d.value);
      return `${p.x.toFixed(1)},${p.y.toFixed(1)}`;
    })
    .join(' ');

  return (
    <div className="pr">
      <div className="pr-head">
        <div className="h">{profile.student} · 六维画像</div>
        <div className="s">最近 30 天 · 综合</div>
      </div>
      <div className="pr-body">
        <svg className="pr-svg" viewBox={`${-SIZE/2} ${-SIZE/2} ${SIZE} ${SIZE}`}>
          {[0.25, 0.5, 0.75, 1].map((s, i) => (
            <circle key={i} cx="0" cy="0" r={R * s} fill="none" stroke="var(--border)" strokeWidth="0.8" />
          ))}
          {dims.map((_, i) => {
            const a = (Math.PI * 2 * i) / total - Math.PI / 2;
            return (
              <line key={i} x1="0" y1="0"
                    x2={Math.cos(a) * R} y2={Math.sin(a) * R}
                    stroke="var(--border)" strokeWidth="0.6" />
            );
          })}
          <polygon points={points} fill="var(--indigo)" fillOpacity="0.18"
                   stroke="var(--indigo)" strokeWidth="1.5" />
          {dims.map((d, i) => {
            const p = polar(i, total, d.value);
            return <circle key={d.key} cx={p.x} cy={p.y} r="3" fill="var(--indigo)" />;
          })}
          {dims.map((d, i) => {
            const a = (Math.PI * 2 * i) / total - Math.PI / 2;
            const lx = Math.cos(a) * (R + 14);
            const ly = Math.sin(a) * (R + 14);
            return (
              <text key={d.key} x={lx} y={ly} textAnchor="middle"
                    dominantBaseline="middle" fontSize="10" fill="var(--mute)">{d.label}</text>
            );
          })}
        </svg>
        <div className="pr-list">
          {dims.map((d) => (
            <div key={d.key} className={`pr-row ${d.pulsing ? 'pulse' : ''}`}>
              <span className="lb">{d.label}</span>
              <span className="bar" style={{ ['--w' as string]: `${d.value}%` }} />
              <span className="v">{d.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Write Calendar.tsx + .css**

`D:\Projects\SelfLearn\demo-serif\src\components\Calendar.css`:

```css
.cal { display: flex; flex-direction: column; height: 100%; }
.cal-head { margin-bottom: 6px; display: flex; justify-content: space-between; align-items: baseline; }
.cal-head .h { font-size: 16px; color: var(--ink); }
.cal-head .s { font-size: 12px; color: var(--mute); }
.cal-grid { flex: 1; display: grid; grid-template-rows: auto repeat(5, 1fr); gap: 4px; min-height: 0; }
.cal-week { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; font-size: 11px; color: var(--mute); text-align: center; }
.cal-row { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }
.cal-c {
  border: 1px solid var(--border);
  border-radius: var(--r-btn);
  padding: 4px 0;
  text-align: center;
  font-size: 11px;
  background: var(--card);
  color: var(--ink);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  min-height: 32px;
}
.cal-c .d { font-size: 12px; }
.cal-c .h { font-size: 10px; margin-top: 2px; }
.cal-c.h0 .h { color: var(--mute); }
.cal-c.h1 .h { color: var(--indigo-soft); }
.cal-c.h2 .h { color: var(--indigo); }
.cal-c.h3 .h { color: var(--indigo); }
.cal-c.h4 { background: var(--indigo); border-color: var(--indigo); color: var(--card); }
.cal-c.h4 .h { color: var(--card); }
.cal-c.today { border: 1.5px solid var(--vermilion); }
```

`D:\Projects\SelfLearn\demo-serif\src\components\Calendar.tsx`:

```tsx
import { useWorkspace } from '../store/useWorkspace';
import './Calendar.css';

const HEAT_GLYPH = ['·', '░', '▒', '▓', '█'];
const WEEK = ['日', '一', '二', '三', '四', '五', '六'];

export function Calendar() {
  const cal = useWorkspace((s) => s.calendar);

  return (
    <div className="cal">
      <div className="cal-head">
        <div className="h">七月 · 本月打卡</div>
        <div className="s">今天 {cal.today} 日</div>
      </div>
      <div className="cal-grid">
        <div className="cal-week">{WEEK.map((w) => <span key={w}>{w}</span>)}</div>
        {cal.rows.map((row, ri) => (
          <div key={ri} className="cal-row">
            {row.cells.map((c, ci) => (
              <div key={ci}
                   className={`cal-c h${c.intensity} ${c.day === cal.today ? 'today' : ''}`}
                   title={`${c.day} 日`}>
                <span className="d">{c.day}</span>
                <span className="h">{HEAT_GLYPH[c.intensity]}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Write TaskList.tsx + .css**

`D:\Projects\SelfLearn\demo-serif\src\components\TaskList.css`:

```css
.tl { display: flex; flex-direction: column; height: 100%; }
.tl-head { margin-bottom: 8px; }
.tl-head .h { font-size: 16px; color: var(--ink); }
.tl-head .s { font-size: 12px; color: var(--mute); }
.tl-list { display: flex; flex-direction: column; gap: 6px; }
.tl-row {
  display: grid; grid-template-columns: 22px 1fr auto; gap: 10px; align-items: center;
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: var(--r-card);
  background: var(--card);
  transition: background 160ms ease;
}
.tl-row:hover { background: var(--hover); }
.tl-row .ck {
  width: 18px; height: 18px;
  border: 1.5px solid var(--border);
  border-radius: var(--r-btn);
  display: flex; align-items: center; justify-content: center;
  color: var(--card);
  font-size: 12px;
}
.tl-row.doing .ck { background: var(--indigo); border-color: var(--indigo); }
.tl-row.done .ck { background: var(--indigo); border-color: var(--indigo); }
.tl-row .ttl { font-size: 14px; color: var(--ink); }
.tl-row.done .ttl { color: var(--mute); text-decoration: line-through; }
.tl-row.doing .ttl { color: var(--indigo); }
.tl-row .m  { font-size: 11px; color: var(--mute); }
```

`D:\Projects\SelfLearn\demo-serif\src\components\TaskList.tsx`:

```tsx
import { useWorkspace } from '../store/useWorkspace';
import './TaskList.css';

const STATUS_LABEL: Record<string, string> = { doing: '进行中', todo: '待办', done: '完成' };

export function TaskList() {
  const tasks = useWorkspace((s) => s.tasks);
  const toggleTask = useWorkspace((s) => s.toggleTask);

  return (
    <div className="tl">
      <div className="tl-head">
        <div className="h">今日学习</div>
        <div className="s">{tasks.filter((t) => t.status !== 'done').length} 项未完成</div>
      </div>
      <div className="tl-list">
        {tasks.map((t) => (
          <div key={t.id} className={`tl-row ${t.status}`}>
            <button className="ck" onClick={() => toggleTask(t.id)} aria-label={t.title}>
              {t.status !== 'todo' ? '✓' : ''}
            </button>
            <span className="ttl">{t.title}</span>
            <span className="m">{t.minutes} min · {STATUS_LABEL[t.status]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## Task 7: Smoke test — start dev server and verify

- [ ] **Step 1: Start dev server in background**

```bash
cd D:/Projects/SelfLearn/demo-serif
npm run dev
```

Expected: terminal shows `Local: http://localhost:5174/` (port may shift if busy).

- [ ] **Step 2: Open browser to localhost:5174**

Use Chrome / Edge to navigate to the URL from Step 1. Confirm:
- 4 floating windows visible (Map, Today, Profile, Calendar)
- TopBar with mode toggle + layout icons
- Dock at bottom with 9 items
- ChatFloat at bottom right
- Backdrop with paper color + faint grid + faint indigo mountain

- [ ] **Step 3: Verify font loading in DevTools**

DevTools → Network → filter `font`. Reload page. Confirm all 4 font files return 200:
- FlyFlowerSong-OTF.otf
- FlyFlowerSong-TTF.ttf
- HedvigLettersSerif-Regular.otf
- HedvigLettersSerif-Regular.ttf

- [ ] **Step 4: Verify interactions**

| Action | Expected |
|---|---|
| Hover any treasure-map node | Node scales 1.05 + stroke turns vermilion |
| Drag a window by its title bar | Window moves with cursor |
| Click 📖 / ✏️ / 💻 in TopBar | 4 windows reposition smoothly |
| Click 精通 / 探索 in mode toggle | Pill indicator slides |
| Click any dock item | That item's background turns indigo |
| Type into ChatFloat input + Enter | User bubble appears + 500ms later AI bubble |
| Hover a nav link in TopBar | Color transitions to indigo |

All 7 should work. If any fails, inspect the relevant component file in `src/components/` and verify it matches the spec in this plan.

- [ ] **Step 5: Stop dev server**

Stop the background `npm run dev` process (Ctrl+C in the terminal where it's running).

---

## Self-Review (already performed by planner)

| Spec section | Implemented in |
|---|---|
| §2.1 Notion skeleton (radii, borders, shadows, spacing) | Task 2 (tokens.css) + components |
| §2.2 UKIYO palette (only 7 colors) | Task 2 tokens.css — used verbatim across components |
| §2.3 Fonts (FlyFlower + Hedvig, unicode-range) | Task 2 fonts.css + Task 1 copy fonts |
| §2.4 Geometry (8/4/999, 1px border, shadow tiers) | Task 2 tokens.css |
| §3 Backdrop paper + grid + mountain | Task 4 Backdrop.tsx |
| §3.2 TopBar (blur, nav) | Task 4 TopBar.tsx |
| §3.3 ModeToggle with layoutId | Task 5 ModeToggle.tsx |
| §3.4 LayoutIcons | Task 5 LayoutIcons.tsx |
| §3.5 Window drag via framer-motion | Task 4 Window.tsx |
| §3.6 3 layout presets | Task 3 layouts.ts + Task 5 LayoutIcons.tsx wiring |
| §3.7 TreasureMap (5 main + 2 interest + 1 sleeping) | Task 6 TreasureMap.tsx (8 nodes total) |
| §3.8 ProfileRadar | Task 6 ProfileRadar.tsx |
| §3.9 Calendar (░▒▓█ heat) | Task 6 Calendar.tsx |
| §3.10 TaskList | Task 6 TaskList.tsx |
| §3.12 ChatFloat z=9999 | Task 4 ChatFloat.tsx |
| §3.13 Dock 9 items | Task 4 Dock.tsx |
| §4.1 must-do interactions | All implemented: node hover (TreasureMap), drag (Window), layout (LayoutIcons), mode (ModeToggle), dock active (Dock), chat (ChatFloat), nav hover (TopBar) |
| §4.2 explicit no-builds | Not built (verified absent) |

No placeholders, no TBDs. Types consistent: `WindowState.appId` matches `lib/layouts.ts` returned objects and `App.tsx` window keys. `MapNode.status` literals match `STATUS_FILL`/`STATUS_TEXT` keys in TreasureMap.