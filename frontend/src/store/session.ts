import { create } from 'zustand';

const KEY = 'selflearn.student_id';

function genId(): string {
  return crypto.randomUUID();
}

export const useSession = create<{ studentId: string; reset: () => void }>((set) => ({
  studentId: localStorage.getItem(KEY) ?? (() => {
    const id = genId();
    localStorage.setItem(KEY, id);
    return id;
  })(),
  reset: () => {
    localStorage.removeItem(KEY);
    set({ studentId: genId() });
    // spec § 10.6 重置 demo
    location.reload();
  },
}));