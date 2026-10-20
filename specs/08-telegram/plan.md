# Plan 08 — Vicky en Telegram

Implementa: [spec.md](spec.md)

## Enfoque

Telegram se conecta con la **integración nativa de Dialogflow ES**: Dialogflow recibe los mensajes del bot, los procesa con el
mismo agente y llama al mismo webhook. El webhook detecta que la petición viene de Telegram y, **en un único punto** (`main.py`),
añade botones a la respuesta según su texto. Los demás canales no cambian.

```
Telegram ─► Dialogflow (integración nativa) ─► webhook: respuesta normal + botones si canal = telegram ─► Telegram
```

## Ficheros

| Fichero | Cambio |
|---|---|
| `webhook/dialogflow.py` | `PeticionDF.canal` devuelve `"telegram"` si `originalDetectIntentRequest.source == "telegram"` |
| `webhook/telegram.py` | `botones_para(texto)`: elige los botones según la respuesta (menú, especialidades, nacionalidad, sí/no); `con_botones(texto, botones)`: construye `fulfillmentMessages` para la plataforma Telegram |
| `webhook/main.py` | Si el canal es Telegram: (1) durante la recogida de datos, cuando Dialogflow iba a preguntar especialidad o nacionalidad (respuesta vacía), el webhook formula él la pregunta para poder añadir botones; (2) añade botones a cualquier respuesta que los admita |
| `webhook/intenciones.py` | Manejadores nuevos: `Default Welcome Intent` (bienvenida con menú), `agendar_cita - no` ("¿Desea empezar de nuevo?") y respuesta al botón "Preguntas frecuentes" en el fallback |
| `agente/` | Nuevo export tras los cambios de la consola (webhook en bienvenida, en `agendar_cita - no` y slot filling en `consultar_horarios`) |
| `tests/test_telegram.py`, `tests/test_agente_export.py` | Peticiones de ejemplo de Telegram; nuevas intenciones con webhook |

## Diseño

### Botones según la respuesta
| La respuesta… | Botones |
|---|---|
| es la bienvenida | Agendar una cita · Horarios de los médicos · Preguntas frecuentes · Hablar con recepción |
| pregunta la especialidad | Las 6 especialidades |
| pregunta la nacionalidad | Venezolano · Extranjero |
| termina en "¿Confirmo la cita…?", "¿Desea empezar de nuevo?" o la oferta de recepción | Sí · No |

Los textos de los botones del menú se eligen para que Dialogflow los clasifique solo ("Agendar una cita" → `agendar_cita`,
"Horarios de los médicos" → `consultar_horarios`, "Hablar con recepción" → `transferir_humano`). "Preguntas frecuentes" no es una
pregunta concreta: el webhook responde con ejemplos ("Puede preguntarme por el estacionamiento, los precios, los seguros…").

### Formato de los botones (verificado en T1)
Dos opciones que admite Dialogflow ES para Telegram; se elige la que **envíe el texto del botón como mensaje y oculte el teclado tras usarlo**:
1. Mensaje `quickReplies` con plataforma `TELEGRAM`.
2. `payload` personalizado de Telegram con `reply_markup` (teclado de respuesta, `one_time_keyboard`).

### Cambios en la consola (guía para ti)
1. **@BotFather** en Telegram → `/newbot` → nombre `Vicky · Grupo Médico Visoria` → usuario (debe terminar en `bot`, p. ej.
   `VisoriaVickyBot`) → copia el **token**.
2. Dialogflow → **Integrations** → **Telegram** → pega el token → **START**. El token queda solo en la consola.
3. `Default Welcome Intent` → **Fulfillment** → activa **Enable webhook call for this intent** → SAVE.
4. `agendar_cita - no` → activa **Enable webhook call for this intent** → SAVE.
5. `consultar_horarios` → activa **Enable webhook call for slot filling** → SAVE.
6. Exportar el agente e incorporarlo con `scripts/preparar_export.py`.

## Riesgos y mitigación

| Riesgo | Mitigación |
|---|---|
| La integración de Telegram ya no aparece en la consola de Dialogflow ES | Se comprueba en T1 antes de programar nada; si no existe, te consulto el plan B (un bot propio en Python que llama a Dialogflow) |
| El formato de botones no se comporta como se espera | T1 prueba los dos formatos con el bot real |
| Cualquiera puede usar el bot y gastar cuota | Decisión del autor; lista de usuarios como mejora futura |
| El webhook debe estar en marcha (ngrok) para que el bot responda | Igual que el resto de canales |

## Verificación
- `uv run pytest` (peticiones de Telegram simuladas).
- Por Dialogflow con la marca de canal Telegram (Claude): las respuestas llevan los mensajes de botones.
- En la app de Telegram (tú): CA-1 a CA-4 y CA-2b; voz y simulador sin botones (CA-6).
