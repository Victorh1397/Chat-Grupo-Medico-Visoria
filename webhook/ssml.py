"""
Texto -> SSML para que Vicky suene natural por voz (spec 06, R3).

Verificado con Dialogflow ES (spec 06, T1): el TTS solo interpreta el SSML si va envuelto en <speak>;
sin él, las etiquetas no se aplican. Solo se usa en el canal de voz.
"""

import re
from xml.sax.saxutils import escape, unescape

PAUSA_FRASES = '<break time="250ms"/>'
PAUSA_CIFRAS = '<break time="150ms"/>'

CODIGO = re.compile(r"\b(CIT|VIS)-(\d{5})\b")
# 6-9 cifras seguidas que no formen parte de otro número ("10:00", "1.234", "2026")
CEDULA = re.compile(r"(?<!\d)(?<!\d[.,:])(\d{6,9})(?!\d)(?![.,:]\d)")
FIN_DE_FRASE = re.compile(r"([.?!])\s+")
ETIQUETA = re.compile(r"<[^>]+>")


def _caracteres(texto: str) -> str:
    return f'<say-as interpret-as="characters">{texto}</say-as>'


def _cedula_por_grupos(m: re.Match) -> str:
    """'14523987' -> '14 · 523 · 987' con pausas: "catorce, quinientos veintitrés, novecientos ochenta y siete"."""
    numero = m.group(1)
    grupos = []
    while numero:
        grupos.insert(0, numero[-3:])
        numero = numero[:-3]
    return PAUSA_CIFRAS.join(grupos)


def a_ssml(texto: str) -> str:
    ssml = escape(texto)
    # "CIT-48213" -> "C I T, cuatro ocho dos uno tres"
    ssml = CODIGO.sub(lambda m: f"{_caracteres(m.group(1))}, {_caracteres(m.group(2))}", ssml)
    ssml = CEDULA.sub(_cedula_por_grupos, ssml)
    ssml = FIN_DE_FRASE.sub(rf"\1{PAUSA_FRASES}", ssml)
    return f"<speak>{ssml}</speak>"


def sin_etiquetas(ssml: str) -> str:
    """SSML -> texto legible (para mostrar en pantalla lo que dice Vicky)."""
    codigo = r'<say-as interpret-as="characters">([A-Z]+)</say-as>, <say-as interpret-as="characters">(\d+)</say-as>'
    texto = re.sub(codigo, r"\1-\2", ssml)  # en pantalla, el código como se escribe: CIT-48213
    texto = ETIQUETA.sub(lambda m: " " if "break" in m.group() else "", texto)
    return " ".join(unescape(texto).split())
