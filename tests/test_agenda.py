"""Reglas de agenda (spec 03, R2.4, R2.5, R3 y R4). "Hoy" es el domingo 18/10/2026 a las 10:00."""

from datetime import date, datetime, time

from webhook.agenda import CARACAS, Propuesta
from webhook.datos import medico_por_nombre

MARTES = date(2026, 10, 20)


def test_fecha_pasada_domingo_y_dia_sin_especialidad(entorno):
    assert "ya pasó" in entorno.validar_fecha("Dermatología", date(2026, 10, 15))
    assert "domingos" in entorno.validar_fecha("Dermatología", date(2026, 10, 25))
    motivo = entorno.validar_fecha("Urología", date(2026, 10, 19))  # lunes: urología atiende mar, vie y sáb
    assert "los martes, viernes y sábados" in motivo
    assert entorno.validar_fecha("Dermatología", MARTES) == ""


def test_hora_dentro_del_horario_prefiere_el_medico_habitual(entorno):
    maria = entorno.paciente("V-14523987")
    preferido = entorno.medico_habitual(maria, "Dermatología")
    assert preferido.nombre == "Laura Rojas"
    medico, inicio, motivo = entorno.validar_hora("Dermatología", MARTES, time(10, 0), preferido)
    assert (medico.nombre, inicio.time(), motivo) == ("Laura Rojas", time(10, 0), "")


def test_hora_fuera_de_horario_indica_la_franja(entorno):
    medico, _, motivo = entorno.validar_hora("Dermatología", MARTES, time(16, 0))
    assert medico is None
    assert "la doctora Laura Rojas de 8:00 a 12:00" in motivo


def test_hora_ambigua_se_pasa_a_la_tarde_y_se_redondea(entorno):
    # Ortega atiende endocrinología los martes de 14:00 a 18:00
    medico, inicio, _ = entorno.validar_hora("Endocrinología", MARTES, time(3, 40))
    assert medico.nombre == "Rafael Ortega"
    assert inicio.time() == time(15, 30)


def test_hora_ocupada_propone_el_siguiente_bloque(entorno):
    # La cita sembrada de Miguel Torres ocupa a Ortega el martes a las 15:00
    medico, _, motivo = entorno.validar_hora("Endocrinología", MARTES, time(15, 0))
    assert medico is None
    assert "siguiente horario libre es a las 15:30" in motivo


def test_confirmar_registra_y_evita_doble_reserva(entorno):
    rojas = medico_por_nombre("Laura Rojas")
    inicio = datetime(2026, 10, 20, 10, 0, tzinfo=CARACAS)
    entorno.proponer("s1", Propuesta("V-30111222", "Nuevo", "Paciente", rojas, inicio))
    cita = entorno.confirmar("s1")
    assert cita.codigo.startswith("CIT-") and len(cita.codigo) == 9
    assert entorno.paciente("V-30111222").nombre == "Nuevo"
    medico, _, motivo = entorno.validar_hora("Dermatología", MARTES, time(10, 0), rojas)
    assert medico is None and "10:30" in motivo
    assert entorno.confirmar("s1") is None  # la propuesta ya se usó


def test_cancelar_la_cita_sembrada(entorno):
    cita = entorno.cancelar_proxima("V-25678901")
    assert cita.codigo == "CIT-10234"
    assert cita.inicio == datetime(2026, 10, 20, 15, 0, tzinfo=CARACAS)
    assert entorno.cancelar_proxima("V-25678901") is None


def test_buscar_paciente_por_numero_sin_letra(entorno):
    assert entorno.paciente_por_numero("81.234.567").nombre == "Carlos"
    assert entorno.paciente_por_numero("11111111") is None
