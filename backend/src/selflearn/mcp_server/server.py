"""SelfLearn MCP server（stdio 进程）。

15 个 tool 分两类：
- utility: fetch_skill / lint_json / lint_html (3 个)
- db: 12 个表操作（见各 task）

启动方式：python -m selflearn.mcp_server
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from selflearn.mcp_server.tools.fetch_skill import fetch_skill
from selflearn.mcp_server.tools.lint_html import lint_html
from selflearn.mcp_server.tools.lint_json import lint_json

mcp = FastMCP("SelfLearn")

mcp.add_tool(fetch_skill, name="tool.fetch_skill")
mcp.add_tool(lint_json, name="tool.lint_json")
mcp.add_tool(lint_html, name="tool.lint_html")


def main() -> None:
    """启动 stdio server。"""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
