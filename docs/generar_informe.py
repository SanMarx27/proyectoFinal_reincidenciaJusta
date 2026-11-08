"""Genera docs/informe_mini_proyecto.pdf a partir de resultados/.

Uso: python docs/generar_informe.py   (antes: python -m src.entrenar_evaluar)
"""
import json
import sys
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from src import config as c  # noqa: E402

RES = RAIZ / "resultados"
SALIDA = RAIZ / "docs" / "informe_mini_proyecto.pdf"
REPO = "https://github.com/SanMarx27/proyectoFinal_reincidenciaJusta"
AZUL = colors.HexColor("#123B5D")

st = getSampleStyleSheet()
CUERPO = ParagraphStyle("c", parent=st["Normal"], fontName="Times-Roman", fontSize=11,
                        leading=16, alignment=TA_JUSTIFY, spaceAfter=6)
VINETA = ParagraphStyle("v", parent=CUERPO, leftIndent=14, bulletIndent=4, spaceAfter=3)
H1 = ParagraphStyle("h1", parent=st["Heading1"], fontName="Times-Bold", fontSize=14,
                    textColor=AZUL, spaceBefore=10, spaceAfter=6, keepWithNext=1)
H2 = ParagraphStyle("h2", parent=st["Heading2"], fontName="Times-Bold", fontSize=12,
                    textColor=AZUL, spaceBefore=8, spaceAfter=4, keepWithNext=1)
CENTRO = ParagraphStyle("ce", parent=CUERPO, alignment=TA_CENTER)
PIE = ParagraphStyle("pie", parent=CUERPO, fontSize=9, alignment=TA_CENTER, textColor=colors.grey)
CELDA = ParagraphStyle("t", parent=CUERPO, fontSize=9, leading=11, alignment=0, spaceAfter=0)


def p(t):
    return Paragraph(t, CUERPO)


def vinetas(items):
    return [Paragraph(i, VINETA, bulletText="•") for i in items]


CABECERA = ParagraphStyle("th", parent=CELDA, textColor=colors.white, fontName="Times-Bold")


def tabla(filas, anchos=None, resaltar=None, estilo_celda=None):
    ec = estilo_celda or CELDA
    eh = ParagraphStyle("th2", parent=ec, textColor=colors.white, fontName="Times-Bold")
    datos = [[Paragraph(str(x), eh) for x in filas[0]]] + [[Paragraph(str(x), ec) for x in f] for f in filas[1:]]
    t = Table(datos, colWidths=anchos, hAlign="CENTER", repeatRows=1)
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f5f8")]),
    ]
    if resaltar:
        estilo.append(("BACKGROUND", (0, resaltar), (-1, resaltar), colors.HexColor("#dbe8f4")))
    t.setStyle(TableStyle(estilo))
    return t


def img(ruta, ancho_cm):
    from reportlab.lib.utils import ImageReader
    w, h = ImageReader(str(ruta)).getSize()
    return Image(str(ruta), width=ancho_cm * cm, height=ancho_cm * cm * h / w)


def f3(x):
    return f"{x:.3f}".replace(".", ",")


def pct(x):
    return f"{x * 100:.1f} %".replace(".", ",")


def pie_pagina(canvas, doc):
    if doc.page > 1:
        canvas.setFont("Times-Roman", 9)
        canvas.setFillColor(colors.grey)
        canvas.drawCentredString(letter[0] / 2, 1.2 * cm,
                                 f"Universidad de La Salle · Teoría de la Computación II · {doc.page}")


def portada():
    return [
        Spacer(1, 2.2 * cm),
        Paragraph("<b>UNIVERSIDAD DE LA SALLE</b>", ParagraphStyle("u", parent=CENTRO, fontSize=16, textColor=AZUL)),
        Paragraph("Facultad de Ingeniería · Ingeniería de Software", CENTRO),
        Spacer(1, 2.5 * cm),
        Paragraph("<b>Actividad 6. Mini-proyecto de Machine Learning</b>", ParagraphStyle("t", parent=CENTRO, fontSize=15)),
        Spacer(1, 0.4 * cm),
        Paragraph("Predicción de reincidencia penal con Regresión Logística: desempeño, "
                  "matriz de confusión y análisis ético con el dataset COMPAS",
                  ParagraphStyle("st", parent=CENTRO, fontSize=12.5, leading=17)),
        Spacer(1, 3 * cm),
        Paragraph("<b>Estudiante:</b><br/>Ximena Sánchez Martínez", CENTRO),
        Spacer(1, 0.5 * cm),
        Paragraph("<b>Asignatura:</b><br/>Teoría de la Computación II", CENTRO),
        Spacer(1, 0.5 * cm),
        Paragraph(f"<b>Repositorio (rama develop):</b><br/><link href='{REPO}/tree/develop' color='blue'>{REPO}/tree/develop</link>", CENTRO),
        Spacer(1, 3 * cm),
        Paragraph("Bogotá D.C., noviembre de 2026", CENTRO),
        PageBreak(),
    ]


def main():
    r = json.loads((RES / "metricas.json").read_text(encoding="utf-8"))
    t, d = r["test"], r["dataset"]
    lr = t["Regresión Logística"]
    cv = pd.read_csv(RES / "comparacion_cv.csv")
    eqr = pd.read_csv(RES / "equidad_raza.csv")
    eqs = pd.read_csv(RES / "equidad_sexo.csv")
    eqc = pd.read_csv(RES / "equidad_raza_compas.csv")
    muestra = pd.read_csv(c.CSV_LIMPIO).head(6)

    def fila(df, col, val):
        return df[df[col] == val].iloc[0]

    afro, cauc = fila(eqr, "race", "African-American"), fila(eqr, "race", "Caucasian")
    afro_c, cauc_c = fila(eqc, "race", "African-American"), fila(eqc, "race", "Caucasian")

    h = portada()

    # 1. Modelo
    h += [Paragraph("1. Modelo seleccionado y propósito", H1),
          p("<b>Problema.</b> Varios sistemas judiciales usan algoritmos para estimar el riesgo de que una "
            "persona acusada vuelva a delinquir. El más conocido es COMPAS, empleado en Estados Unidos para "
            "decisiones de libertad provisional y fianza. El propósito de este mini-proyecto es construir un "
            "modelo sencillo que estime la probabilidad de reincidencia en los dos años siguientes, medir qué "
            "tan bien funciona y, sobre todo, analizar a quién perjudican sus errores."),
          p("<b>Modelo elegido: Regresión Logística.</b> Es un modelo de clasificación binaria que combina las "
            "variables de forma lineal y transforma el resultado en una probabilidad entre 0 y 1 mediante la "
            "función sigmoide. Se eligió por tres razones:"),
          *vinetas([
              "<b>Transparencia:</b> cada variable tiene un coeficiente que se puede leer y explicar. En un "
              "contexto judicial, una persona tiene derecho a saber por qué se le asignó un riesgo.",
              "<b>Probabilidades:</b> entrega un grado de riesgo, no solo un «sí» o un «no».",
              f"<b>Desempeño:</b> se comparó con un Árbol de Decisión y con KNN usando validación cruzada. Obtuvo "
              f"el mejor AUC ({f3(cv.loc[cv.modelo == 'Regresión Logística', 'roc_auc'].iloc[0])}) y un F1 "
              "prácticamente igual al de los demás (diferencias de 0,01, menores que la variación entre particiones)."]),
          img(RES / "coeficientes.png", 13),
          Paragraph("Figura 1. Coeficientes del modelo. Los antecedentes aumentan el riesgo; la edad lo reduce.", PIE)]

    # 2. Dataset
    h += [Paragraph("2. Descripción del dataset", H1),
          p(f"Se usó el dataset público <b>COMPAS</b> publicado por ProPublica (2016): personas evaluadas en el "
            f"condado de Broward (Florida) entre 2013 y 2014. De 7.214 registros quedaron <b>{d['filas']:,}</b> ".replace(",", ".")
            + "tras aplicar los mismos filtros de ProPublica (arresto a menos de 30 días de la evaluación, caso con "
            "desenlace conocido y delitos ordinarios)."),
          p(f"<b>Objetivo del modelo:</b> predecir <i>two_year_recid</i> (1 = la persona volvió a ser acusada en dos "
            f"años). La tasa de reincidencia es de {pct(d['tasa_reincidencia'])}, así que las clases están "
            "razonablemente equilibradas."),
          tabla([["Variable", "Tipo", "Uso", "Descripción"],
                 ["age", "Numérica", "Entrada", "Edad en años"],
                 ["priors_count", "Numérica", "Entrada", "Número de antecedentes como adulto"],
                 ["juv_fel_count", "Numérica", "Entrada", "Delitos graves juveniles"],
                 ["juv_misd_count", "Numérica", "Entrada", "Delitos menores juveniles"],
                 ["juv_other_count", "Numérica", "Entrada", "Otros antecedentes juveniles"],
                 ["c_charge_degree", "Categórica", "Entrada", "F = delito grave (felony); M = menor (misdemeanor)"],
                 ["race, sex", "Categóricas", "Solo auditoría", "No entran al modelo; se usan para medir la equidad"],
                 ["decile_score", "Numérica", "Comparación", "Puntaje COMPAS (1-10)"],
                 ["two_year_recid", "Binaria", "Objetivo", "1 = reincidió en dos años"]],
                [3.2 * cm, 2.3 * cm, 2.5 * cm, 8.5 * cm]),
          Spacer(1, 6),
          p("<b>Muestra de los datos limpios</b> (sin nombres, fechas ni números de caso):"),
          tabla([["edad", "antec.", "juv_fel", "juv_misd", "juv_otros", "grado", "raza", "sexo", "decil", "reincide"]]
                + muestra.astype(str).values.tolist(),
                [1.2 * cm, 1.4 * cm, 1.4 * cm, 1.6 * cm, 1.7 * cm, 1.3 * cm, 2.9 * cm, 1.4 * cm, 1.3 * cm, 1.7 * cm],
                estilo_celda=ParagraphStyle("mini", parent=CELDA, fontSize=8.5)),
          Spacer(1, 4),
          p("Composición: " + ", ".join(f"{k} {v:,}".replace(",", ".") for k, v in d["por_raza"].items())
            + "; " + ", ".join(f"{k} {v:,}".replace(",", ".") for k, v in d["por_sexo"].items()) + "."),
          p(f"<b>Separación:</b> 80 % entrenamiento ({d['train']:,}) y 20 % prueba ({d['test']:,})".replace(",", ".")
            + ", estratificada y con semilla fija. Los modelos se compararon con validación cruzada de 5 particiones "
            "dentro del entrenamiento; la prueba se usó una sola vez.")]

    # 3. Métricas
    filas = [["Modelo", "Accuracy", "Precision", "Recall", "F1", "AUC"]]
    for nombre, m in t.items():
        filas.append([nombre, f3(m["accuracy"]), f3(m["precision"]), f3(m["recall"]), f3(m["f1"]), f3(m["auc"])])
    h += [Paragraph("3. Métricas de evaluación", H1),
          p("Resultados en el conjunto de prueba (1.235 personas). El modelo de referencia predice siempre la clase "
            "más frecuente («no reincide») y sirve para saber si el modelo aporta algo. La fila de COMPAS usa el "
            "puntaje real de la herramienta (decil ≥ 5 = riesgo medio o alto)."),
          tabla(filas, [6 * cm] + [2.1 * cm] * 5, resaltar=2),
          Spacer(1, 6),
          Paragraph("Interpretación de cada métrica (Regresión Logística)", H2),
          *vinetas([
              f"<b>Accuracy = {f3(lr['accuracy'])}:</b> acierta en 69 de cada 100 personas, frente a 55 de la "
              "referencia. Aporta, pero falla en casi un tercio de los casos.",
              f"<b>Precision = {f3(lr['precision'])}:</b> de cada 100 personas marcadas como de alto riesgo, 72 sí "
              "reincidieron y 28 no. Esas 28 recibirían un trato más duro sin motivo.",
              f"<b>Recall = {f3(lr['recall'])}:</b> solo detecta a la mitad de quienes reincidieron.",
              f"<b>F1 = {f3(lr['f1'])}:</b> resume precision y recall; queda bajo por el recall.",
              f"<b>AUC = {f3(lr['auc'])}:</b> el 73 % de las veces le da más riesgo a quien sí reincide que a quien "
              f"no. Es el mismo nivel que COMPAS ({f3(t['COMPAS (decil ≥ 5)']['auc'])}), con solo seis variables públicas."]),
          p("<b>Implicación:</b> el modelo es mejor que adivinar y comparable a una herramienta comercial, pero su "
            "techo es bajo. Con estas variables no se puede predecir el comportamiento futuro de una persona con "
            "mucha seguridad. Dressel y Farid (2018) llegaron a la misma conclusión: personas sin formación "
            "jurídica acertaban tanto como COMPAS.")]

    # 4. Matriz
    h += [PageBreak(), Paragraph("4. Matriz de confusión", H1),
          img(RES / "matriz_confusion.png", 10),
          Paragraph("Figura 2. Matriz de confusión de la Regresión Logística en el conjunto de prueba.", PIE),
          *vinetas([
              f"<b>Verdaderos positivos (VP = {lr['VP']}):</b> personas que reincidieron y el modelo marcó como de "
              "alto riesgo. Acierto.",
              f"<b>Verdaderos negativos (VN = {lr['VN']}):</b> personas que no reincidieron y el modelo marcó como de "
              "bajo riesgo. Acierto.",
              f"<b>Falsos positivos (FP = {lr['FP']}):</b> personas que <u>no</u> reincidieron, pero el modelo las "
              "marcó como de alto riesgo. Es el error más grave desde los derechos: puede llevar a negar la libertad "
              "a alguien que no lo merecía.",
              f"<b>Falsos negativos (FN = {lr['FN']}):</b> personas que <u>sí</u> reincidieron, pero el modelo las "
              "dejó como de bajo riesgo. Afecta la seguridad de posibles víctimas."]),
          p("El modelo es «prudente»: comete pocos falsos positivos (111) a cambio de muchos falsos negativos (278). "
            "Mover el umbral de 0,5 cambia ese equilibrio, y esa es una decisión de política, no técnica.")]

    # 5. Ética
    h += [Paragraph("5. Análisis ético", H1),
          Paragraph("5.1 Sesgos del dataset y del modelo", H2),
          p("La etiqueta no mide «volver a delinquir» sino «volver a ser acusado». Si la policía patrulla más ciertos "
            "barrios, las personas de esos barrios acumulan más arrestos y más antecedentes. El modelo no usa la "
            "raza, pero sí los antecedentes, que funcionan como <b>variable sustituta (proxy)</b> de esos patrones de "
            "vigilancia desiguales."),
          tabla([["Grupo (prueba)", "n", "Reincidencia real", "Marcados alto riesgo", "FPR modelo", "FNR modelo", "FPR COMPAS"],
                 ["Afroamericano", int(afro.n), pct(afro.tasa_real_reincidencia), pct(afro.tasa_marcados_alto_riesgo), f3(afro.FPR), f3(afro.FNR), f3(afro_c.FPR)],
                 ["Caucásico", int(cauc.n), pct(cauc.tasa_real_reincidencia), pct(cauc.tasa_marcados_alto_riesgo), f3(cauc.FPR), f3(cauc.FNR), f3(cauc_c.FPR)]]
                + [[s, int(x.n), pct(x.tasa_real_reincidencia), pct(x.tasa_marcados_alto_riesgo), f3(x.FPR), f3(x.FNR), "—"]
                   for s, x in [("Hombres", fila(eqs, "sex", "Male")), ("Mujeres", fila(eqs, "sex", "Female"))]],
                [3 * cm, 1.3 * cm, 2.5 * cm, 2.6 * cm, 2.2 * cm, 2.2 * cm, 2.2 * cm]),
          Spacer(1, 4),
          img(RES / "equidad_raza.png", 12.5),
          Paragraph("Figura 3. Tasas de error por raza en el conjunto de prueba.", PIE),
          p(f"Una persona afroamericana que <b>no</b> reincide tiene el doble de probabilidad de ser marcada como de "
            f"alto riesgo que una caucásica (FPR {f3(afro.FPR)} frente a {f3(cauc.FPR)}). A las personas caucásicas "
            f"el modelo les deja pasar más reincidencias (FNR {f3(cauc.FNR)}). COMPAS tiene la misma brecha, más "
            f"grande ({f3(afro_c.FPR)} frente a {f3(cauc_c.FPR)}). Nuestro modelo la reduce, pero no la elimina: "
            f"brecha de {f3(r['brecha_fpr_afro_vs_caucasico'])}, por encima del máximo tolerado de 0,10."),
          Paragraph("5.2 Equidad", H2),
          p("Chouldechova (2017) y Kleinberg et al. (2017) demostraron que, cuando dos grupos tienen tasas de "
            "reincidencia distintas, es matemáticamente imposible que un modelo sea a la vez igual de preciso para "
            "ambos y tenga las mismas tasas de error. Siempre hay que escoger qué tipo de justicia se prioriza. "
            "Esa elección no le corresponde al ingeniero: es una decisión jurídica y social que debe ser explícita."),
          Paragraph("5.3 Privacidad y uso responsable de los datos", H2),
          *vinetas([
              "El CSV original contiene nombres, fechas de nacimiento y números de caso de personas reales. No se "
              "sube al repositorio; el código conserva solo diez columnas necesarias (minimización de datos).",
              "Aunque los datos son públicos, siguen siendo datos sensibles sobre antecedentes penales. En Colombia, "
              "la Ley 1581 de 2012 los trata como datos sensibles que requieren protección reforzada.",
              "El modelo no se despliega ni se expone como servicio, para que no se pueda usar con personas reales."]),
          Paragraph("5.4 Impacto social", H2),
          p("Un falso positivo puede significar meses de detención preventiva, pérdida del empleo y ruptura familiar. "
            "Si esos errores se concentran en un grupo, el algoritmo refuerza una desigualdad que ya existía, y lo "
            "hace con apariencia de objetividad. Además, los nuevos arrestos alimentan los datos del siguiente "
            "modelo: es un ciclo que se retroalimenta."),
          Paragraph("5.5 Justicia y transparencia en la toma de decisiones", H2),
          p("COMPAS es un software propietario: los acusados no pueden conocer cómo se calcula su puntaje. Este "
            "proyecto muestra que un modelo abierto de seis variables obtiene el mismo desempeño. Por eso la "
            "opacidad no se justifica técnicamente. Cualquier herramienta de este tipo debería ser auditable, "
            "explicable a la persona afectada y usarse solo como apoyo, nunca como reemplazo, del juicio humano, "
            "con posibilidad de controvertir el resultado (debido proceso).")]

    # 6. Conclusiones
    cr = r["criterios"]
    h += [Paragraph("6. Conclusiones técnicas", H1),
          *vinetas([
              f"La Regresión Logística supera claramente a la referencia (F1 {f3(lr['f1'])} frente a 0) y cumple los "
              f"criterios de desempeño: F1 ≥ {f3(cr['f1_minimo'])} y AUC ≥ {f3(cr['auc_minimo'])}.",
              f"Su capacidad de discriminación (AUC {f3(lr['auc'])}) es igual a la de COMPAS, con un modelo más "
              "simple y transparente.",
              "Los cuatro modelos quedaron muy cerca entre sí. El límite no está en el algoritmo, sino en la poca "
              "información que contienen las variables.",
              f"El recall es bajo ({f3(lr['recall'])}): el modelo deja pasar a la mitad de quienes reinciden.",
              "No hubo sobreajuste: las métricas de validación cruzada y de prueba difieren en menos de 0,02.",
              f"<b>No cumple el criterio de equidad</b> (brecha de FPR {f3(r['brecha_fpr_afro_vs_caucasico'])} > 0,10). "
              "Veredicto: es aceptable como ejercicio académico, pero <b>no es apto para decisiones sobre personas reales</b>."])]

    # 7. Recomendaciones
    h += [Paragraph("7. Recomendaciones para mejorar", H1),
          *vinetas([
              "<b>Ajustar umbrales por grupo</b> o usar técnicas de mitigación (reponderación, post-procesamiento con "
              "<i>equalized odds</i>, por ejemplo con la librería Fairlearn) y medir cuánto desempeño se sacrifica.",
              "<b>Mejorar la etiqueta:</b> usar condenas en lugar de nuevas acusaciones, para reducir el efecto de la "
              "vigilancia policial desigual.",
              "<b>Más y mejores variables:</b> factores protectores (empleo, estudio, red de apoyo) en vez de solo antecedentes.",
              "<b>Calibrar el umbral</b> con validación cruzada según el costo real de cada error (FP frente a FN), "
              "definido con expertos jurídicos.",
              "<b>Validar con otros datos:</b> otras jurisdicciones y años, incluido el contexto colombiano.",
              "<b>Gobernanza:</b> auditorías externas periódicas, explicación individual de cada puntaje y "
              "supervisión humana obligatoria."])]

    # Referencias
    h += [Paragraph("Referencias", H1)] + [Paragraph(x, ParagraphStyle("ref", parent=CUERPO, fontSize=10, leading=13, leftIndent=18, firstLineIndent=-18)) for x in [
        "Angwin, J., Larson, J., Mattu, S. y Kirchner, L. (2016). <i>Machine bias</i>. ProPublica. https://www.propublica.org/article/machine-bias-risk-assessments-in-criminal-sentencing",
        "Chouldechova, A. (2017). Fair prediction with disparate impact: A study of bias in recidivism prediction instruments. <i>Big Data, 5</i>(2), 153-163. https://doi.org/10.1089/big.2016.0047",
        "Congreso de Colombia. (2012). <i>Ley 1581 de 2012, por la cual se dictan disposiciones generales para la protección de datos personales</i>.",
        "Dressel, J. y Farid, H. (2018). The accuracy, fairness, and limits of predicting recidivism. <i>Science Advances, 4</i>(1). https://doi.org/10.1126/sciadv.aao5580",
        "Kleinberg, J., Mullainathan, S. y Raghavan, M. (2017). Inherent trade-offs in the fair determination of risk scores. <i>ITCS 2017</i>. https://arxiv.org/abs/1609.05807",
        "Larson, J., Mattu, S., Kirchner, L. y Angwin, J. (2016). <i>How we analyzed the COMPAS recidivism algorithm</i>. ProPublica. https://github.com/propublica/compas-analysis",
        "Pedregosa, F. et al. (2011). Scikit-learn: Machine learning in Python. <i>Journal of Machine Learning Research, 12</i>, 2825-2830.",
    ]]

    doc = SimpleDocTemplate(str(SALIDA), pagesize=letter, leftMargin=2.5 * cm, rightMargin=2.5 * cm,
                            topMargin=2.2 * cm, bottomMargin=2.2 * cm,
                            title="Mini-proyecto ML – Ximena Sánchez Martínez", author="Ximena Sánchez Martínez")
    doc.build(h, onFirstPage=pie_pagina, onLaterPages=pie_pagina)
    print(SALIDA)


if __name__ == "__main__":
    main()
