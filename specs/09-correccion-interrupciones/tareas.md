# Tareas 09 — Corrección de datos e interrupciones en la cita

Plan: [plan.md](plan.md)

- [x] T1. Prueba corta con el agente real: qué contextos y parámetros llegan al webhook con una cita a medias (Claude). Resultado en
      `plan.md`: no hay `ctx_cita_en_curso` durante la recogida ni datos en la petición de la pregunta; hace falta borrador por sesión
- [x] T1b. Prueba de las dos incógnitas con el agente real (Claude): (a) una respuesta del webhook con solo contextos **conserva** la
      pregunta de Dialogflow; (b) reabrir la recogida desde otra intención **funciona**: tras "¿Tienen estacionamiento?" Vicky repite
      "¿Para qué fecha…?" y "El martes" continúa la cita con todos los datos. El código se integró directamente (T4 y T6)
- [x] T2. Consola: entidad `@dato_cita` e intención `corregir_dato` con sus frases (tú, guía del plan)
- [x] T3. Consola: frases nuevas en `consulta_documental` para menores y acompañantes (tú)
- [x] T4. Borrador de la cita por sesión y contexto `ctx_recogida_cita` en cada turno de `agendar_cita`; `repreguntar()` con intención de destino (Claude)
- [x] T5. `webhook/intenciones.py`: manejador `corregir_dato` + test (Claude). Verificado con el agente real: CA-1, CA-2, CA-3 y R1.3
      (el evento `INICIAR_CITA` con parámetros rellena la cita)
- [x] T6. `webhook/intenciones.py`: retoma de la cita tras `consulta_documental` y fallback + test (Claude)
- [x] T7. Pregunta absorbida por `agendar_cita`: **no necesaria**. Con las frases de la T3, Dialogflow clasifica bien las preguntas
      probadas, también a mitad de la cita (ver plan). Sin filtro, sin test (Claude)
- [x] T8. Nuevo export del agente y `tests/test_agente_export.py` actualizado (tú exportas, Claude incorpora)
- [ ] T9. Pruebas por `detect_intent` (espaciadas ~2 s), por voz y en Telegram: CA-1 a CA-9 (Claude + tú)
- [ ] T10. Verificar CA-8 y CA-10: `uv run pytest` y `uv run ruff check .` (Claude)
- [ ] T11. Actualizar `README.md` y `specs/README.md` (estado, trazabilidad, quitar la mejora futura 09) y commit `feat(09): …` (Claude)
