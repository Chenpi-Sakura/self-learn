# Backlog — HTML 富讲义（Lecture HTML）

**日期**：2026-07-15
**状态**：📋 Backlog（已澄清需求，未实现）
**关联 spec（拟）**：`docs/superpowers/specs/2026-07-XX-html-lecture-design.md`（待 Agent 架构 spec 落地后回填）
**阻塞**：Agent 架构 spec（`backlog/2026-07-15-agent-architecture.md`）需先确定，本任务的 Agent 调用形态才能最终敲定

---

## 一句话描述

`levels` 表加 `lecture_html` 字段，LLM 在 Director 关卡生成时产出一段白名单约束的 HTML 讲义，前端 `LecturePane` 渲染该 HTML 替代当前的"显示第一道题 prompt"占位。

---

## 已确认的设计决策

| # | 决策 | 选择 |
|---|---|---|
| 1 | LLM 调用 | 两次（lecture + exercise 分开），Director 内顺序串行 |
| 2 | 存储格式 | 后端存 HTML（`level.lecture_html`） |
| 3 | HTML 约束 | 白名单标签（h1/h2/h3/p/ul/ol/li/strong/em/code/pre/blockquote/table）+ 预定义 class（`.callout` `.formula` `.example`） |
| 4 | 公式 | v1 上 KaTeX，LLM 出 LaTeX（`$inline$` `$$block$$`） |
| 5 | 长度 | 800-1500 字（LLM 输出 prompt 里约束），DB 层用 `VARCHAR(20000)` 兜底截断 + log warning |
| 6 | 旧关卡 | `lecture_html` 为 NULL → LecturePane 显示"该关卡尚无讲义，请重新启动关卡" |
| 7 | 视觉风格 | 风格 1 古典藏书（米黄底 + 靛蓝标题 + 朱红强调，楷体 + Times） |
| 8 | 字段名 | `lecture_html` |

## 未拍板（依赖 Agent 架构 spec）

- **失败策略**：硬失败 / 软失败 / 重试后软失败
- **代码路径**："独立 LectureAgent class" vs "LLMAgent + 注入 skill.lecture.generate"
- **ReviewAgent 怎么处理讲义**：讲义走独立净化路径 / 复用 ReviewAgent 部分规则
- **后置校验**：bleach/nh3 净化 + 长度截断

---

## 数据模型变更（草案）

```sql
-- Alembic migration 或手动 ALTER
ALTER TABLE levels ADD COLUMN lecture_html VARCHAR(20000);
```

ORM 层（`backend/src/selflearn/domain/level.py`）：
```python
lecture_html: Mapped[str | None] = mapped_column(String(20000), nullable=True)
```

Schema 层（`backend/src/selflearn/schemas/level.py`）：
```python
class LevelDetailResponse(BaseModel):
    level_id: UUID
    node_id: UUID
    status: str
    exercises: list[ExerciseResponse] = []
    lecture_html: str | None = None   # 新增
```

## LLM 接口（草案）

新 prompt 模板（`backend/prompts/lecture_generation_v1.yaml`）：
- type: `lecture_generation`
- version: `v1`
- 约束：白名单标签、预定义 class、KaTeX 公式
- 长度：800-1500 字
- 提示：先核心概念 → 关键细节 → 1-2 个 example → 小结

调用入口：根据 Agent 架构 spec，可能是
- `LectureAgent(env, kp_title).run_sync()`（独立 class）
- `LLMAgent(env).run(skill="skill.lecture.generate", prompt_args={...})`（全能 Agent + skill 注入）

## 前端变更（草案）

`frontend/src/panes/LecturePane.tsx`：
- 接 `levelId` prop（已有）
- `getLevel(levelId)` 拿 `lecture_html`
- 走 `DOMPurify.sanitize(html, ALLOWED_TAGS, ALLOWED_ATTRS, ALLOWED_CLASSES)`
- `dangerouslySetInnerHTML` 注入
- NULL 时显示"该关卡尚无讲义，请重新启动关卡"

新 CSS（`frontend/src/styles/lecture.css`）：
- `.lecture` 容器：米黄底 `#FBF7EC`，楷体 + Times
- `.lecture h1/h2/h3`：靛蓝 `#1B3B6F` + 衬线
- `.lecture .callout`：左边 4px 朱红竖条 + 浅黄底
- `.lecture .formula`：白底 + 1px border + 等宽
- `.lecture .example`：浅米底 + 楷体
- `.lecture code`：等宽
- KaTeX：内置样式（包 katex.min.css）

## 测试清单（草案）

- `tests/unit/test_lecture_agent.py`（生成 + 重试 + 净化）
- `tests/unit/test_lecture_sanitize.py`（白名单边界：剔除 `<script>`、内联 on*、不允许的 class）
- `tests/unit/test_lecture_length.py`（超长截断 + warning）
- `e2e/lecture.spec.ts`（启动关卡 → 看 LecturePane 渲染 HTML）

---

## 实现路径（等 Agent 架构 spec 落地后定）

**乐观路径**：
1. Agent 架构 spec 完成 + 落地
2. 写本讲义 spec（依据 Agent 架构）
3. writing-plans 出实施计划
4. 执行

**保守路径**（如果 Agent 架构要拖一阵）：
- 临时方案：先按现状（独立 LectureAgent class）做讲义，代码上预留 skill 注入点
- 后续：Agent 架构 spec 落地时再迁

---

## 风险与未决

1. **LLM 输出的 HTML 不稳定**——同样的 prompt 不同次可能吐出不同结构。**白名单净化是硬底线**。
2. **KaTeX 包体积**——约 280KB（katex.min.css）+ 200KB（katex.min.js）首屏加载，要看是否要 code-splitting
3. **XSS 攻击面**——LLM 不可信 + `dangerouslySetInnerHTML` 双重风险，必须 sanitization
4. **讲解内容质量**——5 个 KP 现有 description 只有一句话，LLM 是基于 KP title + description 自己扩写，**质量天花板由 prompt 决定**。需要看实际效果调 prompt
5. **风格 1 在长讲义里是否耐看**——米黄底 + 楷体长时间阅读是否累，要用户实测反馈

---

## 评估标准

实现完成后验证：
- 启动 1 个关卡，看 LecturePane 是否能渲染讲义（不是题目）
- 渲染出的 HTML 是否包含：标题层级、callout、formula、example
- KaTeX 公式能否正常显示（如 $\sqrt{d_k}$、$softmax(\frac{QK^T}{\sqrt{d_k}})$）
- 关卡重启后，第二次启动是否复用（与现有 level/start 幂等性一致）
- 旧关卡（level.lecture_html=NULL）显示占位提示
- XSS 测试：手工插入 `<script>alert(1)</script>` 到 LLM 输出是否被净化

---

## 不要做的事

- ❌ 不实现图片 / 视频 / iframe（v1）
- ❌ 不实现代码执行沙箱（v1）
- ❌ 不实现讲义编辑 / 版本管理
- ❌ 不实现互动式组件（路线 4，留给未来）
- ❌ 不在本次重做 ReviewAgent 或其他 Agent 架构（独立 backlog）
- ❌ 不迁移历史关卡讲义（按占位提示处理）
