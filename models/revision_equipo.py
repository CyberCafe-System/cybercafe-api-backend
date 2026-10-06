from sqlmodel import SQLModel, Field, Column, Enum as SAEnum, Text
from typing import Optional
from enum import Enum
from decimal import Decimal
from datetime import datetime, timezone

def obtener_fecha_utc():
    return datetime.now(timezone.utc)

class RevisionEquipoBase(SQLModel):
    detalle_renta_id: int = Field(foreign_key="detalle_renta.detalle_renta_id")
    usuario_id: int = Field(foreign_key="usuarios.usuario_id")
    inspeccion_pasada: bool
    observaciones: str = Field(sa_column=Column(Text))
    fecha_revision: datetime = Field(default_factory=obtener_fecha_utc)

class RevisionEquipo(RevisionEquipoBase, table=True):
    __tablename__ = "revisiones_equipo" #type:ignore
    revision_equipo_id: Optional[int] = Field(default=None, primary_key=True)

class RevisionEquipoCreate(RevisionEquipoBase):
    usuario_id: Optional[int] = None #type: ignore

class RevisionEquipoUpdate(SQLModel):
    inspeccion_pasada: Optional[bool] = None
    observaciones: Optional[str] = None