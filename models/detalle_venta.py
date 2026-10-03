from sqlmodel import SQLModel, Field
from typing import Optional
from decimal import Decimal

class DetalleVentaBase(SQLModel):
    venta_id: int = Field(foreign_key="ventas.venta_id")
    producto_id: int = Field(foreign_key="productos.producto_id")
    precio_unitario: Decimal = Field(max_digits=10, decimal_places=2)
    cantidad: int = Field(ge=1)
    subtotal: Decimal = Field(max_digits=10, decimal_places=2)

class DetalleVenta(DetalleVentaBase, table=True):
    __tablename__ = "detalle_venta" #type: ignore
    detalle_venta_id: Optional[int] = Field(default=None, primary_key=True)

class DetalleVentaCreate(DetalleVentaBase):
    precio_unitario: Optional[Decimal] = None
    subtotal: Optional[Decimal] = None

class DetalleVentaUpdate(SQLModel):
    cantidad: Optional[int] = None
    precio_unitario: Optional[Decimal] = None
    subtotal: Optional[Decimal] = None