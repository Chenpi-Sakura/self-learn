"""MCP test conftest — DB tests need session-scope event loop.

asyncpg connections are bound to a loop; pytest-asyncio default is
function-scope → second DB test gets "Event loop is closed". All DB-touching
tests in this dir use @pytest.mark.asyncio(loop_scope="session") instead.
"""
