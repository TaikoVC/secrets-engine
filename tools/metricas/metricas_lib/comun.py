"""Utilidades comunes de la CLI `metricas`: localización del repositorio,
ejecución de comandos, impresión de tablas en la terminal y guardado de
resultados (JSON + Markdown) en la carpeta de salida."""
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime

# --------------------------------------------------------------------------
# Configuración global (la rellena cli.py a partir de los argumentos)
# --------------------------------------------------------------------------
CFG = {
    "repo": None,          # raíz del repositorio (donde está go.work)
    "salida": None,        # carpeta de resultados
    "ref": "HEAD",         # referencia de git a analizar
    "refrescar": False,    # ignorar cachés (minería de defectos, perfiles)
    "graficos": True,      # generar PNG
    "color": True,         # colores ANSI en la terminal
}

# --------------------------------------------------------------------------
# Colores
# --------------------------------------------------------------------------
_C = {
    "reset": "\033[0m", "neg": "\033[1m", "tenue": "\033[2m",
    "azul": "\033[38;5;33m", "cian": "\033[38;5;37m", "verde": "\033[38;5;34m",
    "amarillo": "\033[38;5;178m", "naranja": "\033[38;5;208m", "rojo": "\033[38;5;160m",
    "gris": "\033[38;5;245m",
}


def c(texto, *estilos):
    if not CFG["color"]:
        return str(texto)
    return "".join(_C[e] for e in estilos) + str(texto) + _C["reset"]


VALORACION_COLOR = {
    "bueno": "verde", "aceptable": "amarillo", "mejorable": "naranja", "bajo": "rojo", "info": "azul",
}
VALORACION_ICONO = {"bueno": "[OK]", "aceptable": "[~]", "mejorable": "[!]", "bajo": "[X]", "info": "[i]"}


# --------------------------------------------------------------------------
# Repositorio y comandos
# --------------------------------------------------------------------------
def encontrar_repo(inicio=None):
    d = os.path.abspath(inicio or os.getcwd())
    while True:
        if os.path.isfile(os.path.join(d, "go.work")):
            return d
        padre = os.path.dirname(d)
        if padre == d:
            return None
        d = padre


def modulos():
    """Lee los módulos declarados en go.work (directiva `use`)."""
    texto = open(os.path.join(CFG["repo"], "go.work"), encoding="utf-8").read()
    bloque = re.search(r"use\s*\((.*?)\)", texto, re.S)
    lineas = bloque.group(1).split() if bloque else re.findall(r"^use\s+(\S+)", texto, re.M)
    mods = [l.strip().lstrip("./") for l in lineas if l.strip() and not l.startswith("//")]
    # orden estable y legible: núcleo primero, plugins después
    orden = ["client", "plugin", "store", "plugins/pass", "plugins/credentialhelper", "x"]
    return sorted(mods, key=lambda m: (orden.index(m) if m in orden else 99, m))


def modulo_de(ruta, mods=None):
    """Módulo al que pertenece una ruta relativa (prefijo más largo)."""
    mods = mods or modulos()
    mejor = None
    for m in mods:
        if ruta == m or ruta.startswith(m + "/"):
            if mejor is None or len(m) > len(mejor):
                mejor = m
    return mejor


def ejecutar(cmd, cwd=None, env=None, entrada=None, tiempo=None):
    r = subprocess.run(cmd, cwd=cwd or CFG["repo"], env=env, input=entrada,
                       capture_output=True, text=True, timeout=tiempo)
    return r.returncode, r.stdout, r.stderr


def git(*args):
    code, out, _ = ejecutar(["git", "-C", CFG["repo"], *args])
    return out if code == 0 else ""


def head_hash():
    return git("rev-parse", CFG["ref"]).strip()


def requiere(*programas):
    faltan = [p for p in programas if shutil.which(p) is None]
    if faltan:
        error(f"Falta(n) en el PATH: {', '.join(faltan)}. Ejecuta `metricas doctor` para ver cómo instalarlos.")
        sys.exit(2)


def carpeta(*partes):
    d = os.path.join(CFG["salida"], *partes)
    os.makedirs(d, exist_ok=True)
    return d


def rel(ruta):
    try:
        return os.path.relpath(ruta, CFG["repo"])
    except ValueError:
        return ruta


# --------------------------------------------------------------------------
# Impresión
# --------------------------------------------------------------------------
def info(msg):
    print(c("  · ", "gris") + c(msg, "gris"), file=sys.stderr)


def aviso(msg):
    print(c("  ! ", "amarillo", "neg") + c(msg, "amarillo"), file=sys.stderr)


def error(msg):
    print(c("  ✗ ", "rojo", "neg") + msg, file=sys.stderr)


def _ancho_visible(s):
    return len(re.sub(r"\033\[[0-9;]*m", "", str(s)))


def tabla(cabeceras, filas, alinear=None, titulo=None):
    """Imprime una tabla con bordes. `alinear` = cadena con 'l'/'r' por columna."""
    filas = [[("" if v is None else v) for v in f] for f in filas]
    n = len(cabeceras)
    alinear = alinear or ("l" + "r" * (n - 1))
    anchos = [max([_ancho_visible(cabeceras[i])] + [_ancho_visible(f[i]) for f in filas]) for i in range(n)]

    def celda(v, i):
        pad = anchos[i] - _ancho_visible(v)
        return (" " * pad + str(v)) if alinear[i] == "r" else (str(v) + " " * pad)

    linea = lambda a, b, d: c(a + b.join("─" * (w + 2) for w in anchos) + d, "gris")
    if titulo:
        print(c("  " + titulo, "neg"))
    print("  " + linea("┌", "┬", "┐"))
    print("  " + c("│", "gris") + c("│", "gris").join(" " + c(celda(h, i), "neg") + " " for i, h in enumerate(cabeceras)) + c("│", "gris"))
    print("  " + linea("├", "┼", "┤"))
    for f in filas:
        print("  " + c("│", "gris") + c("│", "gris").join(" " + celda(v, i) + " " for i, v in enumerate(f)) + c("│", "gris"))
    print("  " + linea("└", "┴", "┘"))


def encabezado(numero, nombre, tipo, que_mide, formula, ubicacion):
    ancho = 78
    titulo = f" MÉTRICA {numero} · {nombre.upper()}  ({tipo}) "
    print()
    print(c("═" * ancho, "azul"))
    print(c(titulo, "azul", "neg"))
    print(c("═" * ancho, "azul"))
    print(c("  Qué mide:   ", "neg") + que_mide)
    print(c("  Fórmula:    ", "neg") + formula)
    print(c("  Dónde está: ", "neg") + ubicacion)
    print()


def resultado_general(texto, valoracion, etiqueta):
    color = VALORACION_COLOR.get(valoracion, "azul")
    icono = VALORACION_ICONO.get(valoracion, "")
    print()
    print("  " + c("▶ RESULTADO GENERAL: ", "neg") + c(texto, color, "neg") + "   " + c(f"{icono} {etiqueta}", color, "neg"))


def parrafo(titulo, texto, ancho=74):
    import textwrap
    lineas = textwrap.wrap(texto, ancho - len(titulo) - 2) or [""]
    print("  " + c(titulo, "neg") + " " + lineas[0])
    for l in lineas[1:]:
        print("  " + " " * (len(titulo) + 1) + l)


def pie_archivos(archivos):
    print()
    print(c("  Archivos generados:", "gris"))
    for a in archivos:
        print(c("    " + rel(a), "gris"))
    print()


# --------------------------------------------------------------------------
# Guardado de resultados
# --------------------------------------------------------------------------
def md_tabla(cabeceras, filas):
    out = ["| " + " | ".join(str(h) for h in cabeceras) + " |",
           "|" + "|".join("---" for _ in cabeceras) + "|"]
    for f in filas:
        out.append("| " + " | ".join("" if v is None else re.sub(r"\033\[[0-9;]*m", "", str(v)) for v in f) + " |")
    return "\n".join(out)


def guardar(clave, datos, md):
    d = carpeta(clave)
    datos = dict(datos)
    datos["_generado"] = datetime.now().astimezone().isoformat(timespec="seconds")
    datos["_commit_analizado"] = head_hash()
    pj = os.path.join(d, f"{clave}.json")
    with open(pj, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False, default=str)
    pm = os.path.join(d, f"{clave}.md")
    with open(pm, "w", encoding="utf-8") as f:
        f.write(md.rstrip() + "\n")
    return pj, pm


def cargar(clave):
    p = os.path.join(CFG["salida"], clave, f"{clave}.json")
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return None


def fmt(x, dec=1, sufijo=""):
    if x is None:
        return "n/d"
    return f"{x:.{dec}f}{sufijo}"


def md_resultado(r):
    """Bloque Markdown estándar con el resultado general e interpretación."""
    return (
        f"## Métrica {r['numero']}: {r['nombre']} ({r['tipo']})\n\n"
        f"**Qué mide:** {r['que_mide']}  \n"
        f"**Fórmula:** `{r['formula']}`  \n"
        f"**Dónde se ubica en el proyecto:** {r['ubicacion']}\n\n"
        f"### Resultado general\n\n**{r['resultado_general']}** — valoración: **{r['etiqueta']}**\n\n"
        f"**Interpretación:** {r['interpretacion']}\n\n"
        f"**Qué significa para el proyecto:** {r['significado']}\n\n"
        f"**Referencia de valoración:** {r['referencia']}\n"
    )


def cerrar(r, archivos):
    """Imprime el resultado general + interpretación y el pie de archivos."""
    resultado_general(r["resultado_general"], r["valoracion"], r["etiqueta"])
    print()
    parrafo("Interpretación:", r["interpretacion"])
    print()
    parrafo("Para el proyecto:", r["significado"])
    print()
    parrafo("Referencia:", r["referencia"])
    pie_archivos(archivos)
