"""tool.lint_html: nh3 白名单 + 预定义 class 清洗。"""

from __future__ import annotations

import re
from typing import Any

import nh3

ALLOWED_TAGS = {"h1", "h2", "h3", "p", "ul", "ol", "li", "strong", "em", "code", "pre", "blockquote", "table", "thead", "tbody", "tr", "th", "td", "br", "hr", "span", "div"}
ALLOWED_CLASSES_DEFAULT = {"callout", "formula", "example", "katex", "katex-display"}

def _attr_filter(allowed_classes: set[str]):
    def _filter(element: str, attr: str, value: str) -> str | None:
        if attr == "class":
            return value if value in allowed_classes else None
        if element in ("th", "td") and attr == "colspan":
            return value
        return None
    return _filter

async def lint_html(html: str, allowed_classes: list[str] | None = None) -> dict[str, Any]:
    """白名单清洗 HTML，返回 {cleaned, is_empty}。"""
    classes = set(allowed_classes) if allowed_classes else ALLOWED_CLASSES_DEFAULT
    cleaned = nh3.clean(html, tags=ALLOWED_TAGS, attributes={"p": {"class"}, "code": {"class"}, "pre": {"class"}, "span": {"class"}, "div": {"class"}, "th": {"colspan"}, "td": {"colspan"}}, attribute_filter=_attr_filter(classes))
    text_only = re.sub(r"<[^>]+>", "", cleaned).strip()
    return {"cleaned": cleaned, "is_empty": len(text_only) == 0}
