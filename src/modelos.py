"""Modelos candidatos. Todos comparten el mismo preprocesamiento."""
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

from src import config as c


def preprocesador():
    # El escalado y la codificación se ajustan dentro del Pipeline,
    # así nunca "ven" los datos de prueba (evita fuga de información).
    return ColumnTransformer([
        ("num", StandardScaler(), c.VARIABLES_NUM),
        ("cat", OneHotEncoder(drop="if_binary"), c.VARIABLES_CAT),
    ])


def candidatos():
    return {
        "Referencia (clase mayoritaria)": DummyClassifier(strategy="most_frequent"),
        "Regresión Logística": LogisticRegression(max_iter=1000),
        "Árbol de Decisión": DecisionTreeClassifier(max_depth=4, random_state=c.SEMILLA),
        "KNN (k=15)": KNeighborsClassifier(n_neighbors=15),
    }


def pipeline(estimador):
    return Pipeline([("prep", preprocesador()), ("modelo", estimador)])
