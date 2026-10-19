# Plan 02 — Guía paso a paso para configurar el agente en Dialogflow ES

Implementa: [spec.md](spec.md)

## Cómo usar esta guía

- Consola: **https://dialogflow.cloud.google.com** → agente **Grupo-Medico-Visoria** (arriba a la izquierda). La interfaz está en inglés; los nombres de botones se citan tal cual.
- Ve **bloque a bloque**. Al terminar cada bloque, pulsa **SAVE** y, si quieres, avísame antes de seguir.
- Los nombres de intenciones, parámetros, contextos y eventos deben escribirse **exactamente** como aquí (el webhook los usa). Están en `código`.
- Tras guardar una intención, Dialogflow la entrena solo (aparece "Agent training started/completed" abajo a la derecha). Si una intención no se dispara, espera a que termine el entrenamiento.

---

## Bloque 0 — Ajustes del agente y Fulfillment

### 0.1 Zona horaria
1. Clic en el ⚙️ junto al nombre del agente → pestaña **General**.
2. **Default time zone:** `(GMT-4:00) America/Caracas`. Si no aparece en la lista, elige `(GMT-4:00) America/Barbados` (misma hora todo el año, sin horario de verano).
3. **SAVE**.

### 0.2 Activar el webhook (URL provisional)
Así el interruptor de webhook de cada intención funciona desde ya. La URL real (túnel) se pone en la spec 03.
1. Menú izquierdo → **Fulfillment**.
2. **Webhook** → **ENABLED**.
3. **URL:** `https://example.com/webhook` (provisional; fallará y Vicky usará las respuestas de reserva, que es justo lo que queremos probar).
4. **SAVE** (abajo).

---

## Bloque 1 — Entidades

Menú izquierdo → **Entities** → **CREATE ENTITY** para cada una.

> **Importante — sinónimos uno a uno:** la consola **no separa por comas**. Si escribes "venezolano, venezolana" en una celda, se guarda como **un único sinónimo**
> y "venezolano" a secas no se reconocerá. Pulsa **Enter** tras cada sinónimo, o mejor usa el modo texto: **⋮ → Switch to raw mode**, pega las líneas CSV
> de abajo (formato `"valor","sinónimo1","sinónimo2",…`) y **SAVE**.

### 1.1 `especialidad`
1. **Entity name:** `especialidad`.
2. Deja marcado **Define synonyms**. Marca **Fuzzy matching** (tolera pequeños errores del reconocimiento de voz).
3. Una fila por especialidad. En la primera columna el valor de referencia; en la segunda, los sinónimos (Enter tras cada uno):

| Valor de referencia | Sinónimos |
|---|---|
| `Dermatología` | dermatología, dermatologia, dermatólogo, dermatóloga, piel, manchas en la piel, acné |
| `Endocrinología` | endocrinología, endocrinologia, endocrino, endocrinólogo, endocrinóloga, tiroides, diabetes, hormonas |
| `Cirugía plástica` | cirugía plástica, cirugia plastica, cirujano plástico, cirujana plástica, cirugía estética, plástica |
| `Urología` | urología, urologia, urólogo, uróloga, próstata, vías urinarias |
| `Cardiología` | cardiología, cardiologia, cardiólogo, cardióloga, corazón, presión arterial |
| `Oftalmología` | oftalmología, oftalmologia, oftalmólogo, oftalmóloga, oculista, ojos, vista |

CSV para raw mode:
```
"Dermatología","Dermatología","dermatología","dermatologia","dermatólogo","dermatóloga","piel","manchas en la piel","acné"
"Endocrinología","Endocrinología","endocrinología","endocrinologia","endocrino","endocrinólogo","endocrinóloga","tiroides","diabetes","hormonas"
"Cirugía plástica","Cirugía plástica","cirugía plástica","cirugia plastica","cirujano plástico","cirujana plástica","cirugía estética","plástica"
"Urología","Urología","urología","urologia","urólogo","uróloga","próstata","vías urinarias"
"Cardiología","Cardiología","cardiología","cardiologia","cardiólogo","cardióloga","corazón","presión arterial"
"Oftalmología","Oftalmología","oftalmología","oftalmologia","oftalmólogo","oftalmóloga","oculista","ojos","vista"
```

4. **SAVE**.

### 1.2 `nacionalidad`
1. **Entity name:** `nacionalidad`.
2. Deja marcado **Define synonyms**. **No** marques **Allow automated expansion**: con ella Dialogflow aceptaba cualquier
   respuesta como nacionalidad (devolvió `Noruega` e incluso el número `81234567`). Los gentilicios no listados los resuelve el
   webhook a partir del texto (spec 03).
3. Dos filas:

| Valor de referencia | Sinónimos |
|---|---|
| `V` | venezolano, venezolana, venezuela, de venezuela, soy de aquí, nacional |
| `E` | extranjero, extranjera, de otro país, colombiano, colombiana, colombia, peruano, peruana, perú, ecuatoriano, ecuatoriana, ecuador, chileno, chilena, argentino, argentina, español, española, españa, portugués, portuguesa, portugal, italiano, italiana, italia, cubano, cubana, dominicano, dominicana, mexicano, mexicana, estadounidense, americano, americana, brasileño, brasileña, panameño, panameña, boliviano, boliviana, uruguayo, uruguaya, paraguayo, paraguaya, haitiano, haitiana, libanés, libanesa, sirio, siria, chino, china, alemán, alemana, francés, francesa, canadiense |

CSV para raw mode:
```
"V","V","venezolano","venezolana","venezuela","de venezuela","soy de aquí","nacional"
"E","E","extranjero","extranjera","de otro país","colombiano","colombiana","colombia","peruano","peruana","perú","ecuatoriano","ecuatoriana","ecuador","chileno","chilena","argentino","argentina","español","española","españa","portugués","portuguesa","portugal","italiano","italiana","italia","cubano","cubana","dominicano","dominicana","mexicano","mexicana","estadounidense","americano","americana","brasileño","brasileña","panameño","panameña","boliviano","boliviana","uruguayo","uruguaya","paraguayo","paraguaya","haitiano","haitiana","libanés","libanesa","sirio","siria","chino","china","alemán","alemana","francés","francesa","canadiense"
```

4. **SAVE**.

> Si alguien dice una nacionalidad que no está en la lista, Dialogflow no la reconoce y el webhook aplica la regla "no es venezolano → E" (spec 03).

### 1.3 `cedula` (entidad regex)
1. **Entity name:** `cedula`.
2. **Deja marcada** Define synonyms (si se desmarca, la casilla Regexp entity desaparece) y **marca Regexp entity** en la fila de casillas.
   Hazlo **al crear** la entidad: una entidad ya guardada no se puede convertir en regex (la consola desmarca la casilla al guardar sin avisar).
   Si te equivocas, borra la entidad (primero quítala de las intenciones que la usen) y créala de nuevo.
3. Dos filas, **en este orden**:

   | Fila | Expresión | Reconoce |
   |---|---|---|
   | 1 | `[1-9][0-9]{5,8}` | Dígitos seguidos: `14523987`, `945123` |
   | 2 | `[1-9][0-9]{0,2}([.,\s][0-9]{3}){1,2}` | Con separadores de miles: `14.523.987`, `14 523 987`, `14,523,987` |

   **Por qué dos filas y en ese orden:** Dialogflow une las filas en una sola expresión y se queda con la **primera coincidencia,
   aunque sea parcial**. Con una única fila de separador opcional (`[.,\s]?`), `14523987` coincidía solo como `145239` y la cédula
   no se reconocía (fallaban justo las de 7 y 8 dígitos). Por eso el patrón de dígitos seguidos va primero y el segundo exige separador.
   La regex de la entidad no comprueba V/E: el webhook valida el rango exacto (6–8 dígitos para V, 6–9 para E).
4. **SAVE**.

---

## Bloque 2 — Bienvenida y fallback

### 2.1 `Default Welcome Intent`
1. **Intents** → `Default Welcome Intent`.
2. **Responses:** borra las respuestas que trae y escribe:
   > Bienvenido a Grupo Médico Visoria, soy Vicky. Puedo agendarle una cita médica o responder sus dudas sobre la clínica. ¿En qué le puedo ayudar?
3. **Fulfillment:** webhook **desactivado**.
4. **SAVE**.

### 2.2 `Default Fallback Intent`
1. **Intents** → `Default Fallback Intent`.
2. **Responses:** borra las que trae y añade dos variantes (Dialogflow elige una al azar):
   > Disculpe, no le entendí. ¿Me lo puede decir de otra forma?

   > Perdone, no he comprendido. Puedo agendarle una cita o responder sus dudas sobre la clínica.
3. **Training phrases (ejemplos negativos):** añade `no`, `no gracias`, `nada más`, `eso es todo`.
   En el fallback, las frases de entrenamiento indican lo que **no** debe asignarse a ninguna otra intención. Sin ellas, un "no" suelto
   (p. ej. tras "¿Le puedo ayudar en algo más?") activaba `cancelar_cita` por parecerse a "No puedo asistir…". Dentro del flujo de cita
   el "no" sigue llegando a `agendar_cita - no`, porque los contextos tienen prioridad. La despedida ante estas frases la dará el webhook (spec 03).
4. **Fulfillment:** activa **Enable webhook call for this intent**.
5. **SAVE**.

---

## Bloque 3 — `agendar_cita` (el flujo principal)

**Intents** → **CREATE INTENT** → nombre: `agendar_cita`.

### 3.1 Frases de entrenamiento
En **Training phrases → ADD TRAINING PHRASES**, añade (Enter tras cada una):

```
Quiero agendar una cita
Necesito una cita médica
Quisiera pedir una cita
Quiero una cita con el dermatólogo
Necesito una consulta de cardiología
Me gustaría ver a un urólogo
Quiero agendar una cita de oftalmología para el martes
Necesito cita con endocrinología mañana a las 9 de la mañana
¿Me puede dar una cita con cirugía plástica?
Quiero reservar una consulta para el próximo lunes
Quisiera una cita para el viernes a las 10
Agéndeme una cita con el cardiólogo
Soy María González y quiero una cita con dermatología
Me llamo Carlos Pérez, necesito una cita
Quiero sacar una cita para los ojos
Necesito ir al médico
Quiero programar una consulta
Pedir cita
```

Dialogflow resaltará en colores las palabras que reconoce como entidades (especialidad, fechas, horas, nombres). Revisa:
- "dermatólogo", "cardiología", "ojos"… → `@especialidad`.
- "martes", "mañana", "el próximo lunes" → `@sys.date`; "a las 9 de la mañana", "a las 10" → `@sys.time`.
- "María", "Carlos" → `@sys.given-name`; "González", "Pérez" → `@sys.last-name`.

Si alguna no está resaltada, **selecciónala con el ratón** y elige la entidad en el menú que aparece. Si una palabra está mal resaltada, haz clic sobre ella y elige **Delete**.

### 3.2 Parámetros (Action and parameters)
Al anotar las frases, Dialogflow crea parámetros con nombres en inglés (`date`, `time`, `given-name`…). La tabla debe quedar así:

| Orden | REQUIRED | PARAMETER NAME | ENTITY | VALUE | Pregunta (PROMPTS) |
|---|---|---|---|---|---|
| 1 | ✅ | `nombre` | `@sys.given-name` | `$nombre` | ¿Me indica su nombre y apellido, por favor? |
| 2 | ✅ | `apellido` | `@sys.last-name` | `$apellido` | Gracias. ¿Me indica también su apellido? |
| 3 | ✅ | `nacionalidad` | `@nacionalidad` | `$nacionalidad` | ¿Usted es venezolano o extranjero? |
| 4 | ✅ | `cedula` | `@cedula` | `$cedula` | ¿Me indica su número de cédula? Por ejemplo: 14523987. |
| 5 | ✅ | `especialidad` | `@especialidad` | `$especialidad` | ¿Con qué especialidad desea la cita? Tenemos dermatología, endocrinología, cirugía plástica, urología, cardiología y oftalmología. |
| 6 | ✅ | `fecha` | `@sys.date` | `$fecha` | ¿Para qué fecha desea la cita? |
| 7 | ✅ | `hora` | `@sys.time` | `$hora` | ¿A qué hora le conviene? |

> **Una sola pregunta para nombre y apellido:** cuando Vicky pregunta "¿Me indica su nombre y apellido?" y el usuario responde "María González", Dialogflow rellena **todos los parámetros que encuentra en esa frase**: `nombre` y `apellido` a la vez. La pregunta de la fila 2 solo se usa si el usuario dijo únicamente el nombre.

Pasos:
1. **Renombra** los parámetros creados automáticamente: haz clic en el nombre (`given-name`, `last-name`, `date`, `time`) y cámbialo por `nombre`, `apellido`, `fecha`, `hora`. El **VALUE** debe quedar igual al nombre con `$` delante.
2. Añade en filas nuevas los que falten (`nacionalidad`, `cedula` y `especialidad` si no apareció): escribe el nombre, elige la entidad y el valor se rellena solo.
3. Marca **REQUIRED** en las 7 filas.
4. En cada fila, clic en **Define prompts** → escribe la pregunta de la tabla → cierra la ventana.
5. **Orden:** Dialogflow pregunta en el orden de la tabla. Arrastra las filas por el borde izquierdo hasta que queden como arriba.
6. Comprueba que **IS LIST** está desmarcado en todas.

> Tras renombrar, haz clic en una frase anotada (p. ej. "martes") y comprueba que el parámetro que muestra es `fecha`. Si sigue diciendo `date`, avísame.

### 3.3 Contextos
1. Sección **Contexts** → **Add output context:** escribe `ctx_cita_en_curso` y Enter. Deja el lifespan en **5**.
2. No pongas contextos de entrada.

### 3.4 Evento
Sección **Events** → **Add event:** `INICIAR_CITA`.

### 3.5 Respuesta de reserva
**Responses → Text Response:**
> Gracias, $nombre. ¿Confirma que desea agendar la cita de $especialidad en la fecha y hora indicadas?

### 3.6 Fulfillment
Activa **Enable webhook call for this intent** y **Enable webhook call for slot filling**.

### 3.7 **SAVE**

---

## Bloque 4 — Follow-ups de confirmación

### 4.1 `agendar_cita - yes`
1. En la lista de **Intents**, pasa el ratón sobre `agendar_cita` → **Add follow-up intent** → **yes**. Se crea `agendar_cita - yes` debajo, con frases ("sí", "claro", "ok"…) ya puestas.
2. Ábrela. En **Contexts**:
   - Entrada: ya tiene `agendar_cita-followup`. **Añade** también `ctx_cita_en_curso`.
   - Salida: añade `ctx_cita_en_curso` y cambia su lifespan a **0**. Si aparece `agendar_cita-followup` en salida, ponlo también a **0**.
3. Añade a las frases de entrenamiento: `Sí, confírmela`, `Confirmo`, `Sí, por favor`, `Correcto`.
4. **Responses:**
   > Disculpe, tuve un problema al registrar su cita. ¿Desea que le comunique con recepción?
5. **Fulfillment:** activa **Enable webhook call for this intent**.
6. **SAVE**.

### 4.2 `agendar_cita - no`
1. Sobre `agendar_cita` → **Add follow-up intent** → **no**.
2. **Contexts:**
   - Entrada: ya tiene `agendar_cita-followup`. **Añade** `ctx_cita_en_curso`.
   - Salida: `ctx_cita_en_curso` con lifespan **0** y `agendar_cita-followup` con lifespan **0**.
3. Añade frases: `No, gracias`, `No la confirme`, `Mejor no`, `Está mal`.
4. **Responses:**
   > Entendido, no he registrado la cita. ¿Desea empezar de nuevo?
5. **Fulfillment:** webhook **desactivado**.
6. **SAVE**.

### 4.3 `agendar_cita - no - yes`
1. Sobre `agendar_cita - no` → **Add follow-up intent** → **yes**.
2. **Contexts:** entrada `agendar_cita-no-followup` (ya puesto). Salida: `agendar_cita-no-followup` con lifespan **0**.
3. **Responses:**
   > De acuerdo. Para empezar de nuevo, dígame: quiero agendar una cita.
4. **Fulfillment:** activa **Enable webhook call for this intent** (el webhook relanzará `agendar_cita` con el evento `INICIAR_CITA`).
5. **SAVE**.

### 4.4 `agendar_cita - no - no`
1. Sobre `agendar_cita - no` → **Add follow-up intent** → **no**.
2. **Contexts:** salida `agendar_cita-no-followup` con lifespan **0**.
3. **Responses:**
   > De acuerdo. ¿Le puedo ayudar en algo más?
4. Webhook **desactivado**. **SAVE**.

> Resultado esperado en la lista de intenciones:
> ```
> agendar_cita
>   ├─ agendar_cita - no
>   │    ├─ agendar_cita - no - no
>   │    └─ agendar_cita - no - yes
>   └─ agendar_cita - yes
> ```

---

## Bloque 5 — Resto de intenciones

Para cada una: **CREATE INTENT** → nombre → frases → parámetros (si hay) → respuesta de reserva → **Enable webhook call for this intent** → **SAVE**. Ninguna lleva contextos.

### 5.1 `consulta_documental`
Frases:
```
¿Dónde queda la clínica?
¿Cuál es la dirección de la clínica?
¿Cómo llego a la clínica en metro?
¿Tienen estacionamiento?
¿Hay dónde estacionar?
¿Cuál es el horario de la clínica?
¿Abren los sábados?
¿Qué formas de pago aceptan?
¿Aceptan pago móvil?
¿Puedo pagar con tarjeta?
¿Cuánto cuesta la consulta de dermatología?
¿Cuánto cobra el cardiólogo?
¿Cuál es el precio de un control?
¿Qué seguros aceptan?
¿Trabajan con mi seguro?
¿Cómo me preparo para la curva de glucosa?
¿Tengo que ir en ayunas?
¿Qué preparación necesito para el examen de próstata?
¿Qué debo llevar a la consulta?
¿Con cuánta anticipación debo cancelar una cita?
¿Puedo ir con un acompañante?
¿Qué pasa si llego tarde?
```
- Si Dialogflow anota "dermatología"/"cardiólogo" como `@especialidad`, déjalo: se crea un parámetro `especialidad` **no obligatorio** (no marques REQUIRED).
- **Responses:**
  > En este momento no puedo consultar esa información. ¿Desea que le comunique con recepción?

### 5.2 `consultar_horarios`
Frases:
```
¿Qué horario tiene dermatología?
¿Qué días atiende el cardiólogo?
¿A qué hora atiende el urólogo?
¿Cuándo hay consulta de oftalmología?
¿Qué días hay endocrinólogo?
Horarios de cirugía plástica
¿Qué médicos atienden cardiología y cuándo?
Quiero saber el horario de los médicos
¿Qué días atienden los dermatólogos?
¿El oculista atiende los sábados?
Horario de consulta
¿Cuándo puedo ver al endocrino?
```
- Parámetro: `especialidad` · `@especialidad` · **REQUIRED** · prompt: *¿De qué especialidad desea conocer el horario?*
- **Responses:**
  > Disculpe, ahora mismo no puedo consultar los horarios. Puede llamar a recepción para confirmarlos.

### 5.3 `consultar_historial`
Frases:
```
¿Con qué médico me atendí la última vez?
Quiero ver mi historial
¿Qué consultas he tenido?
¿Cuándo fue mi última cita?
¿Quién fue mi dermatólogo?
Quiero saber con qué doctor me vi
Consultar mi historial médico
¿Ya he venido antes a la clínica?
¿En qué especialidades me he atendido?
Revisar mis consultas anteriores
¿Me puede decir mis citas pasadas?
```
- **No añadas frases que contengan una cédula** ("Mi cédula es…"): si el usuario dice "mi cédula es 14523987" mientras `agendar_cita` le pide la cédula, Dialogflow saltaría a esta intención y se perderían los datos ya recogidos.
- Parámetro: `cedula` · `@cedula` · **REQUIRED** · prompt: *Con gusto. ¿Me indica su número de cédula?*
- Si se creó `especialidad` por "dermatólogo", déjalo **no obligatorio**.
- **Responses:**
  > Disculpe, ahora mismo no puedo consultar su historial. ¿Desea que le comunique con recepción?

### 5.4 `cancelar_cita`
Frases:
```
Quiero cancelar mi cita
Necesito anular una cita
No voy a poder ir a mi cita
Cancele mi consulta, por favor
Quiero suspender mi cita
Ya no necesito la cita
Elimine mi cita
Cancelar cita
No puedo asistir, cancele la cita
Quiero anular la consulta que tengo
Por favor, cancele mi turno
```
- Igual que en 5.3: **sin frases que contengan una cédula**.
- Parámetro: `cedula` · `@cedula` · **REQUIRED** · prompt: *Entiendo. ¿Me indica su número de cédula?*
- **Responses:**
  > Disculpe, ahora mismo no puedo cancelar su cita. Puede llamar a recepción para hacerlo.

### 5.5 `transferir_humano`
Frases:
```
Quiero hablar con una persona
Comuníqueme con recepción
Páseme con un humano
Necesito hablar con alguien de la clínica
Quiero hablar con un operador
Prefiero hablar con una persona real
Hablar con recepción
¿Me puede pasar con una secretaria?
Quiero atención personalizada
No quiero hablar con un robot
Comuníqueme con un agente
Transferir a recepción
```
- Sin parámetros.
- **Responses:**
  > Le comunico con recepción. Por favor, espere un momento.

> Limitación conocida: cuando Vicky pregunta "¿Desea que le comunique con recepción?" y el usuario dice "sí", ahora mismo no hay intención que lo capture (caerá en el fallback). Se resuelve en la spec 07 (transferencia a humano).

---

## Bloque 6 — Pruebas en el simulador

Usa el panel **Try it now** (derecha). Debajo de cada respuesta, **DIAGNOSTIC INFO** muestra la intención, los parámetros y los contextos. Para empezar una conversación limpia, recarga la página.

| # | Escribe | Esperado |
|---|---|---|
| P1 | `hola` | `Default Welcome Intent`, saludo de Vicky |
| P2 | `quiero una cita con el dermatólogo` | `agendar_cita`, especialidad = Dermatología, pregunta el nombre |
| P3 | `María González` → `venezolana` → `14.523.987` → `el próximo martes` → `a las 10 de la mañana` | Con "María González" rellena nombre y apellido a la vez (no pregunta el apellido); pide el resto en orden y termina con la respuesta de reserva de confirmación |
| P3b | Repite P2 y responde solo `María` | Pregunta "¿Me indica también su apellido?" |
| P4 | `sí` (tras P3) | `agendar_cita - yes` (respuesta de reserva, porque aún no hay webhook) |
| P5 | Repite P2–P3 y responde `no` | `agendar_cita - no`, "¿Desea empezar de nuevo?" |
| P6 | `soy colombiano` cuando pregunte la nacionalidad | nacionalidad = `E` |
| P7 | `14 523 987` cuando pregunte la cédula | cedula reconocida |
| P8 | `¿tienen estacionamiento?` | `consulta_documental` |
| P9 | `¿qué días atiende el cardiólogo?` | `consultar_horarios`, especialidad = Cardiología |
| P10 | `¿con qué médico me atendí la última vez?` | `consultar_historial`, pide la cédula |
| P11 | `quiero cancelar mi cita` | `cancelar_cita`, pide la cédula |
| P12 | `quiero hablar con una persona` | `transferir_humano` |
| P13 | `¿cuál es la capital de Francia?` | `Default Fallback Intent` |

Si alguna falla, dime cuál y qué muestra DIAGNOSTIC INFO.

---

## Bloque 7 — Exportar el agente

1. ⚙️ → pestaña **Export and Import** → **EXPORT AS ZIP** (borra antes cualquier `Grupo-Medico-Visoria.zip` anterior de Descargas).
2. Se descarga `Grupo-Medico-Visoria.zip` (en Descargas).
3. Se incorpora al repositorio **sin secretos** (el export incluye el token de la cabecera `X-Visoria-Token`):
   ```bash
   uv run python scripts/preparar_export.py ~/Downloads/Grupo-Medico-Visoria.zip
   uv run pytest tests/test_agente_export.py
   ```
   El script escribe `agente/` y `entrega/agente_dialogflow.zip` con el token sustituido por `<WEBHOOK_TOKEN>`.

---

## Riesgos y mitigación

| Riesgo | Mitigación |
|---|---|
| `@sys.given-name` no reconoce nombres poco comunes (habituales en Venezuela) | Se prueba en P3; si falla con nombres reales, se cambia a `@sys.any` y el webhook limpia el texto |
| Una regex con separador opcional reconoce solo parte del número (fallaban 7–8 dígitos seguidos) | Dos filas ordenadas (bloque 1.3); verificado con `detect_intent` |
| Frases con cédula en otras intenciones sacan al usuario de `agendar_cita` | Ninguna frase de entrenamiento contiene una cédula (bloques 5.3 y 5.4) |
| La cédula dictada por voz llega como "14 millones 523 mil 987" | Normalización en el webhook (spec 03) y prueba por voz (spec 06) |
| "Sí" tras "¿Desea que le comunique con recepción?" no tiene intención | Spec 07 |
| Un "no" suelto activaba `cancelar_cita` (confianza 0,33) | Ejemplos negativos en el fallback (bloque 2.2) |

## Verificación

- Bloque 6 en el simulador (CA-4 a CA-7).
- Sobre el export en `agente/`, `uv run pytest tests/test_agente_export.py` comprueba nombres de intenciones, follow-ups y sus contextos, parámetros obligatorios y su orden, entidades (incluida la regex de la cédula), webhook, respuestas de reserva, zona horaria y trato de usted (CA-1 a CA-3, CA-5, CA-8 a CA-10).
- Llamadas `detect_intent` de texto contra el agente real con las frases del bloque 6.
