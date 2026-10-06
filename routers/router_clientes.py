from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from config.security_dependencia import Token_Dependencia
from config.session_dependencia import SessionDeDependencia
from models.cliente import Cliente, ClienteCreate, ClienteUpdate
from models.renta import Renta
from models.venta import Venta


ROLES_CON_PERMISO_LECTURA_CLIENTES = {1, 2, 3}
ROLES_CON_PERMISO_GESTION_CLIENTES = {1, 2}
ROLES_CON_PERMISO_ELIMINACION_CLIENTES = {1}

router = APIRouter()


def validar_permisos_lectura(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_LECTURA_CLIENTES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para consultar clientes",
        )


def validar_permisos_gestion(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_GESTION_CLIENTES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para registrar o modificar clientes",
        )


def validar_permisos_eliminacion(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_ELIMINACION_CLIENTES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el administrador puede eliminar clientes",
        )


def obtener_cliente(session: SessionDeDependencia, cliente_id: int) -> Cliente:
    cliente = session.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )
    return cliente


def validar_dui_unico(
    session: SessionDeDependencia,
    dui: str,
    cliente_id: int | None = None,
) -> None:
    consulta = select(Cliente).where(Cliente.dui == dui)
    if cliente_id is not None:
        consulta = consulta.where(Cliente.cliente_id != cliente_id)
    if session.exec(consulta).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un cliente con ese DUI",
        )


def validar_sin_dependencias(session: SessionDeDependencia, cliente_id: int) -> None:
    """Verifica que el cliente no tenga ventas o rentas asociadas antes de eliminarlo."""
    venta_existente = session.exec(
        select(Venta).where(Venta.cliente_id == cliente_id)
    ).first()
    if venta_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar el cliente porque tiene ventas registradas en el sistema",
        )

    renta_existente = session.exec(
        select(Renta).where(Renta.cliente_id == cliente_id)
    ).first()
    if renta_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar el cliente porque tiene rentas registradas en el sistema",
        )


@router.get(
    "/clientes",
    response_model=list[Cliente],
    status_code=status.HTTP_200_OK,
)
async def get_clientes(
    session: SessionDeDependencia,
    token: Token_Dependencia,
    busqueda: str | None = Query(None, description="Buscar por nombre, apellido, DUI o dirección"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1),
):
    validar_permisos_lectura(token)
    consulta = select(Cliente)
    if busqueda:
        termino = f"%{busqueda}%"
        consulta = consulta.where(
            (Cliente.nombre.like(termino)) #type: ignore
            | (Cliente.apellido.like(termino)) #type: ignore
            | (Cliente.dui.like(termino)) #type: ignore
            | (Cliente.direccion.like(termino)) #type: ignore
        )
    return session.exec(consulta.offset(offset).limit(limit)).all()


@router.get(
    "/clientes/{cliente_id}",
    response_model=Cliente,
    status_code=status.HTTP_200_OK,
)
async def get_cliente(
    cliente_id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_lectura(token)
    return obtener_cliente(session, cliente_id)


@router.post(
    "/clientes",
    response_model=Cliente,
    status_code=status.HTTP_201_CREATED,
)
async def create_cliente(
    datos: ClienteCreate,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_gestion(token)
    validar_dui_unico(session, datos.dui)
    cliente = Cliente(**datos.model_dump())
    session.add(cliente)
    session.commit()
    session.refresh(cliente)
    return cliente


@router.put(
    "/clientes/{cliente_id}",
    response_model=Cliente,
    status_code=status.HTTP_200_OK,
)
async def update_cliente(
    cliente_id: int,
    datos: ClienteUpdate,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_gestion(token)
    cliente = obtener_cliente(session, cliente_id)
    validar_dui_unico(session, datos.dui, cliente_id)

    for campo, valor in datos.model_dump().items():
        setattr(cliente, campo, valor)

    session.add(cliente)
    session.commit()
    session.refresh(cliente)
    return cliente


@router.delete(
    "/clientes/{cliente_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_cliente(
    cliente_id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_eliminacion(token)
    cliente = obtener_cliente(session, cliente_id)
    validar_sin_dependencias(session, cliente_id)

    session.delete(cliente)
    session.commit()
    return {"message": "Cliente eliminado exitosamente", "cliente_id": cliente_id}
