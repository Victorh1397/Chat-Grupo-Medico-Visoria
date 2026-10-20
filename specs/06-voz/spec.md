# Spec 06 — Voz de extremo a extremo

- **Estado:** Spec aprobada
- **Rúbrica:** Voz (2 pts): conversación completa por STT y TTS, naturalidad con SSML y latencia por debajo de 5 s por turno.
- **Depende de:** [Spec 02](../02-agente-dialogflow/spec.md), [Spec 03](../03-webhook-fastapi/spec.md), [Spec 05](../05-consulta-documental/spec.md)

## Problema / objetivo

Hasta ahora toda la conversación se ha probado por texto. El enunciado exige que funcione **por voz de principio a fin**: el
usuario habla y Vicky responde hablando, con el **STT y el TTS nativos de Dialogflow** (modo audio, como en la segunda sesión).
Esta spec construye el cliente de voz, mejora la naturalidad de Vicky con **SSML** y mide la **latencia por turno**.

## Alcance

**Incluye**
- Cliente de voz en Python que graba el micrófono, envía el audio a Dialogflow y reproduce la respuesta hablada (parte de
  `webhook_dialogflow/cliente_voz.py` de clase).
- Voz femenina de Vicky configurada desde el cliente (voz, velocidad).
- SSML en las respuestas del webhook cuando la conversación es por voz: pausas, códigos y números leídos de forma natural.
- Ayudas al reconocimiento de voz (palabras esperadas: especialidades, nacionalidades, nombres de médicos).
- Medición de la latencia de cada turno y resumen al terminar la conversación.
- Pruebas por voz de la conversación modelo y de los casos difíciles (cédula dictada, fechas y horas habladas).

**Fuera de alcance**
- STT/TTS de terceros (descartado en la planificación).
- Interrupciones (hablar mientras Vicky habla) y corrección de datos a mitad de flujo (spec 09).
- Telegram (spec 08): aquí solo se garantiza que el SSML no aparezca en los canales de texto.

## Requisitos

### R1. Cliente de voz
1. Se ejecuta en la terminal (`uv run python -m voz.cliente_voz`) y usa **una sesión por conversación** (contexto y parámetros se conservan entre turnos).
2. La conversación la empieza el usuario (por ejemplo, "hola" o "quiero una cita"); Vicky no saluda por su cuenta al arrancar.
3. El usuario pulsa **Enter para hablar**; la grabación termina sola tras **~1,5 s de silencio** (o a los 10 s como máximo), en vez de un tiempo fijo.
4. Muestra en pantalla, en cada turno: lo que Dialogflow entendió, la intención, los parámetros, la respuesta de Vicky y la latencia.
5. Modo texto opcional (`--texto`) para escribir en lugar de hablar, útil para probar sin micrófono; Vicky sigue respondiendo con voz.
6. Errores (sin micrófono, sin red, cuota) se muestran con un mensaje claro sin cerrar el programa de forma abrupta.

### R2. Reconocimiento de voz (STT nativo)
1. Audio LINEAR16 a 16 kHz, mono, idioma `es`.
2. Se envían **pistas de frases** a Dialogflow (especialidades, "venezolano", "extranjero", nombres de médicos, "cédula") para mejorar el reconocimiento.
3. La cédula dictada se reconoce aunque el STT la escriba con separadores o agrupada; si llegara en palabras ("catorce millones…"),
   el webhook la convierte a cifras antes de validarla.

### R2b. Pregunta de la hora con disponibilidad (añadido tras la primera prueba por voz)
1. Cuando Vicky va a preguntar la hora (ya hay especialidad y fecha válidas), en lugar de la pregunta genérica indica quién
   atiende ese día, su horario y el primer horario libre. Ejemplo: *"Ese día atiende la doctora Patricia Medina de 8:00 a 12:00;
   el primer horario libre es a las 8:00. ¿A qué hora le conviene?"*
2. Si el usuario responde sin una hora concreta ("a cualquier hora en la mañana"), Vicky repite esa misma información.
3. Si ese día ya no quedan horarios libres, lo dice y vuelve a pedir la fecha.
4. Fuera de alcance por ahora: elegir la hora automáticamente a partir de "en la mañana" o "la que tenga" y aceptar un "sí" a la
   hora sugerida (anotado como mejora futura).

### R2c. Cédula en la confirmación (añadido tras la segunda prueba por voz)
La pregunta de confirmación incluye el nombre y la cédula del paciente (*"…¿Confirmo la cita a nombre de María González,
cédula 14523987?"*), para que un error al dictarla se detecte antes de confirmar y se pueda responder "no". Corregir un dato
sin empezar de nuevo queda para la spec 09.

### R3. Voz de Vicky (TTS nativo) y SSML
1. Voz **femenina** en español con **acento latinoamericano**, configurada en la petición (no depende de la consola).
2. Las respuestas del webhook usan **SSML solo cuando la conversación es por voz**:
   - Pausas breves entre frases.
   - Códigos (`CIT-48213`, `VIS-12345`) leídos carácter a carácter.
   - Cédulas leídas por grupos de cifras, no como "catorce millones…".
   - Precios y horas leídos con naturalidad ("40 dólares", "las 10").
3. En los canales de texto (simulador de Dialogflow, Telegram) no aparece ninguna etiqueta SSML.

### R4. Latencia
1. El cliente mide cada turno desde que termina la grabación hasta que empieza a sonar la respuesta.
2. Al cerrar la conversación muestra mediana y máximo.
3. Por voz, Gemini responde en **una sola frase de como máximo 25 palabras** (en texto, hasta tres frases): la síntesis de una respuesta larga llevó un
   turno a 5,43 s en la segunda prueba.
3. Objetivo: **< 5 s por turno**, incluidos los turnos con Gemini.

## Criterios de aceptación

- **CA-1.** La conversación modelo de la spec 01 (saludo, cita de María González en dermatología, confirmación y una pregunta
  documental) se completa **solo por voz**, sin escribir nada.
- **CA-2.** Dictando la cédula (`14523987`), la nacionalidad, la especialidad, "el próximo martes" y "a las 10 de la mañana",
  Dialogflow los reconoce y Vicky avanza sin repetir preguntas en al menos 4 de cada 5 intentos.
- **CA-3.** Vicky habla con voz femenina en español; el código de cita se oye letra a letra y hay pausas naturales entre frases.
- **CA-4.** En el simulador de Dialogflow (texto) las respuestas aparecen sin etiquetas SSML.
- **CA-5.** Latencia por turno < 5 s en todos los turnos de la conversación modelo; el cliente muestra mediana y máximo.
- **CA-6.** La grabación termina sola tras el silencio.
- **CA-8.** Al llegar a la pregunta de la hora, Vicky dice quién atiende ese día, su horario y el primer horario libre; si se
  responde sin hora concreta, lo repite en vez de la pregunta genérica.
- **CA-7.** Tests automáticos (sin micrófono ni red) de la generación de SSML, la detección del canal y la conversión de cédulas habladas.

## Decisiones técnicas

| Tema | Decisión | Motivo |
|---|---|---|
| STT/TTS | Nativos de Dialogflow en modo audio (`detect_intent` con audio de entrada y salida) | Lo pide el enunciado como válido; una sola llamada por turno, menos latencia |
| Fin de la grabación | Detección de silencio por energía del audio | Más natural que 5 s fijos y reduce la latencia percibida |
| SSML por canal | El webhook solo añade SSML si la petición viene del cliente de voz | El SSML se vería como texto en el simulador y en Telegram |
| Voz | Configurada en cada petición desde el cliente | Reproducible sin depender de ajustes manuales de la consola |

## Decisiones del autor

- Voz femenina con acento latinoamericano.
- La grabación termina por silencio automático.
- Vicky **no** saluda al arrancar: la conversación la empieza el usuario.
