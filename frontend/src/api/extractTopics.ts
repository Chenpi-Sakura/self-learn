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
 * 返回 cleanup 函数；error 时自动 close 并触发 error event。
 */
export function subscribeExtractTopicsProgress(
  taskId: string,
  onEvent: (e: SSEEvent) => void
): () => void {
  const es = new EventSource(
    `/api/resources/extract_topics/stream?task_id=${encodeURIComponent(taskId)}`
  );
  const handler = (kind: 'progress' | 'completed' | 'error') =>
    (e: MessageEvent) => {
      onEvent({ event: kind, data: JSON.parse(e.data) } as SSEEvent);
    };
  es.addEventListener('progress', handler('progress'));
  es.addEventListener('completed', (e: MessageEvent) => {
    handler('completed')(e);
    es.close();
  });
  es.addEventListener('error', () => {
    es.close();
    onEvent({
      event: 'error',
      data: {
        status: 'failed',
        payload: { code: 'sse_error', message: 'lost connection' },
      },
    } as SSEEvent);
  });
  return () => es.close();
}