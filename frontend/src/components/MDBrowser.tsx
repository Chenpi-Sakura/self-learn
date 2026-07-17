import { useEffect, useState } from 'react';
import { getResource, type ResourceResponse } from '../api/resources';
import { MarkdownRenderer } from './MarkdownRenderer';

/**
 * MD 浏览器（Task 5）。
 * - 顶部 toolbar：文件标题 + 字号 A-/A+ + 复制全文
 * - 中间用 MarkdownRenderer 渲染原始 md（pre 包住保留换行）
 */
export function MDBrowser({ resourceId }: { resourceId: string }) {
  const [res, setRes] = useState<ResourceResponse | null>(null);
  const [fontSize, setFontSize] = useState(15);

  useEffect(() => {
    if (!resourceId) {
      setRes(null);
      return;
    }
    let cancelled = false;
    getResource(resourceId)
      .then((r) => {
        if (!cancelled) setRes(r);
      })
      .catch((err) => console.error('[MDBrowser] getResource failed', err));
    return () => {
      cancelled = true;
    };
  }, [resourceId]);

  if (!resourceId) {
    return (
      <div style={{ padding: 16, color: '#6B6B70' }}>未指定资源 ID</div>
    );
  }
  if (!res) {
    return <div style={{ padding: 16 }}>加载中…</div>;
  }

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(res.content_md);
    } catch (err) {
      console.error('[MDBrowser] clipboard write failed', err);
    }
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
        <span style={{ flex: 1, fontSize: 13, fontWeight: 500 }}>
          {res.name}
        </span>
        <span style={{ fontSize: 12, color: '#6B6B70' }}>字号</span>
        <button
          onClick={() => setFontSize(Math.max(12, fontSize - 1))}
          style={{ padding: '2px 8px' }}
        >
          A-
        </button>
        <span style={{ fontSize: 12, minWidth: 24, textAlign: 'center' }}>
          {fontSize}
        </span>
        <button
          onClick={() => setFontSize(Math.min(24, fontSize + 1))}
          style={{ padding: '2px 8px' }}
        >
          A+
        </button>
        <button onClick={onCopy} style={{ padding: '4px 10px' }}>
          复制全文
        </button>
      </div>
      <div
        style={{
          flex: 1,
          fontSize,
          overflow: 'auto',
          padding: 16,
        }}
      >
        <MarkdownRenderer
          html={`<pre style="white-space: pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;">${escapeHtml(res.content_md)}</pre>`}
        />
      </div>
    </div>
  );
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}
