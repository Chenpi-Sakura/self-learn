import { useEffect, useState } from 'react';
import { getLevel } from '../api/level';
import { MarkdownRenderer } from '../components/MarkdownRenderer';

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

  const lectureHtml = state.html;

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

  // 渲染讲义：把 KaTeX 懒加载移交给 MarkdownRenderer。
  return <MarkdownRenderer html={lectureHtml} className="lecture" />;
}