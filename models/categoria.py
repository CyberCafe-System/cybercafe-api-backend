from sqlmodel import SQLModel, Field, Column, Enum as SAEnum, Text
from typing import Optional
class CategoriaBase(SQLModel):
    nombre: str = Field(max_length=150)
    descripcion: Optional[str] = Field(default=None, max_length=255)
    activa: bool = Field(default=True)

class Categoria(CategoriaBase, table=True):
    __tablename__ = "categorias" #type: ignore
    categoria_id: Optional[int] = Field(default=None, primary_key=True)

class CategoriaCreate(CategoriaBase):
    pass

class CategoriaUpdate(CategoriaBase):
    pass