"""Skill markdown 文档 loader。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import frontmatter

from selflearn.core.logging import get_logger

log = get_logger("skills")
SKILLS_DIR = Path(__file__).resolve().parents[3] / "skills"  # backend/skills/


@dataclass
class Skill:
    name: str
    description: str
    body: str
    output_schema: str | None
    mcp_prefetch: list[str] = field(default_factory=list)
    mcp_tool_use: list[str] = field(default_factory=list)
    max_retries: int = 0


_skill_library: dict[str, Skill] = {}


def load_all(skills_dir: Path | None = None) -> None:
    """进程启动时调一次，从 backend/skills/<id>/SKILL.md 读 Skill。"""
    if skills_dir is None:
        skills_dir = SKILLS_DIR
    _skill_library.clear()
    if not skills_dir.exists():
        log.warning("skills.dir_not_found", path=str(skills_dir))
        return

    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue
        md_path = skill_dir / "SKILL.md"
        if not md_path.exists():
            continue
        post = frontmatter.load(md_path)
        meta: dict[str, Any] = post.metadata
        if "name" not in meta:
            log.warning("skills.skip_missing_name", path=str(md_path))
            continue
        _skill_library[str(meta["name"])] = Skill(
            name=str(meta["name"]),
            description=str(meta.get("description", "")),
            body=post.content,
            output_schema=str(meta["output_schema"]) if "output_schema" in meta else None,
            mcp_prefetch=list(meta.get("mcp_prefetch", [])),
            mcp_tool_use=list(meta.get("mcp_tool_use", [])),
            max_retries=int(meta.get("max_retries", 0)),
        )
    log.info("skills.loaded", count=len(_skill_library))


def get(name: str) -> Skill:
    if name not in _skill_library:
        raise KeyError(f"skill_not_loaded:{name}")
    return _skill_library[name]
