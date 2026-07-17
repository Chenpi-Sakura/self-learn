import { create } from 'zustand';
import { KEEP_STUDENT } from '../constants/account';

// 唯一账户（spec Task 265）：前端不再生成临时 UUID，永久使用 KEEP_STUDENT。
// 这是部署时唯一的合法 student_id。无登录/无注册/无切换。
export const useSession = create<{ studentId: string; reset: () => void }>((set) => ({
  studentId: KEEP_STUDENT,
  reset: () => {
    // reset 保留只是为了兼容旧 demo 的"硬刷"动作；唯一副作用是 location.reload()。
    location.reload();
  },
}));