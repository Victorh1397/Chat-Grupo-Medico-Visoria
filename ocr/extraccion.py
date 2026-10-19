"""
Validación y extracción de campos con expresiones regulares sobre el texto reconocido por OCR (spec 04, R3).

No depende de Tesseract: trabaja sobre texto, así que se prueba con ejemplos que imitan errores de OCR.
"""

import difflib
import re
import unicodedata

from webhook.datos import MEDICOS

# Campos

IMPORTE = re.compile(r"\$\s*(\d{1,4})\b|\b(\d{1,4})\s*(?:USD|d[oó]lares)\b", re.IGNORECASE)
HORARIO = re.compile(r"\b(\d{1,2}):(\d{2})\s*(?:-|–|—|a)\s*(\d{1,2}):(\d{2})\b")
TELEFONO = re.compile(r"\(?\b0(?:2\d{2}|4\d{2})\)?[\s.-]*\d{3}[\s.-]?\d{4}\b")
FECHA = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
MEDICO = re.compile(r"\b(Dra?)\.?\s+((?:[A-ZÁÉÍÓÚÑ][a-záéíóúñü]+\s*){2,3})")

# Confusiones típicas del OCR dentro de algo que debería ser un número
CONFUSIONES = str.maketrans({"O": "0", "o": "0", "D": "0", "l": "1", "I": "1", "|": "1", "S": "5", "B": "8"})
TOKEN_CON_CIFRAS = re.compile(r"[\dOoDlI|SB:$()/.-]*\d[\dOoDlI|SB:$()/.-]*")


def normalizar_para_regex(texto: str) -> str:
    """
    Corrige O/0, l/1, S/5, B/8 SOLO en los fragmentos que ya contienen alguna cifra ("4O USD" -> "40 USD").

    Es destructivo si se aplica a palabras ("Oftalmología" -> "0ftalm0l0gía"), por eso solo se usa
    sobre la copia que pasa por las regex y nunca sobre el texto que verá el LLM.
    """
    return TOKEN_CON_CIFRAS.sub(lambda m: m.group().translate(CONFUSIONES), texto)


def extraer_campos(texto: str) -> dict[str, list[str]]:
    copia = normalizar_para_regex(texto)
    return {
        "importes_usd": [a or b for a, b in IMPORTE.findall(copia)],
        "horarios": [f"{int(h1)}:{m1} - {int(h2)}:{m2}" for h1, m1, h2, m2 in HORARIO.findall(copia)],
        "telefonos": [re.sub(r"\D", "", t) for t in TELEFONO.findall(copia)],
        "fechas": [f"{int(d):02d}/{int(m):02d}/{a}" for d, m, a in FECHA.findall(copia)],
    }


# Médicos

def sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


NOMBRES = {sin_tildes(m.nombre).lower(): m for m in MEDICOS}


def identificar_medico(linea: str):
    """Médico mencionado en la línea, tolerando errores de OCR en el nombre ('Briceno' -> Alejandro Briceño)."""
    m = MEDICO.search(linea)
    if not m:
        return None
    palabras = sin_tildes(m.group(2)).lower().split()
    # Se compara con las mismas palabras que tiene cada nombre (la regex puede arrastrar la palabra siguiente,
    # p. ej. "Gustavo Hemández Martes") y por parecido, porque el OCR confunde "rn" con "m".
    mejor, parecido = None, 0.0
    for nombre, medico in NOMBRES.items():
        leido = " ".join(palabras[:len(nombre.split())])
        ratio = difflib.SequenceMatcher(None, leido, nombre).ratio()
        if ratio > parecido:
            mejor, parecido = medico, ratio
    return mejor if parecido >= 0.85 else None


# Días de la semana

DIAS = {"lunes": 0, "martes": 1, "miercoles": 2, "jueves": 3, "viernes": 4, "sabado": 5, "sabados": 5, "domingo": 6}


def dia_de(palabra: str) -> int | None:
    """Día de la semana tolerando errores de OCR: 'viemes' / 'vienes' -> viernes."""
    parecido = difflib.get_close_matches(palabra, DIAS, n=1, cutoff=0.75)
    return DIAS[parecido[0]] if parecido else None


def leer_dias(texto: str) -> set[int]:
    """'Lunes a miércoles' -> {0, 1, 2}; 'Martes y viemes' -> {1, 4}."""
    palabras = re.findall(r"[a-z]+", sin_tildes(texto).lower())
    encontrados = [(i, d) for i, p in enumerate(palabras) if len(p) >= 5 and (d := dia_de(p)) is not None]
    dias = [d for _, d in encontrados]
    # "lunes a miércoles": dos días separados solo por "a" indican un rango
    if len(encontrados) == 2 and encontrados[1][0] - encontrados[0][0] == 2 and palabras[encontrados[0][0] + 1] == "a":
        return set(range(dias[0], dias[1] + 1))
    return set(dias)


# Validación contra los datos del webhook

def _resultado(esperado: dict, leido: dict) -> dict:
    discrepancias = [f"{nombre}: esperado {esperado[nombre]}, leído {leido.get(nombre, 'nada')}"
                     for nombre in esperado if leido.get(nombre) != esperado[nombre]]
    return {"esperados": len(esperado), "coinciden": len(esperado) - len(discrepancias),
            "discrepancias": discrepancias, "ok": not discrepancias}


def validar_tarifario(texto: str) -> dict:
    """Pares médico -> precio leídos de D2 frente a webhook/datos.py."""
    leido = {}
    for linea in normalizar_para_regex(texto).splitlines():
        medico, importe = identificar_medico(linea), IMPORTE.search(linea)
        if medico and importe:
            leido[medico.nombre] = int(importe.group(1) or importe.group(2))
    return _resultado({m.nombre: m.precio_usd for m in MEDICOS}, leido)


def validar_horarios(texto: str) -> dict:
    """Pares médico -> {(días, apertura, cierre)} leídos de D3 frente a webhook/datos.py."""
    leido: dict[str, set] = {}
    for linea in normalizar_para_regex(texto).splitlines():
        medico, horario = identificar_medico(linea), HORARIO.search(linea)
        if medico and horario:
            h1, m1, h2, m2 = horario.groups()
            franja = (frozenset(leer_dias(linea)), f"{int(h1)}:{m1}", f"{int(h2)}:{m2}")
            leido.setdefault(medico.nombre, set()).add(franja)

    esperado = {}
    for m in MEDICOS:
        franjas: dict[tuple, set] = {}
        for dia, (abre, cierra) in m.horario.items():
            franjas.setdefault((f"{abre.hour}:{abre.minute:02d}", f"{cierra.hour}:{cierra.minute:02d}"), set()).add(dia)
        esperado[m.nombre] = {(frozenset(d), a, c) for (a, c), d in franjas.items()}
    return _resultado(esperado, leido)
