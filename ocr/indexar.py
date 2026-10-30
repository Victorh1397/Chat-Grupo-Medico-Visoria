"""
Índice vectorial de los documentos (spec 10). Proceso offline: se ejecuta una vez, nunca dentro de una petición.

    uv run python -m ocr.indexar                       # calcula los embeddings y escribe ocr/salida/indice.json
    uv run python -m ocr.indexar --solo-fragmentos     # solo enseña los fragmentos, sin llamar a Gemini

Parte del texto OCR de ocr/salida/documentos.json. Si cambian los documentos, hay que volver a ejecutar primero
`ocr.ocr` y después este script: tests/test_recuperacion.py falla si el índice no corresponde a los documentos.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[1]
load_dotenv(RAIZ / ".env")

from webhook.recuperacion import DIMENSION, MODELO_EMBEDDINGS, RUTA_INDICE, incrustar  # noqa: E402

RUTA_DOCUMENTOS = RAIZ / "ocr" / "salida" / "documentos.json"
MAX_CARACTERES = 300  # tamaño aproximado de un fragmento; se ajusta midiendo la evaluación (spec 10, T6)
MIN_CARACTERES = 40  # un fragmento más corto es solo un título de documento
LOTE = 20  # fragmentos por llamada de embeddings

CABECERA_CLINICA = ("Grupo Médico Visoria", "Av. Principal")
PIE = "Documento ficticio"
# Un encabezado es una línea corta, sin punto final ni cifras (las filas de las tablas siempre llevan precio u horas)
ENCABEZADO = re.compile(r"^[^\d.]{3,50}$")


def lineas_utiles(texto: str) -> list[str]:
    """Líneas con contenido, sin la cabecera repetida de cada documento ni el pie, y sin el guion de las viñetas."""
    lineas = []
    for linea in (renglon.strip() for renglon in texto.splitlines()):
        if not linea or linea.startswith(CABECERA_CLINICA) or linea.startswith(PIE):
            continue
        lineas.append(linea.removeprefix("- "))
    return lineas


def fragmentar(documentos: list[dict], max_caracteres: int = MAX_CARACTERES) -> list[dict]:
    """
    Fragmentos con sentido: una pregunta de D1 con su respuesta, una sección de D4/D5, unas filas de tabla de D2/D3.
    Un fragmento nuevo empieza en cada pregunta ("¿") o encabezado; si no, se agrupan líneas hasta `max_caracteres`,
    repitiendo la última línea al continuar para que dos filas vecinas de una tabla queden juntas en algún fragmento.
    En las tablas, cada fragmento lleva la fila de títulos de las columnas ("Especialidad Médico Precio").
    """
    fragmentos = []
    for doc in documentos:
        lineas = lineas_utiles(doc["texto"])
        titulos_tabla = next((linea for linea in lineas if linea.startswith("Especialidad ")), "")
        grupo: list[str] = []

        def cerrar(grupo=grupo, doc=doc, titulos_tabla=titulos_tabla):
            if sum(len(linea) for linea in grupo) < MIN_CARACTERES:  # solo un título: no aporta nada que recuperar
                return
            cuerpo = list(grupo)
            if titulos_tabla and titulos_tabla not in cuerpo and any(" USD" in x or ":" in x for x in cuerpo):
                cuerpo.insert(0, titulos_tabla)
            fragmentos.append({"id": f"{doc['id']}-{sum(f['doc'] == doc['id'] for f in fragmentos) + 1:02d}",
                               "doc": doc["id"], "titulo": doc["titulo"], "texto": "\n".join(cuerpo)})

        for linea in lineas:
            empieza = linea.startswith("¿") or bool(ENCABEZADO.match(linea))
            if grupo and (empieza or sum(len(x) + 1 for x in grupo) + len(linea) > max_caracteres):
                cerrar()
                grupo[:] = [] if empieza else grupo[-1:]
            grupo.append(linea)
        cerrar()
    return fragmentos


def texto_a_incrustar(fragmento: dict) -> str:
    """Lo que se convierte en vector: el título del documento ayuda a distinguir 'precio' de 'horario'."""
    return f"{fragmento['titulo']}\n{fragmento['texto']}"


def escribir_indice(indice: dict, ruta: Path = RUTA_INDICE) -> None:
    """Un fragmento por línea (con su vector): el fichero es legible en un diff, no 19.000 líneas de números."""
    cabecera = {clave: valor for clave, valor in indice.items() if clave != "fragmentos"}
    lineas = [json.dumps(f, ensure_ascii=False) for f in indice["fragmentos"]]
    ruta.write_text(
        "{\n" + "".join(f" {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)},\n" for k, v in cabecera.items())
        + ' "fragmentos": [\n  ' + ",\n  ".join(lineas) + "\n ]\n}\n", encoding="utf-8")


def main(solo_fragmentos: bool = False) -> None:
    documentos = json.loads(RUTA_DOCUMENTOS.read_text(encoding="utf-8"))["documentos"]
    fragmentos = fragmentar(documentos)
    if solo_fragmentos:
        for f in fragmentos:
            print(f"--- {f['id']} ({len(f['texto'])} caracteres) · {f['titulo']}\n{f['texto']}")
        print(f"\n{len(fragmentos)} fragmentos")
        return

    vectores = []
    for inicio in range(0, len(fragmentos), LOTE):
        lote = fragmentos[inicio:inicio + LOTE]
        vectores.extend(incrustar([texto_a_incrustar(f) for f in lote], "RETRIEVAL_DOCUMENT").tolist())
        print(f"Embeddings: {min(inicio + LOTE, len(fragmentos))}/{len(fragmentos)}")

    indice = {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "modelo": MODELO_EMBEDDINGS,
        "dimension": DIMENSION,
        "fragmentos": [{**f, "vector": [round(x, 5) for x in v]} for f, v in zip(fragmentos, vectores)],
    }
    escribir_indice(indice)
    print(f"Escrito {RUTA_INDICE.relative_to(RAIZ)}: {len(fragmentos)} fragmentos de {DIMENSION} dimensiones")


if __name__ == "__main__":
    main(solo_fragmentos="--solo-fragmentos" in sys.argv)
