from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import Field, SQLModel, select

from config.security_dependencia import Token_Dependencia
from config.session_dependencia import SessionDeDependencia
from models.cliente import Cliente
from models.detalle_venta import DetalleVenta, DetalleVentaCreate, DetalleVentaUpdate
from models.producto import Producto
from models.usuario import Usuario
from models.venta import (
    ItemVentaRequest,
    RegistrarVentaRequest,
    Venta,
    VentaConDetallesResponse,
    VentaCreate,
    VentaUpdate,
)


ROLES_CON_PERMISO_VENTAS = {1, 2}
ROLES_CON_PERMISO_ELIMINACION_VENTAS = {1}

router = APIRouter()


def validar_permisos_ventas(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_VENTAS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para realizar o consultar ventas",
        )


def validar_permisos_eliminacion(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_ELIMINACION_VENTAS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el administrador puede anular o eliminar ventas",
        )


def obtener_venta(session: SessionDeDependencia, venta_id: int) -> Venta:
    venta = session.get(Venta, venta_id)
    if not venta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"La venta con ID {venta_id} no fue encontrada",
        )
    return venta


def obtener_detalle_venta(
    session: SessionDeDependencia, detalle_venta_id: int
) -> DetalleVenta:
    detalle = session.get(DetalleVenta, detalle_venta_id)
    if not detalle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El detalle de venta con ID {detalle_venta_id} no fue encontrado",
        )
    return detalle


def validar_cliente(session: SessionDeDependencia, cliente_id: int) -> Cliente:
    cliente = session.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El cliente con ID {cliente_id} no existe",
        )
    return cliente


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
    return VentaConDetallesResponse(venta=venta, detalles=detalles, total=total)


@router.get(
    "/ventas/{venta_id}/detalles",
    response_model=list[DetalleVenta],
    status_code=status.HTTP_200_OK,
)
async def get_detalles_de_venta(
    venta_id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    """Lista las líneas de detalle de una venta específica."""
    validar_permisos_ventas(token)
    obtener_venta(session, venta_id)
    return session.exec(
        select(DetalleVenta).where(DetalleVenta.venta_id == venta_id)
    ).all()


@router.post(
    "/ventas",
    response_model=VentaConDetallesResponse,
    status_code=status.HTTP_201_CREATED,
)
async def registrar_venta(
    datos: RegistrarVentaRequest,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    """
    Registra una venta transaccional en el Punto de Venta (POS):
    - Valida existencia del cliente.
    - Asigna el cajero/usuario autenticado desde el token JWT.
    - Para cada producto: valida existencia, estado activo y disponibilidad de stock.
    - Descuenta automáticamente el inventario del producto.
    - Calcula subtotales, IVA y total de la venta.
    - Guarda la Venta y los DetalleVenta en una sola transacción atómica.
    """
    validar_permisos_ventas(token)

    # 1. Validar cliente y usuario
    validar_cliente(session, datos.cliente_id)
    usuario_id = token.get("id")

    subtotal_general = Decimal("0.00")
    items_preparados: list[dict] = []

    # 2. Validar cada producto y verificar stock antes de realizar cambios
    for item in datos.productos:
        producto = session.get(Producto, item.producto_id)
        if not producto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El producto con ID {item.producto_id} no existe",
            )
        if not producto.activo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El producto '{producto.nombre}' se encuentra inactivo y no se puede vender",
            )
        if producto.cantidad < item.cantidad:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stock insuficiente para '{producto.nombre}'. Disponible: {producto.cantidad}, solicitado: {item.cantidad}",
            )

        precio_unitario = (
            item.precio_unitario
            if item.precio_unitario is not None
            else producto.precio_venta
        )
        subtotal_item = Decimal(
            round(float(precio_unitario * Decimal(item.cantidad)), 2)
        )
        subtotal_general += subtotal_item

        # Descontar stock del producto
        producto.cantidad -= item.cantidad
        session.add(producto)

        items_preparados.append(
            {
                "producto_id": item.producto_id,
                "precio_unitario": precio_unitario,
                "cantidad": item.cantidad,
                "subtotal": subtotal_item,
            }
        )

    # 3. Calcular IVA y crear cabecera de Venta
    iva_calculado = Decimal(
        round(float(subtotal_general * datos.tasa_iva), 2)
    )
    ahora = datetime.now(timezone.utc)

    venta = Venta(
        cliente_id=datos.cliente_id,
        usuario_id=usuario_id,
        fecha=ahora,
        subtotal=subtotal_general,
        iva=iva_calculado,
    )
    session.add(venta)
    session.flush()  # Genera venta_id

    # 4. Crear los detalles de venta vinculados
    detalles_guardados: list[DetalleVenta] = []
    for item_data in items_preparados:
        detalle = DetalleVenta(
            venta_id=venta.venta_id,
            producto_id=item_data["producto_id"],
            precio_unitario=item_data["precio_unitario"],
            cantidad=item_data["cantidad"],
            subtotal=item_data["subtotal"],
        )
        session.add(detalle)
        detalles_guardados.append(detalle)

    session.commit()
    session.refresh(venta)
    for det in detalles_guardados:
        session.refresh(det)

    total_general = venta.subtotal + venta.iva
    return VentaConDetallesResponse(
        venta=venta, detalles=detalles_guardados, total=total_general
    )


@router.get(
    "/detalles-venta",
    response_model=list[DetalleVenta],
    status_code=status.HTTP_200_OK,
)
async def get_detalles_venta(
    session: SessionDeDependencia,
    token: Token_Dependencia,
    venta_id: int | None = Query(None, description="Filtrar por ID de venta"),
    producto_id: int | None = Query(None, description="Filtrar por ID de producto"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1),
):
    validar_permisos_ventas(token)
    consulta = select(DetalleVenta)

    if venta_id is not None:
        consulta = consulta.where(DetalleVenta.venta_id == venta_id)
    if producto_id is not None:
        consulta = consulta.where(DetalleVenta.producto_id == producto_id)

    return session.exec(consulta.offset(offset).limit(limit)).all()


@router.get(
    "/detalles-venta/{detalle_venta_id}",
    response_model=DetalleVenta,
    status_code=status.HTTP_200_OK,
)
async def get_detalle_venta(
    detalle_venta_id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_ventas(token)
    return obtener_detalle_venta(session, detalle_venta_id)


@router.delete(
    "/ventas/{venta_id}",
    status_code=status.HTTP_200_OK,
)
async def anular_venta(
    venta_id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
    reponer_stock: bool = Query(
        True,
        description="Si es True, devuelve las cantidades vendidas al stock de productos",
    ),
):
    """
    Anula / elimina una venta del sistema (solo Admin):
    - Opcionalmente restituye las cantidades vendidas al inventario de productos.
    - Elimina los detalles y la venta asociada.
    """
    validar_permisos_eliminacion(token)
    venta = obtener_venta(session, venta_id)

    detalles = session.exec(
        select(DetalleVenta).where(DetalleVenta.venta_id == venta_id)
    ).all()

    if reponer_stock:
        for detalle in detalles:
            producto = session.get(Producto, detalle.producto_id)
            if producto:
                producto.cantidad += detalle.cantidad
                session.add(producto)

    for detalle in detalles:
        session.delete(detalle)
    session.delete(venta)

    session.commit()
    return {
        "message": "Venta anulada exitosamente",
        "venta_id": venta_id,
        "stock_repuesto": reponer_stock,
    }
