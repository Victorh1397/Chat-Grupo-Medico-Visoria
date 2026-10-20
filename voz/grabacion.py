"""
Grabación del micrófono que termina sola cuando el usuario deja de hablar (spec 06, R1.3).

La decisión (¿hay voz?, ¿ya terminó?) está en DetectorSilencio, sin dependencias del micrófono,
para poder probarla con señales sintéticas.
"""

import numpy as np

FS = 16000  # Dialogflow espera 16 kHz para LINEAR16
BLOQUE_S = 0.1
CALIBRACION_S = 0.3


def nivel(bloque: np.ndarray) -> float:
    """Energía del bloque (raíz cuadrática media de las muestras int16)."""
    return float(np.sqrt(np.mean(bloque.astype(np.float64) ** 2))) if bloque.size else 0.0


class DetectorSilencio:
    """
    Decide bloque a bloque si hay que seguir grabando.

    - Hay voz cuando la energía supera `factor` veces el ruido de fondo (con un mínimo absoluto).
    - La grabación termina tras `silencio_s` sin voz, una vez que el usuario ha hablado.
    - Se corta a los `maximo_s`, y si en `espera_s` no se oye nada se abandona (sin voz).
    """

    def __init__(self, ruido: float, factor: float = 3.0, minimo: float = 400.0,
                 silencio_s: float = 1.5, maximo_s: float = 10.0, espera_s: float = 6.0):
        self.umbral = max(ruido * factor, minimo)
        # Tiempos en milisegundos enteros: sumar 0,1 s muchas veces acumula error de redondeo
        self.silencio_ms, self.maximo_ms, self.espera_ms = (round(s * 1000) for s in (silencio_s, maximo_s, espera_s))
        self.transcurrido_ms = 0
        self.callado_ms = 0
        self.hubo_voz = False

    @property
    def transcurrido(self) -> float:
        return self.transcurrido_ms / 1000

    def seguir(self, bloque: np.ndarray, duracion: float = BLOQUE_S) -> bool:
        ms = round(duracion * 1000)
        self.transcurrido_ms += ms
        if nivel(bloque) >= self.umbral:
            self.hubo_voz, self.callado_ms = True, 0
        else:
            self.callado_ms += ms
        if self.transcurrido_ms >= self.maximo_ms:
            return False
        if not self.hubo_voz:
            return self.transcurrido_ms < self.espera_ms
        return self.callado_ms < self.silencio_ms


def grabar(aviso=print) -> bytes | None:
    """Graba hasta que el usuario deja de hablar. Devuelve el audio LINEAR16 o None si no se oyó voz."""
    import sounddevice as sd  # aquí y no arriba: los tests no necesitan micrófono

    muestras = int(FS * BLOQUE_S)
    with sd.InputStream(samplerate=FS, channels=1, dtype="int16", blocksize=muestras) as entrada:
        fondo, _ = entrada.read(int(FS * CALIBRACION_S))  # ruido de la habitación antes de hablar
        detector = DetectorSilencio(ruido=nivel(fondo))
        aviso("🎙️  Hable ahora…")
        bloques = []
        while True:
            bloque, _ = entrada.read(muestras)
            bloques.append(bloque.copy())
            if not detector.seguir(bloque):
                break
    if not detector.hubo_voz:
        return None
    return np.concatenate(bloques).tobytes()
