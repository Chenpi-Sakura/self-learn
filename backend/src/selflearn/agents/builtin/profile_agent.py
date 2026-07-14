"""ProfileAgent: 5 轮对话构建 6 维画像。"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from selflearn.agents.base import AbstractAgent
from selflearn.core.envelope import ActorRef, Envelope
from selflearn.domain.profile import Profile
from selflearn.infra.db import get_session_factory
from selflearn.progress.stream import progress_publish
from selflearn.progress.stages import ProgressEvent, Stage
from selflearn.skills.library import get as get_skill


class ProfileAgent(AbstractAgent):
    """skill.profile.build: 对话式 6 维画像构建。

    Stage 3 MVP: 跳过真 5 轮 UI 对话，直接读 payload.dimensions（前端 5 轮问答已在 gateway 收齐）→ 写 profiles 表。
    """

    agent_id = "profile-01"
    agent_type = "profile"
    queue = "agent.profile.work"
    # V1.3 Rule #13 第三子规则：Agent 类不声明 skills = [...]。

    DIMENSION_KEYS = [
        "knowledge_base", "visual_preference", "analytic_style",
        "goal_employment", "error_prone_type", "focus_duration",
    ]

    async def run(self, env: Envelope) -> Envelope:
        trace_id = env.trace_id
        student_id_raw = env.payload["student_id"]
        student_id = UUID(student_id_raw) if isinstance(student_id_raw, str) else student_id_raw

        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.PROFILE, status="running",
            payload={"student_id": str(student_id)},
        ))

        # 加载 Skill 做 sanity check（开发者文档：6 维必须全填）
        get_skill("skill.profile.build")

        # MVP：直接读 payload 里的 dimensions；任一缺失 → 默认 0.5
        payload_dim = env.payload.get("dimensions") or {}
        if not isinstance(payload_dim, dict):
            payload_dim = {}
        dimensions = {k: payload_dim.get(k, 0.5) if isinstance(payload_dim.get(k), (int, float)) else 0.5
                      for k in self.DIMENSION_KEYS}

        # 写库（Stage 3 MVP：直连 session。Stage 4 重构时引入 ProfileRepository）
        factory = get_session_factory()
        async with factory() as session:
            profile = Profile(
                student_id=student_id,
                dimensions=dimensions,
                tags=env.payload.get("tags", []),
                last_updated=datetime.now(timezone.utc),
            )
            session.add(profile)
            await session.commit()
            await session.refresh(profile)
            profile_id = str(profile.profile_id)

        # Stage 4 spec § 5.1 / § 10.3: SSE completed payload 用 spec 缩写维度键 + 含 tags
        # 前端 spec § 7.4 line 552 直接读 payload.profile as ProfileDimensions（kb/vp/as/ge/ept/fd）。
        _DIMENSION_KEY_MAP: dict[str, str] = {
            "knowledge_base": "kb", "visual_preference": "vp",
            "analytic_style": "as", "goal_employment": "ge",
            "error_prone_type": "ept", "focus_duration": "fd",
        }
        _short_dims: dict[str, float] = {
            _DIMENSION_KEY_MAP[k]: float(v)
            for k, v in dimensions.items()
            if k in _DIMENSION_KEY_MAP
        }
        _tags_raw = env.payload.get("tags", [])
        _tags: list[object] = list(_tags_raw) if isinstance(_tags_raw, list) else []

        await progress_publish(trace_id, ProgressEvent(
            stage=Stage.PROFILE, status="completed",
            payload={
                "profile_id": profile_id,  # 保留：reply envelope 测试要这个
                "profile": {"dimensions": _short_dims, "tags": _tags},
            },
        ))

        return Envelope(
            action="skill.completed",
            sender=ActorRef(type="agent", id=self.agent_id),
            target=ActorRef(type="gateway", id=env.sender.id),
            payload={"profile_id": profile_id, "dimensions": dimensions},
            trace_id=trace_id,
            parent_id=env.span_id,
        )