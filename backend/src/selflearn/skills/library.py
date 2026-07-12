"""Skill markdown 文档 loader（Stage 3 § 9.1）。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import frontmatter

from selflearn.core.logging import get_logger


log = get_logger("skills")

SKILLS_DIR = Path(__file__).resolve().parents[4] / "docs" / "skills"


@dataclass
class Skill:
    name: str
    description: str
    body: str
    output_schema: str | None


_skill_library: dict[str, Skill] = {}


def load_all(skills_dir: Path | None = None) -> None:
    """进程启动时调一次，从 markdown 读 Skill。"""
    if skills_dir is None:
        skills_dir = SKILLS_DIR
    _skill_library.clear()
    for md_path in skills_dir.glob("*.md"):
        post = frontmatter.load(md_path)
        metadata: dict[str, object] = post.metadata
        if "name" not in metadata:
            log.warning("skills.skip_missing_name", path=str(md_path))
            continue
        raw_schema = metadata.get("output_schema")
        schema_str: str | None = raw_schema if isinstance(raw_schema, str) else None
        _skill_library[str(metadata["name"])] = Skill(
            name=str(metadata["name"]),
            description=str(metadata.get("description", "")),
            body=post.content,
            output_schema=schema_str,
        )
    log.info("skills.loaded", count=len(_skill_library))


def get(name: str) -> Skill:
    if name not in _skill_library:
        raise KeyError(f"skill_not_loaded:{name}")
    return _skill_library[name]