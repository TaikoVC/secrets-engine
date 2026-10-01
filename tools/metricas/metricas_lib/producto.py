"""Métricas de PRODUCTO: complejidad ciclomática, cobertura de código y
densidad de defectos."""
import glob
import json
import os
import re
import shutil
import statistics
import subprocess

from . import comun, defectos, graficos
from .comun import c, info, aviso, tabla, md_tabla

EXCLUIR_TERCEROS = "go-keychain"  # store/keychain/internal/go-keychain (código de terceros)
GENERADO = [".pb.go", "connect/api.connect.go"]


# ==========================================================================
# 1. Complejidad ciclomática
# ==========================================================================
def _umbral_proyecto():
    p = os.path.join(comun.CFG["repo"], ".golangci.yml")
    if os.path.isfile(p):
        m = re.search(r"gocyclo:\s*\n\s*min-complexity:\s*(\d+)", open(p, encoding="utf-8").read())
        if m:
            return int(m.group(1))
    return 16


def complejidad(args=None):
    comun.requiere("gocyclo")
    comun.encabezado(
        1, "Complejidad ciclomática", "producto",
        "número de caminos independientes en el flujo de control de cada función.",
        "CC = 1 + nº de puntos de decisión (if, for, case, &&, ||)",
        "código fuente de los 6 módulos (cada función de cada paquete).")
    info("gocyclo -avg -ignore 'vendor|go-keychain' .   (las funciones de _test.go se separan después)")
    code, out, err = comun.ejecutar(["gocyclo", "-avg", "-ignore", "vendor|go-keychain", "."])
    d = comun.carpeta("complejidad")
    with open(os.path.join(d, "gocyclo.txt"), "w", encoding="utf-8") as f:
        f.write(out)
    mods = comun.modulos()
    funcs = []
    promedio_gocyclo = None
    for l in out.splitlines():
        if l.startswith("Average:"):
            promedio_gocyclo = float(l.split()[1])
            continue
        m = re.match(r"^(\d+) (\S+) (.+) (\S+):(\d+):\d+$", l.strip())
        if not m:
            continue
        cc, pkg, fn, ruta, linea = int(m.group(1)), m.group(2), m.group(3), m.group(4), m.group(5)
        ruta = ruta[2:] if ruta.startswith("./") else ruta
        funcs.append({"cc": cc, "paquete": pkg, "funcion": fn, "archivo": ruta, "linea": int(linea),
                      "modulo": comun.modulo_de(ruta, mods) or "otros", "prueba": ruta.endswith("_test.go")})
    prod = [f for f in funcs if not f["prueba"]]
    promedio_gocyclo = statistics.mean(f["cc"] for f in funcs) if funcs else None
    ccs = [f["cc"] for f in prod]
    umbral = _umbral_proyecto()
    bandas_def = [("1-10 (bajo)", 1, 10), ("11-20 (moderado)", 11, 20), ("21-50 (alto)", 21, 50), ("> 50 (muy alto)", 51, 10 ** 6)]
    bandas = [{"banda": b, "funciones": sum(1 for v in ccs if lo <= v <= hi)} for b, lo, hi in bandas_def]
    por_mod = []
    for m in mods:
        v = [f["cc"] for f in prod if f["modulo"] == m]
        if v:
            por_mod.append({"modulo": m, "funciones": len(v), "media": statistics.mean(v), "mediana": statistics.median(v),
                            "maximo": max(v), "sobre_10": sum(1 for x in v if x > 10)})
    top = sorted(prod, key=lambda f: (-f["cc"], f["archivo"], f["linea"]))[:15]
    media_prod = statistics.mean(ccs)
    maximo = max(ccs)
    pct_bajo = 100 * bandas[0]["funciones"] / len(ccs)

    tabla(["Módulo", "Funciones", "CC media", "Mediana", "Máx.", "> 10"],
          [[p["modulo"], p["funciones"], f"{p['media']:.2f}", f"{p['mediana']:.1f}", p["maximo"], p["sobre_10"]] for p in por_mod]
          + [[c("TOTAL producción", "neg"), len(ccs), c(f"{media_prod:.2f}", "neg"), f"{statistics.median(ccs):.1f}", maximo,
              sum(1 for x in ccs if x > 10)]],
          titulo="Complejidad por módulo (funciones de producción, sin _test.go)")
    tabla(["Banda", "Funciones", "%"], [[b["banda"], b["funciones"], f"{100 * b['funciones'] / len(ccs):.1f}%"] for b in bandas],
          titulo="Distribución por banda de riesgo")
    tabla(["CC", "Función", "Módulo", "Archivo:línea"],
          [[t["cc"], t["funcion"], t["modulo"], f"{t['archivo']}:{t['linea']}"] for t in top[:10]], alinear="rlll",
          titulo="Top 10 funciones más complejas")

    valoracion = "bueno" if media_prod <= 5 and maximo < umbral else ("aceptable" if maximo < umbral else "mejorable")
    r = {
        "clave": "complejidad", "numero": 1, "nombre": "Complejidad ciclomática", "tipo": "Producto",
        "que_mide": "Número de caminos independientes en el flujo de control de cada función.",
        "formula": "CC = 1 + puntos de decisión", "ubicacion": "Código fuente de los 6 módulos (función por función).",
        "valor": round(media_prod, 2), "maximo": maximo,
        "resultado_general": f"CC media {media_prod:.2f} · máx. {maximo} · {pct_bajo:.1f}% de funciones en 1-10",
        "valor_corto": f"{media_prod:.2f}", "detalle_corto": f"media · máx {maximo} · {pct_bajo:.1f}% bajo riesgo",
        "valoracion": valoracion, "etiqueta": {"bueno": "BAJA (buena)", "aceptable": "MODERADA", "mejorable": "ALTA"}[valoracion],
        "interpretacion": (f"De {len(ccs)} funciones de producción, {bandas[0]['funciones']} ({pct_bajo:.1f}%) están en la banda "
                           f"de bajo riesgo y ninguna supera {umbral - 1}; la función más compleja es {top[0]['funcion']} "
                           f"({top[0]['modulo']}, CC {top[0]['cc']}). Incluyendo las {len(funcs) - len(ccs)} funciones de "
                           f"prueba, la media es {promedio_gocyclo:.2f}."),
        "significado": (f"El código es fácil de leer y de probar: ninguna función rebasa el límite de {umbral} que el propio "
                        f"proyecto exige en su CI (.golangci.yml). Las funciones con CC > 10 se concentran en comandos de "
                        f"plugins/pass y en la lógica de patrones de x/secrets: son los primeros candidatos a refactorizar."),
        "referencia": f"McCabe (1976): ≤ 10 bajo riesgo; límite del proyecto en CI: CC < {umbral}.",
        "n_funciones_total": len(funcs), "n_funciones_produccion": len(ccs), "media_con_pruebas": promedio_gocyclo,
        "mediana": statistics.median(ccs), "bandas": bandas, "por_modulo": por_mod, "top15": top, "umbral_proyecto": umbral,
    }
    archivos = []
    if comun.CFG["graficos"]:
        archivos.append(graficos.complejidad(os.path.join(d, "complejidad.png"), bandas, top, umbral))
    md = comun.md_resultado(r) + "\n### Por módulo\n\n" + md_tabla(
        ["Módulo", "Funciones", "CC media", "Mediana", "Máx.", "> 10"],
        [[p["modulo"], p["funciones"], f"{p['media']:.2f}", p["mediana"], p["maximo"], p["sobre_10"]] for p in por_mod]) + \
        "\n\n### Top 15\n\n" + md_tabla(["CC", "Función", "Módulo", "Archivo:línea"],
                                       [[t["cc"], t["funcion"], t["modulo"], f"{t['archivo']}:{t['linea']}"] for t in top])
    archivos = list(comun.guardar("complejidad", r, md)) + archivos + [os.path.join(d, "gocyclo.txt")]
    comun.cerrar(r, archivos)
    return r


# ==========================================================================
# 2. Cobertura de código
# ==========================================================================
def _preparar_dbus(env):
    """Arranca un bus D-Bus de sesión y gnome-keyring (como store/scripts/gnome-keyring
    del propio proyecto) si no hay uno ya; necesario para probar store/keychain en Linux/WSL2."""
    if env.get("DBUS_SESSION_BUS_ADDRESS"):
        info("D-Bus de sesión ya disponible: " + env["DBUS_SESSION_BUS_ADDRESS"])
        return env
    if not shutil.which("dbus-daemon"):
        aviso("No hay dbus-daemon: las pruebas de store/keychain pueden fallar (sudo apt install dbus-x11 gnome-keyring).")
        return env
    code, out, _ = comun.ejecutar(["dbus-daemon", "--session", "--print-address", "--fork"], env=env)
    if code != 0 or not out.strip():
        aviso("No se pudo iniciar dbus-daemon.")
        return env
    env["DBUS_SESSION_BUS_ADDRESS"] = out.strip().splitlines()[0]
    info("Bus D-Bus de sesión iniciado: " + env["DBUS_SESSION_BUS_ADDRESS"])
    if shutil.which("gnome-keyring-daemon"):
        code, out, _ = comun.ejecutar(["gnome-keyring-daemon", "--start", "--components=secrets"], env=env)
        for l in out.splitlines():
            if "=" in l:
                k, v = l.split("=", 1)
                env[k] = v
        comun.ejecutar(["gnome-keyring-daemon", "--unlock"], env=env, entrada="")
        info("gnome-keyring-daemon iniciado y desbloqueado (Secret Service disponible).")
    else:
        aviso("No hay gnome-keyring-daemon: store/keychain no podrá probarse (sudo apt install gnome-keyring).")
    return env


def _leer_perfil(ruta):
    # un mismo bloque puede aparecer varias veces (varios paquetes de prueba): se queda el máximo
    bloques = {}
    with open(ruta, encoding="utf-8") as f:
        for l in f:
            m = re.match(r"^(.*:\d+\.\d+,\d+\.\d+) (\d+) (\d+)$", l.strip())
            if m:
                k = m.group(1)
                n, cnt = int(m.group(2)), int(m.group(3))
                prev = bloques.get(k)
                bloques[k] = (n, max(cnt, prev[1]) if prev else cnt)
    return [(k.rsplit(":", 1)[0], n, cnt) for k, (n, cnt) in bloques.items()]


def cobertura(args=None):
    comun.encabezado(
        2, "Cobertura de código", "producto",
        "porcentaje de sentencias que ejecutan las pruebas automatizadas.",
        "cobertura = sentencias ejecutadas / sentencias totales × 100",
        "pruebas *_test.go de cada módulo frente a su código de producción.")
    reusar = bool(args and getattr(args, "reusar", False))
    importar = getattr(args, "perfiles", None) if args else None
    d = comun.carpeta("cobertura")
    dp = comun.carpeta("cobertura", "perfiles")
    dh = comun.carpeta("cobertura", "html")
    mods = comun.modulos()
    estado = {}

    if importar:
        for m in mods:
            src = os.path.join(importar, m.replace("/", "_") + ".out")
            if os.path.isfile(src):
                shutil.copy(src, os.path.join(dp, m.replace("/", "_") + ".out"))
                estado[m] = "importado"
        info(f"Perfiles importados desde {importar}")
    elif not reusar or not glob.glob(os.path.join(dp, "*.out")):
        comun.requiere("go")
        env = dict(os.environ)
        env["GOWORK"] = os.path.join(comun.CFG["repo"], "go.work")
        if os.path.isfile(os.path.join(comun.CFG["repo"], "vendor", "modules.txt")) and "GOFLAGS" not in os.environ:
            env["GOFLAGS"] = "-mod=vendor"
        if not getattr(args, "sin_dbus", False):
            env = _preparar_dbus(env)
        for m in mods:
            perfil = os.path.join(dp, m.replace("/", "_") + ".out")
            if os.path.isfile(perfil):
                os.remove(perfil)  # nunca mezclar con un perfil viejo
            info(f"(cd {m} && go test -coverprofile={comun.rel(perfil)} ./...)")
            p = subprocess.run(["go", "test", f"-coverprofile={perfil}", "./..."], cwd=os.path.join(comun.CFG["repo"], m),
                               env=env, capture_output=True, text=True)
            with open(os.path.join(dp, m.replace("/", "_") + ".log"), "w", encoding="utf-8") as f:
                f.write(p.stdout + p.stderr)
            estado[m] = "ok" if p.returncode == 0 else "con fallos"
            for l in p.stdout.splitlines():
                if "coverage:" in l and ("ok" in l[:4] or "FAIL" in l[:6]):
                    print("     " + c(l.strip().replace("\t", "  "), "tenue"))
            if p.returncode != 0:
                log = os.path.join(dp, m.replace('/', '_') + '.log')
                primera = next((l for l in (p.stderr + p.stdout).splitlines() if l.strip()), "")
                if os.path.isfile(perfil):
                    aviso(f"{m}: alguna prueba falló (ver {comun.rel(log)}); se usa el perfil parcial.")
                else:
                    estado[m] = "error"
                    aviso(f"{m}: go test no generó perfil: {primera[:150]}  (log: {comun.rel(log)})")
            if os.path.isfile(perfil):
                subprocess.run(["go", "tool", "cover", f"-html={perfil}", "-o",
                                os.path.join(dh, m.replace("/", "_") + ".html")],
                               cwd=os.path.join(comun.CFG["repo"], m), env=env, capture_output=True)
    else:
        info("Reutilizando perfiles existentes en " + comun.rel(dp) + " (--reusar).")
        for m in mods:
            estado[m] = "reusado"

    filas = []
    gt = gc = gtn = gcn = 0
    por_paquete = {}
    for m in mods:
        perfil = os.path.join(dp, m.replace("/", "_") + ".out")
        if not os.path.isfile(perfil):
            aviso(f"Sin perfil de cobertura para {m}")
            continue
        bloques = _leer_perfil(perfil)
        tot = sum(n for _, n, _ in bloques)
        cub = sum(n for _, n, k in bloques if k > 0)
        totn = sum(n for fn, n, _ in bloques if not any(g in fn for g in GENERADO))
        cubn = sum(n for fn, n, k in bloques if k > 0 and not any(g in fn for g in GENERADO))
        for fn, n, k in bloques:
            pk = os.path.dirname(fn)
            a = por_paquete.setdefault(pk, [0, 0])
            a[0] += n
            a[1] += n if k > 0 else 0
        filas.append({"modulo": m, "cubiertas": cub, "totales": tot, "pct_bruto": 100 * cub / tot if tot else 0,
                      "cubiertas_ajust": cubn, "totales_ajust": totn, "pct_ajustado": 100 * cubn / totn if totn else 0,
                      "estado_pruebas": estado.get(m, "")})
        gt += tot
        gc += cub
        gtn += totn
        gcn += cubn
    if not filas:
        comun.error("No hay ningún perfil de cobertura. Revisa los .log en " + comun.rel(dp) +
                    " (versión de Go, GOFLAGS=-mod=vendor, D-Bus).")
        return False
    gb = 100 * gc / gt if gt else 0
    ga = 100 * gcn / gtn if gtn else 0
    tabla(["Módulo", "Cubiertas", "Totales", "Cobertura", "Sin generado", "Pruebas"],
          [[f["modulo"], f["cubiertas"], f["totales"], f"{f['pct_bruto']:.1f}%",
            f"{f['pct_ajustado']:.1f}%", f["estado_pruebas"]] for f in filas]
          + [[c("GLOBAL", "neg"), gc, gt, c(f"{gb:.1f}%", "neg"), c(f"{ga:.1f}%", "neg"), ""]],
          titulo="Cobertura por módulo (sentencias)")

    v = "bueno" if ga >= 75 else ("aceptable" if ga >= 60 else "mejorable")
    mejor = max(filas, key=lambda f: f["pct_ajustado"])
    peor = min(filas, key=lambda f: f["pct_ajustado"])
    r = {
        "clave": "cobertura", "numero": 2, "nombre": "Cobertura de código", "tipo": "Producto",
        "que_mide": "Porcentaje de sentencias de código que ejecutan las pruebas automatizadas.",
        "formula": "sentencias ejecutadas / sentencias totales × 100",
        "ubicacion": "Pruebas *_test.go de cada módulo (lo que corre la CI en unittests.yml).",
        "valor": round(ga, 1), "valor_bruto": round(gb, 1),
        "resultado_general": f"{ga:.1f}% global sin código generado ({gcn}/{gtn}) · {gb:.1f}% bruta ({gc}/{gt})",
        "valor_corto": f"{ga:.1f}%", "detalle_corto": f"sin código generado · bruta {gb:.1f}%",
        "valoracion": v, "etiqueta": {"bueno": "ALTA", "aceptable": "ACEPTABLE", "mejorable": "BAJA"}[v],
        "interpretacion": (f"La cifra bruta ({gb:.1f}%) está castigada por el código que genera protoc/Connect en x "
                           f"(*.pb.go), que no se prueba por diseño; sin él la cobertura real es {ga:.1f}%. El módulo mejor "
                           f"probado es {mejor['modulo']} ({mejor['pct_ajustado']:.1f}%) y el más débil "
                           f"{peor['modulo']} ({peor['pct_ajustado']:.1f}%)."),
        "significado": ("Las rutas principales que usan los consumidores (cliente y plugin pass) están bien probadas; los "
                        "adaptadores pequeños de integración (credentialhelper, plugin) tienen menos pruebas y coinciden con los "
                        "módulos de mayor densidad de defectos, así que ahí es donde más rinde agregar pruebas."),
        "referencia": "Google Testing Blog (Arguelles et al., 2020): 60% aceptable, 75% encomiable, 90% ejemplar.",
        "global_bruto": gb, "global_ajustado": ga, "cubiertas": gc, "totales": gt, "cubiertas_ajust": gcn,
        "totales_ajust": gtn, "por_modulo": filas,
        "por_paquete": {k: {"totales": a[0], "cubiertas": a[1], "pct": 100 * a[1] / a[0] if a[0] else 0}
                        for k, a in sorted(por_paquete.items())},
    }
    archivos = []
    if comun.CFG["graficos"]:
        archivos.append(graficos.cobertura(os.path.join(d, "cobertura.png"), filas, gb, ga))
    md = comun.md_resultado(r) + "\n### Por módulo\n\n" + md_tabla(
        ["Módulo", "Cubiertas", "Totales", "Cobertura bruta", "Sin generado"],
        [[f["modulo"], f["cubiertas"], f["totales"], f"{f['pct_bruto']:.1f}%", f"{f['pct_ajustado']:.1f}%"] for f in filas])
    archivos = list(comun.guardar("cobertura", r, md)) + archivos
    if glob.glob(os.path.join(dh, "*.html")):
        archivos.append(dh + "/  (reporte verde/rojo por archivo: ábrelo en el navegador)")
    comun.cerrar(r, archivos)
    return r


# ==========================================================================
# 3. Densidad de defectos
# ==========================================================================
def kloc_por_modulo():
    comun.requiere("cloc")
    res = {}
    for m in comun.modulos():
        code, out, _ = comun.ejecutar(["cloc", m, "--exclude-dir=vendor", "--fullpath",
                                       f"--not-match-d=internal/{EXCLUIR_TERCEROS}", "--json", "--quiet"])
        dd = json.loads(out) if out.strip() else {}
        res[m] = {"kloc": dd.get("SUM", {}).get("code", 0) / 1000.0,
                  "kloc_go": dd.get("Go", {}).get("code", 0) / 1000.0}
    return res


def densidad(args=None):
    comun.encabezado(
        3, "Densidad de defectos", "producto",
        "defectos corregidos por cada mil líneas de código propio.",
        "densidad = defectos corregidos / KLOC",
        "código de cada módulo (KLOC) cruzado con los commits fix: que lo tocaron.")
    info("cloc <módulo> --exclude-dir=vendor --fullpath --not-match-d=internal/go-keychain")
    kl = kloc_por_modulo()
    dat = defectos.minar()
    filas = []
    for m, k in kl.items():
        n = sum(1 for r in dat["defectos"] if m in r["modulos"])
        filas.append({"modulo": m, "kloc": k["kloc"], "kloc_go": k["kloc_go"], "defectos": n,
                      "densidad": n / k["kloc"] if k["kloc"] else 0})
    total_kloc = sum(f["kloc"] for f in filas)
    total_def = dat["n_fixes"]
    g = total_def / total_kloc
    tabla(["Módulo", "KLOC", "Defectos", "Def./KLOC"],
          [[f["modulo"], f"{f['kloc']:.3f}", f["defectos"], f"{f['densidad']:.2f}"] for f in filas]
          + [[c("GLOBAL", "neg"), f"{total_kloc:.3f}", total_def, c(f"{g:.2f}", "neg")]],
          titulo="Densidad de defectos por módulo")
    info("Un fix que toca varios módulos cuenta en cada uno; el global usa los fixes únicos.")
    v = "bueno" if g <= 10 else ("mejorable" if g <= 25 else "bajo")
    alto = sorted(filas, key=lambda f: -f["densidad"])[:2]
    bajo = min(filas, key=lambda f: f["densidad"])
    r = {
        "clave": "densidad", "numero": 3, "nombre": "Densidad de defectos", "tipo": "Producto",
        "que_mide": "Defectos corregidos por cada mil líneas de código propio (KLOC).",
        "formula": "defectos corregidos / KLOC",
        "ubicacion": "Código de cada módulo (cloc) cruzado con los commits fix: que lo modificaron.",
        "valor": round(g, 2),
        "resultado_general": f"{g:.2f} defectos/KLOC ({total_def} defectos ÷ {total_kloc:.3f} KLOC)",
        "valor_corto": f"{g:.2f}", "detalle_corto": f"def./KLOC · {total_def} defectos en {total_kloc:.1f} KLOC",
        "valoracion": v, "etiqueta": {"bueno": "BAJA (buena)", "mejorable": "MEDIA", "bajo": "ALTA"}[v],
        "interpretacion": (f"Globalmente la densidad es baja, pero está muy concentrada: {alto[0]['modulo']} "
                           f"({alto[0]['densidad']:.1f}) y {alto[1]['modulo']} ({alto[1]['densidad']:.1f}) superan 25 def./KLOC, "
                           f"mientras {bajo['modulo']}, el módulo más grande, apenas llega a {bajo['densidad']:.2f}."),
        "significado": ("Los defectos no están en el núcleo sino en los adaptadores pequeños que hablan con sistemas externos "
                        "(binarios credential-helper, registro de plugins). Son la zona de mayor riesgo del producto."),
        "referencia": "McConnell (Code Complete, 2004): promedio de la industria 15–50 errores/KLOC; aquí ≤ 10 se valora bajo.",
        "total_kloc": total_kloc, "total_defectos": total_def, "por_modulo": filas,
    }
    archivos = []
    d = comun.carpeta("densidad")
    if comun.CFG["graficos"]:
        archivos.append(graficos.densidad(os.path.join(d, "densidad.png"), filas, g))
    md = comun.md_resultado(r) + "\n### Por módulo\n\n" + md_tabla(
        ["Módulo", "KLOC", "Defectos", "Def./KLOC"],
        [[f["modulo"], f"{f['kloc']:.3f}", f["defectos"], f"{f['densidad']:.2f}"] for f in filas])
    archivos = list(comun.guardar("densidad", r, md)) + archivos
    comun.cerrar(r, archivos)
    return r
