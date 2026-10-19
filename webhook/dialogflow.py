"""
Lectura de la petición de Dialogflow ES y construcción de respuestas.

Formato mínimo de respuesta: {"fulfillmentText": "..."}.
Durante la recogida de datos (slot filling), devolver {} deja que Dialogflow haga su propia pregunta.
"""

from dataclasses import dataclass
from datetime import date, datetime, time

# Contextos que Dialogflow crea durante la recogida de datos de una intención
SUFIJO_RECOGIDA = "_dialog_context"
PREFIJO_ESPERANDO = "_dialog_params_"


@dataclass
class PeticionDF:
    cuerpo: dict

    @property
    def _resultado(self) -> dict:
        return self.cuerpo.get("queryResult", {})

    @property
    def intencion(self) -> str:
        return self._resultado.get("intent", {}).get("displayName", "")

    @property
    def intencion_id(self) -> str:
        """'projects/p/agent/intents/<id>' -> '<id>'."""
        return self._resultado.get("intent", {}).get("name", "").rsplit("/", 1)[-1]

    @property
    def sesion(self) -> str:
        return self.cuerpo.get("session", "")

    @property
    def texto(self) -> str:
        return self._resultado.get("queryText", "")

    @property
    def parametros(self) -> dict:
        return self._resultado.get("parameters", {}) or {}

    def parametro(self, nombre: str) -> str:
        """Valor como texto; si Dialogflow manda una lista, el primer elemento."""
        valor = self.parametros.get(nombre, "")
        if isinstance(valor, list):
            valor = valor[0] if valor else ""
        return valor if isinstance(valor, str) else ""

    @property
    def todos_los_datos(self) -> bool:
        return bool(self._resultado.get("allRequiredParamsPresent", False))

    @property
    def contextos(self) -> list[dict]:
        return self._resultado.get("outputContexts", []) or []

    @staticmethod
    def nombre_corto(contexto: dict) -> str:
        return contexto.get("name", "").rsplit("/", 1)[-1]

    def esperando(self) -> str:
        """Parámetro que Dialogflow está preguntando ahora mismo ('' si ninguno)."""
        for c in self.contextos:
            nombre = self.nombre_corto(c)
            if PREFIJO_ESPERANDO in nombre and c.get("lifespanCount", 0) > 0:
                return nombre.split(PREFIJO_ESPERANDO, 1)[1]
        return ""


# Valores de sistema

def leer_fecha(valor: str) -> date | None:
    """'2026-10-20T12:00:00-04:00' -> date(2026, 10, 20)."""
    try:
        return datetime.fromisoformat(valor).date()
    except (TypeError, ValueError):
        return None


def leer_hora(valor: str) -> time | None:
    """Dialogflow pega la hora a la fecha de hoy: '2026-10-19T10:00:00-04:00' -> time(10, 0)."""
    try:
        return datetime.fromisoformat(valor).time().replace(tzinfo=None)
    except (TypeError, ValueError):
        return None


# Respuestas

def texto(mensaje: str) -> dict:
    return {"fulfillmentText": mensaje}


def evento(nombre: str) -> dict:
    """Activa la intención que tenga este evento, como si el usuario la hubiera pedido."""
    return {"followupEventInput": {"name": nombre, "languageCode": "es"}}


def repreguntar(pet: PeticionDF, parametro: str, mensaje: str, cambios: dict | None = None) -> dict:
    """
    Vuelve a abrir la recogida de datos preguntando `parametro`, que queda vacío.

    `cambios` permite además fijar o vaciar otros parámetros (p. ej. nacionalidad='E' cuando
    Dialogflow no reconoció el gentilicio). Se reescriben los contextos de recogida que
    Dialogflow mandó en la petición y se activa el que indica qué dato se espera.
    Si la recogida ya había terminado (turno final), se cierran los contextos de confirmación
    para que no pueda confirmarse una cita con datos inválidos.
    """
    valores = {**pet.parametros, **(cambios or {}), parametro: ""}
    for nombre in [*(cambios or {}), parametro]:
        valores[f"{nombre}.original"] = valores[nombre]

    base = f"{pet.sesion}/contexts/"
    esperado = f"{pet.intencion}{PREFIJO_ESPERANDO}{parametro}"
    salida = [
        {"name": base + f"{pet.intencion_id}_id{SUFIJO_RECOGIDA}", "lifespanCount": 2, "parameters": valores},
        {"name": base + f"{pet.intencion}{SUFIJO_RECOGIDA}", "lifespanCount": 2, "parameters": valores},
        {"name": base + esperado, "lifespanCount": 1, "parameters": valores},
    ]
    for c in pet.contextos:
        nombre = pet.nombre_corto(c)
        if PREFIJO_ESPERANDO in nombre and nombre != esperado:
            salida.append({"name": c["name"], "lifespanCount": 0})
    if pet.todos_los_datos:
        for nombre in ("ctx_cita_en_curso", f"{pet.intencion}-followup"):
            salida.append({"name": base + nombre, "lifespanCount": 0})

    return {"fulfillmentText": mensaje, "outputContexts": salida}
