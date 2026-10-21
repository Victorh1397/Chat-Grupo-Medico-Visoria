# Plan 99 — Entregables

Implementa: [spec.md](spec.md)

## Enfoque

Toda la información del README ya existe repartida en las specs (decisiones, mediciones, resultados). El trabajo es **reunirla en un
documento para el profesor**, con enlaces a las specs para quien quiera el detalle, y producir el diagrama y el guion del vídeo.
Los textos se revisan contigo antes de cerrar.

## Ficheros

| Fichero | Contenido |
|---|---|
| `docs/generar_diagrama.py` | Script con Pillow (ya instalado) que dibuja el diagrama: cajas, flechas y leyenda; tipografía del sistema |
| `docs/arquitectura.png` | Diagrama generado |
| `README.md` | Documento final (ver índice abajo) |
| `docs/guion_video.md` | Guion con escenas, tiempos, frases exactas y lista de comprobación previa |
| `entrega/agente_dialogflow.zip` | Se verifica (no se modifica salvo que esté desactualizado) |

## Diagrama

```
 Usuario (voz) ──► voz/cliente_voz.py ─┐                 ┌──────── Dialogflow ES ─────────┐
 Usuario (Telegram, botones) ──────────┼──────────────► │ STT nativo · intenciones ·      │
 Simulador (texto) ────────────────────┘                 │ contexto ctx_cita_en_curso ·    │
                                                         │ follow-ups sí/no · TTS nativo   │
                                                         └───────────────┬────────────────┘
                                                                         │ ngrok (X-Visoria-Token)
                                                         ┌───────────────▼────────────────┐
                                                         │ Webhook FastAPI                 │
                                                         │ regex cédula · agenda · SSML ·  │
                                                         │ transferencia · botones Telegram│
                                                         └───────┬───────────────┬────────┘
                                                                 │               │ pregunta + documentos
                       Línea offline (una vez)                   │               ▼
 Documentos D1–D5 ─► OCR (Tesseract + preprocesado) + regex ─► documentos.json ─► Gemini 3.5 Flash-Lite
```
Colores por tipo de componente (canales, Dialogflow, webhook, LLM, línea offline) y leyenda.

## Índice del README

1. Vicky en una línea + capturas o enlace al vídeo.
2. **Caso de uso** (un párrafo).
3. **Arquitectura** (diagrama + recorrido de una petición).
4. **Agente Dialogflow**: tabla de intenciones (propósito, parámetros, webhook), entidades, contexto y follow-ups, mapa del flujo de la cita.
5. **Webhook**: validación de la cédula con regex (dos niveles), reglas de agenda, respuestas dinámicas, seguridad con token.
6. **OCR y respuesta documental**: documentos sintéticos, preprocesado y tabla de similitud, regex y validación contra el webhook,
   tratamiento de errores de OCR, texto completo en el prompt (y por qué no la Knowledge Base de Dialogflow), control de alucinaciones en
   tres capas, evaluación.
7. **Voz**: STT/TTS nativos, SSML por canal, fin de grabación por silencio, latencias medidas.
8. **Mejoras opcionales**: transferencia a recepción y Telegram con botones.
9. **Decisiones técnicas** (tabla con el dato que justifica cada una) y **qué pasa si algo falla**.
10. **Resultados** (tests, evaluación documental, latencias, conversación por voz).
11. **Cómo ejecutarlo** (requisitos, `.env`, importar el agente, webhook + ngrok + Fulfillment, cliente de voz, Telegram, OCR, tests, evaluación).
12. **Estructura del repositorio**.
13. **Proceso SDD**: specs, aprobaciones, trazabilidad, decisiones que cambiaron por las pruebas.
14. **Limitaciones y mejoras futuras**.

## Guion del vídeo (≤ 3 min)

| Tiempo | Escena |
|---|---|
| 0:00–0:15 | Presentación: Vicky, Grupo Médico Visoria, qué se va a ver; diagrama en pantalla |
| 0:15–1:35 | **Voz**: cita completa de María González (contexto, cédula validada con regex, disponibilidad, confirmación con código) |
| 1:35–2:00 | **Voz**: pregunta documental ("¿tienen estacionamiento?") y una sin respuesta ("¿hacen resonancias?") |
| 2:00–2:45 | **Telegram**: menú con botones, consulta de horarios con botones, oferta de recepción → "Sí" → caso |
| 2:45–3:00 | Cierre: terminal del webhook mostrando las peticiones; resumen de latencias |

Con las frases exactas de cada turno y una lista de comprobación previa (webhook y ngrok en marcha, webhook reiniciado para tener la agenda limpia,
micrófono, hora de menos carga de Gemini, Telegram abierto).

## Verificación
- Revisión del README, el diagrama y el guion contigo.
- ZIP del agente: `uv run pytest tests/test_agente_export.py` y búsqueda de secretos.
- Clon limpio del repositorio en una carpeta temporal: `uv sync`, `uv run pytest`, arrancar el webhook y `GET /`.

## Resultado (20/10/2026)
- Diagrama, README y guion revisados y aprobados por el autor.
- ZIP del agente: idéntico a `agente/` (32 ficheros), 41 tests de `tests/test_agente_export.py` en verde, cabecera con el marcador
  `<WEBHOOK_TOKEN>`; ni el token de `.env` ni patrones de token de Telegram o claves de Google en el ZIP.
- Clon limpio: `uv sync`, 290 tests y `ruff` en verde sin `.env`; webhook arrancado con `.env` de prueba: `GET /` con 5 documentos,
  401 sin token y respuesta correcta con token. Regenerar documentos, OCR y diagrama da los mismos ficheros (solo cambia la fecha
  de `documentos.json`).
- Hallazgo para el vídeo: la grabación de pantalla de macOS no captura el audio del sistema; se graba con altavoces y micrófono.

