# Constitución del proyecto

Principios no negociables. Toda spec, plan y tarea debe respetarlos; si alguno tiene que cambiar, se cambia aquí primero.

1. **Trazabilidad con el enunciado.** Cada requisito obligatorio del PDF tiene al menos una spec con un criterio de aceptación verificable, y aparece en la matriz de `specs/README.md`.
2. **Latencia < 5 s por turno.** El OCR es offline y nunca se ejecuta dentro de una petición. Toda llamada al LLM lleva timeout, `try/except` y una respuesta de reserva.
3. **Sin alucinaciones.** El LLM responde únicamente con información extraída por OCR de los documentos, nunca con conocimiento propio. Si la respuesta no está en los documentos, el sistema lo dice explícitamente y ofrece una alternativa. El mecanismo de recuperación (texto completo en el prompt o fragmentos desde ChromaDB) no cambia este principio.
4. **Secretos fuera del repositorio.** Claves y credenciales solo en `.env` o en rutas fuera del repo. `.env.example` documenta las variables necesarias.
5. **Agente configurado a mano y versionado por export.** El agente Dialogflow ES se configura manualmente en la consola siguiendo la guía paso a paso del `plan.md` de cada spec; la consola es la fuente de verdad. Tras cada cambio se exporta el ZIP y se versiona descomprimido en `agente/`, donde se verifica automáticamente contra la spec. El ZIP de entrega es el último export.
6. **Diseñado para voz.** Respuestas en español, breves (2–3 frases), con SSML cuando mejore la naturalidad. Voz únicamente con STT/TTS nativos de Dialogflow.
7. **Datos ficticios.** Ningún dato real de pacientes. Los datos de negocio son simulados.
8. **Pequeño y funcionando.** Se prioriza que el mínimo obligatorio funcione de extremo a extremo antes de abordar cualquier extra. Mejor un extra bien hecho que varios a medias.
9. **Verificable.** La lógica del webhook, las regex y el control de alucinaciones tienen tests automáticos (`uv run pytest`).
