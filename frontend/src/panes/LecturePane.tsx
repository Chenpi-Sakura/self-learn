import { useEffect, useState } from 'react';
import { getLevel } from '../api/level';
import '../styles/lecture.css';

export function LecturePane({ levelId }: { levelId: string }) {
  const [state, setState] = useState<
    | { loaded: false }
    | { loaded: true; html: string | null }
  >({ loaded: false });

  useEffect(() => {
    if (!levelId) return;
    getLevel(levelId)
      .then((lv) => setState({ loaded: true, html: lv.lecture_html ?? null }))
      .catch(() => setState({ loaded: true, html: null }));
  }, [levelId]);

  // KaTeX 懒加载：只在 lecture_html 非空时动态 import
  const lectureHtml = state.loaded ? state.html : null;
  useEffect(() => {
    if (!lectureHtml) return;
    Promise.all([
      import('katex/dist/katex.min.css'),
      import('katex'),
      import('katex/dist/contrib/auto-render.min.js'),
    ]).then(([, , autoRenderMod]) => {
      // auto-render.min.js 是 UMD 模块，导出 renderMathInElement 函数。
      // Vite 把 CJS module.exports 包装成 { default: <exports> }；
      // 同时也直接暴露命名导出作为 fallback。两者取其一即可。
      const mod = (autoRenderMod as any).default ?? autoRenderMod;
      const renderMathInElement = mod.renderMathInElement as (
        el: HTMLElement,
        opts: object,
      ) => void;
      const root = document.querySelector('.lecture') as HTMLElement | null;
      if (root && typeof renderMathInElement === 'function') {
        renderMathInElement(root, {
          delimiters: [
            { left: '$$', right: '$$', display: true },
            { left: '$', right: '$', display: false },
          ],
          throwOnError: false,
        });
      }
    });
  }, [lectureHtml]);

  // 加载中
  if (!state.loaded) {
    return <div style={{ padding: 16, height: '100%', overflow: 'auto' }}>加载讲义...</div>;
  }

  // 没讲义（旧关卡 / 生成失败）
  if (!lectureHtml) {
    return (
      <div
        style={{
          padding: 16,
          color: '#6B6B70',
          fontFamily: 'HedvigLettersSerif, serif',
        }}
      >
        该关卡尚无讲义，请重新启动关卡
      </div>
    );
  }

  // 渲染讲义（依赖后端 nh3 白名单清洗，不在前端二次清洗）
  return (
    <div
      className="lecture"
      style={{
        padding: 16,
        height: '100%',
        overflow: 'auto',
        fontFamily: 'HedvigLettersSerif, serif',
      }}
      dangerouslySetInnerHTML={{ __html: lectureHtml }}
    />
  );
}