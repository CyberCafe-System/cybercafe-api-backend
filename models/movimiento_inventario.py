from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone

def obtener_fecha_utc():
    return datetime.now(timezone.utc)

class MovimientoInventarioBase(SQLModel):
    producto_id: int = Field(foreign_key="productos.producto_id")
    usuario_id: int = Field(foreign_key="usuarios.usuario_id")
    tipo: str = Field(max_length=50)  # VENTA, AJUSTE, ENTRADA, ANULACION
    delta: int
    stock_resultante: int
    motivo: str = Field(max_length=255)
    referencia_id: Optional[int] = Field(default=None)
    fecha: datetime = Field(default_factory=obtener_fecha_utc)

class MovimientoInventario(MovimientoInventarioBase, table=True):
    __tablename__ = "movimientos_inventario" #type: ignore
    movimiento_id: Optional[int] = Field(default=None, primary_key=True)

