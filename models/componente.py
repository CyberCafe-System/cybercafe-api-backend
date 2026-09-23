from sqlmodel import SQLModel, Field, Column, Enum as SAEnum, Text
from typing import Optional
from enum import Enum


class TipoComponente(str, Enum):
    MOUSE = "Mouse"
    TECLADO = "Teclado"
    MONITOR = "Monitor"
    CONTROL = "Control"

class EstadoComponente(str, Enum):
    DISPONIBLE = "Disponible"
    DANIOS_MENORES = "Daños menores"
    REQUIERE_REEMPLAZO = "Requiere reemplazo"

class ComponenteBase(SQLModel):
    equipo_id: Optional[int] = Field(default=None, foreign_key="equipos.id")
    nombre: str = Field(nullable=False, min_length=3, max_length=255)
    tipo: TipoComponente = Field(sa_column=Column(SAEnum(TipoComponente)))
    estado: EstadoComponente = Field(sa_column=Column(SAEnum(EstadoComponente)))
    descripcion: Optional[Text] = Field(default=None, sa_column=Column(Text))
    observaciones: Optional[Text] = Field(default=None, sa_column=Column(Text))
    imagen: Optional[str] = Field(default=None, max_length=255)
    activo: bool = Field(default=True)

class Componente(ComponenteBase, table=True):
    __tablename__ = "tareas" #type: ignore
    componente_id: int|None = Field(default=None, primary_key=True)

class ComponenteCreate(ComponenteBase):
    pass
class ComponenteUpdate(ComponenteBase):
    pass