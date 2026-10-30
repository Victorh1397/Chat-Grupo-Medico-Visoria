# Plan 09 — Corrección de datos e interrupciones en la cita

Implementa: [spec.md](spec.md)

## Enfoque

Dos capacidades sobre el flujo de cita existente, sin tocar la recogida de los siete datos:

1. **Corregir:** una intención nueva `corregir_dato`, que solo se activa con la cita en curso, borra el dato indicado y reabre la
   recogida preguntando solo ese. El resto de datos se conserva y las validaciones de siempre (cédula, fecha, hora) se vuelven a
   aplicar porque el manejador de `agendar_cita` las ejecuta en cada turno.
2. **Interrumpir:** si hay una cita a medias, `consulta_documental` y el fallback responden la pregunta y **reabren la recogida** donde
   estaba (misma pregunta pendiente). Las preguntas que Dialogflow clasifica mal como `agendar_cita` se detectan en el webhook
   cuando el dato esperado no se ha entendido y el texto parece una pregunta.

La reapertura reutiliza `repreguntar()` de `webhook/dialogflow.py`, que ya reescribe los contextos de recogida. El agente se sigue
configurando **a mano** (constitución, principio 5); el webhook solo hace lo que la consola no puede.

## Ficheros afectados

| Fichero | Cambio |
|---|---|
| `agente/` (export) | Intención `corregir_dato`, entidad `@dato_cita` y frases de entrenamiento nuevas en `consulta_documental` |
| `entrega/agente_dialogflow.zip` | Último export, generado con `scripts/preparar_export.py` |
| `webhook/dialogflow.py` | `repreguntar()` admite una intención de destino distinta de la actual; lectura de los datos desde `ctx_cita_en_curso` |
| `webhook/intenciones.py` | Manejador `corregir_dato`; retoma de la cita tras `consulta_documental` y fallback; detección de pregunta en `agendar_cita` |
| `tests/test_correccion.py` | Tests nuevos, mínimos (ver Verificación) |
| `tests/test_agente_export.py` | Comprueba la intención y la entidad nuevas |
| `README.md`, `specs/README.md` | Intenciones, trazabilidad, limitaciones (quitar la mejora futura 09) |

## Diseño

### Consola de Dialogflow (lo hacéis a mano; guía abajo)

| Elemento | Detalle |
|---|---|
| Entidad `@dato_cita` | Personalizada, sin regex. Valores: `nombre`, `apellido`, `nacionalidad`, `cedula`, `especialidad`, `fecha`, `hora`, cada uno con sinónimos ("documento", "día", "horario"…) |
| Intención `corregir_dato` | Contexto de entrada `ctx_cita_en_curso` (así solo existe durante una cita). Parámetro `dato` (`@dato_cita`, **no obligatorio**). Webhook activado. Respuesta estática de reserva |
| Frases de `corregir_dato` | "Me equivoqué con la cédula", "La fecha no es esa", "Quiero cambiar la hora", "No, la cédula está mal", "Cambio la especialidad", "Me equivoqué" (sin dato) |
| `consulta_documental` | Frases nuevas sobre menores, acompañantes, retrasos… ("¿Mi hijo menor de edad puede ir solo a la consulta?") para CA-7 |

Con `ctx_cita_en_curso` como entrada, "no, la cédula está mal" puede coincidir con `corregir_dato` y con `agendar_cita - no`; las
frases con "no, …" van en `corregir_dato` para que gane la más específica. Si no gana, se ajusta en la tarea de pruebas.

### Webhook

**`corregir_dato`**
1. Lee los datos de la cita de los parámetros del contexto `ctx_cita_en_curso`.
2. Si `dato` viene vacío: pregunta "¿Qué dato desea corregir: nombre, nacionalidad, cédula, especialidad, fecha u hora?" (la
   respuesta se reconoce con el mismo `@dato_cita`).
3. Si trae dato (y valor nuevo en la frase, p. ej. "la cédula es 14523987"): lo fija y continúa; si no, vacía ese parámetro con
   `repreguntar(..., parametro=dato)`. Los demás no se tocan. Al cambiar `especialidad` o `fecha` se deja `hora` como está: la
   validación habitual del manejador la rechaza con su motivo si ya no encaja (R1.4).
4. Ante la propuesta (todos los datos presentes), `repreguntar()` ya cierra `ctx_cita_en_curso` y el follow-up, de modo que no puede
   confirmarse una cita con datos pendientes de corregir.

**Retoma tras una pregunta (R2)**
- En `consulta_documental` y `fallback`, si hay cita a medias (existe `ctx_cita_en_curso` con datos y falta alguno), se añade a la
  respuesta la pregunta pendiente (`PREGUNTAS[...]`, la de `pregunta_anterior[sesion]`) y se reabren los contextos de recogida.
- Si Gemini no tiene el dato, se da el mensaje habitual y también se retoma.

**Preguntas absorbidas por `agendar_cita` (R2.4)**
- Solo cuando Dialogflow **no entendió el dato esperado** (parámetro vacío tras el turno) y el texto parece pregunta (signos de
  interrogación o palabra interrogativa inicial: qué, cuál, cuánto, cómo, dónde, cuándo, quién, puedo, tienen, hay…), se llama a
  `responder_con_documentos` y se retoma. Si no es pregunta, el comportamiento actual no cambia.
- El filtro evita llamar a Gemini en cada turno de recogida (latencia y cuota).

## Guía de configuración de la consola (a mano)

1. **Entities → Create Entity** `dato_cita`: siete valores con sus sinónimos, **Define synonyms** activado.
2. **Intents → Create Intent** `corregir_dato`:
   - **Contexts → Input contexts:** `ctx_cita_en_curso`.
   - **Training phrases:** las de la tabla; marcar la palabra del dato (cédula, fecha, hora…) como `@dato_cita` → parámetro `dato`.
   - **Parameters:** `dato` no obligatorio.
   - **Responses:** texto de reserva "Disculpe, ¿qué dato desea cambiar?".
   - **Fulfillment:** *Enable webhook call for this intent*.
3. **Intents → consulta_documental:** añadir las frases nuevas.
4. **Export:** ⚙️ → Export and Import → *Export as ZIP*. Incorporarlo con `scripts/preparar_export.py <ruta-al-zip>` (nunca copiar el ZIP a mano).

## Riesgos y mitigación

- **Dialogflow no reabre la recogida con el dato borrado como se espera.** Es la mayor incógnita. Mitigación: la primera tarea es una
  prueba corta con el agente real, antes de escribir el manejador. Si `repreguntar()` no basta, la alternativa es el evento
  `INICIAR_CITA` con parámetros prerrellenados (`followupEventInput.parameters`).
- **La pregunta del usuario hace que Dialogflow cambie de intención y se pierda el contexto.** Mitigación: la retoma reescribe los
  contextos de recogida; si hiciera falta, se amplía el ciclo de vida de `ctx_cita_en_curso` desde el webhook.
- **Falsos positivos del filtro de preguntas** (un nombre raro tomado por pregunta). Mitigación: solo actúa si el dato esperado no
  se entendió; en caso de duda se mantiene el comportamiento actual.
- **Cuota de Dialogflow Trial.** Pruebas espaciadas ~2 s, como indica CLAUDE.md.
- **Las IDs de intención son del agente.** El código obtiene la ID de la propia petición, nunca de valores fijos.

## Verificación

| Criterio | Cómo se comprueba |
|---|---|
| CA-1, CA-2 | Test del manejador `corregir_dato` (cédula válida y no válida) + prueba por `detect_intent` |
| CA-3, CA-4 | Test de la corrección ante la propuesta y de la revalidación de hora + prueba por `detect_intent` |
| CA-5, CA-6 | Test de la retoma tras `consulta_documental` (con datos y sin respuesta) + prueba por `detect_intent` |
| CA-7 | Frases nuevas en el export (`test_agente_export`) + prueba por `detect_intent` en conversación nueva y a medias |
| CA-8 | La batería de tests existente sigue pasando (290) + conversación modelo por texto y por voz |
| CA-9 | Prueba en Telegram (botones) y comprobación de que SSML solo sale en el canal de voz |
| CA-10 | `uv run pytest` y `uv run ruff check .` en verde con tests nuevos mínimos |
