# Spec 09 — Corrección de datos e interrupciones en la cita (mejora opcional)

- **Estado:** Hecha
- **Rúbrica:** Mejoras opcionales (hasta +1,5): *"Gestión de interrupciones y corrección de datos a mitad de flujo mediante eventos"*.
- **Depende de:** [Spec 02](../02-agente-dialogflow/spec.md), [Spec 03](../03-webhook-fastapi/spec.md), [Spec 05](../05-consulta-documental/spec.md), [Spec 06](../06-voz/spec.md), [Spec 08](../08-telegram/spec.md)

## Problema / objetivo

Hoy la cita es un camino de un solo sentido: Vicky pide los siete datos en orden y, mientras los pide, todo lo que dice el
usuario se interpreta como el dato que se está esperando. Dos situaciones reales no funcionan:

1. **Corregir un dato.** El usuario se da cuenta de un error ("me equivoqué con la cédula", "mejor para el jueves") y la única
   salida es decir "no" en la confirmación y empezar de cero, repitiendo los siete datos.
2. **Interrumpir con una pregunta.** A mitad de la cita pregunta algo ("¿tienen estacionamiento?") y Vicky lo toma como respuesta
   a la pregunta pendiente o cambia de intención y pierde lo recogido. Además, ciertas preguntas se clasifican como `agendar_cita`
   (p. ej. "¿Mi hijo menor de edad puede ir solo a la consulta?", confianza 0,50) y Vicky responde "¿Me indica su nombre y
   apellido?" en lugar de contestar.

Esta spec añade ambas capacidades **sin perder los datos ya dados**: corregir cambia solo ese dato, e interrumpir contesta la
pregunta y vuelve a la cita donde se quedó. La spec 09 estaba prevista como hoja de ruta (ver `specs/README.md`); aquí se concreta.

## Alcance

**Incluye**
- Corrección de un dato ya dado, en cualquier momento de la recogida y también ante la propuesta de cita ("¿Confirmo…?").
- Datos corregibles: nombre y apellido, nacionalidad, cédula, especialidad, fecha y hora.
- Interrupción por una pregunta documental durante la recogida de datos: se responde y se retoma la cita.
- Funciona igual por voz, en el simulador y en Telegram.
- Tests automáticos con Gemini y Dialogflow simulados, y pruebas con Dialogflow real.

**Fuera de alcance**
- Corregir una cita ya confirmada (se cancela y se agenda otra con las intenciones existentes).
- Corregir varios datos en una sola frase ("cambia la cédula y la fecha").
- Interrumpir con otras intenciones que no sean preguntas documentales (horarios, historial, cancelar), salvo lo que ya funciona hoy.
- Cambiar los datos de la clínica, el OCR o el modelo de Gemini.

## Requisitos

### R1. Corregir un dato
1. En cualquier momento antes de confirmar, el usuario puede indicar qué dato quiere cambiar ("me equivoqué con la cédula",
   "la fecha no es esa", "cambio la especialidad").
2. Vicky vuelve a pedir **solo ese dato**, conserva los demás y continúa el flujo normal desde ahí, con todas las validaciones
   de siempre (cédula con regex según nacionalidad, fecha laborable, hora libre…).
3. Si el usuario da el nuevo valor en la misma frase ("la cédula es 14523987"), se usa sin volver a preguntarlo.
4. Si cambia un dato del que dependen otros, se revalidan: cambiar la especialidad o la fecha puede invalidar la hora y entonces
   Vicky la vuelve a pedir explicando el motivo.
5. Ante la propuesta de cita, un "no" seguido de una corrección ("no, la cédula está mal") corrige ese dato; un "no" sin más
   mantiene el comportamiento actual (¿empezar de nuevo?).

### R2. Interrupción con una pregunta
1. Si durante la recogida de datos el usuario hace una pregunta sobre la clínica, Vicky la responde con los documentos
   (como en la spec 05) y **retoma la cita** repitiendo la pregunta pendiente.
2. Los datos ya dados se conservan.
3. La respuesta sigue las reglas de siempre: solo con los documentos, y si el dato no está lo dice y ofrece recepción.
4. Una pregunta documental mal clasificada como `agendar_cita` (caso del hijo menor de edad) se responde con los documentos
   en lugar de pedir el nombre.

### R3. Sin regresiones
1. El camino completo actual (siete datos, propuesta, "sí", "no", empezar de nuevo) funciona igual.
2. Voz (SSML solo en ese canal), Telegram (botones) y la transferencia a recepción (spec 07) siguen funcionando.
3. Latencia por turno < 5 s; la corrección y la retoma no añaden llamadas a Gemini salvo la de la propia pregunta documental.

## Criterios de aceptación

- **CA-1.** Dada una cita con nombre, nacionalidad y cédula dados, cuando el usuario dice "me equivoqué con la cédula" y da otra
  válida, entonces la cédula queda actualizada y Vicky continúa con el siguiente dato pendiente sin volver a pedir el resto.
- **CA-2.** Dado ese mismo estado, cuando el nuevo valor no es válido (p. ej. 5 dígitos), entonces Vicky explica el motivo y pide
  solo la cédula.
- **CA-3.** Dados los siete datos y la propuesta ya hecha, cuando el usuario dice "no, la fecha es otra" y da una fecha válida,
  entonces Vicky revalida la hora y hace una nueva propuesta con los datos conservados.
- **CA-4.** Dado que el usuario cambia la especialidad y la hora ya dada no existe para ese médico, entonces Vicky lo explica y
  pide solo la hora.
- **CA-5.** Dada una cita a medias, cuando el usuario pregunta "¿tienen estacionamiento?", entonces Vicky responde con el
  documento D1 y repite la pregunta pendiente; al contestarla, la cita continúa con los datos previos.
- **CA-6.** Dada una cita a medias, cuando el usuario pregunta algo que no está en los documentos, entonces Vicky lo dice y retoma
  la cita (sin perder los datos).
- **CA-7.** "¿Mi hijo menor de edad puede ir solo a la consulta?" se responde con los documentos, tanto en una conversación nueva
  como a mitad de una cita.
- **CA-8.** La conversación modelo de la spec 01 (cita completa de María González) sigue pasando sin cambios, por texto y por voz.
- **CA-9.** CA-1, CA-5 y CA-7 funcionan en Telegram, y las respuestas del canal de voz llevan SSML solo en ese canal.
- **CA-10.** Tests automáticos: los imprescindibles, uno por criterio de aceptación o regla, con Gemini y Dialogflow simulados.

## Preguntas abiertas

- **¿Cómo se logra en Dialogflow ES?** El diseño previsto era una intención `corregir_dato` más un evento que reactive
  `agendar_cita` restaurando los datos con contextos. Hay que comprobar con el agente real qué cambios exigen la consola y cuáles
  se resuelven solo en el webhook, porque el agente se configura a mano (constitución, principio 5). Se decide en el plan.
- **¿Cómo se detecta la interrupción?** Dialogflow ES mantiene el contexto de recogida de datos y puede absorber la pregunta como
  dato. Se estudiará en el plan si basta con el webhook (como ya hace con las fechas y nacionalidades) o si hace falta una
  intención con prioridad o frases de entrenamiento nuevas.
- **¿Se corrige la mala clasificación de R2.4 aquí o en una spec aparte?** La propuesta es incluirla porque comparte causa (una
  pregunta a mitad de flujo); si crece, se separa.
- **¿Se incluyen las limitaciones de la edición Trial** (límite de consultas por minuto) al probar con Dialogflow real? Se
  espaciarán las pruebas ~2 s, como indica CLAUDE.md.

## Decisiones del equipo

- Spec aprobada tal como está redactada.
- El alcance queda como se propone: sin corregir varios datos a la vez, sin corregir citas ya confirmadas y sin otras interrupciones
  que no sean preguntas documentales.
- La mala clasificación del caso "hijo menor de edad" se resuelve dentro de esta spec (R2.4), no en una aparte.
