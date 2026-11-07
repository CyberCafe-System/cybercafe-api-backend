from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlmodel import select

from config.paginacion import paginar_consulta
from config.security_dependencia import Token_Dependencia
from config.session_dependencia import SessionDeDependencia
from models.categoria import Categoria


ROLES_CON_PERMISO_LECTURA_CATEGORIAS = {1, 2, 3}

router = APIRouter()


def validar_permisos_lectura(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_LECTURA_CATEGORIAS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para consultar categorías",
        )


@router.get(
    "/categorias",
    response_model=list[Categoria],
    status_code=status.HTTP_200_OK,
)
def get_categorias(
    response: Response,
    session: SessionDeDependencia,
    token: Token_Dependencia,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=500),
):
    validar_permisos_lectura(token)
    return paginar_consulta(
        session=session,
        response=response,
        consulta=select(Categoria),
        columna_orden=Categoria.categoria_id.asc(),  # type: ignore
        offset=offset,
        limit=limit,
    )
