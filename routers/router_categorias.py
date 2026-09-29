from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from config.security_dependencia import Token_Dependencia
from config.session_dependencia import SessionDeDependencia
from models.categoria import Categoria, CategoriaCreate, CategoriaUpdate


ROLES_CON_PERMISO_GESTION_CATEGORIAS = {1}
ROLES_CON_PERMISO_LECTURA_CATEGORIAS = {1, 2, 3}

router = APIRouter()


def validar_permisos_lectura(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_LECTURA_CATEGORIAS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para consultar categorías",
        )


def validar_permisos_gestion(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_GESTION_CATEGORIAS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el administrador puede gestionar categorías",
        )


def validar_nombre_unico(
    session: SessionDeDependencia,
    nombre: str,
    categoria_id: int | None = None,
) -> None:
    consulta = select(Categoria).where(Categoria.nombre == nombre)
    if categoria_id is not None:
        consulta = consulta.where(Categoria.categoria_id != categoria_id)
    if session.exec(consulta).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una categoría con ese nombre",
        )


def obtener_categoria(session: SessionDeDependencia, categoria_id: int) -> Categoria:
    categoria = session.get(Categoria, categoria_id)
    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada",
        )
    return categoria


@router.get(
    "/categorias",
    response_model=list[Categoria],
    status_code=status.HTTP_200_OK,
)
async def get_categorias(
    session: SessionDeDependencia,
    token: Token_Dependencia,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1),
):
    validar_permisos_lectura(token)
    return session.exec(select(Categoria).offset(offset).limit(limit)).all()


@router.get(
    "/categorias/{categoria_id}",
    response_model=Categoria,
    status_code=status.HTTP_200_OK,
)
async def get_categoria(
    categoria_id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_lectura(token)
    return obtener_categoria(session, categoria_id)


@router.post(
    "/categorias",
    response_model=Categoria,
    status_code=status.HTTP_201_CREATED,
)
async def create_categoria(
    datos: CategoriaCreate,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_gestion(token)
    validar_nombre_unico(session, datos.nombre)
    categoria = Categoria(**datos.model_dump())
    session.add(categoria)
    session.commit()
    session.refresh(categoria)
    return categoria


@router.put(
    "/categorias/{categoria_id}",
    response_model=Categoria,
    status_code=status.HTTP_200_OK,
)
async def update_categoria(
    categoria_id: int,
    datos: CategoriaCreate,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_gestion(token)
    categoria = obtener_categoria(session, categoria_id)
    validar_nombre_unico(session, datos.nombre, categoria_id)

    for campo, valor in datos.model_dump().items():
        setattr(categoria, campo, valor)

    session.add(categoria)
    session.commit()
    session.refresh(categoria)
    return categoria


@router.patch(
    "/categorias/{categoria_id}",
    response_model=Categoria,
    status_code=status.HTTP_200_OK,
)
async def patch_categoria(
    categoria_id: int,
    datos: CategoriaUpdate,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_gestion(token)
    categoria = obtener_categoria(session, categoria_id)
    datos_actualizados = datos.model_dump(exclude_unset=True)

    for campo in ("nombre", "activa"):
        if campo in datos_actualizados and datos_actualizados[campo] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"El campo {campo} no puede ser nulo",
            )

    if "nombre" in datos_actualizados:
        validar_nombre_unico(session, datos_actualizados["nombre"], categoria_id)

    for campo, valor in datos_actualizados.items():
        setattr(categoria, campo, valor)

    session.add(categoria)
    session.commit()
    session.refresh(categoria)
    return categoria


@router.delete(
    "/categorias/{categoria_id}",
    response_model=Categoria,
    status_code=status.HTTP_200_OK,
)
async def eliminar_categoria(
    categoria_id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_gestion(token)
    categoria = obtener_categoria(session, categoria_id)
    categoria.activa = False
    session.add(categoria)
    session.commit()
    session.refresh(categoria)
    return categoria