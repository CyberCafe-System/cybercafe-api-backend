from sqlmodel import SQLModel, Field
from typing import Optional
from decimal import Decimal
from datetime import datetime, timezone

def obtener_fecha_utc():
    return datetime.now(timezone.utc)

class VentaBase(SQLModel):
    cliente_id: int = Field(foreign_key="clientes.cliente_id") # En la imagen es NOT NULL
    usuario_id: int = Field(foreign_key="usuarios.usuario_id")
    fecha: datetime = Field(default_factory=obtener_fecha_utc)
    iva: Decimal = Field(max_digits=10, decimal_places=2)
    subtotal: Decimal = Field(max_digits=10, decimal_places=2)


class Venta(VentaBase, table=True):
    __tablename__ = "ventas" #type: ignore
    venta_id: Optional[int] = Field(default=None, primary_key=True)

class VentaCreate(VentaBase):
    pass

class VentaUpdate(VentaBase):
    pass