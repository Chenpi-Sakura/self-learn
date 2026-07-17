import { useEffect, useMemo, useRef, useState } from 'react';
import type { MouseEvent as ReactMouseEvent } from 'react';
import type { ResourceListItem } from '../api/resources';

/**
 * 共用资源列表 / 网格组件（UX-final）。
 *
 * grid 模式交互（用于 ResourceLibrary）：
 *   - 单击资源 → 单选（替换 selected 为这 1 个）
 *   - Shift+单击 → 切换该资源的选中（多选模式）
 *   - 双击资源 → 打开 MD 浏览器 (onOpen)
 *   - 鼠标在空白处按下 + 拖动 → 矩形框选
 *   - 右键 → onContextMenu（删除/重命名）
 *   - 双击 label → 进入重命名编辑（仅 grid 模式）
 *   - 拖动单资源 → onMove (dataTransfer.setData('resource:id', id))
 *
 * picker 模式（用于 ExtractTopicsDialog）：
 *   - 单击 = 切换选中（无 shift 区别）
 */
export interface ResourceListViewProps {
  items: ResourceListItem[];
  mode?: 'grid' | 'picker';
  selectedIds?: Set<string>;
  onSelectionChange?: (ids: Set<string>) => void;
  onOpen?: (id: string) => void;
  onContextMenu?: (e: ReactMouseEvent, id: string) => void;
  onRename?: (id: string, newName: string) => Promise<void>;
  onMove?: (id: string, newName: string) => Promise<void>;
  onDelete?: (id: string) => void | Promise<void>;
  /** 在空白处右键菜单触发的"新建文件夹" */
  onCreateFolder?: () => void;
}

interface DragRect {
  startX: number;
  startY: number;
  endX: number;
  endY: number;
}

export function ResourceListView({
  items,
  mode = 'grid',
  selectedIds = new Set(),
  onSelectionChange,
  onOpen,
  onContextMenu,
  onRename,
  onMove,
  onDelete,
  onCreateFolder,
}: ResourceListViewProps) {
  const [editing, setEditing] = useState<{ id: string; value: string } | null>(null);

  // 网格列数自适应：实际容器宽度 / 140（不再跟视口挂钩，窗口内部宽度 ≠ 视口宽）。
  const [cols, setCols] = useState<number>(4);
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const recalc = () => {
      const w = el.clientWidth;
      setCols(Math.max(2, Math.floor(w / 140)));
    };
    recalc();
    const ro = new ResizeObserver(recalc);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // 按中文 locale 排序（稳定排序避免 React 抖动）
  const sorted = useMemo(
    () => [...items].sort((a, b) => a.name.localeCompare(b.name, 'zh')),
    [items],
  );

  // 框选状态：拖动时画一个矩形，鼠标抬起时把命中项加入 selected。
  // 用 document-level 监听 mouseup，避免子 div 的 mousedown 拦截冒泡。
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [dragRect, setDragRect] = useState<DragRect | null>(null);
  const dragStartRef = useRef<{ x: number; y: number } | null>(null);
  const itemRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  // 右键菜单状态：区分 item（资源右键）和 background（空白右键）
  const [ctxMenu, setCtxMenu] = useState<
    | { kind: 'item'; id: string; itemName: string; x: number; y: number }
    | { kind: 'background'; x: number; y: number }
    | null
  >(null);
  useEffect(() => {
    if (!ctxMenu) return;
    const close = () => setCtxMenu(null);
    document.addEventListener('click', close);
    document.addEventListener('contextmenu', close);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close();
    };
    window.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('click', close);
      document.removeEventListener('contextmenu', close);
      window.removeEventListener('keydown', onKey);
    };
  }, [ctxMenu]);

  // 新建文件夹的回调（由 ResourceLibrary 注入）

  const hitTest = (rect: DragRect): Set<string> => {
    const minX = Math.min(rect.startX, rect.endX);
    const maxX = Math.max(rect.startX, rect.endX);
    const minY = Math.min(rect.startY, rect.endY);
    const maxY = Math.max(rect.startY, rect.endY);
    const hits = new Set<string>();
    for (const [id, el] of itemRefs.current.entries()) {
      const er = el.getBoundingClientRect();
      // 两个矩形相交（无包含关系要求）
      if (er.right < minX || er.left > maxX || er.bottom < minY || er.top > maxY) continue;
      hits.add(id);
    }
    return hits;
  };

  // 注：因为子缩略图上 onMouseDown 阻止了冒泡，
  // 用 container 的 mousedown 仅当起点在容器空白处（不是缩略图）时启动。
  // mouseup 也用 document 监听，确保拖框松手总能命中。
  useEffect(() => {
    if (!dragStartRef.current) return;
    const onMove = (e: MouseEvent) => {
      if (!dragStartRef.current) return;
      setDragRect({
        startX: dragStartRef.current.x,
        startY: dragStartRef.current.y,
        endX: e.clientX,
        endY: e.clientY,
      });
    };
    const onUp = (e: MouseEvent) => {
      if (!dragStartRef.current) return;
      const rect = {
        startX: dragStartRef.current.x,
        startY: dragStartRef.current.y,
        endX: e.clientX,
        endY: e.clientY,
      } as DragRect;
      const hits = hitTest(rect);
      const startedInContainer = containerRef.current?.contains(e.target as Node) ?? false;
      if (hits.size > 0 && onSelectionChange) {
        onSelectionChange(hits);
      } else if (hits.size === 0 && startedInContainer && onSelectionChange && selectedIds.size > 0) {
        // 起点 + 终点都在容器空白处 → 清空选中
        onSelectionChange(new Set());
      }
      dragStartRef.current = null;
      setDragRect(null);
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
    return () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dragRect]); // 每次 dragRect 改变时 re-attach（仅用于 cleanup 衔接）

  const onContainerMouseDown = (e: ReactMouseEvent<HTMLDivElement>) => {
    if (mode !== 'grid') return;
    if (e.button !== 0) return;
    // 仅当按下时不在任何已知缩略图内才启动框选
    const target = e.target as HTMLElement;
    let insideItem = false;
    for (const el of itemRefs.current.values()) {
      if (el.contains(target) || el === target) {
        insideItem = true;
        break;
      }
    }
    if (insideItem) return;
    dragStartRef.current = { x: e.clientX, y: e.clientY };
    setDragRect({ startX: e.clientX, startY: e.clientY, endX: e.clientX, endY: e.clientY });
  };

  return (
    <div
      ref={containerRef}
      onMouseDown={onContainerMouseDown}
      onContextMenu={(e) => {
        // 仅在 picker 不响应右键；grid 模式下若点在已知缩略图外则显示"新建文件夹"菜单
        if (mode !== 'grid') return;
        const target = e.target as HTMLElement;
        let insideItem = false;
        for (const el of itemRefs.current.values()) {
          if (el.contains(target) || el === target) {
            insideItem = true;
            break;
          }
        }
        if (insideItem) return; // 缩略图自身走各自的 onContextMenu
        if (!onCreateFolder) return;
        e.preventDefault();
        setCtxMenu({ kind: 'background', x: e.clientX, y: e.clientY });
      }}
      style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${cols}, 1fr)`,
        gap: 12,
        padding: 12,
        overflow: 'auto',
        height: '100%',
        boxSizing: 'border-box',
        position: 'relative',
        userSelect: 'none',
        alignItems: 'start',
        alignContent: 'start',
      }}
    >
      {sorted.map((r) => {
        const isSelected = selectedIds.has(r.id);
        const isFolder = !r.name.endsWith('.md');
        const displayName = r.name.split('/').pop() ?? r.name;
        return (
          <div
            key={r.id}
            ref={(el) => {
              if (el) itemRefs.current.set(r.id, el);
              else itemRefs.current.delete(r.id);
            }}
            draggable={mode === 'grid'}
            onDragStart={(e) => {
              if (mode !== 'grid') return;
              e.dataTransfer.setData('resource:id', r.id);
            }}
            onClick={(e) => {
              if (mode === 'picker') {
                if (onSelectionChange) {
                  const ns = new Set(selectedIds);
                  if (ns.has(r.id)) ns.delete(r.id);
                  else ns.add(r.id);
                  onSelectionChange(ns);
                }
                return;
              }
              // grid 模式：单击单选；Shift+单击切换多选
              if (onSelectionChange) {
                if (e.shiftKey) {
                  const ns = new Set(selectedIds);
                  if (ns.has(r.id)) ns.delete(r.id);
                  else ns.add(r.id);
                  onSelectionChange(ns);
                } else {
                  // 单击 → **单选**（只保留这一个）
                  onSelectionChange(new Set([r.id]));
                }
              }
            }}
            onDoubleClick={() => {
              if (mode !== 'grid') return;
              if (onOpen) onOpen(r.id);
            }}
            onContextMenu={(e) => {
              if (mode === 'picker') return;
              e.preventDefault();
              setCtxMenu({ kind: 'item', id: r.id, itemName: r.name, x: e.clientX, y: e.clientY });
            }}
            style={{
              cursor: 'pointer',
              padding: 8,
              borderRadius: 6,
              border: isSelected ? '2px solid #1B3B6F' : '1px solid #E5E5E0',
              position: 'relative',
              background: isSelected ? 'rgba(27,59,111,0.04)' : 'transparent',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              maxWidth: 140,
              minWidth: 100,
              justifySelf: 'start',
            }}
          >
            {isSelected && (
              <div
                style={{
                  position: 'absolute',
                  top: 4,
                  right: 4,
                  color: '#1B3B6F',
                  fontWeight: 700,
                  fontSize: 16,
                }}
              >
                ✓
              </div>
            )}
            <div style={{ fontSize: 48, textAlign: 'center', lineHeight: 1 }}>
              {isFolder ? '📁' : '📄'}
            </div>
            {editing?.id === r.id ? (
              <input
                autoFocus
                value={editing.value}
                onChange={(e) => setEditing({ id: r.id, value: e.target.value })}
                onBlur={async () => {
                  const newName = editing.value.trim();
                  if (newName && newName !== r.name) {
                    try {
                      if (onRename) await onRename(r.id, newName);
                      else if (onMove) await onMove(r.id, newName);
                    } catch (err) {
                      console.error('[ResourceListView] rename failed', err);
                    }
                  }
                  setEditing(null);
                }}
                onKeyDown={async (e) => {
                  if (e.key === 'Enter') {
                    const newName = editing.value.trim();
                    if (newName && newName !== r.name) {
                      try {
                        if (onRename) await onRename(r.id, newName);
                        else if (onMove) await onMove(r.id, newName);
                      } catch (err) {
                        console.error('[ResourceListView] rename failed', err);
                      }
                    }
                    setEditing(null);
                  } else if (e.key === 'Escape') {
                    setEditing(null);
                  }
                }}
                onClick={(e) => e.stopPropagation()}
                style={{ width: '100%', fontSize: 12 }}
              />
            ) : (
              <div
                style={{
                  fontSize: 13,
                  textAlign: 'center',
                  wordBreak: 'break-all',
                  marginTop: 4,
                }}
                onDoubleClick={(e) => {
                  if (mode === 'picker') return;
                  e.stopPropagation();
                  setEditing({ id: r.id, value: r.name });
                }}
              >
                {displayName}
              </div>
            )}
            {void onCreateFolder}
          </div>
        );
      })}
      {/* 右键菜单浮层：item（资源右键）/ background（空白右键） */}
      {ctxMenu && (() => {
        const itemW = 180;
        const itemH = ctxMenu.kind === 'item' ? 96 : 56;
        const maxX = window.innerWidth - itemW - 4;
        const maxY = window.innerHeight - itemH - 4;
        const x = Math.min(ctxMenu.x, maxX);
        const y = Math.min(ctxMenu.y, maxY);
        const buttonStyle = (hoverBg: string): React.CSSProperties => ({
          display: 'block',
          width: '100%',
          padding: '6px 12px',
          background: 'transparent',
          border: 'none',
          borderRadius: 4,
          textAlign: 'left',
          cursor: 'pointer',
          fontSize: 13,
        });
        const enter = (e: ReactMouseEvent<HTMLButtonElement>) =>
          (e.currentTarget.style.background = 'rgba(27,59,111,0.08)');
        const leave = (e: ReactMouseEvent<HTMLButtonElement>) =>
          (e.currentTarget.style.background = 'transparent');
        const enterDanger = (e: ReactMouseEvent<HTMLButtonElement>) =>
          (e.currentTarget.style.background = 'rgba(188,71,73,0.08)');
        const menuStyle: React.CSSProperties = {
          position: 'fixed',
          left: x,
          top: y,
          minWidth: 180,
          background: '#FBF7EC',
          border: '1px solid #1B3B6F',
          borderRadius: 6,
          boxShadow: '0 4px 16px rgba(0,0,0,0.18)',
          padding: 4,
          zIndex: 10000,
          fontFamily: 'HedvigLettersSerif, serif',
        };
        if (ctxMenu.kind === 'item') {
          return (
            <div role="menu" onClick={(e) => e.stopPropagation()} style={menuStyle}>
              <button
                type="button"
                onClick={() => {
                  setEditing({ id: ctxMenu.id, value: ctxMenu.itemName });
                  setCtxMenu(null);
                }}
                style={buttonStyle('rgba(27,59,111,0.08)')}
                onMouseEnter={enter}
                onMouseLeave={leave}
              >
                ✎ 重命名
              </button>
              <button
                type="button"
                onClick={() => {
                  if (window.confirm(`确认删除「${ctxMenu.itemName}」？`)) {
                    onDelete?.(ctxMenu.id);
                  }
                  setCtxMenu(null);
                }}
                style={{ ...buttonStyle(''), color: '#BC4749' }}
                onMouseEnter={enterDanger}
                onMouseLeave={leave}
              >
                🗑 删除
              </button>
            </div>
          );
        }
        // background：空白处右键
        return (
          <div role="menu" onClick={(e) => e.stopPropagation()} style={menuStyle}>
            <button
              type="button"
              onClick={() => {
                onCreateFolder?.();
                setCtxMenu(null);
              }}
              style={buttonStyle('rgba(27,59,111,0.08)')}
              onMouseEnter={enter}
              onMouseLeave={leave}
            >
              📁 新建文件夹
            </button>
          </div>
        );
      })()}
      {/* 框选矩形浮层（与容器同坐标系，避免 fixed 滚动条偏移） */}
      {dragRect && (() => {
        const cr = containerRef.current?.getBoundingClientRect();
        if (!cr) return null;
        const minX = Math.min(dragRect.startX, dragRect.endX) - cr.left + containerRef.current!.scrollLeft;
        const minY = Math.min(dragRect.startY, dragRect.endY) - cr.top + containerRef.current!.scrollTop;
        const w = Math.abs(dragRect.endX - dragRect.startX);
        const h = Math.abs(dragRect.endY - dragRect.startY);
        return (
          <div
            style={{
              position: 'absolute',
              left: minX,
              top: minY,
              width: w,
              height: h,
              border: '1px dashed #1B3B6F',
              background: 'rgba(27,59,111,0.08)',
              pointerEvents: 'none',
              zIndex: 10,
            }}
          />
        );
      })()}
    </div>
  );
}