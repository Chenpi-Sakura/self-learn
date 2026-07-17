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
  onDelete?: (id: string) => Promise<void>;
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
}: ResourceListViewProps) {
  const [editing, setEditing] = useState<{ id: string; value: string } | null>(null);

  // 网格列数自适应：视口宽度 / 140。监听 resize 重新计算。
  const [cols, setCols] = useState<number>(() =>
    typeof window === 'undefined' ? 4 : Math.max(2, Math.floor(window.innerWidth / 140)),
  );
  useEffect(() => {
    const handler = () => setCols(Math.max(2, Math.floor(window.innerWidth / 140)));
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, []);

  // 按中文 locale 排序（稳定排序避免 React 抖动）
  const sorted = useMemo(
    () => [...items].sort((a, b) => a.name.localeCompare(b.name, 'zh')),
    [items],
  );

  // 框选状态：拖动时画一个矩形，鼠标抬起时把命中项加入 selected。
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [dragRect, setDragRect] = useState<DragRect | null>(null);
  const dragStartRef = useRef<{ x: number; y: number } | null>(null);
  const itemRefs = useRef<Map<string, HTMLDivElement>>(new Map());

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

  const onContainerMouseDown = (e: ReactMouseEvent<HTMLDivElement>) => {
    // 只在按下的是容器本身（空白处）时启动框选，点缩略图由子 div 的 onClick 处理
    if (mode !== 'grid') return;
    if (e.target !== e.currentTarget) return;
    if (e.button !== 0) return; // 只响应左键
    dragStartRef.current = { x: e.clientX, y: e.clientY };
    setDragRect({ startX: e.clientX, startY: e.clientY, endX: e.clientX, endY: e.clientY });
  };

  const onContainerMouseMove = (e: ReactMouseEvent<HTMLDivElement>) => {
    if (!dragStartRef.current) return;
    setDragRect({
      startX: dragStartRef.current.x,
      startY: dragStartRef.current.y,
      endX: e.clientX,
      endY: e.clientY,
    });
  };

  const onContainerMouseUp = (e: ReactMouseEvent<HTMLDivElement>) => {
    if (!dragStartRef.current || !dragRect) {
      dragStartRef.current = null;
      setDragRect(null);
      return;
    }
    const hits = hitTest(dragRect);
    if (hits.size > 0 && onSelectionChange) {
      // 替换式框选：拖框内所有项成为 selected（不含已有的全清）
      onSelectionChange(hits);
    } else if (hits.size === 0 && e.target === e.currentTarget) {
      // 框选落空 + 点的是空白 → 清空 selected
      if (onSelectionChange && selectedIds.size > 0) onSelectionChange(new Set());
    }
    dragStartRef.current = null;
    setDragRect(null);
  };

  return (
    <div
      ref={containerRef}
      onMouseDown={onContainerMouseDown}
      onMouseMove={onContainerMouseMove}
      onMouseUp={onContainerMouseUp}
      onMouseLeave={() => {
        if (dragStartRef.current) {
          dragStartRef.current = null;
          setDragRect(null);
        }
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
              onContextMenu?.(e, r.id);
            }}
            style={{
              cursor: 'pointer',
              padding: 8,
              borderRadius: 6,
              border: isSelected ? '2px solid #1B3B6F' : '1px solid #E5E5E0',
              position: 'relative',
              background: isSelected ? 'rgba(27,59,111,0.04)' : 'transparent',
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
            {/* 静默引用 onDelete 以避免"声明但不读取"的 lint 噪音（将来扩展用） */}
            {void onDelete}
          </div>
        );
      })}
      {/* 框选矩形浮层 */}
      {dragRect && (
        <div
          style={{
            position: 'fixed',
            left: Math.min(dragRect.startX, dragRect.endX),
            top: Math.min(dragRect.startY, dragRect.endY),
            width: Math.abs(dragRect.endX - dragRect.startX),
            height: Math.abs(dragRect.endY - dragRect.startY),
            border: '1px dashed #1B3B6F',
            background: 'rgba(27,59,111,0.08)',
            pointerEvents: 'none',
            zIndex: 9999,
          }}
        />
      )}
    </div>
  );
}