"""
Cliente de voz de Vicky (spec 06): micrófono -> Dialogflow -> altavoz, con el STT y el TTS nativos de Dialogflow.

Una sola llamada detect_intent por turno: Dialogflow transcribe el audio, detecta la intención, llama al
webhook (que responde en SSML porque el cliente marca el canal "voz") y devuelve la respuesta ya sintetizada.

Uso (desde la raíz del repositorio, con el webhook y ngrok en marcha):
    uv run python -m voz.cliente_voz            # hablar: Enter para empezar, termina solo al callar
    uv run python -m voz.cliente_voz --texto    # escribir en lugar de hablar (Vicky sigue hablando)

Requiere permiso de micrófono para la terminal (Ajustes del Sistema -> Privacidad y seguridad -> Micrófono).
"""

import io
import json
import os
import statistics
import sys
import time
import uuid
import wave
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import dialogflow
from google.protobuf import struct_pb2

from voz.grabacion import FS, grabar
from webhook.datos import ESPECIALIDADES, MEDICOS
from webhook.ssml import sin_etiquetas

RAIZ = Path(__file__).resolve().parents[1]
load_dotenv(RAIZ / ".env")

PROJECT_ID = os.environ["DIALOGFLOW_PROJECT_ID"]
IDIOMA = "es"
VOZ = "es-US-Chirp3-HD-Aoede"  # elegida por el autor entre las voces femeninas latinoamericanas (spec 06, T2)
VELOCIDAD = 0.95
REGISTROS = RAIZ / "voz" / "registros"

# Pistas para el reconocimiento de voz: palabras que esperamos oír en esta conversación
PISTAS = [
    *ESPECIALIDADES, "dermatólogo", "endocrinólogo", "cirujano plástico", "urólogo", "cardiólogo", "oftalmólogo",
    "venezolano", "venezolana", "extranjero", "extranjera", "cédula", "cita", "Visoria",
    *(m.nombre for m in MEDICOS),
]


class Conversacion:
    """Una sesión de Dialogflow: el contexto y los datos recogidos se conservan entre turnos."""

    def __init__(self):
        self.cliente = dialogflow.SessionsClient()
        self.sesion = self.cliente.session_path(PROJECT_ID, str(uuid.uuid4()))
        canal = struct_pb2.Struct()
        canal.update({"canal": "voz"})  # el webhook solo usa SSML si la petición viene de aquí
        self.parametros_consulta = dialogflow.QueryParameters(payload=canal)
        self.salida_audio = dialogflow.OutputAudioConfig(
            audio_encoding=dialogflow.OutputAudioEncoding.OUTPUT_AUDIO_ENCODING_LINEAR_16,
            synthesize_speech_config=dialogflow.SynthesizeSpeechConfig(
                speaking_rate=VELOCIDAD, voice=dialogflow.VoiceSelectionParams(name=VOZ)),
        )
        self.turnos: list[dict] = []

    def preguntar(self, audio: bytes | None = None, texto: str | None = None):
        if audio is not None:
            entrada = dialogflow.QueryInput(audio_config=dialogflow.InputAudioConfig(
                audio_encoding=dialogflow.AudioEncoding.AUDIO_ENCODING_LINEAR_16,
                language_code=IDIOMA,
                sample_rate_hertz=FS,
                speech_contexts=[dialogflow.SpeechContext(phrases=PISTAS, boost=10)],
            ))
        else:
            entrada = dialogflow.QueryInput(text=dialogflow.TextInput(text=texto, language_code=IDIOMA))
        return self.cliente.detect_intent(request={
            "session": self.sesion,
            "query_input": entrada,
            "query_params": self.parametros_consulta,
            "output_audio_config": self.salida_audio,
            **({"input_audio": audio} if audio is not None else {}),
        })


def reproducir(wav_bytes: bytes) -> None:
    """El audio LINEAR16 que devuelve Dialogflow ya es un WAV completo (empieza por 'RIFF')."""
    import numpy as np
    import sounddevice as sd

    with wave.open(io.BytesIO(wav_bytes)) as w:
        muestras = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        sd.play(muestras, w.getframerate())
        sd.wait()


def mostrar(turno: dict) -> None:
    print(f"  Usted dijo : {turno['entendido'] or '(no se entendió nada)'}")
    print(f"  Intención  : {turno['intencion']} ({turno['confianza']:.2f})")
    if turno["parametros"]:
        print(f"  Datos      : {turno['parametros']}")
    print(f"  Vicky      : {turno['respuesta']}")
    aviso = "" if turno["latencia_s"] < 5 else "  ⚠️ por encima de 5 s"
    print(f"  Latencia   : {turno['latencia_s']:.2f} s{aviso}")
    if turno["webhook"] != "ok":
        print(f"  Webhook    : {turno['webhook']}")


def resumen(conversacion: Conversacion) -> None:
    latencias = [t["latencia_s"] for t in conversacion.turnos]
    if not latencias:
        return
    print(f"\nTurnos: {len(latencias)} | latencia mediana {statistics.median(latencias):.2f} s | "
          f"máxima {max(latencias):.2f} s | por encima de 5 s: {sum(x >= 5 for x in latencias)}")
    REGISTROS.mkdir(parents=True, exist_ok=True)
    ruta = REGISTROS / f"sesion-{datetime.now():%Y%m%d-%H%M%S}.json"
    ruta.write_text(json.dumps({"voz": VOZ, "turnos": conversacion.turnos}, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    print(f"Registro de la sesión: {ruta.relative_to(RAIZ)}")


def main() -> None:
    modo_texto = "--texto" in sys.argv
    sin_audio = "--silencio" in sys.argv  # para pruebas automáticas: no reproduce la voz
    conversacion = Conversacion()

    print("=" * 60)
    print("Vicky · Grupo Médico Visoria")
    print("Escriba su mensaje y pulse Enter." if modo_texto else "Pulse Enter y hable; termine callándose.")
    print("Para salir: 'q' + Enter.")
    print("=" * 60)

    while True:
        try:
            orden = input("\n> " if modo_texto else "\n[Enter para hablar] ").strip()
        except EOFError:
            break
        if orden.lower() == "q":
            break
        try:
            if modo_texto:
                if not orden:
                    continue
                inicio = time.perf_counter()
                respuesta = conversacion.preguntar(texto=orden)
            else:
                audio = grabar()
                if audio is None:
                    print("  No le escuché. Pulse Enter e inténtelo de nuevo.")
                    continue
                inicio = time.perf_counter()
                respuesta = conversacion.preguntar(audio=audio)
        except Exception as e:  # sin micrófono, sin red, cuota…: avisar y seguir
            print(f"  ⚠️ No se pudo completar el turno: {type(e).__name__}: {str(e)[:150]}")
            continue

        latencia = time.perf_counter() - inicio
        r = respuesta.query_result
        turno = {
            "entendido": r.query_text,
            "intencion": r.intent.display_name,
            "confianza": round(r.intent_detection_confidence, 2),
            "parametros": {k: v for k, v in dict(r.parameters).items() if v not in ("", None)},
            "respuesta": sin_etiquetas(r.fulfillment_text),
            "latencia_s": round(latencia, 2),
            "webhook": respuesta.webhook_status.message if respuesta.webhook_status.code else "ok",
        }
        conversacion.turnos.append(turno)
        mostrar(turno)
        if respuesta.output_audio and not sin_audio:
            reproducir(respuesta.output_audio)

    resumen(conversacion)


if __name__ == "__main__":
    main()
