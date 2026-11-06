from sqlmodel import SQLModel, Field, Column
from sqlalchemy.dialects.mysql import JSON
from typing import Optional, Any
from datetime import datetime, timezone

def obtener_fecha_utc():
    return datetime.now(timezone.utc)

class AuditoriaBase(SQLModel):
    usuario_id: int = Field(foreign_key="usuarios.usuario_id")
    fecha: datetime = Field(default_factory=obtener_fecha_utc)
    accion: str = Field(max_length=50)  # CREAR, ACTUALIZAR, ELIMINAR, ESTADO, ANULAR
    entidad: str = Field(max_length=50)  # productos, equipos, usuarios, ventas, etc.
    entidad_id: int
    valor_previo: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    valor_nuevo: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    origen: str = Field(default="API", max_length=10)  # WEB, API
    ip: Optional[str] = Field(default=None, max_length=45)

class Auditoria(AuditoriaBase, table=True):
    __tablename__ = "auditoria" #type: ignore
    auditoria_id: Optional[int] = Field(default=None, primary_key=True)

