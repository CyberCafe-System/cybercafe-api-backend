import os
import asyncio
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlmodel import Session

logger = logging.getLogger("cybercafe.main")

from routers.router_usuarios import router as usuario_router
from routers.router_equipos import router as equipo_router
from routers.router_categorias import router as categoria_router
from routers.router_productos import router as productos_router
from routers.router_clientes import router as cliente_router
from routers.router_componentes import router as componente_router
from routers.router_revision_equipos import router as revision_router
from routers.router_rentas import router as renta_router
from routers.router_ventas import router as venta_router
from routers.router_reportes import router as reporte_router
from routers.router_notificaciones import router as notificacion_router
from oauth.oauth import router as oauth_router

from config.db import crear_db_y_tablas, engine
from services.notificacion_service import verificar_vencimiento_rentas
import models

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "production").strip().lower()
HABILITAR_DOCS = ENVIRONMENT in ("development", "dev", "local")


def _ejecutar_verificacion_sincrona():
    """Ejecuta la verificación de rentas vencidas en un hilo trabajador."""
    with Session(engine) as s:
        try:
            verificar_vencimiento_rentas(s)
        except Exception as exc:
            s.rollback()
            logger.warning("Error en tarea periódica de vencimiento: %s", exc, exc_info=True)


async def _tarea_periodica_vencimiento():
    """Revisa cada 15 segundos sesiones activas vencidas y genera notificaciones."""
    while True:
        try:
            await asyncio.sleep(15)
            await asyncio.to_thread(_ejecutar_verificacion_sincrona)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning("Fallo inesperado en ciclo periódico: %s", exc, exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    crear_db_y_tablas()
    task = asyncio.create_task(_tarea_periodica_vencimiento())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    lifespan=lifespan,
    title="CyberCafe API",
    version="1.0.0",
    docs_url="/docs" if HABILITAR_DOCS else None,
    redoc_url="/redoc" if HABILITAR_DOCS else None,
    openapi_url="/openapi.json" if HABILITAR_DOCS else None,
)

cors_origins_env = os.getenv("CORS_ORIGINS", "*").strip()
if cors_origins_env == "*" or not cors_origins_env:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Total-Count"],
    )
else:
    origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Total-Count"],
    )

@app.get("/", summary="Comprobando Api", status_code=status.HTTP_200_OK)
def home():
    return {"message": "ok"}

app.include_router(oauth_router, tags=['oauth'])
app.include_router(usuario_router, tags=["usuarios"])
app.include_router(cliente_router, tags=["clientes"])
app.include_router(equipo_router, tags=["equipos"])
app.include_router(componente_router, tags=["componentes"])
app.include_router(renta_router, tags=["rentas"])
app.include_router(venta_router, tags=["ventas"])
app.include_router(revision_router, tags=["revisiones_equipo"])
app.include_router(categoria_router, tags=["categorias"])
app.include_router(productos_router, tags=["productos"])
app.include_router(reporte_router, tags=["reportes"])
app.include_router(notificacion_router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True)
