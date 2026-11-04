from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from config.security_dependencia import Token_Dependencia
from config.session_dependencia import SessionDeDependencia
from models.componente import (
    Componente,
    EstadoComponente,
    TipoComponente,
)
from models.equipo import Equipo


ROLES_CON_PERMISO_LECTURA_COMPONENTES = {1, 2, 3}

router = APIRouter()


def validar_permisos_lectura(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_LECTURA_COMPONENTES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para consultar componentes",
        )


def validar_equipo(session: SessionDeDependencia, equipo_id: int | None) -> None:
    """Valida la existencia del equipo si se proporciona una llave foránea."""
    if equipo_id is not None:
        equipo = session.get(Equipo, equipo_id)
        if not equipo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El equipo con ID {equipo_id} no existe",
            )


@router.get(
    "/componentes",
    response_model=list[Componente],
    status_code=status.HTTP_200_OK,
)
async def get_componentes(
    session: SessionDeDependencia,
    token: Token_Dependencia,
    equipo_id: int | None = Query(None, description="Filtrar por equipo asignado"),
    tipo: TipoComponente | None = Query(None, description="Filtrar por tipo de componente"),
    estado: EstadoComponente | None = Query(None, description="Filtrar por estado del componente"),
    activo: bool | None = Query(None, description="Filtrar por estado activo/inactivo"),
    sin_equipo: bool | None = Query(None, description="Filtrar componentes en bodega/sin asignar"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1),
):
    validar_permisos_lectura(token)
    consulta = select(Componente)

    if equipo_id is not None:
        consulta = consulta.where(Componente.equipo_id == equipo_id)
    if sin_equipo is True:
        consulta = consulta.where(Componente.equipo_id.is_(None)) #type: ignore
    if tipo is not None:
        consulta = consulta.where(Componente.tipo == tipo)
    if estado is not None:
        consulta = consulta.where(Componente.estado == estado)
    if activo is not None:
        consulta = consulta.where(Componente.activo == activo)

    return session.exec(consulta.offset(offset).limit(limit)).all()


@router.get(
    "/equipos/{equipo_id}/componentes",
    response_model=list[Componente],
    status_code=status.HTTP_200_OK,
)
async def get_componentes_por_equipo(
    equipo_id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    """Retorna todos los componentes activos instalados en un equipo específico."""
    validar_permisos_lectura(token)
    validar_equipo(session, equipo_id)
    consulta = (
        select(Componente)
        .where(Componente.equipo_id == equipo_id, Componente.activo == True)
    )
    return session.exec(consulta).all()
