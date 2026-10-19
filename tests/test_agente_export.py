"""
Verificación de la spec 02 sobre el export del agente Dialogflow (carpeta agente/).

Se ejecuta tras cada nuevo export:
    uv run pytest tests/test_agente_export.py -v

Los CA-n hacen referencia a los criterios de aceptación de specs/02-agente-dialogflow/spec.md.
"""

import json
import re
import unicodedata
from pathlib import Path

import pytest

AGENTE = Path(__file__).resolve().parents[1] / "agente"

SIGNIFICATIVAS = [
    "agendar_cita",
    "consulta_documental",
    "consultar_horarios",
    "consultar_historial",
    "cancelar_cita",
    "transferir_humano",
]
FOLLOW_UPS = [
    "agendar_cita - yes",
    "agendar_cita - no",
    "agendar_cita - no - yes",
    "agendar_cita - no - no",
]
CON_WEBHOOK = SIGNIFICATIVAS + ["agendar_cita - yes", "agendar_cita - no - yes", "Default Fallback Intent"]


# Utilidades

def leer(ruta: str):
    return json.loads((AGENTE / ruta).read_text(encoding="utf-8"))


def intencion(nombre: str) -> dict:
    return leer(f"intents/{nombre}.json")


def frases(nombre: str) -> list[str]:
    ruta = AGENTE / f"intents/{nombre}_usersays_es.json"
    if not ruta.exists():
        return []
    return ["".join(p["text"] for p in f["data"]) for f in json.loads(ruta.read_text(encoding="utf-8"))]


def respuestas(datos: dict) -> list[str]:
    textos = []
    for m in datos["responses"][0]["messages"]:
        speech = m.get("speech", [])
        textos += [speech] if isinstance(speech, str) else speech
    return [t for t in textos if t.strip()]


def contextos_salida(datos: dict) -> dict[str, int]:
    return {c["name"]: c["lifespan"] for c in datos["responses"][0]["affectedContexts"]}


def parametros(datos: dict) -> list[dict]:
    return datos["responses"][0]["parameters"]


# CA-1: intenciones

def test_ca1_estan_todas_las_intenciones():
    esperadas = SIGNIFICATIVAS + FOLLOW_UPS + ["Default Welcome Intent", "Default Fallback Intent"]
    presentes = {p.stem for p in (AGENTE / "intents").glob("*.json") if not p.stem.endswith("_usersays_es")}
    assert set(esperadas) == presentes


def test_ca1_seis_intenciones_significativas_con_frases():
    for nombre in SIGNIFICATIVAS:
        minimo = 20 if nombre == "consulta_documental" else 10
        assert len(frases(nombre)) >= minimo, nombre


# CA-2: entidades

def test_ca2_cedula_es_regex_con_dos_filas_en_orden():
    assert leer("entities/cedula.json")["isRegexp"] is True
    filas = [e["value"] for e in leer("entities/cedula_entries_es.json")]
    assert filas == ["[1-9][0-9]{5,8}", r"[1-9][0-9]{0,2}([.,\s][0-9]{3}){1,2}"]


def _cedula_reconocida(texto: str) -> str | None:
    """
    Imita a Dialogflow: une las filas con | y se queda con la PRIMERA coincidencia,
    que solo vale si abarca el número completo (sin dígitos pegados a los lados).
    """
    filas = [e["value"] for e in leer("entities/cedula_entries_es.json")]
    m = re.search("|".join(f"(?:{f})" for f in filas), texto)
    if not m:
        return None
    antes = texto[m.start() - 1] if m.start() > 0 else " "
    despues = texto[m.end()] if m.end() < len(texto) else " "
    return None if antes.isdigit() or despues.isdigit() else m.group()


@pytest.mark.parametrize("texto, esperado", [
    ("14523987", "14523987"),
    ("9452312", "9452312"),
    ("81234567", "81234567"),
    ("945123", "945123"),
    ("14.523.987", "14.523.987"),
    ("14 523 987", "14 523 987"),
    ("mi cédula es 14523987", "14523987"),
    ("1234", None),
    ("2026", None),
])
def test_ca2_regex_cedula_reconoce_el_numero_completo(texto, esperado):
    assert _cedula_reconocida(texto) == esperado


@pytest.mark.parametrize("entidad, valores", [
    ("especialidad", ["Dermatología", "Endocrinología", "Cirugía plástica", "Urología", "Cardiología", "Oftalmología"]),
    ("nacionalidad", ["V", "E"]),
])
def test_ca2_entidades_con_sinonimos_separados(entidad, valores):
    entradas = leer(f"entities/{entidad}_entries_es.json")
    assert [e["value"] for e in entradas] == valores
    for e in entradas:
        # Un sinónimo con comas significa que se guardó la lista entera como un solo texto
        assert not any("," in s for s in e["synonyms"]), e["value"]
        assert len(e["synonyms"]) > 2, e["value"]


def test_ca2_nacionalidad_reconoce_gentilicios():
    sinonimos = {e["value"]: e["synonyms"] for e in leer("entities/nacionalidad_entries_es.json")}
    assert {"venezolano", "venezolana"} <= set(sinonimos["V"])
    assert {"extranjero", "extranjera", "colombiano", "española"} <= set(sinonimos["E"])
    assert leer("entities/nacionalidad.json")["automatedExpansion"] is True


# CA-3: agendar_cita

def test_ca3_agendar_cita_parametros_en_orden():
    esperado = [
        ("nombre", "@sys.given-name"),
        ("apellido", "@sys.last-name"),
        ("nacionalidad", "@nacionalidad"),
        ("cedula", "@cedula"),
        ("especialidad", "@especialidad"),
        ("fecha", "@sys.date"),
        ("hora", "@sys.time"),
    ]
    params = parametros(intencion("agendar_cita"))
    assert [(p["name"], p["dataType"]) for p in params] == esperado
    for p in params:
        assert p["required"] and not p["isList"], p["name"]
        assert p["value"] == f"${p['name']}"
        assert p["prompts"] and p["prompts"][0]["value"].strip(), p["name"]


def test_ca3_agendar_cita_contexto_y_evento():
    datos = intencion("agendar_cita")
    assert contextos_salida(datos)["ctx_cita_en_curso"] == 5
    assert "agendar_cita-followup" in contextos_salida(datos)
    assert [e["name"] for e in datos["events"]] == ["INICIAR_CITA"]


CONFIRMACION = {"ctx_cita_en_curso", "agendar_cita-followup"}
REINICIO = {"agendar_cita-no-followup"}


@pytest.mark.parametrize("nombre, entrada, apagados, activos", [
    ("agendar_cita - yes", CONFIRMACION, CONFIRMACION, set()),
    ("agendar_cita - no", CONFIRMACION, CONFIRMACION, REINICIO),
    ("agendar_cita - no - yes", REINICIO, REINICIO, set()),
    ("agendar_cita - no - no", REINICIO, REINICIO, set()),
])
def test_ca5_follow_ups_abren_y_cierran_contextos(nombre, entrada, apagados, activos):
    datos = intencion(nombre)
    salida = contextos_salida(datos)
    assert set(datos["contexts"]) == entrada
    assert all(salida.get(c) == 0 for c in apagados), salida
    assert all(salida.get(c, 0) > 0 for c in activos), salida


@pytest.mark.parametrize("nombre", ["consultar_historial", "cancelar_cita"])
def test_cedula_obligatoria_y_sin_frases_con_cedula(nombre):
    params = {p["name"]: p for p in parametros(intencion(nombre))}
    assert params["cedula"]["dataType"] == "@cedula" and params["cedula"]["required"]
    # Una frase con cédula sacaría al usuario de agendar_cita durante el slot filling
    assert not any(re.search(r"\d{4,}", f) for f in frases(nombre))


def test_consultar_horarios_pide_especialidad():
    params = {p["name"]: p for p in parametros(intencion("consultar_horarios"))}
    assert params["especialidad"]["required"] and not params["especialidad"]["isList"]


def sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def test_fallback_tiene_ejemplos_negativos():
    negativos = {sin_tildes(f) for f in frases("Default Fallback Intent")}
    assert {"no", "no gracias", "nada mas", "eso es todo"} <= negativos


# CA-8: webhook y respuestas de reserva

@pytest.mark.parametrize("nombre", CON_WEBHOOK)
def test_ca8_webhook_activado_y_respuesta_de_reserva(nombre):
    datos = intencion(nombre)
    assert datos["webhookUsed"] is True
    assert respuestas(datos), f"{nombre} no tiene respuesta de reserva"


def test_ca8_agendar_cita_webhook_en_slot_filling():
    assert intencion("agendar_cita")["webhookForSlotFilling"] is True


# CA-9: zona horaria

def test_ca9_zona_horaria_utc_menos_4():
    assert leer("agent.json")["defaultTimezone"] in {"America/Caracas", "America/Barbados"}


# CA-10: trato de usted

TUTEO = re.compile(r"\b(tú|tu|te|ti|quieres|puedes|tienes|deseas|necesitas|dime|dímelo|confirmas)\b", re.IGNORECASE)


def test_ca10_respuestas_y_preguntas_de_usted():
    textos = []
    for ruta in (AGENTE / "intents").glob("*.json"):
        if ruta.stem.endswith("_usersays_es"):
            continue
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        textos += respuestas(datos)
        textos += [pr["value"] for p in parametros(datos) for pr in p["prompts"]]
    tuteo = [t for t in textos if TUTEO.search(t)]
    assert not tuteo, tuteo
