// src/lib/dockPositions.tsx
// Dock 位置查询接口（v4 § 2.2.4 动画需要）

import { createContext, useContext, useRef, useLayoutEffect, useState, useMemo, type ReactNode } from 'react';
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
  // 用 ref 存 DOM 节点 → 不会触发重渲染
  const refs = useRef<Map<AppId, HTMLElement>>(new Map());
  const [highlightAppId, setHighlightAppId] = useState<AppId | null>(null);

  // useMemo 稳定 api 对象 identity，避免 DockButton 的 useLayoutEffect 无限循环
  const api: DockPositionsApi = useMemo(() => ({
    getDockPosition: (appId) => {
      const el = refs.current.get(appId);
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return { x: r.left, y: r.top, w: r.width, h: r.height };
    },
    // register 只操作 ref，不触发 setState（避免无限重渲染）
    register: (appId, el) => {
      if (el) refs.current.set(appId, el);
      else refs.current.delete(appId);
    },
    highlight: (appId) => {
      setHighlightAppId(appId);
      if (appId) {
        setTimeout(() => setHighlightAppId(null), 600);
      }
    },
    highlightAppId,
  }), [highlightAppId]);

  return <DockPositionsContext.Provider value={api}>{children}</DockPositionsContext.Provider>;
}

export function useDockPositions(): DockPositionsApi {
  const ctx = useContext(DockPositionsContext);
  if (!ctx) throw new Error('useDockPositions must be used inside DockPositionsProvider');
  return ctx;
}

/**
 * 给 Dock 按钮调用：注册 ref 与 appId 映射
 * 用法：const setRef = useDockRef(appId); <button ref={setRef} ... />
 */
export function useDockRef(appId: AppId) {
  const api = useDockPositions();
  const [node, setNode] = useState<HTMLElement | null>(null);

  // 把 api 存到 ref，避免 useLayoutEffect 依赖 api identity
  const apiRef = useRef(api);
  apiRef.current = api;

  // 只依赖 [appId, node]，api 通过 ref 访问
  useLayoutEffect(() => {
    if (node) {
      apiRef.current.register(appId, node);
      return () => apiRef.current.register(appId, null);
    }
  }, [appId, node]);

  return setNode;
}