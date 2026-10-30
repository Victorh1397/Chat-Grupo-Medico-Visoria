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


def test_ca6_pregunta_sin_respuesta_a_mitad_de_la_cita_retoma_sin_ofrecer_recepcion(cliente):
    parametros = datos_cita(especialidad="", fecha="", hora="")
    cliente.post("/webhook", json=peticion("agendar_cita", parametros, "14523987", todos=False,
                                           esperando="especialidad"))

    res = cliente.post("/webhook", json=peticion("consulta_documental", {}, "¿Hacen resonancias?")).json()

    sin_info = "No tengo esa información en los documentos de la clínica."
    assert res["fulfillmentText"] == f"{sin_info} {PREGUNTAS['especialidad']}"


def corregir(cliente, dato, texto):
    return cliente.post("/webhook", json=peticion("corregir_dato", {"dato_cita": dato}, texto)).json()


def proponer(cliente):
    """Los siete datos válidos: el webhook deja una propuesta pendiente de confirmar."""
    cliente.post("/webhook", json=peticion("agendar_cita", datos_cita(), "a las 10"))


def test_ca1_corregir_un_dato_pide_solo_ese_y_conserva_los_demas(cliente):
    parametros = datos_cita(especialidad="", fecha="", hora="")
    cliente.post("/webhook", json=peticion("agendar_cita", parametros, "14523987", todos=False,
                                           esperando="especialidad"))

    res = corregir(cliente, "cedula", "me equivoqué con la cédula")

    assert res["fulfillmentText"] == f"De acuerdo. {PREGUNTAS['cedula']}"
    contexto = nombres(res)["agendar_cita_dialog_params_cedula"]
    assert contexto["parameters"]["cedula"] == ""
    assert contexto["parameters"]["nombre"] == "María"


def test_ca3_corregir_ante_la_propuesta_la_descarta_y_pide_el_dato(cliente):
    proponer(cliente)

    res = corregir(cliente, "fecha", "no, la fecha es otra")

    assert res["fulfillmentText"] == f"De acuerdo. {PREGUNTAS['fecha']}"
    assert nombres(res)["ctx_cita_en_curso"]["lifespanCount"] == 0  # ya no se puede confirmar
    sin_cita = cliente.post("/webhook", json=peticion("agendar_cita - yes")).json()
    assert "No tengo ninguna cita pendiente" in sin_cita["fulfillmentText"]


def test_r1_3_el_valor_nuevo_en_la_misma_frase_no_se_vuelve_a_preguntar(cliente):
    proponer(cliente)

    res = corregir(cliente, "cedula", "la cédula es 11222333")

    assert res["followupEventInput"]["name"] == "INICIAR_CITA"
    assert res["followupEventInput"]["parameters"]["cedula"] == "11222333"
    assert res["followupEventInput"]["parameters"]["nombre"] == "María"


def test_corregir_sin_cita_en_marcha(cliente):
    res = corregir(cliente, "cedula", "me equivoqué con la cédula")
    assert "No tengo ninguna cita en curso" in res["fulfillmentText"]


def test_sin_cita_a_medias_la_pregunta_no_retoma_nada(cliente, modelo):
    modelo.respuesta = "Sí, hay estacionamiento propio."
    res = cliente.post("/webhook", json=peticion("consulta_documental", {}, "¿Tienen estacionamiento?")).json()
    assert res == {"fulfillmentText": "Sí, hay estacionamiento propio."}
