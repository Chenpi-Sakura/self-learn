import { ProgressOverlay } from './ProgressOverlay';

/**
 * 关卡进度条浮层（Task 6）。
 * - 复用 ProgressOverlay 的 level source（4 阶段：outline / lecture / exercise / review）。
 * - 与 ProgressOverlay 不同：本组件固定阶段文案，无需调用方每次写一遍。
 *
 * 使用场景：LecturePane 检测到 lecture_html 为 null 时，把 SSE 订阅交给本组件，
 *          等关卡生成完成（completed SSE）后通过 onDone 通知父组件重新拉取关卡。
 */
export function LevelStartProgress({
  levelId,
  traceId,
  onDone,
  onClose,
}: {
  levelId: string;
  traceId: string;
  onDone: () => void;
  onClose: () => void;
}) {
  return (
    <ProgressOverlay
      source={{
        kind: 'level',
        levelId,
        traceId,
        stages: [
          { key: 'outline', label: '提炼纲要' },
          { key: 'lecture', label: '写讲义' },
          { key: 'exercise', label: '出题' },
          { key: 'review', label: '审核' },
        ],
        onDone,
      }}
      onClose={onClose}
    />
  );
}