from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import select

from config.security_dependencia import Token_Dependencia
from config.session_dependencia import SessionDeDependencia
from config.security import get_current_user
from models.equipo import Equipo, EquipoCreate, EquipoUpdate


ROLES_CON_PERMISO_GESTION_EQUIPOS = {1}

router = APIRouter(dependencies=[Depends(get_current_user)])


def validar_permisos_gestion(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_GESTION_EQUIPOS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para modificar equipos",
        )


def obtener_equipo(session: SessionDeDependencia, equipo_id: int) -> Equipo:
    equipo = session.get(Equipo, equipo_id)
    if not equipo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipo no encontrado",
        )
    return equipo


def validar_datos_parciales(datos: EquipoUpdate) -> None:
    datos_actualizados = datos.model_dump(exclude_unset=True)
    campos_no_nulos = {"nombre", "tarifa_por_hora", "tipo", "estado"}
    if any(
        campo in campos_no_nulos and valor is None
        for campo, valor in datos_actualizados.items()
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Los campos requeridos del equipo no pueden ser nulos",
        )


@router.get(
    "/equipos",
    response_model=list[Equipo],
    status_code=status.HTTP_200_OK,
)
async def get_equipos(
    session: SessionDeDependencia,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1),
):
    return session.exec(select(Equipo).offset(offset).limit(limit)).all()


@router.get(
    "/equipos/{equipo_id}",
    response_model=Equipo,
    status_code=status.HTTP_200_OK,
)
async def get_equipo(
    equipo_id: int,
    session: SessionDeDependencia,
):
    return obtener_equipo(session, equipo_id)


@router.post(
    "/equipos",
    response_model=Equipo,
    status_code=status.HTTP_201_CREATED,
)
async def create_equipo(
    datos: EquipoCreate,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_gestion(token)
    equipo = Equipo(**datos.model_dump())
    session.add(equipo)
    session.commit()
    session.refresh(equipo)
    return equipo


@router.put(
    "/equipos/{equipo_id}",
    response_model=Equipo,
    status_code=status.HTTP_200_OK,
)
async def update_equipo(
    equipo_id: int,
    datos: EquipoCreate,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_gestion(token)
    equipo = obtener_equipo(session, equipo_id)

    for campo, valor in datos.model_dump().items():
        setattr(equipo, campo, valor)

    session.add(equipo)
    session.commit()
    session.refresh(equipo)
    return equipo


@router.patch(
    "/equipos/{equipo_id}",
    response_model=Equipo,
    status_code=status.HTTP_200_OK,
)
async def patch_equipo(
    equipo_id: int,
    datos: EquipoUpdate,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_gestion(token)
    equipo = obtener_equipo(session, equipo_id)
    datos_actualizados = datos.model_dump(exclude_unset=True)
    validar_datos_parciales(datos)

    for campo, valor in datos_actualizados.items():
        setattr(equipo, campo, valor)

    session.add(equipo)
    session.commit()
    session.refresh(equipo)
    return equipo

