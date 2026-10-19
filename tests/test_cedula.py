"""Regex de la cédula en el webhook (spec 03, R2.1 y R2.2)."""

import pytest

from webhook.cedula import inferir_nacionalidad, solo_digitos, validar


@pytest.mark.parametrize("valor, nacionalidad, esperado", [
    ("14523987", "V", "V-14523987"),
    ("14.523.987", "V", "V-14523987"),
    ("14 523 987", "V", "V-14523987"),
    ("14,523,987", "V", "V-14523987"),
    ("V-14523987", "V", "V-14523987"),
    ("945123", "V", "V-945123"),
    ("81234567", "E", "E-81234567"),
    ("123456789", "E", "E-123456789"),
    ("14523987", "", "14523987"),
])
def test_cedula_valida(valor, nacionalidad, esperado):
    assert validar(valor, nacionalidad) == (esperado, "")


@pytest.mark.parametrize("valor, nacionalidad, motivo", [
    ("1234", "V", "entre 6 y 8 cifras"),
    ("123456789", "V", "entre 6 y 8 cifras"),
    ("0123456", "V", "cero"),
    ("12345", "E", "entre 6 y 9 cifras"),
    ("1234567890", "E", "entre 6 y 9 cifras"),
    ("", "V", "No he entendido"),
])
def test_cedula_invalida(valor, nacionalidad, motivo):
    cedula, explicacion = validar(valor, nacionalidad)
    assert cedula is None
    assert motivo in explicacion


def test_solo_digitos():
    assert solo_digitos("mi cédula es V-14.523.987") == "14523987"


@pytest.mark.parametrize("texto, esperado", [
    ("venezolana", "V"),
    ("soy venezolano", "V"),
    ("de Venezuela", "V"),
    ("soy de aquí", "V"),
    ("soy de Noruega", "E"),
    ("noruego", "E"),
    ("soy extranjera", "E"),
    ("canadiense", "E"),
    ("no sé", None),
    ("no lo sé", None),
    ("hola", None),
])
def test_inferir_nacionalidad(texto, esperado):
    assert inferir_nacionalidad(texto) == esperado
