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
