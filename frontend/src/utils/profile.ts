export const SHORT_KEYS = ['kb', 'vp', 'as', 'ge', 'ept', 'fd'] as const;
export type ShortKey = (typeof SHORT_KEYS)[number];

/**
 * Profile 是否已初始化（非 null 且 6 维不全 0.5）。
 * - null/undefined → 未初始化（首次）
 * - 全 0.5 → 未初始化（默认初值）
 * - 任一维 ≠ 0.5 → 已初始化（onboarding 完成 或 director 驱动过）
 */
export function isProfileInitialized(
  dims?: Record<string, number> | null
): boolean {
  if (!dims) return false;
  return SHORT_KEYS.some(
    (k) => Math.abs((dims[k] ?? 0.5) - 0.5) > 1e-6
  );
}
