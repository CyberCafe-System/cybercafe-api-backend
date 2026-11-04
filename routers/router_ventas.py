from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from config.security_dependencia import Token_Dependencia
from config.session_dependencia import SessionDeDependencia
from models.detalle_venta import DetalleVenta
from models.venta import (
    Venta,
    VentaConDetallesResponse,
)


ROLES_CON_PERMISO_VENTAS = {1, 2}

router = APIRouter()


def validar_permisos_ventas(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_VENTAS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para realizar o consultar ventas",
        )


def obtener_venta(session: SessionDeDependencia, venta_id: int) -> Venta:
    venta = session.get(Venta, venta_id)
    if not venta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"La venta con ID {venta_id} no fue encontrada",
        )
    return venta


@router.get(
    "/ventas",
    response_model=list[Venta],
    status_code=status.HTTP_200_OK,
)
async def get_ventas(
    session: SessionDeDependencia,
    token: Token_Dependencia,
    cliente_id: int | None = Query(None, description="Filtrar ventas por cliente"),
    usuario_id: int | None = Query(None, description="Filtrar ventas por cajero/usuario"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1),
):
    validar_permisos_ventas(token)
    consulta = select(Venta)

    if cliente_id is not None:
        consulta = consulta.where(Venta.cliente_id == cliente_id)
    if usuario_id is not None:
        consulta = consulta.where(Venta.usuario_id == usuario_id)

    return session.exec(consulta.offset(offset).limit(limit)).all()


@router.get(
    "/ventas/{venta_id}",
    response_model=VentaConDetallesResponse,
    status_code=status.HTTP_200_OK,
)
async def get_venta(
    venta_id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    """Consulta la venta con sus productos asociados y cálculo del total."""
    validar_permisos_ventas(token)
    venta = obtener_venta(session, venta_id)
    detalles = session.exec(
        select(DetalleVenta).where(DetalleVenta.venta_id == venta_id)
    ).all()
    total = venta.subtotal + venta.iva
    return VentaConDetallesResponse(venta=venta, detalles=detalles, total=total) #type: ignore
