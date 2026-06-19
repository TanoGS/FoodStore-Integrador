from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

# Configuración JWT
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Configuración Passlib para encriptar contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# =====================================================================
# 1. EL NUEVO GUARDIA: EXTRACTOR DE TOKENS DESDE COOKIES
# =====================================================================
class OAuth2PasswordBearerWithCookie(OAuth2PasswordBearer):
    """
    Clase personalizada que hereda de OAuth2PasswordBearer.
    Busca el token JWT primero en las Cookies HttpOnly. 
    Si no lo encuentra, hace un fallback a la cabecera Authorization para que Swagger UI siga funcionando.
    """
    async def __call__(self, request: Request) -> Optional[str]:
        # 1. Priorizamos el header Authorization (enviado explícitamente por el
        #    cliente desde su sessionStorage por-pestaña). Esto evita que la
        #    cookie compartida entre pestañas sobreescriba la sesión activa en
        #    cada tab cuando hay múltiples sesiones abiertas simultáneamente.
        authorization = request.headers.get("Authorization")

        # 2. Fallback: Si no hay header, leemos la cookie HttpOnly del login.
        if not authorization:
            authorization = request.cookies.get("access_token")
        
        # 3. Si definitivamente no hay token, lanzamos error 401
        if not authorization:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="No autenticado. Inicie sesión.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        
        # 4. Limpiamos el prefijo "Bearer "
        scheme, _, param = authorization.partition(" ")
        if scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Credenciales inválidas. Formato Bearer requerido.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        
        return param

# Instanciamos nuestro nuevo guardia indicándole cuál es la ruta de login para Swagger
oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="/api/v1/usuarios/login")


# =====================================================================
# 2. FUNCIONES DE HASH Y VERIFICACIÓN
# =====================================================================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# =====================================================================
# 3. CREACIÓN DEL TOKEN JWT
# =====================================================================
def create_access_token(subject: str, roles: List[str], permisos: Optional[List[str]] = None, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Empaquetamos el ID del usuario (sub), sus roles y sus permisos en el JWT
    to_encode = {"exp": expire, "sub": str(subject), "roles": roles, "permisos": permisos or []}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# =====================================================================
# 4. DEPENDENCIA PARA PROTEGER RUTAS (GET CURRENT USER)
# =====================================================================
# Esquema rápido interno para leer el token
class TokenData(BaseModel):
    id: str
    roles: List[str]
    permisos: List[str] = []

def decode_access_token(token: str) -> TokenData:
    """
    Decodifica un JWT raw y devuelve los datos del usuario.
    Helper reutilizable para endpoints que no reciben el token vía Depends
    (p. ej. WebSockets, donde el token viene como query param).
    Levanta HTTPException(401) si el token es inválido o está expirado.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        roles: List[str] = payload.get("roles", [])
        permisos: List[str] = payload.get("permisos", [])

        if user_id is None:
            raise credentials_exception

        return TokenData(id=user_id, roles=roles, permisos=permisos)

    except JWTError:
        raise credentials_exception


def get_current_user_token(token: str = Depends(oauth2_scheme)) -> TokenData:
    """
    Desencripta el token que extrajo nuestro guardia y devuelve los datos del usuario.
    Úsalo en tus rutas así: (current_user = Depends(get_current_user_token))
    """
    return decode_access_token(token)
    
    
class RoleChecker:
    """
    Filtro dinámico de seguridad. 
    Verifica si el usuario logueado posee al menos uno de los roles permitidos.
    """
    def __init__(self, roles_permitidos: list[str]):
        self.roles_permitidos = roles_permitidos

    def __call__(self, user: TokenData = Depends(get_current_user_token)):
        # Verificamos si hay alguna coincidencia entre los roles del usuario y los permitidos
        tiene_permiso = any(rol in user.roles for rol in self.roles_permitidos)
        
        if not tiene_permiso:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operación denegada. No posees los privilegios necesarios."
            )
        return user

class PermissionChecker:
    """
    Verifica que el usuario tenga al menos uno de los permisos requeridos en su token.
    Los permisos se inyectan en el JWT al momento del login desde la tabla roles_permisos.
    """
    def __init__(self, permisos_requeridos: List[str]):
        self.permisos_requeridos = permisos_requeridos

    def __call__(self, user: TokenData = Depends(get_current_user_token)) -> TokenData:
        tiene_permiso = any(p in user.permisos for p in self.permisos_requeridos)
        if not tiene_permiso:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permisos insuficientes. Se requiere alguno de: {self.permisos_requeridos}"
            )
        return user