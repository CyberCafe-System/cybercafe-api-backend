from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from config.security_dependencia import Token_Dependencia
from config.session_dependencia import SessionDeDependencia
from models.categoria import Categoria
from models.producto import Producto, ProductoCreate, ProductoUpdate


ROLES_CON_PERMISO_PRODUCTOS = {1}

router = APIRouter()


def validar_permisos_productos(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_PRODUCTOS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para realizar esta operación",
        )


def validar_categoria(session: SessionDeDependencia, categoria_id: int) -> None:
    if not session.get(Categoria, categoria_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada")


def obtener_producto(session: SessionDeDependencia, producto_id: int) -> Producto:
    producto = session.get(Producto, producto_id)
    if not producto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    return producto


def validar_datos_parciales(datos: ProductoUpdate) -> None:
    if any(valor is None for valor in datos.model_dump(exclude_unset=True).values()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Los campos del producto no pueden ser nulos",
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


@router.get(
    "/productos/{producto_id}",
    response_model=Producto,
    status_code=status.HTTP_200_OK,
)
async def get_producto(
    producto_id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_productos(token)
    return obtener_producto(session, producto_id)


@router.post(
    "/productos",
    response_model=Producto,
    status_code=status.HTTP_201_CREATED,
)
async def create_producto(
    datos: ProductoCreate,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_productos(token)
    validar_categoria(session, datos.categoria_id)
    producto = Producto(**datos.model_dump())
    session.add(producto)
    session.commit()
    session.refresh(producto)
    return producto


@router.put(
    "/productos/{producto_id}",
    response_model=Producto,
    status_code=status.HTTP_200_OK,
)
async def update_producto(
    producto_id: int,
    datos: ProductoCreate,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_productos(token)
    producto = obtener_producto(session, producto_id)
    validar_categoria(session, datos.categoria_id)

    for campo, valor in datos.model_dump().items():
        setattr(producto, campo, valor)

    session.add(producto)
    session.commit()
    session.refresh(producto)
    return producto


@router.patch(
    "/productos/{producto_id}",
    response_model=Producto,
    status_code=status.HTTP_200_OK,
)
async def patch_producto(
    producto_id: int,
    datos: ProductoUpdate,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_productos(token)
    producto = obtener_producto(session, producto_id)
    datos_actualizados = datos.model_dump(exclude_unset=True)
    validar_datos_parciales(datos)

    if "categoria_id" in datos_actualizados:
        validar_categoria(session, datos_actualizados["categoria_id"])

    for campo, valor in datos_actualizados.items():
        setattr(producto, campo, valor)

    session.add(producto)
    session.commit()
    session.refresh(producto)
    return producto


@router.delete(
    "/productos/{producto_id}",
    response_model=Producto,
    status_code=status.HTTP_200_OK,
)
async def eliminar_producto(
    producto_id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_productos(token)
    producto = obtener_producto(session, producto_id)
    producto.activo = False
    session.add(producto)
    session.commit()
    session.refresh(producto)
    return producto