from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select
from config.session_dependencia import SessionDeDependencia
from config.security_dependencia import Token_Dependencia
from models.usuario import Usuario


def validar_administrador(token: dict) -> None:
    if token.get("id_rol") != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el administrador puede acceder o modificar usuarios",
        )


router = APIRouter()

# Listar usuarios


@router.get(
    "/usuarios",
    response_model=list[Usuario],
    response_model_exclude={"password"},
    status_code=status.HTTP_200_OK,
)
async def get_usuarios(
    session: SessionDeDependencia,
    token: Token_Dependencia,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1),
):
    validar_administrador(token)
    return session.exec(select(Usuario).offset(offset).limit(limit)).all()


# Obtener el usuario autenticado (cualquier rol)
@router.get(
    "/usuarios/me",
    response_model=Usuario,
    response_model_exclude={"password"},
    status_code=status.HTTP_200_OK,
)
async def get_mi_usuario(
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    usuario_id = token.get("id")
    if usuario_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
        )

    usuario = session.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario
