"""Punto de entrada de la CLI `metricas`."""
import argparse
import os
import shutil
import subprocess
import sys

from . import comun, producto, proceso, proyecto, resumen

AYUDA = """\
Calcula las métricas de producto, proceso y proyecto de docker/secrets-engine.

Comandos (uno por métrica):
  metricas complejidad   (cc)    1. Complejidad ciclomática        [producto]
  metricas cobertura     (cov)   2. Cobertura de código            [producto]
  metricas densidad      (dd)    3. Densidad de defectos           [producto]
  metricas mttd                  4. Tiempo medio de detección      [proceso]
  metricas mttr                  5. Tiempo medio de reparación     [proceso]
  metricas pruebas       (tests) 6. Eficacia de las pruebas        [proceso]
  metricas revision      (rev)   7. Eficacia de la revisión        [proyecto]
  metricas esfuerzo      (desv)  8. Desviación de esfuerzo         [proyecto]
  metricas arquitectura  (arq)   9. Arquitectura y patrones        [proyecto]

  metricas todo          (all)   Las 9 métricas + resumen, tablero y esquemas
  metricas resumen               Solo la tabla resumen con los últimos resultados guardados
  metricas lint                  golangci-lint por módulo (complementario)
  metricas doctor                Verifica que estén instaladas las herramientas

Ejemplos:
  metricas cobertura --reusar        # no vuelve a correr las pruebas
  metricas todo --rapido             # todo, reutilizando perfiles de cobertura y minería
  metricas mttd --refrescar          # rehace la minería de defectos
"""

ALIAS = {"cc": "complejidad", "cov": "cobertura", "dd": "densidad", "tests": "pruebas", "rev": "revision",
         "revisión": "revision", "desv": "esfuerzo", "arq": "arquitectura", "all": "todo"}


def doctor(args=None):
    print(comun.c("\n  Verificación del entorno\n", "neg"))
    req = [
        ("git", "obligatorio", "sudo apt install git"),
        ("go", "cobertura", "https://go.dev/dl (usa la versión de go.work)"),
        ("gocyclo", "complejidad", "go install github.com/fzipp/gocyclo/cmd/gocyclo@latest  (y agrega ~/go/bin al PATH)"),
        ("cloc", "densidad / esfuerzo", "sudo apt install cloc"),
        ("dbus-daemon", "cobertura de store/keychain", "sudo apt install dbus-x11"),
        ("gnome-keyring-daemon", "cobertura de store/keychain", "sudo apt install gnome-keyring"),
        ("golangci-lint", "lint (opcional)", "https://golangci-lint.run/welcome/install/"),
    ]
    filas = []
    ok = True
    for prog, uso, inst in req:
        ruta = shutil.which(prog)
        ver = ""
        if ruta and prog == "go":
            pv = subprocess.run(["go", "version"], capture_output=True, text=True, cwd=comun.CFG["repo"])
            ver = pv.stdout.split()[2] if pv.returncode == 0 and len(pv.stdout.split()) > 2 else "instalado (no coincide con go.work)"
        estado = comun.c("✔ " + (ver or "instalado"), "verde") if ruta else comun.c("✘ falta", "rojo")
        if not ruta and uso in ("obligatorio",):
            ok = False
        filas.append([prog, uso, estado, "" if ruta else inst])
    try:
        import matplotlib  # noqa: F401
        filas.append(["matplotlib (python)", "gráficos", comun.c("✔ " + matplotlib.__version__, "verde"), ""])
    except ImportError:
        filas.append(["matplotlib (python)", "gráficos", comun.c("✘ falta", "rojo"), "sudo apt install python3-matplotlib"])
    comun.tabla(["Herramienta", "Se usa para", "Estado", "Cómo instalar"], filas, alinear="llll")
    print(f"\n  Repositorio: {comun.CFG['repo']}\n  Módulos (go.work): {', '.join(comun.modulos())}"
          f"\n  Resultados en: {comun.CFG['salida']}\n")
    return ok


def lint(args=None):
    comun.requiere("golangci-lint")
    filas = []
    for m in comun.modulos():
        comun.info(f"(cd {m} && golangci-lint run --timeout=5m ./...)")
        p = subprocess.run(["golangci-lint", "run", "--timeout=5m", "./..."], cwd=os.path.join(comun.CFG["repo"], m),
                           capture_output=True, text=True)
        salida = (p.stdout + p.stderr).strip()
        n = 0
        for l in salida.splitlines():
            if l.strip().endswith("issues.") or " issues:" in l:
                pass
            if ":" in l and l.split(":")[0].endswith(".go"):
                n += 1
                print("    " + l)
        filas.append([m, n, "✔ 0 incidencias" if n == 0 else f"{n} incidencias"])
    comun.tabla(["Módulo", "Incidencias", "Estado"], filas, alinear="lrl", titulo="golangci-lint por módulo")


def main(argv=None):
    p = argparse.ArgumentParser(prog="metricas", description=AYUDA, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("comando", nargs="?", default="ayuda")
    p.add_argument("--repo", help="raíz del repositorio (por defecto se busca go.work hacia arriba)")
    p.add_argument("--salida", help="carpeta de resultados (por defecto <repo>/metricas_resultados)")
    p.add_argument("--ref", default="HEAD", help="rama/commit a analizar en el historial (por defecto HEAD)")
    p.add_argument("--refrescar", action="store_true", help="recalcular la minería de defectos aunque haya caché")
    p.add_argument("--reusar", action="store_true", help="cobertura: reutilizar los perfiles .out ya generados")
    p.add_argument("--rapido", action="store_true", help="todo: equivale a --reusar (no vuelve a correr go test)")
    p.add_argument("--perfiles", help="cobertura: importar perfiles .out desde esta carpeta (client.out, plugin.out, ...)")
    p.add_argument("--sin-dbus", action="store_true", help="cobertura: no iniciar D-Bus/gnome-keyring automáticamente")
    p.add_argument("--sin-graficos", action="store_true", help="no generar PNG")
    p.add_argument("--sin-color", action="store_true", help="salida sin colores ANSI")
    a = p.parse_args(argv)

    cmd = ALIAS.get(a.comando, a.comando)
    if cmd in ("ayuda", "help", "-h"):
        p.print_help()
        return 0
    repo = os.path.abspath(a.repo) if a.repo else comun.encontrar_repo()
    if not repo:
        comun.error("No encontré go.work. Ejecuta el comando dentro del repositorio o usa --repo RUTA.")
        return 2
    comun.CFG.update({
        "repo": repo, "salida": os.path.abspath(a.salida) if a.salida else os.path.join(repo, "metricas_resultados"),
        "ref": a.ref, "refrescar": a.refrescar, "graficos": not a.sin_graficos,
        "color": not a.sin_color and sys.stdout.isatty() and not os.environ.get("NO_COLOR"),
    })
    if a.rapido:
        a.reusar = True
    os.makedirs(comun.CFG["salida"], exist_ok=True)

    comandos = {
        "complejidad": producto.complejidad, "cobertura": producto.cobertura, "densidad": producto.densidad,
        "mttd": proceso.mttd, "mttr": proceso.mttr, "pruebas": proceso.pruebas,
        "revision": proyecto.revision, "esfuerzo": proyecto.esfuerzo, "arquitectura": proyecto.arquitectura,
        "todo": resumen.resumen, "resumen": lambda x: resumen.resumen(x, ejecutar=False),
        "doctor": doctor, "lint": lint,
    }
    if cmd not in comandos:
        comun.error(f"Comando desconocido: {a.comando}")
        p.print_help()
        return 2
    r = comandos[cmd](a)
    return 0 if r is not False else 1


if __name__ == "__main__":
    sys.exit(main())
