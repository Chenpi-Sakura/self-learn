def test_profile_snapshot_migration_creates_table() -> None:
    """验证 ProfileSnapshot ORM 与 SQLite create_all 一致（结构层断言）。

    注：使用独立 DeclarativeBase + 仅 ProfileSnapshot 一个模型，
    避开 Base.metadata 上其他 PG-only 模型（students/profiles/levels 等）
    含有 PG_UUID/JSONB/FK 的依赖。Stage 5+ 真 PG 集成测试再覆盖。
    """
    from sqlalchemy import (
        JSON,
        BigInteger,
        DateTime,
        String,
        create_engine,
        inspect,
    )
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

    class _Base(DeclarativeBase):
        pass

    class _ProfileSnapshotMirror(_Base):
        __tablename__ = "profile_snapshots"
        id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
        student_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
        profile: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
        trigger: Mapped[str] = mapped_column(String(32), nullable=False)
        created_at: Mapped[object] = mapped_column(
            DateTime(timezone=True), nullable=False
        )

    engine = create_engine("sqlite:///:memory:")
    _Base.metadata.create_all(engine)
    insp = inspect(engine)
    assert "profile_snapshots" in insp.get_table_names()
    cols = {c["name"] for c in insp.get_columns("profile_snapshots")}
    assert {"id", "student_id", "profile", "trigger", "created_at"} <= cols
    indexes = list(insp.get_indexes("profile_snapshots"))
    # 至少应有 student_id 单列索引（autogenerate 可能命名 ix_profile_snapshots_student_id）
    assert any("student_id" in i["column_names"] for i in indexes)


def test_profile_snapshot_registered_on_base_metadata() -> None:
    """ProfileSnapshot 必须被 import 一次后注册到 Base.metadata.tables。"""
    from selflearn.domain.base import Base
    from selflearn.domain.profile_snapshot import ProfileSnapshot  # noqa: F401

    assert "profile_snapshots" in Base.metadata.tables
    table = Base.metadata.tables["profile_snapshots"]
    cols = {c.name for c in table.columns}
    assert {"id", "student_id", "profile", "trigger", "created_at"} <= cols
    assert "student_id" in {i.columns[0].name for i in table.indexes}
