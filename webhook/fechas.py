"""
Lectura de fechas de respaldo (spec 08, T7).

La entidad de sistema @sys.date de Dialogflow a veces no reconoce una fecha que sí entiende escrita de otra forma
("Para el 29 de octubre" falló; "29 de octubre" no). Si el usuario respondió a "¿Para qué fecha…?" y el dato llegó
vacío, el webhook intenta leerla del texto con expresiones regulares.
"""

import re
import unicodedata
from datetime import date, timedelta

MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
         "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
DIAS = {"lunes": 0, "martes": 1, "miercoles": 2, "jueves": 3, "viernes": 4, "sabado": 5, "domingo": 6}

DIA_DE_MES = re.compile(r"\b(\d{1,2}|primero)\s+de\s+(" + "|".join(MESES) + r")(?:\s+(?:de|del)\s+(\d{4}))?\b")
NUMERICA = re.compile(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2}|\d{4}))?\b")
DIA_SEMANA = re.compile(r"\b(" + "|".join(DIAS) + r")\b")
PASADO_MANANA = re.compile(r"\bpasado manana\b")
MANANA = re.compile(r"(?<!la )\bmanana\b")  # "mañana", pero no "de la mañana" / "por la mañana"
HOY = re.compile(r"\bhoy\b")


def _plano(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def _proxima(dia: int, mes: int, anio: int | None, hoy: date) -> date | None:
    """La fecha indicada; sin año, la próxima vez que llegue (el 5 de enero dicho en octubre es del año siguiente)."""
    try:
        fecha = date(anio or hoy.year, mes, dia)
    except ValueError:
        return None
    if anio is None and fecha < hoy:
        fecha = fecha.replace(year=fecha.year + 1)
    return fecha


def leer_fecha_texto(texto: str, hoy: date) -> date | None:
    plano = _plano(texto)

    if m := DIA_DE_MES.search(plano):
        dia = 1 if m.group(1) == "primero" else int(m.group(1))
        return _proxima(dia, MESES[m.group(2)], int(m.group(3)) if m.group(3) else None, hoy)

    if m := NUMERICA.search(plano):
        anio = m.group(3)
        anio = (2000 + int(anio) if len(anio) == 2 else int(anio)) if anio else None
        return _proxima(int(m.group(1)), int(m.group(2)), anio, hoy)

    if PASADO_MANANA.search(plano):
        return hoy + timedelta(days=2)
    if MANANA.search(plano):
        return hoy + timedelta(days=1)
    if HOY.search(plano):
        return hoy

    if m := DIA_SEMANA.search(plano):
        # "el martes" / "el próximo martes": el siguiente martes a partir de mañana
        return hoy + timedelta(days=(DIAS[m.group(1)] - hoy.weekday()) % 7 or 7)
    return None


def como_dialogflow(fecha: date) -> str:
    """Mismo formato que @sys.date: '2026-10-29T12:00:00-04:00'."""
    return f"{fecha.isoformat()}T12:00:00-04:00"
