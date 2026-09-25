from fastapi import FastAPI, status
from contextlib import asynccontextmanager
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
