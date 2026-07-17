import { useEffect, useState } from 'react';
import { ResourceListView } from './ResourceListView';
import { listResources, type ResourceListItem } from '../api/resources';

/**
 * 提炼主题对话框（Task 5）。
 * - 用户可在打开后追加 / 取消选择资料
 * - 右下角：取消 / 确认按钮
 * - 空选时确认按钮 disabled
 *
 * `preSelectedIds`: 资源管理器已经选好的 ids；
 * `onConfirm`: 用户点确认后回调，传入选中的 ids（不直接调 API — 让 ResourceLibrary 持有 ProgressOverlay）
 * `onCancel`: 用户点取消后回调
 */
export function ExtractTopicsDialog({
  preSelectedIds,
  onConfirm,
  onCancel,
}: {
  preSelectedIds: string[];
  onConfirm: (selectedIds: string[]) => void;
  onCancel: () => void;
}) {
  const [items, setItems] = useState<ResourceListItem[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set(preSelectedIds));

  useEffect(() => {
    let cancelled = false;
    listResources()
      .then((r) => {
        if (cancelled) return;
        setItems(r.items);
        // 只保留仍在 list 中的预选项
        const valid = preSelectedIds.filter((id) => r.items.some((it) => it.id === id));
        setSelected(new Set(valid));
      })
      .catch((err) => console.error('[ExtractTopicsDialog] listResources failed', err));
    return () => {
      cancelled = true;
    };
  }, [preSelectedIds]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ padding: 12, borderBottom: '1px solid #E5E5E0', fontSize: 13 }}>
        选择要提炼的资料（已选 <strong>{selected.size}</strong> 个）
      </div>
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <ResourceListView
          items={items}
          mode="picker"
          selectedIds={selected}
          onSelectionChange={setSelected}
        />
      </div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'flex-end',
          gap: 8,
          padding: 12,
          borderTop: '1px solid #E5E5E0',
        }}
      >
        <button
          onClick={onCancel}
          style={{
            padding: '6px 16px',
            background: 'transparent',
            color: '#1B3B6F',
            border: '1px solid #1B3B6F',
            borderRadius: 4,
            cursor: 'pointer',
          }}
        >
          取消
        </button>
        <button
          onClick={() => onConfirm([...selected])}
          disabled={selected.size === 0}
          style={{
            padding: '6px 16px',
            background: selected.size ? '#1B3B6F' : '#E5E5E0',
            color: selected.size ? '#FBF7EC' : '#6B6B70',
            border: 'none',
            borderRadius: 4,
            cursor: selected.size ? 'pointer' : 'not-allowed',
          }}
        >
          确认提炼
        </button>
      </div>
    </div>
  );
}
