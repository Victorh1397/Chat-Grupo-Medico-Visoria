"""Formato de textos pensados para ser leídos en voz alta."""

from datetime import date, datetime, time

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
DIAS_PLURAL = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábados", "domingos"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def unir(elementos: list[str]) -> str:
    """['a', 'b', 'c'] -> 'a, b y c'."""
    elementos = list(elementos)
    if len(elementos) <= 1:
        return "".join(elementos)
    return ", ".join(elementos[:-1]) + " y " + elementos[-1]


def hora(h: time) -> str:
    return f"{h.hour}:{h.minute:02d}"


def fecha(d: date, con_anio: bool = False) -> str:
    """'martes 20 de octubre' (o '12 de marzo de 2026' con año)."""
    if con_anio:
        return f"{d.day} de {MESES[d.month - 1]} de {d.year}"
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]}"


def fecha_hora(dt: datetime) -> str:
    """'el martes 20 de octubre a las 10:00'."""
    return f"el {fecha(dt.date())} a las {hora(dt.time())}"


def doctor(titulo: str, nombre: str) -> str:
    """('Dra.', 'Laura Rojas') -> 'la doctora Laura Rojas'."""
    return f"la doctora {nombre}" if titulo == "Dra." else f"el doctor {nombre}"


def dias(dias_semana: list[int]) -> str:
    """[1, 3] -> 'los martes y jueves'; [0, 1, 2] -> 'de lunes a miércoles'."""
    dias_semana = sorted(dias_semana)
    consecutivos = len(dias_semana) >= 3 and dias_semana == list(range(dias_semana[0], dias_semana[-1] + 1))
    if consecutivos:
        return f"de {DIAS[dias_semana[0]]} a {DIAS[dias_semana[-1]]}"
    return "los " + unir([DIAS_PLURAL[d] for d in dias_semana])


def especialidad(nombre: str) -> str:
    """Las especialidades se nombran en minúscula dentro de una frase."""
    return nombre.lower()
