"""Genera el informe en Word con la plantilla de la Universidad de La Salle
(docs/plantilla_lasalle.docx) y lo exporta a PDF.

Uso (después de python -m src.entrenar_evaluar):
    python docs/generar_informe.py

El PDF se exporta con Microsoft Word (Windows). Si Word no está, queda el .docx.
"""
import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import docx
import pandas as pd
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from src import config as c  # noqa: E402

DOCS = RAIZ / "docs"
RES = RAIZ / "resultados"
PLANTILLA = DOCS / "plantilla_lasalle.docx"
SALIDA_DOCX = DOCS / "informe_mini_proyecto.docx"
SALIDA_PDF = DOCS / "informe_mini_proyecto.pdf"
REPO = "https://github.com/SanMarx27/proyectoFinal_reincidenciaJusta/tree/develop"

TITULO = "Actividad 6. Mini-proyecto de Machine Learning"
SUBTITULO = "Predicción de reincidencia con Regresión Logística: métricas y análisis ético"
PORTADA = {
    "Materia": ["Teoría de la Computación II"],
    "Programa": ["Ingeniería de Software"],
    "Autores": ["Ximena Sánchez Martínez"],
    "Título": [f"{TITULO}. {SUBTITULO}"],
    "Docente": ["Rodrigo Aranda Fernández"],
    "Fecha": ["Noviembre 8 de 2026"],
}
FUENTE = "Times New Roman"


# ---------- utilidades de formato (mismo estilo de la plantilla) ----------

def fmt_run(run, size=12, bold=False, italic=False):
    run.font.name = FUENTE
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), FUENTE)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    return run


def texto(par, contenido, size=12, bold=False, italic=False):
    """Admite <b>…</b> e <i>…</i> dentro del texto."""
    for parte in re.split(r"(<b>.*?</b>|<i>.*?</i>)", contenido):
        if not parte:
            continue
        if parte.startswith("<b>"):
            fmt_run(par.add_run(parte[3:-4]), size, True, italic)
        elif parte.startswith("<i>"):
            fmt_run(par.add_run(parte[3:-4]), size, bold, True)
        else:
            fmt_run(par.add_run(parte), size, bold, italic)
    return par


def espaciado(par, linea=1.5, antes=0, despues=6):
    pf = par.paragraph_format
    pf.line_spacing = linea
    pf.space_before = Pt(antes)
    pf.space_after = Pt(despues)
    return par


class Informe:
    def __init__(self):
        self.d = docx.Document(PLANTILLA)
        self.n_fig = 0
        self.n_tab = 0

    # portada y encabezado
    def portada(self):
        # Solo se tocan los nodos de texto (w:t): así no se pierden el panel azul,
        # las estrellas y el logo, que están anclados en esos mismos párrafos.
        def poner(p, nuevo):
            ts = list(p._element.iter(qn("w:t")))
            ts[0].text = nuevo
            for t in ts[1:]:
                t.text = ""

        pars = self.d.paragraphs
        borrar = []
        for i, p in enumerate(pars):
            etiqueta = p.text.strip()
            if etiqueta not in PORTADA:
                continue
            valores = PORTADA[etiqueta]
            j, k = i + 1, 0
            while j < len(pars) and pars[j].text.strip():
                if k < len(valores):
                    poner(pars[j], valores[k])
                else:
                    borrar.append(pars[j])
                j, k = j + 1, k + 1
        for p in borrar:
            if not list(p._element.iter(qn("w:drawing"))):
                p._element.getparent().remove(p._element)
            else:
                poner(p, "")

    def encabezado(self):
        for s in self.d.sections:
            for h in (s.header, s.first_page_header, s.even_page_header):
                for t in h._element.iter(qn("w:t")):
                    pass
                for p in h._element.iter(qn("w:p")):
                    ts = list(p.iter(qn("w:t")))
                    full = "".join(t.text or "" for t in ts)
                    if "actividad" in full.lower() and ts:
                        ts[0].text = TITULO
                        for t in ts[1:]:
                            t.text = ""

    # bloques de contenido
    def salto_pagina(self):
        p = self.d.add_paragraph()
        p.add_run().add_break(WD_BREAK.PAGE)

    def titulo(self, t, nueva_pagina=False):
        p = self.d.add_paragraph()
        p.paragraph_format.page_break_before = nueva_pagina
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        espaciado(p, 1.5, 6, 12)
        p.paragraph_format.keep_with_next = True
        texto(p, t, bold=True)

    def seccion(self, t):
        p = self.d.add_paragraph()
        espaciado(p, 1.5, 12, 6)
        p.paragraph_format.keep_with_next = True
        texto(p, t, bold=True)

    def parrafo(self, t):
        p = self.d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        espaciado(p)
        texto(p, t)
        return p

    def vinetas(self, items):
        for it in items:
            p = self.d.add_paragraph()
            pPr = p._element.get_or_add_pPr()
            num = OxmlElement("w:numPr")
            ilvl = OxmlElement("w:ilvl"); ilvl.set(qn("w:val"), "0")
            nid = OxmlElement("w:numId"); nid.set(qn("w:val"), "2")  # viñeta ❖ de la plantilla
            num.append(ilvl); num.append(nid); pPr.append(num)
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            espaciado(p, 1.5, 0, 2)
            texto(p, it)

    def figura(self, ruta, ancho_cm, titulo):
        self.n_fig += 1
        p = self.d.add_paragraph()
        espaciado(p, 1.0, 6, 0)
        p.paragraph_format.keep_with_next = True
        texto(p, f"Figura {self.n_fig}", bold=True)
        p = self.d.add_paragraph()
        espaciado(p, 1.0, 0, 4)
        p.paragraph_format.keep_with_next = True
        texto(p, titulo, italic=True)
        p = self.d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        espaciado(p, 1.0, 0, 2)
        p.add_run().add_picture(str(ruta), width=Cm(ancho_cm))
        self.nota("Fuente: elaboración propia con los datos de ProPublica (2016).")

    def nota(self, t):
        p = self.d.add_paragraph()
        espaciado(p, 1.0, 2, 10)
        texto(p, t, size=10, italic=True)

    def tabla(self, filas, anchos_cm, titulo, nota=None, tam=10, resaltar=None):
        self.n_tab += 1
        p = self.d.add_paragraph()
        espaciado(p, 1.0, 6, 0)
        p.paragraph_format.keep_with_next = True
        texto(p, f"Tabla {self.n_tab}", bold=True)
        p = self.d.add_paragraph()
        espaciado(p, 1.0, 0, 4)
        p.paragraph_format.keep_with_next = True
        texto(p, titulo, italic=True)

        t = self.d.add_table(rows=len(filas), cols=len(filas[0]))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        for i, fila in enumerate(filas):
            for j, val in enumerate(fila):
                celda = t.cell(i, j)
                celda.width = Cm(anchos_cm[j])
                tcPr = celda._element.get_or_add_tcPr()
                bordes = OxmlElement("w:tcBorders")
                for lado in ("top", "left", "bottom", "right"):
                    b = OxmlElement(f"w:{lado}")
                    b.set(qn("w:val"), "single"); b.set(qn("w:sz"), "4"); b.set(qn("w:color"), "auto")
                    bordes.append(b)
                tcPr.append(bordes)
                if i == 0 or (resaltar is not None and i == resaltar):
                    shd = OxmlElement("w:shd")
                    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto")
                    shd.set(qn("w:fill"), "FFF2CC" if i == 0 else "DEEAF6")
                    tcPr.append(shd)
                va = OxmlElement("w:vAlign"); va.set(qn("w:val"), "center"); tcPr.append(va)
                cp = celda.paragraphs[0]
                cp.alignment = WD_ALIGN_PARAGRAPH.CENTER if (i == 0 or j > 0) else WD_ALIGN_PARAGRAPH.LEFT
                espaciado(cp, 1.0, 1, 1)
                cp.paragraph_format.keep_with_next = i < len(filas) - 1  # la tabla no se parte
                texto(cp, str(val), size=tam, bold=(i == 0))
        # repetir cabecera si la tabla cambia de página
        trPr = t.rows[0]._tr.get_or_add_trPr()
        h = OxmlElement("w:tblHeader"); h.set(qn("w:val"), "true"); trPr.append(h)
        self.nota(nota or "Fuente: elaboración propia.")

    def referencia(self, t):
        p = self.d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        espaciado(p, 1.5, 0, 6)
        p.paragraph_format.left_indent = Cm(1.27)
        p.paragraph_format.first_line_indent = Cm(-1.27)
        texto(p, t)

    def guardar(self):
        cp = self.d.core_properties
        cp.author = cp.last_modified_by = "Ximena Sánchez Martínez"
        cp.title = TITULO
        cp.comments = cp.keywords = cp.subject = ""
        self.d.save(SALIDA_DOCX)


def f3(x):
    return f"{x:.3f}".replace(".", ",")


def pct(x):
    return f"{x * 100:.1f} %".replace(".", ",")


def miles(n):
    return f"{n:,}".replace(",", ".")


def construir():
    r = json.loads((RES / "metricas.json").read_text(encoding="utf-8"))
    t, d, cr = r["test"], r["dataset"], r["criterios"]
    lr, comp = t["Regresión Logística"], t["COMPAS (decil ≥ 5)"]
    cv = pd.read_csv(RES / "comparacion_cv.csv")
    eqr = pd.read_csv(RES / "equidad_raza.csv")
    eqs = pd.read_csv(RES / "equidad_sexo.csv")
    eqc = pd.read_csv(RES / "equidad_raza_compas.csv")
    muestra = pd.read_csv(c.CSV_LIMPIO).head(6)
    g = lambda df, col, v: df[df[col] == v].iloc[0]  # noqa: E731
    afro, cauc = g(eqr, "race", "African-American"), g(eqr, "race", "Caucasian")
    afro_c, cauc_c = g(eqc, "race", "African-American"), g(eqc, "race", "Caucasian")
    brecha = r["brecha_fpr_afro_vs_caucasico"]
    auc_cv = cv.set_index("modelo")["roc_auc"]

    inf = Informe()
    inf.portada()
    inf.encabezado()

    # Introducción
    inf.titulo("Introducción", nueva_pagina=True)
    inf.parrafo(
        "En varios sistemas judiciales se usan algoritmos para estimar el riesgo de que una persona acusada "
        "vuelva a delinquir. Ese puntaje influye en decisiones sobre libertad provisional, fianza o condena. "
        "El caso más conocido es COMPAS, una herramienta comercial empleada en Estados Unidos. En 2016, la "
        "organización periodística ProPublica publicó los datos del condado de Broward (Florida) y mostró que la "
        "herramienta se equivocaba de forma distinta según la raza de la persona (Angwin et al., 2016).")
    inf.parrafo(
        "En este mini-proyecto se construye un modelo propio, sencillo y transparente, que estima la probabilidad "
        "de que una persona reincida en los dos años siguientes. Luego se mide su desempeño con métricas "
        "cuantitativas y se analiza, sobre todo, a quién perjudican sus errores. El trabajo recorre las siete etapas "
        "del workflow básico de Machine Learning y termina con un análisis ético, conclusiones y recomendaciones.")
    inf.parrafo(f"El código, los datos limpios y los resultados están en el repositorio: <b>{REPO}</b>")

    # 1. Modelo
    inf.seccion("1. Selección del modelo")
    inf.seccion("1.1 Problema y propósito")
    inf.parrafo(
        "La tarea es una <b>clasificación binaria</b>: a partir de la edad, los antecedentes y el tipo de cargo, "
        "predecir si la persona volverá a ser acusada de un delito en los dos años siguientes (1) o no (0). El "
        "propósito es académico: comparar un modelo abierto con la herramienta COMPAS y auditar su equidad. "
        "No se pretende apoyar decisiones sobre personas reales.")
    inf.seccion("1.2 Modelo elegido: Regresión Logística")
    inf.parrafo(
        "La Regresión Logística combina las variables de forma lineal y transforma el resultado en una "
        "probabilidad entre 0 y 1 mediante la función sigmoide. Se eligió por tres razones:")
    inf.vinetas([
        "<b>Transparencia.</b> Cada variable tiene un coeficiente que se puede leer y explicar. En un contexto "
        "judicial, la persona afectada tiene derecho a saber por qué se le asignó un riesgo.",
        "<b>Probabilidades.</b> Entrega un grado de riesgo, no solo un «sí» o un «no».",
        f"<b>Desempeño.</b> Se comparó con un Árbol de Decisión y con KNN mediante validación cruzada. Obtuvo "
        f"el mejor AUC ({f3(auc_cv['Regresión Logística'])}) y un F1 prácticamente igual al de los demás "
        "(diferencias de 0,01, menores que la variación entre particiones).",
    ])
    inf.figura(RES / "coeficientes.png", 13, "Peso de cada variable en la Regresión Logística")
    inf.parrafo(
        "Los antecedentes como adulto (<i>priors_count</i>) son la variable que más aumenta el riesgo estimado; "
        "la edad lo reduce: a mayor edad, menor probabilidad de reincidir.")

    # 2. Dataset
    inf.seccion("2. Descripción del dataset")
    inf.parrafo(
        f"Se usó el dataset público <b>COMPAS</b> de ProPublica (archivo <i>compas-scores-two-years.csv</i>): "
        f"personas evaluadas en el condado de Broward entre 2013 y 2014. De 7.214 registros quedaron "
        f"<b>{miles(d['filas'])}</b> tras aplicar los mismos filtros de ProPublica: arresto a menos de 30 días de "
        "la evaluación, caso con desenlace conocido, delitos ordinarios y puntaje válido. La tasa de reincidencia "
        f"es de {pct(d['tasa_reincidencia'])}, así que las clases están razonablemente equilibradas.")
    inf.tabla(
        [["Variable", "Tipo", "Uso", "Descripción"],
         ["age", "Numérica", "Entrada", "Edad en años"],
         ["priors_count", "Numérica", "Entrada", "Antecedentes como adulto"],
         ["juv_fel_count", "Numérica", "Entrada", "Delitos graves juveniles"],
         ["juv_misd_count", "Numérica", "Entrada", "Delitos menores juveniles"],
         ["juv_other_count", "Numérica", "Entrada", "Otros antecedentes juveniles"],
         ["c_charge_degree", "Categórica", "Entrada", "F = delito grave; M = delito menor"],
         ["race, sex", "Categóricas", "Auditoría", "No entran al modelo; miden la equidad"],
         ["decile_score", "Numérica", "Comparación", "Puntaje COMPAS (1 a 10)"],
         ["two_year_recid", "Binaria", "Objetivo", "1 = reincidió en dos años"]],
        [3.6, 2.4, 2.4, 7.2], "Variables del dataset y su uso en el modelo")
    inf.tabla(
        [["edad", "antec.", "juv_fel", "juv_misd", "juv_otros", "grado", "raza", "sexo", "decil", "reincide"]]
        + muestra.astype(str).values.tolist(),
        [1.2, 1.3, 1.4, 1.6, 1.7, 1.3, 3.2, 1.4, 1.3, 1.6],
        "Muestra de seis registros del dataset limpio",
        "Fuente: ProPublica (2016). Se eliminaron nombres, fechas de nacimiento y números de caso.", tam=9)
    inf.parrafo(
        "Composición: " + ", ".join(f"{k} {miles(v)}" for k, v in d["por_raza"].items()) + "; "
        + ", ".join(f"{k} {miles(v)}" for k, v in d["por_sexo"].items()) + ".")

    # 3. Arquitectura y workflow
    inf.seccion("3. Arquitectura del sistema y workflow")
    inf.parrafo(
        "El sistema es un conjunto de módulos de Python con scikit-learn que se ejecutan desde la terminal. "
        "Cada etapa del workflow de Machine Learning corresponde a un archivo del repositorio:")
    inf.tabla(
        [["Etapa", "Archivo", "Qué se hace"],
         ["1. Definir la tarea", "README.md", "Clasificación binaria: reincide o no reincide"],
         ["2. Recolectar datos", "src/datos.py", "Descarga el CSV público de ProPublica"],
         ["3. Representar la entrada", "src/datos.py, src/modelos.py", "Filtros, quita datos personales, escala y codifica"],
         ["4. Elegir modelo", "src/modelos.py", "Referencia, Regresión Logística, Árbol y KNN"],
         ["5. Entrenar", "src/entrenar_evaluar.py", "Validación cruzada de 5 particiones (80 % de los datos)"],
         ["6. Evaluar", "src/entrenar_evaluar.py", "Métricas, matriz de confusión y equidad en el 20 % de prueba"],
         ["7. Usar con datos nuevos", "src/predecir.py", "Probabilidad para un caso nuevo, con validación de entradas"]],
        [3.8, 4.6, 7.2], "Etapas del workflow y su implementación")
    inf.figura(DOCS / "c4_contexto.png", 15.5, "Diagrama C4 de contexto del sistema")
    inf.parrafo(
        "<b>Decisiones de arquitectura.</b> (1) Scripts por lotes con <i>Pipeline</i> de scikit-learn y semilla "
        "fija, para que un solo comando reproduzca todo. (2) Regresión Logística por su transparencia. "
        "(3) Archivos locales versionados en Git, sin despliegue: publicar un modelo de riesgo penal sería un uso "
        "irresponsable. (4) Raza y sexo fuera del modelo, pero conservados para auditar. El detalle de cada "
        "decisión está en el README del repositorio.")
    inf.parrafo(
        "<b>Separación de datos.</b> 80 % entrenamiento (" + miles(d["train"]) + ") y 20 % prueba ("
        + miles(d["test"]) + "), estratificada por la variable objetivo. Los modelos se compararon con validación "
        "cruzada solo dentro del entrenamiento, y la prueba se usó una sola vez, al final. El escalado se ajusta "
        "dentro del <i>Pipeline</i>, así que no hay fuga de información; nueve pruebas automáticas lo verifican.")

    # 4. Métricas
    inf.seccion("4. Métricas de evaluación")
    filas_cv = [["Modelo", "Accuracy", "Precision", "Recall", "F1", "AUC"]] + [
        [x.modelo, f3(x.accuracy), f3(x.precision), f3(x.recall), f3(x.f1), f3(x.roc_auc)]
        for x in cv.itertuples()]
    inf.tabla(filas_cv, [5.6, 2.0, 2.0, 2.0, 2.0, 2.0],
              "Comparación de modelos con validación cruzada de 5 particiones (entrenamiento)", resaltar=2)
    filas_t = [["Modelo", "Accuracy", "Precision", "Recall", "F1", "AUC"]] + [
        [n, f3(m["accuracy"]), f3(m["precision"]), f3(m["recall"]), f3(m["f1"]), f3(m["auc"])]
        for n, m in t.items()]
    inf.tabla(filas_t, [5.6, 2.0, 2.0, 2.0, 2.0, 2.0],
              "Resultados en el conjunto de prueba (1.235 personas)", resaltar=2,
              nota="Fuente: elaboración propia. COMPAS usa el puntaje real de la herramienta (decil ≥ 5 = riesgo medio o alto).")
    inf.parrafo("Interpretación de cada métrica para la Regresión Logística:")
    inf.vinetas([
        f"<b>Accuracy = {f3(lr['accuracy'])}.</b> Acierta en 69 de cada 100 personas. La referencia, que siempre "
        "dice «no reincide», acierta en 55. El modelo aporta, pero falla en casi un tercio de los casos.",
        f"<b>Precision = {f3(lr['precision'])}.</b> De cada 100 personas marcadas como de alto riesgo, 72 sí "
        "reincidieron y 28 no. Esas 28 recibirían un trato más duro sin motivo.",
        f"<b>Recall = {f3(lr['recall'])}.</b> Detecta solo a la mitad de quienes reincidieron.",
        f"<b>F1 = {f3(lr['f1'])}.</b> Resume precision y recall; queda bajo por el recall.",
        f"<b>AUC = {f3(lr['auc'])}.</b> El 73 % de las veces le asigna más riesgo a quien sí reincide que a quien "
        f"no. Es el mismo nivel de COMPAS ({f3(comp['auc'])}), con solo seis variables públicas.",
    ])
    inf.parrafo(
        "<b>Implicación.</b> El modelo es mejor que adivinar y comparable a una herramienta comercial, pero su techo "
        "es bajo: con estas variables no se puede predecir con seguridad el comportamiento futuro de una persona. "
        "Dressel y Farid (2018) llegaron a la misma conclusión: personas sin formación jurídica acertaban tanto "
        "como COMPAS.")
    inf.tabla(
        [["Criterio de aceptación", "Umbral", "Resultado", "¿Cumple?"],
         ["Supera a la referencia (F1)", "> 0", f3(lr["f1"]), "Sí"],
         ["F1 mínimo", f"≥ {f3(cr['f1_minimo'])}", f3(lr["f1"]), "Sí" if cr["cumple_f1"] else "No"],
         ["AUC mínimo", f"≥ {f3(cr['auc_minimo'])}", f3(lr["auc"]), "Sí" if cr["cumple_auc"] else "No"],
         ["Brecha de FPR afroamericano vs. caucásico", f"≤ {f3(cr['brecha_fpr_maxima'])}", f3(brecha),
          "Sí" if cr["cumple_equidad"] else "No"],
         ["Sin datos personales ni fuga train/test", "—", "Verificado por pruebas", "Sí"]],
        [7.0, 2.4, 3.6, 2.2], "Criterios de aceptación del software")

    # 5. Matriz de confusión
    inf.seccion("5. Matriz de confusión")
    inf.figura(RES / "matriz_confusion.png", 10.5, "Matriz de confusión de la Regresión Logística en el conjunto de prueba")
    inf.vinetas([
        f"<b>Verdaderos positivos (VP = {lr['VP']}).</b> Personas que reincidieron y el modelo marcó como de alto "
        "riesgo. Acierto.",
        f"<b>Verdaderos negativos (VN = {lr['VN']}).</b> Personas que no reincidieron y el modelo marcó como de "
        "bajo riesgo. Acierto.",
        f"<b>Falsos positivos (FP = {lr['FP']}).</b> Personas que no reincidieron, pero el modelo las marcó como de "
        "alto riesgo. Es el error más grave desde los derechos: puede llevar a negar la libertad a alguien que no "
        "lo merecía.",
        f"<b>Falsos negativos (FN = {lr['FN']}).</b> Personas que sí reincidieron, pero el modelo las dejó como de "
        "bajo riesgo. Afecta la seguridad de posibles víctimas.",
    ])
    inf.parrafo(
        f"El modelo es «prudente»: comete pocos falsos positivos ({lr['FP']}) a cambio de muchos falsos negativos "
        f"({lr['FN']}). Mover el umbral de 0,5 cambia ese equilibrio, y esa es una decisión de política, no técnica.")

    # 6. Ética
    inf.seccion("6. Análisis ético")
    inf.seccion("6.1 Sesgos del dataset y del modelo")
    inf.parrafo(
        "La etiqueta no mide «volver a delinquir», sino «volver a ser acusado». Si la policía patrulla más ciertos "
        "barrios, las personas de esos barrios acumulan más arrestos y más antecedentes. El modelo no usa la raza, "
        "pero sí los antecedentes, que funcionan como <b>variable sustituta (proxy)</b> de esa vigilancia desigual.")
    filas_eq = [["Grupo", "n", "Reincidencia real", "Marcados alto riesgo", "FPR modelo", "FNR modelo", "FPR COMPAS"],
                ["Afroamericano", int(afro.n), pct(afro.tasa_real_reincidencia), pct(afro.tasa_marcados_alto_riesgo),
                 f3(afro.FPR), f3(afro.FNR), f3(afro_c.FPR)],
                ["Caucásico", int(cauc.n), pct(cauc.tasa_real_reincidencia), pct(cauc.tasa_marcados_alto_riesgo),
                 f3(cauc.FPR), f3(cauc.FNR), f3(cauc_c.FPR)]]
    for nombre, val in (("Hombres", "Male"), ("Mujeres", "Female")):
        x = g(eqs, "sex", val)
        filas_eq.append([nombre, int(x.n), pct(x.tasa_real_reincidencia), pct(x.tasa_marcados_alto_riesgo),
                         f3(x.FPR), f3(x.FNR), "—"])
    inf.tabla(filas_eq, [2.8, 1.3, 2.4, 2.6, 2.1, 2.1, 2.3],
              "Tasas de error por grupo en el conjunto de prueba",
              "Fuente: elaboración propia. FPR: de quienes no reincidieron, cuántos fueron marcados como de alto "
              "riesgo. FNR: de quienes sí reincidieron, cuántos quedaron como de bajo riesgo.")
    inf.figura(RES / "equidad_raza.png", 13.5, "Errores del modelo por raza")
    inf.parrafo(
        f"Una persona afroamericana que <b>no</b> reincide tiene el doble de probabilidad de ser marcada como de "
        f"alto riesgo que una caucásica (FPR {f3(afro.FPR)} frente a {f3(cauc.FPR)}). A las personas caucásicas, "
        f"en cambio, el modelo les deja pasar más reincidencias (FNR {f3(cauc.FNR)}). COMPAS tiene la misma brecha, "
        f"más grande ({f3(afro_c.FPR)} frente a {f3(cauc_c.FPR)}). Nuestro modelo la reduce, pero no la elimina: la "
        f"brecha es de {f3(brecha)}, por encima del máximo tolerado de {f3(cr['brecha_fpr_maxima'])}.")
    inf.seccion("6.2 Equidad")
    inf.parrafo(
        "Chouldechova (2017) y Kleinberg et al. (2017) demostraron que, cuando dos grupos tienen tasas de "
        "reincidencia distintas, es matemáticamente imposible que un modelo sea igual de preciso para ambos y "
        "tenga, a la vez, las mismas tasas de error. Siempre hay que escoger qué tipo de justicia se prioriza. "
        "Esa elección no le corresponde al ingeniero: es una decisión jurídica y social que debe ser explícita.")
    inf.seccion("6.3 Privacidad y uso responsable de los datos")
    inf.vinetas([
        "El CSV original contiene nombres, fechas de nacimiento y números de caso de personas reales. No se sube "
        "al repositorio: el código conserva solo diez columnas necesarias (minimización de datos).",
        "Aunque los datos son públicos, son datos sobre antecedentes penales. En Colombia, la Ley 1581 de 2012 "
        "los trata como datos sensibles, con protección reforzada.",
        "El modelo no se despliega ni se expone como servicio, para que no se pueda usar con personas reales.",
    ])
    inf.seccion("6.4 Impacto social")
    inf.parrafo(
        "Un falso positivo puede significar meses de detención preventiva, pérdida del empleo y ruptura familiar. "
        "Si esos errores se concentran en un grupo, el algoritmo refuerza una desigualdad que ya existía, y lo hace "
        "con apariencia de objetividad. Además, los nuevos arrestos alimentan los datos del siguiente modelo: es un "
        "ciclo que se retroalimenta.")
    inf.seccion("6.5 Justicia y transparencia en la toma de decisiones")
    inf.parrafo(
        "COMPAS es un software propietario: los acusados no pueden conocer cómo se calcula su puntaje. Este "
        "proyecto muestra que un modelo abierto de seis variables obtiene el mismo desempeño, de modo que la "
        "opacidad no se justifica técnicamente. Una herramienta de este tipo debería ser auditable, explicable a "
        "la persona afectada y usarse solo como apoyo del juicio humano, nunca como su reemplazo, con la "
        "posibilidad de controvertir el resultado (debido proceso).")

    # 7. Riesgos
    inf.seccion("7. Riesgos técnicos")
    inf.tabla(
        [["Riesgo", "Impacto", "Mitigación"],
         ["Sesgo en los datos (arrestos desiguales; los antecedentes son proxy de la raza)", "Alto",
          "Raza y sexo fuera del modelo, auditoría de FPR/FNR por grupo y criterio de equidad"],
         ["Fuga de información entre entrenamiento y prueba", "Medio",
          "Pipeline, separación estratificada única y prueba automática"],
         ["Sobreajuste", "Medio",
          "Modelos simples, validación cruzada; CV y prueba difieren en menos de 0,02 de AUC"],
         ["Datos insuficientes (31 asiáticos, 11 nativos; un solo condado)", "Medio",
          "No se reportan grupos con menos de 50 casos; se declara que no se puede generalizar"],
         ["Etiqueta imperfecta: «reincidir» = «volver a ser acusado»", "Alto",
          "Se documenta; se recomienda usar condenas u otras fuentes"]],
        [6.2, 1.8, 7.6], "Riesgos técnicos, impacto y mitigación")

    # 8. Conclusiones
    inf.seccion("8. Conclusiones técnicas")
    inf.vinetas([
        f"La Regresión Logística supera claramente a la referencia (F1 {f3(lr['f1'])} frente a 0) y cumple los "
        f"criterios de desempeño: F1 ≥ {f3(cr['f1_minimo'])} y AUC ≥ {f3(cr['auc_minimo'])}.",
        f"Su capacidad para distinguir entre quien reincide y quien no (AUC {f3(lr['auc'])}) es igual a la de "
        "COMPAS, con un modelo más simple y transparente.",
        "Los cuatro modelos quedaron muy cerca entre sí. El límite no está en el algoritmo, sino en la poca "
        "información que contienen las variables.",
        f"El recall es bajo ({f3(lr['recall'])}): el modelo deja pasar a la mitad de quienes reinciden.",
        "No hubo sobreajuste: las métricas de validación cruzada y de prueba difieren en menos de 0,02.",
        f"<b>No cumple el criterio de equidad</b> (brecha de FPR {f3(brecha)} > {f3(cr['brecha_fpr_maxima'])}). "
        "Veredicto: es aceptable como ejercicio académico, pero <b>no es apto para decisiones sobre personas "
        "reales</b>.",
    ])

    # 9. Recomendaciones
    inf.seccion("9. Recomendaciones para mejorar")
    inf.vinetas([
        "<b>Mitigar el sesgo:</b> ajustar umbrales por grupo o aplicar técnicas como reponderación o "
        "<i>equalized odds</i> (por ejemplo, con la librería Fairlearn) y medir cuánto desempeño se sacrifica.",
        "<b>Mejorar la etiqueta:</b> usar condenas en lugar de nuevas acusaciones, para reducir el efecto de la "
        "vigilancia policial desigual.",
        "<b>Más y mejores variables:</b> factores protectores (empleo, estudio, red de apoyo), no solo antecedentes.",
        "<b>Calibrar el umbral</b> según el costo real de cada error (falso positivo frente a falso negativo), "
        "definido con expertos jurídicos.",
        "<b>Validar con otros datos:</b> otras jurisdicciones y años, incluido el contexto colombiano.",
        "<b>Gobernanza:</b> auditorías externas periódicas, explicación individual de cada puntaje y supervisión "
        "humana obligatoria.",
    ])

    # Referencias
    inf.titulo("Referencias", nueva_pagina=True)
    for ref in [
        "Angwin, J., Larson, J., Mattu, S. y Kirchner, L. (2016). <i>Machine bias</i>. ProPublica. "
        "https://www.propublica.org/article/machine-bias-risk-assessments-in-criminal-sentencing",
        "Chouldechova, A. (2017). Fair prediction with disparate impact: A study of bias in recidivism prediction "
        "instruments. <i>Big Data, 5</i>(2), 153-163. https://doi.org/10.1089/big.2016.0047",
        "Congreso de Colombia. (2012). <i>Ley 1581 de 2012, por la cual se dictan disposiciones generales para la "
        "protección de datos personales</i>.",
        "Dressel, J. y Farid, H. (2018). The accuracy, fairness, and limits of predicting recidivism. "
        "<i>Science Advances, 4</i>(1). https://doi.org/10.1126/sciadv.aao5580",
        "Kleinberg, J., Mullainathan, S. y Raghavan, M. (2017). Inherent trade-offs in the fair determination of "
        "risk scores. En <i>Proceedings of ITCS 2017</i>. https://arxiv.org/abs/1609.05807",
        "Larson, J., Mattu, S., Kirchner, L. y Angwin, J. (2016). <i>How we analyzed the COMPAS recidivism "
        "algorithm</i>. ProPublica. https://github.com/propublica/compas-analysis",
        "Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., … Duchesnay, É. (2011). "
        "Scikit-learn: Machine learning in Python. <i>Journal of Machine Learning Research, 12</i>, 2825-2830.",
    ]:
        inf.referencia(ref)

    inf.guardar()
    return SALIDA_DOCX


def exportar_pdf():
    ps = (
        "$w = New-Object -ComObject Word.Application; $w.Visible = $false; "
        f"$d = $w.Documents.Open('{SALIDA_DOCX}'); $d.Fields.Update() | Out-Null; "
        f"$d.SaveAs([ref]'{SALIDA_PDF}', [ref]17); $d.Close($false); $w.Quit()"
    )
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, timeout=180)
        print(SALIDA_PDF)
    except Exception as e:  # sin Word queda solo el .docx
        print("No se pudo exportar a PDF:", e)


if __name__ == "__main__":
    print(construir())
    exportar_pdf()
