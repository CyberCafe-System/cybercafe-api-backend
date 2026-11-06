from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from config.security_dependencia import (
    Asistente_Token_Dependencia,
    Token_Dependencia,
)
from config.session_dependencia import SessionDeDependencia
from models.componente import Componente, EstadoComponente
from models.revision_componente import RevisionComponente
from models.detalle_renta import DetalleRenta, EstadoRenta
from models.equipo import Equipo, EstadoEquipo
from models.revision_equipo import (
    RevisionEquipo,
    RevisionEquipoCreate,
    RevisionEquipoResponse,
)
from models.usuario import Usuario


ROLES_CON_PERMISO_LECTURA_REVISIONES = {1, 2, 3}

router = APIRouter()


def validar_permisos_lectura(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_LECTURA_REVISIONES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para consultar revisiones de equipos",
        )


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
    limit: int = Query(20, ge=1, le=100),
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
    """
    # 1. Validar existencia del detalle de renta (FK)
    detalle_renta = validar_detalle_renta(session, datos.detalle_renta_id)

    # 1.1 Regla de negocio: la renta debe estar Pendiente Revision (o TIEMPO_TERMINADO) para poder revisarse
    if detalle_renta.estado not in (EstadoRenta.PENDIENTE_REVISION, EstadoRenta.TIEMPO_TERMINADO):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "La renta debe estar en estado 'Pendiente Revision' para poder "
                f"revisarse. Estado actual: {detalle_renta.estado.value}"
            ),
        )

    # 2. Resolver y validar usuario inspector (FK)
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
    session.flush()

    # 6. Actualización sincronizada de estados de negocio
    detalle_renta.estado = EstadoRenta.FINALIZADA
    if not detalle_renta.hora_fin:
        detalle_renta.hora_fin = datetime.now(timezone.utc)

    if not datos.inspeccion_pasada:
        equipo.estado = estado_si_daniado

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
                    estado_previo_str = comp_obj.estado.value if hasattr(comp_obj.estado, "value") else str(comp_obj.estado)
                    if item.estado:
                        try:
                            comp_obj.estado = EstadoComponente(item.estado)
                        except Exception:
                            comp_obj.estado = EstadoComponente.DANIOS_MENORES
                    else:
                        comp_obj.estado = EstadoComponente.DANIOS_MENORES

                    estado_nuevo_str = comp_obj.estado.value if hasattr(comp_obj.estado, "value") else str(comp_obj.estado)
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

                    # Guardar en tabla relacional revision_componentes
                    if comp_obj.componente_id is not None and revision.revision_equipo_id is not None:
                        rev_comp = RevisionComponente(
                            revision_equipo_id=revision.revision_equipo_id,
                            componente_id=comp_obj.componente_id,
                            estado_previo=estado_previo_str,
                            estado_nuevo=estado_nuevo_str,
                            descripcion=detalle_falla,
                        )
                        session.add(rev_comp)
    else:
        # Si pasó la inspección, verificar que no tenga ningún componente activo dañado o en reemplazo
        comp_danados = session.exec(
            select(Componente).where(
                Componente.equipo_id == equipo.equipo_id,
                Componente.activo == True,  # type: ignore
                Componente.estado.in_([EstadoComponente.DANIOS_MENORES, EstadoComponente.REQUIERE_REEMPLAZO]),  # type: ignore
            )
        ).all()
        if comp_danados:
            # Tiene componentes con novedad, no puede quedar DISPONIBLE automáticamente
            equipo.estado = EstadoEquipo.DANIOS_MENORES
        else:
            equipo.estado = EstadoEquipo.DISPONIBLE

    session.add(equipo)
    session.add(detalle_renta)

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
