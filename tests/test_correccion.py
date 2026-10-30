"""Spec 09: interrupciones y corrección de datos en la cita."""

from tests.conftest import INTENT_ID, datos_cita, peticion
from webhook.intenciones import PREGUNTAS


def nombres(respuesta: dict) -> dict:
    return {c["name"].rsplit("/", 1)[-1]: c for c in respuesta.get("outputContexts", [])}


def test_ca5_pregunta_a_mitad_de_la_cita_se_responde_y_se_retoma(cliente, modelo):
    parametros = datos_cita(especialidad="", fecha="", hora="")
    cliente.post("/webhook", json=peticion("agendar_cita", parametros, "14523987", todos=False,
                                           esperando="especialidad"))

    modelo.respuesta = "Sí, hay estacionamiento propio."
    res = cliente.post("/webhook", json=peticion("consulta_documental", {}, "¿Tienen estacionamiento?")).json()

    assert res["fulfillmentText"] == f"Sí, hay estacionamiento propio. {PREGUNTAS['especialidad']}"
    contextos = nombres(res)
    assert set(contextos) >= {"agendar_cita_dialog_params_especialidad", "agendar_cita_dialog_context",
                              f"{INTENT_ID}_id_dialog_context"}
    assert contextos["agendar_cita_dialog_context"]["parameters"]["cedula"] == "14.523.987"


def test_sin_cita_a_medias_la_pregunta_no_retoma_nada(cliente, modelo):
    modelo.respuesta = "Sí, hay estacionamiento propio."
    res = cliente.post("/webhook", json=peticion("consulta_documental", {}, "¿Tienen estacionamiento?")).json()
    assert res == {"fulfillmentText": "Sí, hay estacionamiento propio."}
