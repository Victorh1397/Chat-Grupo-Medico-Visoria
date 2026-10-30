"""SSML solo en el canal de voz (spec 06, R3 y CA-4)."""

from tests.conftest import DEJA_A_DIALOGFLOW, datos_cita, peticion
from webhook.ssml import a_ssml, sin_etiquetas


def test_envuelto_en_speak_y_pausas_entre_frases():
    assert a_ssml("Listo, María. ¿Le puedo ayudar en algo más?") == (
        '<speak>Listo, María.<break time="250ms"/>¿Le puedo ayudar en algo más?</speak>')


def test_codigos_caracter_a_caracter():
    ssml = a_ssml("Su cita CIT-48213 está confirmada.")
    assert ('<say-as interpret-as="characters">CIT</say-as>, '
            '<say-as interpret-as="characters">48213</say-as>') in ssml
    assert '<say-as interpret-as="characters">VIS</say-as>' in a_ssml("Su caso es VIS-12345.")


def test_cedula_por_grupos_de_miles():
    ssml = a_ssml("No encuentro ningún paciente con la cédula 14523987.")
    assert '14<break time="150ms"/>523<break time="150ms"/>987' in ssml
    assert '945<break time="150ms"/>123' in a_ssml("Cédula 945123.")


def test_no_toca_horas_precios_ni_anios():
    ssml = a_ssml("El martes 20 de octubre a las 10:00. Cuesta 40 dólares. Desde el 12 de marzo de 2026.")
    assert "10:00" in ssml and "40 dólares" in ssml and "2026" in ssml
    assert "say-as" not in ssml


def test_caracteres_especiales_escapados():
    assert "Salud &amp; Vida" in a_ssml("Salud & Vida")
    assert "&lt;" in a_ssml("menor <5 años")


def test_sin_etiquetas_para_mostrar_en_pantalla():
    texto = "Su cita CIT-48213 está confirmada. Cédula 14523987 & más."
    assert sin_etiquetas(a_ssml(texto)) == "Su cita CIT-48213 está confirmada. Cédula 14 523 987 & más."


# Canal: el webhook solo usa SSML si la petición viene del cliente de voz

def con_canal(cuerpo: dict, canal: str) -> dict:
    return {**cuerpo, "originalDetectIntentRequest": {"source": "DIALOGFLOW_CONSOLE", "payload": {"canal": canal}}}


def test_canal_voz_recibe_ssml(cliente):
    cuerpo = con_canal(peticion("transferir_humano", {}, "quiero hablar con una persona"), "voz")
    texto = cliente.post("/webhook", json=cuerpo).json()["fulfillmentText"]
    assert texto.startswith("<speak>") and '<say-as interpret-as="characters">VIS</say-as>' in texto


def test_canal_texto_sin_ssml(cliente):
    for cuerpo in [peticion("transferir_humano", {}, "quiero hablar con una persona"),
                   con_canal(peticion("transferir_humano"), "telegram")]:
        texto = cliente.post("/webhook", json=cuerpo).json()["fulfillmentText"]
        assert "<" not in texto and "caso VIS-" in texto


def test_repreguntar_por_voz_tambien_en_ssml(cliente):
    params = datos_cita(cedula="1234", especialidad="", fecha="", hora="")
    cuerpo = con_canal(peticion("agendar_cita", params, "1234", todos=False, esperando="cedula"), "voz")
    respuesta = cliente.post("/webhook", json=cuerpo).json()
    assert respuesta["fulfillmentText"].startswith("<speak>")
    assert respuesta["outputContexts"]  # los contextos de recogida se conservan


def test_respuesta_vacia_de_slot_filling_no_cambia(cliente):
    params = datos_cita(especialidad="", fecha="", hora="")
    cuerpo = con_canal(peticion("agendar_cita", params, "14523987", todos=False, esperando="cedula"), "voz")
    assert cliente.post("/webhook", json=cuerpo).json() == DEJA_A_DIALOGFLOW
