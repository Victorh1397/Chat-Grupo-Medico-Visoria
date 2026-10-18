# Spec 01 — Caso de uso Visoria y mapa de intenciones

- **Estado:** Spec aprobada (spec de definición: sus criterios de aceptación se implementan y verifican en las specs 02–06)
- **Rúbrica:** Agente Dialogflow (4 pts): intenciones, entidad regex, contexto y confirmación. Sienta la base de todas las demás specs.
- **Depende de:** —

## Problema / objetivo

**Grupo Médico Visoria** es una clínica privada con una única sede en **Caracas (Venezuela)** y varias especialidades.
Los pacientes llaman para pedir cita y para hacer preguntas frecuentes (cómo llegar, precios, horarios de los médicos,
seguros, preparación para exámenes). Hoy eso lo atiende recepción por teléfono.

**Vicky** es la asistente virtual por voz de la clínica (voz femenina). Debe:
1. **Agendar una cita médica** en una conversación de varios turnos, recogiendo y validando los datos del paciente y pidiendo confirmación.
2. **Responder preguntas frecuentes** a partir de los documentos de la clínica (procesados con OCR), diciendo claramente cuando algo no está en ellos.
3. Atender peticiones complementarias: horarios, historial, cancelación y paso a una persona de recepción.

Todos los datos (pacientes, médicos, precios, documentos) son **ficticios**.

## Alcance

**Incluye**
- Definición del negocio: especialidades, médicos ficticios, reglas de agenda.
- Mapa de intenciones, entidades y contexto del agente.
- Comportamiento esperado de cada intención (qué pide, qué responde).
- Catálogo de documentos sintéticos para el OCR (contenido general y contenido por especialidad/médico).
- Conversación modelo para el vídeo de demostración.

**Fuera de alcance**
- Configuración concreta en Dialogflow (spec 02), código del webhook (spec 03), generación y OCR de documentos (spec 04), prompt del LLM (spec 05), cliente de voz (spec 06).
- Integración con un sistema real de agenda o historia clínica: todo se simula en el webhook.
- Pagos, recordatorios por SMS/correo y gestión de varias sedes.

## Datos del negocio

| Concepto | Valor |
|---|---|
| Nombre | Grupo Médico Visoria |
| Sede | Una sola, en Caracas (dirección ficticia, se define en los documentos) |
| Zona horaria | `America/Caracas` |
| Asistente | Vicky, voz femenina, trata al paciente de **usted** |
| Especialidades | Dermatología, Endocrinología, Cirugía plástica, Urología, Cardiología y Oftalmología |
| Médicos | 2 médicos ficticios por especialidad (12 en total), cada uno con sus días/horas de consulta y su tarifa |
| Moneda | Dólares estadounidenses (**USD**) |

### Identificación del paciente: nacionalidad + cédula

Se piden por separado, en dos turnos:

1. **Nacionalidad.** Vicky pregunta: *"¿Usted es venezolano o extranjero?"*
   - "venezolano", "venezolana", "de Venezuela" → **V**.
   - "extranjero", "extranjera" → **E**.
   - **Cualquier otra nacionalidad** ("colombiano", "española", "soy de Perú"…) → **E**. La nacionalidad concreta **no se guarda**; solo queda registrado V o E.
   - Respuesta que no permite decidir ("no sé", silencio) → Vicky repite la pregunta.
2. **Número de cédula (entidad regex).** El usuario dice solo el número, sin letra.
   - Se aceptan dígitos con o sin puntos o espacios de miles: `14523987`, `14.523.987`, `14 523 987`.
   - Rango: 6–8 dígitos para V, 6–9 dígitos para E; no empieza por 0.
   - El sistema guarda la forma canónica **letra + guion + número**: `V-14523987`, `E-81234567`.

En `consultar_historial` y `cancelar_cita` solo se pide el número de cédula: en los datos ficticios no hay dos pacientes con el mismo número.

### Pacientes ficticios

Lista de ~8 pacientes con: cédula canónica, nombre, apellido y **historial** (especialidad, médico y fecha de consultas anteriores).
Incluye al menos un paciente extranjero (`E-`) y pacientes con historial en varias especialidades.

### Reglas de agenda (las aplica el webhook)

1. La fecha no puede ser pasada ni domingo.
2. La hora debe estar dentro del horario del médico que atiende esa especialidad ese día.
3. **Paciente existente:** Vicky lo saluda por su nombre registrado y, si ya se atendió en esa especialidad, propone al **mismo médico**.
4. **Paciente nuevo:** se le registra con los datos dados y se asigna un médico disponible de la especialidad.
5. Si no hay disponibilidad, Vicky lo explica y propone el horario más cercano del médico.
6. Al confirmar, se genera un código de cita (p. ej. `CIT-48213`) y se da el precio en USD de la consulta de ese médico.

## Mapa de intenciones

| # | Intención | Propósito | Webhook |
|---|---|---|---|
| — | `Default Welcome Intent` | Saludo de Vicky y qué puede hacer | No |
| 1 | **`agendar_cita`** | Flujo principal multi-turno: recoge nombre, apellido, nacionalidad, cédula, especialidad, fecha y hora | Sí |
| 1a | `agendar_cita - yes` | Confirmación: registra la cita y da código, médico y precio | Sí |
| 1b | `agendar_cita - no` | No confirma: no guarda nada y ofrece empezar de nuevo | No |
| 2 | **`consulta_documental`** | Preguntas frecuentes respondidas con los documentos OCR + Gemini | Sí |
| 3 | **`consultar_horarios`** | Horario de atención de una especialidad o médico | Sí |
| 4 | **`consultar_historial`** | "¿Con qué médico me atendí?": historial del paciente por número de cédula | Sí |
| 5 | **`cancelar_cita`** | Cancela una cita existente a partir del número de cédula | Sí |
| 6 | **`transferir_humano`** | Pasar con recepción (también es mejora opcional) | Sí |
| — | `Default Fallback Intent` | No entendido: intenta responder con los documentos y, si no, reformula u ofrece recepción | Sí |

Total: **6 intenciones significativas** + bienvenida + fallback (el enunciado pide 5–6).

### Contexto: `ctx_cita_en_curso`

```
agendar_cita ──(recoge 7 datos, valida cédula con regex)──► ctx_cita_en_curso
                                                              ├─ "sí" → agendar_cita - yes → cita registrada
                                                              └─ "no" → agendar_cita - no  → "¿Desea empezar de nuevo?"
```
- Es el **único flujo multi-turno con contexto** obligatorio.
- Si tras el "no" el usuario dice "sí", vuelve a empezar `agendar_cita` desde cero; si dice "no", Vicky ofrece otra ayuda.
- El usuario puede dar varios datos en una sola frase ("Soy María González, quiero dermatología el martes"): Vicky solo pide los que falten.

### Entidades

| Entidad | Tipo | Uso |
|---|---|---|
| `@cedula` | **Regex** (personalizada): número de 6–9 dígitos con o sin separadores | `agendar_cita`, `consultar_historial`, `cancelar_cita` |
| `@nacionalidad` | Personalizada: valores `V` (venezolano/a…) y `E` (extranjero/a y otras nacionalidades) | `agendar_cita` |
| `@especialidad` | Personalizada con sinónimos (p. ej. "dermatólogo", "piel" → Dermatología; "ojos" → Oftalmología; "corazón" → Cardiología) | `agendar_cita`, `consultar_horarios` |
| `@sys.given-name`, `@sys.last-name` | Sistema | Nombre y apellido |
| `@sys.date`, `@sys.time` | Sistema | Fecha y hora de la cita |

## Documentos para el OCR (sintéticos)

Se crean como **imágenes** (simulando documentos escaneados) a partir de los datos ficticios, con una parte general y otra que
varía por especialidad y médico:

| # | Documento | Contenido | Parte |
|---|---|---|---|
| D1 | Preguntas frecuentes | Dirección, cómo llegar (metro/autobús), estacionamiento, horario general, formas de pago, qué traer a la consulta | General |
| D2 | Tarifario de consultas | Tabla: especialidad → médico → precio de consulta y de control (USD) | Por médico |
| D3 | Horarios de los médicos | Tabla: especialidad → médico → días y horas de consulta | Por médico |
| D4 | Preparación para exámenes | Indicaciones por especialidad (p. ej. curva de glucosa en endocrinología, PSA en urología, biopsia en dermatología, valoración preoperatoria en cirugía plástica, prueba de esfuerzo en cardiología, fondo de ojo con dilatación en oftalmología) | Por especialidad |
| D5 | Seguros y reglamento | Aseguradoras aceptadas (ficticias), política de cancelación (24 h), llegar 15 min antes, acompañantes | General |

Las tablas (D2, D3) cuentan como "documentos complejos" para la mejora opcional. Los datos de D2 y D3 deben coincidir con los
que usa el webhook para agendar (una única fuente de datos ficticios).

## Conversación modelo (base del vídeo)

> **Vicky:** Bienvenido a Grupo Médico Visoria, soy Vicky. Puedo agendarle una cita o responder sus dudas sobre la clínica. ¿En qué le puedo ayudar?
> **Usuario:** Quiero una cita con el dermatólogo.
> **Vicky:** Con gusto. ¿Cuál es su nombre? → **Usuario:** María. → **Vicky:** ¿Y su apellido? → **Usuario:** González.
> **Vicky:** ¿Usted es venezolana o extranjera? → **Usuario:** Venezolana.
> **Vicky:** ¿Me indica su número de cédula? → **Usuario:** 14 523 987.
> **Vicky:** ¿Para qué fecha desea la cita? → **Usuario:** El próximo martes. → **Vicky:** ¿A qué hora? → **Usuario:** A las 10 de la mañana.
> **Vicky:** Señora González, veo que ya se atendió en dermatología con la doctora Rojas. Le propongo cita con ella el martes 21 a las 10:00. La consulta cuesta 40 dólares. ¿Confirmo la cita?
> **Usuario:** Sí.
> **Vicky:** Listo, su cita CIT-48213 está confirmada. Le recomendamos llegar 15 minutos antes. ¿Le puedo ayudar en algo más?
> **Usuario:** ¿Tienen estacionamiento?
> **Vicky:** Sí, la clínica cuenta con estacionamiento propio… *(respuesta a partir de D1)*
> **Usuario:** ¿Hacen resonancias magnéticas?
> **Vicky:** No tengo esa información en los documentos de la clínica. ¿Desea que le comunique con recepción?

## Criterios de aceptación

- **CA-1.** El agente tiene 6 intenciones significativas además de bienvenida y fallback, con el propósito descrito en el mapa.
- **CA-2.** Dado un usuario que dice "quiero una cita con urología", cuando faltan datos, entonces Vicky los pide uno a uno hasta tener nombre, apellido, nacionalidad, cédula, especialidad, fecha y hora.
- **CA-3.** Dada la respuesta "venezolano" o "venezolana", entonces se registra V; dada "extranjero", "extranjera" o cualquier otra nacionalidad (p. ej. "colombiano"), entonces se registra E y la nacionalidad concreta no se guarda.
- **CA-4.** Dado el número `14523987`, `14.523.987` o `14 523 987`, entonces se reconoce y se guarda como `V-14523987` o `E-14523987` según la nacionalidad; dado `123`, `0123456` o un número de más de 9 dígitos, entonces se rechaza y Vicky lo vuelve a pedir.
- **CA-5.** Dado un paciente registrado con historial en la especialidad pedida, entonces Vicky lo trata de usted por su apellido y propone al mismo médico.
- **CA-6.** Dada una fecha pasada, un domingo o una hora fuera del horario del médico, entonces Vicky lo explica y propone una alternativa.
- **CA-7.** Al final del flujo Vicky resume los datos y pregunta si confirma; con "sí" da código de cita, médico y precio en USD; con "no" no registra nada y ofrece empezar de nuevo.
- **CA-8.** Dado un número de cédula registrado, `consultar_historial` responde con las especialidades, médicos y fechas de sus consultas anteriores; dado uno no registrado, lo indica.
- **CA-9.** Dada una pregunta frecuente cuya respuesta está en D1–D5, entonces Vicky responde con esa información; si no está, lo dice explícitamente y ofrece comunicar con recepción.
- **CA-10.** Los precios y horarios que da Vicky al agendar coinciden con los de los documentos D2 y D3.
- **CA-11.** Todas las respuestas de Vicky tratan al paciente de usted.
- **CA-12.** Todos los nombres, cédulas, médicos y aseguradoras son ficticios.

## Decisiones

| Tema | Decisión |
|---|---|
| Trato | Usted |
| Especialidades | 6: Dermatología, Endocrinología, Cirugía plástica, Urología, Cardiología, Oftalmología |
| 6.ª intención | Se incluye `consultar_historial` |
| Cédula | Nacionalidad preguntada por separado (V/E); la regex valida solo el número; otras nacionalidades cuentan como E y no se guardan |
| Moneda | USD |

## Riesgos (se abordan en specs posteriores)

- **Reconocimiento de voz de la cédula:** el reconocimiento de voz podría escribir el número como "14 millones 523 mil 987" o con comas. El webhook debe normalizarlo antes de aplicar la regex (spec 03) y se probará por voz (spec 06).
- **Otras nacionalidades:** la entidad `@nacionalidad` debe reconocer gentilicios no listados; si no los reconoce, el webhook aplica la regla "no venezolano → E" sobre el texto de la respuesta (spec 02/03).
