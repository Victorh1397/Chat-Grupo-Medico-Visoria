"""
Spec 04: regex sobre texto OCR (con errores típicos) y coherencia de ocr/salida/documentos.json.

No necesitan Tesseract: trabajan sobre texto y sobre el JSON versionado.
"""

import json
from pathlib import Path

import pytest

from ocr.contenido import DOCUMENTOS, archivo
from ocr.extraccion import (
    extraer_campos,
    identificar_medico,
    leer_dias,
    normalizar_para_regex,
    validar_horarios,
    validar_tarifario,
)

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = json.loads((RAIZ / "ocr/salida/documentos.json").read_text(encoding="utf-8"))
POR_ID = {d["id"]: d for d in SALIDA["documentos"]}


def referencia(doc_id: str) -> str:
    return (RAIZ / "ocr/referencia" / f"{archivo(doc_id)}.txt").read_text(encoding="utf-8")


# Normalización solo para regex

@pytest.mark.parametrize("ocr, esperado", [
    ("4O USD", "40 USD"),
    ("(O212) 555-Ol42", "(0212) 555-0142"),
    ("8:OO - l2:00", "8:00 - 12:00"),
    ("Oftalmología Dra. Gabriela Quintero", "Oftalmología Dra. Gabriela Quintero"),  # sin cifras: no se toca
])
def test_normalizacion_solo_donde_hay_cifras(ocr, esperado):
    assert normalizar_para_regex(ocr) == esperado


def test_extraer_campos_con_errores_de_ocr():
    texto = ("Precio 4O USD o $ 35. Horario 8:OO - l2:00 y 14:00 a 18:00. "
             "Tel. (O212) 555-0142, 0414-555-0187. 01/09/2026")
    assert extraer_campos(texto) == {
        "importes_usd": ["40", "35"],
        "horarios": ["8:00 - 12:00", "14:00 - 18:00"],
        "telefonos": ["02125550142", "04145550187"],
        "fechas": ["01/09/2026"],
    }


# Tolerancia a errores de OCR en nombres y días

@pytest.mark.parametrize("linea, medico", [
    ("Dermatología Dra. Laura Rojas Martes y jueves", "Laura Rojas"),
    ("Urología Dr. Gustavo Hemández Martes y viemes", "Gustavo Hernández"),  # "rn" leído como "m"
    ("Cirugía plástica Dr. Alejandro Briceno 80 USD", "Alejandro Briceño"),
    ("Oftalmología Dr. José Luis Arismendi Sábados", "José Luis Arismendi"),
])
def test_identificar_medico(linea, medico):
    assert identificar_medico(linea).nombre == medico


def test_medico_desconocido():
    assert identificar_medico("Dr. Juan Inventado 40 USD") is None


@pytest.mark.parametrize("texto, dias", [
    ("Martes y jueves", {1, 3}),
    ("Martes y viemes", {1, 4}),
    ("Miércoles y vienes", {2, 4}),
    ("Lunes a miércoles", {0, 1, 2}),
    ("Lunes, miércoles y viernes", {0, 2, 4}),
    ("Sábados", {5}),
])
def test_leer_dias(texto, dias):
    assert leer_dias(texto) == dias


# Validación contra webhook/datos.py

def test_validacion_de_referencias():
    assert validar_tarifario(referencia("D2"))["ok"]
    assert validar_horarios(referencia("D3"))["ok"]


def test_validacion_detecta_un_precio_distinto():
    alterado = referencia("D2").replace("Dra. Laura Rojas 40 USD", "Dra. Laura Rojas 45 USD")
    resultado = validar_tarifario(alterado)
    assert not resultado["ok"]
    assert resultado["discrepancias"] == ["Laura Rojas: esperado 40, leído 45"]


# Coherencia de la salida del OCR (CA-1 a CA-7)

def test_ca1_imagenes_jpeg():
    for doc_id in DOCUMENTOS:
        assert (RAIZ / "ocr/documentos" / f"{archivo(doc_id)}.jpg").stat().st_size > 50_000


def test_ca2_tiempo():
    assert SALIDA["segundos"] < 60


def test_ca3_calidad():
    similitudes = [d["similitud"] for d in SALIDA["documentos"]]
    assert min(similitudes) >= 0.85
    assert sum(similitudes) / len(similitudes) >= 0.90


def test_ca4_ca5_precios_y_horarios_coinciden_con_el_webhook():
    # Se revalida sobre el texto guardado: si cambia webhook/datos.py sin regenerar los documentos, falla
    assert validar_tarifario(POR_ID["D2"]["texto"])["ok"]
    assert validar_horarios(POR_ID["D3"]["texto"])["ok"]
    assert len(POR_ID["D2"]["campos"]["importes_usd"]) == 12


def test_ca6_telefonos_y_fecha():
    assert {"02125550142", "04145550187"} <= set(POR_ID["D1"]["campos"]["telefonos"])
    assert POR_ID["D2"]["campos"]["fechas"] == ["01/09/2026"]


def test_ca7_estructura_del_json():
    assert list(POR_ID) == ["D1", "D2", "D3", "D4", "D5"]
    for d in SALIDA["documentos"]:
        assert {"id", "titulo", "archivo", "texto", "similitud", "campos", "validacion"} <= set(d)
        assert len(d["texto"]) > 300


def test_ca9_documentos_ficticios():
    assert all("Documento ficticio" in d["texto"] for d in SALIDA["documentos"])
