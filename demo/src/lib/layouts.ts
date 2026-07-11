/**
 * 三套布局预设：每个布局定义一组浮动窗口的位置/尺寸。
 * 坐标基于 1440×900 视口（状态栏 48 + Dock 72 = 上下预留 120，中间可用区约 1440×780）。
 * 实际尺寸会在窗口组件里 clamp 到视口大小。
 */

export interface WindowBox {
  appId: 'doc' | 'ex' | 'ai' | 'note' | 'mind' | 'code' | 'res' | 'dash';
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface LayoutPreset {
  id: 'reading' | 'practice' | 'coding';
  label: string;
  glyph: string;
  windows: WindowBox[];
}

/** 阅读模式：讲义占左半边，笔记和导图叠在右半边，AI 浮窗保留 */
const reading: LayoutPreset = {
  id: 'reading',
  label: '阅读模式',
  glyph: '📖',
  windows: [
    { appId: 'doc', x: 380, y: 70,  w: 620, h: 620 },
    { appId: 'note', x: 1010, y: 70,  w: 410, h: 400 },
    { appId: 'mind', x: 1010, y: 480, w: 410, h: 210 },
  ],
};

/** 刷题模式：习题居中放大，AI 移到右侧 */
const practice: LayoutPreset = {
  id: 'practice',
  label: '刷题模式',
  glyph: '✏️',
  windows: [
    { appId: 'ex',  x: 410, y: 80,  w: 600, h: 640 },
    { appId: 'note', x: 1020, y: 80, w: 400, h: 320 },
    { appId: 'doc', x: 1020, y: 410, w: 400, h: 310 },
  ],
};

/** 代码实验模式：代码编辑器占主体，讲义和终端分居上下 */
const coding: LayoutPreset = {
  id: 'coding',
  label: '代码实验',
  glyph: '💻',
  windows: [
    { appId: 'code', x: 380, y: 70,  w: 660, h: 470 },
    { appId: 'doc',  x: 380, y: 550, w: 660, h: 170 },
    { appId: 'note', x: 1050, y: 70, w: 370, h: 650 },
  ],
};

export const layouts: Record<LayoutPreset['id'], LayoutPreset> = {
  reading,
  practice,
  coding,
};

export const layoutOrder: LayoutPreset['id'][] = ['reading', 'practice', 'coding'];