"""Ajuste de la recomendacion a la necesidad declarada: evalua desde afuera, con umbrales que ya existen en el modelo, si cada red cumple
costo, espera (lecturas preferencia y requisito) e irrevocabilidad, y clasifica al usuario en cumple, parcial, brecha, sin solucion o no evaluable."""

COSTO_MAX_FRACCION = 0.01
FIRMEZA_MAX_S = 86400.0
LECTURAS = ("preferencia", "requisito")
ESTADOS = ("cumple", "parcial", "brecha", "sin_solucion", "no_evaluable")


def _valor(perfil, mid):
    return perfil.get(mid, {}).get("valor")


def criterios(perfil, usuario, lectura):
    ticket_usd = usuario["monto_cop"] / usuario["trm"]
    a1 = _valor(perfil, "A1")
    resultado = {"costo": None if a1 is None else a1 <= COSTO_MAX_FRACCION * ticket_usd}
    espera = _valor(perfil, "B1" if lectura == "preferencia" else "B2")
    resultado["espera"] = None if espera is None else espera <= usuario["espera_s"]
    if usuario["irrevocabilidad"] == "alta":
        firmeza = _valor(perfil, "B2b")
        if firmeza is None:
            firmeza = _valor(perfil, "B2")
        resultado["irrevocabilidad"] = None if firmeza is None else firmeza <= FIRMEZA_MAX_S
    return resultado


def cumple_red(perfil, usuario, lectura):
    c = criterios(perfil, usuario, lectura)
    fallados = [k for k, v in c.items() if v is False]
    if fallados:
        return False, fallados
    if any(v is None for v in c.values()):
        return None, [k for k, v in c.items() if v is None]
    return True, []


def estado_ajuste(perfiles, usuario, resultado, lectura):
    if resultado is None:
        return "no_evaluable", []
    bandas = resultado.get("bandas") or []
    if not bandas:
        return "sin_solucion", []
    banda1 = bandas[0]["redes"]
    otras = [r for b in bandas[1:] for r in b["redes"]]
    evaluadas = {r: cumple_red(perfiles[r], usuario, lectura) for r in banda1 + otras}
    en1 = [evaluadas[r][0] for r in banda1]
    fallos = sorted({k for r in banda1 for k in evaluadas[r][1] if evaluadas[r][0] is False})
    if any(v is None for v in en1):
        return "no_evaluable", sorted({k for r in banda1 for k in evaluadas[r][1]})
    if all(en1):
        return "cumple", []
    if any(en1):
        return "parcial", fallos
    alternativas = [evaluadas[r][0] for r in otras]
    if any(v is True for v in alternativas):
        return "brecha", fallos
    if any(v is None for v in alternativas):
        return "no_evaluable", fallos
    return "sin_solucion", fallos
