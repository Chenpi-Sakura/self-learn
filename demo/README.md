# SELFLEARN · 制图院 Demo

一个**纯视觉 demo**，不接后端，但能让你看到「个性化学习多智能体工作站」的整体视觉气质——打开页面就明白这产品在讲什么。

## 美学方向：制图院蓝图（Cartographer's Drafting Table）

> 像打开一本建筑制图员的草稿本：精准、安静、有手绘痕迹。深墨 + 米白纸 + 朱印 + 薄荷绿，IBM Plex 字体族，2px 极微圆角，**完全不用 box-shadow**，改用 1px 偏移的硬线框模拟刻度。

- 主色 `#0F0F0E`（墨）/ `#F7F5EF`（米白纸）/ `#C8341C`（朱印）/ `#2A6F4F`（薄荷）
- 字体：IBM Plex Mono（标题）/ IBM Plex Sans（正文）/ JetBrains Mono（数字）
- 签名细节：藏宝图节点 = 罗盘式（圆 + 十字 + 中心点），不用普通圆形

## 启动

```bash
cd D:\Projects\SelfLearn\demo
npm install
npm run dev
```

浏览器打开 http://localhost:5173

## 视觉自检清单

打开后逐项打勾：

- [ ] 页面底色 = 米白纸 `#F7F5EF`，**无紫色渐变**
- [ ] 字体是 IBM Plex Sans/Mono + JetBrains Mono，**不是 Inter/Roboto**
- [ ] 整体**没有 box-shadow**；分隔全部用 1px 硬线
- [ ] 圆角统一 2px
- [ ] 藏宝图节点是**罗盘式**（圆 + 十字刻度 + 中心点），不是普通圆点
- [ ] 至少能看到 1 个 `💤` 休眠节点（虚线边框 + 灰色半透明）
- [ ] 日历热力至少 4 档密度色阶可见（░▒▓█）
- [ ] 顶部状态栏模式切换的指示器在「🎯 精通」上（朱红底）
- [ ] AI 浮窗（深色标题栏）叠在所有窗口之上
- [ ] Dock 栏 9 个图标，第 1 个「藏」有朱红底色

## 交互自检清单

- [ ] 鼠标悬停藏宝图节点 → 节点边框变朱红 + 微缩放
- [ ] 鼠标悬停「🔭 探索」→ 朱红印章动画
- [ ] 鼠标悬停三个布局图标（📖/✏️/💻）→ 选中指示器有滑过动画
- [ ] 点击「📖 阅读」布局图标 → 所有窗口位置/大小在 300ms 内过渡到阅读布局
- [ ] 点击「✏️ 刷题」→ 窗口重新排布
- [ ] 长按藏宝图节点 > 0.5s → 鼠标变 grab，可拖动重排
- [ ] 拖动讲义/习题窗口标题栏 → 窗口跟随移动
- [ ] hover Dock 图标 → 上浮 + tooltip 显示快捷键
- [ ] 点击「今日打卡」按钮 → 印章式反馈，状态变为「已打卡 23min」
- [ ] AI 浮窗输入文字回车 → 假 AI 流式回复

## 文件结构

```
demo/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html
├── README.md
└── src/
    ├── main.tsx              React 入口
    ├── App.tsx               顶层装配
    ├── styles/
    │   ├── tokens.css        设计 token（色板/字体/几何）
    │   └── globals.css       reset + 字体 + 纸纹底
    ├── components/
    │   ├── TopBar.tsx        顶部状态栏
    │   ├── ModeToggle.tsx    精通/探索 印章切换
    │   ├── LayoutIcons.tsx   📖✏️💻 布局图标
    │   ├── TreasureMap.tsx   藏宝图（罗盘节点 + 拖拽）
    │   ├── ProfileRadar.tsx  画像雷达图
    │   ├── Calendar.tsx      日历 + 热力 + 任务
    │   ├── FloatingWindow.tsx 通用可拖动窗口
    │   ├── WindowContents.tsx 讲义/习题/笔记/导图 内容
    │   ├── ChatFloat.tsx     AI 浮窗
    │   └── Dock.tsx          底部 9 图标
    ├── data/
    │   └── sample.ts         假数据
    ├── store/
    │   └── useWorkspace.ts   Zustand store
    └── lib/
        └── layouts.ts        3 套布局预设
```

## 不在范围内（明确不做）

- 真实 AI 对话（demo 用 setInterval 模拟流式打字）
- localStorage 持久化
- 真实文件上传/OCR
- 真实键盘快捷键系统（只展示标签）
- 移动端响应式（PC only，1440×900 起步）
- 突击模式、布局自定义保存（仅占位按钮）

## 后续扩展

如果 demo 通过，下一步可以：
1. 把每个组件拆成独立文件（结构已预留）
2. 接入 `@xyflow/react` 替换自实现藏宝图
3. 接入 `@dnd-kit` 替换自实现窗口拖拽
4. 接入 Zustand 的完整 slice（windowSlice / mapSlice / profileSlice）
5. 接 WebSocket 流式 AI 对话