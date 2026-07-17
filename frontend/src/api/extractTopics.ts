/** Trigger /api/resources/extract_topics + subscribe SSE progress. */
import { apiPost } from './client';
import type { SSEEvent } from './types';

export interface ExtractTopicsResponse {
  task_id: string;
}

/** POST 触发提炼主题，返回 task_id，前端再用 EventSource 连 /stream。 */
export const triggerExtractTopics = (selectedResourceIds: string[]) =>
  apiPost<ExtractTopicsResponse>('/api/resources/extract_topics', {
    selected_resource_ids: selectedResourceIds,
  });

/**
 * SSE 订阅 /api/resources/extract_topics/stream?task_id=...
 * - 5 阶段 progress 事件按序推送
 * - 终态：completed（成功）/ error（失败）
 * 返回 cleanup 函数。
 *
 * EventSource 原生 'error' 事件歧义：连接断开 / 后端 'event: error' 都触发。
 * 用 readyState 区分：CLOSED 且从未收到 error 事件 → 真断连；否则是后端关闭。
 * 由 ProgressOverlay 内部 useEffect cleanup 触发 es.close()，READYSTATE 变 CLOSED，
 * 浏览器仍会再 fire 一次 'error'，需跳过避免覆盖后端的 error payload。
 */
export function subscribeExtractTopicsProgress(
  taskId: string,
  onEvent: (e: SSEEvent) => void
): () => void {
  const es = new EventSource(
    `/api/resources/extract_topics/stream?task_id=${encodeURIComponent(taskId)}`
  );
  let sawTerminal = false;
  const handler = (kind: 'progress' | 'completed' | 'error') =>
    (e: MessageEvent) => {
      if (kind === 'completed' || kind === 'error') {
        sawTerminal = true;
      }
      onEvent({ event: kind, data: JSON.parse(e.data) } as SSEEvent);
    };
  es.addEventListener('progress', handler('progress'));
  es.addEventListener('completed', (e: MessageEvent) => {
    handler('completed')(e);
    es.close();
  });
  es.addEventListener('error', (e: MessageEvent) => {
    // 区分：后端真的发了 'event: error'（MessageEvent）vs 连接断开（Event，无 data）。
    if (e instanceof MessageEvent && e.data) {
      handler('error')(e);
    } else if (!sawTerminal && es.readyState !== EventSource.OPEN) {
      // 真正断连且未收到后端终态事件
      onEvent({
        event: 'error',
        data: { status: 'failed', payload: { error: 'lost connection' } },
      } as SSEEvent);
    }
    es.close();
  });
  return () => es.close();
}