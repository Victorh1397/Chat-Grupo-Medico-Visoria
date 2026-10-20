# Specs — proceso SDD

## Flujo de trabajo

1. **Spec** (`spec.md`): qué se necesita y por qué, alcance, criterios de aceptación. La aprueba el autor del proyecto.
2. **Plan** (`plan.md`): cómo se implementa (ficheros, intents, contratos, riesgos).
3. **Tareas** (`tareas.md`): checklist pequeño y ordenado. Plan y tareas **también los aprueba el autor** antes de empezar.
4. **Implementación** y verificación contra los criterios de aceptación.
5. **Cierre**: commit `feat(NN): …` y actualización de esta página.

Plantillas en [`_plantillas/`](_plantillas/). Principios en [`00-constitucion.md`](00-constitucion.md).

## Estado de las specs

| # | Spec | Rúbrica | Estado |
|---|---|---|---|
| 01 | [Caso de uso Visoria + mapa de intenciones](01-caso-de-uso/spec.md) | Agente (4) | Spec aprobada |
| 02 | [Agente Dialogflow ES: intents, entidades, contexto, follow-up](02-agente-dialogflow/spec.md) | Agente (4) | Hecha |
| 03 | [Webhook FastAPI: validación regex, lógica de negocio](03-webhook-fastapi/spec.md) | Agente / Webhook | Hecha |
| 04 | [Documentos sintéticos y pipeline OCR offline + regex](04-ocr-documentos/spec.md) | OCR (3) | Hecha |
| 05 | [Consulta documental con Gemini + control de alucinaciones](05-consulta-documental/spec.md) | OCR (3) | Hecha |
| 06 | [Voz extremo a extremo (cliente de voz, SSML, latencia)](06-voz/spec.md) | Voz (2) | Hecha |
| 07 | [Extra: transferencia a agente humano](07-transferencia-humano/spec.md) | +1,5 | Hecha |
| 08 | [Extra: Telegram (integración nativa, texto + botones)](08-telegram/spec.md) | +1,5 | Hecha |
| 99 | Entregables: README, diagrama, ZIP del agente, vídeo ≤ 3 min | Docs (1) | Pendiente |

Estados: Pendiente → Spec redactada → Spec aprobada → En implementación → Hecha.

## Matriz de trazabilidad (requisito del PDF → spec → evidencia)

| Requisito del enunciado | Spec | Evidencia |
|---|---|---|
| 5–6 intenciones + bienvenida + fallback | 01, 02 | `agente/intents/` · `tests/test_agente_export.py` (CA-1) |
| Entidad regex + entidad de sistema/personalizada | 02 | `agente/entities/cedula*.json` (regex), `especialidad`, `nacionalidad`, `@sys.date/time/given-name/last-name` · tests CA-2 |
| Flujo multi-turno con contexto + confirmación sí/no | 02, 03 | `agendar_cita` + `ctx_cita_en_curso` + follow-ups · tests CA-3/CA-5 (spec 02) · respuestas dinámicas, confirmación `CIT-…` y reinicio con `INICIAR_CITA` (spec 03) · pruebas `detect_intent` |
| Voz extremo a extremo (STT/TTS nativos), SSML, < 5 s | 06 | `voz/cliente_voz.py` (STT/TTS nativos, una llamada por turno) · `webhook/ssml.py` (solo canal voz) · conversación modelo hablada: 10 turnos, mediana 2,1 s, máx. 4,1 s (`docs/evidencias/voz_conversacion_modelo.json`) |
| Webhook FastAPI expuesto, valida parámetro con regex, respuesta dinámica | 03 | `webhook/` (regex en `webhook/cedula.py`) · `tests/test_cedula.py`, `test_agenda.py`, `test_webhook.py` · ngrok + 50 turnos `detect_intent` sin tiempos agotados |
| OCR de 3–5 documentos (offline) | 04 | 5 imágenes en `ocr/documentos/` · `ocr/ocr.py` (Tesseract + preprocesado) · similitud media 99,8 % (`specs/04-ocr-documentos/plan.md`) |
| Regex sobre el texto extraído | 04 | `ocr/extraccion.py` (importes, horarios, teléfonos, fechas) · validación 12/12 precios y horarios contra el webhook · `tests/test_ocr.py` |
| Texto en fichero + LLM con contexto | 04, 05 | `ocr/salida/documentos.json` (spec 04) · `webhook/documentos.py` con Gemini 3.5 Flash-Lite · evaluación 17/18 aciertos, mediana 0,8 s (`evaluacion/resultados_documental.json`) |
| Control de alucinaciones | 05 | Instrucciones + señal `NO_DISPONIBLE` + red de seguridad · 9/9 preguntas sin respuesta (incluidas manipulación y consejo médico) sin inventar · `tests/test_documentos.py` |
| ZIP del agente + script OCR + webhook | 02, 03, 04, 99 | `entrega/agente_dialogflow.zip` (generado sin secretos con `scripts/preparar_export.py`) · `webhook/` · `ocr/` |
| README (caso de uso, diagrama, intenciones, decisiones, instrucciones) | 99 | |
| Vídeo ≤ 3 min | 99 | |
| *Mejora opcional:* integración con Telegram con respuestas enriquecidas (botones) | 08 | Integración nativa de Dialogflow · `webhook/telegram.py` (botones `quickReplies` solo en Telegram) · `tests/test_telegram.py` · prueba en la app |
| *Mejora opcional:* intención de transferencia a agente humano | 07 | `transferir_humano` + `webhook/transferencia.py` (oferta aceptada con "sí", oferta automática, caso con resumen y horario) · `tests/test_transferencia.py` · prueba por Dialogflow |

## Mejoras futuras (fuera del alcance actual)

| Origen | Mejora | Motivo |
|---|---|---|
| Spec 06 | Al preguntar la hora: elegir automáticamente el primer horario libre ante "en la mañana", "por la tarde" o "la que tenga", y aceptar "sí" a la hora sugerida | Detectado en la prueba por voz; requiere que el webhook cierre él mismo la recogida de datos. Por ahora Vicky informa de la disponibilidad (R2b) |
| Hoja de ruta (spec 09, no realizada) | Corrección de datos a mitad de flujo mediante eventos ("me equivoqué con la cédula": volver a pedir solo ese dato sin perder los demás) y gestión de interrupciones (responder una pregunta a mitad de la cita y retomarla) | Mejora opcional del enunciado que se dejó fuera por decisión del autor para cerrar la entrega; diseño previsto: intención `corregir_dato` + evento que reactiva `agendar_cita` y restauración de los datos con contextos |
| Spec 08 | Restringir el bot de Telegram a una lista de usuarios (`TELEGRAM_USUARIOS_PERMITIDOS` en `.env`) | Proteger la cuota gratuita de Gemini; por ahora el bot queda abierto (decisión del autor) |
| Spec 06 | Ampliar las frases de cierre ("gracias", "ok gracias", "adiós", "chao", "hasta luego") para despedirse sin consultar a Gemini | En la prueba por voz, "okay gracias" llegó a Gemini, que respondió una cortesía propia en lugar de `NO_DISPONIBLE` |
| Spec 04 | Corregir en el texto para el LLM **solo los nombres de los médicos** que el OCR lee mal (p. ej. "Hemández" → "Hernández"), comparándolos con `webhook/datos.py` | Evitar que Vicky pronuncie un nombre con errores de OCR. Descartado por ahora: el LLM recibe el texto OCR sin modificar |
