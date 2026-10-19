"""Rutas HTTP (/api/*): asocian cada endpoint con su controlador. Sin logica propia."""

from fastapi import APIRouter, Request

from ..controllers.controladores import (ControladorMediciones, ControladorModelo, ControladorRecalibracion,
                                         ControladorRedes, ControladorSalud)
from ..models.dominio import PeticionModelo, PeticionRecalibracion

router = APIRouter(prefix="/api")


def _c(request: Request):
    return request.app.state.contenedor


@router.get("/salud")
def salud(request: Request):
    return ControladorSalud(_c(request)).estado()


@router.get("/redes")
def redes(request: Request):
    return ControladorRedes(_c(request)).listar()


@router.get("/mediciones")
def mediciones(request: Request):
    return ControladorMediciones(_c(request)).todas()


@router.get("/mediciones/{red}")
def medicion_red(red: str, request: Request):
    return ControladorMediciones(_c(request)).una(red)


@router.get("/modelo")
def modelo_info(request: Request):
    return ControladorModelo(_c(request)).info()


@router.post("/modelo")
async def modelo_ejecutar(peticion: PeticionModelo, request: Request):
    return await ControladorModelo(_c(request)).ejecutar(peticion)


@router.post("/recalibracion")
async def recalibracion_iniciar(request: Request, peticion: PeticionRecalibracion = PeticionRecalibracion()):
    return await ControladorRecalibracion(_c(request)).iniciar(peticion)


@router.get("/recalibracion")
def recalibracion_estado(request: Request):
    return ControladorRecalibracion(_c(request)).estado()


@router.delete("/recalibracion")
async def recalibracion_cancelar(request: Request):
    return await ControladorRecalibracion(_c(request)).cancelar()
