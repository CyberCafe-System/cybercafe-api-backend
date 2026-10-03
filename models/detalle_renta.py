from sqlmodel import SQLModel, Field, Column, Enum as SAEnum
from typing import Optional
from enum import Enum
from decimal import Decimal
from datetime import datetime

class EstadoRenta(str, Enum):
    ACTIVA = "Activa"
    FINALIZADA = "Finalizada"
    PENDIENTE_REVISION = "Pendiente Revision"

class DetalleRentaBase(SQLModel):
    renta_id: int = Field(foreign_key="rentas.renta_id")
    equipo_id: int = Field(foreign_key="equipos.equipo_id")
    hora_inicio: datetime
    tiempo_de_renta: int
    tiempo_agregado: Optional[int] = Field(default=None)
    hora_fin: Optional[datetime] = Field(default=None)
    subtotal: Decimal = Field(max_digits=10, decimal_places=2)
    estado: EstadoRenta = Field(sa_column=Column(SAEnum(EstadoRenta)))

class DetalleRenta(DetalleRentaBase, table=True):
    __tablename__ = "detalle_renta" #type: ignore
    detalle_renta_id: Optional[int] = Field(default=None, primary_key=True)

class DetalleRentaCreate(DetalleRentaBase):
    hora_inicio: Optional[datetime] = None
    subtotal: Optional[Decimal] = None
    estado: Optional[EstadoRenta] = EstadoRenta.ACTIVA

class DetalleRentaUpdate(SQLModel):
    tiempo_agregado: Optional[int] = None
    hora_fin: Optional[datetime] = None
    subtotal: Optional[Decimal] = None
    estado: Optional[EstadoRenta] = None