import { useEffect, useRef, useState, useCallback } from 'react';
import type { WindowState } from '../store/useWorkspace';
import { useWorkspace } from '../store/useWorkspace';
import { ContextMenu, type ContextMenuItem } from './ContextMenu';
import './Window.css';

interface Props {
  win: WindowState;
  title: string;
  isKey?: boolean;
  children: React.ReactNode;
}

type ResizeDir = 'br' | 'bl';

export function Window({ win, title, isKey, children }: Props) {
  const moveWindow = useWorkspace((s) => s.moveWindow);
  const focusWindow = useWorkspace((s) => s.focusWindow);
  const toggleMinimize = useWorkspace((s) => s.toggleMinimize);
  const toggleMaximize = useWorkspace((s) => s.toggleMaximize);
  const togglePin = useWorkspace((s) => s.togglePin);
  const closeWindow = useWorkspace((s) => s.closeWindow);
  const resizeWindow = useWorkspace((s) => s.resizeWindow);
  const focusedId = useWorkspace((s) => s.focusedId);

  const [dragging, setDragging] = useState(false);
  const [resizing, setResizing] = useState<ResizeDir | null>(null);
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number } | null>(null);
  const dragStart = useRef({ x: 0, y: 0 });
  const winStart = useRef({ x: 0, y: 0 });

  const focused = focusedId === win.id;

  const handleTitleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return; // 左键
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

  // ---- Resize 拖拽 ----
  const resizeStart = useRef({
    mouseX: 0,
    mouseY: 0,
    winX: 0,
    winY: 0,
    winW: 0,
    winH: 0,
  });

  const handleResizeDown = (dir: ResizeDir) => (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    if (win.maximized) return; // 最大化时不允许 resize
    e.stopPropagation();
    e.preventDefault();
    focusWindow(win.id);
    resizeStart.current = {
      mouseX: e.clientX,
      mouseY: e.clientY,
      winX: win.x,
      winY: win.y,
      winW: win.w,
      winH: win.h,
    };
    setResizing(dir);
  };

  useEffect(() => {
    if (!resizing) return;
    const handleMouseMove = (e: MouseEvent) => {
      const s = resizeStart.current;
      const dx = e.clientX - s.mouseX;
      const dy = e.clientY - s.mouseY;
      if (resizing === 'br') {
        resizeWindow(win.id, { w: s.winW + dx, h: s.winH + dy });
      } else if (resizing === 'bl') {
        // 左下角：左边缩进 → x 增加，宽度同步减少
        resizeWindow(win.id, { x: s.winX + dx, w: s.winW - dx, h: s.winH + dy });
      }
    };
    const handleMouseUp = () => setResizing(null);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [resizing, win.id, resizeWindow]);

  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setCtxMenu({ x: e.clientX, y: e.clientY });
  }, []);

  const handleCtrlClick = useCallback((e: React.MouseEvent, action: () => void) => {
    e.stopPropagation();
    action();
  }, []);

  const handleTitleDoubleClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    toggleMaximize(win.id);
  }, [toggleMaximize, win.id]);

  const pinIcon = win.pinLevel === 'always' ? '🔒' : win.pinLevel === 'normal' ? '📌' : null;

  const menuItems: ContextMenuItem[] = [];
  if (win.pinLevel === 'normal') {
    menuItems.push({ type: 'action' as const, label: '取消置顶', icon: '📍', action: () => togglePin(win.id) });
  } else if (win.pinLevel === 'none') {
    menuItems.push({ type: 'action' as const, label: '置顶窗口', icon: '📌', action: () => togglePin(win.id) });
  }
  // always 类（chat 等）不显示置顶项
  if (menuItems.length > 0) menuItems.push({ type: 'separator' as const });
  menuItems.push({ type: 'action' as const, label: '最小化', icon: '—', action: () => toggleMinimize(win.id) });
  menuItems.push({ type: 'action' as const, label: win.maximized ? '还原' : '最大化', icon: win.maximized ? '❐' : '□', action: () => toggleMaximize(win.id) });
  menuItems.push({ type: 'action' as const, label: '关闭窗口', icon: '✕', danger: true, action: () => closeWindow(win.id) });

  const cls = [
    'win',
    focused ? 'focused' : '',
    win.minimized ? 'minimized' : '',
    (dragging || resizing) ? 'dragging' : '',
    win.maximized ? 'maximized' : '',
    resizing === 'br' ? 'resizing-br' : '',
    resizing === 'bl' ? 'resizing-bl' : '',
  ].filter(Boolean).join(' ');

  const dotCls = 'dot' + (isKey ? ' key' : '');

  // 最大化状态：仍走 x/y/w/h + transform，让 CSS transition 接管插值（v4 § 2.2.2）
  const TOPBAR_H = 52;
  const DOCK_H = 72;
  const style: React.CSSProperties = {
    zIndex: win.z,
  };
  if (win.minimized) {
    // Task 14 会替换为 Dock 位置拉拽逻辑
    style.opacity = 0;
    style.pointerEvents = 'none';
  } else if (win.maximized) {
    style.left = 0;
    style.top = 0;
    style.width = '100%';
    style.height = `calc(100vh - ${TOPBAR_H}px - ${DOCK_H}px)`;
    style.transform = `translate(0, ${TOPBAR_H}px)`;
  } else {
    style.width = win.w;
    style.height = win.h;
    style.left = 0;
    style.top = 0;
    style.transform = `translate(${win.x}px, ${win.y}px)`;
  }

  return (
    <>
      <div
        className={cls}
        style={style}
        onMouseDown={() => focusWindow(win.id)}
      >
        <div
          className="win-title"
          onMouseDown={handleTitleMouseDown}
          onDoubleClick={handleTitleDoubleClick}
          onContextMenu={handleContextMenu}
        >
          {pinIcon ? (
            <span className="pin-icon" title={win.pinLevel === 'always' ? '系统置顶' : '已置顶'}>{pinIcon}</span>
          ) : (
            <span className={dotCls} />
          )}
          <span className="name">{title}</span>
          <div className="ctrls">
            <button className="ctrl" title="最小化" onClick={(e) => handleCtrlClick(e, () => toggleMinimize(win.id))}>—</button>
            <button className="ctrl" title={win.maximized ? '还原' : '最大化'} onClick={(e) => handleCtrlClick(e, () => toggleMaximize(win.id))}>□</button>
            <button className="ctrl close" title="关闭" onClick={(e) => handleCtrlClick(e, () => {
              // 关闭动画：先设 minimized 触发淡出，220ms 后才真正关闭
              if (!win.minimized) toggleMinimize(win.id);
              setTimeout(() => closeWindow(win.id), 220);
            })}>×</button>
          </div>
        </div>
        <div className="win-body">{children}</div>
        {!win.maximized && !win.minimized && (
          <>
            <span className="resize-handle rh-br" onMouseDown={handleResizeDown('br')} title="拖拽改变大小" />
            <span className="resize-handle rh-bl" onMouseDown={handleResizeDown('bl')} title="拖拽改变大小" />
          </>
        )}
      </div>
      {ctxMenu && (
        <ContextMenu
          x={ctxMenu.x}
          y={ctxMenu.y}
          items={menuItems}
          onClose={() => setCtxMenu(null)}
        />
      )}
    </>
  );
}
