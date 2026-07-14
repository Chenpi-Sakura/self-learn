"""Stage 4 Map schema（spec § 4.2 + ORM map_node.py 真实字段）。"""
from __future__ import annotations

from pydantic import BaseModel


class MapNodePosition(BaseModel):
    x: float
    y: float


class MapNodeResponse(BaseModel):
    node_id: UUID
    kp_id: UUID
    title: str
    position: MapNodePosition
    # ORM 实际枚举：active / sleeping / completed / locked
    status: str


class MapNodesResponse(BaseModel):
    nodes: list[MapNodeResponse] = []