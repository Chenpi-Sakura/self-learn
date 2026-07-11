/**
 * demo 用假数据。所有坐标基于 1024×640 的 SVG viewBox。
 * 真实工程应改为后端拉取。
 */

// ───── 藏宝图节点 ─────
export type NodeKind = 'done' | 'current' | 'key' | 'normal' | 'locked' | 'dormant';
export interface MapNode {
  id: string;
  x: number;          // SVG 坐标 (0..1000)
  y: number;
  label: string;
  kind: NodeKind;
  /** 关卡形式角标 */
  form?: '📖' | '🤖' | '💻' | '🎯' | '🎧';
  /** 关卡编号 */
  no?: string;
}

export const mapNodes: MapNode[] = [
  { id: 'n1', x: 120, y: 110, label: '词嵌入',     kind: 'done',     form: '📖', no: '01' },
  { id: 'n2', x: 240, y: 170, label: 'RNN',         kind: 'done',     form: '📖', no: '02' },
  { id: 'n3', x: 380, y: 130, label: 'LSTM',        kind: 'done',     form: '💻', no: '03' },
  { id: 'n4', x: 380, y: 250, label: 'GRU',         kind: 'current',  form: '💻', no: '04' },
  { id: 'n5', x: 540, y: 190, label: '自注意力机制', kind: 'key',      form: '🤖', no: '05' },
  { id: 'n6', x: 700, y: 130, label: 'Transformer',  kind: 'normal',  form: '💻', no: '06' },
  { id: 'n7', x: 700, y: 270, label: '位置编码',     kind: 'normal',   form: '📖', no: '07' },
  { id: 'n8', x: 860, y: 200, label: '多头注意力',   kind: 'locked',   form: '🤖', no: '08' },
  { id: 'n9', x: 540, y: 360, label: 'Seq2Seq',      kind: 'normal',   form: '🎯', no: '09' },
  // 休眠分支
  { id: 'n10', x: 240, y: 350, label: '传统机器学习', kind: 'dormant', form: '📖', no: 'A' },
  { id: 'n11', x: 380, y: 430, label: 'CRF',          kind: 'dormant', form: '📖', no: 'B' },
  // 待解锁远端
  { id: 'n12', x: 920, y: 360, label: 'RLHF',         kind: 'locked',   form: '🎯', no: '12' },
];

// 连线（按节点 id 表达）
export const mapEdges: Array<[string, string]> = [
  ['n1', 'n2'],
  ['n2', 'n3'],
  ['n2', 'n4'],
  ['n3', 'n5'],
  ['n4', 'n5'],
  ['n5', 'n6'],
  ['n5', 'n7'],
  ['n6', 'n8'],
  ['n7', 'n8'],
  ['n5', 'n9'],
  // 休眠分支
  ['n2', 'n10'],
  ['n10', 'n11'],
  // 远端
  ['n8', 'n12'],
];

// ───── 画像 6 维度 ─────
export interface ProfileDim {
  key: string;
  label: string;
  value: number;     // 0..1
  /** 是否正在脉动（demo 效果） */
  pulsing?: boolean;
}

export const profile: ProfileDim[] = [
  { key: 'und', label: '理解', value: 0.78 },
  { key: 'rzn', label: '推理', value: 0.62 },
  { key: 'exp', label: '表达', value: 0.55 },
  { key: 'app', label: '应用', value: 0.70 },
  { key: 'trn', label: '迁移', value: 0.74, pulsing: true },
  { key: 'crt', label: '创造', value: 0.48 },
];

// ───── 日历热力（7 列 × 6 行） ─────
// 0=无 1=轻 2=中 3=高 4=极高
export const heatMap: number[][] = (() => {
  const rows: number[][] = [];
  // 用确定性伪随机，让 demo 每次一致
  const seed = [3, 1, 0, 2, 4, 0, 1, 2, 1, 3, 4, 2, 0, 1, 3, 4, 2, 1, 0, 3, 4, 2, 1, 0, 3, 2, 4, 1, 3, 0, 0, 1, 2, 3, 4, 1, 2, 3, 0, 1, 3, 2];
  for (let r = 0; r < 6; r++) {
    const row: number[] = [];
    for (let c = 0; c < 7; c++) {
      row.push(seed[r * 7 + c] ?? 0);
    }
    rows.push(row);
  }
  return rows;
})();

// 今日 = 2026/7/10  -> 第 2 行 第 5 列（周五），索引 [1][4]
export const todayIndex = { row: 1, col: 4 };

// ───── 任务列表 ─────
export interface Task {
  id: string;
  title: string;
  form: '📖' | '🤖' | '💻' | '🎯' | '🎧';
  status: 'done' | 'doing' | 'todo';
  progress: number;
  eta: string;
}

export const tasks: Task[] = [
  { id: 't1', title: '自注意力机制 · 讲义阅读', form: '📖', status: 'done',  progress: 1.00, eta: '12 min' },
  { id: 't2', title: 'Q/K/V 三元组 · 基础练习', form: '🤖', status: 'doing', progress: 0.62, eta: '≈ 8 min' },
  { id: 't3', title: '实现 scaled-dot-product', form: '💻', status: 'doing', progress: 0.30, eta: '≈ 15 min' },
  { id: 't4', title: 'Attention 任务挑战',       form: '🎯', status: 'todo',  progress: 0.00, eta: '≈ 20 min' },
];

// ───── Dock 9 应用 ─────
export interface DockApp {
  id: string;
  glyph: string;       // 单字徽章
  name: string;
  badge?: number;      // 右上红点
}

export const dockApps: DockApp[] = [
  { id: 'map',        glyph: '藏', name: '藏宝图',     badge: 0 },
  { id: 'ai',         glyph: '智', name: 'AI 对话',    badge: 2 },
  { id: 'doc',        glyph: '讲', name: '讲义阅读器' },
  { id: 'ex',         glyph: '习', name: '习题面板' },
  { id: 'code',       glyph: '码', name: '代码实验室' },
  { id: 'note',       glyph: '笔', name: '笔记本' },
  { id: 'mind',       glyph: '图', name: '思维导图' },
  { id: 'res',        glyph: '库', name: '我的资源' },
  { id: 'dash',       glyph: '表', name: '学习仪表盘' },
];

// ───── 浮动窗口初始内容 ─────
export const docSample = {
  title: '自注意力机制 · 第 3 章',
  chapter: '第三章 / 共七章',
  body: [
    '自注意力（Self-Attention）是 Transformer 的核心机制。它允许序列中的每个位置同时关注所有其他位置，从而捕获长距离依赖。',
    '形式上，给定输入序列 X ∈ ℝⁿˣᵈ ，我们通过三个可学习的线性投影得到查询 Q、键 K、值 V 三组向量：',
    'Q = X·Wq ,   K = X·Wk ,   V = X·Wv',
    '随后计算注意力权重：对每个查询向量 qᵢ，用它与所有键 kⱼ 的点积经 softmax 归一化，再加权聚合值向量 vⱼ。',
    '下一节我们讨论 scaled dot-product 的数值稳定性问题，以及多头注意力如何并行学习不同的子空间表征。',
  ] as string[],
  footnote: '·  本章预计阅读 12 分钟 · 关联资源 2 篇 · 含 1 道思考题',
};

export const exSample = {
  title: '今日练习 · 5 / 12',
  q: '给定序列 ["我", "爱", "自然", "语言"] ，若 Q/K/V 维度均为 4，自注意力输出维度是？',
  options: ['A. 4', 'B. 与序列长度 n 相同', 'C. 与 d_model 相同', 'D. 取决于 head 数'],
  hint: '提示：回想 Q = X·Wᵠ 的形状变化',
  selected: 0,
};