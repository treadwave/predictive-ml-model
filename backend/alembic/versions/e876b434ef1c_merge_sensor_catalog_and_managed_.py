"""merge sensor catalog and managed accounts

Revision ID: e876b434ef1c
Revises: b48a001, c4f1a2d9e8b7
Create Date: 2026-11-12 12:54:27.548828

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = 'e876b434ef1c'
down_revision: str | Sequence[str] | None = ('b48a001', 'c4f1a2d9e8b7')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
