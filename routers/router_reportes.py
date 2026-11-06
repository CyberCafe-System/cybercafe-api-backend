from datetime import date
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from config.security_dependencia import Token_Dependencia
from config.session_dependencia import SessionDeDependencia
from config.timezone import (
    fecha_local_actual,
    rango_dia_utc,
)
from models.cliente import Cliente
from models.detalle_renta import DetalleRenta, EstadoRenta
from models.equipo import Equipo, EstadoEquipo
from models.producto import Producto
from models.renta import EstadoPago, Renta
from models.venta import Venta
from models.reporte import (
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

    # 1. Ventas: suma subtotal + iva (excluyendo anuladas)
    ventas = session.exec(select(Venta).where(Venta.estado != "ANULADA")).all()
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
            select(DetalleRenta).where(
                DetalleRenta.estado.in_([EstadoRenta.ACTIVA, EstadoRenta.TIEMPO_TERMINADO]) #type: ignore
            )
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

    dia = fecha_reporte or fecha_local_actual()
    inicio_dia, fin_dia = rango_dia_utc(dia)

    # Ventas del día (excluyendo anuladas)
    ventas_hoy = session.exec(
        select(Venta).where(
            Venta.fecha >= inicio_dia,
            Venta.fecha < fin_dia,
            Venta.estado != "ANULADA",
        )
    ).all()
    ingresos_ventas_hoy = sum(
        (v.subtotal + v.iva for v in ventas_hoy), Decimal("0.00")
    )
    cantidad_ventas_hoy = len(ventas_hoy)

    # Rentas del día
    rentas_hoy = session.exec(
        select(Renta).where(Renta.fecha >= inicio_dia, Renta.fecha < fin_dia)
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
