"""Transferencia a recepción (spec 07). La hora fija de los tests es el domingo 18/10/2026 (recepción cerrada)."""

import json
import re
from datetime import datetime

import pytest

from tests.conftest import datos_cita, peticion
from webhook import agenda as modulo_agenda
from webhook import transferencia
from webhook.agenda import CARACAS
from webhook.documentos import SIN_INFO_DOCUMENTAL, SIN_INFO_FALLBACK

LUNES_10H = datetime(2026, 10, 19, 10, 0, tzinfo=CARACAS)


def decir(cliente, intencion: str, texto: str, parametros: dict | None = None, **kwargs) -> str:
    cuerpo = peticion(intencion, parametros or {}, texto, **kwargs)
    return cliente.post("/webhook", json=cuerpo).json()["fulfillmentText"]


def casos() -> list[dict]:
    if not transferencia.REGISTRO.exists():
        return []
    return [json.loads(linea) for linea in transferencia.REGISTRO.read_text(encoding="utf-8").splitlines()]


@pytest.fixture
def abierto(monkeypatch):
    monkeypatch.setattr(modulo_agenda, "ahora", lambda: LUNES_10H)


# R1 y R5: petición directa y horario

def test_ca1_peticion_directa_en_horario(cliente, abierto):
    texto = decir(cliente, "transferir_humano", "quiero hablar con una persona")
    assert re.fullmatch(r"Le comunico con recepción\. Su número de caso es VIS-\d{5}\. "
                        r"Una persona le atenderá en breve\.", texto)
    [caso] = casos()
    assert caso["motivo"] == "peticion_directa" and caso["pregunta"] == "quiero hablar con una persona"
    assert caso["numero"] in texto and caso["canal"] == "texto"


def test_ca6_fuera_de_horario(cliente):
    texto = decir(cliente, "transferir_humano", "quiero hablar con una persona")
    assert texto.startswith("En este momento recepción está cerrada; abrimos de lunes a viernes de 7:00 a 19:00 "
                            "y los sábados de 7:00 a 13:00. He registrado su caso VIS-")
    assert len(casos()) == 1


@pytest.mark.parametrize("momento, abierta", [
    (datetime(2026, 10, 19, 6, 59, tzinfo=CARACAS), False),
    (datetime(2026, 10, 19, 7, 0, tzinfo=CARACAS), True),
    (datetime(2026, 10, 19, 18, 59, tzinfo=CARACAS), True),
    (datetime(2026, 10, 19, 19, 0, tzinfo=CARACAS), False),
    (datetime(2026, 10, 24, 12, 30, tzinfo=CARACAS), True),   # sábado
    (datetime(2026, 10, 24, 13, 30, tzinfo=CARACAS), False),
    (datetime(2026, 10, 25, 10, 0, tzinfo=CARACAS), False),   # domingo
])
def test_r5_horario_de_recepcion(momento, abierta):
    assert transferencia.recepcion_abierta(momento) is abierta


# R2: aceptar o rechazar la oferta

def test_ca2_si_a_la_oferta_crea_el_caso(cliente, abierto):
    assert decir(cliente, "consulta_documental", "¿hacen resonancias?") == SIN_INFO_DOCUMENTAL
    texto = decir(cliente, "Default Fallback Intent", "sí, por favor")
    assert texto.startswith("Le comunico con recepción. Su número de caso es VIS-")
    [caso] = casos()
    assert (caso["motivo"], caso["pregunta"]) == ("informacion_no_disponible", "¿hacen resonancias?")


def test_ca2_no_a_la_oferta(cliente):
    decir(cliente, "consulta_documental", "¿hacen resonancias?")
    assert decir(cliente, "Default Fallback Intent", "no gracias") == "De acuerdo. ¿Le puedo ayudar en algo más?"
    assert casos() == []


def test_ca3_la_oferta_caduca_si_se_pregunta_otra_cosa(cliente, modelo):
    decir(cliente, "consulta_documental", "¿hacen resonancias?")
    modelo.respuesta = "Sí, la torre tiene estacionamiento propio en el sótano."
    assert decir(cliente, "consulta_documental", "¿tienen estacionamiento?") == modelo.respuesta
    modelo.respuesta = "NO_DISPONIBLE"
    assert "VIS-" not in decir(cliente, "Default Fallback Intent", "sí")
    assert casos() == []


def test_otra_frase_en_el_fallback_tras_la_oferta_se_atiende_con_normalidad(cliente, modelo):
    decir(cliente, "consulta_documental", "¿hacen resonancias?")
    modelo.respuesta = "Sí, se permite un acompañante por paciente."
    assert decir(cliente, "Default Fallback Intent", "¿puedo ir con mi mamá?") == modelo.respuesta


def test_error_tecnico_tambien_ofrece(cliente, modelo):
    modelo.respuesta = TimeoutError()
    decir(cliente, "consulta_documental", "¿tienen estacionamiento?")
    decir(cliente, "Default Fallback Intent", "claro")
    assert casos()[0]["motivo"] == "error_tecnico"


@pytest.mark.parametrize("frase", ["sí", "Sí.", "si por favor", "claro", "de acuerdo", "ok", "okay, gracias",
                                   "está bien"])
def test_afirmativos(frase):
    assert transferencia.AFIRMATIVO.match(frase)


@pytest.mark.parametrize("frase", ["no", "No, gracias", "mejor no", "ahora no"])
def test_negativos(frase):
    assert transferencia.NEGATIVO.match(frase)


@pytest.mark.parametrize("frase", ["¿tienen estacionamiento?", "sí, pero antes dígame el horario", "no sé"])
def test_ni_si_ni_no(frase):
    assert not transferencia.AFIRMATIVO.match(frase) and not transferencia.NEGATIVO.match(frase)


# R3: oferta automática

def test_ca4_dos_turnos_sin_entender(cliente):
    assert decir(cliente, "Default Fallback Intent", "asdfgh") == SIN_INFO_FALLBACK
    assert decir(cliente, "Default Fallback Intent", "qwerty") == transferencia.OFERTA_NO_ENTENDIDO
    decir(cliente, "Default Fallback Intent", "sí")
    assert casos()[0]["motivo"] == "no_entendido"


def test_el_contador_se_reinicia_con_otra_intencion(cliente):
    decir(cliente, "Default Fallback Intent", "asdfgh")
    decir(cliente, "consultar_horarios", "cardiología", {"especialidad": "Cardiología"})
    assert decir(cliente, "Default Fallback Intent", "qwerty") == SIN_INFO_FALLBACK


def test_el_cierre_no_cuenta_como_no_entendido(cliente):
    decir(cliente, "Default Fallback Intent", "asdfgh")
    assert "buen día" in decir(cliente, "Default Fallback Intent", "eso es todo")
    assert decir(cliente, "Default Fallback Intent", "qwerty") == SIN_INFO_FALLBACK


# R4: resumen del caso

def test_ca5_transferencia_a_mitad_de_la_cita(cliente):
    parametros = datos_cita(hora="")
    cliente.post("/webhook", json=peticion("agendar_cita", parametros, "el martes", todos=False, esperando="hora"))
    decir(cliente, "transferir_humano", "quiero hablar con una persona")
    [caso] = casos()
    assert caso["datos_de_cita"] == {"nombre": "María", "apellido": "González", "especialidad": "Dermatología",
                                     "fecha": "20/10/2026", "cedula": "***987"}
    assert "14523987" not in json.dumps(caso)


def test_tras_confirmar_la_cita_no_se_arrastran_sus_datos(cliente):
    cliente.post("/webhook", json=peticion("agendar_cita", datos_cita(), "a las 10"))
    decir(cliente, "agendar_cita - yes", "sí")
    decir(cliente, "transferir_humano", "quiero hablar con una persona")
    assert casos()[0]["datos_de_cita"] == {}


# CA-7: por voz

def test_ca7_por_voz_en_ssml(cliente):
    cuerpo = {**peticion("transferir_humano", {}, "quiero hablar con una persona"),
              "originalDetectIntentRequest": {"payload": {"canal": "voz"}}}
    texto = cliente.post("/webhook", json=cuerpo).json()["fulfillmentText"]
    assert texto.startswith("<speak>") and '<say-as interpret-as="characters">VIS</say-as>' in texto
    assert casos()[0]["canal"] == "voz"


def test_oferta_por_voz_se_detecta_antes_del_ssml(cliente):
    cuerpo = {**peticion("consulta_documental", {}, "¿hacen resonancias?"),
              "originalDetectIntentRequest": {"payload": {"canal": "voz"}}}
    cliente.post("/webhook", json=cuerpo)
    assert transferencia.ofertas[cuerpo["session"]].motivo == "informacion_no_disponible"
