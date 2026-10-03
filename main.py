from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from routers.router_usuarios import router as usuario_router
from routers.router_equipos import router as equipo_router
from routers.router_categorias import router as categoria_router
from routers.router_productos import router as productos_router
from routers.router_clientes import router as cliente_router
from routers.router_roles import router as rol_router
from routers.router_componentes import router as componente_router
from routers.router_revision_equipos import router as revision_router
from routers.router_rentas import router as renta_router
from oauth.oauth import router as oauth_router

from config.db import crear_db_y_tablas
import models

@asynccontextmanager
async def lifespan(app: FastAPI):
    crear_db_y_tablas()
    yield

app = FastAPI(lifespan=lifespan)
app.title = "CyberCafe API"
app.version = "1.0.0"

# Configuración de CORS para permitir solicitudes desde el frontend (Web POS, Flutter, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite cualquier origen en desarrollo (puedes especificar ["http://localhost:3000", ...])
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, PUT, DELETE, PATCH, etc.)
    allow_headers=["*"],  # Permite todos los encabezados (Authorization, Content-Type, etc.)
)

@app.get("/", summary="Comprobando Api", status_code=status.HTTP_200_OK)
async def home():
    return {"message": "ok"}

app.include_router(oauth_router, tags=['oauth'])
app.include_router(rol_router, tags=["roles"])
app.include_router(usuario_router, tags=["usuarios"])
app.include_router(cliente_router, tags=["clientes"])
app.include_router(equipo_router, tags=["equipos"])
app.include_router(componente_router, tags=["componentes"])
app.include_router(renta_router, tags=["rentas"])
app.include_router(revision_router, tags=["revisiones_equipo"])
app.include_router(categoria_router, tags=["categorias"])
app.include_router(productos_router, tags=["productos"])