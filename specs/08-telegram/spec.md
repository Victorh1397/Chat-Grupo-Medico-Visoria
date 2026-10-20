# Spec 08 — Vicky en Telegram (mejora opcional)

- **Estado:** Spec aprobada
- **Rúbrica:** Mejoras opcionales (hasta +1,5): *"Integración con Telegram o Slack, especialmente si usáis respuestas
  enriquecidas (tarjetas, botones, imágenes)"*.
- **Depende de:** [Spec 02](../02-agente-dialogflow/spec.md), [Spec 03](../03-webhook-fastapi/spec.md), [Spec 07](../07-transferencia-humano/spec.md)

## Problema / objetivo

Vicky solo se puede usar por voz (cliente en la terminal) o desde el simulador de Dialogflow. Esta spec la lleva a **Telegram**
como **otro canal del mismo chatbot**: el mismo agente de Dialogflow y el mismo webhook, ahora accesibles desde un bot de Telegram,
por texto y con **botones** para elegir sin escribir (especialidad, nacionalidad, sí/no).

```
Paciente por voz      ─┐
Paciente en Telegram  ─┼─► Dialogflow (agente Visoria) ─► webhook ─► Vicky responde
Simulador (texto)     ─┘
```

## Alcance

**Incluye**
- Bot de Telegram creado con @BotFather y conectado con la **integración nativa de Dialogflow ES** (sin servidor propio para Telegram).
- Detección del canal Telegram en el webhook.
- **Botones** (respuestas rápidas de Telegram) en los momentos de elección.
- Guía paso a paso para crear el bot y conectarlo (lo haces tú en Telegram y en la consola).

**Fuera de alcance**
- Notas de voz en Telegram (la integración nativa solo trata texto; la voz se cubre con el cliente de voz, spec 06).
- Tarjetas con imágenes, pagos o mapas.
- Avisos de Vicky por iniciativa propia (recordatorios de citas).
- Restringir el bot a una lista de usuarios: por ahora queda abierto a cualquiera (mejora futura).

## Requisitos

### R1. Conexión
1. Un bot de Telegram (nombre visible "Vicky · Grupo Médico Visoria") conectado al agente con la integración nativa de Dialogflow ES.
2. El token del bot solo se guarda en la consola de Dialogflow; nunca en el repositorio.
3. Todo lo que funciona por texto en el simulador funciona igual en Telegram: cita, horarios, historial, cancelación, consultas
   documentales con Gemini y transferencia a recepción.

### R2. Canal Telegram en el webhook
1. El webhook reconoce las peticiones que llegan desde Telegram.
2. En Telegram no se usa SSML (ya garantizado por la spec 06) y las respuestas son texto plano.

### R3. Botones
Cuando Vicky pide elegir entre opciones conocidas, en Telegram muestra botones además de la pregunta:

| Momento | Botones |
|---|---|
| Bienvenida | Agendar una cita · Horarios · Preguntas frecuentes · Hablar con recepción |
| Especialidad (al agendar o al consultar horarios) | Las 6 especialidades |
| Nacionalidad | Venezolano · Extranjero |
| Confirmación de la cita | Sí · No |
| "¿Desea empezar de nuevo?" | Sí · No |
| Oferta de recepción (spec 07) | Sí · No |

Los botones son **solo una ayuda, nunca obligatorios**:
- Pulsar un botón equivale a escribir su texto; Dialogflow y el webhook no distinguen entre una cosa y otra.
- El usuario puede ignorarlos y escribir lo que quiera (otra forma de decirlo, otra nacionalidad, otra pregunta): se atiende igual que sin botones.
- Desaparecen tras usarlos.

## Criterios de aceptación

- **CA-1.** Escribiendo "hola" al bot en Telegram, Vicky saluda y muestra los botones del menú.
- **CA-2.** Una cita completa se agenda en Telegram usando botones para especialidad, nacionalidad y confirmación.
- **CA-2b.** Escribir en lugar de pulsar los botones ("soy colombiano", "quiero ver a un dermatólogo", o cambiar de tema con "¿tienen
  estacionamiento?") funciona igual que sin botones.
- **CA-3.** Una pregunta documental ("¿tienen estacionamiento?") se responde con los documentos, sin etiquetas SSML.
- **CA-4.** "¿Hacen resonancias?" → oferta de recepción con botones Sí/No → "Sí" crea el caso (spec 07).
- **CA-6.** El resto de canales (voz y simulador) siguen funcionando igual y sin botones.
- **CA-7.** Tests automáticos con peticiones de ejemplo de Telegram (canal y botones).

## Decisiones técnicas

| Tema | Decisión | Motivo |
|---|---|---|
| Conexión | Integración nativa de Dialogflow ES | Sin servidor ni código propio para Telegram; acordado en la planificación |
| Botones | Respuestas rápidas de Telegram añadidas por el webhook solo en ese canal | Un único punto de control; los otros canales no cambian |
| Voz en Telegram | No | La integración nativa no procesa notas de voz; la voz obligatoria ya está cubierta (spec 06) |

## Decisiones del autor

- Momentos con botones de R3: aprobados.
- Se activa el webhook en la `Default Welcome Intent` para el menú con botones.
- El bot queda abierto a cualquiera; restringirlo a una lista de usuarios queda como posible mejora futura.
