from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import  select
from config.session_dependencia import SessionDeDependencia
from config.security_dependencia import Token_Dependencia
from librerias.pwd import get_password_hash
from models.usuario import Usuario, UsuarioCreate, UsuarioUpdate
from models.rol import Rol, RolCreate, RolUpdate

def validar_rol_autorizado(token: dict) -> None:
    if token.get("id_rol") not in (1, 2):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Rol no autorizado")


def validar_acceso_usuario(token: dict, id: int) -> None:
    validar_rol_autorizado(token)
    if token.get("id_rol") == 2 and token.get("id") != id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="El Vendedor solo puede consultar o actualizar su propio usuario")


def validar_rol(session: SessionDeDependencia, id_rol: int) -> None:
    if not session.get(Rol, id_rol):
        raise HTTPException(status_code=404, detail="Rol no encontrado")

router = APIRouter()
#listar usuarios
@router.get("/usuarios", response_model=list[Usuario], status_code=status.HTTP_200_OK)
async def get_categorias(session: SessionDeDependencia, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1)):
   return session.exec(select(Usuario).offset(offset).limit(limit)).all()

#buscar usuario por id
@router.get("/usuarios/{id}", response_model=Usuario, status_code=status.HTTP_200_OK)
async def get_usuario(id: int, session: SessionDeDependencia, token: Token_Dependencia):
    validar_acceso_usuario(token, id)
    usuario = session.get(Usuario, id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario

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