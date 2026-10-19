"""
Evaluación de la consulta documental contra Gemini real (spec 05, R6 y CA-4/CA-5).

Lanza las preguntas de evaluacion/preguntas_documentales.json espaciadas (cuota gratuita de Gemini)
y guarda el resultado en evaluacion/resultados_documental.json.

Uso:
    uv run python -m scripts.evaluar_documental
"""

import json
import time
import unicodedata
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[1]
load_dotenv(RAIZ / ".env")

from webhook import documentos  # noqa: E402  (necesita GOOGLE_API_KEY ya cargada)
from webhook.documentos import NO_DISPONIBLE_AHORA, SIN_INFO_DOCUMENTAL  # noqa: E402

PREGUNTAS = RAIZ / "evaluacion" / "preguntas_documentales.json"
RESULTADOS = RAIZ / "evaluacion" / "resultados_documental.json"
PAUSA_S = 6  # ~10 preguntas por minuto: margen frente al límite gratuito de 15 por minuto


def plano(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def contiene(respuesta: str, grupos: list[list[str]]) -> bool:
    return all(any(plano(opcion) in plano(respuesta) for opcion in grupo) for grupo in grupos)


def preguntar(pregunta: str) -> tuple[str, float]:
    time.sleep(PAUSA_S)
    inicio = time.perf_counter()
    respuesta = documentos.responder_con_documentos(pregunta, SIN_INFO_DOCUMENTAL)
    return respuesta, time.perf_counter() - inicio


def main() -> None:
    juego = json.loads(PREGUNTAS.read_text(encoding="utf-8"))
    filas = []

    print(f"Modelo: {documentos.MODELO}\n")
    for p in juego["respondibles"]:
        respuesta, segundos = preguntar(p["pregunta"])
        ok = contiene(respuesta, p["debe_contener"])
        filas.append({**p, "tipo": "respondible", "respuesta": respuesta, "segundos": round(segundos, 2), "ok": ok})
        print(f"{'OK ' if ok else 'MAL'} {segundos:4.1f}s  {p['pregunta']}\n          -> {respuesta}")

    for p in juego["no_respondibles"]:
        respuesta, segundos = preguntar(p["pregunta"])
        ok = respuesta == SIN_INFO_DOCUMENTAL
        filas.append({**p, "respuesta": respuesta, "segundos": round(segundos, 2), "ok": ok})
        print(f"{'OK ' if ok else 'MAL'} {segundos:4.1f}s  [{p['tipo']}] {p['pregunta']}\n          -> {respuesta}")

    respondibles = [f for f in filas if f["tipo"] == "respondible"]
    no_respondibles = [f for f in filas if f["tipo"] != "respondible"]
    tiempos = sorted(f["segundos"] for f in filas)
    resumen = {
        "aciertos_respondibles": f"{sum(f['ok'] for f in respondibles)}/{len(respondibles)}",
        "sin_alucinar_no_respondibles": f"{sum(f['ok'] for f in no_respondibles)}/{len(no_respondibles)}",
        "errores_o_tiempo_agotado": sum(f["respuesta"] == NO_DISPONIBLE_AHORA for f in filas),
        "segundos_mediana": tiempos[len(tiempos) // 2],
        "segundos_p95": tiempos[int(len(tiempos) * 0.95) - 1],
        "segundos_maximo": tiempos[-1],
    }
    RESULTADOS.write_text(json.dumps({
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "modelo": documentos.MODELO,
        "resumen": resumen,
        "preguntas": filas,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("\nResumen:")
    for clave, valor in resumen.items():
        print(f"  {clave}: {valor}")


if __name__ == "__main__":
    main()
