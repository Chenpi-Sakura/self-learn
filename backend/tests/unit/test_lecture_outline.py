"""extract_lecture_outline 单测：从 lecture_html 抽 sections/callouts/examples。"""
from __future__ import annotations

from selflearn.agents.lecture_outline import extract_lecture_outline


def test_extract_sections_from_h2_h3() -> None:
    """h2 / h3 标题都被抽到 sections。"""
    html = """
    <h2>核心概念</h2>
    <p>正文</p>
    <h3>子概念</h3>
    <p>子正文</p>
    """
    outline = extract_lecture_outline(html)
    assert outline["sections"] == ["核心概念", "子概念"]
    assert outline["callouts"] == []
    assert outline["examples"] == []


def test_extract_callouts() -> None:
    """callout 块抽到 callouts。"""
    html = """
    <p>上文</p>
    <div class="callout">缩放因子是 √d_k</div>
    <p>下文</p>
    """
    outline = extract_lecture_outline(html)
    assert outline["callouts"] == ["缩放因子是 √d_k"]


def test_extract_examples() -> None:
    """example 块抽到 examples。"""
    html = """
    <div class="example">d_model=512, d_k=64 时</div>
    """
    outline = extract_lecture_outline(html)
    assert outline["examples"] == ["d_model=512, d_k=64 时"]


def test_strip_nested_tags() -> None:
    """嵌套 HTML 标签被剥除（保留纯文本）。"""
    html = '<div class="callout"><strong>关键</strong> 缩放是 <code>√d_k</code></div>'
    outline = extract_lecture_outline(html)
    assert outline["callouts"] == ["关键 缩放是 √d_k"]


def test_empty_html_returns_empty_dict() -> None:
    """空 lecture_html 返回空字典。"""
    outline = extract_lecture_outline("")
    assert outline == {"sections": [], "callouts": [], "examples": []}


def test_full_real_world_html() -> None:
    """完整讲义样例覆盖三类抽取。"""
    html = """
<h2>核心概念</h2>
<p>Self-attention 通过 query 和 key 内积...</p>
<div class="callout">缩放因子是 √d_k</div>
<p>公式：$softmax(QK^T/√d_k)$</p>
<h3>例子</h3>
<div class="example">d_model=512, d_k=64</div>
"""
    outline = extract_lecture_outline(html)
    assert outline["sections"] == ["核心概念", "例子"]
    assert outline["callouts"] == ["缩放因子是 √d_k"]
    assert outline["examples"] == ["d_model=512, d_k=64"]
