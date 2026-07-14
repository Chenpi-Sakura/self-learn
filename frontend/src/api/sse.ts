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

/** Subscribe to /api/level/{levelId}/stream?trace_id=... */
export function subscribeLevelProgress(
  levelId: string, traceId: string, onEvent: (e: SSEEvent) => void
): () => void {
  const es = new EventSource(`/api/level/${levelId}/stream?trace_id=${encodeURIComponent(traceId)}`);
  const handler = (kind: 'progress' | 'completed' | 'error') => (e: MessageEvent) => {
    onEvent({ event: kind, data: JSON.parse(e.data) } as SSEEvent);
  };
  es.addEventListener('progress', handler('progress'));
  es.addEventListener('completed', (e) => { handler('completed')(e); es.close(); });
  es.addEventListener('error', () => { es.close(); });
  return () => es.close();
}