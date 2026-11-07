from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import select

from config.paginacion import paginar_consulta
from config.security import get_current_user
from config.security_dependencia import Token_Dependencia
from config.session_dependencia import SessionDeDependencia
from models.equipo import Equipo


ROLES_CON_PERMISO_LECTURA_EQUIPOS = {1, 2, 3}

router = APIRouter(dependencies=[Depends(get_current_user)])


def validar_permisos_lectura(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_LECTURA_EQUIPOS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para consultar equipos",
        )


@router.get(
    "/equipos",
    response_model=list[Equipo],
    status_code=status.HTTP_200_OK,
)
def get_equipos(
    response: Response,
    session: SessionDeDependencia,
    token: Token_Dependencia,
    incluir_inactivos: bool = Query(
        False, description="Si es True, incluye equipos desactivados"
    ),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=500),
):
    validar_permisos_lectura(token)
    consulta = select(Equipo)
    if not incluir_inactivos:
        consulta = consulta.where(Equipo.activo == True)  # type: ignore

    return paginar_consulta(
        session=session,
        response=response,
        consulta=consulta,
        columna_orden=Equipo.equipo_id.asc(),  # type: ignore
        offset=offset,
        limit=limit,
    )
