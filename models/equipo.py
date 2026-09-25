from sqlmodel import SQLModel, Field, Column, Enum as SAEnum, Text
from typing import Optional
from enum import Enum
from decimal import Decimal

class TipoEquipo(Enum, str):
    PC = "PC"
    CONSOLA = "Consola"

class EstadoEquipo(Enum, str):
    DISPONIBLE = "Disponible"
    DANIOS_MENORES = 'Daños menores'
    DEFECTUOSO = 'Defectuoso'
    EN_MANTENIMIENTO = 'En mantenimiento'

class EquipoBase(SQLModel):
    nombre: str = Field(nullable=False, min_length=3, max_length=255)
    descripcion: Text = Field(nullable=True)
    tarifa_por_hora: Decimal = Field(max_digits=10, decimal_places=2)
    imagen: Optional[str] = Field(default=None, max_length=255)
    tipo: TipoEquipo = Field(sa_column=Column(SAEnum(TipoEquipo)))
    estado: EstadoEquipo = Field(sa_column=Column(SAEnum(EstadoEquipo)))


class Equipo(EquipoBase, table=True):
    __tablename__ = "equipos" #type:ignore
    equipo_id: Optional[int] = Field(default=None, primary_key=True)

class EquipoCreate(EquipoBase):
    pass

class EquipoUpdate(EquipoBase):
    pass
