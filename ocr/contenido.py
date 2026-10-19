"""
Contenido de los documentos D1-D5 (spec 01 y spec 04). Todo es ficticio.

Cada documento es una lista de bloques que generar_documentos.py dibuja:
    ("titulo", texto) ("subtitulo", texto) ("parrafo", texto) ("lista", [textos])
    ("tabla", [cabeceras], [[celdas], ...]) ("nota", texto)

D2 (tarifas) y D3 (horarios) se construyen desde webhook/datos.py, la misma fuente que usa el webhook
para agendar: si cambia un precio, se regenera el documento y Vicky no se contradice.
"""

from webhook import textos
from webhook.datos import ESPECIALIDADES, HORARIO_CLINICA, medicos_de

CLINICA = "Grupo Médico Visoria"
PIE = "Documento ficticio elaborado con fines académicos."
VIGENCIA = "01/09/2026"

DIRECCION = "Av. Principal de Los Palos Grandes, Torre Visoria, piso 3, Caracas"
TELEFONO = "(0212) 555-0142"
WHATSAPP = "(0414) 555-0187"
ASEGURADORAS = ["Seguros Araguaney", "Cumbre Azul Seguros", "Salud Llanera", "Previsión Caribe"]


def dias_tabla(dias: list[int]) -> str:
    """[1, 3] -> 'Martes y jueves'; [0, 1, 2] -> 'Lunes a miércoles'."""
    texto = textos.dias(dias)
    texto = texto.removeprefix("los ").removeprefix("de ")
    return texto[0].upper() + texto[1:]


def _horario_general() -> str:
    semana = HORARIO_CLINICA[0]
    sabado = HORARIO_CLINICA[5]
    return (f"Lunes a viernes de {textos.hora(semana[0])} a {textos.hora(semana[1])} y sábados de "
            f"{textos.hora(sabado[0])} a {textos.hora(sabado[1])}. Domingos y feriados cerrado.")


D1_PREGUNTAS_FRECUENTES = [
    ("titulo", "Preguntas frecuentes"),
    ("subtitulo", "¿Dónde está la clínica?"),
    ("parrafo", f"Estamos en la {DIRECCION}. La estación de metro más cercana es Altamira, a diez minutos a pie. "
                "Las rutas de autobús que pasan por la Av. Francisco de Miranda tienen parada a dos cuadras."),
    ("subtitulo", "¿Tienen estacionamiento?"),
    ("parrafo", "Sí. La torre tiene estacionamiento propio en el sótano. Es gratuito las dos primeras horas para "
                "pacientes con cita; después cuesta 2 USD por hora. Presente el ticket en recepción para validarlo."),
    ("subtitulo", "¿Cuál es el horario de atención?"),
    ("parrafo", _horario_general() + " Cada médico tiene su propio horario de consulta."),
    ("subtitulo", "¿Cómo puedo comunicarme con la clínica?"),
    ("parrafo", f"Teléfono de recepción {TELEFONO} y WhatsApp {WHATSAPP}, en el horario de atención."),
    ("subtitulo", "¿Qué formas de pago aceptan?"),
    ("lista", ["Efectivo en dólares.", "Tarjetas de débito y crédito.", "Pago móvil y transferencia bancaria.",
               "Seguros con convenio (ver documento de seguros y reglamento)."]),
    ("subtitulo", "¿Qué debo llevar a la consulta?"),
    ("lista", ["Cédula de identidad.", "Informes y resultados de exámenes anteriores.",
               "Lista de medicamentos que toma actualmente.", "Carnet del seguro, si aplica."]),
]

D2_TARIFARIO = [
    ("titulo", "Tarifario de consultas"),
    ("parrafo", f"Vigente desde el {VIGENCIA}. Precios en dólares estadounidenses (USD). Cada médico tiene un precio "
                "único por consulta, igual para la primera consulta y para los controles."),
    ("tabla", ["Especialidad", "Médico", "Precio"],
     [[m.especialidad, m.nombre_completo, f"{m.precio_usd} USD"] for esp in ESPECIALIDADES for m in medicos_de(esp)]),
    ("nota", "Los exámenes y procedimientos se cotizan aparte. Los precios pueden cambiar sin previo aviso."),
]


def _filas_horarios() -> list[list[str]]:
    filas = []
    for esp in ESPECIALIDADES:
        for m in medicos_de(esp):
            franjas: dict[tuple, list[int]] = {}
            for dia, franja in sorted(m.horario.items()):
                franjas.setdefault(franja, []).append(dia)
            for (abre, cierra), dias in franjas.items():
                filas.append([esp, m.nombre_completo, dias_tabla(dias),
                              f"{textos.hora(abre)} - {textos.hora(cierra)}"])
    return filas


D3_HORARIOS = [
    ("titulo", "Horarios de consulta de los médicos"),
    ("parrafo", "Las citas son en bloques de 30 minutos. El último bloque empieza media hora antes del cierre."),
    ("tabla", ["Especialidad", "Médico", "Días", "Horario"], _filas_horarios()),
    ("nota", f"Citas: {TELEFONO} o con Vicky, nuestra asistente virtual."),
]

D4_PREPARACION = [
    ("titulo", "Preparación para exámenes"),
    ("parrafo", "Siga estas indicaciones antes de su examen. Si tiene dudas, consulte con su médico."),
    ("subtitulo", "Endocrinología: curva de glucosa"),
    ("lista", ["Ayuno de 8 a 12 horas; puede tomar agua.", "No fumar ni hacer ejercicio la mañana del examen.",
               "El examen dura unas 2 horas; traiga algo para leer."]),
    ("subtitulo", "Urología: antígeno prostático (PSA)"),
    ("lista", ["Evitar relaciones sexuales y ejercicio intenso (ciclismo) 48 horas antes.",
               "No requiere ayuno."]),
    ("subtitulo", "Dermatología: biopsia de piel"),
    ("lista", ["Suspender aspirina y anticoagulantes 7 días antes, solo si su médico lo autoriza.",
               "No aplicar cremas en la zona el día del procedimiento."]),
    ("subtitulo", "Cirugía plástica: valoración preoperatoria"),
    ("lista", ["Traer hematología completa, pruebas de coagulación y electrocardiograma recientes.",
               "No fumar durante las 3 semanas previas a la cirugía."]),
    ("subtitulo", "Cardiología: prueba de esfuerzo"),
    ("lista", ["Ropa y zapatos deportivos.", "Comida ligera 2 horas antes; sin café el día del examen."]),
    ("subtitulo", "Oftalmología: fondo de ojo con dilatación"),
    ("lista", ["La visión queda borrosa de 4 a 6 horas: venga acompañado y no conduzca.",
               "Traiga lentes de sol."]),
]

D5_SEGUROS_REGLAMENTO = [
    ("titulo", "Seguros y reglamento del paciente"),
    ("subtitulo", "Seguros con convenio"),
    ("lista", [f"{a}." for a in ASEGURADORAS]),
    ("parrafo", "Presente su carnet y su cédula en recepción. Según su póliza, puede aplicar un copago del 20 % de la "
                "consulta. Si su seguro no aparece en la lista, puede pagar la consulta y solicitar el reembolso."),
    ("subtitulo", "Reglamento"),
    ("lista", ["Llegue 15 minutos antes de su cita.",
               "Para cancelar o cambiar una cita, avise con al menos 24 horas de anticipación.",
               "Si llega con más de 15 minutos de retraso, la cita podrá reprogramarse.",
               "Se permite un acompañante por paciente.",
               "Los menores de edad deben venir con su representante.",
               "Mantenga el teléfono en silencio en las salas de espera."]),
]

DOCUMENTOS = {
    "D1": ("Preguntas frecuentes", D1_PREGUNTAS_FRECUENTES),
    "D2": ("Tarifario de consultas", D2_TARIFARIO),
    "D3": ("Horarios de los médicos", D3_HORARIOS),
    "D4": ("Preparación para exámenes", D4_PREPARACION),
    "D5": ("Seguros y reglamento", D5_SEGUROS_REGLAMENTO),
}


def archivo(doc_id: str) -> str:
    """'D1' -> 'D1_preguntas_frecuentes'."""
    titulo = DOCUMENTOS[doc_id][0].lower()
    for a, b in zip("áéíóúñ ", "aeioun_"):
        titulo = titulo.replace(a, b)
    return f"{doc_id}_{titulo}"
