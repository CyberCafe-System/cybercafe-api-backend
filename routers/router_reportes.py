from datetime import date
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import case, func
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


def _extraer_tupla(fila) -> tuple:
    if isinstance(fila, tuple):
        return fila
    try:
        return tuple(fila)
    except TypeError:
        return (fila,)


@router.get(
    "/reportes/resumen-general",
    response_model=ResumenGeneralResponse,
    status_code=status.HTTP_200_OK,
)
def get_resumen_general(
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    """
    Retorna los indicadores clave (KPIs) y métricas globales del Cybercafé
    calculados mediante agregación SQL directa sin volcar tablas a RAM.
    """
    validar_permisos_reportes(token, permitir_cajero=True)

    # 1. Ventas: conteo y suma subtotal + iva (excluyendo anuladas)
    fila_ventas = _extraer_tupla(
        session.exec(
            select(
                func.count(Venta.venta_id),
                func.coalesce(func.sum(Venta.subtotal + Venta.iva), Decimal("0.00")),
            ).where(Venta.estado != "ANULADA")
        ).one()
    )
    cantidad_ventas = int(fila_ventas[0] or 0)
    total_ingresos_ventas = Decimal(str(fila_ventas[1] or "0.00"))

    # 2. Rentas: conteo total y suma de totales pagados
    fila_rentas = _extraer_tupla(
        session.exec(
            select(
                func.count(Renta.renta_id),
                func.coalesce(
                    func.sum(
                        case(
                            (Renta.estado_de_pago == EstadoPago.PAGADO, Renta.total),
                            else_=Decimal("0.00"),
                        )
                    ),
                    Decimal("0.00"),
                ),
            )
        ).one()
    )
    cantidad_rentas = int(fila_rentas[0] or 0)
    total_ingresos_rentas = Decimal(str(fila_rentas[1] or "0.00"))

    total_ingresos = total_ingresos_ventas + total_ingresos_rentas

    # 3. Sesiones de renta activas
    sesiones_activas_val = session.exec(
        select(func.count(DetalleRenta.detalle_renta_id)).where(
            DetalleRenta.estado.in_([EstadoRenta.ACTIVA, EstadoRenta.TIEMPO_TERMINADO])  # type: ignore
        )
    ).one()
    sesiones_activas = int(_extraer_tupla(sesiones_activas_val)[0] or 0)

    # 4. Clientes
    total_clientes_val = session.exec(select(func.count(Cliente.cliente_id))).one()
    total_clientes = int(_extraer_tupla(total_clientes_val)[0] or 0)

    # 5. Equipos activos
    fila_equipos = _extraer_tupla(
        session.exec(
            select(
                func.count(Equipo.equipo_id),
                func.coalesce(
                    func.sum(
                        case((Equipo.estado == EstadoEquipo.DISPONIBLE, 1), else_=0)
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                Equipo.estado.in_(  # type: ignore
                                    [
                                        EstadoEquipo.DANIOS_MENORES,
                                        EstadoEquipo.DEFECTUOSO,
                                        EstadoEquipo.EN_MANTENIMIENTO,
                                    ]
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
            ).where(Equipo.activo == True)  # type: ignore
        ).one()
    )
    total_equipos = int(fila_equipos[0] or 0)
    equipos_disponibles = int(fila_equipos[1] or 0)
    equipos_averiados = int(fila_equipos[2] or 0)

    # 6. Productos activos con bajo inventario (<= 5 unidades)
    stock_bajo_val = session.exec(
        select(func.count(Producto.producto_id)).where(
            Producto.activo == True,  # type: ignore
            Producto.cantidad <= 5,  # type: ignore
        )
    ).one()
    productos_stock_bajo = int(_extraer_tupla(stock_bajo_val)[0] or 0)

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
def get_resumen_diario(
    session: SessionDeDependencia,
    token: Token_Dependencia,
    fecha_reporte: date | None = Query(
        None, description="Fecha a consultar (por defecto la fecha actual)"
    ),
):
    """
    Retorna el corte diario de caja del Cybercafé calculado mediante agregación SQL.
    """
    validar_permisos_reportes(token, permitir_cajero=True)

    dia = fecha_reporte or fecha_local_actual()
    inicio_dia, fin_dia = rango_dia_utc(dia)

    # Ventas del día (excluyendo anuladas)
    fila_ventas_hoy = _extraer_tupla(
        session.exec(
            select(
                func.count(Venta.venta_id),
                func.coalesce(func.sum(Venta.subtotal + Venta.iva), Decimal("0.00")),
            ).where(
                Venta.fecha >= inicio_dia,
                Venta.fecha < fin_dia,
                Venta.estado != "ANULADA",
            )
        ).one()
    )
    cantidad_ventas_hoy = int(fila_ventas_hoy[0] or 0)
    ingresos_ventas_hoy = Decimal(str(fila_ventas_hoy[1] or "0.00"))

    # Rentas del día
    fila_rentas_hoy = _extraer_tupla(
        session.exec(
            select(
                func.count(Renta.renta_id),
                func.coalesce(
                    func.sum(
                        case(
                            (Renta.estado_de_pago == EstadoPago.PAGADO, Renta.total),
                            else_=Decimal("0.00"),
                        )
                    ),
                    Decimal("0.00"),
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (Renta.estado_de_pago == EstadoPago.PENDIENTE, 1),
                            else_=0,
                        )
                    ),
                    0,
                ),
            ).where(Renta.fecha >= inicio_dia, Renta.fecha < fin_dia)
        ).one()
    )
    cantidad_rentas_hoy = int(fila_rentas_hoy[0] or 0)
    ingresos_rentas_hoy = Decimal(str(fila_rentas_hoy[1] or "0.00"))
    rentas_pendientes = int(fila_rentas_hoy[2] or 0)

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
