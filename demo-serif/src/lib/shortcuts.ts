// src/lib/shortcuts.ts
// 快捷键系统 + scope 管理（v4 § 3.8）

import { useWorkspace } from '../store/useWorkspace';
import { readingLayout, practiceLayout, codingLayout } from './layouts';

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