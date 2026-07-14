import { apiGet, apiPost } from './client';
import type { ProfileResponse } from './types';

export const getProfile = (sid: string) => apiGet<ProfileResponse>(`/api/profile/${sid}`);
export const getProfileHistory = (sid: string, limit = 10) =>
  apiGet<{ student_id: string; snapshots: { profile: Record<string, number>; trigger: string; created_at: string }[] }>(
    `/api/profile/${sid}/history?limit=${limit}`
  );
export const buildProfile = (sid: string, dims: Record<string, number>, tags: string[]) =>
  apiPost<{ trace_id: string }>('/api/profile/build', { student_id: sid, dimensions: dims, tags });