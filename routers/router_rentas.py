from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import Field, SQLModel, select

from config.security_dependencia import Token_Dependencia
from config.session_dependencia import SessionDeDependencia
from models.cliente import Cliente
from models.detalle_renta import DetalleRenta, EstadoRenta
from models.equipo import Equipo, EstadoEquipo
from models.renta import EstadoPago, Renta, RentaCreate, RentaUpdate
from models.revision_equipo import RevisionEquipo
from models.usuario import Usuario


ROLES_CON_PERMISO_LECTURA_RENTAS = {1, 2, 3}
ROLES_CON_PERMISO_GESTION_RENTAS = {1, 2}
ROLES_CON_PERMISO_ELIMINACION_RENTAS = {1}

router = APIRouter()


class IniciarRentaRequest(SQLModel):
    cliente_id: int
    equipo_id: int
    tiempo_de_renta: int = Field(ge=15, description="Tiempo de uso en minutos (ej: 30, 60, 120)")
    estado_de_pago: EstadoPago = Field(default=EstadoPago.PENDIENTE)


class RentaConDetallesResponse(SQLModel):
    renta: Renta
    detalles: list[DetalleRenta]


def validar_permisos_lectura(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_LECTURA_RENTAS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para consultar rentas",
        )


def validar_permisos_gestion(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_GESTION_RENTAS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el administrador o cajero pueden gestionar rentas",
        )


def validar_permisos_eliminacion(token: dict) -> None:
    if token.get("id_rol") not in ROLES_CON_PERMISO_ELIMINACION_RENTAS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el administrador puede eliminar rentas",
        )


def obtener_renta(session: SessionDeDependencia, renta_id: int) -> Renta:
    renta = session.get(Renta, renta_id)
    if not renta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"La renta con ID {renta_id} no fue encontrada",
        )
    return renta


def obtener_detalle_renta(
    session: SessionDeDependencia, detalle_renta_id: int
) -> DetalleRenta:
    detalle = session.get(DetalleRenta, detalle_renta_id)
    if not detalle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El detalle de renta con ID {detalle_renta_id} no fue encontrado",
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


def validar_equipo_disponible(
    session: SessionDeDependencia, equipo_id: int
) -> Equipo:
    equipo = session.get(Equipo, equipo_id)
    if not equipo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El equipo con ID {equipo_id} no existe",
        )

    if equipo.estado != EstadoEquipo.DISPONIBLE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El equipo '{equipo.nombre}' no está disponible. Estado actual: {equipo.estado.value if hasattr(equipo.estado, 'value') else equipo.estado}",
        )

    # Validar que no tenga otra sesión de renta actualmente activa
    sesion_activa = session.exec(
        select(DetalleRenta).where(
            DetalleRenta.equipo_id == equipo_id,
            DetalleRenta.estado == EstadoRenta.ACTIVA,
        )
    ).first()
    if sesion_activa:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El equipo '{equipo.nombre}' ya tiene una sesión de renta activa (Detalle Renta ID: {sesion_activa.detalle_renta_id})",
        )

    return equipo


@router.get(
    "/rentas",
    response_model=list[Renta],
    status_code=status.HTTP_200_OK,
)
async def get_rentas(
    session: SessionDeDependencia,
    token: Token_Dependencia,
    cliente_id: int | None = Query(None, description="Filtrar por cliente"),
    estado_de_pago: EstadoPago | None = Query(None, description="Filtrar por estado de pago"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1),
):
    validar_permisos_lectura(token)
    consulta = select(Renta)

    if cliente_id is not None:
        consulta = consulta.where(Renta.cliente_id == cliente_id)
    if estado_de_pago is not None:
        consulta = consulta.where(Renta.estado_de_pago == estado_de_pago)

    return session.exec(consulta.offset(offset).limit(limit)).all()


@router.get(
    "/rentas/{renta_id}",
    response_model=RentaConDetallesResponse,
    status_code=status.HTTP_200_OK,
)
async def get_renta(
    renta_id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    """Consulta la renta junto a todos sus detalles de sesiones de equipos."""
    validar_permisos_lectura(token)
    renta = obtener_renta(session, renta_id)
    detalles = session.exec(
        select(DetalleRenta).where(DetalleRenta.renta_id == renta_id)
    ).all()
    return RentaConDetallesResponse(renta=renta, detalles=detalles)


@router.post(
    "/rentas",
    response_model=RentaConDetallesResponse,
    status_code=status.HTTP_201_CREATED,
)
async def iniciar_renta(
    datos: IniciarRentaRequest,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    """
    Inicia una nueva renta de equipo en el Cybercafé:
    - Valida que el cliente exista.
    - Valida que el equipo esté DISPONIBLE y no tenga otra sesión activa.
    - Asigna el usuario cajero/admin autenticado desde el token JWT.
    - Calcula el costo según la tarifa por hora y la duración contratada.
    - Crea la cabecera Renta y el registro DetalleRenta en una transacción atómica.
    """
    validar_permisos_gestion(token)

    # 1. Validar llaves foráneas y disponibilidad
    validar_cliente(session, datos.cliente_id)
    equipo = validar_equipo_disponible(session, datos.equipo_id)
    usuario_id = token.get("id")

    # 2. Calcular subtotal de renta según tiempo contratado
    horas = Decimal(datos.tiempo_de_renta) / Decimal(60)
    subtotal = Decimal(round(float(equipo.tarifa_por_hora * horas), 2))
    ahora = datetime.now(timezone.utc)

    # 3. Crear cabecera de Renta
    renta = Renta(
        cliente_id=datos.cliente_id,
        usuario_id=usuario_id,
        fecha=ahora,
        total=subtotal,
        estado_de_pago=datos.estado_de_pago,
    )
    session.add(renta)
    session.flush()  # Genera renta_id

    # 4. Crear DetalleRenta
    detalle_renta = DetalleRenta(
        renta_id=renta.renta_id,
        equipo_id=datos.equipo_id,
        hora_inicio=ahora,
        tiempo_de_renta=datos.tiempo_de_renta,
        tiempo_agregado=0,
        subtotal=subtotal,
        estado=EstadoRenta.ACTIVA,
    )
    session.add(detalle_renta)

    session.commit()
    session.refresh(renta)
    session.refresh(detalle_renta)

    return RentaConDetallesResponse(renta=renta, detalles=[detalle_renta])


@router.patch(
    "/rentas/{renta_id}/pago",
    response_model=Renta,
    status_code=status.HTTP_200_OK,
)
async def actualizar_estado_pago(
    renta_id: int,
    nuevo_estado_pago: EstadoPago,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    """Actualiza el estado de pago de una renta (PENDIENTE o PAGADO)."""
    validar_permisos_gestion(token)
    renta = obtener_renta(session, renta_id)

    renta.estado_de_pago = nuevo_estado_pago
    session.add(renta)
    session.commit()
    session.refresh(renta)
    return renta


@router.get(
    "/detalles-renta",
    response_model=list[DetalleRenta],
    status_code=status.HTTP_200_OK,
)
async def get_detalles_renta(
    session: SessionDeDependencia,
    token: Token_Dependencia,
    renta_id: int | None = Query(None, description="Filtrar por ID de renta"),
    equipo_id: int | None = Query(None, description="Filtrar por equipo"),
    estado: EstadoRenta | None = Query(None, description="Filtrar por estado (Activa, Pendiente Revision, Finalizada)"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1),
):
    validar_permisos_lectura(token)
    consulta = select(DetalleRenta)

    if renta_id is not None:
        consulta = consulta.where(DetalleRenta.renta_id == renta_id)
    if equipo_id is not None:
        consulta = consulta.where(DetalleRenta.equipo_id == equipo_id)
    if estado is not None:
        consulta = consulta.where(DetalleRenta.estado == estado)

    return session.exec(consulta.offset(offset).limit(limit)).all()


@router.get(
    "/detalles-renta/pendientes-revision",
    response_model=list[DetalleRenta],
    status_code=status.HTTP_200_OK,
)
async def get_detalles_pendientes_revision(
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    """Lista las sesiones finalizadas que esperan inspección física por el asistente."""
    validar_permisos_lectura(token)
    consulta = select(DetalleRenta).where(
        DetalleRenta.estado == EstadoRenta.PENDIENTE_REVISION
    )
    return session.exec(consulta).all()


@router.get(
    "/detalles-renta/{detalle_renta_id}",
    response_model=DetalleRenta,
    status_code=status.HTTP_200_OK,
)
async def get_detalle_renta(
    detalle_renta_id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    validar_permisos_lectura(token)
    return obtener_detalle_renta(session, detalle_renta_id)


@router.patch(
    "/detalles-renta/{detalle_renta_id}/extender",
    response_model=DetalleRenta,
    status_code=status.HTTP_200_OK,
)
async def extender_tiempo_renta(
    detalle_renta_id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
    minutos_extra: int = Query(..., ge=5, description="Minutos adicionales a extender"),
):
    """
    Extiende el tiempo de una sesión activa de equipo:
    - Suma los minutos al tiempo agregado.
    - Calcula el costo adicional proporcional a la tarifa del equipo.
    - Incrementa el subtotal del detalle y el total general de la Renta madre.
    """
    validar_permisos_gestion(token)
    detalle = obtener_detalle_renta(session, detalle_renta_id)

    if detalle.estado != EstadoRenta.ACTIVA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se puede extender el tiempo de sesiones activas. Estado actual: {detalle.estado.value if hasattr(detalle.estado, 'value') else detalle.estado}",
        )

    equipo = session.get(Equipo, detalle.equipo_id)
    if not equipo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipo no encontrado para calcular tarifa",
        )

    # Calcular costo adicional
    horas_extra = Decimal(minutos_extra) / Decimal(60)
    costo_extra = Decimal(round(float(equipo.tarifa_por_hora * horas_extra), 2))

    detalle.tiempo_agregado = (detalle.tiempo_agregado or 0) + minutos_extra
    detalle.subtotal += costo_extra

    # Actualizar cabecera Renta
    renta = session.get(Renta, detalle.renta_id)
    if renta:
        renta.total += costo_extra
        session.add(renta)

    session.add(detalle)
    session.commit()
    session.refresh(detalle)
    return detalle


@router.patch(
    "/detalles-renta/{detalle_renta_id}/finalizar",
    response_model=DetalleRenta,
    status_code=status.HTTP_200_OK,
)
async def finalizar_sesion_renta(
    detalle_renta_id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    """
    Finaliza la sesión del cliente en la computadora o consola:
    - Registra la hora_fin.
    - Cambia el estado a PENDIENTE_REVISION (para que el asistente verifique componentes antes de liberarla).
    """
    validar_permisos_gestion(token)
    detalle = obtener_detalle_renta(session, detalle_renta_id)

    if detalle.estado != EstadoRenta.ACTIVA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se puede finalizar una sesión activa. Estado actual: {detalle.estado.value if hasattr(detalle.estado, 'value') else detalle.estado}",
        )

    detalle.hora_fin = datetime.now(timezone.utc)
    detalle.estado = EstadoRenta.PENDIENTE_REVISION

    session.add(detalle)
    session.commit()
    session.refresh(detalle)
    return detalle


@router.delete(
    "/rentas/{renta_id}",
    status_code=status.HTTP_200_OK,
)
async def eliminar_renta(
    renta_id: int,
    session: SessionDeDependencia,
    token: Token_Dependencia,
):
    """Elimina una renta y sus detalles si no posee revisiones técnicas asociadas (solo Admin)."""
    validar_permisos_eliminacion(token)
    renta = obtener_renta(session, renta_id)

    # Validar si alguno de sus detalles tiene revisiones de equipo registradas
    detalles = session.exec(
        select(DetalleRenta).where(DetalleRenta.renta_id == renta_id)
    ).all()

    for detalle in detalles:
        revision = session.exec(
            select(RevisionEquipo).where(
                RevisionEquipo.detalle_renta_id == detalle.detalle_renta_id
            )
        ).first()
        if revision:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede eliminar la renta porque la sesión de equipo {detalle.equipo_id} ya posee una revisión técnica registrada",
            )

    for detalle in detalles:
        session.delete(detalle)
    session.delete(renta)

    session.commit()
    return {"message": "Renta y detalles eliminados exitosamente", "renta_id": renta_id}
