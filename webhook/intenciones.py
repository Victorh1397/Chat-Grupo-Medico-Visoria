"""Un manejador por intención de Dialogflow. Cada uno recibe la petición y devuelve la respuesta."""

import re
from collections.abc import Callable

from webhook import textos
from webhook.agenda import Agenda, Propuesta, codigo_caso
from webhook.cedula import (
    es_respuesta_de_nacionalidad,
    inferir_nacionalidad,
    normalizar_nacionalidad,
    solo_digitos,
    validar,
)
from webhook.datos import medico_por_nombre, medicos_de
from webhook.dialogflow import PeticionDF, evento, leer_fecha, leer_hora, repreguntar, texto

agenda = Agenda()

# Dato que Dialogflow iba a preguntar tras el turno anterior, por sesión. Los contextos de la petición
# indican lo que se preguntará DESPUÉS de este turno; para saber a qué pregunta respondió el usuario
# hace falta recordar el turno anterior.
pregunta_anterior: dict[str, str] = {}

# Orden de recogida de agendar_cita (spec 02) y la pregunta de cada dato
PREGUNTAS = {
    "nombre": "¿Me indica su nombre y apellido, por favor?",
    "apellido": "¿Me indica también su apellido?",
    "nacionalidad": "¿Usted es venezolano o extranjero?",
    "cedula": "¿Me indica su número de cédula?",
    "especialidad": "¿Con qué especialidad desea la cita?",
    "fecha": "¿Para qué fecha desea la cita?",
    "hora": "¿A qué hora le conviene?",
}

PREFIJO_NOMBRE = re.compile(r"^(?:me llamo|mi nombre es|soy|es)\s+", re.IGNORECASE)
PALABRA_NOMBRE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+")
NO_SON_NOMBRES = {"quiero", "necesito", "cita", "cancelar", "no", "si", "sí", "hola", "gracias",
                  "venezolano", "venezolana", "extranjero", "extranjera"}

CIERRE = re.compile(r"^(no|no,? gracias|nada m[aá]s|eso es todo|es todo)[.!]*$", re.IGNORECASE)


# agendar_cita

def agendar_cita(pet: PeticionDF) -> dict:
    respondio_a = pregunta_anterior.pop(pet.sesion, "")
    respuesta = _agendar_cita(pet, respondio_a)
    siguiente = _esperando_en(respuesta) or ("" if respuesta else pet.esperando())
    if siguiente:
        pregunta_anterior[pet.sesion] = siguiente
    return respuesta


def _esperando_en(respuesta: dict) -> str:
    for c in respuesta.get("outputContexts", []):
        nombre = c["name"].rsplit("/", 1)[-1]
        if "_dialog_params_" in nombre and c.get("lifespanCount", 0) > 0:
            return nombre.split("_dialog_params_", 1)[1]
    return ""


def _palabras_de_nombre(texto: str) -> list[str]:
    """'me llamo Yusmary del Valle' -> ['Yusmary', 'Del', 'Valle']; [] si no parece un nombre."""
    palabras = PREFIJO_NOMBRE.sub("", texto.strip().rstrip(".")).split()
    if not 1 <= len(palabras) <= 4 or not all(PALABRA_NOMBRE.fullmatch(p) for p in palabras):
        return []
    if any(p.lower() in NO_SON_NOMBRES for p in palabras):
        return []
    return [p.capitalize() for p in palabras]


def _corregir(pet: PeticionDF, cambios: dict, motivo: str = "", pregunta: str = "") -> dict:
    """
    Aplica `cambios` (fijar o vaciar datos) y pregunta el primer dato que falte en el orden de la recogida.
    Si el dato rechazado va después de otros que aún faltan (p. ej. una hora dicha en la primera frase,
    antes de dar la cédula), se explica el motivo pero se sigue preguntando en orden.
    """
    valores = {p: pet.parametro(p) for p in PREGUNTAS}
    valores["nacionalidad"] = normalizar_nacionalidad(valores["nacionalidad"])
    valores.update(cambios)
    faltante = next((p for p in PREGUNTAS if not valores[p]), None)
    if not faltante:
        return {}
    texto_pregunta = pregunta if pregunta and faltante in cambios else PREGUNTAS[faltante]
    return repreguntar(pet, faltante, f"{motivo} {texto_pregunta}".strip(), cambios)


def _agendar_cita(pet: PeticionDF, respondio_a: str) -> dict:
    texto_usuario = pet.texto.strip()

    # 0. Nombre o apellido que @sys.given-name / @sys.last-name no reconocieron (nombres poco comunes)
    if respondio_a == "nombre" and not pet.parametro("apellido"):
        palabras = _palabras_de_nombre(texto_usuario)
        if len(palabras) >= 2 or (palabras and not pet.parametro("nombre")):
            cambios = {} if pet.parametro("nombre") else {"nombre": palabras[0]}
            if len(palabras) >= 2:
                cambios["apellido"] = " ".join(palabras[1:])
            return _corregir(pet, cambios)
    if respondio_a == "apellido" and not pet.parametro("apellido"):
        palabras = _palabras_de_nombre(texto_usuario)
        if palabras:
            return _corregir(pet, {"apellido": " ".join(palabras)})

    # 1. Nacionalidad: valor que no es V/E (p. ej. un número) o respuesta que la entidad no reconoció
    nacionalidad = normalizar_nacionalidad(pet.parametro("nacionalidad"))
    if pet.parametro("nacionalidad") and not nacionalidad:
        return _corregir(pet, {"nacionalidad": ""}, "Disculpe, no le entendí.")
    # Si el turno anterior se perdió (p. ej. por tiempo agotado), no se sabe a qué pregunta respondió el
    # usuario: solo se interviene ante una respuesta inequívoca ("soy de Noruega", "extranjera").
    respondio_nacionalidad = respondio_a == "nacionalidad" or (
        not respondio_a and pet.esperando() == "nacionalidad" and es_respuesta_de_nacionalidad(texto_usuario))
    if not nacionalidad and respondio_nacionalidad and texto_usuario:
        inferida = inferir_nacionalidad(texto_usuario)
        if not inferida:
            return _corregir(pet, {"nacionalidad": ""}, "Disculpe, no le entendí.")
        return _corregir(pet, {"nacionalidad": inferida})

    # 2. Cédula: validación con regex según V/E
    cedula = ""
    if pet.parametro("cedula"):
        cedula, motivo = validar(pet.parametro("cedula"), nacionalidad)
        if not cedula:
            return _corregir(pet, {"cedula": ""}, motivo)

    especialidad = pet.parametro("especialidad")
    paciente = agenda.paciente(cedula) if nacionalidad and cedula else None
    preferido = agenda.medico_habitual(paciente, especialidad)

    # 3. Fecha
    dia = leer_fecha(pet.parametro("fecha")) if pet.parametro("fecha") else None
    if pet.parametro("fecha") and not dia:
        return _corregir(pet, {"fecha": "", "hora": ""}, "Necesito un día concreto.")
    if dia and especialidad:
        motivo = agenda.validar_fecha(especialidad, dia)
        if motivo:
            return _corregir(pet, {"fecha": "", "hora": ""}, motivo, "¿Qué otro día le conviene?")

    # 4. Hora
    medico = inicio = None
    hora = leer_hora(pet.parametro("hora")) if pet.parametro("hora") else None
    if pet.parametro("hora") and not hora:
        return _corregir(pet, {"hora": ""}, "Necesito una hora concreta.")
    if hora and dia and especialidad:
        medico, inicio, motivo = agenda.validar_hora(especialidad, dia, hora, preferido)
        if motivo:
            return _corregir(pet, {"hora": ""}, motivo)

    if not pet.todos_los_datos or not medico:
        return {}

    # 5. Propuesta con los 7 datos válidos
    nombre = paciente.nombre if paciente else pet.parametro("nombre")
    apellido = paciente.apellido if paciente else pet.parametro("apellido")
    agenda.proponer(pet.sesion, Propuesta(cedula, nombre, apellido, medico, inicio))

    quien = textos.doctor(medico.titulo, medico.nombre)
    esp = textos.especialidad(especialidad)
    cuando = textos.fecha_hora(inicio)
    if preferido and preferido == medico:
        pronombre = "ella" if medico.titulo == "Dra." else "él"
        inicio_frase = (f"{nombre}, veo que ya se atendió en {esp} con {quien}. "
                        f"Le propongo cita con {pronombre} {cuando}.")
    elif preferido:
        habitual = textos.doctor(preferido.titulo, preferido.nombre)
        inicio_frase = (f"{nombre}, {habitual}, que le atendió en {esp}, no tiene disponibilidad a esa hora. "
                        f"Le propongo cita con {quien} {cuando}.")
    else:
        inicio_frase = f"{nombre}, le propongo cita de {esp} con {quien} {cuando}."
    return texto(f"{inicio_frase} La consulta cuesta {medico.precio_usd} dólares. ¿Confirmo la cita?")


def agendar_cita_si(pet: PeticionDF) -> dict:
    cita = agenda.confirmar(pet.sesion)
    if not cita:
        return texto("No tengo ninguna cita pendiente de confirmar. ¿Desea agendar una nueva cita?")
    quien = textos.doctor(cita.medico.titulo, cita.medico.nombre)
    return texto(f"Listo, {cita.nombre}. Su cita {cita.codigo} con {quien} "
                 f"está confirmada para {textos.fecha_hora(cita.inicio)}. Le recomendamos llegar 15 minutos antes. "
                 "¿Le puedo ayudar en algo más?")


def agendar_cita_empezar_de_nuevo(pet: PeticionDF) -> dict:
    agenda.descartar(pet.sesion)
    return evento("INICIAR_CITA")


# Otras intenciones

def consultar_horarios(pet: PeticionDF) -> dict:
    especialidad = pet.parametro("especialidad")
    medicos = medicos_de(especialidad)
    if not medicos:
        return texto("No conozco esa especialidad. Atendemos dermatología, endocrinología, cirugía plástica, "
                     "urología, cardiología y oftalmología.")
    partes = []
    for m in medicos:
        franjas = {}
        for dia, (abre, cierra) in m.horario.items():
            franjas.setdefault((abre, cierra), []).append(dia)
        horario = textos.unir([f"{textos.dias(d)} de {textos.hora(a)} a {textos.hora(c)}"
                               for (a, c), d in franjas.items()])
        partes.append(f"{textos.doctor(m.titulo, m.nombre)} {horario}")
    return texto(f"En {textos.especialidad(especialidad)} atienden {textos.unir(partes)}.")


def consultar_historial(pet: PeticionDF) -> dict:
    numero = solo_digitos(pet.parametro("cedula"))
    paciente = agenda.paciente_por_numero(numero)
    if not paciente:
        return texto(f"No encuentro ningún paciente con la cédula {numero}. ¿Desea agendar una cita?")

    previas = sorted(paciente.historial, key=lambda c: c.fecha, reverse=True)
    if previas:
        consultas = []
        for c in previas:
            medico = medico_por_nombre(c.medico)
            consultas.append(f"{textos.especialidad(c.especialidad)} con {textos.doctor(medico.titulo, medico.nombre)} "
                             f"el {textos.fecha(c.fecha, con_anio=True)}")
        consultas = textos.unir(consultas)
        mensaje = f"{paciente.nombre}, sus consultas anteriores son: {consultas}."
    else:
        mensaje = f"{paciente.nombre}, todavía no tiene consultas anteriores en la clínica."

    pendientes = agenda.pendientes(paciente.cedula)
    if pendientes:
        citas = textos.unir([f"{textos.especialidad(c.medico.especialidad)} {textos.fecha_hora(c.inicio)}"
                             for c in pendientes])
        mensaje += f" Además tiene pendiente: {citas}."
    return texto(mensaje)


def cancelar_cita(pet: PeticionDF) -> dict:
    numero = solo_digitos(pet.parametro("cedula"))
    paciente = agenda.paciente_por_numero(numero)
    if not paciente:
        return texto(f"No encuentro ningún paciente con la cédula {numero}.")
    cita = agenda.cancelar_proxima(paciente.cedula)
    if not cita:
        return texto(f"{paciente.nombre}, no tiene citas pendientes que cancelar.")
    return texto(f"Listo, {paciente.nombre}. He cancelado su cita {cita.codigo} de "
                 f"{textos.especialidad(cita.medico.especialidad)} con "
                 f"{textos.doctor(cita.medico.titulo, cita.medico.nombre)} {textos.fecha_hora(cita.inicio)}.")


def transferir_humano(pet: PeticionDF) -> dict:
    return texto(f"Le comunico con recepción. Su número de caso es {codigo_caso()}. Por favor, espere un momento.")


def consulta_documental(pet: PeticionDF) -> dict:
    # Provisional hasta la spec 05 (documentos OCR + Gemini)
    return texto("En este momento no puedo consultar esa información. ¿Desea que le comunique con recepción?")


def fallback(pet: PeticionDF) -> dict:
    if CIERRE.match(pet.texto.strip()):
        return texto("Gracias por comunicarse con Grupo Médico Visoria. Que tenga un buen día.")
    return texto("Disculpe, no le entendí. Puedo agendarle una cita, consultar horarios o su historial, "
                 "o responder sus dudas sobre la clínica.")


MANEJADORES: dict[str, Callable[[PeticionDF], dict]] = {
    "agendar_cita": agendar_cita,
    "agendar_cita - yes": agendar_cita_si,
    "agendar_cita - no - yes": agendar_cita_empezar_de_nuevo,
    "consultar_horarios": consultar_horarios,
    "consultar_historial": consultar_historial,
    "cancelar_cita": cancelar_cita,
    "transferir_humano": transferir_humano,
    "consulta_documental": consulta_documental,
    "Default Fallback Intent": fallback,
}
