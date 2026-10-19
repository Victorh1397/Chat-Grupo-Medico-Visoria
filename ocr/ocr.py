"""
OCR offline de los documentos de la clínica con Tesseract (spec 04, R2-R5).

Se ejecuta UNA VEZ (o al cambiar los documentos), nunca dentro de una petición del webhook:
reconocer una imagen tarda segundos y Dialogflow corta a los 5.

Uso (desde la raíz del repositorio):
    uv run python -m ocr.ocr              # OCR + regex + validación -> ocr/salida/documentos.json
    uv run python -m ocr.ocr --comparar   # efecto de cada paso del preprocesado en la calidad
"""

import difflib
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pytesseract
from PIL import Image

from ocr.contenido import DOCUMENTOS, archivo
from ocr.extraccion import extraer_campos, validar_horarios, validar_tarifario

CARPETA = Path(__file__).parent
DOCUMENTOS_DIR = CARPETA / "documentos"
REFERENCIA_DIR = CARPETA / "referencia"
SALIDA = CARPETA / "salida" / "documentos.json"

IDIOMA = "spa"  # sin esto, Tesseract asume inglés y rompe los acentos
CONFIG = "--psm 6"  # un bloque de texto uniforme: funciona con tablas de una fila por médico


# Preprocesado

def umbral_otsu(gris: np.ndarray) -> int:
    """Umbral que mejor separa tinta y papel (maximiza la varianza entre ambas clases)."""
    histograma = np.bincount(gris.ravel(), minlength=256).astype(float)
    total = gris.size
    suma_total = np.dot(np.arange(256), histograma)
    mejor, umbral, peso_fondo, suma_fondo = 0.0, 0, 0.0, 0.0
    for t in range(256):
        peso_fondo += histograma[t]
        if peso_fondo == 0 or peso_fondo == total:
            continue
        suma_fondo += t * histograma[t]
        media_fondo = suma_fondo / peso_fondo
        media_tinta = (suma_total - suma_fondo) / (total - peso_fondo)
        varianza = peso_fondo * (total - peso_fondo) * (media_fondo - media_tinta) ** 2
        if varianza > mejor:
            mejor, umbral = varianza, t
    return umbral


def estimar_inclinacion(gris: Image.Image) -> float:
    """
    Ángulo que endereza el texto: con las líneas horizontales, la suma de tinta por fila alterna
    entre filas llenas y vacías y su varianza es máxima.
    """
    pequena = gris.resize((gris.width // 4, gris.height // 4))
    tinta = np.asarray(pequena) < umbral_otsu(np.asarray(pequena))
    imagen_tinta = Image.fromarray((tinta * 255).astype(np.uint8))
    mejores = max(np.arange(-3, 3.01, 0.1),
                  key=lambda a: np.asarray(imagen_tinta.rotate(a, resample=Image.BILINEAR)).sum(axis=1).var())
    return round(float(mejores), 1)


def tramos_rectos(tinta: np.ndarray, largo: int) -> np.ndarray:
    """Píxeles que forman parte de un tramo horizontal de tinta de al menos `largo` píxeles seguidos."""
    acumulado = np.cumsum(np.pad(tinta, ((0, 0), (1, 0))).astype(np.int32), axis=1)
    empieza = (acumulado[:, largo:] - acumulado[:, :-largo]) == largo  # ventana [j, j+largo) toda tinta
    marcas = np.zeros((tinta.shape[0], tinta.shape[1] + 1), np.int32)
    marcas[:, :empieza.shape[1]] += empieza
    marcas[:, largo:largo + empieza.shape[1]] -= empieza
    return np.cumsum(marcas, axis=1)[:, :tinta.shape[1]] > 0


def quitar_lineas(binaria: np.ndarray) -> np.ndarray:
    """
    Borra las líneas de las tablas: tramos rectos de tinta mucho más largos que cualquier letra.
    Sin este paso Tesseract confunde las celdas con letras y devuelve basura ("CT CIO CN").
    """
    tinta = binaria == 0
    horizontales = engrosar(tramos_rectos(tinta, binaria.shape[1] // 30), 4)
    verticales = engrosar(tramos_rectos(tinta.T, 60), 4).T
    return np.where(horizontales | verticales, 255, binaria).astype(np.uint8)


def engrosar(mascara: np.ndarray, pixeles: int) -> np.ndarray:
    """Extiende la máscara `pixeles` filas arriba y abajo: las líneas escaneadas tienen bordes irregulares."""
    resultado = mascara.copy()
    for d in range(1, pixeles + 1):
        resultado[d:] |= mascara[:-d]
        resultado[:-d] |= mascara[d:]
    return resultado


PASOS = ["grises", "ampliar", "enderezar", "binarizar", "quitar_lineas"]


def preprocesar(imagen: Image.Image, pasos: list[str] = PASOS) -> Image.Image:
    img = imagen.convert("L") if "grises" in pasos else imagen
    if "ampliar" in pasos:
        # Tesseract rinde mejor con letras de unos 30 px de alto; a 150 ppp miden ~15
        img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
    if "enderezar" in pasos:
        gris = img if img.mode == "L" else img.convert("L")
        fondo = 255 if img.mode == "L" else "white"
        img = img.rotate(estimar_inclinacion(gris), resample=Image.BICUBIC, fillcolor=fondo)
    if "binarizar" in pasos:
        gris = np.asarray(img if img.mode == "L" else img.convert("L"))
        img = Image.fromarray(((gris > umbral_otsu(gris)) * 255).astype(np.uint8))
    if "quitar_lineas" in pasos and "binarizar" in pasos:
        img = Image.fromarray(quitar_lineas(np.asarray(img)))
    return img


def reconocer(ruta: Path, pasos: list[str] = PASOS) -> str:
    return pytesseract.image_to_string(preprocesar(Image.open(ruta), pasos), lang=IDIOMA, config=CONFIG)


# Calidad

def similitud(a: str, b: str) -> float:
    """Parecido entre el texto OCR y el de referencia (0-1), ignorando saltos de línea y espacios."""
    return difflib.SequenceMatcher(None, " ".join(a.split()), " ".join(b.split()), autojunk=False).ratio()


def referencia(doc_id: str) -> str:
    return (REFERENCIA_DIR / f"{archivo(doc_id)}.txt").read_text(encoding="utf-8")


# Programa

def procesar() -> None:
    inicio = time.perf_counter()
    documentos = []
    for doc_id, (titulo, _) in DOCUMENTOS.items():
        ruta = DOCUMENTOS_DIR / f"{archivo(doc_id)}.jpg"
        texto = reconocer(ruta)
        validacion = (validar_tarifario(texto) if doc_id == "D2"
                      else validar_horarios(texto) if doc_id == "D3" else None)
        documentos.append({
            "id": doc_id,
            "titulo": titulo,
            "archivo": f"ocr/documentos/{ruta.name}",
            "texto": texto.strip(),
            "caracteres": len(texto.strip()),
            "similitud": round(similitud(texto, referencia(doc_id)), 4),
            "campos": extraer_campos(texto),
            "validacion": validacion,
        })

    segundos = time.perf_counter() - inicio
    SALIDA.parent.mkdir(exist_ok=True)
    SALIDA.write_text(json.dumps({
        "generado": datetime.now().isoformat(timespec="seconds"),
        "motor": f"Tesseract {pytesseract.get_tesseract_version()} (lang={IDIOMA}, {CONFIG})",
        "preprocesado": PASOS,
        "segundos": round(segundos, 1),
        "documentos": documentos,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"{'Doc':4} {'Caract.':>7} {'Similitud':>9}  Campos extraídos")
    for d in documentos:
        c = d["campos"]
        print(f"{d['id']:4} {d['caracteres']:>7} {d['similitud']:>9.1%}  importes={len(c['importes_usd'])} "
              f"horarios={len(c['horarios'])} teléfonos={c['telefonos']} fechas={c['fechas']}")
        if d["validacion"]:
            v = d["validacion"]
            estado = "OK" if v["ok"] else "DISCREPANCIAS"
            print(f"     validación contra webhook/datos.py: {v['coinciden']}/{v['esperados']} {estado}")
            for problema in v["discrepancias"]:
                print(f"       - {problema}")
    media = sum(d["similitud"] for d in documentos) / len(documentos)
    print(f"\nSimilitud media: {media:.1%} | Tiempo total: {segundos:.1f} s | "
          f"Salida: {SALIDA.relative_to(CARPETA.parent)}")


def comparar() -> None:
    """Similitud con referencia al ir añadiendo pasos de preprocesado (para justificarlos en el README)."""
    variantes = {"sin preprocesado": []}
    for i in range(1, len(PASOS) + 1):
        variantes[" + ".join(PASOS[:i])] = PASOS[:i]
    print(f"{'Preprocesado':45}" + "".join(f"{d:>8}" for d in DOCUMENTOS) + f"{'Media':>8}")
    for nombre, pasos in variantes.items():
        valores = [similitud(reconocer(DOCUMENTOS_DIR / f"{archivo(d)}.jpg", pasos), referencia(d))
                   for d in DOCUMENTOS]
        print(f"{nombre:45}" + "".join(f"{v:>8.1%}" for v in valores) + f"{sum(valores) / len(valores):>8.1%}")


if __name__ == "__main__":
    comparar() if "--comparar" in sys.argv else procesar()
