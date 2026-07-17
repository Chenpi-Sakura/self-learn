import { useEffect, useState } from 'react';
import type { MouseEvent } from 'react';
import { useWorkspace } from '../store/useWorkspace';
import { ResourceListView } from './ResourceListView';
import type { WindowState } from '../types/window';
import {
  listResources,
  uploadResources,
  deleteResource,
  updateResource,
  type ResourceListItem,
} from '../api/resources';
import { ProgressOverlay } from './ProgressOverlay';
import { triggerExtractTopics } from '../api/extractTopics';

/**
 * 资源管理器窗口（Task 5）。
 * - 顶部 toolbar：上传 .md 按钮 + 用所选生成地图按钮
 * - 拖拽上传（仅 .md）
 * - 中间使用 ResourceListView(mode='grid') 多选
 * - 右键删除（confirm 二次确认）
 * - 双击重命名走 updateResource
 * - 点击条目 → MD 浏览器（single resource）
 */
export function ResourceLibrary({
  win,
  onOpenExtractDialog,
}: {
  win: WindowState;
  onOpenExtractDialog: (ids: string[]) => void;
}) {
  const openWindow = useWorkspace((s) => s.openWindow);
  const closeWindow = useWorkspace((s) => s.closeWindow);
  const [items, setItems] = useState<ResourceListItem[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [multiSelect, setMultiSelect] = useState<boolean>(false);
  const [extractTaskId, setExtractTaskId] = useState<string | null>(null);

  // 从窗口 metadata 读取已有的 extractTaskId（ExtractTopicsDialog 确认后通过 App.tsx 注入）
  useEffect(() => {
    const tid = (win.metadata as Record<string, unknown>)?.extractTaskId as string | undefined;
    if (tid) {
      setExtractTaskId(tid);
    }
  }, [win.metadata]);

  const refresh = async () => {
    try {
      const r = await listResources();
      setItems(r.items);
    } catch (err) {
      console.error('[ResourceLibrary] listResources failed', err);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const onUpload = async (files: File[]) => {
    if (!files.length) return;
    await uploadResources(files);
    await refresh();
  };

  const onExtractClick = async () => {
    const ids = [...selected];
    if (ids.length === 0) return;
    // 先关掉提炼对话框（如果还开着）→ 立即 open
    onOpenExtractDialog(ids);
  };

  const handleExtractConfirm = async (ids: string[]) => {
    if (ids.length === 0) return;
    closeWindow('extract_topics_dialog');
    try {
      const r = await triggerExtractTopics(ids);
      setExtractTaskId(r.task_id);
    } catch (err) {
      console.error('[ResourceLibrary] triggerExtractTopics failed', err);
      alert('触发提炼失败：' + String(err));
    }
  };

  const handleExtractCancel = () => {
    closeWindow('extract_topics_dialog');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div
        style={{
          display: 'flex',
          gap: 8,
          padding: 8,
          borderBottom: '1px solid #E5E5E0',
          alignItems: 'center',
        }}
      >
        <label
          style={{
            padding: '6px 12px',
            background: '#1B3B6F',
            color: '#FBF7EC',
            borderRadius: 4,
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
          }}
        >
          ⬆ 上传 .md
          <input
            type="file"
            accept=".md"
            multiple
            hidden
            data-testid="resource-library-file-input"
            onChange={(e) => {
              const files = Array.from(e.target.files || []);
              if (files.length) onUpload(files);
              e.target.value = '';
            }}
          />
        </label>
        <button
          type="button"
          onClick={() => {
            setMultiSelect((v) => !v);
            setSelected(new Set());
          }}
          style={{
            padding: '6px 12px',
            background: multiSelect ? '#5A8F4D' : '#E5E5E0',
            color: multiSelect ? '#FBF7EC' : '#6B6B70',
            borderRadius: 4,
            border: 'none',
            cursor: 'pointer',
            fontSize: 12,
          }}
          title={multiSelect ? '退出多选模式（单击资源会直接打开）' : '开启多选模式（单击资源变为勾选）'}
        >
          {multiSelect ? '☑ 多选模式' : '☐ 单击进入多选'}
        </button>
        <button
          disabled={selected.size === 0}
          onClick={onExtractClick}
          style={{
            padding: '6px 12px',
            background: selected.size ? '#BC4749' : '#E5E5E0',
            color: selected.size ? '#FBF7EC' : '#6B6B70',
            borderRadius: 4,
            cursor: selected.size ? 'pointer' : 'not-allowed',
            border: 'none',
          }}
        >
          🗺 用所选生成地图{selected.size > 0 ? ` (${selected.size})` : ''}
        </button>
        <span style={{ marginLeft: 'auto', fontSize: 12, color: '#6B6B70' }}>
          {items.length} 份
        </span>
      </div>
      <div
        onDrop={(e) => {
          e.preventDefault();
          const files = Array.from(e.dataTransfer.files).filter((f) =>
            f.name.toLowerCase().endsWith('.md'),
          );
          if (files.length) onUpload(files);
        }}
        onDragOver={(e) => e.preventDefault()}
        style={{ flex: 1, overflow: 'hidden' }}
      >
        <ResourceListView
          items={items}
          mode={multiSelect ? 'picker' : 'grid'}
          selectedIds={selected}
          onSelectionChange={setSelected}
          onOpen={(id) => openWindow('md_browser', { resourceId: id })}
          onContextMenu={(_e: MouseEvent, id: string) => {
            if (window.confirm('删除这份资源？')) {
              deleteResource(id).then(refresh).catch((err) => {
                console.error('[ResourceLibrary] delete failed', err);
              });
            }
          }}
          onRename={(id, name) => updateResource(id, name).then(refresh)}
        />
      </div>

      {/* 让 ExtractTopicsDialog 能从外部触发 confirm/cancel，
          通过 window.__extractTopics 接口实现 — 避免在 renderBody 用 store 注入。
          实际提炼对话框窗口直接暴露 confirm/cancel handler 给 ResourceLibrary 更简洁，
          但本组件无权获取 dialog window 的 props；改为对话框内自带按钮逻辑。 */}
      <div style={{ display: 'none' }} data-task-id={extractTaskId ?? ''} />

      {extractTaskId && (
        <ProgressOverlay
          source={{
            kind: 'extract_topics',
            taskId: extractTaskId,
            stages: [
              { key: 'parse', label: '加载资料' },
              { key: 'llm', label: 'LLM 抽取' },
              { key: 'validate', label: '校验' },
              { key: 'write', label: '写入图谱' },
              { key: 'done', label: '完成' },
            ],
            onDone: () => {
              setExtractTaskId(null);
              // 触发地图刷新：发一个自定义事件让 TreasureMap 监听
              window.dispatchEvent(new CustomEvent('selflearn:refresh-map'));
            },
          }}
          onClose={() => setExtractTaskId(null)}
        />
      )}
    </div>
  );
}
