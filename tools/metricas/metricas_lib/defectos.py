"""Minería de defectos sobre el historial de git (variante del algoritmo SZZ,
Śliwerski, Zimmermann & Zeller, 2005) y clasificación de la fase de detección.

Es la base común de densidad, MTTD, MTTR, eficacia de pruebas, eficacia de la
revisión y desviación de esfuerzo. El resultado se guarda en caché en
<salida>/defectos/defectos.json y se reutiliza mientras el commit analizado no
cambie (usa --refrescar para forzar el recálculo).

Definiciones (idénticas a las del reporte):
  - Defecto = commit no-merge cuyo asunto empieza con `fix:` / `fix(...)`.
  - Commit inductor = el commit más reciente (anterior al fix) que tocó por
    última vez alguna de las líneas modificadas por el fix (git blame sobre
    el padre del fix, por cada hunk de `git diff -U0`).
  - MTTD = fecha(fix) − fecha(inductor).
  - MTTR = fecha(merge del PR que integró el fix a main) − fecha(fix).
    Los fixes subidos directo a main no tienen MTTR calculable.
  - Fase de detección: revisión (inductor y fix en el mismo PR) /
    pruebas-CI (no se publicó ningún tag entre inductor y fix) /
    producción (sí se publicó un tag entre ambos) / desconocida.
"""
import json
import os
import re
import statistics
from datetime import datetime

from . import comun
from .comun import git, info

FIX_RE = re.compile(r"^fix(\(.+\))?!?:", re.IGNORECASE)
IGNORAR = {"go.sum", "go.work.sum"}
RELEASE_RE = re.compile(r"v\d+\.\d+\.\d+")


def _fecha(s):
    return datetime.fromisoformat(s.strip())


def _commits():
    out = git("log", "--no-merges", "--pretty=format:%H|%ad|%an|%s", "--date=iso-strict", comun.CFG["ref"])
    res = []
    for l in out.splitlines():
        h, d, a, s = l.split("|", 3)
        res.append({"hash": h, "fecha": _fecha(d), "autor": a, "asunto": s})
    return res


def _merges():
    """Lista de merges (más reciente primero) con los commits propios de su rama."""
    out = git("log", "--merges", "--pretty=format:%H|%P|%ad", "--date=iso-strict", comun.CFG["ref"])
    res = []
    for l in out.splitlines():
        partes = l.split("|")
        if len(partes) != 3:
            continue
        mh, padres, fecha = partes
        ps = padres.split()
        if len(ps) != 2:
            continue
        miembros = git("log", "--pretty=format:%H", f"{ps[0]}..{ps[1]}").splitlines()
        res.append({"hash": mh, "fecha": _fecha(fecha), "miembros": set(miembros), "n": len(miembros)})
    return res


def _hunks(h, ruta):
    out = git("diff", "-U0", f"{h}^!", "--", ruta)
    res = []
    for m in re.finditer(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", out, re.M):
        ini, n = int(m.group(1)), int(m.group(2) or "1")
        if n > 0:
            res.append((ini, n))
    return res


def _blame(padre, ruta, ini, n):
    out = git("blame", "-l", "-L", f"{ini},{ini + n - 1}", padre, "--", ruta)
    hs = set()
    for l in out.splitlines():
        h = l.split(" ", 1)[0].lstrip("^")
        if h and set(h) != {"0"}:
            hs.add(h)
    return hs


def _tags():
    out = git("for-each-ref", "--format=%(refname:short)|%(creatordate:iso-strict)", "refs/tags")
    release, por_modulo = [], {m: [] for m in comun.modulos()}
    for l in out.splitlines():
        if "|" not in l:
            continue
        nombre, fecha = l.split("|", 1)
        if not fecha:
            continue
        f = _fecha(fecha)
        if RELEASE_RE.fullmatch(nombre):
            release.append({"tag": nombre, "fecha": f})
        for m in por_modulo:
            if nombre.startswith(m + "/"):
                por_modulo[m].append({"tag": nombre, "fecha": f})
    release.sort(key=lambda t: t["fecha"])
    for m in por_modulo:
        por_modulo[m].sort(key=lambda t: t["fecha"])
    return release, por_modulo


def minar():
    """Ejecuta la minería completa (o usa la caché) y devuelve el dict de defectos."""
    destino = os.path.join(comun.carpeta("defectos"), "defectos.json")
    cabeza = comun.head_hash()
    if os.path.isfile(destino) and not comun.CFG["refrescar"]:
        with open(destino, encoding="utf-8") as f:
            cache = json.load(f)
        if cache.get("commit") == cabeza:
            info(f"Usando la minería de defectos en caché ({comun.rel(destino)}); usa --refrescar para recalcular.")
            return cache

    comun.requiere("git")
    mods = comun.modulos()
    commits = _commits()
    fixes = [c for c in commits if FIX_RE.match(c["asunto"])]
    info(f"{len(commits)} commits no-merge; {len(fixes)} commits fix: (defectos). Minando historial (SZZ)...")
    merges = _merges()
    release, tags_mod = _tags()
    info(f"{len(merges)} merges de PR, {len(release)} tags de release de producto.")

    registros = []
    for i, fc in enumerate(fixes, 1):
        h = fc["hash"]
        archivos = [a for a in git("show", "--pretty=format:", "--name-only", h).splitlines()
                    if a.strip() and a not in IGNORAR and not a.startswith("vendor/")]
        modulos_fix = sorted({comun.modulo_de(a, mods) for a in archivos} - {None})

        candidatos = set()
        for a in archivos:
            for ini, n in _hunks(h, a):
                candidatos |= _blame(f"{h}^", a, ini, n)
        candidatos.discard(h)
        inductor = None
        fechados = []
        for ch in candidatos:
            d = git("show", "-s", "--pretty=format:%ad", "--date=iso-strict", ch)
            if d:
                fd = _fecha(d)
                if fd <= fc["fecha"]:
                    fechados.append((fd, ch))
        if fechados:
            fechados.sort()
            fd, ch = fechados[-1]
            inductor = {"hash": ch, "fecha": fd, "asunto": git("show", "-s", "--pretty=format:%s", ch)}

        merge = next((m for m in merges if h in m["miembros"]), None)
        mttd = (fc["fecha"] - inductor["fecha"]).total_seconds() / 86400 if inductor else None
        mttr = None
        if merge:
            mttr = (merge["fecha"] - fc["fecha"]).total_seconds() / 86400
            if mttr < 0:
                mttr = None

        # Fase de detección
        revision = None
        if merge and inductor:
            revision = inductor["hash"] in merge["miembros"]
        elif merge is None and inductor:
            revision = (fc["fecha"] - inductor["fecha"]).total_seconds() < 6 * 3600
        publicado, tag_pub = None, None
        if inductor:
            publicado = False
            for mod in (modulos_fix or ["x"]):
                cand = [t for t in release if inductor["fecha"] <= t["fecha"] <= fc["fecha"]] or \
                       [t for t in tags_mod.get(mod, []) if inductor["fecha"] <= t["fecha"] <= fc["fecha"]]
                if cand:
                    publicado, tag_pub = True, cand[0]["tag"]
                    break
        if revision is True:
            fase = "revision"
        elif publicado is False:
            fase = "pruebas_ci"
        elif publicado is True:
            fase = "produccion"
        else:
            fase = "desconocida"

        registros.append({
            "fix": h[:10], "fecha_fix": fc["fecha"].isoformat(), "asunto": fc["asunto"],
            "modulos": modulos_fix, "archivos": archivos,
            "inductor": inductor["hash"][:10] if inductor else None,
            "fecha_inductor": inductor["fecha"].isoformat() if inductor else None,
            "mttd_dias": mttd,
            "merge": merge["hash"][:10] if merge else None,
            "fecha_merge": merge["fecha"].isoformat() if merge else None,
            "commits_en_pr": merge["n"] if merge else None,
            "mttr_dias": mttr, "directo_a_main": merge is None,
            "atrapado_en_revision": revision, "publicado_antes_del_fix": publicado, "tag_publicado": tag_pub,
            "fase": fase,
        })
        if i % 10 == 0 or i == len(fixes):
            info(f"  [{i}/{len(fixes)}] fixes analizados")

    datos = {
        "commit": cabeza, "total_commits_no_merge": len(commits), "n_fixes": len(registros),
        "n_merges": len(merges), "n_tags_release": len(release),
        "primer_release": release[0]["fecha"].isoformat() if release else None,
        "ultimo_release": release[-1]["fecha"].isoformat() if release else None,
        "tags_por_modulo": {m: len(v) for m, v in tags_mod.items()},
        "defectos": registros,
    }
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False, default=str)
    info(f"Minería guardada en {comun.rel(destino)}")
    return datos


def mediana(v):
    return statistics.median(v) if v else None


def media(v):
    return statistics.mean(v) if v else None
