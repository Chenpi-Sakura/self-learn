"""tool.create_level 单测：lecture_html 入参 + 截断 + None 跳过。

为避免 pytest-asyncio + module-level engine 的 'attached to a different loop'
问题，单测用 AsyncMock + patch session_factory 避免真 DB。
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from selflearn.mcp_server.tools.create_level import (
    MAX_LECTURE_HTML_LEN,
    create_level,
)


@pytest.mark.asyncio
async def test_create_level_accepts_lecture_html() -> None:
    """lecture_html 入参正常时，Level 行带该字段。"""
    node_id = str(uuid4())
    lecture = "<h2>概念</h2><p>讲解</p>"

    fake_level = MagicMock()
    fake_level.level_id = uuid4()
    fake_session = AsyncMock()
    fake_session.__aenter__ = AsyncMock(return_value=fake_session)
    fake_session.__aexit__ = AsyncMock(return_value=None)
    fake_session.add = MagicMock()
    fake_session.commit = AsyncMock()
    fake_session.refresh = AsyncMock(side_effect=lambda lvl: setattr(lvl, "level_id", fake_level.level_id))

    with patch("selflearn.mcp_server.tools.create_level.get_session_factory") as gsf:
        gsf.return_value = lambda: fake_session

        result = await create_level(node_id=node_id, lecture_html=lecture)

    assert result["ok"] is True
    assert "level_id" in result
    # 关键断言：Level(...) 调用传入了 lecture_html
    fake_session.add.assert_called_once()
    added_level = fake_session.add.call_args[0][0]
    assert added_level.lecture_html == lecture


@pytest.mark.asyncio
async def test_create_level_truncates_long_lecture_html() -> None:
    """lecture_html 超 MAX_LECTURE_HTML_LEN 时硬截断。"""
    node_id = str(uuid4())
    long_html = "<p>" + ("x" * (MAX_LECTURE_HTML_LEN + 1000)) + "</p>"

    fake_session = AsyncMock()
    fake_session.__aenter__ = AsyncMock(return_value=fake_session)
    fake_session.__aexit__ = AsyncMock(return_value=None)
    fake_session.add = MagicMock()
    fake_session.commit = AsyncMock()
    fake_session.refresh = AsyncMock()

    with patch("selflearn.mcp_server.tools.create_level.get_session_factory") as gsf:
        gsf.return_value = lambda: fake_session

        result = await create_level(node_id=node_id, lecture_html=long_html)

    assert result["ok"] is True
    fake_session.add.assert_called_once()
    added_level = fake_session.add.call_args[0][0]
    assert added_level.lecture_html is not None
    assert len(added_level.lecture_html) == MAX_LECTURE_HTML_LEN
    assert added_level.lecture_html == long_html[:MAX_LECTURE_HTML_LEN]


@pytest.mark.asyncio
async def test_create_level_lecture_html_none_skips_field() -> None:
    """lecture_html=None 时，Level 行的 lecture_html 字段为 None（不写列）。"""
    node_id = str(uuid4())

    fake_session = AsyncMock()
    fake_session.__aenter__ = AsyncMock(return_value=fake_session)
    fake_session.__aexit__ = AsyncMock(return_value=None)
    fake_session.add = MagicMock()
    fake_session.commit = AsyncMock()
    fake_session.refresh = AsyncMock()

    with patch("selflearn.mcp_server.tools.create_level.get_session_factory") as gsf:
        gsf.return_value = lambda: fake_session

        result = await create_level(node_id=node_id, lecture_html=None)

    assert result["ok"] is True
    fake_session.add.assert_called_once()
    added_level = fake_session.add.call_args[0][0]
    assert added_level.lecture_html is None