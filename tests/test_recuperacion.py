"""Spec 10: base vectorial para la consulta documental. Sin red: los embeddings se simulan."""

import json

import numpy as np
import pytest

from ocr.indexar import fragmentar
from webhook import documentos, recuperacion
from webhook.documentos import DOCUMENTOS, SIN_INFO_DOCUMENTAL, responder_con_documentos
from webhook.recuperacion import Indice, recuperar

ESTACIONAMIENTO = {"id": "D1-02", "doc": "D1", "titulo": "Preguntas frecuentes", "puntuacion": 0.8,
                   "texto": "¿Tienen estacionamiento?\nSí. La torre tiene estacionamiento propio en el sótano."}


def test_ca1_fragmentos_con_sentido_en_todos_los_documentos():
    fragmentos = fragmentar(DOCUMENTOS)
    assert {f["doc"] for f in fragmentos} == {d["id"] for d in DOCUMENTOS}
    # la pregunta y su respuesta quedan en el mismo fragmento
    estacionamiento = next(f for f in fragmentos if "¿Tienen estacionamiento?" in f["texto"])
    assert "estacionamiento propio" in estacionamiento["texto"]
    # las filas de una tabla llevan los títulos de sus columnas, y los dos cardiólogos quedan juntos en algún fragmento
    cardiologos = [f for f in fragmentos if f["doc"] == "D2" and "Rangel" in f["texto"] and "Medina" in f["texto"]]
    assert cardiologos and "Especialidad Médico Precio" in cardiologos[0]["texto"]


def test_ca1_el_indice_versionado_corresponde_a_los_documentos():
    indice = json.loads(recuperacion.RUTA_INDICE.read_text(encoding="utf-8"))
    esperados = fragmentar(DOCUMENTOS)
    assert [(f["id"], f["texto"]) for f in indice["fragmentos"]] == [(f["id"], f["texto"]) for f in esperados], \
        "ocr/salida/indice.json no corresponde a documentos.json: ejecutar `uv run python -m ocr.indexar`"
    assert {len(f["vector"]) for f in indice["fragmentos"]} == {indice["dimension"]}


def test_la_base_vectorial_devuelve_el_fragmento_mas_cercano(monkeypatch):
    fragmentos = [{"id": f"D1-0{i}", "doc": "D1", "titulo": "t", "texto": f"texto {i}"} for i in range(3)]
    indice = Indice(fragmentos, np.array([[1, 0], [0, 1], [0.7, 0.7]], dtype="float32"))
    monkeypatch.setattr(recuperacion, "incrustar", lambda textos, tarea: np.array([[0, 1]], dtype="float32"))
    recuperados = recuperar("pregunta", k=2, indice=indice)
    assert [f["id"] for f in recuperados] == ["D1-01", "D1-02"]


def test_ca2_al_modelo_solo_llegan_los_fragmentos_recuperados(monkeypatch, modelo):
    monkeypatch.setattr(recuperacion, "recuperar", lambda pregunta, **kw: [ESTACIONAMIENTO])
    modelo.respuesta = "Sí, hay estacionamiento."
    responder_con_documentos("¿Tienen estacionamiento?", SIN_INFO_DOCUMENTAL)
    prompt = modelo.prompts[0]
    assert "estacionamiento propio" in prompt
    assert "Patricia Medina" not in prompt  # los demás documentos no se envían


@pytest.mark.parametrize("fallo", [ConnectionError("sin red"), TimeoutError("lento"), RuntimeError("sin índice")])
def test_ca5_si_falla_la_recuperacion_se_envia_el_texto_completo(monkeypatch, modelo, fallo):
    def falla(pregunta, **kw):
        raise fallo

    monkeypatch.setattr(recuperacion, "recuperar", falla)
    modelo.respuesta = "Sí."
    assert responder_con_documentos("¿Tienen estacionamiento?", SIN_INFO_DOCUMENTAL) == "Sí."
    assert "estacionamiento propio" in modelo.prompts[0] and "Patricia Medina" in modelo.prompts[0]


def test_el_modo_completo_no_recupera(monkeypatch, modelo):
    monkeypatch.setenv("RECUPERACION", "completo")
    monkeypatch.setattr(recuperacion, "recuperar", lambda *a, **kw: pytest.fail("no debe recuperar"))
    responder_con_documentos("¿Tienen estacionamiento?", SIN_INFO_DOCUMENTAL)
    assert "Patricia Medina" in modelo.prompts[0]


def test_con_documentos_explicitos_no_se_recupera(monkeypatch, modelo):
    monkeypatch.setattr(recuperacion, "recuperar", lambda *a, **kw: pytest.fail("no debe recuperar"))
    documentos_de_prueba = [{"id": "X", "titulo": "Prueba", "texto": "contenido de prueba"}]
    responder_con_documentos("¿Qué hay?", SIN_INFO_DOCUMENTAL, documentos_de_prueba)
    assert "contenido de prueba" in modelo.prompts[0]
    assert documentos.DOCUMENTOS  # el módulo sigue cargado
