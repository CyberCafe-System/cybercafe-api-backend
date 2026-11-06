from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select, or_

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
    busqueda: str | None = Query(None, description="Buscar por nombre, apellido o DUI"),
    activo: bool | None = Query(None, description="Filtrar por estado activo"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    validar_permisos_lectura(token)
    consulta = select(Cliente)
    if activo is not None:
        consulta = consulta.where(Cliente.activo == activo)
    if busqueda:
        termino = f"%{busqueda}%"
        consulta = consulta.where(
            or_(
                Cliente.nombre.like(termino),  # type: ignore
                Cliente.apellido.like(termino),  # type: ignore
                Cliente.dui.like(termino),  # type: ignore
            )
        )
    return session.exec(consulta.offset(offset).limit(limit)).all()


@router.get(
    "/clientes/buscar",
    status_code=status.HTTP_200_OK,
)
async def buscar_clientes_autocompletado(
    session: SessionDeDependencia,
    token: Token_Dependencia,
    q: str = Query(..., min_length=2, description="Término de búsqueda (mínimo 2 caracteres)"),
    limit: int = Query(10, ge=1, le=50),
):
    """Búsqueda ligera y rápida para autocompletado en POS y Rentas."""
    validar_permisos_lectura(token)
    termino = f"%{q.strip()}%"
    consulta = (
        select(Cliente)
        .where(
            Cliente.activo == True,  # type: ignore
            or_(
                Cliente.nombre.like(termino),  # type: ignore
                Cliente.apellido.like(termino),  # type: ignore
                Cliente.dui.like(termino),  # type: ignore
                Cliente.telefono.like(termino),  # type: ignore
            ),
        )
        .limit(limit)
    )
    clientes = session.exec(consulta).all()
    return [
        {
            "id": c.cliente_id,
            "nombre": f"{c.nombre} {c.apellido}",
            "dui": c.dui,
            "telefono": c.telefono,
            "correo": c.correo or "",
            "tiene_correo": bool(c.correo),
        }
        for c in clientes
    ]
