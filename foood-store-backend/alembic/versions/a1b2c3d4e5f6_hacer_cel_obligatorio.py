"""Hacer campo cel NOT NULL en tabla usuario

Revision ID: a1b2c3d4e5f6
Revises: 722520f41860
Create Date: 2026-06-14 13:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '722520f41860'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("UPDATE usuarios SET cel = '0000000000' WHERE cel IS NULL")
    op.alter_column('usuarios', 'cel',
                    existing_type=sa.String(length=20),
                    nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('usuarios', 'cel',
                    existing_type=sa.String(length=20),
                    nullable=True)
