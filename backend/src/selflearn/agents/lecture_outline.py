"""lecture_outline: 从 lecture_html 提取结构化纲要供 exercise LLM 引用。"""
from __future__ import annotations

import re

_OUTLINE_RE_SECTION = re.compile(r"<h[23][^>]*>(.*?)</h[23]>", re.DOTALL)
_OUTLINE_RE_CALLOUT = re.compile(r'<div class="callout"[^>]*>(.*?)</div>', re.DOTALL)
_OUTLINE_RE_EXAMPLE = re.compile(r'<div class="example"[^>]*>(.*?)</div>', re.DOTALL)
_TAG_STRIP_RE = re.compile(r"<[^>]+>")


def _strip_tags(html_fragment: str) -> str:
    """去掉 HTML 标签 + 收尾空白。"""
    return _TAG_STRIP_RE.sub("", html_fragment).strip()


def extract_lecture_outline(lecture_html: str) -> dict[str, list[str]]:
    """从 lecture_html 提取结构化纲要，供 exercise LLM 在 explanation 里引用。

    Returns:
        {
            "sections": ["核心概念：self-attention", ...],  # h2/h3 标题
            "callouts": ["缩放因子是 √d_k...", ...],       # callout 块文本
            "examples": ["d_model=512 时...", ...],         # example 块文本
        }
    """
    return {
        "sections": [_strip_tags(m) for m in _OUTLINE_RE_SECTION.findall(lecture_html)],
        "callouts": [_strip_tags(m) for m in _OUTLINE_RE_CALLOUT.findall(lecture_html)],
        "examples": [_strip_tags(m) for m in _OUTLINE_RE_EXAMPLE.findall(lecture_html)],
    }
