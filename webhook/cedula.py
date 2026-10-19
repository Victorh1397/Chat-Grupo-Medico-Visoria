"""
Cédula de identidad venezolana: normalización y validación con expresiones regulares.

La entidad regex @cedula de Dialogflow solo EXTRAE el número (formato). Aquí se VALIDA con las
reglas de negocio, que dependen de la nacionalidad que Dialogflow no conoce al extraer:
    V (venezolano): 6 a 8 dígitos      E (extranjero): 6 a 9 dígitos      nunca empieza por 0
"""

import re

PATRON_CEDULA = {
    "V": re.compile(r"^[1-9]\d{5,7}$"),
    "E": re.compile(r"^[1-9]\d{5,8}$"),
}
# Sin nacionalidad conocida todavía: el rango más amplio
PATRON_CEDULA_GENERICO = PATRON_CEDULA["E"]

NO_DIGITO = re.compile(r"\D")


def solo_digitos(valor: str) -> str:
    """'V-14.523.987', '14 523 987', 'mi cédula es 14523987' -> '14523987'."""
    return NO_DIGITO.sub("", str(valor))


def validar(valor: str, nacionalidad: str = "") -> tuple[str | None, str]:
    """
    Devuelve (cédula canónica, "") si es válida, o (None, motivo) si no lo es.
    Sin nacionalidad devuelve el número sin letra ("14523987").
    """
    numero = solo_digitos(valor)
    nacionalidad = nacionalidad.upper()
    patron = PATRON_CEDULA.get(nacionalidad, PATRON_CEDULA_GENERICO)

    if patron.match(numero):
        return (f"{nacionalidad}-{numero}" if nacionalidad in PATRON_CEDULA else numero), ""

    if not numero:
        motivo = "No he entendido el número de cédula."
    elif numero.startswith("0"):
        motivo = "El número de cédula no puede empezar por cero."
    elif nacionalidad == "V":
        motivo = "La cédula de un venezolano tiene entre 6 y 8 cifras."
    else:
        motivo = "El número de cédula debe tener entre 6 y 9 cifras."
    return None, motivo


# Nacionalidad a partir de texto libre (cuando la entidad @nacionalidad no la reconoce)

VENEZOLANO = re.compile(r"\bvenezolan[oa]s?\b|\bvenezuela\b|\bde aqu[ií]\b", re.IGNORECASE)
EXTRANJERO = re.compile(
    r"\bextranjer[oa]s?\b"
    r"|\bsoy de\b|\bvengo de\b|\bnac[ií] en\b"
    r"|\b\w{3,}(?:ano|ana|ense|eño|eña|és|esa|ino|ina|ego|ega)\b",
    re.IGNORECASE,
)
DUDA = re.compile(r"\bno s[eé]\b|\bno lo s[eé]\b|\bprefiero no\b|\bninguna?\b", re.IGNORECASE)


def inferir_nacionalidad(texto: str) -> str | None:
    """'soy de Noruega' -> 'E'; 'venezolana' -> 'V'; 'no sé' -> None (volver a preguntar)."""
    if DUDA.search(texto):
        return None
    if VENEZOLANO.search(texto):
        return "V"
    if EXTRANJERO.search(texto):
        return "E"
    return None
