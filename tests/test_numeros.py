"""Cédulas dichas en palabras (spec 06, R2.3)."""

import pytest

from tests.conftest import peticion
from webhook.numeros import palabras_a_numero

SIN_CEDULA = {"nombre": "María", "apellido": "González", "nacionalidad": "V", "cedula": "",
              "especialidad": "", "fecha": "", "hora": ""}


@pytest.mark.parametrize("texto, numero", [
    ("catorce millones quinientos veintitrés mil novecientos ochenta y siete", 14523987),
    ("14 millones 523 mil 987", 14523987),
    ("mi cédula es nueve millones cuatrocientos cincuenta y dos mil trescientos doce", 9452312),
    ("uno cuatro cinco dos tres nueve ocho siete", 14523987),
    ("novecientos cuarenta y cinco mil ciento veintitrés", 945123),
    ("veintiún millones", 21000000),
    ("ochenta y un millones doscientos treinta y cuatro mil quinientos sesenta y siete", 81234567),
    ("mil", 1000),
    ("1614 8811", 16148811),  # agrupación real del reconocimiento de voz
    ("14 523 987", 14523987),
])
def test_palabras_a_numero(texto, numero):
    assert palabras_a_numero(texto) == numero


@pytest.mark.parametrize("texto", ["no me la sé", "venezolano", ""])
def test_sin_numero(texto):
    assert palabras_a_numero(texto) is None


def _pedir_cedula(cliente):
    cliente.post("/webhook", json=peticion("agendar_cita", {**SIN_CEDULA, "nacionalidad": ""}, "venezolana",
                                           todos=False, esperando="cedula"))


def test_cedula_en_palabras_durante_la_cita(cliente):
    _pedir_cedula(cliente)
    res = cliente.post("/webhook", json=peticion(
        "agendar_cita", SIN_CEDULA, "catorce millones quinientos veintitrés mil novecientos ochenta y siete",
        todos=False, esperando="cedula")).json()
    parametros = next(c["parameters"] for c in res["outputContexts"]
                      if c["name"].endswith("agendar_cita_dialog_context"))
    assert parametros["cedula"] == "14523987"
    assert "especialidad" in res["fulfillmentText"]


def test_cedula_en_palabras_invalida_se_vuelve_a_pedir(cliente):
    _pedir_cedula(cliente)
    res = cliente.post("/webhook", json=peticion("agendar_cita", SIN_CEDULA, "mil doscientos",
                                                 todos=False, esperando="cedula")).json()
    assert "entre 6 y 8 cifras" in res["fulfillmentText"]
