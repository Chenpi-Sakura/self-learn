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
      import('katex/dist/contrib/auto-render.mjs'),
    ]).then(([, , autoRenderMod]) => {
      // auto-render.mjs 是 ESM 模块，export default 就是 renderMathInElement 函数。
      // Vite ESM-mode 动态 import 返回 { default: renderMathInElement }。
      const renderMathInElement = (autoRenderMod as any).default ?? autoRenderMod;
      if (typeof renderMathInElement !== 'function') {
        console.warn('[LecturePane] renderMathInElement 获取失败，模块结构:', autoRenderMod);
        return;
      }
      const root = document.querySelector('.lecture') as HTMLElement | null;
      if (root) {
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

  // 加载中或未选节点
  if (!state.loaded) {
    if (!levelId) {
      return (
        <div
          style={{
            padding: 16,
            height: '100%',
            overflow: 'auto',
            color: '#6B6B70',
            fontFamily: 'HedvigLettersSerif, serif',
          }}
        >
          请先选择左侧地图上的节点
        </div>
      );
    }
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

  // 防御：LLM 偶尔会把 tool 错误信息当成讲义内容输出。
  // 检测 lecture_html 是否含 kp_id/student_id/无法获取 等明显错误文本，提示重试。
  const looksLikeError =
    /无法获取|请检查参数|\bkp_id\b.*\bstudent_id\b|invalid_uuid/i.test(lectureHtml);
  if (looksLikeError) {
    return (
      <div
        style={{
          padding: 16,
          color: '#BC4749',
          fontFamily: 'HedvigLettersSerif, serif',
        }}
      >
        讲义生成失败（LLM 把工具错误写进了讲义）。请重新启动关卡重试。
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