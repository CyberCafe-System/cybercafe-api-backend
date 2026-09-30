from sqlmodel import SQLModel, Field
from typing import Optional
from decimal import Decimal

class ProductoBase(SQLModel):
    categoria_id: int = Field(foreign_key="categorias.categoria_id")
    nombre: str = Field(max_length=255)
    precio_compra: Decimal = Field(max_digits=10, decimal_places=2)
    precio_venta: Decimal = Field(max_digits=10, decimal_places=2)
    cantidad: int
    imagen: Optional[str] = Field(default=None, max_length=255)
    activo: bool = Field(default=True)

class Producto(ProductoBase, table=True):
    __tablename__ = "productos" #type: ignore
    producto_id: Optional[int] = Field(default=None, primary_key=True)

class ProductoCreate(ProductoBase):
    pass

class ProductoUpdate(SQLModel):
    categoria_id: Optional[int] = Field(default=None, foreign_key="categorias.categoria_id")
    nombre: Optional[str] = Field(default=None, max_length=255)
    precio_compra: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=2)
    precio_venta: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=2)
    cantidad: Optional[int] = None
    imagen: Optional[str] = Field(default=None, max_length=255)
    activo: Optional[bool] = None