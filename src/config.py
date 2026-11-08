"""Configuración central del proyecto."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
RESULTADOS = RAIZ / "resultados"

URL_DATOS = (
    "https://raw.githubusercontent.com/propublica/compas-analysis/"
    "master/compas-scores-two-years.csv"
)
CSV_CRUDO = DATA / "compas-scores-two-years.csv"   # no se versiona (trae nombres)
CSV_LIMPIO = DATA / "compas_limpio.csv"            # sin datos personales

SEMILLA = 42
TAMANO_TEST = 0.20
FOLDS_CV = 5

# Variables que usa el modelo (no incluyen raza ni sexo).
VARIABLES_NUM = ["age", "priors_count", "juv_fel_count", "juv_misd_count", "juv_other_count"]
VARIABLES_CAT = ["c_charge_degree"]
VARIABLES_MODELO = VARIABLES_NUM + VARIABLES_CAT

# Variables sensibles: solo se usan para auditar la equidad.
VARIABLES_SENSIBLES = ["race", "sex"]

# Puntaje COMPAS (decil 1-10). Sirve como punto de comparación externo.
PUNTAJE_COMPAS = "decile_score"

OBJETIVO = "two_year_recid"  # 1 = reincidió en dos años

# Criterios de aceptación del software (ver README, sección 7).
MIN_F1 = 0.55          # claramente por encima de la referencia (F1 = 0)
MIN_AUC = 0.70         # nivel de las herramientas de riesgo usadas en la práctica
MAX_BRECHA_FPR = 0.10  # diferencia máxima tolerada de falsos positivos entre grupos
