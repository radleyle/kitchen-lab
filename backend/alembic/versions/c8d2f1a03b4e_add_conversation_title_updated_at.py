"""Add title and updated_at to assistant conversations (Ask history).

Revision ID: c8d2f1a03b4e
Revises: b7c4e91a2f10
Create Date: 2026-07-20 05:05:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c8d2f1a03b4e"
down_revision: Union[str, Sequence[str], None] = "b7c4e91a2f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assistant_conversations",
        sa.Column("title", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "assistant_conversations",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("assistant_conversations", "updated_at")
    op.drop_column("assistant_conversations", "title")
