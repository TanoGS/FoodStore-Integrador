"""agregar_tipo_entrega_a_pedidos

Revision ID: f1a2b3c4d5e6
Revises: 4b2c1a8d3e5f
Create Date: 2026-06-14 14:00:00.000000

Agrega el campo tipo_entrega a la tabla pedidos para distinguir
entre pedidos para consumir en el local (EN_LOCAL) y delivery (DELIVERY).
Los pedidos existentes quedan como DELIVERY por defecto.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = '4b2c1a8d3e5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agregar columna tipo_entrega con default 'DELIVERY' para pedidos existentes
    op.add_column(
        'pedidos',
        sa.Column('tipo_entrega', sa.String(length=20), nullable=False, server_default='DELIVERY')
    )


def downgrade() -> None:
    op.drop_column('pedidos', 'tipo_entrega')
