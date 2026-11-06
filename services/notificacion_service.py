from datetime import datetime, timezone
from sqlmodel import Session, select
from models.detalle_renta import DetalleRenta, EstadoRenta
from models.notificacion import Notificacion
from models.usuario import Usuario
from models.equipo import Equipo
from models.renta import Renta
from models.cliente import Cliente


def verificar_vencimiento_rentas(session: Session) -> int:
    """
    Busca todas las sesiones activas cuya hora_vencimiento ya transcurrió
    y las marca como TIEMPO_TERMINADO, creando notificaciones para los asistentes y administradores activos.
    Retorna la cantidad de sesiones vencidas.
    """
    ahora = datetime.now(timezone.utc)
    # Seleccionar sesiones activas con hora_vencimiento <= ahora
    detalles = session.exec(
        select(DetalleRenta).where(
            DetalleRenta.estado == EstadoRenta.ACTIVA,
            DetalleRenta.hora_vencimiento != None, #type: ignore
            DetalleRenta.hora_vencimiento <= ahora, #type: ignore
        )
    ).all()

    verificar_equipos_en_revision(session)

    if not detalles:
        return 0

    # Obtener asistentes (rol_id = 3) y admins (rol_id = 1) activos
    destinatarios = session.exec(
        select(Usuario).where(
            Usuario.activo == True, #type: ignore
            Usuario.rol_id.in_([1, 3]), #type: ignore
        )
    ).all()

    vencidas = 0
    for detalle in detalles:
        detalle.estado = EstadoRenta.TIEMPO_TERMINADO
        session.add(detalle)
        vencidas += 1

        equipo = session.get(Equipo, detalle.equipo_id)
        equipo_nom = equipo.nombre if equipo else f"Equipo #{detalle.equipo_id}"
        renta = session.get(Renta, detalle.renta_id)
        cliente = session.get(Cliente, renta.cliente_id) if renta else None
        cliente_nom = f"{cliente.nombre} {cliente.apellido}".strip() if cliente else "Cliente General"

        for u in destinatarios:
            # Comprobar si ya existe notificación para evitar duplicados
            notif_existente = session.exec(
                select(Notificacion).where(
                    Notificacion.usuario_destino_id == u.usuario_id,
                    Notificacion.tipo == "TIEMPO_TERMINADO",
                    Notificacion.detalle_renta_id == detalle.detalle_renta_id,
                )
            ).first()
            if not notif_existente and u.usuario_id is not None and detalle.detalle_renta_id is not None:
                notif = Notificacion(
                    usuario_destino_id=u.usuario_id,
                    tipo="TIEMPO_TERMINADO",
                    detalle_renta_id=detalle.detalle_renta_id,
                    titulo=f"Tiempo terminado: {equipo_nom}",
                    mensaje=f"La renta de {cliente_nom} en {equipo_nom} ha finalizado su tiempo contratado ({detalle.tiempo_de_renta} min).",
                    creada_en=ahora,
                )
                session.add(notif)

    session.commit()
    verificar_equipos_en_revision(session)
    return vencidas


def verificar_equipos_en_revision(session: Session) -> int:
    """
    Busca todas las sesiones en estado PENDIENTE_REVISION y crea notificaciones
    para los asistentes y administradores activos si aún no existen.
    Retorna la cantidad de notificaciones creadas.
    """
    ahora = datetime.now(timezone.utc)
    detalles_revision = session.exec(
        select(DetalleRenta).where(
            DetalleRenta.estado == EstadoRenta.PENDIENTE_REVISION,
        )
    ).all()

    if not detalles_revision:
        return 0

    destinatarios = session.exec(
        select(Usuario).where(
            Usuario.activo == True,  # type: ignore
            Usuario.rol_id.in_([1, 3]),  # type: ignore
        )
    ).all()

    if not destinatarios:
        return 0

    creadas = 0
    for detalle in detalles_revision:
        equipo = session.get(Equipo, detalle.equipo_id)
        equipo_nom = equipo.nombre if equipo else f"Equipo #{detalle.equipo_id}"

        for u in destinatarios:
            notif_existente = session.exec(
                select(Notificacion).where(
                    Notificacion.usuario_destino_id == u.usuario_id,
                    Notificacion.tipo == "PENDIENTE_REVISION",
                    Notificacion.detalle_renta_id == detalle.detalle_renta_id,
                )
            ).first()
            if not notif_existente and u.usuario_id is not None and detalle.detalle_renta_id is not None:
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
        session.commit()
    return creadas


