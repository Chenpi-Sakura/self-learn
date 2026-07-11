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
// calendar 已并入 dashboard，本期移除（v4 § 3.15 + 附录 A #1）
// 保留空 export 防止连锁引用错误
export const calendar: { rows: { cells: ReturnType<typeof cell>[] }[]; today: number } = {
  today: 18,
  rows: [{ cells: [] as ReturnType<typeof cell>[] }],
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
