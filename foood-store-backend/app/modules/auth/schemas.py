from sqlmodel import SQLModel


class LoginRequest(SQLModel):
    """Body para POST /auth/login"""
    email: str
    password: str


class TokenResponse(SQLModel):
    """Respuesta del login: JWT + tipo"""
    access_token: str
    token_type: str = "bearer"
    usuario_id: int
    nombre: str
    roles: list[str]
