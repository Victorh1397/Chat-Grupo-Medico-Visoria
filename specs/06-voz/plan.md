# Plan 06 — Voz de extremo a extremo

Implementa: [spec.md](spec.md)

## Enfoque

Un cliente de voz en la terminal (paquete `voz/`) que hace **una llamada `detect_intent` por turno** con audio de entrada y
pide audio de salida: Dialogflow transcribe (STT), detecta la intención, llama al webhook y sintetiza la respuesta (TTS).
El cliente marca sus peticiones como "canal voz" y el webhook, solo en ese caso, convierte su respuesta a SSML.
Parte de `webhook_dialogflow/cliente_voz.py` de clase (sesión única, LINEAR16 a 16 kHz, reproducción del WAV), sin modificarlo.

```
micrófono ─► voz/grabacion.py (fin por silencio) ─► detect_intent(audio, pistas de frases, voz de Vicky, payload canal=voz)
                                                        │  STT nativo → intención → webhook (SSML si canal=voz) → TTS nativo
altavoz  ◄─ reproducción del WAV ◄──────────────────────┘
```

## Ficheros

| Fichero | Contenido |
|---|---|
| `voz/grabacion.py` | Grabación con `sounddevice` por bloques de 100 ms; empieza a contar al detectar voz (energía sobre el ruido de fondo medido al inicio) y termina tras ~1,5 s de silencio o 10 s; descarta grabaciones sin voz |
| `voz/cliente_voz.py` | Bucle de conversación: Enter para hablar, `detect_intent` con audio, pistas de frases (`speech_contexts`), voz configurada (`synthesize_speech_config`) y `query_params.payload = {"canal": "voz"}`; muestra transcripción, intención, parámetros, respuesta (sin etiquetas) y latencia; `--texto` para escribir; resumen de latencias al salir; registro JSON de la sesión |
| `webhook/ssml.py` | Texto → SSML: escapa caracteres, pausas entre frases, códigos `CIT-`/`VIS-` leídos carácter a carácter, cédulas por grupos de miles |
| `webhook/numeros.py` | Números dichos en palabras → cifras ("catorce millones quinientos veintitrés mil novecientos ochenta y siete" → 14523987) |
| `webhook/dialogflow.py` | `PeticionDF.canal` (lee `originalDetectIntentRequest.payload.canal`) |
| `webhook/main.py` | Si el canal es voz, pasa `fulfillmentText` a SSML antes de responder (un único punto) |
| `webhook/intenciones.py` | Si el usuario respondió a la pregunta de la cédula y no se extrajo, convertir palabras a cifras y validar |
| `tests/test_ssml.py`, `tests/test_numeros.py`, `tests/test_grabacion.py` | Tests sin micrófono ni red (la grabación se prueba con señales sintéticas) |

## Diseño

### Voz de Vicky
Se configura en cada petición (`OutputAudioConfig.synthesize_speech_config`: voz, velocidad ~0,95). Candidatas femeninas
latinoamericanas `es-US` (Neural2 / WaveNet / Standard): se generan **muestras de audio con la misma frase** para que tú elijas la voz.

### SSML (solo canal voz)
- `<speak>` envolvente; `<break time="250ms"/>` entre frases.
- `CIT-48213` → `<say-as interpret-as="characters">CIT</say-as>, <say-as interpret-as="characters">48213</say-as>`.
- Cédulas de 6–9 cifras → grupos de miles con pausas cortas ("14 · 523 · 987").
- Caracteres especiales escapados (`&`, `<`, `>`).
- El cliente muestra en pantalla el texto sin etiquetas.

### Riesgos verificados primero (T1)
1. **¿El TTS de Dialogflow ES interpreta SSML del webhook?** La documentación no lo confirma explícitamente. Se prueba con una
   respuesta SSML y se escucha. **Plan B:** sin SSML; naturalidad con puntuación (comas, puntos) y códigos escritos separados
   ("C, I, T, 4, 8, 2, 1, 3") solo en canal voz.
2. **¿Llega `query_params.payload` al webhook como `originalDetectIntentRequest.payload`?** Se comprueba en el log del webhook.
   **Plan B:** detectar el canal por la presencia de `outputAudioConfig`… o un parámetro de contexto enviado por el cliente.
3. **Voces disponibles** en el TTS de Dialogflow para `es-US`: se prueban las candidatas y se descartan las que fallen.

### Resultado de la verificación (T1, 19/10/2026)
- **SSML interpretado** si va envuelto en `<speak>`: una pausa `<break time="3s"/>` produjo un silencio de 2,91 s en el audio.
  Sin `<speak>`, las etiquetas no se interpretan (no hay pausa y el audio se alarga). → Se usa SSML; no hace falta el plan B.
- **El payload llega al webhook** (`originalDetectIntentRequest.payload`).
- **Voces:** `es-US-Neural2-A`, `es-US-Wavenet-A` y `es-US-Standard-A` producen exactamente el mismo audio (probablemente no
  disponibles y sustituidas por una voz genérica). Las voces femeninas `es-US-Chirp3-HD-Kore`, `-Aoede` y `-Leda` sí son distintas.

### Latencia por voz (T8)
| Voz | Turno del saludo, sin Gemini (mediana de 4) |
|---|---|
| `es-US-Chirp3-HD-Aoede` | 2,21 s |
| **Por defecto del agente (elegida)** | **1,31 s** |
| Sin audio | 0,69 s |

Respuestas de Gemini por voz limitadas a una frase de 25 palabras (antes 35–40): turnos documentales de 2,2–4,97 s con Aoede.

### Picos de latencia de Gemini y petición de respaldo (T8c, T8d)
- Con límite de 3 s, en la tarde 4 de cada 10 preguntas documentales recibían la respuesta de reserva; con 4 s, seguían fallando:
  las respuestas eran rápidas (0,7–1,1 s) o superaban los 4 s, sin término medio (picos aleatorios de Gemini).
- Petición de respaldo a los 1,5 s y primera respuesta válida: en un webhook de prueba, 12/12 respondidas (máximo 2,6 s, respaldo
  activado 4 veces); por el webhook real y canal voz, 5/5 respondidas, turno completo con mediana 2,99 s y máximo 3,60 s.

### Latencia
Desde el final de la grabación hasta el inicio de la reproducción (incluye STT + webhook + Gemini si aplica + TTS).
Se muestra por turno y, al salir, mediana y máximo. El registro de la sesión (`voz/registros/*.json`, no versionado salvo el de la
demo) sirve de evidencia: transcripción, intención, respuesta y latencia de cada turno.

## Reparto del trabajo

| Quién | Qué |
|---|---|
| Claude | Código, tests, verificación técnica (T1), muestras de voz, análisis de los registros de sesión |
| Tú | Elegir la voz escuchando las muestras; dar permiso de micrófono a VS Code; **hablar** en las pruebas por voz (yo no puedo hablarle al micrófono) |

## Riesgos y mitigación

| Riesgo | Mitigación |
|---|---|
| SSML no interpretado por el TTS de ES | Verificación en T1; plan B con puntuación |
| El STT transcribe mal especialidades o nombres | Pistas de frases con refuerzo; el webhook ya tolera nombres poco comunes |
| Cédula transcrita en palabras | `webhook/numeros.py` |
| Ruido de fondo impide detectar el silencio | Umbral relativo al ruido medido al inicio; corte a los 10 s |
| Cuota de audio de Dialogflow Trial | Pruebas por voz espaciadas; las pruebas automáticas no usan audio |
| Micrófono sin permiso en macOS | Ajustes del Sistema → Privacidad → Micrófono → VS Code |

## Verificación
- `uv run pytest`: SSML, conversión de números, detección de silencio, canal (CA-4 parcial, CA-6 parcial, CA-7).
- Prueba técnica de SSML y canal (T1).
- Conversación modelo por voz hablada por ti, con el registro de sesión como evidencia (CA-1, CA-2, CA-3, CA-5).
- Simulador de Dialogflow por texto sin etiquetas SSML (CA-4).
