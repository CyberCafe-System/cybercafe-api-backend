from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import  select
from config.session_dependencia import SessionDeDependencia
from librerias.pwd import get_password_hash
from models.usuario import Usuario, UsuarioCreate, UsuarioUpdate
from models.rol import Rol, RolCreate, RolUpdate



router = APIRouter()
#listar usuarios
@router.get("/usuarios", response_model=list[Usuario], status_code=status.HTTP_200_OK)
async def get_categorias(session: SessionDeDependencia, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1)):
   return session.exec(select(Usuario).offset(offset).limit(limit)).all()

#buscar usuario por id

#crear usuario
@router.post("/usuarios", response_model=Usuario, status_code=status.HTTP_201_CREATED)
async def create_usuario(datos: UsuarioCreate, session: SessionDeDependencia):
    if session.exec(select(Usuario).where(Usuario.username == datos.username)).first():
        raise HTTPException(status_code=400, detail="El usuario ya esta en uso")
   
    usuario = Usuario(**datos.model_dump())
    usuario.password_hash = get_password_hash(datos.password_hash)
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario