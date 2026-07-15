"""tool.fetch_skill 行为测试。"""
import pytest
from selflearn.mcp_server.tools.fetch_skill import fetch_skill

@pytest.mark.asyncio
async def test_fetch_skill_not_found():
    result = await fetch_skill("nonexistent.skill.id")
    assert result["ok"] is False and "skill_not_found" in result["error"]

@pytest.mark.asyncio
async def test_fetch_skill_existing(tmp_path):
    import selflearn.mcp_server.tools.fetch_skill as module
    original_dir = module.SKILLS_DIR
    module.SKILLS_DIR = tmp_path
    try:
        skill_dir = tmp_path / "skill.test"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: skill.test\ndescription: Use when testing.\noutput_schema: schemas/test.schema.json\nmcp_prefetch:\n  - tool.get_kp\nmcp_tool_use: []\nmax_retries: 1\n---\n\n# Body\n", encoding="utf-8")
        result = await fetch_skill("skill.test")
        assert result["ok"] is True and result["name"] == "skill.test"
        assert result["mcp_prefetch"] == ["tool.get_kp"] and result["max_retries"] == 1
    finally:
        module.SKILLS_DIR = original_dir
