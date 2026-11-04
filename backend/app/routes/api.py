"""Rutas HTTP (/api/*): asocian cada endpoint con su controlador. Sin logica propia."""

from typing import Optional

from fastapi import APIRouter, Header, Request

from ..controllers.controladores import (ControladorIntegraciones, ControladorMediciones, ControladorModelo, ControladorRecalibracion,
                                         ControladorRedes, ControladorSalud, ControladorSimulacion)
from ..models.dominio import PeticionLote, PeticionModelo, PeticionRecalibracion

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


@router.get("/integraciones")
async def integraciones(request: Request):
    return await ControladorIntegraciones(_c(request)).verificar()


@router.get("/simulacion")
def simulacion_estado(request: Request):
    return ControladorSimulacion(_c(request)).estado()


@router.post("/simulacion/lote", status_code=202)
async def simulacion_lote(request: Request, peticion: PeticionLote = PeticionLote(), authorization: Optional[str] = Header(default=None)):
    ctl = ControladorSimulacion(_c(request))
    ctl.autorizar(authorization)
    return await ctl.iniciar_lote(peticion)


@router.delete("/simulacion/lote")
async def simulacion_lote_cancelar(request: Request, authorization: Optional[str] = Header(default=None)):
    ctl = ControladorSimulacion(_c(request))
    ctl.autorizar(authorization)
    return await ctl.cancelar_lote()


@router.post("/simulacion/continuo")
async def simulacion_continuo_iniciar(request: Request, authorization: Optional[str] = Header(default=None)):
    ctl = ControladorSimulacion(_c(request))
    ctl.autorizar(authorization)
    return ctl.iniciar_continuo()


@router.delete("/simulacion/continuo")
async def simulacion_continuo_detener(request: Request, authorization: Optional[str] = Header(default=None)):
    ctl = ControladorSimulacion(_c(request))
    ctl.autorizar(authorization)
    return await ctl.detener_continuo()


@router.post("/simulacion/informe")
async def simulacion_informe(request: Request, authorization: Optional[str] = Header(default=None)):
    ctl = ControladorSimulacion(_c(request))
    ctl.autorizar(authorization)
    return await ctl.informe()


@router.get("/simulacion/archivos")
def simulacion_archivos(request: Request):
    return ControladorSimulacion(_c(request)).archivos()


@router.get("/simulacion/archivos/{nombre}")
def simulacion_archivo(nombre: str, request: Request):
    return ControladorSimulacion(_c(request)).archivo(nombre)
