# Tareas 10 — Base de datos vectorial para la consulta documental

Plan: [plan.md](plan.md)

- [x] T1. Prueba corta antes de escribir código definitivo: instalar `faiss-cpu`, confirmar con la clave real que el modelo de
      embeddings está disponible (dimensión, latencia, cuota) y que normalizar y buscar con FAISS funciona (Claude). Resultado en
      `plan.md`: `gemini-embedding-001`, 768 dimensiones, ~270 ms por consulta, FAISS correcto
- [x] T2. `ocr/indexar.py`: `fragmentar()` sin red + test (Claude)
- [x] T3. Generar `ocr/salida/indice.json` con embeddings reales + test de sincronía con `documentos.json` (Claude)
- [x] T4. `webhook/recuperacion.py`: carga en FAISS al arrancar y `recuperar()` con límite de tiempo + test del cableado (Claude)
- [x] T5. Integración en `webhook/documentos.py`: modo `RECUPERACION`, presupuesto de 4 s, respaldo al texto completo y registro de
      fragmentos + tests de respaldo y de que al modelo solo llegan los fragmentos recuperados (Claude)
- [x] T6. Evaluación comparativa de las 27 preguntas en los dos modos y ajuste de k y del tamaño de fragmento; resultados en `plan.md`
      (Claude; consume peticiones de la cuota gratuita)
- [x] T7. Pruebas con el agente real: voz (latencia del turno completo) y Telegram, CA-7 (tú + Claude). Telegram: preguntas documentales,
      una con errata, una sin respuesta y una a mitad de la cita, sin SSML. Voz: turnos de 1,85–3,24 s por el canal de voz con
      Dialogflow real (cliente en modo texto; sin conversación hablada con micrófono)
- [x] T8. Documentación: constitución, CLAUDE.md, README, notas en las specs 04 y 05, `.env.example`, diagrama y `specs/README.md` (Claude)
- [x] T9. `uv run pytest` y `uv run ruff check .`; commit `feat(10): …` (Claude)
