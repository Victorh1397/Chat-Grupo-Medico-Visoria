"""
Reglas de agenda de la clínica y estado en memoria.

En un sistema real esto sería una base de datos. Para la entrega basta con memoria: lo que se
evalúa es que la respuesta la decide el código a partir de los datos recogidos.
"""

import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from webhook import textos
from webhook.cedula import solo_digitos
from webhook.datos import (
    CITA_SEMBRADA,
    DOM,
    DURACION_CITA_MIN,
    PACIENTES,
    Medico,
    Paciente,
    medico_por_nombre,
    medicos_de,
)

CARACAS = ZoneInfo("America/Caracas")
BLOQUE = timedelta(minutes=DURACION_CITA_MIN)


def ahora() -> datetime:
    """Hora actual en Caracas. Los tests la sustituyen para tener fechas fijas."""
    return datetime.now(CARACAS)


@dataclass
class Cita:
    codigo: str
    cedula: str
    nombre: str
    medico: Medico
    inicio: datetime


@dataclass
class Propuesta:
    cedula: str
    nombre: str
    apellido: str
    medico: Medico
    inicio: datetime


def _codigo(prefijo: str, usados: set[str]) -> str:
    while True:
        codigo = f"{prefijo}-{random.randint(10000, 99999)}"
        if codigo not in usados:
            return codigo


def redondear(h: time) -> time:
    """Lleva la hora al inicio de su bloque de 30 minutos: 10:20 -> 10:00."""
    return time(h.hour, 0 if h.minute < 30 else 30)


def atiende(medico: Medico, inicio: datetime) -> bool:
    """True si el bloque completo que empieza en `inicio` está dentro del horario del médico."""
    franja = medico.horario.get(inicio.weekday())
    if not franja:
        return False
    abre = datetime.combine(inicio.date(), franja[0], CARACAS)
    cierra = datetime.combine(inicio.date(), franja[1], CARACAS)
    return abre <= inicio and inicio + BLOQUE <= cierra


class Agenda:
    def __init__(self):
        self.reiniciar()

    def reiniciar(self) -> None:
        self.citas: list[Cita] = []
        self.propuestas: dict[str, Propuesta] = {}
        self.pacientes_nuevos: dict[str, Paciente] = {}
        self._sembrar()

    def _sembrar(self) -> None:
        hoy = ahora().date()
        dias = (CITA_SEMBRADA["dia_semana"] - hoy.weekday()) % 7 or 7
        inicio = datetime.combine(hoy + timedelta(days=dias), CITA_SEMBRADA["hora"], CARACAS)
        paciente = self.paciente(CITA_SEMBRADA["cedula"])
        self.citas.append(Cita(CITA_SEMBRADA["codigo"], paciente.cedula, paciente.nombre,
                               medico_por_nombre(CITA_SEMBRADA["medico"]), inicio))

    # Pacientes

    def paciente(self, cedula: str) -> Paciente | None:
        """Busca por cédula canónica (V-14523987)."""
        return next((p for p in PACIENTES if p.cedula == cedula), None) or self.pacientes_nuevos.get(cedula)

    def paciente_por_numero(self, valor: str) -> Paciente | None:
        """Busca solo por el número, sea V o E (historial y cancelación no preguntan la nacionalidad)."""
        numero = solo_digitos(valor)
        todos = PACIENTES + list(self.pacientes_nuevos.values())
        return next((p for p in todos if solo_digitos(p.cedula) == numero), None) if numero else None

    @staticmethod
    def medico_habitual(paciente: Paciente | None, especialidad: str) -> Medico | None:
        """Médico de la consulta más reciente del paciente en esa especialidad."""
        if not paciente:
            return None
        previas = sorted((c for c in paciente.historial if c.especialidad == especialidad),
                         key=lambda c: c.fecha, reverse=True)
        return medico_por_nombre(previas[0].medico) if previas else None

    # Validaciones

    @staticmethod
    def validar_fecha(especialidad: str, dia: date) -> str:
        """Devuelve el motivo de rechazo o "" si la fecha es válida."""
        if dia < ahora().date():
            return "Esa fecha ya pasó."
        if dia.weekday() == DOM:
            return "Los domingos la clínica está cerrada."
        medicos = medicos_de(especialidad)
        if not any(dia.weekday() in m.horario for m in medicos):
            dias_atencion = sorted({d for m in medicos for d in m.horario})
            return (f"Ese día no hay consulta de {textos.especialidad(especialidad)}; "
                    f"se atiende {textos.dias(dias_atencion)}.")
        return ""

    def ocupado(self, medico: Medico, inicio: datetime) -> bool:
        return any(c.medico == medico and c.inicio == inicio for c in self.citas)

    def validar_hora(self, especialidad: str, dia: date, hora: time,
                     preferido: Medico | None = None) -> tuple[Medico | None, datetime | None, str]:
        """
        Busca un médico de la especialidad libre ese día a esa hora, empezando por el preferido.
        Devuelve (médico, inicio, "") o (None, None, motivo con una alternativa).
        """
        candidatos = sorted(medicos_de(especialidad), key=lambda m: m != preferido)
        candidatos = [m for m in candidatos if dia.weekday() in m.horario]

        h = redondear(hora)
        # "a las 3" suele ser las 15:00 y, según la hora del día, Dialogflow entiende "a las 9" como las 21:00:
        # si la hora no encaja en ningún horario pero la de 12 horas antes o después sí, se usa esa.
        alternativa = time((h.hour + 12) % 24, h.minute)
        if (not any(atiende(m, datetime.combine(dia, h, CARACAS)) for m in candidatos)
                and any(atiende(m, datetime.combine(dia, alternativa, CARACAS)) for m in candidatos)):
            h = alternativa
        inicio = datetime.combine(dia, h, CARACAS)

        if inicio <= ahora():
            return None, None, "Esa hora ya pasó."

        for medico in candidatos:
            if atiende(medico, inicio) and not self.ocupado(medico, inicio):
                return medico, inicio, ""

        en_horario = [m for m in candidatos if atiende(m, inicio)]
        if en_horario:
            siguiente = self.siguiente_libre(en_horario, inicio)
            if siguiente:
                medico, libre = siguiente
                quien = textos.doctor(medico.titulo, medico.nombre)
                return None, None, (f"A las {textos.hora(h)} ya no hay disponibilidad. El siguiente horario libre "
                                    f"es a las {textos.hora(libre.time())} con {quien}.")
            return None, None, "Ese día ya no quedan horarios libres en esa especialidad."

        franjas = [f"{textos.doctor(m.titulo, m.nombre)} de {textos.hora(m.horario[dia.weekday()][0])} "
                   f"a {textos.hora(m.horario[dia.weekday()][1])}" for m in candidatos]
        return None, None, f"Ese día atiende {textos.unir(franjas)}."

    def siguiente_libre(self, medicos: list[Medico], desde: datetime) -> tuple[Medico, datetime] | None:
        inicio = desde + BLOQUE
        while inicio.date() == desde.date():
            for medico in medicos:
                if atiende(medico, inicio) and not self.ocupado(medico, inicio):
                    return medico, inicio
            inicio += BLOQUE
        return None

    # Flujo de cita

    def proponer(self, sesion: str, propuesta: Propuesta) -> None:
        self.propuestas[sesion] = propuesta

    def descartar(self, sesion: str) -> None:
        self.propuestas.pop(sesion, None)

    def confirmar(self, sesion: str) -> Cita | None:
        """Registra la cita propuesta en la sesión. None si no hay propuesta o el hueco ya se ocupó."""
        propuesta = self.propuestas.pop(sesion, None)
        if not propuesta or self.ocupado(propuesta.medico, propuesta.inicio):
            return None
        if not self.paciente(propuesta.cedula):
            self.pacientes_nuevos[propuesta.cedula] = Paciente(propuesta.cedula, propuesta.nombre, propuesta.apellido)
        cita = Cita(_codigo("CIT", {c.codigo for c in self.citas}), propuesta.cedula, propuesta.nombre,
                    propuesta.medico, propuesta.inicio)
        self.citas.append(cita)
        return cita

    def pendientes(self, cedula: str) -> list[Cita]:
        return sorted((c for c in self.citas if c.cedula == cedula and c.inicio > ahora()), key=lambda c: c.inicio)

    def cancelar_proxima(self, cedula: str) -> Cita | None:
        pendientes = self.pendientes(cedula)
        if not pendientes:
            return None
        self.citas.remove(pendientes[0])
        return pendientes[0]


def codigo_caso() -> str:
    return _codigo("VIS", set())
