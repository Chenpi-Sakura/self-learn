import { useEffect, useState } from 'react';
import { useWorkspace } from '../store/useWorkspace';
import { listResources } from '../api/resources';

/**
 * 冷启动引导卡（Task 5 + Q1 fix）。
 * 仅当 **windows 为空** 且 **资源列表为空** 时显示。
 * 用户开了任何窗口、或已经上传过至少一份资源，都不再骚扰。
 */
export function EmptyStateOverlay() {
  const windows = useWorkspace((s) => s.windows);
  const openWindow = useWorkspace((s) => s.openWindow);
  const [hasResources, setHasResources] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    listResources()
      .then((r) => {
        if (!cancelled) setHasResources(r.items.length > 0);
      })
      .catch(() => {
        // 后端不在线时不阻塞 UI：保守显示引导卡
        if (!cancelled) setHasResources(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (Object.keys(windows).length > 0) return null;
  if (hasResources === null) return null; // 初次加载未完成不闪
  if (hasResources) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(251,247,236,0.96)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 999,
        fontFamily: 'HedvigLettersSerif, serif',
        padding: 24,
      }}
    >
      <h1
        style={{
          fontSize: 32,
          color: '#1B3B6F',
          marginBottom: 16,
          textAlign: 'center',
        }}
      >
        开始上传你的学习资料
      </h1>
      <p
        style={{
          fontSize: 16,
          color: '#6B6B70',
          maxWidth: 480,
          textAlign: 'center',
          lineHeight: 1.7,
          margin: 0,
        }}
      >
        上传 1-4 份 .md 文件，
        <br />
        系统会从中抽取主题，生成知识地图。
      </p>
      <button
        onClick={() => openWindow('resource_library')}
        style={{
          marginTop: 24,
          padding: '12px 24px',
          background: '#1B3B6F',
          color: '#FBF7EC',
          borderRadius: 6,
          fontSize: 15,
          border: 'none',
          cursor: 'pointer',
        }}
      >
        打开资源管理器
      </button>
      <p
        style={{
          marginTop: 16,
          fontSize: 13,
          color: '#6B6B70',
        }}
      >
        （也可以从 Dock 栏打开）
      </p>
    </div>
  );
}
