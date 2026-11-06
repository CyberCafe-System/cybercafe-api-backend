from sqlmodel import SQLModel, Field, Column, Text
from typing import Optional

class RevisionComponenteBase(SQLModel):
    revision_equipo_id: int = Field(foreign_key="revisiones_equipo.revision_equipo_id")
    componente_id: int = Field(foreign_key="componentes.componente_id")
    estado_previo: str = Field(max_length=50)
    estado_nuevo: str = Field(max_length=50)
    descripcion: Optional[str] = Field(default=None, sa_column=Column(Text))

class RevisionComponente(RevisionComponenteBase, table=True):
    __tablename__ = "revision_componentes" #type: ignore
    id: Optional[int] = Field(default=None, primary_key=True)

