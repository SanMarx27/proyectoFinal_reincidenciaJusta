"""Carga, limpieza y separación del dataset COMPAS (ProPublica, 2016)."""
import urllib.request

import pandas as pd
from sklearn.model_selection import train_test_split

from src import config as c


def descargar():
    """Descarga el CSV original de ProPublica si no está en data/."""
    c.DATA.mkdir(exist_ok=True)
    if not c.CSV_CRUDO.exists():
        urllib.request.urlretrieve(c.URL_DATOS, c.CSV_CRUDO)
    return c.CSV_CRUDO


def limpiar(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica los mismos filtros de ProPublica y quita los datos personales.

    Filtros: arresto a +-30 días de la evaluación, caso con desenlace conocido,
    delitos ordinarios (F o M) y puntaje COMPAS válido.
    """
    df = df.loc[:, ~df.columns.duplicated()]  # el CSV trae columnas repetidas
    df = df[
        df["days_b_screening_arrest"].between(-30, 30)
        & (df["is_recid"] != -1)
        & (df["c_charge_degree"] != "O")
        & (df["score_text"] != "N/A")
    ]
    columnas = c.VARIABLES_MODELO + c.VARIABLES_SENSIBLES + [c.PUNTAJE_COMPAS, c.OBJETIVO]
    # Solo quedan estas columnas: nombre, fechas y número de caso se descartan.
    return df[columnas].dropna().reset_index(drop=True)


def cargar() -> pd.DataFrame:
    """Devuelve el dataset limpio. Lo genera la primera vez."""
    if not c.CSV_LIMPIO.exists():
        crudo = pd.read_csv(descargar())
        limpiar(crudo).to_csv(c.CSV_LIMPIO, index=False)
    return pd.read_csv(c.CSV_LIMPIO)


def separar(df: pd.DataFrame):
    """80 % entrenamiento / 20 % prueba, estratificado por la clase objetivo.

    La prueba solo se toca una vez, al final. La selección de modelo se hace
    con validación cruzada dentro del entrenamiento.
    """
    return train_test_split(
        df, test_size=c.TAMANO_TEST, random_state=c.SEMILLA, stratify=df[c.OBJETIVO]
    )
