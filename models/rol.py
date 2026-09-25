from sqlmodel import SQLModel, Field
from typing import Optional

class RolBase(SQLModel):
    nombre: str = Field(max_length=255)
    descripcion: Optional[str] = Field(default=None, max_length=255)

class Rol(RolBase, table=True):
    __tablename__ = "roles" #type: ignore
    rol_id: Optional[int] = Field(default=None, primary_key=True)

class RolCreate(RolBase):
    pass

class RolUpdate(RolBase):
    pass