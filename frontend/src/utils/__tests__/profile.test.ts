import { describe, it, expect } from 'vitest';
import { isProfileInitialized, SHORT_KEYS } from '../profile';

describe('isProfileInitialized', () => {
  it('null → false', () => {
    expect(isProfileInitialized(null)).toBe(false);
    expect(isProfileInitialized(undefined)).toBe(false);
  });

  it('全 0.5 → false (默认初值)', () => {
    const dims = Object.fromEntries(SHORT_KEYS.map((k) => [k, 0.5]));
    expect(isProfileInitialized(dims)).toBe(false);
  });

  it('任一维 ≠ 0.5 → true', () => {
    const dims = Object.fromEntries(SHORT_KEYS.map((k) => [k, 0.5]));
    dims.kb = 0.72;
    expect(isProfileInitialized(dims)).toBe(true);
  });

  it('空对象 → false (视为未初始化)', () => {
    expect(isProfileInitialized({})).toBe(false);
  });
});
