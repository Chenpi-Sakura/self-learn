import { useRef, useState, useCallback } from 'react';
import type { ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useWorkspace } from '../store/useWorkspace';

interface Props {
  appId: 'doc' | 'ex' | 'ai' | 'note' | 'mind' | 'code' | 'res' | 'dash';
  title: string;
  subtitle?: string;
  badge?: string;
  pinned?: boolean;
  children: ReactNode;
  /** 由父组件传位置（store 驱动布局切换动画） */
  x: number;
  y: number;
  w: number;
  h: number;
  z: number;
}

export function FloatingWindow({
  appId,
  title,
  subtitle,
  badge,
  pinned,
  children,
  x,
  y,
  w,
  h,
  z,
}: Props) {
  const focus = useWorkspace((s) => s.focusWindow);
  const moveWindow = useWorkspace((s) => s.moveWindow);
  const [dragging, setDragging] = useState(false);
  const startRef = useRef<{ mx: number; my: number; wx: number; wy: number } | null>(null);

  const onPointerDown = useCallback(
    (e: React.PointerEvent) => {
      const target = e.target as HTMLElement;
      if (target.closest('[data-no-drag]')) return;
      focus(appId);
      setDragging(true);
      startRef.current = { mx: e.clientX, my: e.clientY, wx: x, wy: y };
      (e.target as Element).setPointerCapture?.(e.pointerId);
    },
    [appId, focus, x, y],
  );

  const onPointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!dragging || !startRef.current) return;
      const dx = e.clientX - startRef.current.mx;
      const dy = e.clientY - startRef.current.my;
      moveWindow(appId, startRef.current.wx + dx, startRef.current.wy + dy);
    },
    [appId, dragging, moveWindow],
  );

  const onPointerUp = useCallback(() => {
    setDragging(false);
    startRef.current = null;
  }, []);

  return (
    <AnimatePresence>
      <motion.div
        className="fwin"
        style={{ left: x, top: y, width: w, height: h, zIndex: z }}
        onPointerDown={() => focus(appId)}
        initial={{ opacity: 0, scale: 0.97 }}
        animate={{
          opacity: 1,
          scale: 1,
          x: 0,
          y: 0,
          width: w,
          height: h,
          left: x,
          top: y,
        }}
        exit={{ opacity: 0, scale: 0.97 }}
        transition={{ type: 'spring', stiffness: 320, damping: 32, mass: 0.6 }}
      >
        <div
          className="fwin-title"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerLeave={onPointerUp}
          style={{ cursor: dragging ? 'grabbing' : 'grab' }}
        >
          <span className="fwin-pin" title={pinned ? '系统置顶' : '普通窗口'}>
            {pinned ? '🔒' : <svg width="11" height="11" viewBox="0 0 11 11"><path d="M 5.5 1 L 5.5 7 M 3 5 L 8 5 M 2.5 9 L 8.5 9" fill="none" stroke="currentColor" strokeWidth="1" /></svg>}
          </span>
          <span className="fwin-name mono">{title}</span>
          {subtitle && <span className="fwin-sub tiny">{subtitle}</span>}
          {badge && <span className="fwin-badge num mono">{badge}</span>}
          <span className="fwin-ctrls" data-no-drag>
            <button title="最小化" aria-label="最小化"><svg width="10" height="10" viewBox="0 0 10 10"><line x1="2" y1="5" x2="8" y2="5" stroke="currentColor" strokeWidth="1" /></svg></button>
            <button title="最大化" aria-label="最大化"><svg width="10" height="10" viewBox="0 0 10 10"><rect x="2" y="2" width="6" height="6" fill="none" stroke="currentColor" strokeWidth="1" /></svg></button>
            <button title="关闭" aria-label="关闭" className="fwin-close"><svg width="10" height="10" viewBox="0 0 10 10"><line x1="2" y1="2" x2="8" y2="8" stroke="currentColor" strokeWidth="1" /><line x1="8" y1="2" x2="2" y2="8" stroke="currentColor" strokeWidth="1" /></svg></button>
          </span>
        </div>
        <div className="fwin-body" data-no-drag>{children}</div>

        <style>{`
          .fwin {
            position: absolute;
            background: var(--paper-card);
            border: var(--border);
            display: flex;
            flex-direction: column;
            box-shadow: 1px 1px 0 0 var(--ink-soft);
          }
          .fwin-title {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 0 8px;
            height: 28px;
            background: var(--paper-deep);
            border-bottom: var(--border);
            user-select: none;
          }
          .fwin-pin { color: var(--ink-mute); display: inline-flex; }
          .fwin-name {
            font-size: 11px;
            letter-spacing: 0.06em;
            color: var(--ink);
          }
          .fwin-sub {
            margin-left: auto;
            font-size: 9px;
            color: var(--ink-mute);
          }
          .fwin-badge {
            padding: 1px 6px;
            background: var(--vermilion);
            color: var(--paper);
            font-size: 9px;
            letter-spacing: 0.04em;
          }
          .fwin-ctrls {
            display: inline-flex;
            gap: 0;
            margin-left: 8px;
          }
          .fwin-ctrls button {
            width: 22px;
            height: 22px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            color: var(--ink-mute);
            border-left: var(--border-fade);
          }
          .fwin-ctrls button:hover {
            background: var(--paper);
            color: var(--ink);
          }
          .fwin-ctrls .fwin-close:hover { background: var(--vermilion); color: var(--paper); }
          .fwin-body {
            flex: 1;
            min-height: 0;
            overflow: auto;
            background: var(--paper);
          }
        `}</style>
      </motion.div>
    </AnimatePresence>
  );
}