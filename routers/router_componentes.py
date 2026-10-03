from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from config.security_dependencia import Token_Dependencia
from config.session_dependencia import SessionDeDependencia
from models.componente import (
    Componente,
    ComponenteCreate,
    ComponenteUpdate,
    EstadoComponente,
    TipoComponente,
)
from models.equipo import Equipo


ROLES_CON_PERMISO_LECTURA_COMPONENTES = {1, 2, 3}
ROLES_CON_PERMISO_GESTION_COMPONENTES = {1, 3}
ROLES_CON_PERMISO_ELIMINACION_COMPONENTES = {1}

router = APIRouter()


def validar_permisos_lectura(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_LECTURA_COMPONENTES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para consultar componentes",
        )


def validar_permisos_gestion(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_GESTION_COMPONENTES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el administrador o el asistente pueden gestionar componentes",
        )


def validar_permisos_eliminacion(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_ELIMINACION_COMPONENTES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el administrador puede eliminar componentes",
        )


def obtener_componente(session: SessionDeDependencia, componente_id: int) -> Componente:
    componente = session.get(Componente, componente_id)
    if not componente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Componente no encontrado",
        )
    return componente


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
        consulta = consulta.where(Componente.equipo_id.is_(None))
    if tipo is not None:
        consulta = consulta.where(Componente.tipo == tipo)
    if estado is not None:
        consulta = consulta.where(Componente.estado == estado)
    if activo is not None:
        consulta = consulta.where(Componente.activo == activo)

    return session.exec(consulta.offset(offset).limit(limit)).all()


@router.get(
    "/componentes/{componente_id}",
    response_model=Componente,
    status_code=status.HTTP_200_OK,
)
async def get_componente(
    componente_id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_lectura(token)
    return obtener_componente(session, componente_id)


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


@router.post(
    "/componentes",
    response_model=Componente,
    status_code=status.HTTP_201_CREATED,
)
async def create_componente(
    datos: ComponenteCreate,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_gestion(token)
    validar_equipo(session, datos.equipo_id)

    componente = Componente(**datos.model_dump())
    session.add(componente)
    session.commit()
    session.refresh(componente)
    return componente


@router.put(
    "/componentes/{componente_id}",
    response_model=Componente,
    status_code=status.HTTP_200_OK,
)
async def update_componente(
    componente_id: int,
    datos: ComponenteUpdate,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_gestion(token)
    componente = obtener_componente(session, componente_id)
    validar_equipo(session, datos.equipo_id)

    for campo, valor in datos.model_dump().items():
        setattr(componente, campo, valor)

    session.add(componente)
    session.commit()
    session.refresh(componente)
    return componente


@router.patch(
    "/componentes/{componente_id}/asignar",
    response_model=Componente,
    status_code=status.HTTP_200_OK,
)
async def asignar_componente(
    componente_id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
    nuevo_equipo_id: int | None = Query(None, description="ID del equipo a asignar, o null para desvincular"),
):
    """Asigna o desvincula un componente a un equipo determinado."""
    validar_permisos_gestion(token)
    componente = obtener_componente(session, componente_id)
    validar_equipo(session, nuevo_equipo_id)

    componente.equipo_id = nuevo_equipo_id
    session.add(componente)
    session.commit()
    session.refresh(componente)
    return componente


@router.patch(
    "/componentes/{componente_id}/estado",
    response_model=Componente,
    status_code=status.HTTP_200_OK,
)
async def cambiar_estado_componente(
    componente_id: int,
    nuevo_estado: EstadoComponente,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    """Permite al asistente o admin actualizar rápidamente el estado de salud de un componente."""
    validar_permisos_gestion(token)
    componente = obtener_componente(session, componente_id)

    componente.estado = nuevo_estado
    session.add(componente)
    session.commit()
    session.refresh(componente)
    return componente


@router.delete(
    "/componentes/{componente_id}",
    response_model=Componente,
    status_code=status.HTTP_200_OK,
)
async def eliminar_componente(
    componente_id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    """Realiza un borrado lógico desactivando el componente."""
    validar_permisos_eliminacion(token)
    componente = obtener_componente(session, componente_id)

    componente.activo = False
    session.add(componente)
    session.commit()
    session.refresh(componente)
    return componente
