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