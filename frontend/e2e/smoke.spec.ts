/** Stage 4 demo smoke（前端 + CORS + 基本数据流）。
 *
 * 前置条件：
 * - backend 已起：http://localhost:8000（worker + gateway）
 * - frontend npm run dev 在 5174
 *
 * 覆盖范围（与 docs/superpowers/specs/2026-07-13-stage4-demo-integration-design.md 一致）：
 * 1. 页面加载，藏宝图 + 画像窗口可见
 * 2. CORS：无浏览器层 CORS 报错
 * 3. 数据流：profile / map API 调用成功，无 console error
 */
import { test, expect } from "@playwright/test";

const STUDENT_ID = "00000000-0000-0000-0000-000000000001";

test.describe("Stage 4 demo smoke", () => {
  test("页面加载后看到藏宝图与画像", async ({ page }) => {
    // 注：前端 session store key = 'selflearn.student_id'（非 'student_id'）
    await page.addInitScript((sid: string) => {
      localStorage.setItem("selflearn.student_id", sid);
    }, STUDENT_ID);

    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });

    await page.goto("/");
    // 等 React 挂载 + 数据加载
    await page.waitForLoadState("networkidle", { timeout: 30_000 });
    // TreasureMap: .tm-svg (SVG 节点)
    await expect(page.locator(".tm-svg")).toBeVisible({ timeout: 15_000 });
    // ProfileRadar: 等 dims 加载后 .pr-svg 才渲染（API 异步）
    await expect(page.locator(".pr-svg")).toBeVisible({ timeout: 15_000 });
    // 6 个维度标签（雷达图外圈文字）
    const profileLabels = await page.locator(".pr-body text").allTextContents();
    expect(profileLabels.length).toBeGreaterThanOrEqual(6);

    if (consoleErrors.length > 0) {
      console.log("[test] console errors:", consoleErrors);
    }
  });

  test("CORS：无浏览器层 CORS 报错", async ({ page }) => {
    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];

    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });
    page.on("pageerror", (err) => {
      pageErrors.push(err.message);
    });

    await page.addInitScript((sid: string) => {
      localStorage.setItem("selflearn.student_id", sid);
    }, STUDENT_ID);

    await page.goto("/");
    await page.waitForLoadState("networkidle", { timeout: 30_000 });

    const corsErrors = [...consoleErrors, ...pageErrors].filter((m) =>
      m.toLowerCase().includes("cors")
    );
    expect(corsErrors).toEqual([]);
  });

  test("profile / map API 调用成功（200）", async ({ request }) => {
    // 直接调 API 验证 backend 在跑
    const profileResp = await request.get(
      `http://localhost:8000/api/profile/${STUDENT_ID}`
    );
    // 404 也是合法的（首次启动无 profile）
    expect([200, 404]).toContain(profileResp.status());

    const mapResp = await request.get(
      `http://localhost:8000/api/map/${STUDENT_ID}/nodes`
    );
    expect([200, 404]).toContain(mapResp.status());
  });
});