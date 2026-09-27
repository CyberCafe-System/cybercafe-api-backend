from fastapi import FastAPI, status
from contextlib import asynccontextmanager
from routers.usuario_router import router as usuario_router
from routers.router_equipo import router as equipo_router
from routers.router_categoria import router as categoria_router
from routers.router_productos import router as productos_router
from oauth.oauth import router as oauth_router

from config.db import crear_db_y_tablas
import models

@asynccontextmanager
async def lifespan(app: FastAPI):
    crear_db_y_tablas()
    yield

app = FastAPI(lifespan=lifespan)
app.title = "API insertar nombre"
app.version = "0.0.1"

@app.get("/", summary="Comprobando Api", status_code=status.HTTP_200_OK)
async def home():
    return {"message": "ok"}

app.include_router(oauth_router, tags=['oauth'])
app.include_router(usuario_router, tags=["usuarios"])
app.include_router(equipo_router, tags=["equipos"])
app.include_router(categoria_router, tags=["categorias"])
app.include_router(productos_router, tags=["productos"])