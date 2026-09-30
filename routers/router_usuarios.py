from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select
from config.session_dependencia import SessionDeDependencia
from config.security_dependencia import Token_Dependencia
from librerias.pwd import get_password_hash
from models.usuario import Usuario, UsuarioCreate, UsuarioUpdate
from models.rol import Rol


def validar_administrador(token: dict) -> None:
    if token.get("id_rol") != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el administrador puede acceder o modificar usuarios",
        )


def validar_rol(session: SessionDeDependencia, id_rol: int) -> None:
    if not session.get(Rol, id_rol):
        raise HTTPException(status_code=404, detail="Rol no encontrado")


router = APIRouter()

# Listar usuarios


@router.get(
    "/usuarios",
    response_model=list[Usuario],
    response_model_exclude={"password_hash"},
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


# Buscar usuario por id
@router.get(
    "/usuarios/{id}",
    response_model=Usuario,
    response_model_exclude={"password_hash"},
    status_code=status.HTTP_200_OK,
)
async def get_usuario(id: int, session: SessionDeDependencia, token: Token_Dependencia):
    validar_administrador(token)
    usuario = session.get(Usuario, id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario


# Crear usuario
@router.post(
    "/usuarios",
    response_model=Usuario,
    response_model_exclude={"password_hash"},
    status_code=status.HTTP_201_CREATED,
)
async def create_usuario(
    datos: UsuarioCreate,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_administrador(token)
    if session.exec(select(Usuario).where(Usuario.username == datos.username)).first():
        raise HTTPException(
            status_code=400, detail="El usuario ya esta en uso")

    validar_rol(session, datos.rol_id)
    usuario = Usuario(**datos.model_dump())
    usuario.password_hash = get_password_hash(datos.password_hash)
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario


# Actualizar usuario
@router.put(
    "/usuarios/{id}",
    response_model=Usuario,
    response_model_exclude={"password_hash"},
    status_code=status.HTTP_200_OK,
)
async def update_usuario(
    id: int,
    datos: UsuarioUpdate,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_administrador(token)
    usuario = session.get(Usuario, id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if token.get("id") == id and not datos.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes desactivar tu propio usuario",
        )

    if session.exec(
        select(Usuario).where(Usuario.username ==
                              datos.username, Usuario.usuario_id != id)
    ).first():
        raise HTTPException(
            status_code=400, detail="El usuario ya esta en uso")

    validar_rol(session, datos.rol_id)
    datos_actualizados = datos.model_dump()
    datos_actualizados["password_hash"] = get_password_hash(
        datos.password_hash)
    for campo, valor in datos_actualizados.items():
        setattr(usuario, campo, valor)

    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario


# Desactivar usuario
@router.patch(
    "/usuarios/{id}/desactivar",
    response_model=Usuario,
    response_model_exclude={"password_hash"},
    status_code=status.HTTP_200_OK,
)
async def desactivar_usuario(
    id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_administrador(token)
    if token.get("id") == id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes desactivar tu propio usuario",
        )

    usuario = session.get(Usuario, id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    usuario.activo = False
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario
