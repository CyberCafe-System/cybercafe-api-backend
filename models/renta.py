from sqlmodel import SQLModel, Field, Column, Enum as SAEnum, Text
from typing import Optional
from enum import Enum
from decimal import Decimal
from datetime import datetime, timezone

class EstadoPago(str, Enum):
    PENDIENTE = "Pendiente"
    PAGADO = "Pagado"

class EstadoRenta(str, Enum):
    ACTIVA = "Activa"
    FINALIZADA = "Finalizada"
    PENDIENTE_REVISION = "Pendiente Revision"

def obtener_fecha_utc():
    return datetime.now(timezone.utc)

class RentaBase(SQLModel):
    usuario_id: int = Field(foreign_key="usuarios.usuario_id")
    cliente_id: int = Field(foreign_key="clientes.cliente_id") # En la imagen es NOT NULL
    fecha: datetime = Field(default_factory=obtener_fecha_utc)
    total: Decimal = Field(max_digits=10, decimal_places=2)
    estado_de_pago: EstadoPago = Field(sa_column=Column(SAEnum(EstadoPago)))

class Renta(RentaBase, table=True):
    __tablename__ = "rentas" #type: ignore
    renta_id: Optional[int] = Field(default=None, primary_key=True)

class RentaCreate(RentaBase):
    pass

class RentaUpdate(RentaBase):
    pass