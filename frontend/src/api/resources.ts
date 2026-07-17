// 资源 CRUD REST 客户端（Task 1）。
// 直接用 fetch：上传走 multipart/form-data，PUT/DELETE 及 204 无 body 需自处理，
// 现有 client.ts 的 apiPost 会强制 JSON.stringify，不适用于 FormData。
const BASE = ''; // 走 vite proxy

export interface ResourceListItem {
  id: string;
  name: string;
  size_bytes: number;
  created_at: string;
}

export interface ResourceResponse extends ResourceListItem {
  content_md: string;
}

export interface ResourceUploadItem {
  id: string;
  name: string;
  size_bytes: number;
}

export interface ResourceUploadResponse {
  uploaded: ResourceUploadItem[];
}

export async function listResources(): Promise<{ items: ResourceListItem[] }> {
  const r = await fetch(`${BASE}/api/resources/list`);
  if (!r.ok) throw new Error(`GET /api/resources/list → ${r.status}`);
  return r.json();
}

export async function getResource(id: string): Promise<ResourceResponse> {
  const path = `/api/resources/${encodeURIComponent(id)}`;
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`GET ${path} → ${r.status}`);
  return r.json();
}

export async function uploadResources(files: File[]): Promise<ResourceUploadResponse> {
  const form = new FormData();
  for (const f of files) form.append('files', f, f.name);
  const r = await fetch(`${BASE}/api/resources/upload`, { method: 'POST', body: form });
  if (!r.ok) throw new Error(`POST /api/resources/upload → ${r.status}`);
  return r.json();
}

export async function updateResource(id: string, name: string): Promise<ResourceResponse> {
  const path = `/api/resources/${encodeURIComponent(id)}`;
  const r = await fetch(`${BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  if (!r.ok) throw new Error(`PUT ${path} → ${r.status}`);
  return r.json();
}

export async function deleteResource(id: string): Promise<void> {
  const path = `/api/resources/${encodeURIComponent(id)}`;
  const r = await fetch(`${BASE}${path}`, { method: 'DELETE' });
  if (!r.ok) throw new Error(`DELETE ${path} → ${r.status}`);
}
