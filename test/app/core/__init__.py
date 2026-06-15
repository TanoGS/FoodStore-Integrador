# Capa de infraestructura compartida del proyecto.
#
# Subpaquetes:
#   - middleware/    → middlewares de Starlette/FastAPI (logging, timing)
#   - exceptions/   → excepciones custom y manejadores globales
#   - rate_limit/   → limitador de peticiones y middleware asociado
#
# Módulos en este nivel:
#   - config.py         → Settings leídos desde .env
#   - database.py       → engine SQLModel y dependencia get_session
#   - security.py       → JWT (encode/decode) y hashing de passwords
#   - deps.py           → dependencias FastAPI (get_current_user, require_role)
#   - base_repository.py→ CRUD genérico sobre cualquier modelo
#   - unit_of_work.py   → context manager para transacciones
#   - logger.py         → configuración del sistema de logging
