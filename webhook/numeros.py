"""
Números dichos en palabras -> cifras (spec 06, R2.3).

El reconocimiento de voz suele escribir la cédula en cifras, pero puede devolverla en palabras
("catorce millones quinientos veintitrés mil novecientos ochenta y siete"), mezclada
("14 millones 523 mil 987") o cifra a cifra ("uno cuatro cinco dos tres nueve ocho siete").
"""

import re
import unicodedata

VALORES = {
    "cero": 0, "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
    "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14,
    "quince": 15, "dieciseis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19, "veinte": 20,
    "veintiun": 21, "veintiuno": 21, "veintidos": 22, "veintitres": 23, "veinticuatro": 24, "veinticinco": 25,
    "veintiseis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29, "treinta": 30, "cuarenta": 40,
    "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90, "cien": 100, "ciento": 100,
    "doscientos": 200, "doscientas": 200, "trescientos": 300, "trescientas": 300, "cuatrocientos": 400,
    "cuatrocientas": 400, "quinientos": 500, "quinientas": 500, "seiscientos": 600, "seiscientas": 600,
    "setecientos": 700, "setecientas": 700, "ochocientos": 800, "ochocientas": 800, "novecientos": 900,
    "novecientas": 900,
}
MULTIPLICADORES = {"mil": 1_000, "millon": 1_000_000, "millones": 1_000_000}


def _plano(texto: str) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]", " ", sin_tildes)


def palabras_a_numero(texto: str) -> int | None:
    """Número contenido en el texto, o None si no hay ninguno. Ignora palabras de relleno ("mi cédula es…")."""
    piezas = []
    for palabra in _plano(texto).split():
        if palabra.isdigit():
            piezas.append(int(palabra))
        elif palabra in VALORES:
            piezas.append(VALORES[palabra])
        elif palabra in MULTIPLICADORES:
            piezas.append(palabra)
    if not piezas:
        return None
    numeros = [p for p in piezas if isinstance(p, int)]

    # Dictado cifra a cifra: "uno cuatro cinco dos tres nueve ocho siete"
    if len(numeros) >= 6 and len(numeros) == len(piezas) and all(n < 10 for n in numeros):
        return int("".join(map(str, numeros)))

    total, grupo = 0, 0
    for pieza in piezas:
        if pieza == "mil":
            total += (grupo or 1) * 1_000
            grupo = 0
        elif pieza in ("millon", "millones"):
            total += (grupo or 1) * 1_000_000
            grupo = 0
        else:
            grupo += pieza
    return total + grupo
