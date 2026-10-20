"""Vicky en Telegram (spec 08): canal, botones y preguntas con botones, con la forma real de la integración."""

import pytest

from tests.conftest import datos_cita, peticion
from webhook import telegram
from webhook.datos import ESPECIALIDADES
from webhook.dialogflow import PeticionDF
from webhook.intenciones import BIENVENIDA


def desde_telegram(cuerpo: dict, texto: str = "") -> dict:
    datos = {"text": texto, "from": {"id": 1}, "chat": {"id": 1}, "date": 0, "message_id": 1}
    return {**cuerpo, "originalDetectIntentRequest": {"source": "telegram", "payload": {"data": datos}}}


def enviar(cliente, intencion: str, texto: str, parametros: dict | None = None, **kwargs) -> dict:
    cuerpo = desde_telegram(peticion(intencion, parametros or {}, texto, **kwargs), texto)
    return cliente.post("/webhook", json=cuerpo).json()


def botones(respuesta: dict) -> tuple[str, list[str]]:
    [mensaje] = respuesta["fulfillmentMessages"]
    assert mensaje["platform"] == "TELEGRAM" and "fulfillmentText" not in respuesta
    return mensaje["quickReplies"]["title"], mensaje["quickReplies"]["quickReplies"]


# R2: canal

def test_canal_telegram():
    assert PeticionDF(desde_telegram(peticion("x"))).canal == "telegram"
    assert PeticionDF(peticion("x")).canal == ""


# R3: botones

def test_ca1_bienvenida_con_menu(cliente):
    assert botones(enviar(cliente, "Default Welcome Intent", "hola")) == (BIENVENIDA, telegram.MENU)


def test_nacionalidad_con_botones_formulada_por_el_webhook(cliente):
    parametros = {"nombre": "María", "apellido": "González", "nacionalidad": "", "cedula": "", "especialidad": "",
                  "fecha": "", "hora": ""}
    respuesta = enviar(cliente, "agendar_cita", "María González", parametros, todos=False, esperando="nacionalidad")
    assert botones(respuesta) == ("¿Usted es venezolano o extranjero?", ["Venezolano", "Extranjero"])
    assert "outputContexts" not in respuesta  # Dialogflow sigue esperando la nacionalidad


def test_especialidad_con_botones_al_agendar(cliente):
    parametros = {**datos_cita(especialidad="", fecha="", hora="")}
    titulo, opciones = botones(enviar(cliente, "agendar_cita", "14523987", parametros, todos=False,
                                      esperando="especialidad"))
    assert titulo.startswith("¿Con qué especialidad desea la cita?") and opciones == ESPECIALIDADES


def test_especialidad_con_botones_al_consultar_horarios(cliente):
    respuesta = enviar(cliente, "consultar_horarios", "horarios de los médicos", {"especialidad": ""},
                       todos=False, esperando="especialidad")
    assert botones(respuesta) == (telegram.PREGUNTA_ESPECIALIDAD_HORARIOS, ESPECIALIDADES)


def test_horarios_sin_especialidad_fuera_de_telegram_deja_preguntar_a_dialogflow(cliente):
    cuerpo = peticion("consultar_horarios", {"especialidad": ""}, "horarios", todos=False, esperando="especialidad")
    assert cliente.post("/webhook", json=cuerpo).json() == {}


def test_otros_datos_no_llevan_botones(cliente):
    parametros = datos_cita(cedula="", especialidad="", fecha="", hora="")
    assert enviar(cliente, "agendar_cita", "venezolana", parametros, todos=False, esperando="cedula") == {}


@pytest.mark.parametrize("intencion, texto, parametros", [
    ("agendar_cita", "a las 10", datos_cita()),                       # ¿Confirmo la cita…?
    ("agendar_cita - no", "no", {}),                                  # ¿Desea empezar de nuevo?
    ("consulta_documental", "¿hacen resonancias?", {}),               # oferta de recepción
])
def test_si_no(cliente, intencion, texto, parametros):
    titulo, opciones = botones(enviar(cliente, intencion, texto, parametros))
    assert opciones == ["Sí", "No"] and titulo.endswith("?")


def test_respuestas_sin_pregunta_no_llevan_botones(cliente):
    respuesta = enviar(cliente, "consultar_horarios", "cardiología", {"especialidad": "Cardiología"})
    assert respuesta["fulfillmentText"].startswith("En cardiología atienden") and "fulfillmentMessages" not in respuesta


def test_preguntas_frecuentes(cliente, modelo):
    titulo = enviar(cliente, "Default Fallback Intent", "Preguntas frecuentes")["fulfillmentText"]
    assert titulo.startswith("Con gusto. Puede preguntarme") and modelo.prompts == []


# La oferta de recepción se registra antes de convertir la respuesta en botones (spec 07)

def test_oferta_con_botones_y_si_crea_el_caso(cliente):
    enviar(cliente, "consulta_documental", "¿hacen resonancias?")
    respuesta = enviar(cliente, "Default Fallback Intent", "Sí")
    assert "caso VIS-" in respuesta["fulfillmentText"]


# CA-6: los demás canales no llevan botones

def test_otros_canales_sin_botones(cliente):
    respuesta = cliente.post("/webhook", json=peticion("Default Welcome Intent", {}, "hola")).json()
    assert respuesta == {"fulfillmentText": BIENVENIDA}
    voz = {**peticion("agendar_cita - no", {}, "no"), "originalDetectIntentRequest": {"payload": {"canal": "voz"}}}
    assert cliente.post("/webhook", json=voz).json()["fulfillmentText"].startswith("<speak>")
