"""add_columns_to_ingrediente

Revision ID: 85772143cbc2
Revises: 722520f41860
Create Date: 2026-05-23 13:22:44.980522

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '85772143cbc2'
down_revision: Union[str, Sequence[str], None] = '722520f41860'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === STEP 1: Create new plural-named tables ===
    op.create_table('categorias',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('nombre', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
    sa.Column('descripcion', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    sa.Column('activo', sa.Boolean(), nullable=False),
    sa.Column('eliminado_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('parent_id', sa.BigInteger(), nullable=True),
    sa.ForeignKeyConstraint(['parent_id'], ['categorias.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_categorias_nombre'), 'categorias', ['nombre'], unique=True)
    op.create_table('permisos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nombre', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
    sa.Column('descripcion', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_permisos_nombre'), 'permisos', ['nombre'], unique=True)
    op.create_table('productos',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('nombre', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
    sa.Column('descripcion', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
    sa.Column('imagen_url', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    sa.Column('stock', sa.Integer(), nullable=False),
    sa.Column('activo', sa.Boolean(), nullable=False),
    sa.Column('costo_produccion', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('margen_ganancia', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('precio', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('creado_en', sa.DateTime(), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(), nullable=True),
    sa.Column('eliminado_en', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_productos_nombre'), 'productos', ['nombre'], unique=False)
    op.create_table('roles',
    sa.Column('codigo', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
    sa.Column('nombre', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
    sa.Column('descripcion', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    sa.PrimaryKeyConstraint('codigo')
    )
    op.create_index(op.f('ix_roles_nombre'), 'roles', ['nombre'], unique=True)
    op.create_table('usuarios',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('email', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
    sa.Column('password', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('nombre', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
    sa.Column('apellido', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
    sa.Column('cel', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
    sa.Column('activo', sa.Boolean(), nullable=False),
    sa.Column('creado_en', sa.DateTime(), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(), nullable=True),
    sa.Column('eliminado_en', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_usuarios_email'), 'usuarios', ['email'], unique=True)
    op.create_table('direcciones_entrega',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('calle', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
    sa.Column('numero', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
    sa.Column('piso', sqlmodel.sql.sqltypes.AutoString(length=10), nullable=True),
    sa.Column('departamento', sqlmodel.sql.sqltypes.AutoString(length=10), nullable=True),
    sa.Column('ciudad', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
    sa.Column('codigo_postal', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
    sa.Column('predeterminada', sa.Boolean(), nullable=False),
    sa.Column('usuario_id', sa.BigInteger(), nullable=False),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('productos_categorias',
    sa.Column('producto_id', sa.BigInteger(), nullable=False),
    sa.Column('categoria_id', sa.BigInteger(), nullable=False),
    sa.ForeignKeyConstraint(['categoria_id'], ['categorias.id'], ),
    sa.ForeignKeyConstraint(['producto_id'], ['productos.id'], ),
    sa.PrimaryKeyConstraint('producto_id', 'categoria_id')
    )
    op.create_table('productos_ingredientes',
    sa.Column('producto_id', sa.BigInteger(), nullable=False),
    sa.Column('ingrediente_id', sa.BigInteger(), nullable=False),
    sa.Column('cantidad_requerida', sa.Numeric(precision=10, scale=3), nullable=False),
    sa.Column('es_removible', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['ingrediente_id'], ['ingrediente.id'], ),
    sa.ForeignKeyConstraint(['producto_id'], ['productos.id'], ),
    sa.PrimaryKeyConstraint('producto_id', 'ingrediente_id')
    )
    op.create_table('roles_permisos',
    sa.Column('rol_codigo', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
    sa.Column('permiso_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['permiso_id'], ['permisos.id'], ),
    sa.ForeignKeyConstraint(['rol_codigo'], ['roles.codigo'], ),
    sa.PrimaryKeyConstraint('rol_codigo', 'permiso_id')
    )
    op.create_table('usuarios_roles',
    sa.Column('usuario_id', sa.BigInteger(), nullable=False),
    sa.Column('rol_codigo', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
    sa.Column('asignado_por_id', sa.BigInteger(), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['asignado_por_id'], ['usuarios.id'], ),
    sa.ForeignKeyConstraint(['rol_codigo'], ['roles.codigo'], ),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('usuario_id', 'rol_codigo')
    )

    # === STEP 2: Drop FKs referencing old singular tables ===
    op.drop_constraint('detallepedido_producto_id_fkey', 'detallepedido', type_='foreignkey')
    op.drop_constraint('pedido_usuario_id_fkey', 'pedido', type_='foreignkey')
    op.drop_constraint('direccion_entrega_usuario_id_fkey', 'direccion_entrega', type_='foreignkey')

    # === STEP 3: Drop old association tables ===
    op.drop_table('producto_ingrediente')
    op.drop_table('producto_categoria')

    # === STEP 4: Drop old singular base tables ===
    op.drop_index(op.f('ix_producto_nombre'), table_name='producto')
    op.drop_table('producto')
    op.drop_index(op.f('ix_usuario_email'), table_name='usuario')
    op.drop_table('usuario')
    op.drop_index(op.f('ix_categoria_nombre'), table_name='categoria')
    op.drop_table('categoria')

    # === STEP 5: Re-create FKs pointing to new plural tables ===
    op.create_foreign_key(None, 'detallepedido', 'productos', ['producto_id'], ['id'])
    op.create_foreign_key(None, 'direccion_entrega', 'usuarios', ['usuario_id'], ['id'])
    op.create_foreign_key(None, 'pedido', 'usuarios', ['usuario_id'], ['id'])

    # === STEP 6: Add new columns to ingrediente ===
    op.add_column('ingrediente', sa.Column('stock', sa.Numeric(precision=10, scale=3), nullable=False, server_default='0'))
    op.add_column('ingrediente', sa.Column('stock_seguridad', sa.Numeric(precision=10, scale=3), nullable=False, server_default='0'))
    op.add_column('ingrediente', sa.Column('unidad_medida', sa.String(length=20), nullable=False, server_default='UNIDAD'))
    op.add_column('ingrediente', sa.Column('costo_unitario', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
    op.alter_column('ingrediente', 'id',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False,
               autoincrement=True)
    op.alter_column('ingrediente', 'eliminado_en',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True)


def downgrade() -> None:
    pass
