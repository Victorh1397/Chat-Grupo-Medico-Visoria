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

from webhook.dialogflow import PeticionDF, texto
from webhook.documentos import DOCUMENTOS, MODELO
from webhook.intenciones import MANEJADORES, agenda

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

    manejador = MANEJADORES.get(pet.intencion)
    try:
        respuesta = manejador(pet) if manejador else texto(
            "Disculpe, todavía no sé gestionar esa petición. ¿Le puedo ayudar en otra cosa?")
    except Exception:
        # Nunca dejar al usuario en silencio: Dialogflow leería una respuesta vacía
        log.exception("Error en la intención %s", pet.intencion)
        respuesta = texto("Disculpe, tuve un problema técnico. ¿Desea que le comunique con recepción?")

    ms = (time.perf_counter() - inicio) * 1000
    parametros = {k: v for k, v in pet.parametros.items() if v and not k.endswith(".original")}
    log.info("-" * 60)
    log.info("INTENCIÓN: %s | esperando: %s | %.0f ms", pet.intencion, pet.esperando() or "-", ms)
    log.info("TEXTO: %s", pet.texto)
    log.info("PARÁMETROS: %s", parametros)
    log.info("RESPUESTA: %s", respuesta.get("fulfillmentText")
             or respuesta.get("followupEventInput") or "(pregunta de Dialogflow)")
    return respuesta
