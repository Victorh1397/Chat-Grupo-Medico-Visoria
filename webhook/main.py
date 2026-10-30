"""
Webhook de Dialogflow ES en FastAPI para Vicky, la asistente de Grupo Médico Visoria.

Arrancar (desde la raíz del repositorio):
    uv run uvicorn webhook.main:app --reload --port 8000

Después, en otra terminal: ngrok http 8000. En Fulfillment, la URL del dominio de ngrok
+ /webhook y la cabecera X-Visoria-Token (ver specs/03-webhook-fastapi/plan.md).
"""

import logging
import os
import secrets
import time

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request

from webhook import intenciones, telegram, transferencia
from webhook.dialogflow import PeticionDF, texto
from webhook.documentos import DOCUMENTOS, MODELO
from webhook.intenciones import FALLBACK, MANEJADORES, PREGUNTAS, agenda
from webhook.ssml import a_ssml

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("visoria")

app = FastAPI(title="Webhook Grupo Médico Visoria")


def comprobar_token(token: str | None) -> None:
    """La URL del túnel es pública: solo Dialogflow conoce este token (cabecera de Fulfillment)."""
    esperado = os.environ.get("WEBHOOK_TOKEN", "")
    if not esperado or not token or not secrets.compare_digest(token, esperado):
        raise HTTPException(status_code=401, detail="Token no válido")


@app.get("/")
def estado():
    """Para comprobar de un vistazo que el túnel llega hasta aquí."""
    return {"estado": "ok", "servicio": "Vicky - Grupo Médico Visoria", "citas_en_agenda": len(agenda.citas),
            "documentos_cargados": len(DOCUMENTOS), "modelo": MODELO}


@app.post("/webhook")
async def webhook(request: Request, x_visoria_token: str | None = Header(default=None)):
    comprobar_token(x_visoria_token)
    inicio = time.perf_counter()
    pet = PeticionDF(await request.json())

    # Spec 07: un "sí"/"no" a la oferta de recepción del turno anterior llega como fallback
    oferta = transferencia.tomar_oferta(pet.sesion)
    if pet.intencion != FALLBACK:
        transferencia.sin_entender.pop(pet.sesion, None)
    respuesta_oferta = (transferencia.responder_a_oferta(pet.texto, oferta, pet.sesion, pet.canal)
                        if oferta and pet.intencion == FALLBACK else None)

    manejador = MANEJADORES.get(pet.intencion)
    try:
        if respuesta_oferta:
            respuesta = texto(respuesta_oferta)
        else:
            respuesta = manejador(pet) if manejador else texto(
                "Disculpe, todavía no sé gestionar esa petición. ¿Le puedo ayudar en otra cosa?")
    except Exception:
        # Nunca dejar al usuario en silencio: Dialogflow leería una respuesta vacía
        log.exception("Error en la intención %s", pet.intencion)
        respuesta = texto("Disculpe, tuve un problema técnico. ¿Desea que le comunique con recepción?")

    # Si Vicky ofreció recepción, la oferta vale para el turno siguiente (antes de pasar a SSML)
    transferencia.ofrecer_si_procede(pet.sesion, respuesta.get("fulfillmentText", ""), pet.texto)

    # Telegram (spec 08): Dialogflow formula sus propias preguntas de recogida de datos y a esas no se les pueden
    # añadir botones; para especialidad y nacionalidad las formula el webhook. Después se añaden los botones.
    if pet.canal == "telegram":
        if not respuesta and pet.esperando() in ("especialidad", "nacionalidad"):
            pregunta = (telegram.PREGUNTA_ESPECIALIDAD_HORARIOS if pet.intencion == "consultar_horarios"
                        else PREGUNTAS[pet.esperando()])
            respuesta = texto(pregunta)
        respuesta = telegram.con_botones(respuesta)

    # Spec 09: mientras hay una cita en marcha, contexto propio para que `corregir_dato` solo coincida entonces.
    # Va después del bloque de Telegram porque ese distingue una respuesta vacía (pregunta de Dialogflow).
    if pet.intencion == "agendar_cita":
        respuesta = intenciones.marcar_cita_en_curso(pet, respuesta)

    # SSML solo en el canal de voz: en el simulador o en Telegram las etiquetas se verían como texto
    if pet.canal == "voz" and respuesta.get("fulfillmentText"):
        respuesta["fulfillmentText"] = a_ssml(respuesta["fulfillmentText"])

    ms = (time.perf_counter() - inicio) * 1000
    parametros = {k: v for k, v in pet.parametros.items() if v and not k.endswith(".original")}
    log.info("-" * 60)
    log.info("INTENCIÓN: %s | canal: %s | esperando: %s | %.0f ms", pet.intencion, pet.canal or "texto",
             pet.esperando() or "-", ms)
    log.info("TEXTO: %s", pet.texto)
    log.info("PARÁMETROS: %s", parametros)
    botones = next((m["quickReplies"] for m in respuesta.get("fulfillmentMessages", []) if "quickReplies" in m), None)
    con_botones = botones and f"{botones['title']} {botones['quickReplies']}"
    log.info("RESPUESTA: %s", respuesta.get("fulfillmentText") or con_botones
             or respuesta.get("followupEventInput") or "(pregunta de Dialogflow)")
    return respuesta
