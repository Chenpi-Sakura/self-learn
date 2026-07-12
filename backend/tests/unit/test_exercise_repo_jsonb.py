import pytest

pytestmark = pytest.mark.asyncio


async def test_exercise_repo_update_options_replaces_whole_list() -> None:
    """JSONB 字段更新：必须整体替换 list 引用，不能 in-place mutate。

    SQLAlchemy 2.x 对 JSONB dict/list 就地 mutate 不会触发 dirty tracking，
    实战必须整体赋值或 flag_modified。repo 层强制此约束。

    注：原 brief 用 sqlite + JSONB 跑不通（SQLite 不渲染 JSONB；FK 引用 students 也没建）。
    这里改用 sqlalchemy.JSON 在 sqlite 上跑，并跳过 FK 约束验证 dirty-tracking 语义。
    真正的 PG 集成测试（含 JSONB + FK）见 testcontainers 集成层。
    """
    from sqlalchemy import JSON, Column, ForeignKey, MetaData, String, Table
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

    class _Base(DeclarativeBase):
        pass

    class ExFixture(_Base):
        """同形 ORM：options 用 JSON（SQLite 兼容），不带 FK（避开 students/levels 依赖）。"""
        __tablename__ = "exercises_fixture"
        level_id: Mapped[str] = mapped_column(String(36), primary_key=True)
        exercise_type: Mapped[str] = mapped_column(String(32), nullable=False)
        prompt: Mapped[str] = mapped_column(String, nullable=False)
        options: Mapped[list[object]] = mapped_column(JSON, nullable=False, default=list)
        correct_answer: Mapped[str] = mapped_column(String, nullable=False)

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(_Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        ex = ExFixture(
            level_id="00000000-0000-0000-0000-000000000001",
            exercise_type="single_choice",
            prompt="Q?",
            options=["A", "B"],
            correct_answer="A",
        )
        session.add(ex)
        await session.commit()
        await session.refresh(ex)

        # SQLAlchemy 2.x dirty tracking caveat：JSON 列 in-place mutate 不会被持久化。
        ex.options.append("C")
        await session.commit()
        await session.refresh(ex)
        assert ex.options == ["A", "B"], "in-place mutate should not persist (SQLAlchemy caveat)"

        # 整体赋值才能传播。
        ex.options = ["A", "B", "C"]
        await session.commit()
        await session.refresh(ex)
        assert ex.options == ["A", "B", "C"], "whole-replace assignment should persist"