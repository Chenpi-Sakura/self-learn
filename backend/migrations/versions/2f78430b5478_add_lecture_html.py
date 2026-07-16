"""add lecture_html to levels

Revision ID: 2f78430b5478
Revises: f1963078e4e4
Create Date: 2026-07-16

"""
from alembic import op
import sqlalchemy as sa


revision = "2f78430b5478"
down_revision = "f1963078e4e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "levels",
        sa.Column("lecture_html", sa.String(50000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("levels", "lecture_html")