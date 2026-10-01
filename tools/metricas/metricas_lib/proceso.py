"""Métricas de PROCESO: MTTD, MTTR y eficacia de las pruebas."""
import os

from . import comun, defectos, graficos
from .comun import c, tabla, md_tabla
from .defectos import media, mediana


def _por_modulo(dat, campo):
    res = {}
    for m in comun.modulos():
        v = [r[campo] for r in dat["defectos"] if m in r["modulos"] and r[campo] is not None]
        res[m] = mediana(v)
    return res


# ==========================================================================
# 4. MTTD
# ==========================================================================
def mttd(args=None):
    comun.encabezado(
        4, "Tiempo medio de detección (MTTD)", "proceso",
        "cuánto tiempo pasa desde que se introduce un defecto hasta que se corrige.",
        "MTTD = promedio(fecha del fix − fecha del commit que introdujo el defecto)",
        "historial de git: del commit inductor (rama de trabajo) al commit fix: (ver ciclo de vida).")
    dat = defectos.minar()
    v = [r["mttd_dias"] for r in dat["defectos"] if r["mttd_dias"] is not None]
    me, md_ = media(v), mediana(v)
    pm = _por_modulo(dat, "mttd_dias")
    rangos = [("< 1 día", 0, 1), ("1–7 días", 1, 7), ("7–30 días", 7, 30), ("30–180 días", 30, 180), ("> 180 días", 180, 1e9)]
    dist = [(t, sum(1 for x in v if lo <= x < hi)) for t, lo, hi in rangos]
    tabla(["Estadístico", "Valor"], [
        ["Defectos (commits fix:)", dat["n_fixes"]],
        ["Con commit inductor identificado (SZZ)", f"{len(v)} ({100 * len(v) / dat['n_fixes']:.1f}%)"],
        [c("MTTD mediana", "neg"), c(f"{md_:.2f} días", "neg")],
        ["MTTD promedio", f"{me:.2f} días"],
        ["Máximo", f"{max(v):.1f} días"]], titulo="Tiempo medio de detección")
    tabla(["Rango", "Defectos", "%"], [[t, n, f"{100 * n / len(v):.1f}%"] for t, n in dist], titulo="Distribución")
    tabla(["Módulo", "Mediana (días)"], [[m, comun.fmt(x, 2)] for m, x in pm.items()], titulo="Mediana por módulo")
    val = "bueno" if md_ <= 7 else ("aceptable" if md_ <= 30 else "mejorable")
    lento = max((m for m in pm if pm[m] is not None), key=lambda m: pm[m])
    r = {
        "clave": "mttd", "numero": 4, "nombre": "MTTD", "tipo": "Proceso",
        "que_mide": "Tiempo entre que se introduce un defecto y el commit que lo corrige.",
        "formula": "promedio(fecha fix − fecha commit inductor)",
        "ubicacion": "Ciclo de vida: desde el commit que introduce el defecto hasta el commit fix: (git blame/SZZ).",
        "valor": round(md_, 2), "media": me, "mediana": md_, "n": len(v),
        "resultado_general": f"mediana {md_:.2f} días · promedio {me:.1f} días (n = {len(v)})",
        "valor_corto": f"{md_:.1f} d", "detalle_corto": f"mediana · promedio {me:.1f} días",
        "valoracion": val, "etiqueta": {"bueno": "RÁPIDA", "aceptable": "MODERADA", "mejorable": "LENTA"}[val],
        "interpretacion": (f"La mitad de los defectos se detecta y corrige en menos de {md_:.1f} días; el promedio ({me:.1f} días) "
                           f"es mucho mayor porque una minoría de defectos latentes tarda meses (cola larga), sobre todo en "
                           f"{lento} (mediana {pm[lento]:.1f} días). Por eso la mediana es el valor representativo."),
        "significado": ("El equipo detecta rápido la mayoría de los errores, pero el almacenamiento (llavero/archivos cifrados) "
                        "esconde defectos que solo aparecen con el uso real en distintos sistemas operativos."),
        "referencia": "Valoración propia: mediana ≤ 7 días rápida, ≤ 30 moderada, > 30 lenta.",
        "distribucion": dict(dist), "por_modulo_mediana": pm,
    }
    archivos = []
    d = comun.carpeta("mttd")
    if comun.CFG["graficos"]:
        archivos.append(graficos.distribucion_tiempos(os.path.join(d, "mttd.png"), v, me, md_,
                                                      "Distribución del MTTD (introducción → corrección)", "días", pm,
                                                      nota="Fuente: minería SZZ sobre los commits fix: del historial."))
    md = comun.md_resultado(r) + "\n### Por módulo (mediana, días)\n\n" + md_tabla(
        ["Módulo", "Mediana"], [[m, comun.fmt(x, 2)] for m, x in pm.items()])
    archivos = list(comun.guardar("mttd", r, md)) + archivos
    comun.cerrar(r, archivos)
    return r


# ==========================================================================
# 5. MTTR
# ==========================================================================
def mttr(args=None):
    comun.encabezado(
        5, "Tiempo medio de reparación (MTTR)", "proceso",
        "cuánto tarda una corrección ya escrita en integrarse a la rama principal.",
        "MTTR = promedio(fecha del merge del PR a main − fecha del commit fix:)",
        "ciclo de vida: del commit fix: en su rama al merge del Pull Request en main.")
    dat = defectos.minar()
    v = [r["mttr_dias"] for r in dat["defectos"] if r["mttr_dias"] is not None]
    me, md_ = media(v), mediana(v)
    directos = sum(1 for r in dat["defectos"] if r["directo_a_main"])
    pm = _por_modulo(dat, "mttr_dias")
    horas = lambda x: f"{x * 24:.2f} h" if x is not None else "n/d"
    tabla(["Estadístico", "Valor"], [
        ["Correcciones vía Pull Request", len(v)],
        ["Correcciones directo a main (sin MTTR)", directos],
        [c("MTTR mediana", "neg"), c(f"{horas(md_)}  ({md_ * 24 * 60:.0f} min)", "neg")],
        ["MTTR promedio", f"{horas(me)}  ({me:.2f} días)"],
        ["Correcciones fusionadas en < 1 hora", f"{sum(1 for x in v if x < 1 / 24)} ({100 * sum(1 for x in v if x < 1 / 24) / len(v):.1f}%)"],
        ["Correcciones fusionadas en < 1 día", f"{sum(1 for x in v if x < 1)} ({100 * sum(1 for x in v if x < 1) / len(v):.1f}%)"]],
        titulo="Tiempo medio de reparación")
    tabla(["Módulo", "Mediana"], [[m, horas(x)] for m, x in pm.items()], titulo="Mediana por módulo")
    val = "bueno" if md_ * 24 < 24 else ("aceptable" if md_ <= 7 else "mejorable")
    r = {
        "clave": "mttr", "numero": 5, "nombre": "MTTR", "tipo": "Proceso",
        "que_mide": "Tiempo entre el commit de corrección y su integración (merge) a main.",
        "formula": "promedio(fecha merge − fecha fix)",
        "ubicacion": "Ciclo de vida: Pull Request → fusión a main (etapa de revisión e integración).",
        "valor": round(md_ * 24, 2), "media_dias": me, "mediana_dias": md_, "n": len(v), "directo_a_main": directos,
        "resultado_general": f"mediana {md_ * 24:.2f} h ({md_ * 24 * 60:.0f} min) · promedio {me * 24:.1f} h (n = {len(v)})",
        "valor_corto": f"{md_ * 24 * 60:.0f} min", "detalle_corto": f"mediana · promedio {me * 24:.1f} h",
        "valoracion": val, "etiqueta": {"bueno": "MUY ÁGIL", "aceptable": "ÁGIL", "mejorable": "LENTA"}[val],
        "interpretacion": (f"Una vez escrita la corrección, la mitad se fusiona en menos de {md_ * 24 * 60:.0f} minutos y el "
                           f"promedio es {me * 24:.1f} horas. {directos} correcciones se subieron directo a main y no tienen MTTR."),
        "significado": ("Las correcciones casi no esperan en cola: PRs pequeños, CI rápida y revisores disponibles. Es una "
                        "práctica de integración continua madura (rasgo de los equipos de alto desempeño según DORA)."),
        "referencia": "DORA (Forsgren et al., 2019): restauración < 1 h en equipos élite y < 1 día en equipos de "
                      "alto desempeño. Aquí el MTTR es una aproximación desde git.",
        "por_modulo_mediana_dias": pm,
    }
    archivos = []
    d = comun.carpeta("mttr")
    if comun.CFG["graficos"]:
        archivos.append(graficos.distribucion_tiempos(
            os.path.join(d, "mttr.png"), v, me, md_, "Distribución del MTTR (commit fix → merge a main)", "horas", pm,
            bandas=[(1e-3, 1, "< 1 h", graficos.ESTADO["bueno"]), (1, 24, "< 1 día", graficos.ESTADO["aceptable"]),
                    (24, 24 * 30, "> 1 día", graficos.ESTADO["mejorable"])],
            nota="Fuente: fecha del merge del PR que contiene cada commit fix:."))
    md = comun.md_resultado(r) + "\n### Por módulo (mediana)\n\n" + md_tabla(
        ["Módulo", "Mediana"], [[m, horas(x)] for m, x in pm.items()])
    archivos = list(comun.guardar("mttr", r, md)) + archivos
    comun.cerrar(r, archivos)
    return r


# ==========================================================================
# 6. Eficacia de las pruebas
# ==========================================================================
def pruebas(args=None):
    comun.encabezado(
        6, "Eficacia de las pruebas", "proceso",
        "porcentaje de defectos atrapados antes de llegar a una versión publicada.",
        "eficacia = (defectos en revisión + en pruebas/CI) / defectos con fase conocida × 100",
        "ciclo de vida: PR + CI frente a release (tags v0.x.y y tags por módulo).")
    dat = defectos.minar()
    cont = {}
    for r_ in dat["defectos"]:
        cont[r_["fase"]] = cont.get(r_["fase"], 0) + 1
    conocidos = dat["n_fixes"] - cont.get("desconocida", 0)
    antes = cont.get("revision", 0) + cont.get("pruebas_ci", 0)
    ef = 100 * antes / conocidos if conocidos else 0
    nombres = {"revision": "Revisión (mismo PR, antes de fusionar)", "pruebas_ci": "Pruebas / CI (antes de publicarse)",
               "produccion": "Producción (ya publicado)", "desconocida": "Sin clasificar"}
    tabla(["Fase de detección", "Defectos", "% del total"],
          [[nombres[k], cont.get(k, 0), f"{100 * cont.get(k, 0) / dat['n_fixes']:.1f}%"] for k in nombres],
          alinear="lrr", titulo="Fase en la que se detectó cada defecto")
    pm = {}
    for m in comun.modulos():
        rs = [x for x in dat["defectos"] if m in x["modulos"] and x["fase"] != "desconocida"]
        pm[m] = 100 * sum(1 for x in rs if x["fase"] in ("revision", "pruebas_ci")) / len(rs) if rs else None
    tabla(["Módulo", "Eficacia"], [[m, comun.fmt(x, 1, "%")] for m, x in pm.items()], titulo="Eficacia por módulo")
    val = "bueno" if ef >= 85 else ("aceptable" if ef >= 65 else "mejorable")
    r = {
        "clave": "pruebas", "numero": 6, "nombre": "Eficacia de las pruebas", "tipo": "Proceso",
        "que_mide": "Porcentaje de defectos atrapados antes de llegar a una versión publicada.",
        "formula": "(revisión + pruebas/CI) / defectos con fase conocida × 100",
        "ubicacion": "Ciclo de vida: revisión del PR y CI (unittests, lint, keychain) frente a los releases.",
        "valor": round(ef, 1),
        "resultado_general": f"{ef:.1f}% ({antes} de {conocidos} defectos atrapados antes de producción)",
        "valor_corto": f"{ef:.1f}%", "detalle_corto": f"{antes}/{conocidos} antes de producción",
        "valoracion": val, "etiqueta": {"bueno": "ALTA", "aceptable": "MEDIA", "mejorable": "MEJORABLE"}[val],
        "interpretacion": (f"Casi la mitad de los defectos se atrapa antes de publicar ({cont.get('revision', 0)} en revisión y "
                           f"{cont.get('pruebas_ci', 0)} en pruebas/CI), pero {cont.get('produccion', 0)} llegaron a una "
                           f"versión publicada antes de corregirse."),
        "significado": ("La red de pruebas automatizadas deja pasar la mitad de los errores. Reforzar pruebas en los módulos "
                        "con más defectos (plugin, credentialhelper) es la mejora con mayor impacto."),
        "referencia": "Jones (2008): eficiencia de eliminación de defectos (DRE) promedio ≈ 85%; los mejores equipos > 95%.",
        "fases": cont, "conocidos": conocidos, "antes_produccion": antes, "por_modulo": pm,
    }
    archivos = []
    d = comun.carpeta("pruebas")
    if comun.CFG["graficos"]:
        archivos.append(graficos.fases(os.path.join(d, "pruebas.png"), cont, ef))
    md = comun.md_resultado(r) + "\n### Por fase\n\n" + md_tabla(
        ["Fase", "Defectos"], [[nombres[k], cont.get(k, 0)] for k in nombres])
    archivos = list(comun.guardar("pruebas", r, md)) + archivos
    comun.cerrar(r, archivos)
    return r
