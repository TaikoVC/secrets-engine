"""Gráficos de la CLI `metricas` (matplotlib, PNG para el reporte).

Estilo: una sola tinta de serie (azul), colores de estado reservados para
valoraciones (bueno/advertencia/serio/crítico) siempre acompañados de etiqueta
de texto, cuadrícula tenue y etiquetas directas en las barras."""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA2 = "#52514e"
TENUE = "#898781"
REJILLA = "#e1e0d9"
EJE = "#c3c2b7"
SERIE = "#2a78d6"
SERIE_CLARA = "#86b6ef"
SERIE2 = "#eb6834"
ESTADO = {"bueno": "#0ca30c", "aceptable": "#fab219", "mejorable": "#ec835a", "bajo": "#d03b3b", "info": SERIE}
ETIQUETA_ESTADO = {"bueno": "Bueno", "aceptable": "Aceptable", "mejorable": "Mejorable", "bajo": "Bajo", "info": "Info"}

plt.rcParams.update({
    "figure.facecolor": SUPERFICIE, "axes.facecolor": SUPERFICIE, "savefig.facecolor": SUPERFICIE,
    "font.family": "DejaVu Sans", "font.size": 10, "text.color": TINTA,
    "axes.edgecolor": EJE, "axes.labelcolor": TINTA2, "axes.titlesize": 12, "axes.titleweight": "bold",
    "axes.titlecolor": TINTA, "axes.titlelocation": "left", "axes.titlepad": 10,
    "xtick.color": TENUE, "ytick.color": TINTA2, "xtick.labelsize": 9, "ytick.labelsize": 9,
    "axes.grid": False, "grid.color": REJILLA, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
    "legend.fontsize": 9,
})


def _fin(fig, ruta, nota=None):
    if nota:
        fig.text(0.01, 0.01, nota, fontsize=8, color=TENUE, ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.04 if nota else 0, 1, 1))
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    fig.savefig(ruta, dpi=160)
    plt.close(fig)
    return ruta


def _barras_h(ax, etiquetas, valores, colores=None, fmt="{:.1f}", max_x=None, sufijo=""):
    y = list(range(len(etiquetas)))[::-1]
    colores = colores or [SERIE] * len(valores)
    ax.barh(y, valores, color=colores, height=0.62, edgecolor=SUPERFICIE, linewidth=2)
    ax.set_yticks(y)
    ax.set_yticklabels(etiquetas)
    tope = max_x or (max(valores) * 1.18 if valores and max(valores) > 0 else 1)
    ax.set_xlim(0, tope)
    for yi, v in zip(y, valores):
        ax.text(v + tope * 0.01, yi, fmt.format(v) + sufijo, va="center", fontsize=9, color=TINTA)
    ax.xaxis.grid(True)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)


def _linea_ref(ax, x, texto, vertical=True, color=TINTA2, ha="left"):
    if vertical:
        ax.axvline(x, color=color, linestyle=(0, (4, 3)), linewidth=1.2)
        ax.text(x, ax.get_ylim()[1], " " + texto if ha == "left" else texto, color=color, fontsize=8, va="bottom", ha=ha)
    else:
        ax.axhline(x, color=color, linestyle=(0, (4, 3)), linewidth=1.2)
        ax.text(ax.get_xlim()[1], x, texto + " ", color=color, fontsize=8, va="bottom", ha="right")


def leyenda_estados(ax, estados, titulo=None):
    from matplotlib.patches import Patch
    h = [Patch(color=ESTADO[e], label=t) for e, t in estados]
    ax.legend(handles=h, loc="lower right", title=titulo, title_fontsize=8)


# --------------------------------------------------------------------------
# Gráficos por métrica
# --------------------------------------------------------------------------
def complejidad(ruta, bandas, top, umbral_proyecto):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.5, 4.0), gridspec_kw={"width_ratios": [1, 1.6]})
    etiquetas = [b["banda"] for b in bandas]
    vals = [b["funciones"] for b in bandas]
    cols = [ESTADO["bueno"], ESTADO["aceptable"], ESTADO["mejorable"], ESTADO["bajo"]][: len(vals)]
    x = range(len(vals))
    a1.bar(x, vals, color=cols, width=0.6, edgecolor=SUPERFICIE, linewidth=2)
    tot = sum(vals) or 1
    for xi, v in zip(x, vals):
        a1.text(xi, v + tot * 0.01, f"{v}\n({100 * v / tot:.1f}%)", ha="center", va="bottom", fontsize=9)
    a1.set_xticks(list(x))
    a1.set_xticklabels([e.replace(" (", "\n").rstrip(")") for e in etiquetas], fontsize=8)
    a1.set_ylim(0, max(vals) * 1.25)
    a1.yaxis.grid(True)
    a1.set_axisbelow(True)
    a1.set_ylabel("Funciones de producción")
    a1.set_title("Distribución por banda de riesgo (McCabe)")

    nombres = [f"{t['funcion']}  ({t['modulo']})" for t in top]
    ccs = [t["cc"] for t in top]
    colores = [ESTADO["aceptable"] if v > 10 else ESTADO["bueno"] for v in ccs]
    _barras_h(a2, nombres, ccs, colores, fmt="{:.0f}", max_x=max(umbral_proyecto + 2, max(ccs) + 2))
    _linea_ref(a2, 10, "McCabe 10 ", ha="right")
    _linea_ref(a2, umbral_proyecto, f" límite CI {umbral_proyecto}", color=ESTADO["bajo"])
    a2.set_title(f"Top {len(top)} funciones más complejas")
    a2.set_xlabel("Complejidad ciclomática (CC)")
    return _fin(fig, ruta, "Fuente: gocyclo sobre el código propio (sin vendor/ ni go-keychain de terceros).")


def cobertura(ruta, filas, global_bruto, global_ajustado):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.5, 3.7), gridspec_kw={"width_ratios": [1.7, 1]})
    et = [f["modulo"] for f in filas]
    vals = [f["pct_ajustado"] for f in filas]

    def estado(v):
        return "bueno" if v >= 75 else ("aceptable" if v >= 60 else "mejorable")

    _barras_h(a1, et, vals, [ESTADO[estado(v)] for v in vals], max_x=105, sufijo="%")
    for xref in (60, 75, 90):
        _linea_ref(a1, xref, str(xref), ha="center")
    a1.set_title("Cobertura por módulo (sin código generado)")
    a1.set_xlabel("% de sentencias cubiertas (ref.: 60 aceptable · 75 encomiable · 90 ejemplar)", fontsize=8.5)
    leyenda_estados(a1, [("bueno", "≥ 75%"), ("aceptable", "60–75%"), ("mejorable", "< 60%")])

    a2.bar([0, 1], [global_bruto, global_ajustado], color=[SERIE_CLARA, SERIE], width=0.55,
           edgecolor=SUPERFICIE, linewidth=2)
    for xi, v in zip([0, 1], [global_bruto, global_ajustado]):
        a2.text(xi, v + 1.5, f"{v:.1f}%", ha="center", fontsize=11, fontweight="bold")
    a2.set_xticks([0, 1])
    a2.set_xticklabels(["Bruta\n(incluye protobuf/\nconnect generado)", "Ajustada\n(sin código\ngenerado)"], fontsize=8.5)
    a2.set_ylim(0, 100)
    a2.yaxis.grid(True)
    a2.set_axisbelow(True)
    a2.set_title("Cobertura global")
    return _fin(fig, ruta, "Fuente: go test -coverprofile en los módulos del go.work. Referencias: Google Testing Blog (2020).")


def densidad(ruta, filas, global_dens):
    fig, ax = plt.subplots(figsize=(9, 3.5))
    et = [f"{f['modulo']}  ({f['defectos']} def. / {f['kloc']:.2f} KLOC)" for f in filas]
    vals = [f["densidad"] for f in filas]

    def estado(v):
        return "bajo" if v > 25 else ("mejorable" if v > 10 else "bueno")

    _barras_h(ax, et, vals, [ESTADO[estado(v)] for v in vals], fmt="{:.2f}")
    _linea_ref(ax, global_dens, f"global {global_dens:.2f}")
    ax.set_title("Densidad de defectos por módulo (defectos corregidos / KLOC)")
    ax.set_xlabel("Defectos por cada 1 000 líneas de código")
    leyenda_estados(ax, [("bueno", "≤ 10"), ("mejorable", "10–25"), ("bajo", "> 25")])
    return _fin(fig, ruta, "Fuente: commits fix: (minería tipo SZZ) y cloc --fullpath por módulo.")


def distribucion_tiempos(ruta, valores_dias, media, mediana, titulo, unidad="días", por_modulo=None,
                         bandas=None, nota=None):
    import math
    fig, axs = plt.subplots(1, 2 if por_modulo else 1, figsize=(9.5 if por_modulo else 7, 3.6),
                            gridspec_kw={"width_ratios": [1.5, 1]} if por_modulo else None)
    a1 = axs[0] if por_modulo else axs
    factor = 24.0 if unidad == "horas" else 1.0
    vals = [v * factor for v in valores_dias if v is not None and v > 0]
    lo = max(min(vals), 1e-3)
    hi = max(vals)
    nb = 24
    edges = [10 ** (math.log10(lo) + i * (math.log10(hi) - math.log10(lo)) / nb) for i in range(nb + 1)]
    a1.hist(vals, bins=edges, color=SERIE, edgecolor=SUPERFICIE, linewidth=1.5)
    a1.set_xscale("log")
    if bandas:
        for (x0, x1, texto, col) in bandas:
            x0, x1 = max(x0, lo / 1.5), min(x1, hi * 1.5)
            if x1 <= x0:
                continue
            a1.axvspan(x0, x1, color=col, alpha=0.08, lw=0)
            a1.text((x0 * x1) ** 0.5 if x0 > 0 else x1 / 3, a1.get_ylim()[1] * 0.96, texto, ha="center",
                    va="top", fontsize=7.5, color=TINTA2)
    a1.axvline(mediana * factor, color=TINTA, linewidth=1.6)
    a1.axvline(media * factor, color=SERIE2, linewidth=1.6, linestyle=(0, (4, 3)))
    caja = dict(boxstyle="round,pad=0.25", fc=SUPERFICIE, ec="none", alpha=0.92)
    a1.text(mediana * factor, a1.get_ylim()[1] * 0.80, f"mediana {mediana * factor:.2f} {unidad}", fontsize=8.5,
            ha="right", bbox=caja)
    a1.text(media * factor, a1.get_ylim()[1] * 0.66, f"media {media * factor:.2f} {unidad}", fontsize=8.5,
            color=SERIE2, ha="left", bbox=caja)
    a1.set_xlabel(f"{unidad.capitalize()} (escala logarítmica)")
    a1.set_ylabel("Número de defectos")
    a1.yaxis.grid(True)
    a1.set_axisbelow(True)
    a1.set_title(titulo)
    if por_modulo:
        et = list(por_modulo.keys())
        vs = [(por_modulo[k] or 0) * factor for k in et]
        _barras_h(axs[1], et, vs, fmt="{:.2f}", sufijo=" " + unidad[0])
        axs[1].set_title("Mediana por módulo")
        axs[1].set_xlabel(unidad.capitalize())
    return _fin(fig, ruta, nota)


def fases(ruta, conteos, eficacia):
    orden = [("revision", "Revisión\n(mismo PR)", "bueno"), ("pruebas_ci", "Pruebas / CI\n(antes de publicar)", "aceptable"),
             ("produccion", "Producción\n(ya publicado)", "bajo"), ("desconocida", "Sin clasificar", "info")]
    fig, ax = plt.subplots(figsize=(8.5, 3.5))
    vals = [conteos.get(k, 0) for k, _, _ in orden]
    tot = sum(vals) or 1
    cols = [ESTADO[e] if e != "info" else EJE for _, _, e in orden]
    ax.bar(range(4), vals, color=cols, width=0.6, edgecolor=SUPERFICIE, linewidth=2)
    for i, v in enumerate(vals):
        ax.text(i, v + tot * 0.01, f"{v}  ({100 * v / tot:.1f}%)", ha="center", va="bottom", fontsize=9.5)
    ax.set_xticks(range(4))
    ax.set_xticklabels([t for _, t, _ in orden])
    ax.set_ylim(0, max(vals) * 1.25)
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    ax.set_ylabel("Defectos")
    ax.set_title(f"Fase en que se detectó cada defecto — eficacia antes de producción: {eficacia:.1f}%")
    return _fin(fig, ruta, "Eficacia de pruebas = (revisión + pruebas/CI) / defectos con fase conocida.")


def revision(ruta, global_pct, atrapados, total, por_modulo):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.5, 3.3), gridspec_kw={"width_ratios": [1, 1.3]})
    a1.barh([0], [atrapados], color=ESTADO["bueno"], height=0.5, edgecolor=SUPERFICIE, linewidth=2)
    a1.barh([0], [total - atrapados], left=[atrapados], color=EJE, height=0.5, edgecolor=SUPERFICIE, linewidth=2)
    a1.text(atrapados / 2, 0, f"En revisión\n{atrapados}", ha="center", va="center", color="white", fontsize=9,
            fontweight="bold")
    a1.text(atrapados + (total - atrapados) / 2, 0, f"Después de fusionar\n{total - atrapados}", ha="center",
            va="center", color=TINTA, fontsize=9)
    a1.set_xlim(0, total)
    a1.set_ylim(-1.2, 1.2)
    a1.set_yticks([])
    a1.set_xlabel("Defectos con fase conocida")
    a1.set_title(f"Eficacia de la revisión: {global_pct:.1f}%")
    a1.spines["left"].set_visible(False)
    et = list(por_modulo.keys())
    vs = [por_modulo[k] for k in et]
    _barras_h(a2, et, vs, max_x=100, sufijo="%")
    _linea_ref(a2, global_pct, f"global {global_pct:.1f}%")
    a2.set_title("Eficacia de la revisión por módulo")
    a2.set_xlabel("% de defectos atrapados en el mismo PR")
    return _fin(fig, ruta, "Un defecto cuenta como 'atrapado en revisión' si el commit que lo introdujo y su corrección están en el mismo PR.")


def esfuerzo(ruta, filas):
    import numpy as np
    fig, ax = plt.subplots(figsize=(9, 3.6))
    et = [f["modulo"] for f in filas]
    esp = [f["esperado_pct"] for f in filas]
    real = [f["real_pct"] for f in filas]
    x = np.arange(len(et))
    w = 0.38
    ax.bar(x - w / 2, esp, w, color=SERIE_CLARA, label="Esperado (proporción de KLOC)", edgecolor=SUPERFICIE, linewidth=2)
    ax.bar(x + w / 2, real, w, color=SERIE, label="Real (proporción de commits)", edgecolor=SUPERFICIE, linewidth=2)
    for i, f in enumerate(filas):
        top = max(esp[i], real[i])
        col = ESTADO["bueno"] if abs(f["desviacion_pct"]) <= 25 else (ESTADO["mejorable"] if abs(f["desviacion_pct"]) <= 100 else ESTADO["bajo"])
        ax.text(i, top + 1.2, f"{f['desviacion_pct']:+.0f}%", ha="center", fontsize=9.5, fontweight="bold", color=col)
    ax.set_xticks(x)
    ax.set_xticklabels(et)
    ax.set_ylim(0, max(esp + real) * 1.22)
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    ax.set_ylabel("% del total")
    ax.legend(loc="upper left")
    ax.set_title("Esfuerzo esperado vs. real por módulo (etiqueta = desviación)")
    return _fin(fig, ruta, "Desviación = (real − esperado) / esperado × 100.")


# --------------------------------------------------------------------------
# Esquemas: arquitectura con métricas de producto y ciclo de vida con proceso
# --------------------------------------------------------------------------
def _caja(ax, x, y, w, h, titulo, lineas, borde=SERIE, fondo="#ffffff", tam=9):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                                linewidth=1.6, edgecolor=borde, facecolor=fondo, zorder=3))
    ax.text(x, y + h / 2 - 0.13, titulo, ha="center", va="top", fontsize=tam + 0.5, fontweight="bold", zorder=4)
    for i, (txt, col) in enumerate(lineas):
        ax.text(x, y + h / 2 - 0.42 - i * 0.22, txt, ha="center", va="top", fontsize=tam - 0.5, color=col, zorder=4)


def _flecha(ax, x0, y0, x1, y1, texto=None, color=TENUE):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), zorder=2,
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.3, shrinkA=4, shrinkB=4))
    if texto:
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, texto, fontsize=7.5, color=TINTA2, ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.15", fc=SUPERFICIE, ec="none"), zorder=4)


def arquitectura(ruta, nodos, aristas, metricas_por_modulo):
    """nodos: {modulo: (x, y, descripcion)}; aristas: [(origen, destino, n_imports)];
    metricas_por_modulo: {modulo: {"cc":..,"cov":..,"dens":..,"desv":..}}"""
    fig, ax = plt.subplots(figsize=(9.6, 5.53))
    ax.set_xlim(0, 12.5)
    ax.set_ylim(0, 7.2)
    ax.axis("off")
    W, H = 2.95, 1.62
    for o, d, n in aristas:
        x0, y0, _ = nodos[o]
        x1, y1, _ = nodos[d]
        ya, yb = y0 - H / 2, y1 + H / 2
        # curvatura para no atravesar cajas intermedias en saltos de dos capas
        rad = 0.0 if abs(y0 - y1) < 3 else (-0.25 if x1 < x0 else 0.25)
        ax.annotate("", xy=(x1, yb), xytext=(x0, ya), zorder=2,
                    arrowprops=dict(arrowstyle="-|>", color=TENUE, lw=1.0 + min(n, 30) / 10,
                                    shrinkA=2, shrinkB=2, connectionstyle=f"arc3,rad={rad}"))
        if rad:
            dx, dy = x1 - x0, yb - ya
            lx, ly = (x0 + x1) / 2 + 0.5 * rad * dy, (ya + yb) / 2 - 0.5 * rad * dx
        else:
            lx, ly = x0 + (x1 - x0) * 0.30, ya + (yb - ya) * 0.30
        ax.text(lx, ly, f"{n}", fontsize=8, color=TINTA2, ha="center", va="center", zorder=4,
                bbox=dict(boxstyle="circle,pad=0.25", fc=SUPERFICIE, ec=EJE, lw=0.8))

    def col_cc(v):
        return ESTADO["bueno"] if v is not None and v <= 5 else ESTADO["mejorable"]

    def col_cov(v):
        return TENUE if v is None else (ESTADO["bueno"] if v >= 75 else ("#b07d00" if v >= 60 else ESTADO["mejorable"]))

    def col_d(v):
        return TENUE if v is None else (ESTADO["bueno"] if v <= 10 else (ESTADO["mejorable"] if v <= 25 else ESTADO["bajo"]))

    for m, (x, y, desc) in nodos.items():
        mm = metricas_por_modulo.get(m, {})
        lineas = [(desc, TINTA2)]
        lineas.append((f"CC media {mm['cc']:.2f} · máx {mm['cc_max']}" if mm.get("cc") is not None else "CC n/d", col_cc(mm.get("cc"))))
        lineas.append((f"Cobertura {mm['cov']:.1f}%" if mm.get("cov") is not None else "Cobertura n/d", col_cov(mm.get("cov"))))
        lineas.append((f"Densidad {mm['dens']:.2f} def/KLOC" if mm.get("dens") is not None else "Densidad n/d", col_d(mm.get("dens"))))
        if mm.get("desv") is not None:
            lineas.append((f"Desv. esfuerzo {mm['desv']:+.0f}%", TINTA2))
        _caja(ax, x, y, W, H, m, lineas, tam=8.5)
    ax.text(0.1, 7.05, "Estructura real de módulos (dependencias por imports) y métricas de producto",
            fontsize=12, fontweight="bold", va="top")
    ax.text(0.1, 0.12, "Flecha A → B: el módulo A importa paquetes de B (el número es la cantidad de imports). Colores: verde = bueno, ámbar = aceptable, "
            "naranja/rojo = mejorable/alto.", fontsize=8, color=TENUE)
    return _fin(fig, ruta)


def ciclo_vida(ruta, valores):
    """Pipeline de desarrollo del proyecto con las métricas de proceso/proyecto
    ubicadas en la etapa donde se miden."""
    fig, ax = plt.subplots(figsize=(10, 3.68))
    ax.set_xlim(0, 12.5)
    ax.set_ylim(1.0, 5.6)
    ax.axis("off")
    etapas = [
        (1.2, "Commit", "rama de trabajo", "introduce el defecto"),
        (3.4, "Pull Request", "revisión de código", "pr-review.yml"),
        (5.6, "CI / pruebas", "unittests, lint,", "keychain, fuzz"),
        (7.8, "Fusión a main", "commit fix: + merge", ""),
        (10.2, "Release", "tags v0.x.y", "y tags por módulo"),
    ]
    y = 3.6
    for i, (x, t, l1, l2) in enumerate(etapas):
        _caja(ax, x, y, 1.95, 1.15, t, [(l1, TINTA2), (l2, TINTA2)], tam=8.5)
        if i < len(etapas) - 1:
            _flecha(ax, x + 0.98, y, etapas[i + 1][0] - 0.98, y, color=TINTA2)

    def chip(x, yy, titulo, valor, estado, ancho=2.1):
        ax.add_patch(FancyBboxPatch((x - ancho / 2, yy - 0.38), ancho, 0.76, boxstyle="round,pad=0.02,rounding_size=0.08",
                                    lw=1.4, ec=ESTADO[estado], fc="#ffffff", zorder=3))
        ax.text(x, yy + 0.14, titulo, ha="center", fontsize=8, color=TINTA2, zorder=4)
        ax.text(x, yy - 0.18, valor, ha="center", fontsize=9.5, fontweight="bold", color=TINTA, zorder=4)

    v = valores
    chip(3.4, 2.15, "Eficacia de la revisión", v["revision"], v["revision_estado"], ancho=1.95)
    chip(5.6, 2.15, "Eficacia de pruebas", v["pruebas"], v["pruebas_estado"], ancho=1.95)
    chip(7.8, 2.15, "MTTR (fix → merge)", v["mttr"], v["mttr_estado"], ancho=1.95)
    # MTTD abarca desde que se introduce el defecto hasta su corrección
    ax.annotate("", xy=(7.8, 4.45), xytext=(1.2, 4.45),
                arrowprops=dict(arrowstyle="<->", color=SERIE, lw=1.6))
    ax.text(4.5, 4.62, f"MTTD (introducción → corrección): {v['mttd']}", ha="center", fontsize=9.5,
            fontweight="bold", color=SERIE)
    for xx in (3.4, 5.6, 7.8):
        ax.annotate("", xy=(xx, 2.55), xytext=(xx, 3.0), arrowprops=dict(arrowstyle="-", color=EJE, lw=1, ls=":"))
    ax.text(10.2, 2.15, f"Defectos que llegaron\na producción: {v['produccion']}", ha="center", fontsize=8.5,
            color=ESTADO["bajo"])
    ax.text(1.2, 2.15, f"{v['fixes']} commits fix:\nminados (SZZ)", ha="center", fontsize=8.5, color=TINTA2)
    ax.text(0.1, 5.5, "Ciclo de vida del cambio y dónde se mide cada métrica de proceso y proyecto",
            fontsize=12, fontweight="bold", va="top")
    ax.text(0.1, 1.15, f"Desviación de esfuerzo (proyecto) se mide sobre todo el ciclo, por módulo: {v['esfuerzo']}.",
            fontsize=8.5, color=TINTA2)
    return _fin(fig, ruta)


def tablero(ruta, tarjetas):
    """Resumen de las 9 métricas como tarjetas (3x3)."""
    fig, ax = plt.subplots(figsize=(10, 6.1))
    ax.set_xlim(0, 3)
    ax.set_ylim(0, 3.25)
    ax.axis("off")
    for i, t in enumerate(tarjetas):
        fila, col = divmod(i, 3)
        x, y = col + 0.04, 2.0 - fila * 1.0 + 0.04
        ax.add_patch(FancyBboxPatch((x, y), 0.92, 0.86, boxstyle="round,pad=0.0,rounding_size=0.04",
                                    lw=1.2, ec=REJILLA, fc="#ffffff"))
        ax.add_patch(FancyBboxPatch((x, y + 0.8), 0.92, 0.06, boxstyle="square,pad=0", lw=0, fc=ESTADO[t["valoracion"]]))
        ax.text(x + 0.04, y + 0.72, f"{t['numero']}. {t['nombre']}", fontsize=9.5, fontweight="bold", va="top")
        ax.text(x + 0.04, y + 0.59, t["tipo"], fontsize=8, color=TENUE, va="top")
        ax.text(x + 0.04, y + 0.36, t["valor_corto"], fontsize=17, fontweight="bold", va="center")
        ax.text(x + 0.04, y + 0.17, t["detalle_corto"], fontsize=7.8, color=TINTA2, va="center")
        ax.text(x + 0.88, y + 0.06, ETIQUETA_ESTADO[t["valoracion"]] if t["valoracion"] != "info" else "Descriptiva",
                fontsize=8, color=TINTA, ha="right", va="bottom",
                bbox=dict(boxstyle="round,pad=0.25", fc=ESTADO[t["valoracion"]], ec="none", alpha=0.25))
    ax.text(0.04, 3.2, "Resumen de métricas — docker/secrets-engine", fontsize=14, fontweight="bold", va="top")
    return _fin(fig, ruta)
