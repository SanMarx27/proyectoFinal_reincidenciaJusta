"""Entrena, compara y evalúa los modelos. Guarda todo en resultados/.

Uso:  python -m src.entrenar_evaluar
"""
import json

import joblib
import matplotlib
import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import StratifiedKFold, cross_validate

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src import config as c  # noqa: E402
from src.datos import cargar, separar  # noqa: E402
from src.modelos import candidatos, pipeline  # noqa: E402

MODELO_ELEGIDO = "Regresión Logística"


def metricas(y, pred, prob=None):
    vn, fp, fn, vp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "accuracy": accuracy_score(y, pred),
        "precision": precision_score(y, pred, zero_division=0),
        "recall": recall_score(y, pred, zero_division=0),
        "f1": f1_score(y, pred, zero_division=0),
        "auc": roc_auc_score(y, prob) if prob is not None else None,
        "VP": int(vp), "FP": int(fp), "VN": int(vn), "FN": int(fn),
    }


def equidad(df, y, pred, grupo):
    """Tasas de error por grupo. FPR = personas que NO reincidieron
    pero el modelo marcó como de alto riesgo."""
    filas = []
    for valor, idx in df.groupby(grupo).groups.items():
        yt, yp = y.loc[idx], pred.loc[idx]
        if len(yt) < 50:  # grupos muy pequeños dan tasas poco fiables
            continue
        vn, fp, fn, vp = confusion_matrix(yt, yp, labels=[0, 1]).ravel()
        filas.append({
            grupo: valor, "n": len(yt),
            "tasa_real_reincidencia": yt.mean(),
            "tasa_marcados_alto_riesgo": yp.mean(),
            "FPR": fp / (fp + vn) if fp + vn else np.nan,
            "FNR": fn / (fn + vp) if fn + vp else np.nan,
            "precision": vp / (vp + fp) if vp + fp else np.nan,
            "accuracy": (vp + vn) / len(yt),
        })
    return pd.DataFrame(filas)


def graficar_matriz(m, ruta):
    mat = np.array([[m["VN"], m["FP"]], [m["FN"], m["VP"]]])
    fig, ax = plt.subplots(figsize=(5.8, 4.6))
    ax.imshow(mat, cmap="Blues")
    etiquetas = [["VN", "FP"], ["FN", "VP"]]
    for i in range(2):
        for j in range(2):
            ax.text(j, i, f"{etiquetas[i][j]}\n{mat[i, j]}", ha="center", va="center",
                    color="white" if mat[i, j] > mat.max() / 2 else "black", fontsize=12)
    ax.set_xticks([0, 1], ["Pred: no reincide", "Pred: reincide"])
    ax.set_yticks([0, 1], ["Real: no reincide", "Real: reincide"])
    ax.set_title("Matriz de confusión – Regresión Logística\n(conjunto de prueba, n = %d)" % mat.sum())
    fig.tight_layout()
    fig.savefig(ruta, dpi=150)
    plt.close(fig)


def graficar_equidad(tabla, grupo, ruta):
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    x = np.arange(len(tabla))
    ax.bar(x - 0.2, tabla["FPR"], 0.4, label="Falsos positivos (FPR)", color="#c0504d")
    ax.bar(x + 0.2, tabla["FNR"], 0.4, label="Falsos negativos (FNR)", color="#4f81bd")
    ax.set_xticks(x, tabla[grupo])
    ax.set_ylabel("Tasa")
    ax.set_title(f"Errores del modelo por {'raza' if grupo == 'race' else 'sexo'} (prueba)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(ruta, dpi=150)
    plt.close(fig)


def graficar_coeficientes(modelo, ruta):
    nombres = modelo.named_steps["prep"].get_feature_names_out()
    coef = modelo.named_steps["modelo"].coef_[0]
    orden = np.argsort(coef)
    fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.barh([nombres[i].split("__")[1] for i in orden], coef[orden], color="#2e7d6b")
    ax.axvline(0, color="black", lw=0.8)
    ax.set_title("Peso de cada variable (Regresión Logística)")
    fig.tight_layout()
    fig.savefig(ruta, dpi=150)
    plt.close(fig)


def main():
    c.RESULTADOS.mkdir(exist_ok=True)
    df = cargar()
    train, test = separar(df)
    Xtr, ytr = train[c.VARIABLES_MODELO], train[c.OBJETIVO]
    Xte, yte = test[c.VARIABLES_MODELO], test[c.OBJETIVO]

    # 1) Comparación con validación cruzada (solo entrenamiento)
    cv = StratifiedKFold(c.FOLDS_CV, shuffle=True, random_state=c.SEMILLA)
    filas_cv = []
    for nombre, est in candidatos().items():
        r = cross_validate(pipeline(est), Xtr, ytr, cv=cv,
                           scoring=["accuracy", "precision", "recall", "f1", "roc_auc"])
        filas_cv.append({"modelo": nombre, **{k: r[f"test_{k}"].mean() for k in
                         ["accuracy", "precision", "recall", "f1", "roc_auc"]},
                         "f1_desv": r["test_f1"].std()})
    pd.DataFrame(filas_cv).to_csv(c.RESULTADOS / "comparacion_cv.csv", index=False)

    # 2) Evaluación final en prueba (una sola vez)
    en_test, modelos = {}, {}
    for nombre, est in candidatos().items():
        m = pipeline(est).fit(Xtr, ytr)
        modelos[nombre] = m
        en_test[nombre] = metricas(yte, m.predict(Xte), m.predict_proba(Xte)[:, 1])
    # Punto de comparación externo: la herramienta COMPAS (decil >= 5 = riesgo medio/alto)
    pred_compas = (test[c.PUNTAJE_COMPAS] >= 5).astype(int)
    en_test["COMPAS (decil ≥ 5)"] = metricas(yte, pred_compas, test[c.PUNTAJE_COMPAS])

    elegido = modelos[MODELO_ELEGIDO]
    pred = pd.Series(elegido.predict(Xte), index=test.index)

    # 3) Auditoría de equidad
    eq_raza = equidad(test, yte, pred, "race")
    eq_sexo = equidad(test, yte, pred, "sex")
    eq_raza_compas = equidad(test, yte, pd.Series(pred_compas.values, index=test.index), "race")
    eq_raza.to_csv(c.RESULTADOS / "equidad_raza.csv", index=False)
    eq_sexo.to_csv(c.RESULTADOS / "equidad_sexo.csv", index=False)
    eq_raza_compas.to_csv(c.RESULTADOS / "equidad_raza_compas.csv", index=False)

    principales = eq_raza[eq_raza["race"].isin(["African-American", "Caucasian"])]
    brecha_fpr = float(principales["FPR"].max() - principales["FPR"].min())

    # 4) Gráficas y artefactos
    graficar_matriz(en_test[MODELO_ELEGIDO], c.RESULTADOS / "matriz_confusion.png")
    graficar_equidad(eq_raza, "race", c.RESULTADOS / "equidad_raza.png")
    graficar_equidad(eq_sexo, "sex", c.RESULTADOS / "equidad_sexo.png")
    graficar_coeficientes(elegido, c.RESULTADOS / "coeficientes.png")
    joblib.dump(elegido, c.RESULTADOS / "modelo.joblib")

    resumen = {
        "dataset": {"filas": len(df), "train": len(train), "test": len(test),
                    "tasa_reincidencia": float(df[c.OBJETIVO].mean()),
                    "por_raza": df["race"].value_counts().to_dict(),
                    "por_sexo": df["sex"].value_counts().to_dict()},
        "modelo_elegido": MODELO_ELEGIDO,
        "test": en_test,
        "brecha_fpr_afro_vs_caucasico": brecha_fpr,
        "criterios": {
            "f1_minimo": c.MIN_F1, "auc_minimo": c.MIN_AUC, "brecha_fpr_maxima": c.MAX_BRECHA_FPR,
            "cumple_f1": en_test[MODELO_ELEGIDO]["f1"] >= c.MIN_F1,
            "cumple_auc": en_test[MODELO_ELEGIDO]["auc"] >= c.MIN_AUC,
            "supera_referencia": en_test[MODELO_ELEGIDO]["f1"] > en_test["Referencia (clase mayoritaria)"]["f1"],
            "cumple_equidad": brecha_fpr <= c.MAX_BRECHA_FPR,
        },
    }
    with open(c.RESULTADOS / "metricas.json", "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2, default=float)

    print(pd.DataFrame(filas_cv).round(3).to_string(index=False))
    print(pd.DataFrame(en_test).T.round(3).to_string())
    print(eq_raza.round(3).to_string(index=False))
    print(eq_sexo.round(3).to_string(index=False))
    print(json.dumps(resumen["criterios"], indent=2))


if __name__ == "__main__":
    main()
