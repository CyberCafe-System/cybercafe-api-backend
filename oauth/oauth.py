from datetime import datetime, timezone
from fastapi import APIRouter, status, HTTPException
from config.session_dependencia import SessionDeDependencia
from sqlmodel import select
from models.usuario import Usuario
from librerias.pwd import verify_password
from config.security import create_access_token
from config.security_dependencia import OAuth2FormDeDependencia

router = APIRouter()


@router.post("/oauth/login", status_code=status.HTTP_200_OK)
async def login(form_data: OAuth2FormDeDependencia, session: SessionDeDependencia):
    username = form_data.username

    consulta = select(Usuario).where(Usuario.username == username)
    usuario = session.exec(consulta).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="username o password incorrectos",
        )

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario se encuentra inactivo",
        )

    # verifica que la contraseña ingresada por el usuario sea correcta
    if not verify_password(form_data.password, usuario.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="username o password incorrectos",
        )

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