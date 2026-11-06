from sqlmodel import SQLModel, Field
from typing import Optional

class ClienteBase(SQLModel):
    nombre: str = Field(nullable=False, max_length=255)
    apellido: str = Field(nullable=False, max_length=255)
    dui: str = Field(nullable=False, max_length=10)
    direccion: str = Field(nullable=False, max_length=255)
    telefono: int = Field(nullable=False, ge=10000000, le=99999999)
    correo: Optional[str] = Field(nullable=True, default=None, max_length=255)
    activo: bool = Field(default=True)

class Cliente(ClienteBase, table=True):
    __tablename__ = "clientes" #type: ignore
    cliente_id: Optional[int] = Field(default=None, primary_key=True)

class ClienteCreate(ClienteBase):
    pass

class ClienteUpdate(SQLModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    dui: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[int] = None
    correo: Optional[str] = None
    activo: Optional[bool] = None
