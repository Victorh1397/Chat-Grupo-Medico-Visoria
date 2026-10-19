"""Utilidades comunes de los tests: fecha fija, estado limpio y peticiones de ejemplo de Dialogflow."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from webhook import agenda as modulo_agenda
from webhook.agenda import CARACAS

# "Hoy" en los tests: domingo 18 de octubre de 2026, 10:00 en Caracas.
# El próximo martes es el 20/10 y la cita sembrada de Miguel Torres queda el 20/10 a las 15:00.
AHORA = datetime(2026, 10, 18, 10, 0, tzinfo=CARACAS)
TOKEN = "token-de-prueba"
SESION = "projects/visoria-chat-1397/agent/sessions/prueba"
INTENT_ID = "e12a9d5b-1eb2-41a0-877f-05cfa9b6a5a2"


class ModeloSimulado:
    """Sustituye a Gemini en los tests: sin red ni cuota. Registra los prompts y devuelve `respuesta`."""

    def __init__(self):
        self.respuesta = "NO_DISPONIBLE"
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if isinstance(self.respuesta, Exception):
            raise self.respuesta
        return self.respuesta


@pytest.fixture(autouse=True)
def modelo(monkeypatch):
    from webhook import documentos

    simulado = ModeloSimulado()
    monkeypatch.setattr(documentos, "preguntar_al_modelo", simulado)
    return simulado


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    monkeypatch.setattr(modulo_agenda, "ahora", lambda: AHORA)
    monkeypatch.setenv("WEBHOOK_TOKEN", TOKEN)
    from webhook.intenciones import agenda, pregunta_anterior

    agenda.reiniciar()
    pregunta_anterior.clear()
    yield agenda


@pytest.fixture
def cliente():
    from webhook.main import app

    return TestClient(app, headers={"X-Visoria-Token": TOKEN})


def peticion(intencion: str, parametros: dict | None = None, texto: str = "", todos: bool = True,
             esperando: str = "", sesion: str = SESION) -> dict:
    """Petición de Dialogflow ES como la que llega al webhook."""
    contextos = []
    if esperando:
        base = f"{sesion}/contexts/"
        valores = parametros or {}
        contextos = [
            {"name": base + f"{INTENT_ID}_id_dialog_context", "lifespanCount": 2, "parameters": valores},
            {"name": base + f"{intencion}_dialog_context", "lifespanCount": 2, "parameters": valores},
            {"name": base + f"{intencion}_dialog_params_{esperando}", "lifespanCount": 1, "parameters": valores},
        ]
    return {
        "responseId": "prueba",
        "session": sesion,
        "queryResult": {
            "queryText": texto,
            "parameters": parametros or {},
            "allRequiredParamsPresent": todos,
            "outputContexts": contextos,
            "intent": {"name": f"projects/visoria-chat-1397/agent/intents/{INTENT_ID}", "displayName": intencion},
            "languageCode": "es",
        },
    }


def datos_cita(**cambios) -> dict:
    """Los 7 datos de la conversación modelo (spec 01), como los manda Dialogflow."""
    base = {
        "nombre": "María",
        "apellido": "González",
        "nacionalidad": "V",
        "cedula": "14.523.987",
        "especialidad": "Dermatología",
        "fecha": "2026-10-20T12:00:00-04:00",
        "hora": "2026-10-18T10:00:00-04:00",
    }
    return {**base, **cambios}
