"""Endpoint /webhook con peticiones de ejemplo de Dialogflow (criterios de aceptación de la spec 03)."""

import re
import time
from datetime import datetime, timedelta

import pytest

from tests.conftest import DEJA_A_DIALOGFLOW, datos_cita, peticion
from webhook.agenda import CARACAS, Propuesta
from webhook.datos import medico_por_nombre


def respuesta(cliente, cuerpo) -> dict:
    r = cliente.post("/webhook", json=cuerpo)
    assert r.status_code == 200
    return r.json()


def esperando(res: dict) -> str:
    """Parámetro que el webhook pide volver a preguntar."""
    for c in res.get("outputContexts", []):
        nombre = c["name"].rsplit("/", 1)[-1]
        if "_dialog_params_" in nombre and c["lifespanCount"] > 0:
            return nombre.split("_dialog_params_")[1]
    return ""


def parametros_devueltos(res: dict) -> dict:
    return next(c["parameters"] for c in res["outputContexts"] if c["name"].endswith("agendar_cita_dialog_context"))


# CA-1: token

def test_ca1_sin_token_401(cliente):
    from fastapi.testclient import TestClient

    from webhook.main import app

    assert TestClient(app).post("/webhook", json=peticion("transferir_humano")).status_code == 401
    assert TestClient(app, headers={"X-Visoria-Token": "otro"}).post(
        "/webhook", json=peticion("transferir_humano")).status_code == 401


def test_estado(cliente):
    assert cliente.get("/").json()["estado"] == "ok"


# CA-2: cédula durante la recogida

def test_ca2_cedula_invalida_se_vuelve_a_pedir(cliente):
    params = datos_cita(cedula="123456789", especialidad="", fecha="", hora="")
    res = respuesta(cliente, peticion("agendar_cita", params, "123456789", todos=False, esperando="cedula"))
    assert "entre 6 y 8 cifras" in res["fulfillmentText"]
    assert esperando(res) == "cedula"
    assert parametros_devueltos(res)["cedula"] == ""


def test_ca2_cedula_valida_deja_seguir_a_dialogflow(cliente):
    params = datos_cita(especialidad="", fecha="", hora="")
    assert respuesta(cliente, peticion("agendar_cita", params, "14.523.987", todos=False,
                                       esperando="cedula")) == DEJA_A_DIALOGFLOW


# CA-3: nacionalidad no reconocida

SIN_NACIONALIDAD = {"nombre": "Ana", "apellido": "Rodríguez", "nacionalidad": "", "cedula": "",
                    "especialidad": "", "fecha": "", "hora": ""}


def test_ca3_al_dar_el_nombre_no_se_interpreta_como_nacionalidad(cliente):
    # Tras "Ana Rodríguez", Dialogflow va a preguntar la nacionalidad: el webhook no debe intervenir
    res = respuesta(cliente, peticion("agendar_cita", SIN_NACIONALIDAD, "Ana Rodríguez", todos=False,
                                      esperando="nacionalidad"))
    assert res == DEJA_A_DIALOGFLOW


def test_ca3_otra_nacionalidad_es_e_y_pide_la_cedula(cliente):
    respuesta(cliente, peticion("agendar_cita", SIN_NACIONALIDAD, "Ana Rodríguez", todos=False,
                                esperando="nacionalidad"))
    res = respuesta(cliente, peticion("agendar_cita", SIN_NACIONALIDAD, "soy de Noruega", todos=False,
                                      esperando="nacionalidad"))
    assert parametros_devueltos(res)["nacionalidad"] == "E"
    assert esperando(res) == "cedula"
    assert "cédula" in res["fulfillmentText"]


def test_ca3_no_se_repite_la_pregunta(cliente):
    respuesta(cliente, peticion("agendar_cita", SIN_NACIONALIDAD, "Ana Rodríguez", todos=False,
                                esperando="nacionalidad"))
    res = respuesta(cliente, peticion("agendar_cita", SIN_NACIONALIDAD, "no sé", todos=False,
                                      esperando="nacionalidad"))
    assert esperando(res) == "nacionalidad"
    assert "venezolano o extranjero" in res["fulfillmentText"]


def test_ca3_valor_expandido_por_dialogflow_cuenta_como_e(cliente):
    # Con "automated expansion", Dialogflow devolvió nacionalidad="Noruega" en la prueba real
    params = {**SIN_NACIONALIDAD, "nacionalidad": "Noruega", "cedula": "123456789"}
    assert respuesta(cliente, peticion("agendar_cita", params, "123456789", todos=False,
                                       esperando="especialidad")) == DEJA_A_DIALOGFLOW


# CA-4: fecha y hora

def test_ca4_domingo_se_rechaza(cliente):
    params = datos_cita(fecha="2026-10-25T12:00:00-04:00", hora="")
    res = respuesta(cliente, peticion("agendar_cita", params, "el domingo", todos=False, esperando="fecha"))
    assert "domingos" in res["fulfillmentText"]
    assert esperando(res) == "fecha"


def test_ca4_hora_fuera_de_horario_en_el_turno_final(cliente):
    res = respuesta(cliente, peticion("agendar_cita", datos_cita(hora="2026-10-18T17:00:00-04:00"), "a las 5"))
    assert "de 8:00 a 12:00" in res["fulfillmentText"]
    assert esperando(res) == "hora"
    cerrados = {c["name"].rsplit("/", 1)[-1] for c in res["outputContexts"] if c["lifespanCount"] == 0}
    assert {"ctx_cita_en_curso", "agendar_cita-followup"} <= cerrados


# CA-5 y CA-6: propuesta y confirmación

def test_ca5_conversacion_modelo(cliente):
    res = respuesta(cliente, peticion("agendar_cita", datos_cita(), "a las 10 de la mañana"))
    assert res["fulfillmentText"] == (
        "María, veo que ya se atendió en dermatología con la doctora Laura Rojas. Le propongo cita con ella "
        "el martes 20 de octubre a las 10:00. La consulta cuesta 40 dólares. ¿Confirmo la cita a nombre de "
        "María González, cédula 14523987?")


def test_ca6_confirmar_y_segundo_paciente_recibe_otra_hora(cliente):
    respuesta(cliente, peticion("agendar_cita", datos_cita(), "a las 10"))
    res = respuesta(cliente, peticion("agendar_cita - yes", {}, "sí"))
    assert re.search(r"Su cita CIT-\d{5} con la doctora Laura Rojas está confirmada "
                     r"para el martes 20 de octubre a las 10:00", res["fulfillmentText"])

    otro = datos_cita(nombre="Pedro", apellido="Martínez", cedula="6123456")
    res = respuesta(cliente, peticion("agendar_cita", otro, "a las 10", sesion="projects/p/agent/sessions/otra"))
    assert "siguiente horario libre es a las 10:30" in res["fulfillmentText"]


def test_paciente_nuevo_recibe_propuesta_sin_historial(cliente):
    params = datos_cita(nombre="Laura", apellido="Díaz", cedula="30111222", especialidad="Cardiología",
                        fecha="2026-10-19T12:00:00-04:00", hora="2026-10-18T09:00:00-04:00")
    res = respuesta(cliente, peticion("agendar_cita", params, "a las 9"))
    assert res["fulfillmentText"].startswith("Laura, le propongo cita de cardiología con la doctora Patricia Medina")
    assert "55 dólares" in res["fulfillmentText"]


def test_confirmar_sin_propuesta(cliente):
    res = respuesta(cliente, peticion("agendar_cita - yes", {}, "sí"))
    assert "No tengo ninguna cita pendiente" in res["fulfillmentText"]


# CA-7: reinicio

def test_ca7_empezar_de_nuevo_lanza_el_evento(cliente):
    res = respuesta(cliente, peticion("agendar_cita - no - yes", {}, "sí"))
    assert res == {"followupEventInput": {"name": "INICIAR_CITA", "languageCode": "es"}}


# CA-8 a CA-12: otras intenciones

def test_ca8_horarios_cardiologia(cliente):
    res = respuesta(cliente, peticion("consultar_horarios", {"especialidad": "Cardiología"}, "cardiología"))
    assert res["fulfillmentText"] == (
        "En cardiología atienden la doctora Patricia Medina de lunes a miércoles de 8:00 a 12:00 y "
        "el doctor Eduardo Rangel los jueves y viernes de 14:00 a 18:00.")


def test_horarios_medico_con_dos_franjas(cliente):
    res = respuesta(cliente, peticion("consultar_horarios", {"especialidad": ["Oftalmología"]}, "oftalmología"))
    assert "los martes y jueves de 14:00 a 18:00 y los sábados de 8:00 a 12:00" in res["fulfillmentText"]


def test_ca9_historial(cliente):
    res = respuesta(cliente, peticion("consultar_historial", {"cedula": "14523987"}, "14523987"))
    assert res["fulfillmentText"] == (
        "María, sus consultas anteriores son: dermatología con la doctora Laura Rojas el 12 de marzo de 2026 y "
        "cardiología con la doctora Patricia Medina el 4 de noviembre de 2025.")
    res = respuesta(cliente, peticion("consultar_historial", {"cedula": "11111111"}, "11111111"))
    assert "No encuentro ningún paciente" in res["fulfillmentText"]


def test_historial_incluye_citas_pendientes(cliente):
    res = respuesta(cliente, peticion("consultar_historial", {"cedula": "25678901"}, "25678901"))
    assert "Además tiene pendiente: endocrinología el martes 20 de octubre a las 15:00." in res["fulfillmentText"]


def test_ca10_cancelar_dos_veces(cliente):
    res = respuesta(cliente, peticion("cancelar_cita", {"cedula": "25.678.901"}, "25.678.901"))
    assert res["fulfillmentText"] == (
        "Listo, Miguel. He cancelado su cita CIT-10234 de endocrinología con el doctor Rafael Ortega "
        "el martes 20 de octubre a las 15:00.")
    res = respuesta(cliente, peticion("cancelar_cita", {"cedula": "25678901"}, "25678901"))
    assert "no tiene citas pendientes" in res["fulfillmentText"]


def test_ca11_transferir(cliente):
    res = respuesta(cliente, peticion("transferir_humano", {}, "quiero hablar con una persona"))
    assert re.search(r"caso VIS-\d{5}", res["fulfillmentText"])


@pytest.mark.parametrize("frase", ["no", "No gracias", "nada más", "eso es todo"])
def test_ca12_despedida(cliente, frase):
    res = respuesta(cliente, peticion("Default Fallback Intent", {}, frase))
    assert "Que tenga un buen día" in res["fulfillmentText"]


def test_fallback_sin_informacion_en_los_documentos(cliente):
    res = respuesta(cliente, peticion("Default Fallback Intent", {}, "¿cuál es la capital de Francia?"))
    assert res["fulfillmentText"].startswith("Disculpe, no tengo información sobre eso.")


def test_intencion_desconocida_nunca_en_silencio(cliente):
    assert respuesta(cliente, peticion("intencion_nueva", {}, "hola"))["fulfillmentText"]


def test_error_interno_responde_con_disculpa(cliente, monkeypatch):
    from webhook import intenciones

    def roto(_):
        raise RuntimeError("fallo")

    monkeypatch.setitem(intenciones.MANEJADORES, "transferir_humano", roto)
    assert "problema técnico" in respuesta(cliente, peticion("transferir_humano"))["fulfillmentText"]


# CA-13: tiempo y trato de usted

TUTEO = re.compile(r"\b(tú|tu|te|quieres|puedes|tienes|deseas|necesitas|dime)\b", re.IGNORECASE)


def test_ca13_rapido_y_de_usted(cliente):
    casos = [
        peticion("agendar_cita", datos_cita(), "a las 10"),
        peticion("agendar_cita - yes", {}, "sí"),
        peticion("consultar_horarios", {"especialidad": "Urología"}),
        peticion("consultar_historial", {"cedula": "20345678"}),
        peticion("cancelar_cita", {"cedula": "25678901"}),
        peticion("transferir_humano"),
        peticion("consulta_documental", {}, "¿tienen estacionamiento?"),
        peticion("Default Fallback Intent", {}, "eso es todo"),
        peticion("agendar_cita", datos_cita(cedula="1234", especialidad="", fecha="", hora=""), "1234",
                 todos=False, esperando="cedula"),
    ]
    for cuerpo in casos:
        inicio = time.perf_counter()
        texto = respuesta(cliente, cuerpo).get("fulfillmentText", "")
        assert time.perf_counter() - inicio < 1
        assert not TUTEO.search(texto), texto


# Regresiones de las pruebas end-to-end con Dialogflow real

def test_hora_invalida_en_la_primera_frase_sigue_preguntando_en_orden(cliente):
    # "Soy Carlos Pérez y necesito cita con cardiología el viernes a las 9 de la mañana"
    params = {"nombre": "Carlos", "apellido": "Pérez", "nacionalidad": "", "cedula": "", "especialidad": "Cardiología",
              "fecha": "2026-10-23T12:00:00-04:00", "hora": "2026-10-20T09:00:00-04:00"}
    res = respuesta(cliente, peticion("agendar_cita", params, "Soy Carlos Pérez…", todos=False,
                                      esperando="nacionalidad"))
    assert res["fulfillmentText"] == ("Ese día atiende el doctor Eduardo Rangel de 14:00 a 18:00. "
                                      "¿Usted es venezolano o extranjero?")
    assert esperando(res) == "nacionalidad"
    assert parametros_devueltos(res)["hora"] == ""


def test_numero_tomado_como_nacionalidad_se_vuelve_a_preguntar(cliente):
    params = {**SIN_NACIONALIDAD, "nacionalidad": "81234567"}
    res = respuesta(cliente, peticion("agendar_cita", params, "81234567", todos=False, esperando="cedula"))
    assert esperando(res) == "nacionalidad"
    assert parametros_devueltos(res)["nacionalidad"] == ""


def test_nombre_poco_comun_se_toma_del_texto(cliente):
    vacio = {**SIN_NACIONALIDAD, "nombre": "", "apellido": ""}
    respuesta(cliente, peticion("agendar_cita", vacio, "quiero una cita", todos=False, esperando="nombre"))
    res = respuesta(cliente, peticion("agendar_cita", vacio, "me llamo Yusmary Del Valle", todos=False,
                                      esperando="nombre"))
    devueltos = parametros_devueltos(res)
    assert (devueltos["nombre"], devueltos["apellido"]) == ("Yusmary", "Del Valle")
    assert esperando(res) == "nacionalidad"


def test_apellido_no_reconocido_se_toma_del_texto(cliente):
    params = {**SIN_NACIONALIDAD, "nombre": "José", "apellido": ""}
    respuesta(cliente, peticion("agendar_cita", {**params, "nombre": ""}, "quiero una cita", todos=False,
                                esperando="nombre"))
    res = respuesta(cliente, peticion("agendar_cita", params, "José Rodríguez", todos=False, esperando="apellido"))
    assert parametros_devueltos(res)["apellido"] == "Rodríguez"
    assert esperando(res) == "nacionalidad"


def test_frase_que_no_es_un_nombre_no_se_toma_como_nombre(cliente):
    vacio = {**SIN_NACIONALIDAD, "nombre": "", "apellido": ""}
    respuesta(cliente, peticion("agendar_cita", vacio, "quiero una cita", todos=False, esperando="nombre"))
    assert respuesta(cliente, peticion("agendar_cita", vacio, "quiero cancelar", todos=False,
                                       esperando="nombre")) == DEJA_A_DIALOGFLOW


def test_a_las_9_entendido_como_21_se_corrige(cliente):
    # Dialogflow devolvió 21:00 para "a las 9" (sábado, oftalmología: Arismendi 8:00-12:00)
    params = datos_cita(nombre="Pedro", apellido="Martínez", cedula="6123456", especialidad="Oftalmología",
                        fecha="2026-10-24T12:00:00-04:00", hora="2026-10-19T21:00:00-04:00")
    res = respuesta(cliente, peticion("agendar_cita", params, "a las 9"))
    assert "Le propongo cita con él el sábado 24 de octubre a las 9:00" in res["fulfillmentText"]


def test_nacionalidad_inequivoca_aunque_se_perdiera_el_turno_anterior(cliente):
    # El turno "Ana Rodríguez" agotó el tiempo: el webhook no sabe qué se preguntó, pero "soy de Noruega" es inequívoco
    res = respuesta(cliente, peticion("agendar_cita", SIN_NACIONALIDAD, "soy de Noruega", todos=False,
                                      esperando="nacionalidad"))
    assert parametros_devueltos(res)["nacionalidad"] == "E"
    assert esperando(res) == "cedula"


# Spec 06, R2b: preguntar la hora diciendo la disponibilidad

HASTA_LA_HORA = {"nombre": "Víctor", "apellido": "Méndez", "nacionalidad": "V", "cedula": "30111222",
                 "especialidad": "Cardiología", "fecha": "2026-10-19T12:00:00-04:00", "hora": ""}  # lunes


def test_r2b_pregunta_la_hora_con_la_disponibilidad(cliente):
    res = respuesta(cliente, peticion("agendar_cita", HASTA_LA_HORA, "el lunes", todos=False, esperando="hora"))
    assert res["fulfillmentText"] == ("Ese día atiende la doctora Patricia Medina de 8:00 a 12:00; el primer "
                                      "horario libre es a las 8:00. ¿A qué hora le conviene?")


def test_r2b_sin_hora_concreta_repite_la_disponibilidad(cliente):
    respuesta(cliente, peticion("agendar_cita", HASTA_LA_HORA, "el lunes", todos=False, esperando="hora"))
    res = respuesta(cliente, peticion("agendar_cita", HASTA_LA_HORA, "a cualquier hora en la mañana",
                                      todos=False, esperando="hora"))
    assert res["fulfillmentText"].startswith("Ese día atiende la doctora Patricia Medina")


def test_r2b_primer_horario_libre_salta_los_ocupados(cliente, entorno):
    # Martes de endocrinología: Ortega 14:00-18:00; la cita sembrada de Miguel Torres ocupa las 15:00
    ortega = medico_por_nombre("Rafael Ortega")
    entorno.proponer("otra", Propuesta("V-111111", "A", "B", ortega, datetime(2026, 10, 20, 14, 0, tzinfo=CARACAS)))
    entorno.confirmar("otra")
    params = {**HASTA_LA_HORA, "especialidad": "Endocrinología", "fecha": "2026-10-20T12:00:00-04:00"}
    res = respuesta(cliente, peticion("agendar_cita", params, "el martes", todos=False, esperando="hora"))
    assert "el primer horario libre es a las 14:30" in res["fulfillmentText"]


def test_r2b_sin_horarios_libres_pide_otra_fecha(cliente, entorno):
    rojas = medico_por_nombre("Laura Rojas")
    for i in range(8):  # martes 20/10 de 8:00 a 12:00, ocho bloques
        entorno.proponer(f"s{i}", Propuesta(f"V-1000000{i}", "A", "B", rojas,
                                            datetime(2026, 10, 20, 8, 0, tzinfo=CARACAS) + timedelta(minutes=30 * i)))
        entorno.confirmar(f"s{i}")
    params = {**HASTA_LA_HORA, "especialidad": "Dermatología", "fecha": "2026-10-20T12:00:00-04:00"}
    res = respuesta(cliente, peticion("agendar_cita", params, "el martes", todos=False, esperando="hora"))
    assert res["fulfillmentText"] == ("Ese día ya no quedan horarios libres en dermatología. "
                                      "¿Qué otro día le conviene?")
    assert esperando(res) == "fecha"


def test_r2b_no_interviene_si_aun_faltan_datos_anteriores(cliente):
    params = {**HASTA_LA_HORA, "cedula": ""}
    assert respuesta(cliente, peticion("agendar_cita", params, "venezolano", todos=False,
                                       esperando="cedula")) == DEJA_A_DIALOGFLOW


def test_medico_habitual_que_no_atiende_ese_dia(cliente):
    # Carlos Pérez se atendió con Rangel (jueves y viernes); pide cardiología un martes
    params = datos_cita(nombre="Carlos", apellido="Pérez", nacionalidad="E", cedula="81234567",
                        especialidad="Cardiología", fecha="2026-10-20T12:00:00-04:00", hora="2026-10-18T09:00:00-04:00")
    texto = respuesta(cliente, peticion("agendar_cita", params, "a las 9"))["fulfillmentText"]
    assert "el doctor Eduardo Rangel, que le atendió en cardiología, no atiende ese día" in texto
