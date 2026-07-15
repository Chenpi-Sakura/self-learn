"""tool.lint_html 行为测试。"""
import pytest
from selflearn.mcp_server.tools.lint_html import lint_html

@pytest.mark.asyncio
async def test_lint_html_clean_allowed_tags():
    result = await lint_html("<h1>标题</h1><p>段落 <strong>强调</strong></p>")
    assert "<h1>" in result["cleaned"] and "<strong>" in result["cleaned"] and not result["is_empty"]

@pytest.mark.asyncio
async def test_lint_html_strip_script():
    result = await lint_html("<h1>ok</h1><script>alert(1)</script>")
    assert "<script>" not in result["cleaned"] and "alert" not in result["cleaned"]

@pytest.mark.asyncio
async def test_lint_html_strip_disallowed_class():
    result = await lint_html("<p class=\"evil\">x</p><p class=\"callout\">y</p>", ["callout"])
    assert "evil" not in result["cleaned"] and "callout" in result["cleaned"]

@pytest.mark.asyncio
async def test_lint_html_katex_preserved():
    result = await lint_html("<span class=\"katex\"><span class=\"katex-html\">x</span></span>")
    assert "katex" in result["cleaned"]

@pytest.mark.asyncio
async def test_lint_html_is_empty():
    assert (await lint_html(""))["is_empty"] is True
