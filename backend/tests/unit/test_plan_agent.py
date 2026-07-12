"""Unit tests for PlanAgent + seed_map.py (Task 8)."""
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


async def test_plan_agent_skill_loads() -> None:
    """SkillLibrary skill.plan.generate must load."""
    from selflearn.skills.library import load_all, get
    load_all()
    skill = get("skill.plan.generate")
    assert skill.name == "skill.plan.generate"


async def test_seed_map_file_exists() -> None:
    """seed_map.py must exist."""
    assert os.path.exists("scripts/seed_map.py"), "seed_map.py must exist"


async def test_plan_agent_run_writes_map_nodes_and_returns_envelope() -> None:
    """PlanAgent.run() must push progress running -> completed, create MapNodes, return Envelope."""
    import uuid as _uuid

    fake_kps = []
    for _ in range(3):
        kp = MagicMock()
        kp.kp_id = MagicMock(__str__=lambda s: "fake-kp-" + str(id(kp))[-4:])
        fake_kps.append(kp)

    fake_session = AsyncMock()
    fake_session.add = MagicMock()
    fake_session.commit = AsyncMock()
    fake_session.flush = AsyncMock()
    fake_session.execute = AsyncMock(
        return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=fake_kps))))
    )
    fake_session.refresh = AsyncMock(
        side_effect=lambda obj: setattr(obj, "node_id", _uuid.UUID("22222222-3333-4444-5555-666666666666"))
    )

    with patch("selflearn.agents.builtin.plan_agent.get_session_factory") as mock_factory, \
         patch("selflearn.agents.builtin.plan_agent.progress_publish", new=AsyncMock()) as mock_pub:
        factory_callable = MagicMock()
        factory_callable.return_value.__aenter__ = AsyncMock(return_value=fake_session)
        factory_callable.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_factory.return_value = factory_callable

        from selflearn.agents.builtin.plan_agent import PlanAgent
        from selflearn.core.envelope import ActorRef, Envelope

        env = Envelope(
            action="skill.execute",
            sender=ActorRef(type="gateway", id="g"),
            target=ActorRef(type="skill", id="skill.plan.generate"),
            payload={"student_id": "00000000-0000-0000-0000-000000000001"},
        )
        reply = await PlanAgent().run(env)

        assert reply.action == "skill.completed"
        node_count = reply.payload["node_count"]
        node_ids = reply.payload["node_ids"]
        assert isinstance(node_count, int) and node_count == 3
        assert isinstance(node_ids, list) and len(node_ids) == 3
        assert fake_session.add.call_count == 3, "3 MapNodes must be added"
        assert fake_session.commit.called
        assert mock_pub.call_count == 2