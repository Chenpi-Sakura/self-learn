// src/lib/persistence.ts
// 持久化层封装：localStorage（轻量配置）+ IndexedDB（结构化数据）
// 设计依据：详细设计规格说明书 v4 § 5.2

const DB_NAME = 'selflearn';
const DB_VERSION = 1;

/**
 * 安全写入 localStorage。QuotaExceededError 时降级到控制台 warn 并返回 false
 */
export function safeSetItem(key: string, value: string): boolean {
  try {
    localStorage.setItem(key, value);
    return true;
  } catch (e) {
    if (e instanceof DOMException && e.name === 'QuotaExceededError') {
      console.warn(`[persistence] localStorage quota exceeded for key: ${key}`);
    } else {
      console.error(`[persistence] localStorage setItem failed for key: ${key}`, e);
    }
    return false;
  }
}

export function safeGetItem(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch (e) {
    console.error(`[persistence] localStorage getItem failed for key: ${key}`, e);
    return null;
  }
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      // 按 v4 § 5.2 的 IndexedDB store 命名
      if (!db.objectStoreNames.contains('profile_cache')) db.createObjectStore('profile_cache');
      if (!db.objectStoreNames.contains('map_cache')) db.createObjectStore('map_cache');
      if (!db.objectStoreNames.contains('window_states')) db.createObjectStore('window_states');
      if (!db.objectStoreNames.contains('chat_history')) db.createObjectStore('chat_history');
      if (!db.objectStoreNames.contains('resource_cache')) db.createObjectStore('resource_cache');
      if (!db.objectStoreNames.contains('level_metrics_buffer')) db.createObjectStore('level_metrics_buffer');
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function idbGet<T>(storeName: string, key: string): Promise<T | undefined> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readonly');
    const req = tx.objectStore(storeName).get(key);
    req.onsuccess = () => resolve(req.result as T | undefined);
    req.onerror = () => reject(req.error);
  });
}

export async function idbSet<T>(storeName: string, key: string, value: T): Promise<void> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readwrite');
    tx.objectStore(storeName).put(value, key);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function idbDelete(storeName: string, key: string): Promise<void> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readwrite');
    tx.objectStore(storeName).delete(key);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}