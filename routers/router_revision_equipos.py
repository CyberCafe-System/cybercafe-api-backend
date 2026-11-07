from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from config.paginacion import paginar_consulta
from config.security_dependencia import (
    Asistente_Token_Dependencia,
    Token_Dependencia,
)
from config.session_dependencia import SessionDeDependencia
from models.auditoria import Auditoria
from models.cliente import Cliente
from models.componente import Componente, EstadoComponente
from models.detalle_renta import DetalleRenta, EstadoRenta
from models.equipo import Equipo, EstadoEquipo
from models.renta import Renta
from models.revision_componente import RevisionComponente
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


def validar_detalle_renta_bloqueado(
    session: SessionDeDependencia, detalle_renta_id: int
) -> DetalleRenta:
    detalle_renta = session.exec(
        select(DetalleRenta)
        .where(DetalleRenta.detalle_renta_id == detalle_renta_id)
        .with_for_update()
    ).first()
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
    revision: RevisionEquipo,
    usuario: Usuario | None,
    equipo: Equipo | None = None,
    cliente_nombre: str | None = None,
) -> RevisionEquipoResponse:
    tipo_str = None
    if equipo is not None:
        tipo_str = equipo.tipo.value if hasattr(equipo.tipo, "value") else str(equipo.tipo)
    return RevisionEquipoResponse(
        **revision.model_dump(),
        usuario_nombre=obtener_nombre_usuario(usuario),
        equipo_id=equipo.equipo_id if equipo else None,
        equipo_nombre=equipo.nombre if equipo else None,
        equipo_tipo=tipo_str,
        cliente_nombre=cliente_nombre,
    )


@router.get(
    "/revisiones",
    response_model=list[RevisionEquipoResponse],
    status_code=status.HTTP_200_OK,
)
def get_revisiones(
    response: Response,
    session: SessionDeDependencia,
    token: Token_Dependencia,
    inspeccion_pasada: bool | None = Query(
        None, description="Filtrar por resultado de inspección (aprobada o reprobada)"
    ),
    usuario_id: int | None = Query(
        None, description="Filtrar por ID del usuario que realizó la inspección"
    ),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=500),
):
    validar_permisos_lectura(token)
    consulta = select(RevisionEquipo)

    if inspeccion_pasada is not None:
        consulta = consulta.where(RevisionEquipo.inspeccion_pasada == inspeccion_pasada)
    if usuario_id is not None:
        consulta = consulta.where(RevisionEquipo.usuario_id == usuario_id)

    revisiones = paginar_consulta(
        session=session,
        response=response,
        consulta=consulta,
        columna_orden=(
            RevisionEquipo.fecha_revision.desc(),  # type: ignore
            RevisionEquipo.revision_equipo_id.desc(),  # type: ignore
        ),
        offset=offset,
        limit=limit,
    )
    if not revisiones:
        return []

    usuario_ids = {r.usuario_id for r in revisiones if r.usuario_id is not None}
    usuarios_por_id: dict[int, Usuario] = {}
    if usuario_ids:
        usuarios = session.exec(
            select(Usuario).where(Usuario.usuario_id.in_(usuario_ids))  # type: ignore
        ).all()
        usuarios_por_id = {u.usuario_id: u for u in usuarios if u.usuario_id is not None}

    detalle_ids = {r.detalle_renta_id for r in revisiones if r.detalle_renta_id is not None}
    detalles_por_id: dict[int, DetalleRenta] = {}
    if detalle_ids:
        detalles = session.exec(
            select(DetalleRenta).where(DetalleRenta.detalle_renta_id.in_(detalle_ids))  # type: ignore
        ).all()
        detalles_por_id = {
            d.detalle_renta_id: d for d in detalles if d.detalle_renta_id is not None
        }

    equipo_ids = {d.equipo_id for d in detalles_por_id.values() if d.equipo_id is not None}
    equipos_por_id: dict[int, Equipo] = {}
    if equipo_ids:
        equipos = session.exec(
            select(Equipo).where(Equipo.equipo_id.in_(equipo_ids))  # type: ignore
        ).all()
        equipos_por_id = {e.equipo_id: e for e in equipos if e.equipo_id is not None}

    renta_ids = {d.renta_id for d in detalles_por_id.values() if d.renta_id is not None}
    rentas_por_id: dict[int, Renta] = {}
    if renta_ids:
        rentas = session.exec(
            select(Renta).where(Renta.renta_id.in_(renta_ids))  # type: ignore
        ).all()
        rentas_por_id = {r.renta_id: r for r in rentas if r.renta_id is not None}

    cliente_ids = {r.cliente_id for r in rentas_por_id.values() if r.cliente_id is not None}
    clientes_por_id: dict[int, Cliente] = {}
    if cliente_ids:
        clientes = session.exec(
            select(Cliente).where(Cliente.cliente_id.in_(cliente_ids))  # type: ignore
        ).all()
        clientes_por_id = {c.cliente_id: c for c in clientes if c.cliente_id is not None}

    respuestas: list[RevisionEquipoResponse] = []
    for revision in revisiones:
        detalle = detalles_por_id.get(revision.detalle_renta_id)
        equipo = equipos_por_id.get(detalle.equipo_id) if detalle else None
        renta = rentas_por_id.get(detalle.renta_id) if detalle else None
        cliente = clientes_por_id.get(renta.cliente_id) if renta else None
        cliente_nombre = (
            f"{cliente.nombre} {cliente.apellido}".strip() if cliente else None
        )
        respuestas.append(
            construir_respuesta_revision(
                revision,
                usuarios_por_id.get(revision.usuario_id),
                equipo=equipo,
                cliente_nombre=cliente_nombre,
            )
        )
    return respuestas


@router.post(
    "/revisiones",
    response_model=RevisionEquipoResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_revision(
    request: Request,
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
    estados del equipo, componentes y de la sesión de renta.
    """
    # 1. Validar y bloquear el detalle de renta (FK)
    detalle_renta = validar_detalle_renta_bloqueado(session, datos.detalle_renta_id)

    # 1.1 Regla de negocio: la renta debe haber sido enviada primero a PENDIENTE_REVISION desde recepción/web
    if detalle_renta.estado != EstadoRenta.PENDIENTE_REVISION:
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

    # 3. Comprobar bajo el lock si ya existe una revisión previa para este detalle_renta
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

    # 4. Obtener y bloquear el equipo asociado a través del detalle de renta
    equipo = session.exec(
        select(Equipo)
        .where(Equipo.equipo_id == detalle_renta.equipo_id)
        .with_for_update()
    ).first()
    if not equipo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El equipo asociado a la renta (ID {detalle_renta.equipo_id}) no existe",
        )

    estado_equipo_previo = equipo.estado.value if hasattr(equipo.estado, "value") else str(equipo.estado)

    # 5. Si pasa la inspección, validar primero que ningún componente activo esté en REQUIERE_REEMPLAZO o inactivo
    if datos.inspeccion_pasada:
        ids_rehabilitados = {
            item.componente_id
            for item in (datos.componentes_afectados or [])
            if item.componente_id is not None and item.estado == EstadoComponente.DISPONIBLE.value
        }
        comp_reemplazo = session.exec(
            select(Componente).where(
                Componente.equipo_id == equipo.equipo_id,
                Componente.activo == True,  # type: ignore
                Componente.estado == EstadoComponente.REQUIERE_REEMPLAZO,
            )
        ).all()
        comp_reemplazo_sin_reparar = [
            c for c in comp_reemplazo if c.componente_id not in ids_rehabilitados
        ]
        if comp_reemplazo_sin_reparar:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede habilitar el equipo como Disponible mientras tenga componentes que requieren reemplazo.",
            )

    # 6. Crear el registro de revisión
    componentes_input = datos.componentes_afectados or []
    datos_dict = datos.model_dump(exclude={"componentes_afectados"})
    datos_dict["usuario_id"] = usuario_id
    revision = RevisionEquipo(**datos_dict)
    session.add(revision)
    session.flush()

    # 7. Actualización sincronizada de estados de componentes y equipo
    detalle_renta.estado = EstadoRenta.FINALIZADA
    if not detalle_renta.hora_fin:
        detalle_renta.hora_fin = datetime.now(timezone.utc)

    fecha_str = (revision.fecha_revision or datetime.now(timezone.utc)).strftime("%d/%m/%Y %H:%M")

    # Procesar cualquier cambio de componente enviado explícitamente desde el móvil
    componentes_procesados_ids: set[int] = set()
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

        if comp_obj and comp_obj.equipo_id == equipo.equipo_id:
            if comp_obj.componente_id is not None:
                componentes_procesados_ids.add(comp_obj.componente_id)
            estado_previo_str = (
                comp_obj.estado.value if hasattr(comp_obj.estado, "value") else str(comp_obj.estado)
            )
            if item.estado:
                try:
                    comp_obj.estado = EstadoComponente(item.estado)
                except Exception:
                    comp_obj.estado = (
                        EstadoComponente.DISPONIBLE
                        if datos.inspeccion_pasada
                        else EstadoComponente.DANIOS_MENORES
                    )
            else:
                comp_obj.estado = (
                    EstadoComponente.DISPONIBLE
                    if datos.inspeccion_pasada
                    else EstadoComponente.DANIOS_MENORES
                )

            estado_nuevo_str = (
                comp_obj.estado.value if hasattr(comp_obj.estado, "value") else str(comp_obj.estado)
            )
            if comp_obj.estado != EstadoComponente.DISPONIBLE:
                detalle_falla = (
                    item.descripcion_danio
                    or datos.observaciones
                    or "Reportado con novedades en inspección técnica"
                )
                bloque_historial = (
                    f"[REVISIÓN: #{revision.revision_equipo_id} | FECHA: {fecha_str}]\n"
                    f"Descripción: {detalle_falla}\n"
                    f"--------------------------------------------------"
                )
                if comp_obj.observaciones:
                    comp_obj.observaciones = f"{bloque_historial}\n{comp_obj.observaciones}"
                else:
                    comp_obj.observaciones = bloque_historial
            else:
                detalle_falla = item.descripcion_danio or datos.observaciones or "Componente rehabilitado a Disponible"

            session.add(comp_obj)

            if comp_obj.componente_id is not None and revision.revision_equipo_id is not None:
                rev_comp = RevisionComponente(
                    revision_equipo_id=revision.revision_equipo_id,
                    componente_id=comp_obj.componente_id,
                    estado_previo=estado_previo_str,
                    estado_nuevo=estado_nuevo_str,
                    descripcion=detalle_falla,
                )
                session.add(rev_comp)

    if not datos.inspeccion_pasada:
        equipo.estado = estado_si_daniado
    else:
        # Si aprobó la inspección, restablecer también cualquier componente en DANIOS_MENORES que no haya venido en el payload
        comp_menores = session.exec(
            select(Componente).where(
                Componente.equipo_id == equipo.equipo_id,
                Componente.estado == EstadoComponente.DANIOS_MENORES,
            )
        ).all()
        for comp in comp_menores:
            if comp.componente_id in componentes_procesados_ids:
                continue
            estado_prev = comp.estado.value if hasattr(comp.estado, "value") else str(comp.estado)
            comp.estado = EstadoComponente.DISPONIBLE
            session.add(comp)
            if comp.componente_id is not None and revision.revision_equipo_id is not None:
                session.add(
                    RevisionComponente(
                        revision_equipo_id=revision.revision_equipo_id,
                        componente_id=comp.componente_id,
                        estado_previo=estado_prev,
                        estado_nuevo=EstadoComponente.DISPONIBLE.value,
                        descripcion=datos.observaciones or "Rehabilitado en inspección aprobada",
                    )
                )

        comp_inactivos = session.exec(
            select(Componente).where(
                Componente.equipo_id == equipo.equipo_id,
                Componente.activo == False,  # type: ignore
            )
        ).all()
        if comp_inactivos:
            equipo.estado = EstadoEquipo.EN_MANTENIMIENTO
        else:
            equipo.estado = EstadoEquipo.DISPONIBLE

    session.add(equipo)
    session.add(detalle_renta)

    # 8. Registrar en tabla de auditoría
    if revision.revision_equipo_id is not None:
        estado_equipo_nuevo = equipo.estado.value if hasattr(equipo.estado, "value") else str(equipo.estado)
        session.add(
            Auditoria(
                usuario_id=usuario_id,
                accion="CREAR_REVISION",
                entidad="RevisionEquipo",
                entidad_id=revision.revision_equipo_id,
                valor_previo={"equipo_estado": estado_equipo_previo, "renta_estado": "Pendiente Revision"},
                valor_nuevo={
                    "equipo_estado": estado_equipo_nuevo,
                    "renta_estado": "Finalizada",
                    "inspeccion_pasada": datos.inspeccion_pasada,
                },
                origen="API",
                ip=request.client.host if request.client else None,
            )
        )

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una revisión registrada para este detalle de renta",
        )
    except Exception:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo registrar la revisión; la transacción fue revertida",
        )

    session.refresh(revision)
    renta = session.get(Renta, detalle_renta.renta_id)
    cliente = session.get(Cliente, renta.cliente_id) if renta else None
    cliente_nombre = f"{cliente.nombre} {cliente.apellido}".strip() if cliente else None
    return construir_respuesta_revision(
        revision,
        usuario,
        equipo=equipo,
        cliente_nombre=cliente_nombre,
    )
