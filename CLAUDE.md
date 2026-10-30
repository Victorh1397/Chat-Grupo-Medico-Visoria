# Chat Grupo Médico Visoria

Asistente conversacional por voz (Dialogflow ES + webhook FastAPI + OCR + Gemini) para la evaluación final de
"Herramientas de IA Clásica". El enunciado (material de la asignatura) no se versiona: cada persona lo guarda en local como `enunciado_*.md`, ignorado por git.

## Metodología: SDD (Spec-Driven Development)

- No se escribe código de negocio sin una spec aprobada en `specs/NN-nombre/spec.md`.
- Orden por spec: `spec.md` (qué y por qué) → **aprobación de la spec** → `plan.md` (cómo) + `tareas.md` → **presentarlos y esperar a que el equipo los lea y los apruebe** → implementación → verificación contra criterios de aceptación → commit `feat(NN): …`.
- Aprobar la spec **no** autoriza a implementar: no se escribe código, ni se ejecutan scripts o pruebas contra APIs de esa spec, hasta aprobar plan y tareas. Si durante la ejecución cambia el enfoque (otro modelo, otra técnica, tareas nuevas), se consulta antes de seguir.
- Plantillas en `specs/_plantillas/`. Principios en `specs/00-constitucion.md`. Estado y trazabilidad en `specs/README.md` (actualizar al cerrar cada spec).
- Las specs, la documentación y las respuestas al usuario van siempre en español.

## Entorno

- Python 3.12 gestionado con `uv` (`uv sync`, `uv run …`, `uv add …`). No usar `pip` directamente.
- Webhook: `uv run uvicorn webhook.main:app --reload --port 8000`, expuesto con **ngrok** (`ngrok http --url=<dominio-propio> 8000`; cada persona usa su dominio fijo gratuito, anotado en su `CLAUDE.local.md`, ignorado por git). En Fulfillment: `https://<dominio-propio>/webhook` y cabecera `X-Visoria-Token` (valor de `WEBHOOK_TOKEN` en `.env`). Se descartó el túnel de VS Code por latencia (ver decisiones de la spec 03).
- Datos ficticios de la clínica: fuente única en `webhook/datos.py` (los documentos de la spec 04 se generan desde ahí).
- Voz: `uv run python -m voz.cliente_voz` (Enter para hablar; termina por silencio) o `--texto`; `--silencio` no reproduce audio (pruebas automáticas). El webhook solo devuelve SSML si `originalDetectIntentRequest.payload.canal == "voz"`. Registros de sesión en `voz/registros/` (no versionados).
- Documentos y OCR (offline, nunca en el webhook): `uv run python -m ocr.generar_documentos` y `uv run python -m ocr.ocr` (escribe `ocr/salida/documentos.json`, versionado). Si cambian precios u horarios en `webhook/datos.py`, regenerar ambos: `tests/test_ocr.py` falla si no coinciden.
- Pruebas contra Dialogflow real (`detect_intent`): espaciarlas ~2 s; la edición Trial limita las consultas por minuto.
- Consulta documental: `webhook/documentos.py` (Gemini `gemini-3.5-flash-lite`). Los tests **siempre** simulan el modelo (`ModeloSimulado` en `tests/conftest.py`); la evaluación real es `uv run python -m scripts.evaluar_documental` (gasta 27 de las 500 peticiones diarias gratuitas, ~3 min).
- Tests: `uv run pytest`. Lint: `uv run ruff check .`.
- Tesseract con el idioma `spa` (Homebrew en macOS; instalador de UB-Mannheim en Windows). Solo hace falta para regenerar el OCR. En Windows, `tesseract` debe estar en el `PATH` y, si `spa` no está en su carpeta `tessdata`, definir `TESSDATA_PREFIX` hacia una carpeta que lo contenga.
- Windows: `tzdata` está en las dependencias porque `zoneinfo` no trae zonas horarias. Si se cambia el `.env`, reiniciar el webhook.

## Reglas

- Voz solo con STT/TTS nativos de Dialogflow (sin servicios externos de voz).
- Latencia < 5 s por turno: nada de OCR en la petición; el LLM siempre con `try/except` y respuesta de reserva.
- El LLM responde solo con información de los documentos procesados por OCR (sin conocimiento propio); si el dato no está, lo dice explícitamente. El texto completo de los documentos se incluye en el prompt.
- Secretos solo en `.env` o fuera del repo. Datos de pacientes siempre ficticios.
- El usuario configura el agente Dialogflow **a mano** en la consola; Claude no lo crea ni lo modifica por API. Claude redacta la guía paso a paso (en el `plan.md` de la spec) y guía al usuario durante la configuración.
- Tras cada cambio, el usuario exporta el ZIP (⚙️ → Export and Import → Export as ZIP); se incorpora con `uv run python scripts/preparar_export.py <ruta-al-zip-descargado>` (sustituye el token del webhook por `<WEBHOOK_TOKEN>`; **nunca copiar el ZIP a mano**), se verifica con `uv run pytest tests/test_agente_export.py` y pruebas `detect_intent`, y se hace commit. El ZIP de entrega es el último export.
- Material de clase de referencia, si se dispone de él (no modificar): `../../webhook_dialogflow/` y `../../Asegurador-Demo2/`.

## Trabajo en equipo

- **Aprobaciones:** spec y, después, plan + tareas los aprueba el equipo (las personas que aportan), no una sola. Quien no ha escrito el cambio lo revisa y lo verifica contra los criterios de aceptación.
- **Ramas:** `spec/NN-nombre` por cada spec y `docs/nombre` para cambios solo de documentación. Una PR por rama, fusionada con commit de merge.
- **Commits:** `tipo(NN): descripción` en español, con tipo `docs`, `feat`, `fix`, `test` o `chore`. Los cambios de entorno sin funcionalidad van como `chore:` sin spec. Antes de commitear, revisar que `git diff` solo muestra los cambios previstos (en Windows, los finales de línea pueden añadir ruido).
- **Tests:** solo los imprescindibles, uno por criterio de aceptación o regla de negocio relevante. Siempre con Gemini y Dialogflow simulados.
- **Configuración personal** (dominio de ngrok, rutas, sistema operativo): en `CLAUDE.local.md` y `.env`, nunca en ficheros versionados.
