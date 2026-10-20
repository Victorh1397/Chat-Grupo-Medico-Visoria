"""
Botones para Telegram (spec 08).

Telegram se conecta con la integración nativa de Dialogflow ES. Los botones son respuestas rápidas
("quickReplies"): aparecen sobre el teclado, al pulsarlos se envía su texto como un mensaje normal y
desaparecen tras usarlos (verificado en la spec 08, T1). Son solo una ayuda: el usuario puede escribir lo que quiera.
"""

from webhook.datos import ESPECIALIDADES
from webhook.transferencia import OFERTA

MENU = ["Agendar una cita", "Horarios de los médicos", "Preguntas frecuentes", "Hablar con recepción"]
SI_NO = ["Sí", "No"]
NACIONALIDADES = ["Venezolano", "Extranjero"]

PREGUNTA_ESPECIALIDAD_HORARIOS = "¿De qué especialidad desea conocer el horario?"


def botones_para(texto: str) -> list[str]:
    """Botones que corresponden a una respuesta de Vicky, según lo que pregunta (lista vacía si ninguno)."""
    if texto.startswith("Bienvenido a Grupo Médico Visoria"):
        return MENU
    if "¿Con qué especialidad desea la cita?" in texto or PREGUNTA_ESPECIALIDAD_HORARIOS in texto:
        return ESPECIALIDADES
    if "¿Usted es venezolano o extranjero?" in texto:
        return NACIONALIDADES
    if texto.endswith("?") and any(p in texto for p in ("¿Confirmo la cita", "¿Desea empezar de nuevo?", OFERTA)):
        return SI_NO
    return []


def con_botones(respuesta: dict) -> dict:
    """Si la respuesta admite botones, la convierte en un mensaje de respuestas rápidas para Telegram."""
    texto = respuesta.get("fulfillmentText", "")
    botones = botones_para(texto)
    if not botones:
        return respuesta
    con = {k: v for k, v in respuesta.items() if k != "fulfillmentText"}
    con["fulfillmentMessages"] = [{"platform": "TELEGRAM", "quickReplies": {"title": texto, "quickReplies": botones}}]
    return con
