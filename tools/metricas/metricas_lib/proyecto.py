"""Métricas de PROYECTO: eficacia de la revisión, desviación de esfuerzo y
arquitectura (módulos, dependencias, patrones y frameworks)."""
import os
import re

from . import comun, defectos, graficos, producto
from .comun import c, tabla, md_tabla


# ==========================================================================
# 7. Eficacia de la revisión
# ==========================================================================
def revision(args=None):
    comun.encabezado(
        7, "Eficacia de la revisión", "proyecto",
        "porcentaje de defectos que se atrapan dentro del mismo Pull Request que los introdujo.",
        "eficacia = defectos detectados en revisión / defectos con fase conocida × 100",
        "ciclo de vida: etapa de Pull Request / revisión de código (antes del merge).")
    dat = defectos.minar()
    conocidos = [r for r in dat["defectos"] if r["atrapado_en_revision"] is not None]
    atrap = sum(1 for r in conocidos if r["atrapado_en_revision"])
    ef = 100 * atrap / len(conocidos) if conocidos else 0
    pr = [r for r in dat["defectos"] if not r["directo_a_main"]]
    un_commit = sum(1 for r in pr if r["commits_en_pr"] == 1)
    pm = {}
    for m in comun.modulos():
        rs = [r for r in conocidos if m in r["modulos"]]
        pm[m] = 100 * sum(1 for r in rs if r["atrapado_en_revision"]) / len(rs) if rs else 0
    tabla(["Indicador", "Valor"], [
        ["Defectos con fase de detección conocida", len(conocidos)],
        ["Detectados en revisión (mismo PR)", atrap],
        [c("Eficacia de la revisión", "neg"), c(f"{ef:.1f}%", "neg")],
        ["Fixes que llegaron por PR", len(pr)],
        ["  de ellos, PR de un solo commit", f"{un_commit} ({100 * un_commit / len(pr):.1f}%)"]], titulo="Eficacia de la revisión")
    tabla(["Módulo", "Eficacia"], [[m, f"{x:.1f}%"] for m, x in pm.items()], titulo="Por módulo")
    val = "bueno" if ef >= 50 else ("aceptable" if ef >= 30 else "mejorable")
    r = {
        "clave": "revision", "numero": 7, "nombre": "Eficacia de la revisión", "tipo": "Proyecto",
        "que_mide": "Porcentaje de defectos atrapados durante la revisión del Pull Request, antes del merge.",
        "formula": "defectos en revisión / defectos con fase conocida × 100",
        "ubicacion": "Ciclo de vida: etapa de Pull Request (revisión de código humana y pr-review.yml).",
        "valor": round(ef, 1),
        "resultado_general": f"{ef:.1f}% ({atrap} de {len(conocidos)} defectos detectados en revisión)",
        "valor_corto": f"{ef:.1f}%", "detalle_corto": f"{atrap}/{len(conocidos)} en el mismo PR",
        "valoracion": val, "etiqueta": {"bueno": "ALTA", "aceptable": "MEDIA", "mejorable": "BAJA"}[val],
        "interpretacion": (f"Solo {atrap} de {len(conocidos)} defectos se corrigieron dentro del mismo PR que los introdujo. "
                           f"El {100 * un_commit / len(pr):.0f}% de los PRs de corrección tiene un solo commit, así que hay poca "
                           f"oportunidad de que la revisión produzca un segundo commit que corrija al primero."),
        "significado": ("La revisión de código es el filtro más débil del proceso: la mayoría de los errores se detecta "
                        "después del merge. Compensar con más pruebas automatizadas rinde más que agregar revisión manual."),
        "referencia": "Jones (2008): las inspecciones formales eliminan alrededor del 60-65% de los defectos; las revisiones informales, bastante menos.",
        "conocidos": len(conocidos), "atrapados": atrap, "prs_un_commit": un_commit, "prs": len(pr), "por_modulo": pm,
    }
    archivos = []
    d = comun.carpeta("revision")
    if comun.CFG["graficos"]:
        archivos.append(graficos.revision(os.path.join(d, "revision.png"), ef, atrap, len(conocidos), pm))
    md = comun.md_resultado(r) + "\n### Por módulo\n\n" + md_tabla(["Módulo", "Eficacia"], [[m, f"{x:.1f}%"] for m, x in pm.items()])
    archivos = list(comun.guardar("revision", r, md)) + archivos
    comun.cerrar(r, archivos)
    return r


# ==========================================================================
# 8. Desviación de esfuerzo
# ==========================================================================
def esfuerzo(args=None):
    comun.encabezado(
        8, "Desviación de tiempo y esfuerzo", "proyecto",
        "diferencia entre el esfuerzo que cada módulo debería recibir por su tamaño y el que recibió.",
        "desviación = (esfuerzo real − esperado) / esperado × 100   [esperado = % KLOC; real = % commits]",
        "gestión del proyecto: reparto de trabajo entre los 6 módulos a lo largo de todo el historial.")
    kl = producto.kloc_por_modulo()
    commits = {}
    for m in comun.modulos():
        out = comun.git("log", "--no-merges", "--pretty=format:%H", comun.CFG["ref"], "--", m)
        commits[m] = len([l for l in out.splitlines() if l.strip()])
    tk = sum(v["kloc"] for v in kl.values())
    tc = sum(commits.values())
    dat = defectos.minar()
    filas = []
    for m in comun.modulos():
        esp = 100 * kl[m]["kloc"] / tk
        real = 100 * commits[m] / tc
        n = sum(1 for r in dat["defectos"] if m in r["modulos"])
        filas.append({"modulo": m, "kloc": kl[m]["kloc"], "commits": commits[m], "esperado_pct": esp, "real_pct": real,
                      "desviacion_pct": (real - esp) / esp * 100, "densidad": n / kl[m]["kloc"]})
    tabla(["Módulo", "KLOC", "Commits", "Esperado", "Real", "Desviación", "Def./KLOC"],
          [[f["modulo"], f"{f['kloc']:.3f}", f["commits"], f"{f['esperado_pct']:.1f}%", f"{f['real_pct']:.1f}%",
            c(f"{f['desviacion_pct']:+.1f}%", "neg"), f"{f['densidad']:.2f}"] for f in filas]
          + [["TOTAL", f"{tk:.3f}", tc, "100%", "100%", "", ""]], titulo="Esfuerzo esperado vs. real")
    dmin = min(filas, key=lambda f: f["desviacion_pct"])
    dmax = max(filas, key=lambda f: f["desviacion_pct"])
    prom_abs = sum(abs(f["desviacion_pct"]) for f in filas) / len(filas)
    # correlación de Spearman simple entre desviación y densidad
    def rangos(v):
        o = sorted(range(len(v)), key=lambda i: v[i])
        rr = [0] * len(v)
        for k, i in enumerate(o):
            rr[i] = k + 1
        return rr
    a, b = rangos([f["desviacion_pct"] for f in filas]), rangos([f["densidad"] for f in filas])
    n = len(filas)
    rho = 1 - 6 * sum((x - y) ** 2 for x, y in zip(a, b)) / (n * (n * n - 1))
    r = {
        "clave": "esfuerzo", "numero": 8, "nombre": "Desviación de esfuerzo", "tipo": "Proyecto",
        "que_mide": "Diferencia entre el esfuerzo esperado por tamaño y el esfuerzo real (commits) de cada módulo.",
        "formula": "(real − esperado) / esperado × 100",
        "ubicacion": "Gestión del proyecto: reparto del trabajo entre módulos durante todo el historial.",
        "valor": round(prom_abs, 1),
        "resultado_general": (f"rango {dmin['desviacion_pct']:+.1f}% ({dmin['modulo']}) a {dmax['desviacion_pct']:+.1f}% "
                              f"({dmax['modulo']}) · |desviación| media {prom_abs:.0f}%"),
        "valor_corto": f"{dmin['desviacion_pct']:+.0f}…{dmax['desviacion_pct']:+.0f}%",
        "detalle_corto": f"ρ(desviación, densidad) = {rho:+.2f}",
        "valoracion": "info", "etiqueta": "REASIGNADO AL RIESGO" if rho > 0.5 else "DESBALANCEADO",
        "interpretacion": (f"Los módulos pequeños de integración reciben mucho más esfuerzo del que su tamaño sugiere "
                           f"({dmax['modulo']} {dmax['desviacion_pct']:+.0f}%), y el más grande, {dmin['modulo']}, mucho menos "
                           f"({dmin['desviacion_pct']:+.0f}%). La correlación de rangos entre desviación y densidad de defectos "
                           f"es ρ = {rho:+.2f}."),
        "significado": ("El esfuerzo no se reparte por tamaño sino por riesgo: el equipo trabaja más donde hay más defectos. "
                        "Es una desviación sana para un equipo ágil, no un problema de planeación."),
        "referencia": "|desviación| ≤ 25% equilibrado; > 100% fuerte reasignación. El commit se usa como unidad de esfuerzo.",
        "total_kloc": tk, "total_commits": tc, "spearman_desv_densidad": rho, "por_modulo": filas,
    }
    archivos = []
    d = comun.carpeta("esfuerzo")
    if comun.CFG["graficos"]:
        archivos.append(graficos.esfuerzo(os.path.join(d, "esfuerzo.png"), filas))
    md = comun.md_resultado(r) + "\n### Por módulo\n\n" + md_tabla(
        ["Módulo", "KLOC", "Commits", "Esperado", "Real", "Desviación", "Def./KLOC"],
        [[f["modulo"], f"{f['kloc']:.3f}", f["commits"], f"{f['esperado_pct']:.1f}%", f"{f['real_pct']:.1f}%",
          f"{f['desviacion_pct']:+.1f}%", f"{f['densidad']:.2f}"] for f in filas])
    archivos = list(comun.guardar("esfuerzo", r, md)) + archivos
    comun.cerrar(r, archivos)
    return r


# ==========================================================================
# 9. Arquitectura, patrones y frameworks
# ==========================================================================
PATRONES = [
    ("Strategy", "Comportamiento", r"^type (Plugin|Resolver) interface",
     "contrato común con implementaciones intercambiables (plugins, resolvedores)"),
    ("Repository", "Arquitectónico", r"^type Store interface",
     "store.Store abstrae el acceso a secretos; el dominio no conoce el backend"),
    ("Functional Options", "Idiomático Go", r"^type \w*Options? func\(", "configuración por funciones Option"),
    ("Factory genérica", "Creacional", r"^type Factory\[|^func New\[", "constructores genéricos New[T] / Factory[T]"),
    ("Builder", "Creacional", r"_builder\) Build\(", "mensajes protobuf construidos con *_builder.Build()"),
    ("Interceptor / Middleware", "Comportamiento", r"Interceptor(Func)?\(|func \w*[Ii]nterceptor\(",
     "intercepta RPC entrantes (gating hasta registrar el plugin)"),
    ("Stub / Proxy", "Estructural", r"^type (Stub|stub) (interface|struct)", "representante local del demonio remoto"),
    ("Adapter", "Estructural", r"client\.(Get|List|Store|Erase)\(\w*\.?ProgramFunc",
     "traduce credential-helpers de Docker al contrato de store"),
]
FRAMEWORKS = {
    "connectrpc.com/connect": "RPC (compatible gRPC) entre demonio, cliente y plugins",
    "google.golang.org/protobuf": "Contratos de la API (Protocol Buffers)",
    "filippo.io/age": "Cifrado de archivos (backend posixage)",
    "golang.org/x/crypto": "Primitivas criptográficas (scrypt)",
    "github.com/godbus/dbus/v5": "D-Bus / Secret Service (llavero Linux)",
    "github.com/keybase/go-keychain": "Keychain de macOS",
    "github.com/danieljoos/wincred": "Credential Manager de Windows",
    "github.com/docker/docker-credential-helpers": "credential-helpers de Docker",
    "github.com/spf13/cobra": "CLI de los plugins",
    "go.opentelemetry.io/otel": "Trazas y métricas (OpenTelemetry)",
    "github.com/stretchr/testify": "Aserciones en pruebas",
    "golang.org/x/sync": "Concurrencia (errgroup)",
    "github.com/sirupsen/logrus": "Logging",
}


def _archivos_go(base, pruebas=False):
    for raiz, dirs, files in os.walk(base):
        dirs[:] = [x for x in dirs if x not in ("vendor", ".git", "testdata") and not x.startswith(".")]
        for f in files:
            if f.endswith(".go") and (pruebas or not f.endswith("_test.go")):
                yield os.path.join(raiz, f)


def arquitectura(args=None):
    comun.encabezado(
        9, "Arquitectura, patrones y frameworks", "proyecto",
        "estructura de módulos y sus dependencias, patrones de diseño presentes y frameworks usados.",
        "conteo de módulos/paquetes/imports entre módulos (go.work, go.mod e imports) + detección de patrones",
        "estructura completa del repositorio (monorepo con Go workspaces).")
    repo = comun.CFG["repo"]
    mods = comun.modulos()
    rutas_mod = {}
    for m in mods:
        t = open(os.path.join(repo, m, "go.mod"), encoding="utf-8").read()
        rutas_mod[m] = re.search(r"^module\s+(\S+)", t, re.M).group(1)
    por_ruta = sorted(rutas_mod.items(), key=lambda kv: -len(kv[1]))
    aristas, paquetes, archivos_n = {}, {}, {}
    hallazgos = {p[0]: [] for p in PATRONES}
    for m in mods:
        pk = set()
        n = 0
        for f in _archivos_go(os.path.join(repo, m)):
            n += 1
            pk.add(os.path.dirname(f))
            texto = open(f, encoding="utf-8", errors="ignore").read()
            for imp in re.findall(r'"(github\.com/docker/secrets-engine/[^"]+)"', texto):
                dest = next((mm for mm, ruta in por_ruta if imp == ruta or imp.startswith(ruta + "/")), None)
                if dest and dest != m:
                    aristas[(m, dest)] = aristas.get((m, dest), 0) + 1
            relf = comun.rel(f)
            if "go-keychain" in relf:
                continue
            for nombre, _, rx, _ in PATRONES:
                for mt in re.finditer(rx, texto, re.M):
                    linea = texto[: mt.start()].count("\n") + 1
                    hallazgos[nombre].append(f"{relf}:{linea}")
        paquetes[m] = len(pk)
        archivos_n[m] = n
    # ciclos entre módulos
    grafo = {m: [d for (o, d) in aristas if o == m] for m in mods}
    ciclos = []

    def dfs(n, pila):
        for s in grafo[n]:
            if s in pila:
                ciclos.append(pila[pila.index(s):] + [s])
            elif len(pila) < len(mods):
                dfs(s, pila + [s])
    for m in mods:
        dfs(m, [m])
    # frameworks (dependencias directas de los go.mod)
    deps = {}
    for m in mods:
        t = open(os.path.join(repo, m, "go.mod"), encoding="utf-8").read()
        for ruta, ver, ind in re.findall(r"^\s*(?:require\s+)?([a-z0-9][^\s]+\.[^\s]+)\s+(v[^\s]+)(\s*// indirect)?", t, re.M):
            if not ind and not ruta.startswith("github.com/docker/secrets-engine"):
                deps.setdefault(ruta, set()).add(m)
    agrupado = {}
    for r_, ms in deps.items():
        for k in FRAMEWORKS:
            if r_ == k or r_.startswith(k + "/"):
                agrupado.setdefault(k, set()).update(ms)
    fw = [(k, FRAMEWORKS[k], sorted(ms)) for k, ms in agrupado.items()]
    otras = sorted(r_ for r_ in deps if not any(r_ == k or r_.startswith(k + "/") for k in FRAMEWORKS))

    tabla(["Módulo", "Ruta Go", "Paquetes", "Archivos .go", "Depende de"],
          [[m, rutas_mod[m].replace("github.com/docker/secrets-engine", "…"), paquetes[m], archivos_n[m],
            ", ".join(d for (o, d) in aristas if o == m) or "—"] for m in mods], alinear="llrrl", titulo="Módulos y dependencias")
    tabla(["Patrón", "Tipo", "Apariciones", "Ejemplo en el código"],
          [[p[0], p[1], len(hallazgos[p[0]]), hallazgos[p[0]][0] if hallazgos[p[0]] else "—"] for p in PATRONES],
          alinear="llrl", titulo="Patrones de diseño detectados")
    abrev = lambda ms: "los 6 módulos" if len(ms) == len(mods) else ", ".join(ms)
    tabla(["Framework / biblioteca", "Función", "Módulos"], [[a, b, abrev(cc)] for a, b, cc in fw], alinear="lll",
          titulo="Frameworks y bibliotecas (dependencias directas)")
    n_pat = sum(1 for p in PATRONES if hallazgos[p[0]])
    val = "bueno" if not ciclos else "mejorable"
    r = {
        "clave": "arquitectura", "numero": 9, "nombre": "Arquitectura y patrones", "tipo": "Proyecto",
        "que_mide": "Estructura de módulos y dependencias, patrones de diseño y frameworks.",
        "formula": "conteo de módulos, paquetes, imports entre módulos, patrones y dependencias directas",
        "ubicacion": "Toda la estructura del repositorio (go.work + go.mod + imports).",
        "valor": n_pat,
        "resultado_general": (f"{len(mods)} módulos · {sum(paquetes.values())} paquetes · {len(aristas)} dependencias entre "
                              f"módulos · {'sin ciclos' if not ciclos else f'{len(ciclos)} ciclos'} · {n_pat} patrones · "
                              f"{len(fw)} frameworks"),
        "valor_corto": f"{len(mods)} módulos", "detalle_corto": f"{n_pat} patrones · {len(fw)} frameworks · sin ciclos" if not ciclos else "con ciclos",
        "valoracion": val, "etiqueta": "MODULAR (ACÍCLICA)" if not ciclos else "CON CICLOS",
        "interpretacion": ("Las dependencias fluyen en un solo sentido: de los plugins hacia el núcleo (plugin, client, "
                           "store) y de ahí hacia x, que concentra los contratos protobuf y utilidades compartidas. Ningún "
                           "módulo base depende de un plugin, así que el grafo es acíclico y cada módulo se versiona con "
                           "sus propios tags."),
        "significado": ("La arquitectura demonio + plugins sobre RPC local aísla los backends de almacenamiento detrás de "
                        "interfaces (Strategy/Repository) y explica la complejidad baja: cada pieza es pequeña y sustituible."),
        "referencia": "Principio de dependencias acíclicas (Martin, 2017); patrones según Gamma et al. (1994).",
        "modulos": {m: {"ruta": rutas_mod[m], "paquetes": paquetes[m], "archivos": archivos_n[m]} for m in mods},
        "dependencias": [{"de": o, "a": d, "imports": n} for (o, d), n in sorted(aristas.items())],
        "ciclos": ciclos, "patrones": {p[0]: {"tipo": p[1], "descripcion": p[3], "apariciones": len(hallazgos[p[0]]),
                                              "ubicaciones": hallazgos[p[0]][:10]} for p in PATRONES},
        "frameworks": [{"dependencia": a, "funcion": b, "modulos": cc} for a, b, cc in fw],
        "otras_dependencias_directas": otras,
    }
    archivos = []
    d = comun.carpeta("arquitectura")
    if comun.CFG["graficos"]:
        archivos.append(dibujar_arquitectura(os.path.join(d, "arquitectura.png"), r))
    md = comun.md_resultado(r) + "\n### Dependencias entre módulos\n\n" + md_tabla(
        ["De", "A", "Imports"], [[o, d_, n] for (o, d_), n in sorted(aristas.items())]) + "\n\n### Patrones\n\n" + md_tabla(
        ["Patrón", "Tipo", "Apariciones", "Ejemplo"],
        [[p[0], p[1], len(hallazgos[p[0]]), hallazgos[p[0]][0] if hallazgos[p[0]] else "—"] for p in PATRONES]) + \
        "\n\n### Frameworks\n\n" + md_tabla(["Dependencia", "Función", "Módulos"], [[a, b, ", ".join(cc)] for a, b, cc in fw])
    archivos = list(comun.guardar("arquitectura", r, md)) + archivos
    comun.cerrar(r, archivos)
    return r


DESCRIPCION = {
    "client": "cliente para consumidores", "plugin": "SDK para escribir plugins", "store": "backends: llavero y age",
    "plugins/pass": "plugin docker pass", "plugins/credentialhelper": "adaptador credential-helper",
    "x": "API protobuf, IPC, utilidades",
}


def dibujar_arquitectura(ruta, r_arq):
    """Grafo de módulos (capas por profundidad de dependencias) anotado con las
    métricas de producto ya calculadas (si existen en la carpeta de salida)."""
    mods = list(r_arq["modulos"].keys())
    deps = [(x["de"], x["a"], x["imports"]) for x in r_arq["dependencias"]]
    # capa = longitud del camino más largo hacia una hoja
    memo = {}

    def nivel(m, vis=()):
        if m in memo:
            return memo[m]
        hijos = [d for o, d, _ in deps if o == m and d not in vis]
        memo[m] = 0 if not hijos else 1 + max(nivel(h, vis + (m,)) for h in hijos)
        return memo[m]
    capas = {}
    for m in mods:
        capas.setdefault(nivel(m), []).append(m)
    nodos = {}
    max_n = max(capas)
    fijas = {"plugins/credentialhelper": (3.2, 5.75), "plugins/pass": (9.3, 5.75), "client": (1.9, 3.45),
             "plugin": (5.0, 3.45), "store": (10.6, 3.45), "x": (6.25, 1.15)}
    if set(mods) == set(fijas):
        for m in mods:
            nodos[m] = (*fijas[m], DESCRIPCION.get(m, ""))
        capas = {}
    for k, ms in capas.items():
        y = 1.25 + (k / max(max_n, 1)) * 4.5
        for i, m in enumerate(sorted(ms)):
            x = (i + 1) * 12.5 / (len(ms) + 1)
            nodos[m] = (x, y, DESCRIPCION.get(m, ""))
    cc, cov, den, esf = comun.cargar("complejidad"), comun.cargar("cobertura"), comun.cargar("densidad"), comun.cargar("esfuerzo")
    met = {}
    for m in mods:
        mm = {}
        if cc:
            p = next((x for x in cc["por_modulo"] if x["modulo"] == m), None)
            if p:
                mm["cc"], mm["cc_max"] = p["media"], p["maximo"]
        if cov:
            p = next((x for x in cov["por_modulo"] if x["modulo"] == m), None)
            if p:
                mm["cov"] = p["pct_ajustado"]
        if den:
            p = next((x for x in den["por_modulo"] if x["modulo"] == m), None)
            if p:
                mm["dens"] = p["densidad"]
        if esf:
            p = next((x for x in esf["por_modulo"] if x["modulo"] == m), None)
            if p:
                mm["desv"] = p["desviacion_pct"]
        met[m] = mm
    return graficos.arquitectura(ruta, nodos, deps, met)
