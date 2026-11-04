from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from config.security_dependencia import (
    Asistente_Token_Dependencia,
    Token_Dependencia,
)
from config.session_dependencia import SessionDeDependencia
from models.detalle_renta import DetalleRenta, EstadoRenta
from models.renta import (
    EstadoPago,
    Renta,
    RentaActivaResponse,
    RentaConDetallesResponse,
)


ROLES_CON_PERMISO_LECTURA_RENTAS = {1, 2, 3}

router = APIRouter()


def validar_permisos_lectura(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_LECTURA_RENTAS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para consultar rentas",
        )


def obtener_renta(session: SessionDeDependencia, renta_id: int) -> Renta:
    renta = session.get(Renta, renta_id)
    if not renta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"La renta con ID {renta_id} no fue encontrada",
        )
    return renta


@router.get(
    "/rentas",
    response_model=list[Renta],
    status_code=status.HTTP_200_OK,
)
async def get_rentas(
    session: SessionDeDependencia,
    token: Token_Dependencia,
    cliente_id: int | None = Query(None, description="Filtrar por cliente"),
    estado_de_pago: EstadoPago | None = Query(None, description="Filtrar por estado de pago"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1),
):
    validar_permisos_lectura(token)
    consulta = select(Renta)

    if cliente_id is not None:
        consulta = consulta.where(Renta.cliente_id == cliente_id)
    if estado_de_pago is not None:
        consulta = consulta.where(Renta.estado_de_pago == estado_de_pago)

    return session.exec(consulta.offset(offset).limit(limit)).all()


@router.get(
    "/rentas/activas",
    response_model=list[RentaActivaResponse],
    status_code=status.HTTP_200_OK,
)
async def get_rentas_activas(
    session: SessionDeDependencia,
    token: Asistente_Token_Dependencia,
):
    """
    Monitorea las computadoras y consolas en uso, calculando el tiempo restante
    en vivo de cada sesión activa.

    Acceso exclusivo del Asistente (rol_id = 3) y del Administrador (rol_id = 1).
    """
    detalles = session.exec(
        select(DetalleRenta).where(DetalleRenta.estado == EstadoRenta.ACTIVA)
    ).all()

    ahora = datetime.now(timezone.utc)
    resultado: list[RentaActivaResponse] = []

    for detalle in detalles:
        tiempo_total = detalle.tiempo_de_renta + (detalle.tiempo_agregado or 0)
        # Normaliza hora_inicio a UTC consciente para el cálculo del transcurso
        hora_inicio = detalle.hora_inicio
        if hora_inicio.tzinfo is None:
            hora_inicio = hora_inicio.replace(tzinfo=timezone.utc)

        transcurridos = int((ahora - hora_inicio).total_seconds() // 60)
        resultado.append(
            RentaActivaResponse(
                detalle_renta_id=detalle.detalle_renta_id, #type: ignore
                renta_id=detalle.renta_id,
                equipo_id=detalle.equipo_id,
                hora_inicio=detalle.hora_inicio,
                hora_fin=detalle.hora_fin,
                tiempo_de_renta=detalle.tiempo_de_renta,
                tiempo_agregado=detalle.tiempo_agregado,
                tiempo_total=tiempo_total,
                minutos_transcurridos=transcurridos,
                minutos_restantes=max(tiempo_total - transcurridos, 0),
                subtotal=detalle.subtotal,
                estado=detalle.estado.value,
            )
        )

    return resultado


@router.get(
    "/rentas/{renta_id}",
    response_model=RentaConDetallesResponse,
    status_code=status.HTTP_200_OK,
)
async def get_renta(
    renta_id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    """Consulta la renta junto a todos sus detalles de sesiones de equipos."""
    validar_permisos_lectura(token)
    renta = obtener_renta(session, renta_id)
    detalles = session.exec(
        select(DetalleRenta).where(DetalleRenta.renta_id == renta_id)
    ).all()
    return RentaConDetallesResponse(renta=renta, detalles=detalles) #type: ignore


@router.get(
    "/detalles-renta",
    response_model=list[DetalleRenta],
    status_code=status.HTTP_200_OK,
)
async def get_detalles_renta(
    session: SessionDeDependencia,
    token: Token_Dependencia,
    renta_id: int | None = Query(None, description="Filtrar por ID de renta"),
    equipo_id: int | None = Query(None, description="Filtrar por equipo"),
    estado: EstadoRenta | None = Query(None, description="Filtrar por estado (Activa, Pendiente Revision, Finalizada)"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1),
):
    validar_permisos_lectura(token)
    consulta = select(DetalleRenta)

    if renta_id is not None:
        consulta = consulta.where(DetalleRenta.renta_id == renta_id)
    if equipo_id is not None:
        consulta = consulta.where(DetalleRenta.equipo_id == equipo_id)
    if estado is not None:
        consulta = consulta.where(DetalleRenta.estado == estado)

    return session.exec(consulta.offset(offset).limit(limit)).all()
