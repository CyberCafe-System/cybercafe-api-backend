from datetime import date, datetime
from decimal import Decimal
from sqlmodel import SQLModel


class ResumenGeneralResponse(SQLModel):
    total_ingresos: Decimal
    total_ingresos_ventas: Decimal
    total_ingresos_rentas: Decimal
    cantidad_ventas: int
    cantidad_rentas: int
    sesiones_renta_activas: int
    total_clientes: int
    total_equipos: int
    equipos_disponibles: int
    equipos_en_mantenimiento_o_averiados: int
    productos_stock_bajo: int


class ResumenDiarioResponse(SQLModel):
    fecha: date
    total_dia: Decimal
    ingresos_ventas_hoy: Decimal
    ingresos_rentas_hoy: Decimal
    cantidad_ventas_hoy: int
    cantidad_rentas_hoy: int
    rentas_pendientes_pago_hoy: int


class ReporteRangoFechasResponse(SQLModel):
    fecha_inicio: datetime
    fecha_fin: datetime
    total_recaudado: Decimal
    cantidad_operaciones: int


class ProductoTopResponse(SQLModel):
    producto_id: int
    nombre: str
    unidades_vendidas: int
    ingresos_generados: Decimal


class EquipoTopResponse(SQLModel):
    equipo_id: int
    nombre: str
    total_minutos_rentados: int
    ingresos_generados: Decimal
