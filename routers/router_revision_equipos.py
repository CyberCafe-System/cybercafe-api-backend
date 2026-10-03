from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from config.security_dependencia import Token_Dependencia
from config.session_dependencia import SessionDeDependencia
from models.detalle_renta import DetalleRenta, EstadoRenta
from models.equipo import Equipo, EstadoEquipo
from models.revision_equipo import (
    RevisionEquipo,
    RevisionEquipoCreate,
    RevisionEquipoUpdate,
)
from models.usuario import Usuario


ROLES_CON_PERMISO_LECTURA_REVISIONES = {1, 2, 3}
ROLES_CON_PERMISO_GESTION_REVISIONES = {1, 3}
ROLES_CON_PERMISO_ELIMINACION_REVISIONES = {1}

router = APIRouter()


def validar_permisos_lectura(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_LECTURA_REVISIONES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para consultar revisiones de equipos",
        )


def validar_permisos_gestion(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_GESTION_REVISIONES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el administrador o el asistente pueden registrar o modificar revisiones",
        )


def validar_permisos_eliminacion(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_ELIMINACION_REVISIONES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el administrador puede eliminar revisiones de equipos",
        )


def obtener_revision(
    session: SessionDeDependencia, revision_equipo_id: int
) -> RevisionEquipo:
    revision = session.get(RevisionEquipo, revision_equipo_id)
    if not revision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Revisión de equipo no encontrada",
        )
    return revision


def validar_detalle_renta(
    session: SessionDeDependencia, detalle_renta_id: int
) -> DetalleRenta:
    detalle_renta = session.get(DetalleRenta, detalle_renta_id)
    if not detalle_renta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El detalle de renta con ID {detalle_renta_id} no existe",
        )
    return detalle_renta


def validar_usuario(session: SessionDeDependencia, usuario_id: int) -> Usuario:
    usuario = session.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El usuario con ID {usuario_id} no existe",
        )
    return usuario


@router.get(
    "/revisiones",
    response_model=list[RevisionEquipo],
    status_code=status.HTTP_200_OK,
)
async def get_revisiones(
    session: SessionDeDependencia,
    token: Token_Dependencia,
    inspeccion_pasada: bool | None = Query(
        None, description="Filtrar por resultado de inspección (aprobada o reprobada)"
    ),
    usuario_id: int | None = Query(
        None, description="Filtrar por ID del usuario que realizó la inspección"
    ),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1),
):
    validar_permisos_lectura(token)
    consulta = select(RevisionEquipo)

    if inspeccion_pasada is not None:
        consulta = consulta.where(RevisionEquipo.inspeccion_pasada == inspeccion_pasada)
    if usuario_id is not None:
        consulta = consulta.where(RevisionEquipo.usuario_id == usuario_id)

    return session.exec(consulta.offset(offset).limit(limit)).all()


@router.get(
    "/revisiones/{revision_equipo_id}",
    response_model=RevisionEquipo,
    status_code=status.HTTP_200_OK,
)
async def get_revision(
    revision_equipo_id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_lectura(token)
    return obtener_revision(session, revision_equipo_id)


@router.get(
    "/revisiones/detalle-renta/{detalle_renta_id}",
    response_model=RevisionEquipo,
    status_code=status.HTTP_200_OK,
)
async def get_revision_por_detalle_renta(
    detalle_renta_id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    """Consulta la inspección técnica vinculada a una sesión específica de renta."""
    validar_permisos_lectura(token)
    validar_detalle_renta(session, detalle_renta_id)

    revision = session.exec(
        select(RevisionEquipo).where(
            RevisionEquipo.detalle_renta_id == detalle_renta_id
        )
    ).first()
    if not revision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se ha registrado ninguna revisión técnica para este detalle de renta",
        )
    return revision


@router.post(
    "/revisiones",
    response_model=RevisionEquipo,
    status_code=status.HTTP_201_CREATED,
)
async def create_revision(
    datos: RevisionEquipoCreate,
    session: SessionDeDependencia,
    token: Token_Dependencia,
    estado_si_daniado: EstadoEquipo = Query(
        EstadoEquipo.DANIOS_MENORES,
        description="Estado asignado al equipo si la inspección no pasa (por defecto Daños menores)",
    ),
):
    """Registra la inspección física pos-renta y actualiza automáticamente los estados del equipo y de la renta."""
    validar_permisos_gestion(token)

    # 1. Validar existencia del detalle de renta (FK)
    detalle_renta = validar_detalle_renta(session, datos.detalle_renta_id)

    # 2. Resolver y validar usuario inspector (FK)
    usuario_id = datos.usuario_id or token.get("id")
    validar_usuario(session, usuario_id) #type: ignore

    # 3. Comprobar si ya existe una revisión previa para este detalle_renta
    revision_existente = session.exec(
        select(RevisionEquipo).where(
            RevisionEquipo.detalle_renta_id == datos.detalle_renta_id
        )
    ).first()
    if revision_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una revisión registrada para este detalle de renta",
        )

    # 4. Obtener el equipo asociado a través del detalle de renta
    equipo = session.get(Equipo, detalle_renta.equipo_id)
    if not equipo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El equipo asociado a la renta (ID {detalle_renta.equipo_id}) no existe",
        )

    # 5. Crear el registro de revisión
    datos_dict = datos.model_dump()
    datos_dict["usuario_id"] = usuario_id
    revision = RevisionEquipo(**datos_dict)
    session.add(revision)

    # 6. Actualización sincronizada de estados de negocio
    if datos.inspeccion_pasada:
        # Si pasó la inspección, el equipo vuelve a estar disponible para nuevos clientes
        equipo.estado = EstadoEquipo.DISPONIBLE
        detalle_renta.estado = EstadoRenta.FINALIZADA
    else:
        # Si no pasó, el equipo se marca con daños y queda bloqueado para renta
        equipo.estado = estado_si_daniado
        detalle_renta.estado = EstadoRenta.FINALIZADA

    session.add(equipo)
    session.add(detalle_renta)

    session.commit()
    session.refresh(revision)
    return revision


@router.put(
    "/revisiones/{revision_equipo_id}",
    response_model=RevisionEquipo,
    status_code=status.HTTP_200_OK,
)
async def update_revision(
    revision_equipo_id: int,
    datos: RevisionEquipoUpdate,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_gestion(token)
    revision = obtener_revision(session, revision_equipo_id)

    for campo, valor in datos.model_dump(exclude_unset=True).items():
        if valor is not None:
            setattr(revision, campo, valor)

    session.add(revision)
    session.commit()
    session.refresh(revision)
    return revision


@router.delete(
    "/revisiones/{revision_equipo_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_revision(
    revision_equipo_id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_eliminacion(token)
    revision = obtener_revision(session, revision_equipo_id)

    session.delete(revision)
    session.commit()
    return {
        "message": "Revisión técnica eliminada exitosamente",
        "revision_equipo_id": revision_equipo_id,
    }
