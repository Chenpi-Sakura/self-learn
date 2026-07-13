"""stage4 profile_snapshots

Revision ID: f1963078e4e4
Revises: 8ae5ad324ca9
Create Date: 2026-07-13 20:03:37.084515

"""
from alembic import op
import sqlalchemy as sa


revision = 'f1963078e4e4'
down_revision = '8ae5ad324ca9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 画像演变快照（Stage 4 spec § 5.3）
    # 写入触发：关卡完成时由 DirectorAgent 通过 ProfileRepository.apply_delta 调用。
    # 读取触发：前端 GET /api/profile/{student_id}/history。
    op.create_table(
        "profile_snapshots",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.String(36), nullable=False),
        sa.Column("profile", sa.JSON, nullable=False),
        sa.Column("trigger", sa.String(32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_profile_snapshots_student_id", "profile_snapshots", ["student_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_profile_snapshots_student_id", table_name="profile_snapshots")
    op.drop_table("profile_snapshots")
