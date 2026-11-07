from sqlmodel import SQLModel, Field, Column, Text
from typing import Optional
from datetime import datetime, timezone

def obtener_fecha_utc():
    return datetime.now(timezone.utc)

class NotificacionBase(SQLModel):
    usuario_destino_id: int = Field(foreign_key="usuarios.usuario_id")
    tipo: str = Field(max_length=50)
    detalle_renta_id: int = Field(foreign_key="detalle_renta.detalle_renta_id")
    titulo: str = Field(max_length=150)
    mensaje: str = Field(sa_column=Column(Text))
    creada_en: datetime = Field(default_factory=obtener_fecha_utc)
    leida_en: Optional[datetime] = Field(default=None)

class Notificacion(NotificacionBase, table=True):
    __tablename__ = "notificaciones" #type: ignore
    notificacion_id: Optional[int] = Field(default=None, primary_key=True)

class NotificacionResponse(SQLModel):
    notificacion_id: int
    usuario_destino_id: int
    tipo: str
    detalle_renta_id: int
    titulo: str
    mensaje: str
    creada_en: datetime
    leida_en: Optional[datetime] = None

