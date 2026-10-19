# Specs — proceso SDD

## Flujo de trabajo

1. **Spec** (`spec.md`): qué se necesita y por qué, alcance, criterios de aceptación. La aprueba el autor del proyecto.
2. **Plan** (`plan.md`): cómo se implementa (ficheros, intents, contratos, riesgos).
3. **Tareas** (`tareas.md`): checklist pequeño y ordenado.
4. **Implementación** y verificación contra los criterios de aceptación.
5. **Cierre**: commit `feat(NN): …` y actualización de esta página.

Plantillas en [`_plantillas/`](_plantillas/). Principios en [`00-constitucion.md`](00-constitucion.md).

## Estado de las specs

| # | Spec | Rúbrica | Estado |
|---|---|---|---|
| 01 | [Caso de uso Visoria + mapa de intenciones](01-caso-de-uso/spec.md) | Agente (4) | Spec aprobada |
| 02 | [Agente Dialogflow ES: intents, entidades, contexto, follow-up](02-agente-dialogflow/spec.md) | Agente (4) | Hecha |
| 03 | [Webhook FastAPI: validación regex, lógica de negocio](03-webhook-fastapi/spec.md) | Agente / Webhook | Spec aprobada |
| 04 | Pipeline OCR offline + regex sobre el texto | OCR (3) | Pendiente |
| 05 | Consulta documental con Gemini + control de alucinaciones | OCR (3) | Pendiente |
| 06 | Voz extremo a extremo (cliente de voz, SSML, latencia) | Voz (2) | Pendiente |
| 07 | Extra: transferencia a agente humano | +1,5 | Pendiente |
| 08 | Extra: Telegram (integración nativa, texto + botones) | +1,5 | Pendiente |
| 09 | Extra: corrección de datos a mitad de flujo con eventos | +1,5 | Pendiente |
| 10 | Extra: ChromaDB | +1,5 | Pendiente |
| 99 | Entregables: README, diagrama, ZIP del agente, vídeo ≤ 3 min | Docs (1) | Pendiente |

Estados: Pendiente → Spec redactada → Spec aprobada → En implementación → Hecha.

## Matriz de trazabilidad (requisito del PDF → spec → evidencia)

| Requisito del enunciado | Spec | Evidencia |
|---|---|---|
| 5–6 intenciones + bienvenida + fallback | 01, 02 | `agente/intents/` · `tests/test_agente_export.py` (CA-1) |
| Entidad regex + entidad de sistema/personalizada | 02 | `agente/entities/cedula*.json` (regex), `especialidad`, `nacionalidad`, `@sys.date/time/given-name/last-name` · tests CA-2 |
| Flujo multi-turno con contexto + confirmación sí/no | 02, 03 | `agendar_cita` + `ctx_cita_en_curso` + follow-ups · tests CA-3/CA-5 · pruebas `detect_intent` (spec 02) |
| Voz extremo a extremo (STT/TTS nativos), SSML, < 5 s | 06 | |
| Webhook FastAPI expuesto, valida parámetro con regex, respuesta dinámica | 03 | |
| OCR de 3–5 documentos (offline) | 04 | |
| Regex sobre el texto extraído | 04 | |
| Texto en fichero + LLM con contexto | 05 | |
| Control de alucinaciones | 05 | |
| ZIP del agente + script OCR + webhook | 02, 99 | `entrega/agente_dialogflow.zip` (export de la spec 02; se actualizará) |
| README (caso de uso, diagrama, intenciones, decisiones, instrucciones) | 99 | |
| Vídeo ≤ 3 min | 99 | |
