import { apiGet, apiPost } from './client';
import type { LevelDetail } from './types';

export const startLevel = (sid: string) =>
  apiPost<{ trace_id: string }>('/api/level/start', { student_id: sid });
export const getLevel = (lid: string) => apiGet<LevelDetail>(`/api/level/${lid}`);
export const submitLevel = (lid: string, answers: Record<string, string>) =>
  apiPost<{ status: string; score: number }>(`/api/level/${lid}/submit`, { answers });