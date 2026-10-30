# Tareas 09 — Corrección de datos e interrupciones en la cita

Plan: [plan.md](plan.md)

- [ ] T1. Prueba corta con el agente real, antes de escribir código: con una cita a medias, comprobar qué contextos y parámetros llegan al
      webhook y si `repreguntar()` reabre la recogida con un dato vaciado (Claude lee el registro; tú haces la conversación)
- [ ] T2. Consola: entidad `@dato_cita` e intención `corregir_dato` con sus frases (tú, guía del plan)
- [ ] T3. Consola: frases nuevas en `consulta_documental` para menores y acompañantes (tú)
- [ ] T4. `webhook/dialogflow.py`: `repreguntar()` con intención de destino y lectura de datos desde `ctx_cita_en_curso` (Claude)
- [ ] T5. `webhook/intenciones.py`: manejador `corregir_dato` + test (Claude)
- [ ] T6. `webhook/intenciones.py`: retoma de la cita tras `consulta_documental` y fallback + test (Claude)
- [ ] T7. `webhook/intenciones.py`: pregunta absorbida por `agendar_cita` (filtro + retoma) + test (Claude)
- [ ] T8. Nuevo export del agente y `tests/test_agente_export.py` actualizado (tú exportas, Claude incorpora)
- [ ] T9. Pruebas por `detect_intent` (espaciadas ~2 s), por voz y en Telegram: CA-1 a CA-9 (Claude + tú)
- [ ] T10. Verificar CA-8 y CA-10: `uv run pytest` y `uv run ruff check .` (Claude)
- [ ] T11. Actualizar `README.md` y `specs/README.md` (estado, trazabilidad, quitar la mejora futura 09) y commit `feat(09): …` (Claude)
