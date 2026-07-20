"""Add recipe cover image columns (Unsplash).

Revision ID: b7c4e91a2f10
Revises: eff1e64b3e70
Create Date: 2026-07-20 03:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b7c4e91a2f10"
down_revision: Union[str, Sequence[str], None] = "eff1e64b3e70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("recipes", sa.Column("image_url", sa.String(length=1000), nullable=True))
    op.add_column("recipes", sa.Column("image_credit", sa.String(length=200), nullable=True))
    op.add_column(
        "recipes", sa.Column("image_credit_url", sa.String(length=500), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("recipes", "image_credit_url")
    op.drop_column("recipes", "image_credit")
    op.drop_column("recipes", "image_url")
