from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlmodel import select

from config.paginacion import paginar_consulta
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
def get_productos(
    response: Response,
    session: SessionDeDependencia,
    token: Token_Dependencia,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=500),
):
    validar_permisos_productos(token)
    return paginar_consulta(
        session=session,
        response=response,
        consulta=select(Producto),
        columna_orden=Producto.producto_id.asc(),  # type: ignore
        offset=offset,
        limit=limit,
    )
