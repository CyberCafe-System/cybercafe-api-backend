from datetime import datetime
from sqlmodel import SQLModel, Field
from typing import Optional
from pydantic import EmailStr


class UsuarioBase(SQLModel):
    rol_id: int = Field(foreign_key="roles.rol_id")
    nombre: str = Field(min_length=3, max_length=255)
    username: str = Field(max_length=100)
    correo: EmailStr = Field(max_length=255)
    password: str = Field(max_length=255)
    is_superuser: bool = Field(default=False)
    last_login: Optional[datetime] = Field(default=None)
    activo: bool = Field(default=True)

class Usuario(UsuarioBase, table=True):
    __tablename__ = "usuarios" #type: ignore
    usuario_id: Optional[int] = Field(default=None, primary_key=True)

class UsuarioCreate(UsuarioBase):
    is_superuser: Optional[bool] = None

class UsuarioUpdate(SQLModel):
    rol_id: Optional[int] = None
    nombre: Optional[str] = None
    username: Optional[str] = None
    correo: Optional[EmailStr] = None
    password: Optional[str] = None
    is_superuser: Optional[bool] = None
    activo: Optional[bool] = None