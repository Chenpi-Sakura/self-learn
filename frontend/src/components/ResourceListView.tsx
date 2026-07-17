import { useEffect, useMemo, useState } from 'react';
import type { MouseEvent } from 'react';
import type { ResourceListItem } from '../api/resources';

/**
 * 共用资源列表 / 网格组件。
 *
 * 模式：
 * - 'grid'：默认缩略图网格，单击触发 onOpen；右键触发 onContextMenu；
 *           双击标题进入重命名编辑态。
 * - 'picker'：多选模式（提炼对话框），单击切换选中；隐藏拖动 / 重命名 / 右键菜单。
 */
export interface ResourceListViewProps {
  items: ResourceListItem[];
  mode?: 'grid' | 'picker';
  selectedIds?: Set<string>;
  onSelectionChange?: (ids: Set<string>) => void;
  onOpen?: (id: string) => void;
  onContextMenu?: (e: MouseEvent, id: string) => void;
  onRename?: (id: string, newName: string) => Promise<void>;
  onMove?: (id: string, newName: string) => Promise<void>;
  onDelete?: (id: string) => Promise<void>;
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

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${cols}, 1fr)`,
        gap: 12,
        padding: 12,
        overflow: 'auto',
        height: '100%',
        boxSizing: 'border-box',
      }}
    >
      {sorted.map((r) => {
        const isSelected = selectedIds.has(r.id);
        const isFolder = !r.name.endsWith('.md');
        const displayName = r.name.split('/').pop() ?? r.name;
        return (
          <div
            key={r.id}
            draggable={mode === 'grid'}
            onDragStart={(e) => {
              if (mode !== 'grid') return;
              e.dataTransfer.setData('resource:id', r.id);
            }}
            onClick={() => {
              // 默认：单击切换选中（无论 grid 或 picker 模式，缩略图单击=勾选）
              if (onSelectionChange) {
                const ns = new Set(selectedIds);
                if (ns.has(r.id)) ns.delete(r.id);
                else ns.add(r.id);
                onSelectionChange(ns);
              }
            }}
            onDoubleClick={() => {
              // 双击才打开 MD 浏览器（grid 模式专用）
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
              userSelect: 'none',
            }}
          >
            {mode === 'picker' && isSelected && (
              <div
                style={{
                  position: 'absolute',
                  top: 4,
                  right: 4,
                  color: '#1B3B6F',
                  fontWeight: 700,
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
    </div>
  );
}