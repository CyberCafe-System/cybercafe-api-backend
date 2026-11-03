from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from config.security_dependencia import (
    Asistente_Token_Dependencia,
    Token_Dependencia,
)
from config.session_dependencia import SessionDeDependencia
from models.componente import Componente, EstadoComponente
from models.detalle_renta import DetalleRenta, EstadoRenta
from models.equipo import Equipo, EstadoEquipo
from models.revision_equipo import (
    RevisionEquipo,
    RevisionEquipoCreate,
    RevisionEquipoResponse,
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


def obtener_nombre_usuario(usuario: Usuario | None) -> str | None:
    if not usuario:
        return None

    nombre = (usuario.nombre or "").strip()
    if nombre:
        return nombre

    username = (usuario.username or "").strip()
    return username or None


def construir_respuesta_revision(
    revision: RevisionEquipo, usuario: Usuario | None
) -> RevisionEquipoResponse:
    return RevisionEquipoResponse(
        **revision.model_dump(),
        usuario_nombre=obtener_nombre_usuario(usuario),
    )


@router.get(
    "/revisiones",
    response_model=list[RevisionEquipoResponse],
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

    revisiones = session.exec(consulta.offset(offset).limit(limit)).all()
    if not revisiones:
        return []

    usuario_ids = {revision.usuario_id for revision in revisiones}
    usuarios = session.exec(
        select(Usuario).where(Usuario.usuario_id.in_(usuario_ids))
    ).all()
    usuarios_por_id = {usuario.usuario_id: usuario for usuario in usuarios}

    return [
        construir_respuesta_revision(
            revision, usuarios_por_id.get(revision.usuario_id)
        )
        for revision in revisiones
    ]


@router.get(
    "/revisiones/{revision_equipo_id}",
    response_model=RevisionEquipoResponse,
    status_code=status.HTTP_200_OK,
)
async def get_revision(
    revision_equipo_id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_lectura(token)
    revision = obtener_revision(session, revision_equipo_id)
    usuario = session.get(Usuario, revision.usuario_id)
    return construir_respuesta_revision(revision, usuario)


@router.get(
    "/revisiones/detalle-renta/{detalle_renta_id}",
    response_model=RevisionEquipoResponse,
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

    usuario = session.get(Usuario, revision.usuario_id)
    return construir_respuesta_revision(revision, usuario)


@router.post(
    "/revisiones",
    response_model=RevisionEquipoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_revision(
    datos: RevisionEquipoCreate,
    session: SessionDeDependencia,
    token: Asistente_Token_Dependencia,
    estado_si_daniado: EstadoEquipo = Query(
        EstadoEquipo.DANIOS_MENORES,
        description="Estado asignado al equipo si la inspección no pasa (por defecto Daños menores)",
    ),
):
    """
    Registra la inspección física pos-renta y actualiza de forma atómica los
    estados del equipo y de la sesión de renta.

    Regla de negocio: solo se puede inspeccionar un detalle de renta que esté en
    estado 'Pendiente Revision' (es decir, una sesión ya finalizada por el cajero
    que espera la verificación del asistente). Una renta todavía 'Activa' o ya
    'Finalizada' no puede revisarse.

    La dependencia `Asistente_Token_Dependencia` garantiza que solo el Asistente
    (rol_id = 3) o el Administrador (rol_id = 1) ejecuten esta operación.
    """

    # 1. Validar existencia del detalle de renta (FK)
    detalle_renta = validar_detalle_renta(session, datos.detalle_renta_id)

    # 1.1 Regla de negocio: la renta debe estar Pendiente Revision para poder revisarse
    if detalle_renta.estado != EstadoRenta.PENDIENTE_REVISION:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "La renta debe estar en estado 'Pendiente Revision' para poder "
                f"revisarse. Estado actual: {detalle_renta.estado.value}"
            ),
        )

    # 2. Resolver y validar usuario inspector (FK)
    # El asistente no puede atribuir la revisión a otro usuario; el administrador
    # conserva la capacidad de indicar explícitamente al inspector.
    if token.get("id_rol") == 3:
        usuario_id = token.get("id")
    else:
        usuario_id = datos.usuario_id or token.get("id")

    if usuario_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se pudo identificar al usuario autenticado",
        )

    usuario_id = int(usuario_id)
    usuario = validar_usuario(session, usuario_id)

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
    componentes_input = datos.componentes_afectados
    datos_dict = datos.model_dump(exclude={"componentes_afectados"})
    datos_dict["usuario_id"] = usuario_id
    revision = RevisionEquipo(**datos_dict)
    session.add(revision)
    session.flush()  # Genera revision.revision_equipo_id de inmediato

    # 6. Actualización sincronizada de estados de negocio
    if datos.inspeccion_pasada:
        # Si pasó la inspección, el equipo vuelve a estar disponible para nuevos clientes
        equipo.estado = EstadoEquipo.DISPONIBLE
        detalle_renta.estado = EstadoRenta.FINALIZADA
    else:
        # Si no pasó, el equipo se marca con daños y queda bloqueado para renta
        equipo.estado = estado_si_daniado
        detalle_renta.estado = EstadoRenta.FINALIZADA

        # Formatear y actualizar revisiones en componentes afectados de forma acumulativa
        if componentes_input:
            fecha_str = (revision.fecha_revision or datetime.now()).strftime("%d/%m/%Y %H:%M")
            for item in componentes_input:
                comp_obj = None
                if item.componente_id:
                    comp_obj = session.get(Componente, item.componente_id)
                elif item.nombre:
                    comp_obj = session.exec(
                        select(Componente).where(
                            Componente.equipo_id == equipo.equipo_id,
                            Componente.nombre == item.nombre,
                        )
                    ).first()

                if comp_obj:
                    if item.estado:
                        try:
                            comp_obj.estado = EstadoComponente(item.estado)
                        except Exception:
                            comp_obj.estado = EstadoComponente.DANIOS_MENORES
                    else:
                        comp_obj.estado = EstadoComponente.DANIOS_MENORES

                    estado_label = comp_obj.estado.value if hasattr(comp_obj.estado, "value") else str(comp_obj.estado)
                    detalle_falla = item.descripcion_danio or datos.observaciones or "Reportado con novedades en inspección técnica"
                    bloque_historial = (
                        f"[REVISIÓN: #{revision.revision_equipo_id} | FECHA: {fecha_str}]\n"
                        f"Descripción: {detalle_falla}\n"
                        f"--------------------------------------------------"
                    )
                    if comp_obj.observaciones:
                        comp_obj.observaciones = f"{bloque_historial}\n{comp_obj.observaciones}"
                    else:
                        comp_obj.observaciones = bloque_historial
                    session.add(comp_obj)

    session.add(equipo)
    session.add(detalle_renta)

    # 7. Confirmación transaccional atómica.
    # Las tres entidades (revision, equipo, detalle_renta) pertenecen a la MISMA
    # sesión de base de datos (`SessionDeDependencia`) y sólo se persisten juntas
    # al ejecutar un único `commit()`. Si cualquier escritura falla, se revierte
    # TODO con `rollback()`, evitando estados inconsistentes (p. ej. una revisión
    # registrada sin que el equipo haya cambiado de estado).
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo registrar la revisión; la transacción fue revertida",
        )

    session.refresh(revision)
    return construir_respuesta_revision(revision, usuario)


@router.put(
    "/revisiones/{revision_equipo_id}",
    response_model=RevisionEquipoResponse,
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
    usuario = session.get(Usuario, revision.usuario_id)
    return construir_respuesta_revision(revision, usuario)


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
