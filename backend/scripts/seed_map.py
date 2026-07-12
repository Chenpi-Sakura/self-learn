"""Seed 5-10 个 KnowledgePoint（Stage 3 MVP — 自注意力机制 / Transformer 等示例）。

幂等性：重复执行不抛错（SELECT WHERE title = ... 已存在则跳过）。
"""
from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select

from selflearn.domain.knowledge_point import KnowledgePoint
from selflearn.infra.db import get_session_factory


SEED_KPS = [
    {"subject": "大语言模型", "title": "自注意力机制",
     "description": "Self-Attention 通过 QKV 矩阵计算序列内依赖。",
     "difficulty": 2, "prerequisites": []},
    {"subject": "大语言模型", "title": "多头注意力",
     "description": "Multi-Head 将 QKV 拆 h 份并行学习不同子空间。",
     "difficulty": 3, "prerequisites": ["自注意力机制"]},
    {"subject": "大语言模型", "title": "位置编码",
     "description": "Positional Encoding 注入序列顺序信息（sin/cos 或 RoPE）。",
     "difficulty": 2, "prerequisites": []},
    {"subject": "大语言模型", "title": "Transformer 编码器",
     "description": "Encoder = Multi-Head Self-Attention + FFN + 残差 + LN。",
     "difficulty": 3, "prerequisites": ["自注意力机制", "多头注意力"]},
    {"subject": "大语言模型", "title": "Transformer 解码器",
     "description": "Decoder = Masked Self-Attn + Cross-Attn + FFN。",
     "difficulty": 3, "prerequisites": ["Transformer 编码器"]},
]


async def main() -> None:
    factory = get_session_factory()
    async with factory() as session:
        inserted = 0
        for kp_data in SEED_KPS:
            stmt = select(KnowledgePoint).where(KnowledgePoint.title == kp_data["title"])
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing is not None:
                continue
            kp = KnowledgePoint(**kp_data, kp_id=uuid.uuid4())
            session.add(kp)
            inserted += 1
        await session.commit()
        print(f"[seed_map] inserted {inserted} knowledge_points (skipped {len(SEED_KPS) - inserted})")


if __name__ == "__main__":
    asyncio.run(main())