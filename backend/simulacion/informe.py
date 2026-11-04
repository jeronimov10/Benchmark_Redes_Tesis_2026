"""Generador del informe del banco: lee la base propia (simulacion.db) y escribe informe.md, los CSV por prueba y el manifiesto, sin volver a correr
el modelo. Los hallazgos son automaticos, por pregunta, con sus cifras y sus limites; no sacan conclusiones de tesis."""

import csv
import json
import os
import subprocess
from collections import Counter, defaultdict
from statistics import mean

from app.utils.tiempo import ahora, iso

from .ajuste import ESTADOS, LECTURAS
from .experimentos import cuota_modal, wilson_semiancho
from .personas import POR_ID, TRM

ARCHIVOS = ("informe.md", "personas.csv", "contrafactuales.csv", "sensibilidad.csv", "convergencia.csv", "serie_vivo.csv", "manifiesto.json")
MAYORIA = 0.5
COLUMNAS_CONTRA = ["fuente", "prueba", "escenario", "perfil", "n", "cambios_banda1", "cuota_cambio", "aptos_supera_a_la_mejor", "perdida_puntaje_media", "empeora_ajuste_req"]


def _banda(d):
    return tuple(sorted(d["bandas"][0])) if d.get("bandas") else ()


def _orden(d):
    return tuple(tuple(sorted(b)) for b in d.get("bandas", []))


def _escribir_csv(ruta, columnas, filas):
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columnas)
        w.writeheader()
        w.writerows(filas)


def _por_clave(evaluaciones):
    return {(e["fuente"], e["escenario"], e["perfil"], e["indice"]): e["datos"] for e in evaluaciones}


def _commit():
    for var in ("RAILWAY_GIT_COMMIT_SHA", "GIT_COMMIT"):
        if os.environ.get(var):
            return os.environ[var]
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5).stdout.strip() or "desconocido"
    except Exception:
        return "desconocido"


def filas_personas(evals):
    por = defaultdict(list)
    for e in evals:
        por[(e["fuente"], e["perfil"])].append(e["datos"])
    filas = []
    for (fuente, perfil), regs in sorted(por.items()):
        modal, k = cuota_modal(regs)
        niveles = Counter(r["nivel"] for r in regs)
        fila = {"fuente": fuente, "perfil": perfil, "nombre": POR_ID[perfil].nombre, "tipo": POR_ID[perfil].tipo, "n": len(regs),
                "banda1_modal": "+".join(modal) or "ninguna", "cuota_modal": round(k / len(regs), 3),
                "semiancho_wilson": round(wilson_semiancho(k, len(regs)), 3), "llego_al_tope": len(regs) >= 400,
                "certidumbre_media": round(mean(r["certidumbre"] for r in regs if r["certidumbre"] is not None), 3) if any(r["certidumbre"] is not None for r in regs) else "",
                "cuota_certidumbre_baja": round(niveles.get("baja", 0) / len(regs), 3),
                "empates_banda1": round(sum(1 for r in regs if len(_banda(r)) > 1) / len(regs), 3)}
        for lectura in LECTURAS:
            c = Counter(r[f"ajuste_{lectura}"] for r in regs)
            for estado in ESTADOS:
                fila[f"{lectura}_{estado}"] = round(c.get(estado, 0) / len(regs), 3)
        filas.append(fila)
    return filas


def filas_contrafactuales(evals_p3, evals_p4, evals_ref):
    ref = {(e["fuente"], e["perfil"], e["indice"]): e["datos"] for e in evals_ref}
    por = defaultdict(list)
    for e in evals_p3 + evals_p4:
        por[(e["fuente"], e["escenario"], e["perfil"])].append(e["datos"])
    filas = []
    for (fuente, escenario, perfil), regs in sorted(por.items()):
        fila = {"fuente": fuente, "prueba": "P4" if escenario.startswith("sin_") else "P3", "escenario": escenario, "perfil": perfil, "n": len(regs)}
        if escenario == "aptos_sombra":
            fila.update({"cambios_banda1": "", "cuota_cambio": "", "aptos_supera_a_la_mejor": round(sum(1 for r in regs if r["aptos_supera"]) / len(regs), 3),
                         "perdida_puntaje_media": round(mean(r["mejor_otra_central"] - r["aptos_central"] for r in regs), 4), "empeora_ajuste_req": ""})
            filas.append(fila)
            continue
        pares = [(r, ref[(fuente, r["perfil"], r["indice"])]) for r in regs if (fuente, r["perfil"], r["indice"]) in ref]
        cambios = sum(1 for r, b in pares if _banda(r) != _banda(b))
        fila.update({"cambios_banda1": cambios, "cuota_cambio": round(cambios / len(pares), 3) if pares else "", "aptos_supera_a_la_mejor": ""})
        medias = [(max(b["medianas"].values()) - max(r["medianas"].values())) for r, b in pares if r["medianas"] and b["medianas"]]
        fila["perdida_puntaje_media"] = round(mean(medias), 4) if medias else ""
        peor = sum(1 for r, b in pares if ESTADOS.index(r["ajuste_requisito"]) > ESTADOS.index(b["ajuste_requisito"])
                   and r["ajuste_requisito"] in ("brecha", "sin_solucion") and b["ajuste_requisito"] not in ("brecha", "sin_solucion"))
        fila["empeora_ajuste_req"] = peor
        filas.append(fila)
    return filas


def filas_sensibilidad(evals_p5, evals_ref):
    ref = {(e["fuente"], e["perfil"], e["indice"]): e["datos"] for e in evals_ref}
    por = defaultdict(list)
    for e in evals_p5:
        por[(e["fuente"], e["perfil"], e["escenario"])].append(e["datos"])
    filas = []
    for (fuente, perfil, atributo), regs in sorted(por.items()):
        pares = [(r, ref[(fuente, r["perfil"], r["indice"])]) for r in regs if (fuente, r["perfil"], r["indice"]) in ref]
        cambios = sum(1 for r, b in pares if _banda(r) != _banda(b))
        filas.append({"fuente": fuente, "perfil": perfil, "atributo": atributo, "n": len(pares), "cambios_banda1": cambios,
                      "cuota_cambio": round(cambios / len(pares), 3) if pares else ""})
    return filas


def filas_convergencia(evals_p6):
    niveles = defaultdict(dict)
    for e in evals_p6:
        niveles[(e["fuente"], int(e["escenario"].split("_")[1]))][(e["perfil"], e["indice"])] = e["datos"]
    filas = []
    for fuente in sorted({f for f, _ in niveles}):
        mayor = max(n for f, n in niveles if f == fuente)
        ref = niveles[(fuente, mayor)]
        for nivel in sorted(n for f, n in niveles if f == fuente):
            datos = niveles[(fuente, nivel)]
            comunes = [k for k in datos if k in ref]
            filas.append({"fuente": fuente, "replicas": nivel, "referencia": mayor, "n": len(comunes),
                          "coincide_banda1": round(sum(1 for k in comunes if _banda(datos[k]) == _banda(ref[k])) / len(comunes), 3) if comunes else "",
                          "coincide_orden": round(sum(1 for k in comunes if _orden(datos[k]) == _orden(ref[k])) / len(comunes), 3) if comunes else ""})
    return filas


def filas_vivo(ciclos):
    filas = []
    for c in ciclos:
        d = c["datos"]
        base = {"ciclo": c["id"], "ts": iso(c["ts"]), "valido": bool(c["valido"]), "metricas_vivas": c["vivas"], "metricas_esperadas": c["esperadas"],
                "version_perfil": c["version_perfil"]}
        if not c["valido"]:
            filas.append({**base, "perfil": "", "usuarios": "", "cambios": "", "distintos_de_base": "", "causa_probable": ""})
            continue
        por_perfil = defaultdict(lambda: [0, 0, 0])
        for k in d["bandas"]:
            p = int(k.split(":")[0])
            por_perfil[p][0] += 1
            por_perfil[p][1] += k in d["cambios"]
            por_perfil[p][2] += k in d["distintos_de_base"]
        causa = d["causa"]["metrica"] if d.get("causa") else ""
        for p, (n, cambios, distintos) in sorted(por_perfil.items()):
            filas.append({**base, "perfil": p, "usuarios": n, "cambios": cambios, "distintos_de_base": distintos, "causa_probable": causa})
    return filas


def _tabla(cabecera, filas):
    return "\n".join(["| " + " | ".join(cabecera) + " |", "|" + "---|" * len(cabecera)] + ["| " + " | ".join(str(x) for x in f) + " |" for f in filas])


def hallazgos(personas, contra, sens, conv, vivo, notas):
    t = ["# Informe del banco de usuarios simulados", "",
         "Generado automaticamente a partir de simulacion.db. Los resultados se leen por perfil; nunca como porcentaje de la poblacion. "
         "Los rangos de los perfiles 4 a 12 son supuestos de diseno. Un mal ajuste es evidencia para discutir, no un defecto demostrado.", ""]
    if notas:
        t += ["## Notas de la corrida", ""] + [f"- {n}" for n in notas] + [""]
    if personas:
        t += ["## P1. Cobertura", "", _tabla(["fuente", "perfil", "n", "banda 1 modal", "cuota", "semiancho", "cert. baja", "empates"],
                                              [(f["fuente"], f"{f['perfil']} {f['nombre']}", f["n"], f["banda1_modal"], f["cuota_modal"], f["semiancho_wilson"],
                                                f["cuota_certidumbre_baja"], f["empates_banda1"]) for f in personas]), ""]
        alertas = [f for f in personas if f["cuota_certidumbre_baja"] > MAYORIA or f["llego_al_tope"]]
        t += [f"- ALERTA P1: perfil {f['perfil']} ({f['nombre']}, {f['fuente']}): " + ("llego al tope de 400 usuarios" if f["llego_al_tope"] else "certidumbre baja en la mayoria") for f in alertas]
        t += ["- Sin alertas de cobertura." if not alertas else "", ""]
        t += ["## P2. Ajuste a la necesidad", "", _tabla(["fuente", "perfil", "lectura", *ESTADOS],
                                                        [(f["fuente"], f["perfil"], lec, *[f[f"{lec}_{e}"] for e in ESTADOS]) for f in personas for lec in LECTURAS]), ""]
        brechas = [f for f in personas if f["requisito_brecha"] > 0 or f["preferencia_brecha"] > 0]
        t += [f"- ALERTA P2: perfil {f['perfil']} ({f['nombre']}, {f['fuente']}): brecha preferencia {f['preferencia_brecha']}, requisito {f['requisito_brecha']}"
              for f in brechas] or ["- No se observaron brechas."]
        t += [""]
    p3 = [f for f in contra if f["prueba"] == "P3" and f["escenario"] != "aptos_sombra"]
    if p3:
        t += ["## P3. Contrafactuales de medicion", "", "Cuota de usuarios del panel cuya banda 1 cambia frente a la referencia.", "",
              _tabla(["fuente", "escenario", "perfil", "n", "cuota de cambio"], [(f["fuente"], f["escenario"], f["perfil"], f["n"], f["cuota_cambio"]) for f in p3]), ""]
        comunes = [f for f in p3 if f["escenario"] == "metricas_comunes" and f["cuota_cambio"] != "" and f["cuota_cambio"] > MAYORIA]
        t += [f"- ALERTA P3: con metricas comunes cambia el ganador de la mayoria del perfil {f['perfil']} ({f['fuente']}): la comparacion dependeria de la cobertura de metricas." for f in comunes]
        sombra = [f for f in contra if f["escenario"] == "aptos_sombra"]
        t += [f"- Aptos en sombra, perfil {f['perfil']} ({f['fuente']}): supera a la mejor otra red en {f['aptos_supera_a_la_mejor']} de los usuarios; diferencia media de puntaje central {f['perdida_puntaje_media']}." for f in sombra]
        t += [""]
    p4 = [f for f in contra if f["prueba"] == "P4"]
    if p4:
        t += ["## P4. Caida de una red", "", _tabla(["fuente", "escenario", "perfil", "cuota de cambio", "perdida de puntaje", "empeora ajuste (req.)"],
                                                     [(f["fuente"], f["escenario"], f["perfil"], f["cuota_cambio"], f["perdida_puntaje_media"], f["empeora_ajuste_req"]) for f in p4]), ""]
        t += [f"- ALERTA P4: el perfil {f['perfil']} ({f['fuente']}) empeora su ajuste en {f['empeora_ajuste_req']} usuarios al caer {f['escenario'][4:]}." for f in p4 if f["empeora_ajuste_req"]]
        t += [""]
    if sens:
        mas = defaultdict(lambda: ("", 0.0))
        for f in sens:
            if f["cuota_cambio"] != "" and f["cuota_cambio"] >= mas[(f["fuente"], f["perfil"])][1]:
                mas[(f["fuente"], f["perfil"])] = (f["atributo"], f["cuota_cambio"])
        t += ["## P5. Sensibilidad del usuario", "", "Atributo que mas cambia la banda 1 por perfil.", "",
              _tabla(["fuente", "perfil", "atributo mas sensible", "cuota de cambio"], [(k[0], k[1], v[0], v[1]) for k, v in sorted(mas.items())]), ""]
    if conv:
        t += ["## P6. Convergencia de replicas", "", _tabla(["fuente", "replicas", "referencia", "banda 1", "orden completo"],
                                                          [(f["fuente"], f["replicas"], f["referencia"], f["coincide_banda1"], f["coincide_orden"]) for f in conv]), ""]
        t += [f"- ALERTA P6: las 10000 replicas de la tesis no coinciden por completo con la referencia ({f['coincide_banda1']} en banda 1, {f['coincide_orden']} en orden completo, {f['fuente']})."
              for f in conv if f["replicas"] == 10000 and f["replicas"] != f["referencia"] and (f["coincide_banda1"] != 1 or f["coincide_orden"] != 1)]
        t += [""]
    if vivo:
        validos = [f for f in vivo if f["valido"]]
        ciclos = len({f["ciclo"] for f in vivo})
        n_validos = len({f["ciclo"] for f in validos})
        cambios = sum(f["cambios"] for f in validos)
        usuarios = sum(f["usuarios"] for f in validos)
        distintos = sum(f["distintos_de_base"] for f in validos)
        t += ["## P7. Panel continuo", "", f"- Ciclos: {ciclos} ({n_validos} validos, {ciclos - n_validos} invalidos por cobertura de metricas vivas).",
              f"- Evaluaciones de usuario en ciclos validos: {usuarios}; cambios de banda 1 entre ciclos consecutivos: {cambios}.",
              f"- Usuarios con banda 1 distinta entre modo vivo y modo medicion: {distintos}" + (f" ({round(distintos / usuarios, 3)})." if usuarios else "."),
              "- La causa probable es una atribucion indicativa (mayor cambio relativo entre perfiles); ver serie_vivo.csv.", ""]
    return "\n".join(x for x in t if x is not None)


def generar(almacen, directorio, settings, corrida_id=None):
    directorio.mkdir(parents=True, exist_ok=True)
    corrida = almacen.corrida(corrida_id) if corrida_id else almacen.ultima_corrida("completado")
    personas, contra, sens, conv, notas = [], [], [], [], []
    if corrida:
        cid = corrida["id"]
        personas = filas_personas(almacen.evaluaciones(cid, "P1P2"))
        ref = almacen.evaluaciones(cid, "REF")
        contra = filas_contrafactuales(almacen.evaluaciones(cid, "P3"), almacen.evaluaciones(cid, "P4"), ref)
        sens = filas_sensibilidad(almacen.evaluaciones(cid, "P5"), ref)
        conv = filas_convergencia(almacen.evaluaciones(cid, "P6"))
        notas = (corrida.get("manifiesto") or {}).get("notas", [])
    vivo = filas_vivo(almacen.ciclos())
    if personas:
        _escribir_csv(directorio / "personas.csv", list(personas[0]), personas)
    if contra:
        _escribir_csv(directorio / "contrafactuales.csv", COLUMNAS_CONTRA, contra)
    if sens:
        _escribir_csv(directorio / "sensibilidad.csv", list(sens[0]), sens)
    if conv:
        _escribir_csv(directorio / "convergencia.csv", list(conv[0]), conv)
    if vivo:
        _escribir_csv(directorio / "serie_vivo.csv", list(vivo[0]), vivo)
    (directorio / "informe.md").write_text(hallazgos(personas, contra, sens, conv, vivo, notas), encoding="utf-8")
    manifiesto = {"generado_en": iso(ahora()), "commit": _commit(), "trm": TRM, "corrida": corrida["id"] if corrida else None,
                  "config": corrida["config"] if corrida else None, "version_perfil": (corrida.get("manifiesto") or {}).get("version_perfil") if corrida else None,
                  "ciclos_continuos": len(almacen.ciclos())}
    (directorio / "manifiesto.json").write_text(json.dumps(manifiesto, indent=2, ensure_ascii=False), encoding="utf-8")
    return sorted(p.name for p in directorio.iterdir() if p.name in ARCHIVOS)
