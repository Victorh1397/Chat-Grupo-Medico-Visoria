"""
Transferencia a recepción (spec 07). La transferencia es simulada: se registra un caso con el resumen
de la conversación en logs/transferencias.jsonl (la "cola" de recepción) y se informa al usuario.

Vicky ofrece recepción en varias respuestas ("¿Desea que le comunique con recepción?"). Un "sí" o "no"
suelto llega al fallback de Dialogflow; el webhook recuerda la oferta de cada sesión durante un turno
para interpretarlo, sin intenciones nuevas en la consola.
"""

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from webhook import agenda as modulo_agenda
from webhook import textos
from webhook.agenda import codigo_caso
from webhook.datos import HORARIO_CLINICA
from webhook.dialogflow import leer_fecha

log = logging.getLogger("visoria")

REGISTRO = Path(__file__).resolve().parents[1] / "logs" / "transferencias.jsonl"

OFERTA = "¿Desea que le comunique con recepción?"
OFERTA_NO_ENTENDIDO = f"Parece que no le estoy entendiendo bien. {OFERTA}"
RECHAZO = "De acuerdo. ¿Le puedo ayudar en algo más?"
TURNOS_SIN_ENTENDER = 2

AFIRMATIVO = re.compile(
    r"^(?:s[ií]|claro|por favor|de acuerdo|ok(?:ay)?|vale|est[aá] bien|perfecto|bueno|dale)"
    r"(?:[\s,]+(?:s[ií]|por favor|claro|gracias|de acuerdo))*[.!]*$",
    re.IGNORECASE,
)
NEGATIVO = re.compile(r"^(?:no|mejor no|ahora no|no hace falta|no por ahora)(?:[\s,]+gracias)?[.!]*$", re.IGNORECASE)


@dataclass
class Oferta:
    motivo: str
    pregunta: str


@dataclass
class Caso:
    numero: str
    fecha: str
    canal: str
    motivo: str
    pregunta: str
    datos_de_cita: dict = field(default_factory=dict)


# Estado por sesión (en memoria, como las propuestas de cita de la spec 03)
ofertas: dict[str, Oferta] = {}
sin_entender: dict[str, int] = {}
datos_de_cita: dict[str, dict] = {}


def reiniciar() -> None:
    ofertas.clear()
    sin_entender.clear()
    datos_de_cita.clear()


# Oferta

def motivo_de(respuesta: str) -> str:
    """Motivo de la transferencia según el texto con el que Vicky ofreció recepción."""
    if respuesta.startswith("Parece que no le estoy entendiendo"):
        return "no_entendido"
    if "no puedo consultar" in respuesta or "problema técnico" in respuesta:
        return "error_tecnico"
    return "informacion_no_disponible"


def ofrecer_si_procede(sesion: str, respuesta: str, pregunta: str) -> None:
    """Si la respuesta de Vicky termina ofreciendo recepción, la oferta vale para el turno siguiente."""
    if respuesta.endswith(OFERTA):
        ofertas[sesion] = Oferta(motivo_de(respuesta), pregunta)


def tomar_oferta(sesion: str) -> Oferta | None:
    """La oferta pendiente de la sesión, que caduca al tomarla (solo vale un turno)."""
    return ofertas.pop(sesion, None)


def responder_a_oferta(texto_usuario: str, oferta: Oferta, sesion: str, canal: str) -> str | None:
    """Texto de Vicky si el usuario aceptó o rechazó la oferta; None si dijo otra cosa."""
    texto_usuario = texto_usuario.strip()
    if AFIRMATIVO.match(texto_usuario):
        return mensaje(crear_caso(sesion, canal, oferta.motivo, oferta.pregunta))
    if NEGATIVO.match(texto_usuario):
        return RECHAZO
    return None


# Datos de la cita dados en la conversación (para el resumen del caso)

def recordar_cita(sesion: str, parametros: dict) -> None:
    actuales = datos_de_cita.setdefault(sesion, {})
    actuales.update({k: v for k, v in parametros.items() if v})


def olvidar_cita(sesion: str) -> None:
    datos_de_cita.pop(sesion, None)


def _resumen_cita(sesion: str) -> dict:
    datos = dict(datos_de_cita.get(sesion, {}))
    if "cedula" in datos:
        cifras = re.sub(r"\D", "", datos["cedula"])
        datos["cedula"] = f"***{cifras[-3:]}"  # el caso lo lee personal de recepción
    if "fecha" in datos:
        dia = leer_fecha(datos["fecha"])
        datos["fecha"] = dia.strftime("%d/%m/%Y") if dia else datos["fecha"]
    return datos


# Caso

def crear_caso(sesion: str, canal: str, motivo: str, pregunta: str) -> Caso:
    caso = Caso(codigo_caso(), modulo_agenda.ahora().isoformat(timespec="seconds"), canal or "texto", motivo,
                pregunta, _resumen_cita(sesion))
    REGISTRO.parent.mkdir(parents=True, exist_ok=True)
    with REGISTRO.open("a", encoding="utf-8") as registro:
        registro.write(json.dumps(asdict(caso), ensure_ascii=False) + "\n")
    log.info("TRANSFERENCIA %s | motivo: %s | pregunta: %s | cita: %s",
             caso.numero, caso.motivo, caso.pregunta, caso.datos_de_cita or "-")
    return caso


def recepcion_abierta(momento: datetime) -> bool:
    franja = HORARIO_CLINICA.get(momento.weekday())
    return bool(franja) and franja[0] <= momento.time() < franja[1]


def _horario() -> str:
    semana, sabado = HORARIO_CLINICA[0], HORARIO_CLINICA[5]
    return (f"de lunes a viernes de {textos.hora(semana[0])} a {textos.hora(semana[1])} y los sábados de "
            f"{textos.hora(sabado[0])} a {textos.hora(sabado[1])}")


def mensaje(caso: Caso) -> str:
    if recepcion_abierta(modulo_agenda.ahora()):
        return f"Le comunico con recepción. Su número de caso es {caso.numero}. Una persona le atenderá en breve."
    return (f"En este momento recepción está cerrada; abrimos {_horario()}. He registrado su caso {caso.numero} "
            "y le contactarán en el próximo horario de atención.")
