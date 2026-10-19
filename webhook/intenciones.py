"""Un manejador por intención de Dialogflow. Cada uno recibe la petición y devuelve la respuesta."""

import re
from collections.abc import Callable

from webhook import textos
from webhook.agenda import Agenda, Propuesta, codigo_caso
from webhook.cedula import inferir_nacionalidad, solo_digitos, validar
from webhook.datos import medico_por_nombre, medicos_de
from webhook.dialogflow import PeticionDF, evento, leer_fecha, leer_hora, repreguntar, texto

agenda = Agenda()

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

CIERRE = re.compile(r"^(no|no,? gracias|nada m[aá]s|eso es todo|es todo)[.!]*$", re.IGNORECASE)


# agendar_cita

def agendar_cita(pet: PeticionDF) -> dict:
    nacionalidad = pet.parametro("nacionalidad")

    # 1. Nacionalidad que la entidad @nacionalidad no reconoció ("soy de Noruega")
    if not nacionalidad and pet.esperando() == "nacionalidad" and pet.texto:
        inferida = inferir_nacionalidad(pet.texto)
        if not inferida:
            return repreguntar(pet, "nacionalidad", "Disculpe, no le entendí. " + PREGUNTAS["nacionalidad"])
        nacionalidad = inferida
        faltante = next((p for p in PREGUNTAS if p != "nacionalidad" and not pet.parametro(p)), "cedula")
        return repreguntar(pet, faltante, PREGUNTAS[faltante], {"nacionalidad": inferida})

    # 2. Cédula: validación con regex según V/E
    cedula = ""
    if pet.parametro("cedula"):
        cedula, motivo = validar(pet.parametro("cedula"), nacionalidad)
        if not cedula:
            return repreguntar(pet, "cedula", f"{motivo} {PREGUNTAS['cedula']}")

    especialidad = pet.parametro("especialidad")
    paciente = agenda.paciente(cedula) if nacionalidad and cedula else None
    preferido = agenda.medico_habitual(paciente, especialidad)

    # 3. Fecha
    dia = leer_fecha(pet.parametro("fecha")) if pet.parametro("fecha") else None
    if pet.parametro("fecha") and not dia:
        return repreguntar(pet, "fecha", "Necesito un día concreto. " + PREGUNTAS["fecha"], {"hora": ""})
    if dia and especialidad:
        motivo = agenda.validar_fecha(especialidad, dia)
        if motivo:
            return repreguntar(pet, "fecha", f"{motivo} ¿Qué otro día le conviene?", {"hora": ""})

    # 4. Hora
    medico = inicio = None
    hora = leer_hora(pet.parametro("hora")) if pet.parametro("hora") else None
    if pet.parametro("hora") and not hora:
        return repreguntar(pet, "hora", "Necesito una hora concreta. " + PREGUNTAS["hora"])
    if hora and dia and especialidad:
        medico, inicio, motivo = agenda.validar_hora(especialidad, dia, hora, preferido)
        if motivo:
            return repreguntar(pet, "hora", f"{motivo} {PREGUNTAS['hora']}")

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
