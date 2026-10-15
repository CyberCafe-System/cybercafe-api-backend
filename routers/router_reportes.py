from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import SQLModel, func, select

from config.security_dependencia import Token_Dependencia
from config.session_dependencia import SessionDeDependencia
from models.cliente import Cliente
from models.detalle_renta import DetalleRenta, EstadoRenta
from models.detalle_venta import DetalleVenta
from models.equipo import Equipo, EstadoEquipo
from models.producto import Producto
from models.renta import EstadoPago, Renta
from models.venta import Venta
from models.reporte import (
    EquipoTopResponse,
    ProductoTopResponse,
    ReporteRangoFechasResponse,
    ResumenDiarioResponse,
    ResumenGeneralResponse,
)


ROLES_ADMIN = {1}
ROLES_ADMIN_Y_CAJERO = {1, 2}

router = APIRouter()


def validar_permisos_reportes(token: dict, permitir_cajero: bool = False) -> None:
    roles_validos = ROLES_ADMIN_Y_CAJERO if permitir_cajero else ROLES_ADMIN
    if token.get("id_rol") not in roles_validos:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para consultar estos reportes",
        )


@router.get(
    "/reportes/resumen-general",
    response_model=ResumenGeneralResponse,
    status_code=status.HTTP_200_OK,
)
async def get_resumen_general(
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    """
    Retorna los indicadores clave (KPIs) y métricas globales del Cybercafé:
    - Ingresos totales por ventas y rentas.
    - Conteo de clientes, equipos y estado operativo.
    - Sesiones de renta en curso y alertas de inventario.
    """
    validar_permisos_reportes(token, permitir_cajero=True)

    # 1. Ventas: suma subtotal + iva
    ventas = session.exec(select(Venta)).all()
    cantidad_ventas = len(ventas)
    total_ingresos_ventas = sum((v.subtotal + v.iva for v in ventas), Decimal("0.00"))

    # 2. Rentas: suma de totales pagados
    rentas = session.exec(select(Renta)).all()
    cantidad_rentas = len(rentas)
    total_ingresos_rentas = sum(
        (r.total for r in rentas if r.estado_de_pago == EstadoPago.PAGADO),
        Decimal("0.00"),
    )

    total_ingresos = total_ingresos_ventas + total_ingresos_rentas

    # 3. Sesiones de renta activas
    sesiones_activas = len(
        session.exec(
            select(DetalleRenta).where(DetalleRenta.estado == EstadoRenta.ACTIVA)
        ).all()
    )

    # 4. Clientes
    total_clientes = len(session.exec(select(Cliente)).all())

    # 5. Equipos
    equipos = session.exec(select(Equipo)).all()
    total_equipos = len(equipos)
    equipos_disponibles = sum(
        1 for e in equipos if e.estado == EstadoEquipo.DISPONIBLE
    )
    equipos_averiados = sum(
        1
        for e in equipos
        if e.estado in (EstadoEquipo.DANIOS_MENORES, EstadoEquipo.DEFECTUOSO, EstadoEquipo.EN_MANTENIMIENTO)
    )

    # 6. Productos con bajo inventario (<= 5 unidades)
    productos = session.exec(select(Producto).where(Producto.activo == True)).all()
    productos_stock_bajo = sum(1 for p in productos if p.cantidad <= 5)

    return ResumenGeneralResponse(
        total_ingresos=total_ingresos,
        total_ingresos_ventas=total_ingresos_ventas,
        total_ingresos_rentas=total_ingresos_rentas,
        cantidad_ventas=cantidad_ventas,
        cantidad_rentas=cantidad_rentas,
        sesiones_renta_activas=sesiones_activas,
        total_clientes=total_clientes,
        total_equipos=total_equipos,
        equipos_disponibles=equipos_disponibles,
        equipos_en_mantenimiento_o_averiados=equipos_averiados,
        productos_stock_bajo=productos_stock_bajo,
    )


@router.get(
    "/reportes/diario",
    response_model=ResumenDiarioResponse,
    status_code=status.HTTP_200_OK,
)
async def get_resumen_diario(
    session: SessionDeDependencia,
    token: Token_Dependencia,
    fecha_reporte: date | None = Query(
        None, description="Fecha a consultar (por defecto la fecha actual)"
    ),
):
    """
    Retorna el corte diario de caja del Cybercafé:
    - Ingresos recaudados hoy por venta de productos.
    - Ingresos recaudados hoy por alquiler de computadoras/consolas.
    - Cantidad de transacciones del día y rentas pendientes de pago.
    """
    validar_permisos_reportes(token, permitir_cajero=True)

    dia = fecha_reporte or datetime.now(timezone.utc).date()
    inicio_dia = datetime.combine(dia, time.min)
    fin_dia = datetime.combine(dia, time.max)

    # Ventas del día
    ventas_hoy = session.exec(
        select(Venta).where(Venta.fecha >= inicio_dia, Venta.fecha <= fin_dia)
    ).all()
    ingresos_ventas_hoy = sum(
        (v.subtotal + v.iva for v in ventas_hoy), Decimal("0.00")
    )
    cantidad_ventas_hoy = len(ventas_hoy)

    # Rentas del día
    rentas_hoy = session.exec(
        select(Renta).where(Renta.fecha >= inicio_dia, Renta.fecha <= fin_dia)
    ).all()
    ingresos_rentas_hoy = sum(
        (r.total for r in rentas_hoy if r.estado_de_pago == EstadoPago.PAGADO),
        Decimal("0.00"),
    )
    cantidad_rentas_hoy = len(rentas_hoy)
    rentas_pendientes = sum(
        1 for r in rentas_hoy if r.estado_de_pago == EstadoPago.PENDIENTE
    )

    total_dia = ingresos_ventas_hoy + ingresos_rentas_hoy

    return ResumenDiarioResponse(
        fecha=dia,
        total_dia=total_dia,
        ingresos_ventas_hoy=ingresos_ventas_hoy,
        ingresos_rentas_hoy=ingresos_rentas_hoy,
        cantidad_ventas_hoy=cantidad_ventas_hoy,
        cantidad_rentas_hoy=cantidad_rentas_hoy,
        rentas_pendientes_pago_hoy=rentas_pendientes,
    )


@router.get(
    "/reportes/ventas-por-fecha",
    response_model=ReporteRangoFechasResponse,
    status_code=status.HTTP_200_OK,
)
async def get_reporte_ventas_por_fecha(
    fecha_inicio: datetime,
    fecha_fin: datetime,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    """Consulta el total recaudado en ventas dentro de un rango específico de fechas."""
    validar_permisos_reportes(token, permitir_cajero=False)

    ventas = session.exec(
        select(Venta).where(Venta.fecha >= fecha_inicio, Venta.fecha <= fecha_fin)
    ).all()

    total = sum((v.subtotal + v.iva for v in ventas), Decimal("0.00"))
    return ReporteRangoFechasResponse(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        total_recaudado=total,
        cantidad_operaciones=len(ventas),
    )


@router.get(
    "/reportes/rentas-por-fecha",
    response_model=ReporteRangoFechasResponse,
    status_code=status.HTTP_200_OK,
)
async def get_reporte_rentas_por_fecha(
    fecha_inicio: datetime,
    fecha_fin: datetime,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    """Consulta el total recaudado en rentas dentro de un rango específico de fechas."""
    validar_permisos_reportes(token, permitir_cajero=False)

    rentas = session.exec(
        select(Renta).where(Renta.fecha >= fecha_inicio, Renta.fecha <= fecha_fin)
    ).all()

    total = sum(
        (r.total for r in rentas if r.estado_de_pago == EstadoPago.PAGADO),
        Decimal("0.00"),
    )
    return ReporteRangoFechasResponse(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        total_recaudado=total,
        cantidad_operaciones=len(rentas),
    )


@router.get(
    "/reportes/productos-top",
    response_model=list[ProductoTopResponse],
    status_code=status.HTTP_200_OK,
)
async def get_productos_top(
    session: SessionDeDependencia,
    token: Token_Dependencia,
    limit: int = Query(10, ge=1, le=50, description="Cantidad máxima de productos a listar"),
):
    """Ranking de los productos más vendidos en el Cybercafé con sus ingresos generados."""
    validar_permisos_reportes(token, permitir_cajero=True)

    detalles = session.exec(select(DetalleVenta)).all()

    acumulador: dict[int, dict] = {}
    for det in detalles:
        if det.producto_id not in acumulador:
            acumulador[det.producto_id] = {
                "unidades": 0,
                "ingresos": Decimal("0.00"),
            }
        acumulador[det.producto_id]["unidades"] += det.cantidad
        acumulador[det.producto_id]["ingresos"] += det.subtotal

    resultado: list[ProductoTopResponse] = []
    for producto_id, data in acumulador.items():
        prod = session.get(Producto, producto_id)
        nombre = prod.nombre if prod else f"Producto #{producto_id}"
        resultado.append(
            ProductoTopResponse(
                producto_id=producto_id,
                nombre=nombre,
                unidades_vendidas=data["unidades"],
                ingresos_generados=data["ingresos"],
            )
        )

    # Ordenar descendente por unidades vendidas
    resultado.sort(key=lambda x: x.unidades_vendidas, reverse=True)
    return resultado[:limit]


@router.get(
    "/reportes/equipos-top",
    response_model=list[EquipoTopResponse],
    status_code=status.HTTP_200_OK,
)
async def get_equipos_top(
    session: SessionDeDependencia,
    token: Token_Dependencia,
    limit: int = Query(10, ge=1, le=50, description="Cantidad máxima de equipos a listar"),
):
    """Ranking de las computadoras y consolas más utilizadas y con mayores ingresos generados."""
    validar_permisos_reportes(token, permitir_cajero=True)

    detalles = session.exec(select(DetalleRenta)).all()

    acumulador: dict[int, dict] = {}
    for det in detalles:
        if det.equipo_id not in acumulador:
            acumulador[det.equipo_id] = {
                "minutos": 0,
                "ingresos": Decimal("0.00"),
            }
        tiempo_total = det.tiempo_de_renta + (det.tiempo_agregado or 0)
        acumulador[det.equipo_id]["minutos"] += tiempo_total
        acumulador[det.equipo_id]["ingresos"] += det.subtotal

    resultado: list[EquipoTopResponse] = []
    for equipo_id, data in acumulador.items():
        equipo = session.get(Equipo, equipo_id)
        nombre = equipo.nombre if equipo else f"Equipo #{equipo_id}"
        resultado.append(
            EquipoTopResponse(
                equipo_id=equipo_id,
                nombre=nombre,
                total_minutos_rentados=data["minutos"],
                ingresos_generados=data["ingresos"],
            )
        )

    # Ordenar descendente por minutos de uso
    resultado.sort(key=lambda x: x.total_minutos_rentados, reverse=True)
    return resultado[:limit]


@router.get(
    "/reportes/stock-bajo",
    response_model=list[Producto],
    status_code=status.HTTP_200_OK,
)
async def get_productos_stock_bajo(
    session: SessionDeDependencia,
    token: Token_Dependencia,
    umbral: int = Query(5, ge=1, description="Límite mínimo de existencias para emitir alerta"),
):
    """Lista los productos activos cuyo inventario es igual o menor al umbral configurado."""
    validar_permisos_reportes(token, permitir_cajero=True)
    consulta = (
        select(Producto)
        .where(Producto.activo == True, Producto.cantidad <= umbral)
        .order_by(Producto.cantidad) #type: ignore
    )
    return session.exec(consulta).all()
