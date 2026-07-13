def test_profile_snapshot_table_exists() -> None:
    from selflearn.domain.profile_snapshot import ProfileSnapshot  # noqa: F401
    from selflearn.domain.base import Base
    assert "profile_snapshots" in Base.metadata.tables
