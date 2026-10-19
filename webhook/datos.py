"""
Datos ficticios de Grupo Médico Visoria.

Es la fuente única de verdad: el webhook agenda con estos datos y la spec 04 genera a partir de
ellos los documentos de tarifas (D2) y horarios (D3), para que Vicky nunca se contradiga.
Todos los nombres, cédulas y fechas son inventados.
"""

from dataclasses import dataclass, field
from datetime import date, time

# Días de la semana: 0 = lunes ... 6 = domingo (como date.weekday())
LUN, MAR, MIE, JUE, VIE, SAB, DOM = range(7)

DURACION_CITA_MIN = 30

HORARIO_CLINICA = {
    LUN: (time(7, 0), time(19, 0)),
    MAR: (time(7, 0), time(19, 0)),
    MIE: (time(7, 0), time(19, 0)),
    JUE: (time(7, 0), time(19, 0)),
    VIE: (time(7, 0), time(19, 0)),
    SAB: (time(7, 0), time(13, 0)),
}

ESPECIALIDADES = [
    "Dermatología",
    "Endocrinología",
    "Cirugía plástica",
    "Urología",
    "Cardiología",
    "Oftalmología",
]


@dataclass(frozen=True)
class Medico:
    nombre: str
    titulo: str  # "Dr." o "Dra."
    especialidad: str
    precio_usd: int
    # día de la semana -> (hora de inicio, hora de cierre)
    horario: dict[int, tuple[time, time]] = field(hash=False)

    @property
    def nombre_completo(self) -> str:
        return f"{self.titulo} {self.nombre}"


def _dias(dias: list[int], inicio: time, fin: time) -> dict[int, tuple[time, time]]:
    return {d: (inicio, fin) for d in dias}


MANANA = (time(8, 0), time(12, 0))
TARDE = (time(14, 0), time(18, 0))

MEDICOS = [
    Medico("Laura Rojas", "Dra.", "Dermatología", 40, _dias([MAR, JUE], *MANANA)),
    Medico("Andrés Salazar", "Dr.", "Dermatología", 35, _dias([LUN, MIE], *TARDE)),
    Medico("Carmen Villalobos", "Dra.", "Endocrinología", 50, _dias([LUN, MIE, VIE], *MANANA)),
    Medico("Rafael Ortega", "Dr.", "Endocrinología", 45, _dias([MAR, JUE], *TARDE)),
    Medico("Alejandro Briceño", "Dr.", "Cirugía plástica", 80, _dias([LUN, JUE], time(9, 0), time(13, 0))),
    Medico("Valentina Pacheco", "Dra.", "Cirugía plástica", 90, _dias([MIE, VIE], *TARDE)),
    Medico("Gustavo Hernández", "Dr.", "Urología", 45, _dias([MAR, VIE], *MANANA)),
    Medico("Luis Carrillo", "Dr.", "Urología", 50, _dias([SAB], *MANANA)),
    Medico("Patricia Medina", "Dra.", "Cardiología", 55, _dias([LUN, MAR, MIE], *MANANA)),
    Medico("Eduardo Rangel", "Dr.", "Cardiología", 50, _dias([JUE, VIE], *TARDE)),
    Medico("Gabriela Quintero", "Dra.", "Oftalmología", 40, _dias([LUN, MIE], *MANANA)),
    Medico("José Luis Arismendi", "Dr.", "Oftalmología", 45, {**_dias([MAR, JUE], *TARDE), SAB: MANANA}),
]


def medico_por_nombre(nombre: str) -> Medico:
    return next(m for m in MEDICOS if m.nombre == nombre)


def medicos_de(especialidad: str) -> list[Medico]:
    return [m for m in MEDICOS if m.especialidad == especialidad]


@dataclass(frozen=True)
class ConsultaPrevia:
    especialidad: str
    medico: str  # nombre, sin título
    fecha: date


@dataclass(frozen=True)
class Paciente:
    cedula: str  # forma canónica: V-14523987 / E-81234567
    nombre: str
    apellido: str
    historial: tuple[ConsultaPrevia, ...] = ()


PACIENTES = [
    Paciente("V-14523987", "María", "González", (
        ConsultaPrevia("Dermatología", "Laura Rojas", date(2026, 3, 12)),
        ConsultaPrevia("Cardiología", "Patricia Medina", date(2025, 11, 4)),
    )),
    Paciente("V-9452312", "José", "Rodríguez", (
        ConsultaPrevia("Urología", "Gustavo Hernández", date(2026, 5, 20)),
    )),
    Paciente("E-81234567", "Carlos", "Pérez", (
        ConsultaPrevia("Cardiología", "Eduardo Rangel", date(2026, 1, 15)),
    )),
    Paciente("V-20345678", "Ana", "Rodríguez", (
        ConsultaPrevia("Endocrinología", "Carmen Villalobos", date(2026, 7, 2)),
        ConsultaPrevia("Oftalmología", "Gabriela Quintero", date(2026, 2, 10)),
    )),
    Paciente("V-17890123", "Luisa", "Fernández", (
        ConsultaPrevia("Cirugía plástica", "Valentina Pacheco", date(2026, 8, 21)),
    )),
    Paciente("V-6123456", "Pedro", "Martínez", (
        ConsultaPrevia("Oftalmología", "José Luis Arismendi", date(2025, 9, 30)),
    )),
    Paciente("E-84567890", "Sofía", "Ramírez", (
        ConsultaPrevia("Dermatología", "Andrés Salazar", date(2026, 4, 9)),
    )),
    Paciente("V-25678901", "Miguel", "Torres", (
        ConsultaPrevia("Endocrinología", "Rafael Ortega", date(2026, 6, 18)),
    )),
]

# Cita pendiente sembrada para poder demostrar la cancelación. La fecha se calcula al
# arrancar (próximo martes a las 15:00) para que nunca quede en el pasado.
CITA_SEMBRADA = {
    "codigo": "CIT-10234",
    "cedula": "V-25678901",
    "medico": "Rafael Ortega",
    "dia_semana": MAR,
    "hora": time(15, 0),
}
