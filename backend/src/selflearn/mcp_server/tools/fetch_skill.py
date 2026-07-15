"""tool.fetch_skill: 读 SKILL.md。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import frontmatter

SKILLS_DIR = Path(__file__).resolve().parents[4] / "skills"

async def fetch_skill(skill_id: str) -> dict[str, Any]:
    """读 backend/skills/<skill_id>/SKILL.md。"""
    path = SKILLS_DIR / skill_id / "SKILL.md"
    if not path.exists():
        return {"ok": False, "error": f"skill_not_found:{skill_id}", "name": None, "description": None, "body": None, "output_schema": None, "mcp_prefetch": [], "mcp_tool_use": [], "max_retries": 0}
    post = frontmatter.load(path)
    meta: dict[str, Any] = post.metadata
    return {"ok": True, "error": None, "name": str(meta.get("name", skill_id)), "description": str(meta.get("description", "")), "body": post.content, "output_schema": meta.get("output_schema"), "mcp_prefetch": list(meta.get("mcp_prefetch", [])), "mcp_tool_use": list(meta.get("mcp_tool_use", [])), "max_retries": int(meta.get("max_retries", 0))}
