import { useEffect, useRef } from 'react';
import '../styles/markdown.css';

/**
 * 共用 Markdown 渲染器：
 * 1. 直接以 dangerouslySetInnerHTML 注入已清洗的 html 字符串
 *    （后端用 nh3 白名单清洗，前端不再二次清洗）。
 * 2. KaTeX 通过动态 import 懒加载，只在有 html 时才下载大体积包。
 *    - 沿用 auto-render.mjs ESM 模式（不要回退 .min.js）。
 *    - 模块结构：{ default: renderMathInElement }。
 */
export function MarkdownRenderer({
  html,
  className,
}: {
  html: string;
  className?: string;
}) {
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!html) return;
    let cancelled = false;
    Promise.all([
      import('katex/dist/katex.min.css'),
      import('katex'),
      import('katex/dist/contrib/auto-render.mjs'),
    ]).then(([, , autoRenderMod]) => {
      if (cancelled) return;
      const renderMathInElement = (autoRenderMod as any).default ?? autoRenderMod;
      if (typeof renderMathInElement !== 'function') {
        console.warn('[MarkdownRenderer] renderMathInElement 获取失败，模块结构:', autoRenderMod);
        return;
      }
      if (rootRef.current) {
        renderMathInElement(rootRef.current, {
          delimiters: [
            { left: '$$', right: '$$', display: true },
            { left: '$', right: '$', display: false },
          ],
          throwOnError: false,
        });
      }
    });
    return () => {
      cancelled = true;
    };
  }, [html]);

  return (
    <div
      ref={rootRef}
      className={className ?? 'markdown-body'}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}