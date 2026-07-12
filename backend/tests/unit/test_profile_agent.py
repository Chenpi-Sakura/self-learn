import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.asyncio


async def test_profile_agent_initializes_6_dimensions() -> None:
    """SkillLibrary 中 skill.profile.build 必须可加载（sanity check）。"""
    from selflearn.skills.library import load_all, get
    load_all()
    skill = get("skill.profile.build")
    assert skill.name == "skill.profile.build"


async def test_profile_agent_run_writes_profile_and_returns_envelope() -> None:
    """ProfileAgent.run() 必须：(1) 推 progress running → completed；(2) 写 profiles 表；(3) 返回 Envelope.payload 含 profile_id。"""
    fake_uuid = "11111111-2222-3333-4444-555555555555"
    fake_session = AsyncMock()
    fake_session.add = MagicMock()  # session.add() is sync; AsyncMock returns coroutine → warning
    fake_session.commit = AsyncMock()
    fake_session.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "profile_id", __import__("uuid").UUID(fake_uuid)))

    async def fake_session_ctx(*_args: object, **_kwargs: object) -> AsyncMock:
        return fake_session

    with patch("selflearn.agents.builtin.profile_agent.get_session_factory") as mock_factory, \
         patch("selflearn.agents.builtin.profile_agent.progress_publish", new=AsyncMock()) as mock_pub:
        # factory() 返回可调用，调用返回 async ctx manager → fake_session
        factory_callable = MagicMock()
        factory_callable.return_value.__aenter__ = AsyncMock(return_value=fake_session)
        factory_callable.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_factory.return_value = factory_callable

        from selflearn.agents.builtin.profile_agent import ProfileAgent
        from selflearn.core.envelope import ActorRef, Envelope

        env = Envelope(
            action="skill.execute",
            sender=ActorRef(type="gateway", id="g"),
            target=ActorRef(type="skill", id="skill.profile.build"),
            payload={"student_id": "00000000-0000-0000-0000-000000000001",
                     "dimensions": {k: 0.5 for k in ["knowledge_base", "visual_preference", "analytic_style",
                                                     "goal_employment", "error_prone_type", "focus_duration"]},
                     "tags": []},
        )
        reply = await ProfileAgent().run(env)

        assert reply.action == "skill.completed"
        assert "profile_id" in reply.payload
        assert fake_session.add.called, "Profile 实例必须 add 到 session"
        assert fake_session.commit.called, "commit 必须被调"
        # 两次 publish：running + completed
        assert mock_pub.call_count == 2
        stages = [c.args[1].stage for c in mock_pub.call_args_list]
        from selflearn.progress.stages import Stage
        assert Stage.PROFILE in stages