import { useEffect, useState } from 'react';
import { subscribeExtractTopicsProgress } from '../api/extractTopics';
import { subscribeLevelProgress } from '../api/sse';
import type { SSEEvent } from '../api/types';

export interface ProgressStage {
  key: string;
  label: string;
}

export type ProgressSource =
  | {
      kind: 'extract_topics';
      taskId: string;
      stages: ProgressStage[];
      onDone: (createdNodeIds: string[]) => void;
    }
  | {
      kind: 'level';
      levelId: string;
      traceId: string;
      stages: ProgressStage[];
      onDone: () => void;
    };

type StageStatus = 'pending' | 'running' | 'completed' | 'failed';

const STAGE_KEY_TO_INDEX = (stages: ProgressStage[]) =>
  Object.fromEntries(stages.map((s, i) => [s.key, i]));

/**
 * 浮层进度条组件（Task 3）。
 * - extract_topics 走 subscribeExtractTopicsProgress；
 * - level 走 subscribeLevelProgress（Task 6 才会接入）。
 * 视觉：横向串点（✓ 绿 / ● 蓝脉冲 / ○ 灰）。无取消按钮（按 brief 全局约束）。
 */
export function ProgressOverlay({
  source,
  onClose,
}: {
  source: ProgressSource;
  onClose: () => void;
}) {
  const [progressStatus, setProgressStatus] = useState<
    Record<string, StageStatus>
  >({});
  const [currentStageIdx, setCurrentStageIdx] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const idxMap = STAGE_KEY_TO_INDEX(source.stages);
    const handle = (ev: SSEEvent) => {
      if (ev.event === 'progress') {
        const d = ev.data as {
          stage: string;
          status: StageStatus;
          payload: Record<string, unknown>;
        };
        // 后端 stage 是 "extract_topics.parse"，前端 key 是 "parse"。
        // 取最后一段匹配 stages[].key。
        const shortKey = d.stage.split('.').pop() ?? d.stage;
        setProgressStatus((s) => ({ ...s, [shortKey]: d.status }));
        if (idxMap[shortKey] !== undefined) {
          setCurrentStageIdx(idxMap[shortKey]);
        }
      } else if (ev.event === 'completed') {
        const d = ev.data as {
          status: string;
          payload: { created_node_ids?: string[] };
        };
        if (source.kind === 'extract_topics') {
          source.onDone(d.payload.created_node_ids ?? []);
        } else {
          source.onDone();
        }
      } else if (ev.event === 'error') {
        const d = ev.data as { status: string; payload: { error?: string; code?: string; message?: string } };
        const reason = d.payload.error ?? d.payload.message ?? d.payload.code ?? '未知错误';
        setError(`任务失败: ${reason}`);
      }
    };
    const close =
      source.kind === 'extract_topics'
        ? subscribeExtractTopicsProgress(source.taskId, handle)
        : subscribeLevelProgress(source.levelId, source.traceId, handle);
    return () => close();
  }, [source]);

  const title =
    source.kind === 'extract_topics' ? '提炼主题进度' : '关卡生成进度';

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.4)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          background: '#FBF7EC',
          borderRadius: 12,
          padding: 24,
          minWidth: 480,
          fontFamily: 'HedvigLettersSerif, serif',
        }}
      >
        <h3 style={{ margin: 0, marginBottom: 16 }}>{title}</h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {source.stages.map((stage, idx) => {
            const status = progressStatus[stage.key] ?? 'pending';
            const isCurrent = idx === currentStageIdx && status === 'running';
            const isDone = status === 'completed';
            const isFailed = status === 'failed';
            return (
              <div
                key={stage.key}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  flex: 1,
                }}
              >
                <div
                  style={{
                    width: 24,
                    height: 24,
                    borderRadius: '50%',
                    background: isFailed
                      ? '#BC4749'
                      : isDone
                      ? '#5A8F4D'
                      : isCurrent
                      ? '#1B3B6F'
                      : '#E5E5E0',
                    color: '#FBF7EC',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    animation: isCurrent ? 'pulse 1.2s infinite' : 'none',
                    flexShrink: 0,
                  }}
                >
                  {isFailed ? '✗' : isDone ? '✓' : idx + 1}
                </div>
                <div
                  style={{
                    marginLeft: 6,
                    fontSize: 13,
                    color: isFailed
                      ? '#BC4749'
                      : isDone
                      ? '#5A8F4D'
                      : isCurrent
                      ? '#1B3B6F'
                      : '#6B6B70',
                  }}
                >
                  {stage.label}
                </div>
                {idx < source.stages.length - 1 && (
                  <div
                    style={{
                      flex: 1,
                      height: 2,
                      background: isFailed
                        ? '#BC4749'
                        : isDone
                        ? '#5A8F4D'
                        : '#E5E5E0',
                      margin: '0 8px',
                    }}
                  />
                )}
              </div>
            );
          })}
        </div>
        {error && (
          <div
            style={{
              marginTop: 16,
              color: '#BC4749',
              fontSize: 13,
            }}
          >
            {error}
            <button onClick={onClose} style={{ marginLeft: 12 }}>
              关闭
            </button>
          </div>
        )}
        <style>{`@keyframes pulse {
          0% { box-shadow: 0 0 0 0 rgba(27,59,111,0.4); }
          70% { box-shadow: 0 0 0 8px rgba(27,59,111,0); }
          100% { box-shadow: 0 0 0 0 rgba(27,59,111,0); }
        }`}</style>
      </div>
    </div>
  );
}