from sqlmodel import SQLModel, Field
from typing import Optional
from decimal import Decimal
from datetime import datetime, timezone
from models.detalle_venta import DetalleVenta

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
    usuario_id: Optional[int] = None #type: ignore
    iva: Optional[Decimal] = None #type: ignore
    subtotal: Optional[Decimal] = None #type: ignore

class VentaUpdate(SQLModel):
    cliente_id: Optional[int] = None
    iva: Optional[Decimal] = None
    subtotal: Optional[Decimal] = None


class ItemVentaRequest(SQLModel):
    producto_id: int
    cantidad: int = Field(ge=1, description="Cantidad a comprar")
    precio_unitario: Optional[Decimal] = Field(
        default=None, description="Precio unitario (si se omite, se usa el precio_venta del producto)"
    )


class RegistrarVentaRequest(SQLModel):
    cliente_id: int
    productos: list[ItemVentaRequest] = Field(
        min_length=1, description="Lista de productos y cantidades a comprar"
    )
    tasa_iva: Decimal = Field(
        default=Decimal("0.13"), description="Tasa de IVA aplicada (por defecto 0.13 = 13%)"
    )


class VentaConDetallesResponse(SQLModel):
    venta: Venta
    detalles: list[DetalleVenta]
    total: Decimal