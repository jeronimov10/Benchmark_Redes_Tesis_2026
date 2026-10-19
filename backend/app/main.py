"""Aplicacion FastAPI: ciclo de vida (siembra de la linea base, inicio y parada ordenada de los colectores), CORS, manejo uniforme de
errores y montaje de las rutas /api. Ejecutar con: uvicorn app.main:app --port 8000 (desde backend/)."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import Settings
from .container import Contenedor
from .routes.api import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)


def crear_app(contenedor=None):
    @asynccontextmanager
    async def vida(app):
        c = contenedor or Contenedor()
        app.state.contenedor = c
        c.iniciar()
        try:
            yield
        finally:
            await c.detener()

    app = FastAPI(title="Monitor de redes y recomendacion de liquidacion", version="1.0.0", lifespan=vida)
    settings = contenedor.settings if contenedor else Settings()
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origenes), allow_methods=["*"], allow_headers=["*"])

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail)})

    @app.exception_handler(RequestValidationError)
    async def validacion_error(_: Request, exc: RequestValidationError):
        return JSONResponse(status_code=400, content={"error": "peticion invalida", "detalle": exc.errors()})

    @app.exception_handler(Exception)
    async def error_inesperado(_: Request, exc: Exception):
        logging.getLogger("api").exception("error no controlado")
        return JSONResponse(status_code=500, content={"error": f"{type(exc).__name__}: {exc}"})

    app.include_router(router)
    return app


app = crear_app()
