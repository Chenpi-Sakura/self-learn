/** Task 5 端到端：上传两份 md → 选 → 提炼对话框 → SSE 进度 → 引导卡消失。
 *
 * 前置条件：
 * - backend 已起 http://localhost:8000（worker + gateway，含 SSE 端点）
 * - frontend npm run dev 在 5174
 * - ResourceLibrary 的 file input 接受 .md 多文件
 * - ProgressOverlay 5 阶段标签：
 *     '加载资料' | '向量化' | 'AI 抽取主题' | '去重' | '写入知识图谱'
 */
import { test, expect } from '@playwright/test';

const STUDENT_ID = '86820161-b0f0-455f-91b4-a69e49445bdf';

test('user uploads 2 md, opens extract dialog, confirms, sees progress, empty-state hides', async ({
  page,
}) => {
  // 前端 student_id session (Task 5 唯一账户约定：从 localStorage 注入)
  await page.addInitScript((sid: string) => {
    localStorage.setItem('selflearn.student_id', sid);
  }, STUDENT_ID);

  // 预清已有资源 / map nodes，避免上轮 stub 数据污染（通过 backend API）
  await page.request.delete('http://localhost:8000/api/_test/clear_map_nodes', {
    failOnStatusCode: false,
  });

  await page.goto('/');
  await page.waitForLoadState('networkidle', { timeout: 30_000 });

  // 1) 引导卡可见
  await expect(
    page.getByRole('heading', { name: '开始上传你的学习资料' }),
  ).toBeVisible({ timeout: 15_000 });

  // 2) 打开资源管理器
  await page.getByRole('button', { name: '打开资源管理器' }).click();
  // ResourceLibrary 渲染在 Window 内；用窗口标题定位
  const rlWin = page.locator('.win').filter({ has: page.getByText('资源管理器') });
  await expect(rlWin).toBeVisible({ timeout: 5_000 });

  // 3) 上传 2 份 md
  const fileInput = rlWin.locator('input[type="file"]').first();
  await fileInput.setInputFiles({
    name: '01-self-attn.md',
    mimeType: 'text/markdown',
    buffer: Buffer.from('# Self-Attention\n\n' + 'A'.repeat(700)),
  });
  await fileInput.setInputFiles({
    name: '02-multi-head.md',
    mimeType: 'text/markdown',
    buffer: Buffer.from('# Multi-Head\n\n' + 'B'.repeat(700)),
  });

  // 4) 资源出现在网格（zh locale 排序下 01 在 02 前）
  await expect(rlWin.getByText('01-self-attn.md')).toBeVisible({
    timeout: 8_000,
  });
  await expect(rlWin.getByText('02-multi-head.md')).toBeVisible();

  // 5) 选中两份 → 用所选生成地图
  await rlWin.getByText('01-self-attn.md').click();
  await rlWin.getByText('02-multi-head.md').click();
  await rlWin.getByRole('button', { name: /用所选生成地图/ }).click();

  // 6) 提炼对话框窗口出现
  const dlg = page
    .locator('.win')
    .filter({ has: page.getByText('生成地图对话框') });
  await expect(dlg).toBeVisible({ timeout: 5_000 });

  // 7) 确认提炼（ResourceLibrary 接管 ProgressOverlay；点完 confirm 后窗口会被关掉）
  await dlg.getByRole('button', { name: '确认提炼' }).click();

  // 8) 提炼进度浮层出现
  await expect(page.getByText('提炼主题进度')).toBeVisible({ timeout: 8_000 });
  await expect(page.getByText('加载资料')).toBeVisible();

  // 9) 等待完成（SSE 全 5 阶段完成 ≤ 120s）
  await expect(page.getByText('提炼主题进度')).toBeHidden({
    timeout: 120_000,
  });

  // 10) 引导卡已不显示（说明资源管理器已开窗）
  await expect(
    page.getByRole('heading', { name: '开始上传你的学习资料' }),
  ).toBeHidden();
});
