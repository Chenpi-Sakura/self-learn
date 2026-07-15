"""SelfLearn MCP server（stdio 进程）。

15 个 tool 分两类：
- utility: fetch_skill / lint_json / lint_html (3 个)
- db: 12 个表操作（见各 task）

启动方式：python -m selflearn.mcp_server
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

# 暂不 import 任何 tool，本 task 只搭骨架
mcp = FastMCP("SelfLearn")


def main() -> None:
    """启动 stdio server。"""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()