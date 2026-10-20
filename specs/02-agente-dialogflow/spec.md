# Spec 02 — Agente Dialogflow ES

- **Estado:** Hecha
- **Rúbrica:** Agente Dialogflow (4 pts): intenciones, entidad regex, contexto y confirmación.
- **Depende de:** [Spec 01](../01-caso-de-uso/spec.md)

## Problema / objetivo

Configurar en Dialogflow ES el agente `Grupo-Medico-Visoria` (proyecto `visoria-chat-1397`) para que implemente el mapa de
intenciones, las entidades y el contexto definidos en la spec 01. La configuración la hace el autor **a mano en la consola**,
siguiendo la guía paso a paso del `plan.md`. El resultado se exporta y se versiona en `agente/`.

## Alcance

**Incluye**
- Ajustes generales del agente (idioma, zona horaria).
- Entidades `@especialidad`, `@nacionalidad` y `@cedula`.
- Las 6 intenciones significativas, la bienvenida, el fallback y los follow-ups del flujo de cita.
- Contexto `ctx_cita_en_curso`, parámetros obligatorios con sus preguntas y respuestas estáticas de reserva.
- Activación del webhook en las intenciones que lo usan.
- Export del agente a `agente/` y verificación.

**Fuera de alcance**
- La URL del webhook y su lógica (spec 03). Hasta entonces, las intenciones con webhook responden con su respuesta estática de reserva.
- SSML y elección de voz (spec 06).
- Integración con Telegram (spec 08). Corrección de datos a mitad de flujo: mejora futura.

## Requisitos

### Ajustes del agente
1. Idioma `es`, zona horaria **`America/Caracas`** o, si la consola no la ofrece, una equivalente UTC-4 sin horario de verano (`America/Barbados`).

### Entidades
2. **`@especialidad`** (personalizada, con sinónimos): Dermatología, Endocrinología, Cirugía plástica, Urología, Cardiología, Oftalmología, cada una con sinónimos de uso común (nombre del especialista, órgano o motivo frecuente).
3. **`@nacionalidad`** (personalizada, con sinónimos, **sin** expansión automática; los gentilicios no listados los resuelve el webhook): valor `V` (venezolano, venezolana, de Venezuela…) y valor `E` (extranjero, extranjera y gentilicios frecuentes en Venezuela: colombiano, peruano, ecuatoriano, español, portugués, italiano…).
4. **`@cedula`** (regex): número sin 0 inicial, escrito con dígitos seguidos (6–9) o con separadores de miles (punto, coma o espacio). Dos expresiones, con la de dígitos seguidos primero. La validación estricta del rango según V/E la hace el webhook (spec 03).
4b. Ninguna frase de entrenamiento de `consultar_historial` ni `cancelar_cita` contiene una cédula, para que decir "mi cédula es…" durante `agendar_cita` no cambie de intención.

### Intenciones
5. **`Default Welcome Intent`**: presentación de Vicky y de lo que puede hacer, de usted.
6. **`agendar_cita`**:
   - Frases de entrenamiento variadas (≥ 15), con y sin datos dentro de la frase, anotando especialidad, fecha, hora, nombre y apellido cuando aparezcan.
   - Nombre y apellido se piden con **una sola pregunta** ("¿Me indica su nombre y apellido?"); si el usuario solo dice el nombre, se pregunta únicamente el apellido.
   - 7 parámetros **obligatorios**, en este orden y con su pregunta: `nombre` (@sys.given-name), `apellido` (@sys.last-name), `nacionalidad` (@nacionalidad), `cedula` (@cedula), `especialidad` (@especialidad), `fecha` (@sys.date), `hora` (@sys.time).
   - Contexto de salida `ctx_cita_en_curso` y el contexto de follow-up que crea Dialogflow.
   - Webhook activado, **también para el slot filling**, para validar la cédula en el turno en que se dice (spec 03).
   - Evento `INICIAR_CITA`, para poder reiniciar el flujo después de un "no".
7. **`agendar_cita - yes`** (follow-up *yes*): requiere `ctx_cita_en_curso`; webhook activado; cierra el contexto (lifespan 0).
8. **`agendar_cita - no`** (follow-up *no*): requiere `ctx_cita_en_curso`; respuesta estática "no se ha registrado la cita, ¿desea empezar de nuevo?"; cierra el contexto.
9. **`agendar_cita - no - yes`**: webhook activado; el webhook lanza el evento `INICIAR_CITA` para empezar de nuevo (spec 03). **`agendar_cita - no - no`**: respuesta estática ofreciendo otra ayuda.
10. **`consulta_documental`**: ≥ 20 frases que cubran los temas de los documentos D1–D5 (cómo llegar, estacionamiento, horario general, formas de pago, precios, horarios de médicos, preparación para exámenes, seguros, reglamento). Webhook activado.
11. **`consultar_horarios`**: parámetro obligatorio `especialidad`. Webhook activado.
12. **`consultar_historial`**: parámetro obligatorio `cedula`. Webhook activado.
13. **`cancelar_cita`**: parámetro obligatorio `cedula`. Webhook activado.
14. **`transferir_humano`**: frases tipo "quiero hablar con una persona", "comuníqueme con recepción". Webhook activado.
15. **`Default Fallback Intent`**: webhook activado.
16. Toda intención con webhook tiene una **respuesta estática de reserva**, de usted, para cuando el webhook no responda.

### Export
17. El agente se exporta como ZIP, se descomprime en `agente/` y se versiona en git.

## Criterios de aceptación

Se verifican sobre el export (`agente/`) y con llamadas `detect_intent` de texto al agente real:

- **CA-1.** El export contiene las 6 intenciones significativas, la bienvenida, el fallback y los 4 follow-ups, con los nombres exactos de esta spec.
- **CA-2.** `@cedula` es una entidad regex; `@especialidad` y `@nacionalidad` son personalizadas con los valores indicados.
- **CA-3.** `agendar_cita` tiene los 7 parámetros obligatorios, en orden, con su pregunta, y produce el contexto `ctx_cita_en_curso`.
- **CA-4.** "Quiero una cita con el dermatólogo" activa `agendar_cita` con `especialidad = Dermatología`, y Vicky pregunta el nombre.
- **CA-5.** Respondiendo uno a uno los datos de la conversación modelo, Vicky pide cada dato que falta y, al terminar, llega a la confirmación; "sí" activa `agendar_cita - yes` y "no" activa `agendar_cita - no`.
- **CA-6.** "Soy colombiano" y "venezolana" se reconocen como `E` y `V`; "14.523.987" y "14 523 987" se reconocen como `@cedula`.
- **CA-7.** Cada una de las frases de prueba del plan activa la intención esperada (consulta documental, horarios, historial, cancelación, humano).
- **CA-8.** Todas las intenciones que lo necesitan tienen el webhook activado (y el slot filling en `agendar_cita`) y una respuesta estática de reserva.
- **CA-9.** La zona horaria del agente es `America/Caracas` o equivalente UTC-4 sin horario de verano (`America/Barbados`).
- **CA-10.** Todas las respuestas y preguntas estáticas tratan al paciente de usted.

## Decisiones técnicas

| Tema | Decisión | Motivo |
|---|---|---|
| Configuración | Manual en la consola, guiada | Entender y poder defender cada pieza |
| Validación de la cédula | Regex permisiva en la entidad + validación estricta en el webhook durante el slot filling | El enunciado pide validar con regex en el webhook; detectar el error en el turno en que se dice |
| Reinicio tras "no" | Follow-up `- no - yes` + evento `INICIAR_CITA` lanzado por el webhook | Una respuesta estática no puede reactivar el slot filling de `agendar_cita` |
| Respuestas de reserva | Estáticas en cada intención con webhook | Si el webhook falla o tarda, Vicky no se queda en silencio |
| Zona horaria | `America/Barbados` | La consola no ofrece `America/Caracas`; ambas son UTC-4 sin horario de verano. Dialogflow solo la usa para resolver fechas relativas; el webhook trabaja con `America/Caracas` |
