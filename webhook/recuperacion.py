"""
Recuperación de fragmentos con una base vectorial en memoria (spec 10).

El índice (ocr/salida/indice.json) se genera offline con `uv run python -m ocr.indexar` y se carga UNA VEZ al arrancar
en un índice FAISS. En cada pregunta se calcula el embedding de la consulta y se recuperan los fragmentos más
cercanos; la consulta al modelo se hace en documentos.py, que usa el texto completo si algo de aquí falla.
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import faiss
import numpy as np
from google.genai import types

log = logging.getLogger("visoria")

RUTA_INDICE = Path(__file__).resolve().parents[1] / "ocr" / "salida" / "indice.json"
MODELO_EMBEDDINGS = "gemini-embedding-001"  # el mismo para el índice y para las consultas
# 768 dimensiones separan mejor lo respondible de lo que no está en los documentos que 256 (spec 10, T1)
DIMENSION = 768
# El embedding es solo una parte del presupuesto de 4 s del turno (documentos.TIEMPO_MAXIMO_S): medido ~0,27 s
TIEMPO_EMBEDDING_S = 1.0
FRAGMENTOS_POR_PREGUNTA = 4

_hilos = ThreadPoolExecutor(max_workers=4, thread_name_prefix="embedding")


def incrustar(textos: list[str], tarea: str) -> np.ndarray:
    """
    Embeddings normalizados (L2) de Gemini. `tarea`: RETRIEVAL_DOCUMENT para los fragmentos,
    RETRIEVAL_QUERY para la pregunta.
    """
    from webhook.documentos import cliente  # import tardío: documentos.py importa este módulo

    respuesta = cliente().models.embed_content(
        model=MODELO_EMBEDDINGS, contents=textos,
        config=types.EmbedContentConfig(task_type=tarea, output_dimensionality=DIMENSION))
    vectores = np.array([e.values for e in respuesta.embeddings], dtype="float32")
    faiss.normalize_L2(vectores)
    return vectores


class Indice:
    """Fragmentos y su índice FAISS (búsqueda exacta por producto interno; con vectores normalizados es el coseno)."""

    def __init__(self, fragmentos: list[dict], vectores: np.ndarray):
        self.fragmentos = fragmentos
        self.faiss = faiss.IndexFlatIP(vectores.shape[1])
        self.faiss.add(vectores)

    def buscar(self, vector: np.ndarray, k: int) -> list[dict]:
        puntuaciones, posiciones = self.faiss.search(vector, k)
        return [{**self.fragmentos[i], "puntuacion": round(float(p), 3)}
                for i, p in zip(posiciones[0], puntuaciones[0]) if i >= 0]


def cargar_indice(ruta: Path = RUTA_INDICE) -> Indice | None:
    try:
        fragmentos = json.loads(ruta.read_text(encoding="utf-8"))["fragmentos"]
        vectores = np.array([f["vector"] for f in fragmentos], dtype="float32")
        faiss.normalize_L2(vectores)
        return Indice([{c: f[c] for c in ("id", "doc", "titulo", "texto")} for f in fragmentos], vectores)
    except (OSError, ValueError, KeyError, IndexError) as e:
        log.warning("No se pudo cargar el índice vectorial (%s): se usará el texto completo", e)
        return None


INDICE = cargar_indice()


def calentar(esperar: bool = False) -> None:
    """
    Primera consulta de embeddings, para que el arranque en frío (cliente y conexión) no caiga sobre una pregunta
    real: medido, la primera superaba el límite de 1 s y esa pregunta se quedaba sin recuperación.
    """
    if INDICE is None:
        return
    futuro = _hilos.submit(incrustar, ["calentamiento"], "RETRIEVAL_QUERY")
    if esperar:
        futuro.result(timeout=10)


def recuperar(pregunta: str, k: int = FRAGMENTOS_POR_PREGUNTA, indice: Indice | None = None) -> list[dict]:
    """Los k fragmentos más cercanos a la pregunta. Lanza una excepción si no hay índice o el embedding falla."""
    indice = INDICE if indice is None else indice
    if indice is None:
        raise RuntimeError("No hay índice vectorial")
    vector = _hilos.submit(incrustar, [pregunta], "RETRIEVAL_QUERY").result(timeout=TIEMPO_EMBEDDING_S)
    return indice.buscar(vector, k)
