# Chat Grupo Médico Visoria

Asistente conversacional por voz (Dialogflow ES + webhook FastAPI + OCR + Gemini) para la evaluación final de
"Herramientas de IA Clásica". El enunciado está en `../1-Enunciado_Evaluacion_Final.pdf`.

## Metodología: SDD (Spec-Driven Development)

- No se escribe código de negocio sin una spec aprobada en `specs/NN-nombre/spec.md`.
- Orden por spec: `spec.md` (qué y por qué) → aprobación del usuario → `plan.md` (cómo) → `tareas.md` → implementación → verificación contra criterios de aceptación → commit `feat(NN): …`.
- Plantillas en `specs/_plantillas/`. Principios en `specs/00-constitucion.md`. Estado y trazabilidad en `specs/README.md` (actualizar al cerrar cada spec).
- Las specs, la documentación y las respuestas al usuario van siempre en español.

## Entorno

- Python 3.12 gestionado con `uv` (`uv sync`, `uv run …`, `uv add …`). No usar `pip` directamente.
- Webhook: `uv run uvicorn webhook.main:app --reload --port 8000`, expuesto con VS Code Dev Tunnels (puerto 8000, visibilidad Public). En Fulfillment se añade la cabecera `X-Tunnel-Skip-AntiPhishing-Page: true`.
- Tests: `uv run pytest`. Lint: `uv run ruff check .`.
- Tesseract instalado con Homebrew (`spa` disponible).

## Reglas

- Voz solo con STT/TTS nativos de Dialogflow (sin servicios externos de voz).
- Latencia < 5 s por turno: nada de OCR en la petición; el LLM siempre con `try/except` y respuesta de reserva.
- El LLM responde solo con información de los documentos procesados por OCR (sin conocimiento propio); si el dato no está, lo dice explícitamente. Cómo se recupera ese texto es independiente: en el mínimo obligatorio se incluye entero en el prompt; con el extra de ChromaDB (spec 10) se recuperan solo los fragmentos relevantes del mismo texto OCR.
- Secretos solo en `.env` o fuera del repo. Datos de pacientes siempre ficticios.
- El agente Dialogflow vive en `agente/` (export descomprimido) y es la fuente de verdad; el ZIP de entrega se genera desde ahí.
- Material de clase de referencia (no modificar): `../../webhook_dialogflow/` y `../../Asegurador-Demo2/`.
