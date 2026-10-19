# Spec 03 — Webhook FastAPI con la lógica de negocio

- **Estado:** Spec aprobada
- **Rúbrica:** Webhook con lógica de negocio (requisito 3 del enunciado) y parte del bloque Agente (4 pts): el flujo con contexto y la confirmación se completan con respuestas dinámicas.
- **Depende de:** [Spec 01](../01-caso-de-uso/spec.md), [Spec 02](../02-agente-dialogflow/spec.md)

## Problema / objetivo

El agente ya reconoce las intenciones y recoge los datos (spec 02), pero todas las intenciones con webhook responden con su
respuesta de reserva. Esta spec construye el **webhook en FastAPI**, expuesto a internet, que:

1. **Valida con expresiones regulares** la cédula en el mismo turno en que se dice.
2. Aplica las **reglas de agenda** de la clínica con datos ficticios (pacientes, médicos, horarios, precios).
3. Genera **respuestas dinámicas** que dependen de los datos recogidos.
4. Atiende el resto de intenciones: horarios, historial, cancelación, transferencia, reinicio del flujo y despedida.

## Alcance

**Incluye**
- Servidor FastAPI con `POST /webhook` y `GET /` (comprobación de estado).
- Datos ficticios de la clínica en un **único módulo** (fuente de verdad que también usará la spec 04 para generar los documentos D2 y D3).
- Lógica de las intenciones `agendar_cita` (durante la recogida y al final), `agendar_cita - yes`, `agendar_cita - no - yes`, `consultar_horarios`, `consultar_historial`, `cancelar_cita`, `transferir_humano` y `Default Fallback Intent` (solo despedida).
- Exposición con ngrok y conexión en Fulfillment.
- Tests automáticos de la lógica y del endpoint.

**Fuera de alcance**
- Respuestas con documentos y Gemini (`consulta_documental` y el resto del fallback): spec 05. En esta spec responden con un mensaje provisional.
- SSML y voz: spec 06. Aquí las respuestas son texto breve, pensado para ser leído en voz alta.
- Transferencia real y "sí" a "¿Desea que le comunique con recepción?": spec 07.
- Persistencia en base de datos: las citas nuevas viven en memoria y se pierden al reiniciar (suficiente para la demo).

## Datos ficticios

### Clínica
- Horario general: lunes a viernes de 7:00 a 19:00; sábados de 7:00 a 13:00; domingos cerrado.
- Citas en **bloques de 30 minutos** (hh:00 o hh:30). Un médico atiende una cita por bloque.

### Médicos (12)

| Especialidad | Médico | Días y horas | Precio consulta (USD) |
|---|---|---|---|
| Dermatología | Dra. Laura Rojas | Martes y jueves, 8:00–12:00 | 40 |
| Dermatología | Dr. Andrés Salazar | Lunes y miércoles, 14:00–18:00 | 35 |
| Endocrinología | Dra. Carmen Villalobos | Lunes, miércoles y viernes, 8:00–12:00 | 50 |
| Endocrinología | Dr. Rafael Ortega | Martes y jueves, 14:00–18:00 | 45 |
| Cirugía plástica | Dr. Alejandro Briceño | Lunes y jueves, 9:00–13:00 | 80 |
| Cirugía plástica | Dra. Valentina Pacheco | Miércoles y viernes, 14:00–18:00 | 90 |
| Urología | Dr. Gustavo Hernández | Martes y viernes, 8:00–12:00 | 45 |
| Urología | Dr. Luis Carrillo | Sábados, 8:00–12:00 | 50 |
| Cardiología | Dra. Patricia Medina | Lunes a miércoles, 8:00–12:00 | 55 |
| Cardiología | Dr. Eduardo Rangel | Jueves y viernes, 14:00–18:00 | 50 |
| Oftalmología | Dra. Gabriela Quintero | Lunes y miércoles, 8:00–12:00 | 40 |
| Oftalmología | Dr. José Luis Arismendi | Martes y jueves 14:00–18:00; sábados 8:00–12:00 | 45 |

La hora final es la de cierre: el último bloque que se puede reservar empieza 30 minutos antes.
Cada médico tiene un **precio único** por consulta, igual para la primera vez y para los controles.

### Pacientes (8)

| Cédula | Nombre | Historial |
|---|---|---|
| V-14523987 | María González | Dermatología con Dra. Laura Rojas (12/03/2026); Cardiología con Dra. Patricia Medina (04/11/2025) |
| V-9452312 | José Rodríguez | Urología con Dr. Gustavo Hernández (20/05/2026) |
| E-81234567 | Carlos Pérez | Cardiología con Dr. Eduardo Rangel (15/01/2026) |
| V-20345678 | Ana Rodríguez | Endocrinología con Dra. Carmen Villalobos (02/07/2026); Oftalmología con Dra. Gabriela Quintero (10/02/2026) |
| V-17890123 | Luisa Fernández | Cirugía plástica con Dra. Valentina Pacheco (21/08/2026) |
| V-6123456 | Pedro Martínez | Oftalmología con Dr. José Luis Arismendi (30/09/2025) |
| E-84567890 | Sofía Ramírez | Dermatología con Dr. Andrés Salazar (09/04/2026) |
| V-25678901 | Miguel Torres | Endocrinología con Dr. Rafael Ortega (18/06/2026). **Cita pendiente** `CIT-10234`: Endocrinología con Dr. Rafael Ortega, el próximo martes a las 15:00 (fecha calculada al arrancar el webhook, para que nunca quede en el pasado) |

Las citas pendientes (la de Miguel Torres y las que se agenden) sirven para `cancelar_cita` y `consultar_historial`.

## Requisitos

### R1. Servidor y conexión
1. `POST /webhook` recibe la petición de Dialogflow ES y devuelve siempre una respuesta válida; ante cualquier error interno responde con un mensaje de disculpa (nunca un error HTTP ni silencio).
2. `GET /` devuelve el estado del servicio.
3. El webhook exige una cabecera secreta (`X-Visoria-Token`) cuyo valor está en `.env` y se configura en Fulfillment; sin ella responde 401. Evita que cualquiera con la URL del túnel use el webhook.
4. Cada turno responde en **menos de 1 segundo** (sin llamadas externas en esta spec), muy por debajo del límite de 5 s.
5. Se expone con ngrok (`ngrok http 8000`, dominio fijo gratuito de la cuenta) y la URL `…/webhook` se configura en Fulfillment.

### R2. Validación durante la recogida de datos de `agendar_cita`
Con el webhook de slot filling, en cada turno el webhook revisa los datos recibidos. Si alguno no es válido, **lo borra y lo vuelve a pedir explicando el motivo**; si todo es válido, deja que Dialogflow siga con su siguiente pregunta.

1. **Cédula (regex en el webhook):** se normaliza (quitar puntos, comas, espacios, letra V/E inicial y palabras) y se valida con regex: sin 0 inicial, 6–8 dígitos para V y 6–9 para E. Se guarda en forma canónica `V-14523987`.
2. **Nacionalidad no reconocida:** si Dialogflow no reconoce la respuesta a "¿Usted es venezolano o extranjero?" (p. ej. "soy de Noruega"), el webhook aplica la regla de la spec 01: si el texto menciona "venezolan…" o "Venezuela" → V; si menciona otra nacionalidad o país → E; si no permite decidir ("no sé") → se repite la pregunta.
3. **Paciente registrado:** en cuanto hay cédula válida, si el paciente existe se usa su nombre registrado y su historial para la propuesta final.
4. **Fecha:** se rechaza si es pasada, si es domingo o si ningún médico de la especialidad atiende ese día; Vicky indica qué días atiende la especialidad (o el médico propuesto).
5. **Hora:** se rechaza si no cae dentro del horario del médico ese día o si el bloque ya está ocupado; Vicky propone el horario del médico o el siguiente bloque libre. Las horas ambiguas (1–7) se interpretan de la tarde si así encajan en el horario. Las horas se redondean al bloque de 30 minutos anterior.

### R3. Propuesta al completar `agendar_cita`
Con los 7 datos válidos, el webhook:
1. Combina el **día** de `fecha` con la **hora** de `hora` (Dialogflow devuelve la hora pegada a la fecha de hoy), en hora de Caracas.
2. Elige médico: si el paciente ya se atendió en esa especialidad y ese médico atiende ese día y hora, el mismo médico; si no, uno disponible de la especialidad.
3. Guarda la propuesta como **cita pendiente de confirmar** para esa sesión.
4. Responde con un resumen y la pregunta de confirmación, de usted y dirigiéndose al paciente por su nombre. Ejemplo:
   > María, veo que ya se atendió en dermatología con la doctora Laura Rojas. Le propongo cita con ella el martes 20 de octubre a las 10:00. La consulta cuesta 40 dólares. ¿Confirmo la cita?

### R4. Confirmación y reinicio
1. **`agendar_cita - yes`:** registra la cita pendiente de la sesión (y al paciente, si es nuevo), genera un código `CIT-#####` y responde con código, médico, fecha, hora, precio y el recordatorio de llegar 15 minutos antes. Si no hay cita pendiente para la sesión, lo dice y ofrece empezar de nuevo.
2. **`agendar_cita - no - yes`:** descarta la cita pendiente y lanza el evento `INICIAR_CITA` para que `agendar_cita` empiece de nuevo y pregunte el nombre.
3. **`agendar_cita - no` y `agendar_cita - no - no`:** **no usan el webhook** (spec 02); responden con su texto fijo. La cita pendiente de la sesión no se registra: no puede confirmarse porque esos follow-ups cierran `ctx_cita_en_curso`, y se sustituye si se propone otra.

### R5. Otras intenciones
1. **`consultar_horarios`:** médicos de la especialidad con sus días y horas.
2. **`consultar_historial`:** con el número de cédula (se acepta V o E), lista las consultas anteriores (especialidad, médico, fecha) y las citas pendientes. Si la cédula no está registrada, lo dice.
3. **`cancelar_cita`:** con el número de cédula, cancela la próxima cita pendiente y lo confirma con su código, fecha y médico. Si no tiene citas pendientes o no está registrada, lo dice.
4. **`transferir_humano`:** genera un número de caso `VIS-#####` y responde que le comunica con recepción, dándole el número de caso.
5. **`Default Fallback Intent`:** si el texto es una frase de cierre ("no", "no gracias", "nada más", "eso es todo"), responde con una despedida; si no, con la respuesta genérica de no entendido (la consulta a documentos se añade en la spec 05).
6. **`consulta_documental`:** respuesta provisional hasta la spec 05.
7. Cualquier intención no prevista: respuesta genérica, nunca silencio.

### R6. Formato de las respuestas
- De usted, en español, 1–3 frases, sin datos técnicos (nada de fechas ISO ni códigos internos salvo `CIT-…` y `VIS-…`).
- Fechas habladas: "el martes 20 de octubre a las 10:00".
- Precios: "40 dólares".

## Criterios de aceptación

- **CA-1.** `POST /webhook` sin la cabecera `X-Visoria-Token` correcta devuelve 401; con ella, responde a todas las intenciones de la spec 02 sin errores.
- **CA-2.** Durante `agendar_cita`, una cédula de menos de 6 dígitos, que empiece por 0, o de 9 dígitos para un venezolano, se rechaza en ese turno y Vicky la vuelve a pedir explicando el formato; `14.523.987`, `14 523 987` y `14523987` se guardan como `V-14523987`.
- **CA-3.** "Soy de Noruega" como nacionalidad se registra como E y Vicky pasa a pedir la cédula; "no sé" repite la pregunta.
- **CA-4.** Una fecha pasada, un domingo o un día en que no atiende la especialidad se rechazan en ese turno con los días disponibles; una hora fuera del horario o ya ocupada se rechaza con una alternativa.
- **CA-5.** Con la conversación modelo de la spec 01 (María González, V-14523987, dermatología, próximo martes a las 10:00), Vicky propone a la Dra. Laura Rojas, da el precio de 40 dólares y pregunta si confirma.
- **CA-6.** Al confirmar, Vicky da un código `CIT-#####`; un segundo paciente que pida el mismo médico, día y hora recibe otra hora.
- **CA-7.** Tras "no" y "sí" ("¿Desea empezar de nuevo?"), Vicky vuelve a preguntar el nombre sin que el usuario repita "quiero una cita".
- **CA-8.** `consultar_horarios` con "cardiología" responde con la Dra. Patricia Medina y el Dr. Eduardo Rangel y sus horarios.
- **CA-9.** `consultar_historial` con `14523987` lista las dos consultas de María González; con un número no registrado lo dice.
- **CA-10.** `cancelar_cita` con `25678901` cancela `CIT-10234`; una segunda cancelación indica que no hay citas pendientes.
- **CA-11.** `transferir_humano` responde con un número de caso `VIS-#####`.
- **CA-12.** "No gracias" (fallback) responde con una despedida.
- **CA-13.** Cada respuesta se genera en menos de 1 segundo y ninguna tutea al paciente.
- **CA-14.** Los tests automáticos (`uv run pytest`) cubren la regex de la cédula, las reglas de agenda y el endpoint con peticiones de ejemplo de Dialogflow.

## Decisiones técnicas

| Tema | Decisión | Motivo |
|---|---|---|
| Validación de la cédula | Dos niveles: la entidad regex `@cedula` de Dialogflow **extrae** el número (formato); el webhook lo **valida** con su propia regex según V/E y lo normaliza | Dialogflow no conoce la nacionalidad ni puede explicar el error; el enunciado pide una entidad regex en el agente y una validación con regex en el webhook |
| Datos | Módulo Python con médicos y pacientes ficticios; citas nuevas en memoria | El enunciado pide lógica de negocio, no persistencia; un único origen evita contradicciones con los documentos (spec 04) |
| Cita pendiente | Se guarda por sesión al proponerla y se confirma en `- yes` | Al confirmar, los contextos ya se han cerrado; guardar la propuesta evita depender de ellos |
| Rechazo de un dato | Borrar el parámetro en el contexto de recogida de Dialogflow y responder con la nueva pregunta | Permite volver a pedir solo ese dato sin reiniciar el flujo |
| Seguridad | Cabecera secreta `X-Visoria-Token` | La URL del túnel es pública |
| Túnel | **ngrok** con dominio fijo gratuito, en lugar del túnel de VS Code previsto inicialmente | Medido con 10 peticiones intercaladas: VS Code mediana 2,57 s, 4/10 por encima de 3 s y 2 bloqueos de 30 s (en Dialogflow, 30–42 % de turnos con tiempo agotado); ngrok mediana 0,69 s y máximo 1,19 s. Cloud Run se descartó porque exige facturación, incompatible con el plan gratuito de Gemini |
| Zona horaria | `America/Caracas` en el webhook | El agente usa `America/Barbados` (equivalente) solo para resolver fechas relativas |

## Preguntas abiertas

1. ¿Te sirven los **médicos, horarios y precios** propuestos, o quieres cambiar alguno?
2. ¿Te sirve la **lista de pacientes**? (Incluye a María González y Carlos Pérez, que ya usamos en las pruebas.)
3. ¿Bloques de **30 minutos** te parecen bien?
