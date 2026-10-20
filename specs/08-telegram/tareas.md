# Tareas 08 — Vicky en Telegram

Plan: [plan.md](plan.md)

- [x] T1. Crear el bot con @BotFather y conectarlo en Integrations → Telegram (tú); comprobar que responde con el agente actual.
      Probar los dos formatos de botones con una respuesta de prueba y elegir el que funcione como se espera (Claude + tú): ambos se comportan igual; elegido `quickReplies`
- [x] T2. Canal Telegram en `webhook/dialogflow.py` + `webhook/telegram.py` (botones según la respuesta) + tests (Claude)
- [x] T3. Preguntas de especialidad y nacionalidad formuladas por el webhook en Telegram para añadir botones + tests (Claude)
- [x] T4. Manejadores de bienvenida, `agendar_cita - no` y "Preguntas frecuentes" + tests (Claude)
- [x] T5. Cambios en la consola: webhook en bienvenida y `agendar_cita - no`, slot filling en `consultar_horarios` (tú)
- [x] T6. Nuevo export del agente + `tests/test_agente_export.py` actualizado (tú exportas, Claude incorpora)
- [ ] T7. Pruebas en la app de Telegram (tú) y por Dialogflow (Claude): CA-1 a CA-6
- [ ] T8. Actualizar `specs/README.md` y commit `feat(08): …` (Claude)
