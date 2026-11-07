from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlmodel import select

from config.paginacion import paginar_consulta
from config.security_dependencia import (
    Asistente_Token_Dependencia,
    Token_Dependencia,
)
from config.session_dependencia import SessionDeDependencia
from models.cliente import Cliente
from models.detalle_renta import DetalleRenta, EstadoRenta
from models.renta import (
    EstadoPago,
    Renta,
    RentaActivaResponse,
    RentaConDetallesResponse,
)
from services.notificacion_service import verificar_vencimiento_rentas


ROLES_CON_PERMISO_LECTURA_RENTAS = {1, 2}
ROLES_CON_PERMISO_OPERATIVO_RENTAS = {1, 2, 3}

router = APIRouter()


def validar_permisos_lectura(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_LECTURA_RENTAS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para consultar rentas",
        )


def validar_permisos_operativos(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_OPERATIVO_RENTAS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para consultar detalles operativos de rentas",
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
def get_rentas(
    response: Response,
    session: SessionDeDependencia,
    token: Token_Dependencia,
    cliente_id: int | None = Query(None, description="Filtrar por cliente"),
    estado_de_pago: EstadoPago | None = Query(None, description="Filtrar por estado de pago"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=500),
):
    validar_permisos_lectura(token)
    consulta = select(Renta)

    if cliente_id is not None:
        consulta = consulta.where(Renta.cliente_id == cliente_id)
    if estado_de_pago is not None:
        consulta = consulta.where(Renta.estado_de_pago == estado_de_pago)

    return paginar_consulta(
        session=session,
        response=response,
        consulta=consulta,
        columna_orden=Renta.renta_id.desc(),  # type: ignore
        offset=offset,
        limit=limit,
    )


@router.get(
    "/rentas/activas",
    response_model=list[RentaActivaResponse],
    status_code=status.HTTP_200_OK,
)
def get_rentas_activas(
    session: SessionDeDependencia,
    token: Asistente_Token_Dependencia,
):
    """
    Monitorea las computadoras y consolas en uso o con tiempo terminado,
    calculando el tiempo restante en vivo de cada sesión.
    Ejecuta el auto-cierre de tiempo vencido.
    """
    try:
        verificar_vencimiento_rentas(session)
    except Exception:
        session.rollback()

    detalles = session.exec(
        select(DetalleRenta)
        .where(
            DetalleRenta.estado.in_([EstadoRenta.ACTIVA, EstadoRenta.TIEMPO_TERMINADO])  # type: ignore
        )
        .order_by(DetalleRenta.detalle_renta_id.asc())  # type: ignore
    ).all()

    if not detalles:
        return []

    renta_ids = {d.renta_id for d in detalles if d.renta_id is not None}
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

    ahora = datetime.now(timezone.utc)
    resultado: list[RentaActivaResponse] = []

    for detalle in detalles:
        tiempo_total = detalle.tiempo_de_renta + (detalle.tiempo_agregado or 0)
        hora_inicio = detalle.hora_inicio
        if hora_inicio.tzinfo is None:
            hora_inicio = hora_inicio.replace(tzinfo=timezone.utc)

        transcurridos = int((ahora - hora_inicio).total_seconds() // 60)
        if detalle.estado == EstadoRenta.TIEMPO_TERMINADO:
            min_restantes = 0
        elif detalle.hora_vencimiento is not None:
            hv = detalle.hora_vencimiento
            if hv.tzinfo is None:
                hv = hv.replace(tzinfo=timezone.utc)
            min_restantes = max(int((hv - ahora).total_seconds() // 60), 0)
        else:
            min_restantes = max(tiempo_total - transcurridos, 0)

        renta = rentas_por_id.get(detalle.renta_id)
        cliente = clientes_por_id.get(renta.cliente_id) if renta else None
        cl_nombre = (
            f"{cliente.nombre} {cliente.apellido}".strip()
            if cliente
            else "Cliente General"
        )

        resultado.append(
            RentaActivaResponse(
                detalle_renta_id=detalle.detalle_renta_id,  # type: ignore
                renta_id=detalle.renta_id,
                equipo_id=detalle.equipo_id,
                cliente_nombre=cl_nombre,
                hora_inicio=detalle.hora_inicio,
                hora_fin=detalle.hora_fin,
                hora_vencimiento=detalle.hora_vencimiento,
                tiempo_de_renta=detalle.tiempo_de_renta,
                tiempo_agregado=detalle.tiempo_agregado,
                tiempo_total=tiempo_total,
                minutos_transcurridos=transcurridos,
                minutos_restantes=min_restantes,
                subtotal=detalle.subtotal,
                estado=detalle.estado.value,
            )
        )

    return resultado


@router.get(
    "/detalles-renta/pendientes-revision",
    status_code=status.HTTP_200_OK,
)
def get_detalles_pendientes_revision(
    response: Response,
    session: SessionDeDependencia,
    token: Token_Dependencia,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """
    Devuelve los puestos enviados a revisión física post-renta (PENDIENTE_REVISION),
    con los datos del cliente resueltos en lote y cabecera X-Total-Count.
    """
    validar_permisos_operativos(token)
    consulta = select(DetalleRenta).where(
        DetalleRenta.estado == EstadoRenta.PENDIENTE_REVISION
    )
    detalles = paginar_consulta(
        session=session,
        response=response,
        consulta=consulta,
        columna_orden=(
            DetalleRenta.hora_fin.asc(),  # type: ignore
            DetalleRenta.detalle_renta_id.asc(),  # type: ignore
        ),
        offset=offset,
        limit=limit,
    )

    if not detalles:
        return []

    renta_ids = {d.renta_id for d in detalles if d.renta_id is not None}
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

    resultado = []
    for d in detalles:
        renta = rentas_por_id.get(d.renta_id)
        cliente = clientes_por_id.get(renta.cliente_id) if renta else None
        cl_nombre = (
            f"{cliente.nombre} {cliente.apellido}".strip()
            if cliente
            else "Cliente General"
        )
        resultado.append({
            "detalle_renta_id": d.detalle_renta_id,
            "equipo_id": d.equipo_id,
            "renta_id": d.renta_id,
            "cliente_nombre": cl_nombre,
            "hora_inicio": d.hora_inicio.isoformat() if d.hora_inicio else None,
            "hora_fin": d.hora_fin.isoformat() if d.hora_fin else None,
            "tiempo_de_renta": d.tiempo_de_renta,
            "tiempo_agregado": d.tiempo_agregado,
            "subtotal": float(d.subtotal),
            "estado": d.estado.value,
        })
    return resultado


@router.get(
    "/rentas/{renta_id}",
    response_model=RentaConDetallesResponse,
    status_code=status.HTTP_200_OK,
)
def get_renta(
    renta_id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    """Consulta la renta junto a todos sus detalles de sesiones de equipos."""
    validar_permisos_lectura(token)
    renta = obtener_renta(session, renta_id)
    detalles = session.exec(
        select(DetalleRenta)
        .where(DetalleRenta.renta_id == renta_id)
        .order_by(DetalleRenta.detalle_renta_id.asc())  # type: ignore
    ).all()
    return RentaConDetallesResponse(renta=renta, detalles=detalles)  # type: ignore


@router.get(
    "/detalles-renta",
    response_model=list[DetalleRenta],
    status_code=status.HTTP_200_OK,
)
def get_detalles_renta(
    response: Response,
    session: SessionDeDependencia,
    token: Token_Dependencia,
    renta_id: int | None = Query(None, description="Filtrar por ID de renta"),
    equipo_id: int | None = Query(None, description="Filtrar por equipo"),
    estado: EstadoRenta | None = Query(None, description="Filtrar por estado"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=500),
):
    validar_permisos_operativos(token)
    consulta = select(DetalleRenta)

    if renta_id is not None:
        consulta = consulta.where(DetalleRenta.renta_id == renta_id)
    if equipo_id is not None:
        consulta = consulta.where(DetalleRenta.equipo_id == equipo_id)
    if estado is not None:
        consulta = consulta.where(DetalleRenta.estado == estado)

    return paginar_consulta(
        session=session,
        response=response,
        consulta=consulta,
        columna_orden=DetalleRenta.detalle_renta_id.desc(),  # type: ignore
        offset=offset,
        limit=limit,
    )
