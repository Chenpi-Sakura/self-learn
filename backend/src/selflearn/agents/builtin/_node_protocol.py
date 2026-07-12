"""Plan Agent / Director Agent 传给 Exercise Agent 的 `node` 参数接口约定。

`MapNode` ORM 实体满足此 Protocol；测试中用 `AsyncMock` + 手工 set 属性也能跑通。
"""
from __future__ import annotations

from typing import Protocol
from uuid import UUID

from selflearn.domain.knowledge_point import KnowledgePoint


class Node(Protocol):
    node_id: UUID
    kp: KnowledgePoint
