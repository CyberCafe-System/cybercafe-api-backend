from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from config.security_dependencia import Token_Dependencia
from config.session_dependencia import SessionDeDependencia
from models.producto import Producto


ROLES_CON_PERMISO_PRODUCTOS = {1}

router = APIRouter()


def validar_permisos_productos(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_PRODUCTOS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para realizar esta operación",
        )


@router.get(
    "/productos",
    response_model=list[Producto],
    status_code=status.HTTP_200_OK,
)
async def get_productos(
    session: SessionDeDependencia,
    token: Token_Dependencia,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1),
):
    validar_permisos_productos(token)
    return session.exec(select(Producto).offset(offset).limit(limit)).all()
