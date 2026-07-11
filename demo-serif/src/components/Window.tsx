import { useEffect, useRef, useState } from 'react';
import type { WindowState } from '../store/useWorkspace';
import { useWorkspace } from '../store/useWorkspace';
import './Window.css';

interface Props {
  win: WindowState;
  title: string;
  isKey?: boolean;
  children: React.ReactNode;
}

export function Window({ win, title, isKey, children }: Props) {
  const moveWindow = useWorkspace((s) => s.moveWindow);
  const focusWindow = useWorkspace((s) => s.focusWindow);
  const focusedId = useWorkspace((s) => s.focusedId);
  const [dragging, setDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0 });
  const winStart = useRef({ x: 0, y: 0 });

  const focused = focusedId === win.id;

  const handleTitleMouseDown = (e: React.MouseEvent) => {
    dragStart.current = { x: e.clientX, y: e.clientY };
    winStart.current = { x: win.x, y: win.y };
    setDragging(true);
    focusWindow(win.id);
  };

  useEffect(() => {
    if (!dragging) return;
    const handleMouseMove = (e: MouseEvent) => {
      const dx = e.clientX - dragStart.current.x;
      const dy = e.clientY - dragStart.current.y;
      moveWindow(win.id, winStart.current.x + dx, winStart.current.y + dy);
    };
    const handleMouseUp = () => setDragging(false);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [dragging, win.id, moveWindow]);

  const cls = ['win', focused ? 'focused' : '', win.minimized ? 'minimized' : '', dragging ? 'dragging' : ''].filter(Boolean).join(' ');
  const dotCls = 'dot' + (isKey ? ' key' : '');

  const style: React.CSSProperties = {
    zIndex: win.z,
    width: win.w,
    height: win.h,
    left: 0,
    top: 0
  };
  if (!win.minimized) {
    style.transform = `translate(${win.x}px, ${win.y}px)`;
  }

  return (
    <div
      className={cls}
      style={style}
      onMouseDown={() => focusWindow(win.id)}
    >
      <div
        className="win-title"
        onMouseDown={handleTitleMouseDown}
      >
        <span className={dotCls} />
        <span className="name">{title}</span>
        <div className="ctrls">
          <button className="ctrl" title="最小化">—</button>
          <button className="ctrl" title="最大化">□</button>
          <button className="ctrl close" title="关闭">×</button>
        </div>
      </div>
      <div className="win-body">{children}</div>
    </div>
  );
}