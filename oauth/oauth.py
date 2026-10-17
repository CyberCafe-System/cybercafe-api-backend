from datetime import datetime, timezone
from fastapi import APIRouter, Request, status, HTTPException
from config.session_dependencia import SessionDeDependencia
from sqlmodel import select
from models.usuario import Usuario
from librerias.pwd import verify_password
from librerias.rate_limiter import login_rate_limiter
from config.security import create_access_token
from config.security_dependencia import OAuth2FormDeDependencia

router = APIRouter()


@router.post("/oauth/login", status_code=status.HTTP_200_OK)
async def login(
    request: Request,
    form_data: OAuth2FormDeDependencia,
    session: SessionDeDependencia,
):
    username = form_data.username
    client_key = login_rate_limiter.get_client_key(request, username)

    # 1. Comprobar si el usuario/IP se encuentra en período de bloqueo
    is_locked, remaining = login_rate_limiter.is_locked(client_key)
    if is_locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Demasiados intentos fallidos. Por favor, espere {remaining} segundos antes de volver a intentarlo.",
            headers={"Retry-After": str(remaining)},
        )

    # Función auxiliar para registrar intento fallido y responder acordemente
    def _fallo_autenticacion(detail: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        _, is_now_locked, wait_seconds = login_rate_limiter.record_failure(client_key)
        if is_now_locked:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Ha superado el límite de {login_rate_limiter.max_attempts} intentos fallidos. Debe esperar {wait_seconds} segundos para volver a intentarlo.",
                headers={"Retry-After": str(wait_seconds)},
            )
        raise HTTPException(
            status_code=status_code,
            detail=detail,
        )

    # 2. Búsqueda del usuario en la base de datos
    consulta = select(Usuario).where(Usuario.username == username)
    usuario = session.exec(consulta).first()

    if not usuario:
        _fallo_autenticacion("username o password incorrectos", status.HTTP_401_UNAUTHORIZED)

    if not usuario.activo:
        _fallo_autenticacion("El usuario se encuentra inactivo. Comuníquese con el administrador.", status.HTTP_403_FORBIDDEN)

    # 3. Verifica que la contraseña ingresada por el usuario sea correcta
    if not verify_password(form_data.password, usuario.password):
        _fallo_autenticacion("username o password incorrectos", status.HTTP_401_UNAUTHORIZED)

    # 4. Credenciales válidas: reiniciar contador de fallos
    login_rate_limiter.record_success(client_key)

    # Actualiza last_login al momento actual
    usuario.last_login = datetime.now(timezone.utc)
    session.add(usuario)
    session.commit()
    session.refresh(usuario)

    token = create_access_token(
        data={
            "id": usuario.usuario_id,
            "username": usuario.username,
            "id_rol": usuario.rol_id,
            "is_superuser": usuario.is_superuser,
        }
    )
    return {"access_token": token, "token_type": "bearer"}