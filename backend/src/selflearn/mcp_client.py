"""MCP stdio client (lifespan wrapper)."""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import json
from pathlib import Path
import sys
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

BACKEND_DIR = str(Path(__file__).resolve().parents[2])


class _MCPClientProc:
    """Expose SelfLearn's simple ``call`` interface over an MCP ClientSession."""

    def __init__(self, session: ClientSession) -> None:
        self._session = session

    async def call(self, tool: str, **kwargs: Any) -> Any:
        """Call one MCP tool and decode its structured or text result."""
        result = await self._session.call_tool(tool, arguments=kwargs)
        if result.isError:
            message = self._text_content(result.content) or "unknown"
            return {"ok": False, "error": message}
        if result.structuredContent is not None:
            structured = result.structuredContent
            if set(structured) == {"result"}:
                return structured["result"]
            return structured
        text = self._text_content(result.content)
        if not text:
            return {}
        return json.loads(text)

    @staticmethod
    def _text_content(content: list[Any]) -> str:
        return "".join(str(item.text) for item in content if getattr(item, "type", None) == "text")


@asynccontextmanager
async def mcp_client_lifespan() -> AsyncIterator[_MCPClientProc]:
    """Start, initialize, and close the MCP stdio subprocess with its lifespan."""
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "selflearn.mcp_server"],
        cwd=BACKEND_DIR,
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield _MCPClientProc(session)
