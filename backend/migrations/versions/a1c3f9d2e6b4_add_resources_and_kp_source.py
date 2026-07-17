"""add resources table and kp.source / kp.source_content_md

Revision ID: a1c3f9d2e6b4
Revises: 2f78430b5478
Create Date: 2026-07-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "a1c3f9d2e6b4"
down_revision = "2f78430b5478"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # KP 加列
    op.add_column("knowledge_points", sa.Column("source", sa.String(500), nullable=True))
    op.add_column("knowledge_points", sa.Column("source_content_md", sa.Text(), nullable=True))

    # 新表 resources
    op.create_table(
        "resources",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # NOTE: student_id 不加 FK——与 map_nodes.student_id（plain String，无 FK）保持一致。
        # KEEP_STUDENT 唯一账户以 profiles 行为锚点，students 表未必有对应行，
        # RESTRICT FK 会阻断上传。故沿用项目既有 no-FK 约定。
    )
    op.create_index(
        "idx_resources_student_active",
        "resources",
        ["student_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "idx_resources_student_name",
        "resources",
        ["student_id", "name"],
    )


def downgrade() -> None:
    op.drop_index("idx_resources_student_name", table_name="resources")
    op.drop_index("idx_resources_student_active", table_name="resources")
    op.drop_table("resources")
    op.drop_column("knowledge_points", "source_content_md")
    op.drop_column("knowledge_points", "source")
