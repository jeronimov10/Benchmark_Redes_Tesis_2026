"""Linea de comandos del banco: python -m simulacion lote | continuo | informe (desde backend/). Usa la misma logica que los endpoints /api/simulacion."""

import argparse
import asyncio
import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings  # noqa: E402
from app.container import Contenedor  # noqa: E402
from app.models.dominio import PeticionLote  # noqa: E402


def _servicio(args):
    settings = Settings()
    if args.salida:
        settings = dataclasses.replace(settings, sim_dir_env=args.salida)
    c = Contenedor(dataclasses.replace(settings, colectores_activos=False))
    c.sembrar()
    return c.simulacion


async def _lote(args):
    s = _servicio(args)
    p = PeticionLote(fuente=args.fuente, semilla=args.semilla, replicas=args.replicas, tope=args.tope, panel_por_perfil=args.panel,
                     niveles_replicas=args.niveles)
    info = await s.iniciar_lote(p)
    print(f"lote {info['id']} iniciado")
    await s.esperar()
    e = s.estado()["lote"]
    print(f"estado: {e['estado']} | evaluaciones: {e.get('evaluaciones')} | salida: {s.settings.dir_simulacion}")
    await s.cerrar()


async def _continuo(args):
    s = _servicio(args)
    s.iniciar_continuo()
    print(f"panel continuo cada {s.settings.sim_intervalo_s:.0f} s; Ctrl+C para detener")
    try:
        await asyncio.Event().wait()
    finally:
        await s.cerrar()


async def _informe(args):
    s = _servicio(args)
    print("\n".join(await s.generar_informe()))
    await s.cerrar()


def main():
    ap = argparse.ArgumentParser(prog="simulacion")
    ap.add_argument("--salida", help="directorio de salida (por defecto backend/data/simulacion)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    lote = sub.add_parser("lote")
    lote.add_argument("--fuente", choices=["base", "vivo", "ambas"], default="base")
    lote.add_argument("--semilla", type=int)
    lote.add_argument("--replicas", type=int)
    lote.add_argument("--tope", type=int, default=400)
    lote.add_argument("--panel", type=int, default=10)
    lote.add_argument("--niveles", type=int, nargs="+", default=[500, 2000, 10000, 40000])
    sub.add_parser("continuo")
    sub.add_parser("informe")
    args = ap.parse_args()
    asyncio.run({"lote": _lote, "continuo": _continuo, "informe": _informe}[args.cmd](args))


if __name__ == "__main__":
    main()
