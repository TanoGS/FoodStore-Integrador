"""producto_imagenes_url_array_y_refresh_token

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-06-16 00:00:00.000000

Cambios:
1. Productos: reemplaza imagen_url (VARCHAR) por imagenes_url (TEXT[]).
   - Migra el valor existente al primer elemento del array.
   - Elimina la columna vieja.

2. Crea la tabla refresh_tokens para invalidación server-side de sesiones.
   - Vinculada a usuarios.id con CASCADE DELETE.
   - Índice en token_hash y en expires_at para limpieza eficiente.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Productos: imagen_url → imagenes_url TEXT[] ────────────────────
    # Agregar nueva columna array (nullable)
    op.add_column(
        'productos',
        sa.Column('imagenes_url', postgresql.ARRAY(sa.Text()), nullable=True),
    )
    # Migrar dato existente: si imagen_url tenía valor, lo ponemos en el array
    op.execute(
        """
        UPDATE productos
        SET imagenes_url = ARRAY[imagen_url]
        WHERE imagen_url IS NOT NULL
        """
    )
    # Eliminar columna vieja
    op.drop_column('productos', 'imagen_url')

    # ── 2. Tabla refresh_tokens ───────────────────────────────────────────
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            'usuario_id',
            sa.BigInteger(),
            sa.ForeignKey('usuarios.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        # Almacenamos el hash del token (SHA-256 hex), nunca el token en claro.
        sa.Column('token_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'creado_en',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('now()'),
        ),
    )
    op.create_index('ix_refresh_tokens_token_hash', 'refresh_tokens', ['token_hash'])
    op.create_index('ix_refresh_tokens_expires_at', 'refresh_tokens', ['expires_at'])


def downgrade() -> None:
    # ── 2. Eliminar tabla refresh_tokens ─────────────────────────────────
    op.drop_index('ix_refresh_tokens_expires_at', table_name='refresh_tokens')
    op.drop_index('ix_refresh_tokens_token_hash', table_name='refresh_tokens')
    op.drop_table('refresh_tokens')

    # ── 1. Productos: imagenes_url TEXT[] → imagen_url VARCHAR ───────────
    op.add_column(
        'productos',
        sa.Column('imagen_url', sa.String(255), nullable=True),
    )
    op.execute(
        """
        UPDATE productos
        SET imagen_url = imagenes_url[1]
        WHERE imagenes_url IS NOT NULL AND array_length(imagenes_url, 1) > 0
        """
    )
    op.drop_column('productos', 'imagenes_url')
