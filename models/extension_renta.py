from sqlmodel import SQLModel, Field
from typing import Optional
from decimal import Decimal
from datetime import datetime, timezone

def obtener_fecha_utc():
    return datetime.now(timezone.utc)

class ExtensionRentaBase(SQLModel):
    detalle_renta_id: int = Field(foreign_key="detalle_renta.detalle_renta_id")
    usuario_id: int = Field(foreign_key="usuarios.usuario_id")
    minutos: int = Field(ge=1, le=480)
    costo: Decimal = Field(max_digits=10, decimal_places=2)
    efectivo_recibido: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=2)
    cambio: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=2)
    clave_idempotencia: Optional[str] = Field(default=None, max_length=32)
    fecha: datetime = Field(default_factory=obtener_fecha_utc)

class ExtensionRenta(ExtensionRentaBase, table=True):
    __tablename__ = "extensiones_renta" #type: ignore
    extension_id: Optional[int] = Field(default=None, primary_key=True)

