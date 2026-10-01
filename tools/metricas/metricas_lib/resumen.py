"""`metricas todo`: ejecuta las 9 métricas y produce el resumen completo
(tabla consolidada, tablero, esquema de ciclo de vida y arquitectura anotada)."""
import os
import time

from . import comun, graficos, producto, proceso, proyecto
from .comun import c, tabla, md_tabla

ORDEN = [
    ("complejidad", producto.complejidad), ("cobertura", producto.cobertura), ("densidad", producto.densidad),
    ("mttd", proceso.mttd), ("mttr", proceso.mttr), ("pruebas", proceso.pruebas),
    ("revision", proyecto.revision), ("esfuerzo", proyecto.esfuerzo), ("arquitectura", proyecto.arquitectura),
]


def resumen(args=None, ejecutar=True):
    t0 = time.time()
    res = []
    for clave, fn in ORDEN:
        if ejecutar:
            r = fn(args) or comun.cargar(clave)
            if not r:
                comun.error(f"La métrica '{clave}' no pudo calcularse; corrige el problema y vuelve a ejecutar.")
                return False
            res.append(r)
        else:
            r = comun.cargar(clave)
            if r is None:
                comun.aviso(f"No hay resultado guardado de '{clave}'; se calcula ahora.")
                r = fn(args)
            res.append(r)
    # la arquitectura se redibuja al final para incluir todas las métricas por módulo
    d = comun.carpeta("resumen")
    archivos = []
    if comun.CFG["graficos"]:
        archivos.append(proyecto.dibujar_arquitectura(os.path.join(d, "arquitectura_metricas.png"), res[8]))
        archivos.append(graficos.ciclo_vida(os.path.join(d, "ciclo_vida_metricas.png"), _valores_ciclo(res)))
        archivos.append(graficos.tablero(os.path.join(d, "tablero.png"), res))

    print()
    print(c("═" * 78, "azul"))
    print(c(" RESUMEN DE MÉTRICAS — " + os.path.basename(comun.CFG["repo"]) + f" @ {comun.head_hash()[:10]}", "azul", "neg"))
    print(c("═" * 78, "azul"))
    filas = []
    for r in res:
        col = comun.VALORACION_COLOR.get(r["valoracion"], "azul")
        filas.append([r["numero"], r["tipo"], r["nombre"], c(r["valor_corto"], "neg"), r["detalle_corto"],
                      c(f"{comun.VALORACION_ICONO[r['valoracion']]} {r['etiqueta']}", col, "neg")])
    tabla(["#", "Tipo", "Métrica", "Resultado", "Detalle", "Valoración"], filas, alinear="rllrll")
    print()
    comun.parrafo("Lectura conjunta:", _conclusion(res))
    md = "# Resumen de métricas — docker/secrets-engine\n\n" + \
         f"Commit analizado: `{comun.head_hash()}`\n\n" + md_tabla(
             ["#", "Tipo", "Métrica", "Resultado general", "Valoración"],
             [[r["numero"], r["tipo"], r["nombre"], r["resultado_general"], r["etiqueta"]] for r in res]) + \
         "\n\n**Lectura conjunta:** " + _conclusion(res) + "\n\n" + "\n\n".join(comun.md_resultado(r) for r in res)
    datos = {"metricas": [{k: r[k] for k in ("numero", "clave", "tipo", "nombre", "valor", "resultado_general",
                                              "valoracion", "etiqueta", "interpretacion", "significado")} for r in res]}
    archivos = list(comun.guardar("resumen", datos, md)) + archivos
    comun.pie_archivos(archivos)
    print(c(f"  Tiempo total: {time.time() - t0:.0f} s", "gris"))
    return datos


def _valores_ciclo(res):
    by = {r["clave"]: r for r in res}
    return {
        "revision": f"{by['revision']['valor']:.1f}%", "revision_estado": by["revision"]["valoracion"],
        "pruebas": f"{by['pruebas']['valor']:.1f}%", "pruebas_estado": by["pruebas"]["valoracion"],
        "mttr": f"mediana {by['mttr']['mediana_dias'] * 24 * 60:.0f} min", "mttr_estado": by["mttr"]["valoracion"],
        "mttd": f"mediana {by['mttd']['mediana']:.1f} días · promedio {by['mttd']['media']:.1f} días",
        "produccion": by["pruebas"]["fases"].get("produccion", 0),
        "fixes": by["densidad"]["total_defectos"],
        "esfuerzo": by["esfuerzo"]["resultado_general"],
    }


def _conclusion(res):
    by = {r["clave"]: r for r in res}
    return (f"código de baja complejidad (CC media {by['complejidad']['valor']:.2f}) y cobertura "
            f"{by['cobertura']['etiqueta'].lower()} ({by['cobertura']['valor']:.1f}%); los defectos "
            f"({by['densidad']['valor']:.2f}/KLOC) se concentran en los adaptadores pequeños, se corrigen y fusionan "
            f"muy rápido (MTTR mediana {by['mttr']['mediana_dias'] * 24 * 60:.0f} min), pero solo "
            f"{by['pruebas']['valor']:.0f}% se atrapa antes de publicarse y {by['revision']['valor']:.0f}% en revisión: "
            f"la mejora prioritaria es reforzar las pruebas automatizadas de plugin y credentialhelper.")
