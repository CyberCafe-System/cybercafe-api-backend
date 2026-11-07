from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select
from config.security_dependencia import Token_Dependencia
from config.session_dependencia import SessionDeDependencia
from models.notificacion import Notificacion, NotificacionResponse
from services.notificacion_service import verificar_vencimiento_rentas

router = APIRouter(prefix="/notificaciones", tags=["notificaciones"])


@router.get(
    "/pendientes",
    response_model=list[NotificacionResponse],
    status_code=status.HTTP_200_OK,
)
def get_notificaciones_pendientes(
    session: SessionDeDependencia,
    token: Token_Dependencia,
    limit: int = Query(100, ge=1, le=500),
):
    """
    Obtiene las notificaciones no leídas para el usuario autenticado (Asistente o Admin).
    Verifica automáticamente si hay rentas que hayan terminado su tiempo.
    """
    usuario_id = token.get("id")
    if not usuario_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")

    # Ejecutar verificación de vencimientos en cada sondeo de forma segura
    try:
        verificar_vencimiento_rentas(session)
    except Exception:
        session.rollback()

    consulta = (
        select(Notificacion)
        .where(
            Notificacion.usuario_destino_id == usuario_id,
            Notificacion.leida_en == None,  # type: ignore
        )
        .order_by(Notificacion.creada_en.desc())  # type: ignore
        .limit(limit)
    )
    return session.exec(consulta).all()


@router.post(
    "/{notificacion_id}/leer",
    status_code=status.HTTP_200_OK,
)
def marcar_notificacion_leida(
    notificacion_id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    """Marca una notificación como leída."""
    usuario_id = token.get("id")
    notif = session.get(Notificacion, notificacion_id)
    if not notif or notif.usuario_destino_id != usuario_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificación no encontrada")

    notif.leida_en = datetime.now(timezone.utc)
    session.add(notif)
    session.commit()
    return {"message": "Notificación marcada como leída", "notificacion_id": notificacion_id}


@router.post(
    "/leer-todas",
    status_code=status.HTTP_200_OK,
)
def marcar_todas_leidas(
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    """Marca todas las notificaciones pendientes del usuario como leídas."""
    usuario_id = token.get("id")
    notificaciones = session.exec(
        select(Notificacion).where(
            Notificacion.usuario_destino_id == usuario_id,
            Notificacion.leida_en == None,  # type: ignore
        )
    ).all()
    ahora = datetime.now(timezone.utc)
    for n in notificaciones:
        n.leida_en = ahora
        session.add(n)
    session.commit()
    return {"message": "Todas las notificaciones fueron marcadas como leídas", "total": len(notificaciones)}
