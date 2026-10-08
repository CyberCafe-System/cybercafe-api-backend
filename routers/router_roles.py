from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from config.security_dependencia import Token_Dependencia
from config.session_dependencia import SessionDeDependencia
from models.rol import Rol, RolCreate, RolUpdate


ROLES_CON_PERMISO_LECTURA_ROLES = {1, 2, 3}
ROLES_CON_PERMISO_GESTION_ROLES = {1}

router = APIRouter()


def validar_permisos_lectura(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_LECTURA_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para consultar roles",
        )


def validar_permisos_gestion(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_GESTION_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el administrador puede gestionar roles",
        )


def obtener_rol(session: SessionDeDependencia, rol_id: int) -> Rol:
    rol = session.get(Rol, rol_id)
    if not rol:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado",
        )
    return rol


def validar_nombre_unico(
    session: SessionDeDependencia,
    nombre: str,
    rol_id: int | None = None,
) -> None:
    consulta = select(Rol).where(Rol.nombre == nombre)
    if rol_id is not None:
        consulta = consulta.where(Rol.rol_id != rol_id)
    if session.exec(consulta).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un rol con ese nombre",
        )


@router.get(
    "/roles",
    response_model=list[Rol],
    status_code=status.HTTP_200_OK,
)
async def get_roles(
    session: SessionDeDependencia,
    token: Token_Dependencia,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1),
):
    validar_permisos_lectura(token)
    return session.exec(select(Rol).offset(offset).limit(limit)).all()


@router.get(
    "/roles/{rol_id}",
    response_model=Rol,
    status_code=status.HTTP_200_OK,
)
async def get_rol(
    rol_id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_lectura(token)
    return obtener_rol(session, rol_id)


@router.post(
    "/roles",
    response_model=Rol,
    status_code=status.HTTP_201_CREATED,
)
async def create_rol(
    datos: RolCreate,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_gestion(token)
    validar_nombre_unico(session, datos.nombre)
    rol = Rol(**datos.model_dump())
    session.add(rol)
    session.commit()
    session.refresh(rol)
    return rol


@router.put(
    "/roles/{rol_id}",
    response_model=Rol,
    status_code=status.HTTP_200_OK,
)
async def update_rol(
    rol_id: int,
    datos: RolUpdate,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_gestion(token)
    rol = obtener_rol(session, rol_id)
    validar_nombre_unico(session, datos.nombre, rol_id)

    for campo, valor in datos.model_dump().items():
        setattr(rol, campo, valor)

    session.add(rol)
    session.commit()
    session.refresh(rol)
    return rol
