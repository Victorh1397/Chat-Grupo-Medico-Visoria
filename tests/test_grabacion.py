"""Fin de la grabación por silencio (spec 06, R1.3 y CA-6), con señales sintéticas: sin micrófono."""

import numpy as np

from voz.grabacion import BLOQUE_S, FS, DetectorSilencio, nivel

AZAR = np.random.default_rng(0)
MUESTRAS = int(FS * BLOQUE_S)


def ruido(nivel_rms: float = 60) -> np.ndarray:
    return (AZAR.normal(0, nivel_rms, MUESTRAS)).astype(np.int16)


def voz(nivel_rms: float = 3000) -> np.ndarray:
    t = np.arange(MUESTRAS) / FS
    return (np.sin(2 * np.pi * 220 * t) * nivel_rms * np.sqrt(2)).astype(np.int16)


def segundos_hasta_parar(detector: DetectorSilencio, señal: list[np.ndarray]) -> float:
    for bloque in señal:
        if not detector.seguir(bloque):
            break
    return round(detector.transcurrido, 1)


def test_nivel():
    assert nivel(voz(3000)) > 2500 and nivel(ruido(60)) < 100


def test_termina_tras_1_5_s_de_silencio():
    detector = DetectorSilencio(ruido=60)
    señal = [ruido()] * 3 + [voz()] * 20 + [ruido()] * 50  # 0,3 s ruido + 2 s voz + silencio
    assert segundos_hasta_parar(detector, señal) == 3.8  # 0,3 + 2 + 1,5
    assert detector.hubo_voz


def test_pausa_corta_al_hablar_no_corta_la_grabacion():
    detector = DetectorSilencio(ruido=60)
    señal = [voz()] * 10 + [ruido()] * 8 + [voz()] * 10 + [ruido()] * 50  # pausa de 0,8 s entre palabras
    assert segundos_hasta_parar(detector, señal) == 4.3  # 1 + 0,8 + 1 + 1,5


def test_corte_a_los_10_s():
    assert segundos_hasta_parar(DetectorSilencio(ruido=60), [voz()] * 200) == 10.0


def test_sin_voz_se_abandona():
    detector = DetectorSilencio(ruido=60)
    assert segundos_hasta_parar(detector, [ruido()] * 200) == 6.0
    assert not detector.hubo_voz


def test_umbral_relativo_al_ruido_de_la_sala():
    # En una sala ruidosa (rms 800) una voz débil (rms 1500) no supera 3 x ruido
    assert DetectorSilencio(ruido=800).umbral == 2400
    assert DetectorSilencio(ruido=10).umbral == 400  # mínimo absoluto
