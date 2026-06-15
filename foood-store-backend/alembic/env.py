import os
import sys
from logging.config import fileConfig

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from sqlmodel import SQLModel

# Modelos Catálogo de Productos
from core.config import settings

from app.modules.pedido.models import Pedido, DetallePedido, HistorialEstadoPedido
from app.modules.direccion.models import DireccionEntrega
# Modelos Identidad y Acceso
from app.modules.usuario.models import Usuario

# Objeto de configuración de Alembic
config = context.config

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Configuración de logs
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

#  Metadata de SQLModel
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
  
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
