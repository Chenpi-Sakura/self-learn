import { create } from 'zustand';
import type { ProfileDimensions } from '../api/types';

export const useProfile = create<{
  dimensions: ProfileDimensions | null;
  setDimensions: (d: ProfileDimensions) => void;
}>((set) => ({
  dimensions: null,
  setDimensions: (d) => set({ dimensions: d }),
}));