"""Usa el modelo entrenado con datos nuevos (paso 7 del workflow).

Uso:
  python -m src.predecir --edad 23 --antecedentes 4 --grado F
  python -m src.predecir --edad 45 --antecedentes 0 --grado M --juv-fel 0

La salida es una probabilidad orientativa, no una decisión.
"""
import argparse

import joblib
import pandas as pd

from src import config as c


def validar(edad, antecedentes, grado, juv_fel, juv_misd, juv_otros):
    if not 18 <= edad <= 100:
        raise ValueError("La edad debe estar entre 18 y 100 años.")
    if min(antecedentes, juv_fel, juv_misd, juv_otros) < 0:
        raise ValueError("Los conteos de antecedentes no pueden ser negativos.")
    if grado not in ("F", "M"):
        raise ValueError("El grado del cargo debe ser F (felony) o M (misdemeanor).")


def predecir(edad, antecedentes, grado, juv_fel=0, juv_misd=0, juv_otros=0, modelo=None):
    validar(edad, antecedentes, grado, juv_fel, juv_misd, juv_otros)
    modelo = modelo or joblib.load(c.RESULTADOS / "modelo.joblib")
    fila = pd.DataFrame([{
        "age": edad, "priors_count": antecedentes, "juv_fel_count": juv_fel,
        "juv_misd_count": juv_misd, "juv_other_count": juv_otros, "c_charge_degree": grado,
    }])
    return float(modelo.predict_proba(fila[c.VARIABLES_MODELO])[0, 1])


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--edad", type=int, required=True)
    p.add_argument("--antecedentes", type=int, required=True)
    p.add_argument("--grado", choices=["F", "M"], required=True)
    p.add_argument("--juv-fel", type=int, default=0)
    p.add_argument("--juv-misd", type=int, default=0)
    p.add_argument("--juv-otros", type=int, default=0)
    a = p.parse_args()
    prob = predecir(a.edad, a.antecedentes, a.grado, a.juv_fel, a.juv_misd, a.juv_otros)
    print(f"Probabilidad estimada de reincidencia en dos años: {prob:.1%}")
    print("Aviso: uso académico. No debe usarse para decidir sobre personas reales.")


if __name__ == "__main__":
    main()
