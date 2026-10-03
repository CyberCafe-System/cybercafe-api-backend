from sqlmodel import SQLModel, Field, Column, Enum as SAEnum
from typing import Optional
from enum import Enum
from decimal import Decimal
from datetime import datetime, timezone
from models.detalle_renta import DetalleRenta

class EstadoPago(str, Enum):
    PENDIENTE = "Pendiente"
    PAGADO = "Pagado"



def obtener_fecha_utc():
    return datetime.now(timezone.utc)

class RentaBase(SQLModel):
    usuario_id: int = Field(foreign_key="usuarios.usuario_id")
    cliente_id: int = Field(foreign_key="clientes.cliente_id")
    fecha: datetime = Field(default_factory=obtener_fecha_utc)
    total: Decimal = Field(max_digits=10, decimal_places=2)
    estado_de_pago: EstadoPago = Field(sa_column=Column(SAEnum(EstadoPago)))

class Renta(RentaBase, table=True):
    __tablename__ = "rentas"
    renta_id: Optional[int] = Field(default=None, primary_key=True)

class RentaCreate(RentaBase):
    usuario_id: Optional[int] = None

class RentaUpdate(SQLModel):
    cliente_id: Optional[int] = None
    total: Optional[Decimal] = None
    estado_de_pago: Optional[EstadoPago] = None


class IniciarRentaRequest(SQLModel):
    cliente_id: int
    equipo_id: int
    tiempo_de_renta: int = Field(ge=15, description="Tiempo de uso en minutos (ej: 30, 60, 120)")
    estado_de_pago: EstadoPago = Field(default=EstadoPago.PENDIENTE)


class RentaConDetallesResponse(SQLModel):
    renta: Renta
    detalles: list[DetalleRenta]