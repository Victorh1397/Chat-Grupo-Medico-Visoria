# Guion del vídeo de demostración (≤ 3 minutos)

Spec: [99 — Entregables](../specs/99-entregables/spec.md) (R4). El vídeo debe mostrar la conversación **por voz de principio a
fin**, el **flujo con contexto** (cita con confirmación) y una **pregunta resuelta con los documentos**; además se enseña el
extra de **Telegram**.

## Escenas

| Tiempo | Escena | En pantalla |
|---|---|---|
| 0:00–0:12 | Presentación | Diagrama `docs/arquitectura.png` |
| 0:12–1:50 | **Voz**: cita completa de María González | Terminal del cliente de voz (y, si cabe, el log del webhook) |
| 1:50–2:15 | **Voz**: una pregunta documental y una sin respuesta | Igual |
| 2:15–2:50 | **Telegram**: menú, horarios con botones y transferencia a recepción | Telegram Desktop |
| 2:50–3:00 | Cierre: resumen de latencias | Terminal del cliente de voz tras salir |

Los tiempos de la escena de voz incluyen lo que tarda Vicky en hablar (la propuesta de cita dura ~15 s). Medido en la prueba
de la spec 06: 2,1 s de mediana por turno, más el habla de cada uno.

---

## Escena 1 — Presentación (0:00–0:12)

Con el diagrama en pantalla, decir (o poner como texto):

> "Esta es Vicky, la asistente por voz de Grupo Médico Visoria. Usa Dialogflow ES con su voz nativa, un webhook en FastAPI
> y Gemini con documentos leídos por OCR. Vamos a pedir una cita hablando."

## Escena 2 — Cita por voz (0:12–1:50)

`uv run python -m voz.cliente_voz` ya arrancado. En cada turno: **Enter**, decir la frase y **callar** (la grabación termina
sola). No pulsar Enter hasta que Vicky termine de hablar.

| # | Decir exactamente | Vicky responde (aprox.) | Qué demuestra |
|---|---|---|---|
| 1 | **"Hola"** | "Bienvenido a Grupo Médico Visoria, soy Vicky…" | Bienvenida |
| 2 | **"Quiero una cita con el dermatólogo"** | "¿Me indica su nombre y apellido, por favor?" | `agendar_cita`, entidad `@especialidad` |
| 3 | **"María González"** | "¿Usted es venezolano o extranjero?" | Parámetros de sistema |
| 4 | **"Venezolana"** | "¿Me indica su número de cédula?" | Entidad `@nacionalidad` |
| 5 | **"Catorce, quinientos veintitrés, novecientos ochenta y siete"** (pausado, en grupos: 14 523 987) | "¿Para qué fecha desea la cita?" | Entidad regex + validación con regex en el webhook |
| 6 | **"El próximo martes"** | "Ese día atiende la doctora Laura Rojas de 8:00 a 12:00; el primer horario libre es…" | Respuesta dinámica con disponibilidad |
| 7 | **"A las 10 de la mañana"** | "María, veo que ya se atendió en dermatología con la doctora Laura Rojas… 40 dólares. ¿Confirmo la cita a nombre de María González, cédula 14 523 987?" | Paciente reconocido, mismo médico, precio; cédula leída por grupos (SSML) |
| 8 | **"Sí"** | "Listo, María. Su cita C-I-T… está confirmada…" | Follow-up de confirmación; código leído letra a letra (SSML) |

## Escena 3 — Preguntas documentales por voz (1:50–2:15)

| # | Decir exactamente | Vicky responde (aprox.) | Qué demuestra |
|---|---|---|---|
| 9 | **"¿Tienen estacionamiento?"** | "Sí, la torre tiene estacionamiento propio en el sótano, gratuito las dos primeras horas…" | Respuesta con los documentos OCR + Gemini |
| 10 | **"¿Hacen resonancias magnéticas?"** | "No tengo esa información en los documentos de la clínica. ¿Desea que le comunique con recepción?" | Control de alucinaciones |

Después del turno 10, **no** contestar a la oferta: escribir `q` + Enter para salir y dejar el resumen de latencias en
pantalla para el cierre (se puede mostrar al final con un corte).

## Escena 4 — Telegram (2:15–2:50)

En Telegram Desktop, en el chat con el bot:

| # | Acción | Vicky responde | Qué demuestra |
|---|---|---|---|
| 11 | Escribir **"hola"** | Bienvenida con 4 botones | Integración nativa + menú con botones |
| 12 | Pulsar **"Horarios de los médicos"** | "¿De qué especialidad…?" con los 6 botones | Botones de especialidad |
| 13 | Pulsar **"Cardiología"** | Dra. Patricia Medina y Dr. Eduardo Rangel con sus horarios | `consultar_horarios` |
| 14 | Escribir **"¿Tienen servicio de pediatría?"** | "No tengo esa información… ¿Desea que le comunique con recepción?" con botones Sí/No | Sin alucinar, también por texto |
| 15 | Pulsar **"Sí"** | "Le comunico con recepción. Su número de caso es VIS-…" (o el mensaje de recepción cerrada, según la hora) | Transferencia a agente humano |

## Escena 5 — Cierre (2:50–3:00)

Volver a la terminal del cliente de voz con el resumen (mediana y máximo de latencia) y, si se quiere, el log del webhook con
las peticiones. Decir o poner como texto:

> "Todos los turnos por debajo de 5 segundos. El código, las specs y las instrucciones están en el repositorio."

---

## Lista de comprobación antes de grabar

**Entorno**
- [ ] Webhook **reiniciado justo antes de cada toma** (`Ctrl+C` y `uv run uvicorn webhook.main:app --port 8000`): la agenda
      vive en memoria y, si en una toma anterior ya se reservó el martes a las 10:00, Vicky propondrá otra hora.
- [ ] ngrok en marcha (`ngrok http 8000`) y `https://reenter-fled-lyricist.ngrok-free.dev/` responde con `"documentos_cargados": 5`.
- [ ] Una pregunta de prueba en el simulador de Dialogflow ("¿tienen estacionamiento?") para comprobar que Gemini responde.
- [ ] Grabar a una hora de poca carga para Gemini (preferiblemente por la mañana): en la spec 06 los picos de más de 4 s se
      dieron por la tarde.
- [ ] Un cliente de voz nuevo por toma (`uv run python -m voz.cliente_voz`): cada arranque es una sesión nueva.

**Audio y pantalla**
- [ ] Permiso de micrófono para la terminal o VS Code (Ajustes del Sistema → Privacidad y seguridad → Micrófono).
- [ ] **Altavoces, no auriculares**: la grabación de pantalla de macOS (`Cmd+Shift+5`) no captura el audio del sistema; con
      **Opciones → Micrófono** activado, el micrófono recoge tu voz y la de Vicky por los altavoces.
- [ ] Habitación en silencio (la grabación termina al detectar silencio).
- [ ] Letra de la terminal grande; terminal del cliente de voz y log del webhook visibles a la vez si es posible.
- [ ] Modo concentración activado (sin notificaciones).
- [ ] Telegram Desktop abierto en el chat con el bot.

**Ensayo**
- [ ] Un ensayo completo antes de la toma buena (y reiniciar el webhook después).
- [ ] Si un turno se reconoce mal, repetir la misma frase; si el flujo se desvía, reiniciar el webhook y empezar la toma de nuevo.

## Montaje

- Se pueden recortar los silencios **antes de pulsar Enter**, pero no las esperas de Vicky: la latencia real forma parte de lo
  que se evalúa.
- Duración final ≤ 3:00. Si se pasa, acortar la escena de Telegram (quitar los turnos 12–13).
- Subir el vídeo (por ejemplo, a YouTube como "no listado" o a Google Drive con enlace) y pegar el enlace al principio del README.
