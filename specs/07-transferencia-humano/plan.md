# Plan 07 — Transferencia a agente humano

Implementa: [spec.md](spec.md)

## Enfoque

Todo en el webhook, sin cambios en la consola de Dialogflow. Un módulo nuevo `webhook/transferencia.py` crea y registra los casos;
el estado por sesión (oferta pendiente, turnos sin entender, datos de la cita en curso) vive en memoria, como las propuestas de cita
de la spec 03. La detección de la oferta se hace **en un único punto** (`main.py`), sobre el texto de la respuesta antes de pasarlo a SSML.

```
respuesta de Vicky termina en "¿Desea que le comunique con recepción?"  ─► se guarda la oferta de esa sesión (motivo + pregunta)
siguiente turno ─► ¿fallback con "sí"?  ─► caso VIS-##### + mensaje según horario
                 ─► ¿fallback con "no"?  ─► "De acuerdo. ¿Le puedo ayudar en algo más?"
                 ─► otra cosa            ─► se atiende con normalidad; la oferta caduca
```

## Ficheros

| Fichero | Cambio |
|---|---|
| `webhook/transferencia.py` | `Caso` (número, fecha, canal, motivo, pregunta, resumen); `crear_caso()`; registro en `logs/transferencias.jsonl`; `mensaje()` según el horario de la clínica (`HORARIO_CLINICA`, hora de Caracas); detección de "sí"/"no"; estado por sesión (oferta pendiente y turnos sin entender) |
| `webhook/main.py` | Antes del manejador: recoger la oferta pendiente de la sesión y, si el turno es un fallback con "sí"/"no", responder directamente. Después: si la respuesta termina en la oferta, guardarla con su motivo; reiniciar el contador de turnos sin entender si la intención no es el fallback |
| `webhook/intenciones.py` | `transferir_humano` usa `crear_caso()` (motivo "petición directa"); el fallback cuenta los turnos sin información y al segundo cambia el texto por la oferta automática; `agendar_cita` guarda por sesión los datos ya dados (para el resumen) |
| `tests/test_transferencia.py` | R1–R5 y CA-1 a CA-7 con peticiones de ejemplo y hora simulada (dentro y fuera de horario) |
| `.gitignore` | `logs/` ya está ignorado |

## Diseño

### Motivo según la oferta
| Texto de la oferta | Motivo |
|---|---|
| "No tengo esa información…" / "Disculpe, no tengo información sobre eso…" | `informacion_no_disponible` |
| "En este momento no puedo consultar…" / "tuve un problema técnico…" | `error_tecnico` |
| "Parece que no le estoy entendiendo bien…" | `no_entendido` |

### "Sí" y "no"
Regex sobre el texto completo del usuario: afirmativo `^(sí|si|claro|por favor|de acuerdo|ok|vale|está bien|sí,? por favor|…)$`;
negativo `^(no|no,? gracias|mejor no|ahora no)$`. Si el texto es una pregunta u otra cosa, la oferta caduca sin más.

### Resumen del caso
- Pregunta del usuario que motivó la oferta (o la frase de la petición directa).
- Si hay una cita en curso en la sesión: nombre, apellido, especialidad y fecha; cédula como `***987`.

### Horario de recepción
Abierto si el día de la semana está en `HORARIO_CLINICA` y la hora actual de Caracas cae entre apertura y cierre. Los tests fijan la
hora (como en la spec 03) para probar ambos mensajes.

## Riesgos y mitigación

| Riesgo | Mitigación |
|---|---|
| Un "sí" llega a otra intención en vez de al fallback | Verificado en la spec 02 que "sí"/"no" sueltos van al fallback; prueba por Dialogflow |
| Ofertas de las respuestas de reserva estáticas de Dialogflow (webhook caído) | No se pueden detectar sin webhook; caso aceptado |
| El estado en memoria se pierde al reiniciar | Igual que las citas (demo) |

## Resultado (19/10/2026, por Dialogflow en texto, fuera del horario de recepción)
- "¿Hacen resonancias magnéticas?" → oferta → "sí, por favor" → caso `informacion_no_disponible` con la pregunta original.
- La misma oferta → "no gracias" → "De acuerdo. ¿Le puedo ayudar en algo más?".
- Dos frases sin sentido → oferta automática → "sí" → caso `no_entendido`.
- A mitad de la cita, "quiero hablar con una persona" sale del flujo; el caso incluye nombre, especialidad y cédula `***987`.
- Tras una pregunta intermedia, un "sí" ya no transfiere (oferta caducada).
- Mensaje de recepción cerrada con el horario. 249 tests.

## Verificación
- `uv run pytest` (tests nuevos con modelo simulado y hora fija).
- Por Dialogflow en texto (Claude): "¿hacen resonancias?" → "sí"; "¿hacen resonancias?" → "no"; dos frases sin sentido → oferta → "sí";
  "quiero hablar con una persona"; a mitad de una cita → "quiero hablar con una persona".
- Opcional por voz (tú).
