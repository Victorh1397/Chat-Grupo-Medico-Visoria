# Spec 10 — Base de datos vectorial para la consulta documental (mejora opcional)

- **Estado:** Spec aprobada
- **Rúbrica:** Mejoras opcionales (hasta +1,5): *"Base de datos vectorial (ChromaDB, FAISS) en lugar de contexto directo en el prompt"*.
- **Depende de:** [Spec 04](../04-ocr-documentos/spec.md), [Spec 05](../05-consulta-documental/spec.md), [Spec 06](../06-voz/spec.md)

## Problema / objetivo

Hoy, para cada pregunta, el webhook envía a Gemini el **texto completo** de los cinco documentos (~5.600 caracteres, ~1.500 tokens;
spec 05). Funciona y es lo que el enunciado acepta como mínimo ("con un número reducido de documentos basta con incluir el texto en
el prompt"), pero no recupera: cada petición reenvía todo el texto y el sistema no escalaría si los documentos crecieran.

Esta spec sustituye el contexto directo por una **recuperación**: los documentos ya procesados por OCR se trocean y se indexan
**offline** en una base de datos vectorial; en cada pregunta se recuperan los fragmentos más cercanos y **solo esos** van al LLM.

```
OCR (offline) → documentos.json → fragmentos → embeddings → índice vectorial (offline, una vez)
Pregunta → embedding → fragmentos más cercanos → Gemini (solo esos fragmentos) → respuesta
                                 └─ si falla algo → texto completo, como hoy
```

**Antecedente:** Victor había previsto esta mejora (spec 10 con ChromaDB) y la descartó para cerrar la entrega (commit `1d9f317`),
retirando las referencias de la constitución, de CLAUDE.md y de las specs 04–05. El equipo la recupera: la spec incluye revisar esos
textos y los del README para que sigan siendo coherentes con la realidad.

## Alcance

**Incluye**
- Script offline de indexación: fragmentación del texto OCR, embeddings y escritura del índice.
- Base vectorial cargada al arrancar el webhook y recuperación por pregunta.
- Respaldo al texto completo si la recuperación falla.
- Evaluación comparativa con las 27 preguntas existentes.
- Tests mínimos y revisión de la documentación afectada (constitución, CLAUDE.md, README, diagrama).

**Fuera de alcance**
- Nuevos documentos o cambios en el OCR.
- Cambiar el modelo que redacta la respuesta ni sus instrucciones (control de alucinaciones de la spec 05).
- Embeddings locales (modelos que se descargan y ocupan memoria) y servidores de base vectorial externos.
- La Knowledge Base de Dialogflow (ya descartada en la spec 05).

## Requisitos

### R1. Indexación offline
1. Parte de `ocr/salida/documentos.json` y trocea por unidades con sentido: pregunta y respuesta (D1), fila de tabla (D2, D3),
   sección (D4, D5).
2. Calcula un embedding por fragmento con el modelo de embeddings de Gemini (misma clave que el resto del proyecto).
3. Escribe un índice versionado en texto (`ocr/salida/indice.json`: fragmentos, documento de origen y vectores). Se ejecuta una vez,
   nunca dentro de una petición, y se regenera si cambian los documentos (un test falla si no coinciden, como con el OCR).

### R2. Base vectorial
1. Al arrancar, el webhook carga el índice en una base vectorial en memoria (sin servidor ni descargas de modelos).
2. Si falta el índice, el webhook arranca igualmente y usa el texto completo.

### R3. Recuperación
1. Por pregunta se calcula un embedding de la consulta y se recuperan los k fragmentos más cercanos.
2. Al LLM solo llegan esos fragmentos, delimitados y con su documento de origen, y la pregunta sigue delimitada. Las instrucciones y
   la señal `NO_DISPONIBLE` no cambian.

### R4. Respaldo
1. Si el embedding falla, tarda más que su límite o la base no responde, la pregunta se contesta con el texto completo, como hoy.
2. El límite total de 4 s para Gemini, la petición de respaldo y los mensajes de reserva de la spec 06 siguen igual.

### R5. Sin pérdida de calidad
1. El control de alucinaciones en tres capas se mantiene.
2. La evaluación comparativa no debe empeorar respecto al texto completo medido en la misma sesión.

### R6. Documentación coherente
Las afirmaciones del repositorio sobre "texto completo en el prompt" se actualizan, y el README explica por qué se añadió la base
vectorial y qué se ganó o perdió con ella, con datos.

## Criterios de aceptación

- **CA-1.** La indexación genera un fragmento por unidad con sentido en los cinco documentos, todos los vectores con la misma
  dimensión, y es reproducible. Un test falla si el índice no corresponde a `documentos.json`.
- **CA-2.** "¿Tienen estacionamiento?" recupera el fragmento de D1 sobre estacionamiento y se responde bien.
- **CA-3.** "¿Cuánto cuesta el cardiólogo?" recupera las dos filas de cardiología de D2 y se responden los dos precios.
- **CA-4.** Las preguntas sin respuesta en los documentos (incluidas manipulación y consejo médico) siguen sin inventar: mismo
  mensaje de no disponible que hoy, 9/9.
- **CA-5.** Si el embedding o la base fallan (simulado en el test), la respuesta se da con el texto completo.
- **CA-6.** Evaluación con las 27 preguntas: aciertos respondibles no inferiores a los del texto completo en la misma sesión; turno
  completo por voz por debajo de 5 s; se documenta la latencia añadida por el embedding.
- **CA-7.** Voz y Telegram siguen funcionando igual (SSML solo en voz, botones en Telegram).
- **CA-8.** Tests automáticos: los imprescindibles, uno por criterio, sin red (embeddings simulados).
- **CA-9.** Constitución, CLAUDE.md, README (decisiones técnicas, "cómo se recupera") y diagrama de arquitectura actualizados.

## Preguntas abiertas

- **ChromaDB o FAISS.** Propuesta: **ChromaDB** en memoria (lo nombra el enunciado, guarda texto y metadatos junto al vector). Su
  coste es de dependencias: se comprobará en el plan que instala bien en Windows y macOS. FAISS es más ligero, pero obliga a guardar
  los textos aparte.
- **Modelo de embeddings y cuota.** Propuesta: el de Gemini con la clave actual. Hay que medir su latencia y su cuota gratuita, porque
  se suma a las 500 peticiones diarias en la parte de consultas.
- **Parámetros.** Valor de k, tamaño de los fragmentos y si un umbral de similitud baja decide algo; se fijan midiendo.
- **¿Se conserva el modo "texto completo" como alternativa?** Propuesta: sí, con una variable de entorno (`RECUPERACION`) para poder
  comparar y como respaldo; sin ella el comportamiento por defecto sería el nuevo.
- **Victor.** Fue su decisión descartarla; conviene avisarle antes de fusionar.

## Decisiones del equipo

- Spec aprobada tal como está redactada.
- La elección entre ChromaDB y FAISS queda para el plan, con datos de instalación (ver `plan.md`).
