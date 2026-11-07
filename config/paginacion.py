from typing import Any, Sequence
from fastapi import Response
from sqlalchemy import func
from sqlmodel import Session, select


def paginar_consulta(
    session: Session,
    response: Response,
    consulta: Any,
    columna_orden: Any,
    offset: int = 0,
    limit: int = 20,
) -> Sequence[Any]:
    """
    Aplica conteo total (cabecera X-Total-Count), ordenamiento determinista y
    paginación offset/limit sobre una consulta SQLModel/SQLAlchemy.
    """
    conteo_stmt = select(func.count()).select_from(consulta.subquery())
    total = session.exec(conteo_stmt).one()
    total_int = int(total[0] if isinstance(total, tuple) else total)
    response.headers["X-Total-Count"] = str(total_int)

    if isinstance(columna_orden, (list, tuple)):
        consulta_ordenada = consulta.order_by(*columna_orden)
    else:
        consulta_ordenada = consulta.order_by(columna_orden)

    return session.exec(consulta_ordenada.offset(offset).limit(limit)).all()

