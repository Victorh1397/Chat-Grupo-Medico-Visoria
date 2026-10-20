# Spec 07 — Transferencia a agente humano (mejora opcional)

- **Estado:** Hecha
- **Rúbrica:** Mejoras opcionales (hasta +1,5): *"Intención adicional de transferencia a agente humano"*.
- **Depende de:** [Spec 03](../03-webhook-fastapi/spec.md), [Spec 05](../05-consulta-documental/spec.md)

## Problema / objetivo

Hoy `transferir_humano` solo responde "Le comunico con recepción" con un número de caso. Pero Vicky **ofrece** pasar con recepción
en muchos momentos ("No tengo esa información… ¿Desea que le comunique con recepción?") y, si el usuario dice **"sí"**, la frase
cae en el fallback y no pasa nada (limitación anotada desde la spec 02). Esta spec convierte la transferencia en un flujo
completo y coherente: se puede pedir directamente, aceptar cuando Vicky la ofrece, y Vicky la ofrece sola si no está entendiendo
al usuario. La transferencia es **simulada**: se registra un caso con el resumen de la conversación para recepción.

## Alcance

**Incluye**
- Aceptar ("sí", "por favor", "claro") o rechazar ("no", "no gracias") la oferta de recepción que Vicky hace en sus respuestas.
- Ofrecer recepción tras **dos turnos seguidos sin entender** al usuario.
- Caso de transferencia con número `VIS-#####`, motivo y resumen (qué estaba haciendo el usuario y los datos ya dados).
- Registro de los casos en un fichero (simula la cola de recepción) y mensaje según el horario de recepción.

**Fuera de alcance**
- Conexión con una persona real (llamada, chat en vivo).
- Notificar el caso al personal de recepción por otro medio (correo, mensajería…): el caso solo se registra en un fichero.
- Corrección de datos a mitad de flujo (mejora futura).

## Requisitos

### R1. Petición directa
"Quiero hablar con una persona" (intención `transferir_humano`) crea un caso y Vicky responde con el número de caso y qué ocurrirá.

### R2. Aceptar o rechazar la oferta
1. Cuando una respuesta de Vicky termina ofreciendo recepción, el siguiente turno del usuario se interpreta en ese contexto:
   - "sí", "sí, por favor", "claro", "de acuerdo"… → se crea el caso (motivo: el de la oferta).
   - "no", "no gracias"… → *"De acuerdo. ¿Le puedo ayudar en algo más?"*
   - Cualquier otra cosa → se atiende con normalidad y la oferta caduca.
2. La oferta solo vale para el turno siguiente.

### R3. Oferta automática
Si Vicky no entiende al usuario **dos turnos seguidos** (fallback sin información), en el segundo dice:
*"Parece que no le estoy entendiendo bien. ¿Desea que le comunique con recepción?"*

### R4. Caso de transferencia
1. Número `VIS-#####`, fecha y hora, canal (voz o texto) y **motivo**: petición directa, información no disponible, error técnico o no entendido.
2. **Resumen** para recepción: última pregunta del usuario y, si estaba agendando una cita, los datos ya dados (nombre, especialidad, fecha).
   Nunca la cédula completa: solo los 3 últimos dígitos.
3. Se guarda en `logs/transferencias.jsonl` (no versionado) y se muestra en el log del webhook.

### R5. Horario de recepción
1. Dentro del horario de la clínica (lunes a viernes 7:00–19:00, sábados 7:00–13:00, hora de Caracas): *"Le comunico con recepción.
   Su número de caso es VIS-12345. Una persona le atenderá en breve."*
2. Fuera de horario: *"En este momento recepción está cerrada; abrimos de lunes a viernes de 7:00 a 19:00 y los sábados de 7:00 a
   13:00. He registrado su caso VIS-12345 y le contactarán en el próximo horario de atención."*

## Criterios de aceptación

- **CA-1.** "Quiero hablar con una persona" → caso `VIS-#####` registrado con motivo "petición directa" y respuesta según el horario.
- **CA-2.** Tras *"No tengo esa información… ¿Desea que le comunique con recepción?"*, "sí" crea el caso con motivo "información no
  disponible" y la pregunta original en el resumen; "no" responde *"De acuerdo. ¿Le puedo ayudar en algo más?"*.
- **CA-3.** Si tras la oferta el usuario pregunta otra cosa ("¿tienen estacionamiento?"), se responde con normalidad; un "sí" posterior ya no transfiere.
- **CA-4.** Dos turnos seguidos sin entender → oferta automática; con "sí", caso con motivo "no entendido".
- **CA-5.** Si la transferencia ocurre a mitad de una cita, el resumen incluye nombre, especialidad y fecha, y solo los 3 últimos dígitos de la cédula.
- **CA-6.** Fuera de horario, el mensaje lo indica y da el horario de recepción.
- **CA-7.** Funciona igual por voz (SSML) y por texto; tests automáticos de R1–R5 y prueba por Dialogflow.

## Decisiones técnicas

| Tema | Decisión | Motivo |
|---|---|---|
| Detectar el "sí" a la oferta | El webhook recuerda, por sesión, que acaba de ofrecer recepción; el "sí"/"no" sin contexto llega al fallback (verificado en la spec 02) y el webhook lo interpreta | No requiere cambios en la consola de Dialogflow; misma técnica de estado por sesión que la spec 03 |
| Registro de casos | Fichero JSON Lines | Simula una cola de recepción legible |
| Privacidad | Cédula enmascarada en el resumen | El caso lo lee personal de recepción |

## Decisiones del autor

- El "sí"/"no" a la oferta se detecta en el webhook (sin cambios en la consola).
- Oferta automática tras dos turnos sin entender: aprobada.
- Mensaje fuera de horario: aprobado.
