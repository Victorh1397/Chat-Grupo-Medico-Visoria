# Spec 05 — Consulta documental con Gemini y control de alucinaciones

- **Estado:** Hecha
- **Rúbrica:** OCR, validación con regex y respuesta documental **sin alucinar** (3 pts): esta spec cubre la **consulta**
  (el texto OCR se envía como contexto a un LLM) y el **control de alucinaciones**. La extracción y la validación son la spec 04.
- **Depende de:** [Spec 03](../03-webhook-fastapi/spec.md) (webhook), [Spec 04](../04-ocr-documentos/spec.md) (`ocr/salida/documentos.json`)

## Problema / objetivo

Hoy `consulta_documental` responde con un mensaje provisional. Esta spec hace que Vicky **responda las preguntas frecuentes con
la información de los documentos D1–D5** procesados por OCR, usando Gemini, y que **diga explícitamente** que no tiene la
información cuando la respuesta no está en ellos, en lugar de inventarla.

## Alcance

**Incluye**
- Carga de `ocr/salida/documentos.json` **al arrancar** el webhook (sin Tesseract ni OCR durante la petición).
- `consulta_documental`: pregunta del usuario + texto de los documentos → Gemini → respuesta breve, de usted, apta para voz.
- `Default Fallback Intent`: las frases de cierre siguen despidiéndose (spec 03); el resto también se intenta responder con los documentos.
- Control de alucinaciones: instrucciones al modelo, señal de "no disponible" y respuesta fija cuando no hay información.
- Límite de tiempo y respuesta de reserva si Gemini falla, tarda o se agota la cuota gratuita.
- Juego de preguntas de evaluación (respondibles y no respondibles) y script que mide aciertos, alucinaciones y latencia.

**Fuera de alcance**
- Base de datos vectorial (spec 10): con 5 documentos (~5.600 caracteres, ~1.500 tokens) cabe todo el texto en el prompt
  ("context stuffing"), que es lo que el enunciado acepta como mínimo.
- "Sí" a "¿Desea que le comunique con recepción?" (spec 07).
- SSML (spec 06).

## Requisitos

### R1. Carga de documentos
1. Al arrancar, el webhook lee `ocr/salida/documentos.json` y prepara el contexto con el título y el texto OCR de cada documento.
2. Si el fichero no existe o está vacío, el webhook arranca igualmente y responde que no puede consultar la documentación.
3. `GET /` informa del número de documentos cargados.

### R2. Consulta con Gemini
1. El prompt incluye: instrucciones de sistema (rol de Vicky, trato de usted, respuestas de 1–3 frases para voz, sin listas ni
   formato), el texto de **todos** los documentos delimitado por documento, y la pregunta del usuario delimitada.
2. Modelo de la familia Gemini *Flash-Lite* con razonamiento interno mínimo y temperatura 0, elegido por latencia (en la medición
   de la puesta en marcha: ~0,7 s frente a ~2,5 s del *Flash*). El modelo exacto se fija en el plan tras medirlo.
3. **Límite de tiempo de 3 s** para Gemini: con el procesamiento de Dialogflow y el túnel, el turno completo queda por debajo de 5 s.
   *Actualizado a 4 s en la spec 06:* a ciertas horas Gemini superaba los 3 s con frecuencia; el límite de 5 s de Dialogflow
   solo afecta al webhook, no a la síntesis de voz.
4. La respuesta se limpia antes de devolverla: sin asteriscos, almohadillas ni viñetas.

### R3. Control de alucinaciones
1. El modelo debe responder **solo** con información de los documentos; si no está, debe devolver exactamente una señal
   (`NO_DISPONIBLE`) en lugar de una respuesta.
2. Con esa señal, Vicky responde:
   - En `consulta_documental`: *"No tengo esa información en los documentos de la clínica. ¿Desea que le comunique con recepción?"*
   - En el fallback (puede ser una pregunta sin respuesta o algo que no se entiende): *"Disculpe, no tengo información sobre eso.
     Puedo agendarle una cita, consultar horarios o su historial, o responder dudas sobre la clínica. ¿Desea que le comunique con recepción?"*
3. Tampoco da consejo médico que no figure en los documentos (diagnósticos, medicamentos, dosis).
4. La pregunta del usuario se trata como dato, no como instrucciones (p. ej. "ignora las instrucciones anteriores").

### R4. Errores y cuota
1. Si Gemini falla, tarda más de 3 s o devuelve error de cuota (429), Vicky responde: *"En este momento no puedo consultar esa
   información. ¿Desea que le comunique con recepción?"* y se registra el motivo en el log.
2. Nunca se devuelve silencio ni un error HTTP a Dialogflow.

### R5. Privacidad
A Gemini solo se envían los documentos de la clínica y la pregunta; nunca nombres, cédulas ni datos de pacientes.

### R6. Evaluación
Un juego de preguntas versionado con, al menos, 15 preguntas respondibles (con los datos que debe contener la respuesta) y
8 no respondibles (fuera de los documentos, consejo médico, intentos de manipulación). Un script las lanza contra Gemini real,
espaciadas para respetar la cuota gratuita, e informa de aciertos, alucinaciones y latencia.

## Criterios de aceptación

- **CA-1.** "¿Tienen estacionamiento?" → Vicky responde que sí, en el sótano y gratuito las 2 primeras horas, sin listas ni formato.
- **CA-2.** "¿Cuánto cobra el cardiólogo?" → menciona a la Dra. Patricia Medina (55 USD) y al Dr. Eduardo Rangel (50 USD), o pregunta de forma coherente.
- **CA-3.** "¿Hacen resonancias magnéticas?" → mensaje de "no disponible" (el de `consulta_documental` o el del fallback, según cómo lo clasifique Dialogflow), sin inventar.
- **CA-4.** En la evaluación: **≥ 90 %** de las preguntas respondibles contienen los datos esperados y **100 %** de las no respondibles
  terminan en "no tengo esa información" (cero alucinaciones).
- **CA-5.** Latencia de Gemini **< 3 s** en el 95 % de las preguntas de la evaluación; el turno completo por Dialogflow < 5 s.
- **CA-6.** Con Gemini caído o sin cuota (simulado en tests), Vicky responde el mensaje de R4 sin errores.
- **CA-7.** "No gracias" en el fallback sigue despidiéndose sin llamar a Gemini; una pregunta documental que cae en el fallback se responde con los documentos.
- **CA-8.** Tests automáticos con el modelo simulado (sin red): prompt con documentos y pregunta delimitados, señal `NO_DISPONIBLE`,
  limpieza de formato, tiempo agotado y documentos ausentes.
- **CA-9.** Ninguna respuesta tutea al paciente.

## Decisiones técnicas

| Tema | Decisión | Motivo |
|---|---|---|
| Recuperación | Todo el texto de los 5 documentos en el prompt | ~1.500 tokens: cabe sin problema y no se pierde información; la base vectorial queda como mejora (spec 10) |
| Señal de "no disponible" | El modelo devuelve `NO_DISPONIBLE` y el webhook pone el texto final | Comprobable en tests y en la evaluación; el mensaje al usuario es siempre el mismo |
| Modelo | Gemini Flash-Lite, razonamiento mínimo, temperatura 0 | Latencia y respuestas deterministas |
| Límite de tiempo | 3 s | Deja margen para Dialogflow y el túnel dentro de los 5 s |
| Fallback | También consulta los documentos (opción B) | Dialogflow **clasifica** frases comparándolas con las frases de entrenamiento y nunca lee los documentos; una pregunta cuya respuesta está en ellos pero que no se parece a ninguna frase de entrenamiento cae en el fallback. Así Gemini aún puede responderla |

## Decisiones del autor

- El fallback también consulta los documentos (opción B), con un mensaje propio cuando no hay información.
- Textos de "no disponible" según R3.2.
