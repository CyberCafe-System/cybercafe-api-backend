from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import select

from config.security_dependencia import Token_Dependencia
from config.session_dependencia import SessionDeDependencia
from config.security import get_current_user
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
async def get_equipos(
    session: SessionDeDependencia,
    token: Token_Dependencia,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1),
):
    validar_permisos_lectura(token)
    return session.exec(select(Equipo).offset(offset).limit(limit)).all()
