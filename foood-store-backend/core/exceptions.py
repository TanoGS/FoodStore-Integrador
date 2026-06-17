"""
core/exceptions.py
==================
Jerarquía de excepciones de dominio de FoodStore.

Ventajas sobre HTTPException directo en services:
  - Los services no importan FastAPI → son testeables sin HTTP.
  - Un único punto de mapeo excepción → status code + formato JSON.
  - El formato de error es consistente en toda la API.

Jerarquía:
    AppError (base)
    ├── NotFoundError          404
    ├── ForbiddenError         403
    ├── UnauthorizedError      401
    ├── BadRequestError        400
    ├── ConflictError          409
    ├── UnprocessableError     422
    ├── ServiceUnavailableError 503
    └── BadGatewayError        502
"""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


# ===========================================================================
# Base
# ===========================================================================

class AppError(Exception):
    """Excepción base de dominio. Todos los handlers la capturan."""

    status_code: int = 500
    default_message: str = "Error interno del servidor."
    code: str = "internal_error"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


# ===========================================================================
# Subclases concretas
# ===========================================================================

class NotFoundError(AppError):
    status_code = 404
    default_message = "Recurso no encontrado."
    code = "not_found"


class ForbiddenError(AppError):
    status_code = 403
    default_message = "No tenés permisos para realizar esta acción."
    code = "forbidden"


class UnauthorizedError(AppError):
    status_code = 401
    default_message = "No autenticado o credenciales inválidas."
    code = "unauthorized"


class BadRequestError(AppError):
    status_code = 400
    default_message = "Solicitud inválida."
    code = "bad_request"


class ConflictError(AppError):
    status_code = 409
    default_message = "Conflicto con el estado actual del recurso."
    code = "conflict"


class UnprocessableError(AppError):
    status_code = 422
    default_message = "Los datos enviados no son válidos."
    code = "unprocessable"


class ServiceUnavailableError(AppError):
    status_code = 503
    default_message = "Servicio externo no disponible."
    code = "service_unavailable"


class BadGatewayError(AppError):
    status_code = 502
    default_message = "Error en la comunicación con el servicio externo."
    code = "bad_gateway"


# ===========================================================================
# Handler global — registrar en main.py
# ===========================================================================

async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """
    Convierte cualquier AppError en una respuesta JSON con formato unificado:
        { "detail": "<mensaje>", "code": "<código>" }
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "code": exc.code},
    )
