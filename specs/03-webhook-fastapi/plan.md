# Plan 03 — Webhook FastAPI

Implementa: [spec.md](spec.md)

## Enfoque

Un paquete `webhook/` con FastAPI que recibe la petición de Dialogflow, la envuelve en un objeto cómodo de leer,
despacha por nombre de intención a un manejador y devuelve la respuesta. La lógica de negocio (cédula, agenda) está
separada de FastAPI y de Dialogflow para poder probarla con tests unitarios. Se parte del esqueleto de clase
(`webhook_dialogflow/main.py`: `responder()`, despacho por `displayName`, `allRequiredParamsPresent`) sin modificarlo.

## Ficheros

| Fichero | Contenido |
|---|---|
| `webhook/main.py` | App FastAPI: `GET /`, `POST /webhook`, comprobación de `X-Visoria-Token`, despacho, captura de errores, registro por consola de intención, parámetros, respuesta y latencia |
| `webhook/dialogflow.py` | `PeticionDF` (intención, parámetros, texto, sesión, contextos, `todos_los_datos`) y constructores de respuesta: `texto()`, `evento()`, `repreguntar()` |
| `webhook/datos.py` | Fuente única de datos ficticios: especialidades, médicos (días, horas, precio), pacientes con historial, cita pendiente sembrada |
| `webhook/cedula.py` | Normalización y validación de la cédula con regex según V/E; inferencia de nacionalidad desde texto libre |
| `webhook/agenda.py` | Estado en memoria (citas, propuestas por sesión, pacientes nuevos) y reglas: validar fecha y hora, elegir médico, proponer, confirmar, cancelar, historial, horarios |
| `webhook/textos.py` | Formato hablado: fechas ("el martes 20 de octubre a las 10:00"), "doctor/doctora", listas con "y" |
| `webhook/intenciones.py` | Un manejador por intención que une lo anterior |
| `tests/conftest.py` | Fábrica de peticiones de Dialogflow de ejemplo, token de prueba, reinicio del estado |
| `tests/test_cedula.py`, `tests/test_agenda.py`, `tests/test_webhook.py` | Tests de regex, reglas y endpoint |
| `.env.example`, `CLAUDE.md` | Variable `WEBHOOK_TOKEN` y comando de arranque |

## Diseño

### Petición y respuesta de Dialogflow ES
- Entrada: `session`, `queryResult.{queryText, intent.displayName, intent.name, parameters, allRequiredParamsPresent, outputContexts}`.
- Salida: `{"fulfillmentText": ...}`; para relanzar el flujo, `{"followupEventInput": {"name": "INICIAR_CITA", "languageCode": "es"}}`;
  durante la recogida, `{}` cuando todo es válido (Dialogflow hace su propia pregunta).

### Volver a pedir un dato (`repreguntar`)
Dialogflow guarda el estado de la recogida en contextos de sistema que llegan en la petición:
`<id>_id_dialog_context`, `agendar_cita_dialog_context` (con los parámetros) y `agendar_cita_dialog_params_<parámetro>`
(qué dato está esperando). Para rechazar un dato, la respuesta devuelve esos contextos con el parámetro vaciado,
apaga el `…_dialog_params_*` actual y activa `agendar_cita_dialog_params_<dato>` (lifespan 1), junto con el texto que explica
el motivo y vuelve a preguntar. Si el rechazo ocurre en el turno final (con los 7 datos), además apaga `ctx_cita_en_curso`
y `agendar_cita-followup` y recrea los contextos de recogida, para que no se pueda confirmar una cita inválida.
El mismo mecanismo sirve para **fijar** un valor (nacionalidad `E` cuando Dialogflow no reconoce el gentilicio).

> **Riesgo principal:** este mecanismo no está documentado oficialmente. Se verifica primero con Dialogflow real (tarea T6).
> Plan B si no funciona: rechazar solo en el turno final y relanzar `agendar_cita` con el evento `INICIAR_CITA`, explicando el motivo.

### Orden de validación en cada turno de `agendar_cita`
1. Nacionalidad vacía y Dialogflow esperando la nacionalidad → inferir desde el texto (V / E / volver a preguntar).
2. Cédula presente → normalizar y validar con regex (según V/E si ya se sabe) → si no vale, repreguntar la cédula.
3. Fecha y especialidad presentes → pasada, domingo o día sin médicos de la especialidad → repreguntar la fecha (vaciando también la hora).
4. Hora, fecha y especialidad presentes → buscar médico libre (primero el del historial) → si no hay, repreguntar la hora con el horario o el siguiente bloque libre.
5. Todo válido y faltan datos → `{}`. Todo válido y están los 7 → guardar propuesta de la sesión y responder con el resumen.

### Regex
- Normalización: quitar todo lo que no sea dígito (puntos, comas, espacios, la letra V/E y palabras).
- Validación: `^[1-9]\d{5,7}$` para V y `^[1-9]\d{5,8}$` para E.
- Nacionalidad desde texto: `venezolan[oa]|venezuela` → V; `extranjer[oa]`, `soy de …` o un gentilicio (`\w+(ano|ana|ense|eño|eña|és|esa|ino|ina|ego|ega)`) → E; resto → repreguntar.
- Frases de cierre en el fallback: `^(no|no,? gracias|nada m[aá]s|eso es todo)\.?$`.

### Estado en memoria (`Agenda`)
- `citas`: lista de citas confirmadas (incluida la sembrada de Miguel Torres) con código, cédula, médico, inicio.
- `propuestas`: cita propuesta por id de sesión, pendiente de "sí".
- `pacientes_nuevos`: pacientes registrados al confirmar.
- `reiniciar()` para los tests.

## Guía para ti (consola y VS Code)

### Paso A — Token del webhook
1. Yo añado `WEBHOOK_TOKEN=<valor aleatorio>` a tu `.env` (sin leer el resto del fichero).
2. Abre `.env` y copia ese valor: lo necesitarás en el paso D.

### Paso B — Arrancar el webhook
En la terminal de VS Code, dentro del repo:
```bash
uv run uvicorn webhook.main:app --reload --port 8000
```
Déjala abierta: ahí verás cada petición que llega (intención, parámetros, respuesta y tiempo).

### Paso C — Túnel con ngrok
> Inicialmente se usó el túnel de VS Code (pestaña PORTS, visibilidad Public), pero su latencia provocaba tiempos agotados
> en Dialogflow (ver "Decisiones técnicas" en la spec). Se sustituyó por ngrok.

Una sola vez:
1. `brew install ngrok` y cuenta gratuita en https://dashboard.ngrok.com/signup.
2. `ngrok config add-authtoken <token>` (el token queda en la configuración de ngrok del Mac, fuera del repositorio).

Cada vez que trabajes con el agente, en una segunda terminal:
```bash
ngrok http 8000
```
La cuenta gratuita tiene un **dominio fijo**: `https://reenter-fled-lyricist.ngrok-free.dev`. Comprueba en el navegador
`https://reenter-fled-lyricist.ngrok-free.dev/` → debe mostrar `{"estado": "ok", …}` (ngrok puede mostrar antes una página de aviso: pulsa **Visit Site**).

### Paso D — Fulfillment en Dialogflow
1. **Fulfillment** → **Webhook** (ya está ENABLED).
2. **URL:** borra el contenido del campo y pega `https://reenter-fled-lyricist.ngrok-free.dev/webhook`.
3. **HEADERS** → una fila:
   | Key | Value |
   |---|---|
   | `X-Visoria-Token` | el valor de `WEBHOOK_TOKEN` de tu `.env` |
4. **SAVE**.

> Si cierras la terminal de ngrok o el Mac se duerme, el túnel se corta y Vicky responderá con las respuestas de reserva.
> Como el dominio es fijo, basta con volver a ejecutar `ngrok http 8000`; Fulfillment no hay que tocarlo.

## Riesgos y mitigación

| Riesgo | Mitigación |
|---|---|
| Dialogflow no acepta los contextos modificados para repreguntar | Verificación temprana (T6); plan B descrito arriba |
| La hora llega con la fecha de hoy | Se combina el día de `fecha` con la hora de `hora` |
| "A las 3" se interpreta como 3:00 de la madrugada | Horas 1–7 se pasan a la tarde si encajan en el horario |
| Estado en memoria se pierde al reiniciar | Aceptado (demo); la cita de Miguel Torres se siembra en cada arranque |
| Cuota por minuto de Dialogflow Trial | Pruebas end-to-end espaciadas (~1 consulta/2 s) |
| Latencia del túnel (con VS Code: 30–42 % de turnos > 5 s) | Cambio a ngrok (mediana 0,69 s, máximo 1,19 s en la medición) |

## Verificación

- `uv run pytest`: regex de cédula (CA-2), nacionalidad (CA-3), reglas de fecha/hora y doble reserva (CA-4, CA-6), propuesta del modelo (CA-5), horarios, historial, cancelación, transferencia, despedida (CA-8 a CA-12), token (CA-1), tiempos y trato de usted (CA-13).
- End-to-end con `detect_intent` contra el agente real a través del túnel: conversación modelo, rechazos en mitad del flujo, reinicio tras "no" (CA-7).
