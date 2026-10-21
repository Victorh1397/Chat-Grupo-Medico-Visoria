# Spec 99 — Entregables: README, diagrama, ZIP del agente y vídeo

- **Estado:** Hecha (falta grabar el vídeo, T7)
- **Rúbrica:** Documentación, diagrama y vídeo (1 pt). Además, el README es donde se defiende el resto de la nota: el material de clase
  insiste en que *"no es un trámite: es donde se evalúa que entendéis el sistema"*.
- **Depende de:** specs 01–08

## Problema / objetivo

Todo el sistema está construido y verificado, pero la entrega exige tres cosas que aún no existen en su forma final:

1. **Repositorio** con el export del agente (ZIP), el script de OCR y el código del webhook.
2. **README.md** con: descripción del caso de uso en un párrafo, diagrama de la arquitectura, lista de intenciones con su propósito,
   decisiones técnicas tomadas e instrucciones para ejecutar el proyecto.
3. **Vídeo** de un máximo de 3 minutos con la conversación por voz de principio a fin, incluyendo el flujo con contexto y una
   pregunta resuelta con los documentos.

El lector del README es **el profesor**: debe entender qué hace Vicky, cómo está construida, por qué se tomó cada decisión y cómo
ejecutarla en su máquina.

## Alcance

**Incluye**
- README.md completo en la raíz, en español.
- Diagrama de arquitectura (imagen en `docs/`).
- Comprobación final del ZIP del agente (`entrega/agente_dialogflow.zip`: último export, sin secretos).
- Guion del vídeo con tiempos y lista de comprobación previa a la grabación.
- Prueba de las instrucciones de ejecución en una copia limpia del repositorio.

**Fuera de alcance**
- Grabar y editar el vídeo (lo haces tú con el guion; macOS: `Cmd+Shift+5`).
- Cambios de funcionalidad (si la revisión final detecta un fallo, se trata aparte).

## Requisitos

### R1. README.md
1. **Caso de uso** en un párrafo: Grupo Médico Visoria, Vicky, qué resuelve.
2. **Diagrama de arquitectura**: voz / Telegram / simulador → Dialogflow ES (STT, intenciones, contexto, TTS) → webhook FastAPI
   (regex, agenda, transferencia) → Gemini; y la línea offline: documentos → OCR + regex → `documentos.json`.
3. **Intenciones** con su propósito, parámetros y si usan webhook; entidades (regex `@cedula`, `@nacionalidad`, `@especialidad`, de sistema);
   contexto `ctx_cita_en_curso` y follow-ups sí/no.
4. **Decisiones técnicas**, con los datos que las justifican: ngrok frente al túnel de VS Code, regex en dos niveles, preprocesado del OCR
   (tabla de similitud) y tratamiento de errores de OCR, texto completo en el prompt y por qué no la Knowledge Base de Dialogflow, control de
   alucinaciones en tres capas, modelo y latencia de Gemini (límite, petición de respaldo), SSML por canal, voz por defecto, botones de Telegram.
5. **Qué pasa si algo falla**: Gemini lento o caído, webhook caído (respuestas de reserva), cuota.
6. **Resultados**: tests, evaluación documental, latencias por voz.
7. **Mejoras opcionales realizadas** (transferencia, Telegram) y **mejoras futuras**.
8. **Instrucciones de ejecución** reproducibles por un tercero: requisitos, `.env`, importar el agente, webhook, ngrok, Fulfillment, cliente de voz,
   regenerar documentos y OCR, tests, evaluación.
9. **Estructura del repositorio**.
10. **Proceso SDD**: cómo se desarrolló el proyecto con specs (spec → plan → tareas → implementación → verificación), con enlace a `specs/`,
    la matriz de trazabilidad y ejemplos de decisiones que cambiaron gracias a las pruebas.

### R2. Diagrama
Imagen PNG en `docs/arquitectura.png`, **generada por código** (script versionado, reproducible), legible y referenciada desde el README.

### R3. ZIP del agente
`entrega/agente_dialogflow.zip` es el último export, coincide con `agente/`, pasa `tests/test_agente_export.py` y no contiene el token del
webhook ni el del bot de Telegram.

### R4. Guion del vídeo (`docs/guion_video.md`)
1. Escenas con tiempos que sumen **≤ 3 minutos**: presentación breve, conversación por voz de la cita (contexto, cédula validada, confirmación),
   pregunta documental por voz y **Telegram** (botones y transferencia a recepción).
2. Frases exactas que decir, para que el reconocimiento de voz funcione a la primera.
3. Lista de comprobación previa: webhook y ngrok en marcha, permiso de micrófono, latencia de Gemini (grabar en horas de menos carga),
   reiniciar el webhook para partir de una agenda limpia.

### R5. Verificación final
1. `uv run pytest` y `uv run ruff check .` en verde.
2. Una copia limpia del repositorio (clon nuevo) sigue las instrucciones del README hasta tener los tests en verde y el webhook arrancado.

## Criterios de aceptación

- **CA-1.** El README contiene los cinco elementos que pide el enunciado (caso de uso, diagrama, intenciones, decisiones técnicas, instrucciones).
- **CA-2.** El diagrama muestra todos los componentes y la línea offline del OCR.
- **CA-3.** Cada decisión técnica del README cita el dato o la prueba que la justifica (con enlace a la spec correspondiente).
- **CA-4.** El ZIP del agente pasa la verificación y no contiene secretos.
- **CA-5.** El guion del vídeo dura ≤ 3 minutos y cubre voz de principio a fin, flujo con contexto, pregunta documental y Telegram.
- **CA-6.** En un clon limpio, siguiendo el README, `uv sync` + `uv run pytest` pasan y el webhook arranca.

## Decisiones del autor

- Diagrama generado por código como imagen.
- El vídeo incluye Telegram.
- El README incluye una sección sobre el proceso SDD.
