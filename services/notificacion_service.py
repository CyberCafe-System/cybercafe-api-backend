import logging
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select
from models.detalle_renta import DetalleRenta, EstadoRenta
from models.notificacion import Notificacion
from models.usuario import Usuario
from models.equipo import Equipo
from models.renta import Renta
from models.cliente import Cliente

logger = logging.getLogger("cybercafe.notificaciones")


def _obtener_destinatarios_activos(session: Session) -> list[Usuario]:
    return list(
        session.exec(
            select(Usuario).where(
                Usuario.activo == True,  # type: ignore
                Usuario.rol_id.in_([1, 3]),  # type: ignore
            )
        ).all()
    )


def verificar_vencimiento_rentas(session: Session) -> int:
    """
    Busca todas las sesiones activas cuya hora_vencimiento ya transcurrió
    y las marca como TIEMPO_TERMINADO, creando notificaciones para los asistentes
    y administradores activos sin consultas N+1.
    Retorna la cantidad de sesiones vencidas.
    """
    ahora = datetime.now(timezone.utc)
    detalles = list(
        session.exec(
            select(DetalleRenta)
            .where(
                DetalleRenta.estado == EstadoRenta.ACTIVA,
                DetalleRenta.hora_vencimiento != None,  # type: ignore
                DetalleRenta.hora_vencimiento <= ahora,  # type: ignore
            )
            .with_for_update(skip_locked=True)
        ).all()
    )

    if not detalles:
        verificar_equipos_en_revision(session)
        return 0

    destinatarios = _obtener_destinatarios_activos(session)
    detalle_ids = [d.detalle_renta_id for d in detalles if d.detalle_renta_id is not None]
    equipo_ids = {d.equipo_id for d in detalles if d.equipo_id is not None}
    renta_ids = {d.renta_id for d in detalles if d.renta_id is not None}

    equipos_por_id: dict[int, Equipo] = {}
    if equipo_ids:
        equipos = session.exec(
            select(Equipo).where(Equipo.equipo_id.in_(equipo_ids))  # type: ignore
        ).all()
        equipos_por_id = {e.equipo_id: e for e in equipos if e.equipo_id is not None}

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

    existentes_set: set[tuple[int, int]] = set()
    if detalle_ids and destinatarios:
        existentes = session.exec(
            select(Notificacion).where(
                Notificacion.tipo == "TIEMPO_TERMINADO",
                Notificacion.detalle_renta_id.in_(detalle_ids),  # type: ignore
            )
        ).all()
        existentes_set = {
            (n.usuario_destino_id, n.detalle_renta_id)
            for n in existentes
            if n.usuario_destino_id is not None and n.detalle_renta_id is not None
        }

    vencidas = 0
    for detalle in detalles:
        detalle.estado = EstadoRenta.TIEMPO_TERMINADO
        session.add(detalle)
        vencidas += 1

        equipo = equipos_por_id.get(detalle.equipo_id)
        equipo_nom = equipo.nombre if equipo else f"Equipo #{detalle.equipo_id}"
        renta = rentas_por_id.get(detalle.renta_id)
        cliente = clientes_por_id.get(renta.cliente_id) if renta else None
        cliente_nom = (
            f"{cliente.nombre} {cliente.apellido}".strip()
            if cliente
            else "Cliente General"
        )

        for u in destinatarios:
            if u.usuario_id is None or detalle.detalle_renta_id is None:
                continue
            clave = (u.usuario_id, detalle.detalle_renta_id)
            if clave not in existentes_set:
                existentes_set.add(clave)
                notif = Notificacion(
                    usuario_destino_id=u.usuario_id,
                    tipo="TIEMPO_TERMINADO",
                    detalle_renta_id=detalle.detalle_renta_id,
                    titulo=f"Tiempo terminado: {equipo_nom}",
                    mensaje=f"La renta de {cliente_nom} en {equipo_nom} ha finalizado su tiempo contratado ({detalle.tiempo_de_renta} min).",
                    creada_en=ahora,
                )
                session.add(notif)

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
    except Exception as exc:
        session.rollback()
        logger.warning("Error al confirmar vencimiento de rentas: %s", exc)

    verificar_equipos_en_revision(session, destinatarios=destinatarios)
    return vencidas


def verificar_equipos_en_revision(
    session: Session, destinatarios: list[Usuario] | None = None
) -> int:
    """
    Busca todas las sesiones en estado PENDIENTE_REVISION y crea notificaciones
    para los asistentes y administradores activos si aún no existen, sin N+1.
    Retorna la cantidad de notificaciones creadas.
    """
    ahora = datetime.now(timezone.utc)
    detalles_revision = list(
        session.exec(
            select(DetalleRenta).where(
                DetalleRenta.estado == EstadoRenta.PENDIENTE_REVISION,
            )
        ).all()
    )

    if not detalles_revision:
        return 0

    if destinatarios is None:
        destinatarios = _obtener_destinatarios_activos(session)

    if not destinatarios:
        return 0

    detalle_ids = [
        d.detalle_renta_id for d in detalles_revision if d.detalle_renta_id is not None
    ]
    equipo_ids = {d.equipo_id for d in detalles_revision if d.equipo_id is not None}

    equipos_por_id: dict[int, Equipo] = {}
    if equipo_ids:
        equipos = session.exec(
            select(Equipo).where(Equipo.equipo_id.in_(equipo_ids))  # type: ignore
        ).all()
        equipos_por_id = {e.equipo_id: e for e in equipos if e.equipo_id is not None}

    existentes_set: set[tuple[int, int]] = set()
    if detalle_ids:
        existentes = session.exec(
            select(Notificacion).where(
                Notificacion.tipo == "PENDIENTE_REVISION",
                Notificacion.detalle_renta_id.in_(detalle_ids),  # type: ignore
            )
        ).all()
        existentes_set = {
            (n.usuario_destino_id, n.detalle_renta_id)
            for n in existentes
            if n.usuario_destino_id is not None and n.detalle_renta_id is not None
        }

    creadas = 0
    for detalle in detalles_revision:
        if detalle.detalle_renta_id is None:
            continue
        equipo = equipos_por_id.get(detalle.equipo_id)
        equipo_nom = equipo.nombre if equipo else f"Equipo #{detalle.equipo_id}"

        for u in destinatarios:
            if u.usuario_id is None:
                continue
            clave = (u.usuario_id, detalle.detalle_renta_id)
            if clave not in existentes_set:
                existentes_set.add(clave)
                notif = Notificacion(
                    usuario_destino_id=u.usuario_id,
                    tipo="PENDIENTE_REVISION",
                    detalle_renta_id=detalle.detalle_renta_id,
                    titulo=f"Equipo a revisión: {equipo_nom}",
                    mensaje=f"{equipo_nom} ha sido enviado a revisión técnica. Se requiere realizar la inspección de componentes.",
                    creada_en=ahora,
                )
                session.add(notif)
                creadas += 1

    if creadas > 0:
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            return 0
        except Exception as exc:
            session.rollback()
            logger.warning("Error al confirmar notificaciones de revisión: %s", exc)
            return 0
    return creadas
