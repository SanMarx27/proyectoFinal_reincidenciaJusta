"""Pruebas de datos y criterios de aceptación.  Uso:  python -m pytest -q"""
import json

import pytest

from src import config as c
from src.datos import cargar, separar
from src.predecir import predecir


@pytest.fixture(scope="module")
def df():
    return cargar()


@pytest.fixture(scope="module")
def resumen():
    with open(c.RESULTADOS / "metricas.json", encoding="utf-8") as f:
        return json.load(f)


def test_sin_datos_personales(df):
    for col in ["name", "first", "last", "dob", "c_case_number", "id"]:
        assert col not in df.columns


def test_modelo_no_usa_raza_ni_sexo():
    assert not set(c.VARIABLES_SENSIBLES) & set(c.VARIABLES_MODELO)


def test_filtros_propublica(df):
    assert len(df) == 6172
    assert set(df["c_charge_degree"]) == {"F", "M"}


def test_sin_fuga_entre_train_y_test(df):
    train, test = separar(df)
    assert set(train.index).isdisjoint(test.index)
    assert len(train) + len(test) == len(df)
    # la proporción de la clase se mantiene (estratificación)
    assert abs(train[c.OBJETIVO].mean() - test[c.OBJETIVO].mean()) < 0.01


def test_supera_a_la_referencia(resumen):
    assert resumen["criterios"]["supera_referencia"]


def test_criterios_de_desempeno(resumen):
    assert resumen["criterios"]["cumple_f1"]
    assert resumen["criterios"]["cumple_auc"]


def test_prediccion_valida():
    p = predecir(edad=23, antecedentes=4, grado="F")
    assert 0 <= p <= 1


def test_mas_antecedentes_mas_riesgo():
    assert predecir(30, 10, "F") > predecir(30, 0, "F")


def test_rechaza_entradas_invalidas():
    with pytest.raises(ValueError):
        predecir(edad=12, antecedentes=0, grado="F")
    with pytest.raises(ValueError):
        predecir(edad=30, antecedentes=-1, grado="F")
