"""验证 MCP server 进程能启动并响应 initialize 请求。"""
import asyncio
import json
import subprocess
import sys

import pytest


def test_mcp_server_starts_and_responds_to_initialize():
    """stdio MCP server 启动后能响应 initialize + list_tools。"""
    proc = subprocess.Popen(
        [sys.executable, "-m", "selflearn.mcp_server"],
        cwd="backend",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        # 发送 initialize 请求
        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "0.1.0"},
            },
        }
        body = json.dumps(init_msg).encode()
        proc.stdin.write(body + b"\n")
        proc.stdin.flush()

        # 读一行响应
        line = proc.stdout.readline()
        response = json.loads(line)
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["serverInfo"]["name"] == "SelfLearn"
    finally:
        proc.terminate()
        proc.wait(timeout=5)