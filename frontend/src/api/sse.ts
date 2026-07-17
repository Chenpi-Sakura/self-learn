import type { SSEEvent } from './types';

/** Subscribe to /api/profile/init/{traceId}/stream */
export function subscribeProfileProgress(traceId: string, onEvent: (e: SSEEvent) => void): () => void {
  const es = new EventSource(`/api/profile/init/${traceId}/stream`);
  const handler = (kind: 'progress' | 'completed' | 'error') => (e: MessageEvent) => {
    onEvent({ event: kind, data: JSON.parse(e.data) } as SSEEvent);
  };
  es.addEventListener('progress', handler('progress'));
  es.addEventListener('completed', (e) => { handler('completed')(e); es.close(); });
  es.addEventListener('error', () => { es.close(); });
  return () => es.close();
}

/**
 * Subscribe to /api/level/{levelId}/stream?trace_id=...
 *
 * reused=true (levelId 已是真实 UUID) → /api/level/{levelId}/stream
 * reused=false (levelId="pending"，director chain 还没生成) → /api/level/start-stream
 */
export function subscribeLevelProgress(
  levelId: string, traceId: string, onEvent: (e: SSEEvent) => void
): () => void {
  const path = levelId === 'pending'
    ? `/api/level/start-stream?trace_id=${encodeURIComponent(traceId)}`
    : `/api/level/${levelId}/stream?trace_id=${encodeURIComponent(traceId)}`;
  const es = new EventSource(path);
  const handler = (kind: 'progress' | 'completed' | 'error') => (e: MessageEvent) => {
    onEvent({ event: kind, data: JSON.parse(e.data) } as SSEEvent);
  };
  es.addEventListener('progress', handler('progress'));
  es.addEventListener('completed', (e) => { handler('completed')(e); es.close(); });
  es.addEventListener('error', () => { es.close(); });
  return () => es.close();
}