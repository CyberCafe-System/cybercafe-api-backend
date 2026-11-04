from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from config.security_dependencia import Token_Dependencia
from config.session_dependencia import SessionDeDependencia
from models.cliente import Cliente


ROLES_CON_PERMISO_LECTURA_CLIENTES = {1, 2, 3}

router = APIRouter()


def validar_permisos_lectura(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_LECTURA_CLIENTES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para consultar clientes",
        )


@router.get(
    "/clientes",
    response_model=list[Cliente],
    status_code=status.HTTP_200_OK,
)
async def get_clientes(
    session: SessionDeDependencia,
    token: Token_Dependencia,
    busqueda: str | None = Query(None, description="Buscar por nombre, apellido, DUI o dirección"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1),
):
    validar_permisos_lectura(token)
    consulta = select(Cliente)
    if busqueda:
        termino = f"%{busqueda}%"
        consulta = consulta.where(
            (Cliente.nombre.like(termino)) #type: ignore
            | (Cliente.apellido.like(termino)) #type: ignore
            | (Cliente.dui.like(termino)) #type: ignore
            | (Cliente.direccion.like(termino)) #type: ignore
        )
    return session.exec(consulta.offset(offset).limit(limit)).all()
