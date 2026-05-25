"""dominio_3_pedidos_historial_auditoria

Revision ID: 2a6aaf476cba
Revises: c9ae320f08b6
Create Date: 2026-05-04 22:38:57.847767

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2a6aaf476cba'
down_revision: Union[str, Sequence[str], None] = 'c9ae320f08b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # Tabla: pedidos
    # -----------------------------------------------------------------------
    op.create_table(
        'pedidos',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('usuario_id', sa.BigInteger(), nullable=False),
        sa.Column('direccion_id', sa.BigInteger(), nullable=True),
        sa.Column('estado_codigo', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column('forma_pago_codigo', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column('subtotal', sa.Numeric(10, 2), nullable=False),
        sa.Column('descuento', sa.Numeric(10, 2), nullable=False),
        sa.Column('costo_envio', sa.Numeric(10, 2), nullable=False),
        sa.Column('total', sa.Numeric(10, 2), nullable=False),
        sa.Column('notas', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('creado_en', sa.DateTime(timezone=True), nullable=False),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['direccion_id'], ['direcciones_entrega.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    # -----------------------------------------------------------------------
    # Tabla: detalles_pedido  (PK compuesta + snapshot inmutable)
    # -----------------------------------------------------------------------
    op.create_table(
        'detalles_pedido',
        sa.Column('pedido_id', sa.BigInteger(), nullable=False),
        sa.Column('producto_id', sa.BigInteger(), nullable=False),
        sa.Column('cantidad', sa.Integer(), nullable=False),
        sa.Column('nombre_snapshot', sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
        sa.Column('precio_snapshot', sa.Numeric(10, 2), nullable=False),
        sa.Column('subtotal_snap', sa.Numeric(10, 2), nullable=False),
        sa.Column('personalizacion', postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column('creado_en', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['pedido_id'], ['pedidos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['producto_id'], ['productos.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('pedido_id', 'producto_id'),
    )

    # -----------------------------------------------------------------------
    # Tabla: historial_estados_pedido  (Audit Trail — APPEND-ONLY)
    # -----------------------------------------------------------------------
    op.create_table(
        'historial_estados_pedido',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('pedido_id', sa.BigInteger(), nullable=False),
        sa.Column('estado_desde', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
        sa.Column('estado_hacia', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column('usuario_id', sa.BigInteger(), nullable=True),
        sa.Column('motivo', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('creado_en', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['pedido_id'], ['pedidos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('historial_estados_pedido')
    op.drop_table('detalles_pedido')
    op.drop_table('pedidos')

