import { apiGet, apiPost } from './client';
import type { MapNodesResponse } from './types';

export const generateMap = (sid: string) =>
  apiPost<{ trace_id: string }>('/api/map/generate', { student_id: sid });
export const getMapNodes = (sid: string) => apiGet<MapNodesResponse>(`/api/map/${sid}/nodes`);