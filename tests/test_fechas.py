"""Lectura de fechas de respaldo (spec 08, T7). "Hoy" es el domingo 18/10/2026."""

from datetime import date

import pytest

from tests.conftest import DEJA_A_DIALOGFLOW, peticion
from webhook.fechas import como_dialogflow, leer_fecha_texto

HOY = date(2026, 10, 18)


@pytest.mark.parametrize("texto, fecha", [
    ("Para el 29 de octubre", date(2026, 10, 29)),
    ("el 29 de octubre", date(2026, 10, 29)),
    ("para el primero de diciembre", date(2026, 12, 1)),
    ("5 de enero", date(2027, 1, 5)),              # ya pasó este año: el próximo
    ("el 3 de noviembre de 2026", date(2026, 11, 3)),
    ("29/10", date(2026, 10, 29)),
    ("29/10/2026", date(2026, 10, 29)),
    ("2/11/26", date(2026, 11, 2)),
    ("mañana", date(2026, 10, 19)),
    ("pasado mañana", date(2026, 10, 20)),
    ("para hoy", date(2026, 10, 18)),
    ("el martes", date(2026, 10, 20)),
    ("para el próximo jueves", date(2026, 10, 22)),
    ("el domingo", date(2026, 10, 25)),            # hoy es domingo: el siguiente
    ("el sábado", date(2026, 10, 24)),
])
def test_leer_fecha(texto, fecha):
    assert leer_fecha_texto(texto, HOY) == fecha


@pytest.mark.parametrize("texto", ["a las 10 de la mañana", "no sé", "31 de febrero", "45/13", "cuando pueda"])
def test_sin_fecha(texto):
    assert leer_fecha_texto(texto, HOY) is None


def test_formato_de_dialogflow():
    assert como_dialogflow(date(2026, 10, 29)) == "2026-10-29T12:00:00-04:00"


SIN_FECHA = {"nombre": "Jairo", "apellido": "Restrepo", "nacionalidad": "E", "cedula": "12123456",
             "especialidad": "Dermatología", "fecha": "", "hora": ""}


def _parametros_devueltos(respuesta):
    return next(c["parameters"] for c in respuesta["outputContexts"]
                if c["name"].endswith("agendar_cita_dialog_context"))


def test_fecha_no_reconocida_por_dialogflow_se_lee_del_texto(cliente):
    cliente.post("/webhook", json=peticion("agendar_cita", SIN_FECHA, "Dermatología", todos=False, esperando="fecha"))
    respuesta = cliente.post("/webhook", json=peticion("agendar_cita", SIN_FECHA, "Para el 29 de octubre",
                                                       todos=False, esperando="fecha")).json()
    assert _parametros_devueltos(respuesta)["fecha"] == "2026-10-29T12:00:00-04:00"
    assert respuesta["fulfillmentText"] == ("Ese día atiende la doctora Laura Rojas de 8:00 a 12:00; el primer "
                                            "horario libre es a las 8:00. ¿A qué hora le conviene?")
    assert any(c["name"].endswith("_dialog_params_hora") and c["lifespanCount"] == 1
               for c in respuesta["outputContexts"])


def test_fecha_leida_que_no_vale_se_rechaza(cliente):
    cliente.post("/webhook", json=peticion("agendar_cita", SIN_FECHA, "Dermatología", todos=False, esperando="fecha"))
    respuesta = cliente.post("/webhook", json=peticion("agendar_cita", SIN_FECHA, "para el 25 de octubre",
                                                       todos=False, esperando="fecha")).json()  # domingo
    assert "Los domingos la clínica está cerrada" in respuesta["fulfillmentText"]


def test_sin_fecha_reconocible_dialogflow_vuelve_a_preguntar(cliente):
    cliente.post("/webhook", json=peticion("agendar_cita", SIN_FECHA, "Dermatología", todos=False, esperando="fecha"))
    assert cliente.post("/webhook", json=peticion("agendar_cita", SIN_FECHA, "cuando pueda",
                                                  todos=False, esperando="fecha")).json() == DEJA_A_DIALOGFLOW
