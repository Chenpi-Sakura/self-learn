"""stage3 business tables

Revision ID: 8ae5ad324ca9
Revises: 0001
Create Date: 2026-07-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "8ae5ad324ca9"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # knowledge_points
    op.create_table(
        "knowledge_points",
        sa.Column("kp_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("subject", sa.String(128), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("difficulty", sa.SmallInteger, nullable=False),
        sa.Column("prerequisites", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("difficulty BETWEEN 1 AND 5", name="ck_kp_difficulty"),
    )
    op.create_index("idx_kp_subject", "knowledge_points", ["subject"])

    # map_nodes（依赖 students 表，Stage 2 已有）
    op.create_table(
        "map_nodes",
        sa.Column("node_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", UUID(as_uuid=True),
                  sa.ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False),
        sa.Column("kp_id", UUID(as_uuid=True),
                  sa.ForeignKey("knowledge_points.kp_id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("branch_type", sa.String(32), nullable=False, server_default="main"),
        sa.Column("position", JSONB, nullable=False, server_default=sa.text("'{\"x\": 0, \"y\": 0}'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("status IN ('active','sleeping','completed','locked')", name="ck_mn_status"),
        sa.CheckConstraint("branch_type IN ('main','interest')", name="ck_mn_branch"),
    )
    op.create_index("idx_map_nodes_student_status", "map_nodes", ["student_id", "status"])

    # levels
    op.create_table(
        "levels",
        sa.Column("level_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("node_id", UUID(as_uuid=True),
                  sa.ForeignKey("map_nodes.node_id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="generated"),
        sa.Column("form", sa.String(32), nullable=False, server_default="exercise"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("form IN ('exercise','document','mindmap','code')", name="ck_l_form"),
    )
    op.create_index("idx_levels_node", "levels", ["node_id"])

    # exercises
    op.create_table(
        "exercises",
        sa.Column("exercise_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("level_id", UUID(as_uuid=True),
                  sa.ForeignKey("levels.level_id", ondelete="CASCADE"), nullable=False),
        sa.Column("exercise_type", sa.String(32), nullable=False),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("options", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("correct_answer", sa.Text, nullable=False),
        sa.Column("explanation", sa.Text, nullable=False, server_default=""),
        sa.Column("difficulty", sa.SmallInteger, nullable=False, server_default="1"),
        sa.Column("score", sa.Numeric(4, 2), nullable=False, server_default="1.0"),
        sa.CheckConstraint("exercise_type IN ('single_choice','fill_blank','short_answer','code')", name="ck_e_type"),
        sa.CheckConstraint("difficulty BETWEEN 1 AND 3", name="ck_e_diff"),
    )
    op.create_index("idx_exercises_level", "exercises", ["level_id"])

    # level_completions
    op.create_table(
        "level_completions",
        sa.Column("completion_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("level_id", UUID(as_uuid=True),
                  sa.ForeignKey("levels.level_id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", UUID(as_uuid=True),
                  sa.ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("duration_seconds", sa.Integer, nullable=False),
        sa.Column("answers", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("metrics", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("submitted_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_lc_student", "level_completions", ["student_id"])
    op.create_index("idx_lc_level", "level_completions", ["level_id"])

    # review_results
    op.create_table(
        "review_results",
        sa.Column("review_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("level_id", UUID(as_uuid=True),
                  sa.ForeignKey("levels.level_id", ondelete="CASCADE"), nullable=False),
        sa.Column("verdict", sa.String(32), nullable=False),
        sa.Column("score", sa.Numeric(4, 2), nullable=False),
        sa.Column("issues", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("verdict IN ('passed','rejected','needs_fix')", name="ck_rr_verdict"),
    )
    op.create_index("idx_rr_level", "review_results", ["level_id"])


def downgrade() -> None:
    op.drop_index("idx_rr_level", table_name="review_results")
    op.drop_table("review_results")
    op.drop_index("idx_lc_level", table_name="level_completions")
    op.drop_index("idx_lc_student", table_name="level_completions")
    op.drop_table("level_completions")
    op.drop_index("idx_exercises_level", table_name="exercises")
    op.drop_table("exercises")
    op.drop_index("idx_levels_node", table_name="levels")
    op.drop_table("levels")
    op.drop_index("idx_map_nodes_student_status", table_name="map_nodes")
    op.drop_table("map_nodes")
    op.drop_index("idx_kp_subject", table_name="knowledge_points")
    op.drop_table("knowledge_points")