"""Dibuja el diagrama C4 de contexto (nivel 1).  Uso: python docs/generar_c4.py"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

AZUL, GRIS, VERDE = "#1168bd", "#8c8c8c", "#2e7d6b"


def caja(ax, x, y, w, h, titulo, tipo, texto, color):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02",
                                fc=color, ec="black", lw=0.8))
    ax.text(x + w / 2, y + h - 0.07, titulo, ha="center", va="top", color="white",
            fontsize=10.5, weight="bold")
    ax.text(x + w / 2, y + h - 0.21, f"[{tipo}]", ha="center", va="top", color="white", fontsize=8)
    ax.text(x + w / 2, y + 0.07, texto, ha="center", va="bottom", color="white",
            fontsize=8, wrap=True)


def flecha(ax, a, b, texto, dy=0.0):
    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="->", lw=1.1))
    ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 0.06 + dy, texto, ha="center",
            fontsize=7.8, style="italic",
            bbox=dict(fc="white", ec="none", alpha=0.85, pad=1))


fig, ax = plt.subplots(figsize=(11, 6.2))
ax.set_xlim(0, 11)
ax.set_ylim(0, 6.2)
ax.axis("off")
ax.set_title("Diagrama C4 – Contexto: Sistema de estimación de reincidencia (académico)",
             fontsize=12, weight="bold")

caja(ax, 0.3, 4.3, 2.6, 1.3, "Estudiante / analista", "Persona",
     "Ejecuta el pipeline,\nrevisa métricas y equidad", "#08427b")
caja(ax, 0.3, 1.2, 2.6, 1.3, "Docente / revisor", "Persona",
     "Lee README, informe\ny resultados en develop", "#08427b")
caja(ax, 4.2, 2.6, 2.8, 1.6, "proyectoFinal_reincidenciaJusta", "Sistema de software (Python)",
     "Limpia datos, entrena y compara\nmodelos, mide equidad y\nentrega probabilidades", AZUL)
caja(ax, 8.2, 4.3, 2.5, 1.3, "ProPublica – COMPAS", "Fuente externa de datos",
     "CSV público en GitHub\n(Broward, Florida 2013-2014)", GRIS)
caja(ax, 8.2, 2.6, 2.5, 1.3, "Repositorio GitHub", "Sistema externo",
     "Ramas dev_xsanchez90\ny develop", GRIS)
caja(ax, 8.2, 0.7, 2.5, 1.3, "Juez / operador judicial", "Persona (fuera de alcance)",
     "NO recibe salidas:\nsolo uso académico", "#b03a2e")

flecha(ax, (2.9, 4.9), (4.2, 3.9), "ejecuta y consulta")
flecha(ax, (2.9, 1.9), (4.2, 2.9), "revisa resultados")
flecha(ax, (8.2, 4.9), (7.0, 3.9), "descarga CSV (HTTPS)")
flecha(ax, (7.0, 3.3), (8.2, 3.3), "versiona código y\nartefactos", dy=-0.02)
ax.annotate("", xy=(8.2, 1.35), xytext=(7.0, 2.7),
            arrowprops=dict(arrowstyle="->", lw=1.1, ls="--", color="#b03a2e"))
ax.text(7.35, 1.75, "sin integración\n(prohibido)", fontsize=7.8, color="#b03a2e", style="italic")

salida = Path(__file__).resolve().parent / "c4_contexto.png"
fig.tight_layout()
fig.savefig(salida, dpi=160)
print(salida)
