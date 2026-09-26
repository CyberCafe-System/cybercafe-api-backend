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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="username o password incorrectos")
        
    # verifica que la contraseña ingresada por el usuario sea correcta
    # comparándola con la contraseña almacenada en la base de datos
    if not verify_password(form_data.password, usuario.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="username o password incorrectos")
        
    token = create_access_token(
        data={"id": usuario.usuario_id, "username": usuario.username, 'id_rol': usuario.rol_id})
    # retorna el access token y el tipo de token (bearer) en formato JSON esto es un estandar
    # e seguridad para la autenticacion de usuarios siempre se debe retornar de esta manera
    return {"access_token": token, "token_type": "bearer"}