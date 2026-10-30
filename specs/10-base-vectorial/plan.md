# Plan 10 — Base de datos vectorial para la consulta documental

Implementa: [spec.md](spec.md)

## Enfoque

Se añade una capa de recuperación entre el texto OCR y Gemini, sin tocar el resto del flujo:

```
OCR (offline)  documentos.json ──► fragmentar ──► embeddings (Gemini) ──► indice.json   [offline, una vez]
Petición       pregunta ──► embedding ──► FAISS (en memoria) ──► k fragmentos ──► Gemini   [con respaldo: texto completo]
```

- La recuperación vive en un módulo nuevo (`webhook/recuperacion.py`). `webhook/documentos.py` solo decide qué documentos entran en el
  prompt: los fragmentos recuperados o, si algo falla, todo el texto como hasta ahora.
- El prompt, las instrucciones, la señal `NO_DISPONIBLE` y la red de seguridad de la spec 05 **no cambian**.
- La indexación es offline y el índice se versiona en texto, igual que `documentos.json`.

## Decisión de librería: FAISS en lugar de ChromaDB (cambio respecto a la spec)

La spec proponía ChromaDB. Comprobado en seco con `uv pip install --dry-run` en este equipo:

| | Paquetes nuevos | Observaciones |
|---|---|---|
| `chromadb` 1.5.9 | **53** (onnxruntime, kubernetes, tokenizers, opentelemetry…) | Para ~50 vectores es desproporcionado y alarga la instalación del proyecto |
| `faiss-cpu` 1.15.1 | **1** | Búsqueda exacta (`IndexFlatIP`) en memoria; los textos se guardan en el propio `indice.json` |

Propuesta: **FAISS**. Sigue siendo una base vectorial de las que cita el enunciado ("ChromaDB, FAISS"). Si el equipo prefiere ChromaDB, el
diseño no cambia: solo se sustituye el interior de `webhook/recuperacion.py`.

## Ficheros afectados

| Fichero | Cambio |
|---|---|
| `ocr/indexar.py` (nuevo) | `fragmentar()` (pura, probable sin red) y el script offline que calcula los embeddings y escribe el índice |
| `ocr/salida/indice.json` (nuevo, versionado) | Modelo, dimensión, y por fragmento: id, documento, título, texto y vector |
| `webhook/recuperacion.py` (nuevo) | Carga el índice en FAISS al arrancar; `recuperar(pregunta, k)`; embedding de la consulta con límite de tiempo |
| `webhook/documentos.py` | Modo de recuperación, presupuesto de tiempo total, respaldo al texto completo, registro de los fragmentos usados |
| `scripts/evaluar_documental.py` | Opción para elegir fichero de salida y poder comparar los dos modos en la misma sesión |
| `tests/test_recuperacion.py` (nuevo), `tests/conftest.py` | Tests mínimos sin red; el embedding se simula (por defecto falla, de modo que los tests actuales siguen usando el texto completo) |
| `pyproject.toml`, `uv.lock`, `.env.example` | Dependencia `faiss-cpu`; variable `RECUPERACION` |
| `specs/00-constitucion.md`, `CLAUDE.md`, `README.md`, `specs/04`, `specs/05`, `specs/README.md`, `docs/generar_diagrama.py`, `docs/arquitectura.png` | Documentación coherente (CA-9) |

## Diseño

### Fragmentación (`ocr/indexar.py::fragmentar`)
Sin depender del formato exacto del OCR:
1. Se quita la cabecera repetida de cada documento (nombre y dirección de la clínica), que ensuciaría los vectores; se conserva el título.
2. Se parte por bloques en blanco; un documento de un solo bloque (D4) se parte por líneas.
3. En D1 cada línea que empieza por "¿" abre un fragmento nuevo (pregunta y respuesta juntas).
4. Se agrupan líneas hasta ~400 caracteres con solape de una línea, de modo que dos filas de tabla vecinas (p. ej. los dos cardiólogos
   de D2) queden juntas en algún fragmento.
5. Cada fragmento lleva delante el título de su documento.

Resultado esperado: ~50 fragmentos. El tamaño y el solape se ajustan midiendo (T6), no a ojo.

### Embeddings
- Modelo de embeddings de Gemini con la clave actual (candidato: `gemini-embedding-001`, con `RETRIEVAL_DOCUMENT` para los fragmentos y
  `RETRIEVAL_QUERY` para la pregunta, y una dimensión reducida, p. ej. 768, para que el índice sea pequeño). Los vectores se normalizan
  (L2) para usar producto interno como similitud del coseno.
- **T1 confirma** que el modelo está disponible con la clave, su dimensión, su latencia y su cuota antes de escribir nada definitivo.

### Recuperación y presupuesto de tiempo (R3, R4)
- `recuperar()` embebe la pregunta con un límite propio (~1 s) y devuelve los k fragmentos más cercanos (k inicial 4–5).
- **El límite total sigue siendo 4 s** (Dialogflow da 5 s). Hoy esos 4 s son solo de Gemini; con el embedding delante, `documentos.py`
  descuenta lo gastado: `tiempo_máximo = 4 s − lo consumido`, y `preguntar_con_limite()` recibe ese límite. Si el embedding falla rápido,
  Gemini conserva casi todo el margen; si tarda el máximo, queda ~3 s, que es lo habitual (mediana 0,8–1,7 s).
- Cualquier fallo (embedding, índice ausente, FAISS) → texto completo, con un `log.warning`. Es el mismo patrón que la spec 05.
- Al LLM llega el mismo formato de siempre (`<documento id= titulo=>`), pero con el texto de los fragmentos recuperados agrupados por
  documento. El log registra qué fragmentos se usaron.
- Si se pasa `documentos` explícitamente a `responder_con_documentos()` (tests y evaluación), no se recupera: se usan esos documentos.

### Modo y configuración
`RECUPERACION=vectorial` (por defecto) o `completo` en el `.env`. Permite comparar en la misma sesión (CA-6) y deja una salida de
emergencia sin tocar código.

### Sin cambios en la consola de Dialogflow
Toda la lógica está en el webhook. No hay tareas de consola ni nuevo export del agente.

## Resultados de la prueba T1

Con la clave del equipo, 4 fragmentos de ejemplo y 5 consultas:

| Observación | Dato |
|---|---|
| Modelos con `embedContent` | `gemini-embedding-001`, `gemini-embedding-2` y `gemini-embedding-2-preview` |
| Modelo elegido | `gemini-embedding-001` |
| Latencia de una consulta | Mediana ~270 ms, máx. 286 ms (768 y 256 dimensiones) |
| Latencia de un lote de 4 fragmentos | 280–360 ms |
| FAISS (`IndexFlatIP` con vectores normalizados) | Funciona; 4 de 4 consultas respondibles devuelven el fragmento correcto en primer lugar |
| Separación respondible / no respondible | A 768 dimensiones: respondibles 0,74–0,78 y "¿Hacen resonancias?" (no está en los documentos) 0,62. A 256 la separación es menor (0,79–0,81 frente a 0,73) |
| Dimensión elegida | **768** |
| Cuota de embeddings | No se expone en la respuesta de la API; se vigila con los errores 429 en T3 y T6 |

La latencia del embedding (~0,3 s) cabe holgadamente en el presupuesto de 4 s. La diferencia entre respondibles y no respondibles abre la
puerta a un umbral de similitud, pero el plan no lo da por hecho: se decide con la evaluación (T6).

## Resultados de la evaluación comparativa (T6)

**Recuperación sola** (sin generar respuesta): para las 18 preguntas respondibles, los datos necesarios están en los fragmentos
recuperados con **k = 3, 4, 5 y 6** (18/18 en todos). Se fija **k = 4**, con margen sobre el mínimo. Las preguntas no respondibles
puntúan 0,55–0,74 y las respondibles 0,68–0,78: **se solapan, así que un umbral de similitud no es fiable** y la decisión de "no está en
los documentos" sigue siendo del modelo, como antes. Tamaño de fragmento: 25 fragmentos de ≤ 300 caracteres; no hizo falta ajustarlo.

**Evaluación de las 27 preguntas con Gemini real**, misma sesión y mismo código (`evaluacion/resultados_spec10_*.json`):

| | Texto completo | Base vectorial |
|---|---|---|
| Respondibles | 18/18 | 18/18 |
| No respondibles sin inventar | 9/9 | 9/9 |
| Errores o tiempo agotado | 0 | 0 |
| Latencia: mediana / p95 / máximo | 0,74 / 1,01 / 2,01 s | 0,83 / 0,96 / 1,21 s |

Conclusión honesta: con cinco documentos pequeños la base vectorial **no mejora la calidad** (el texto completo ya cabía de sobra) y cuesta
unos 0,1 s de mediana por el embedding; a cambio envía menos texto al modelo y el peor caso no empeora. Su valor es que el diseño escala
si los documentos crecen.

**Hallazgos durante la evaluación**
1. **Regresión latente de la spec 05 destapada por los fragmentos.** La red de seguridad contra negativas redactadas (`NEGATIVA`) buscaba
   "no aparece", "no figura"… en toda la respuesta. Una respuesta correcta que dice de pasada "si su seguro **no aparece** en la lista,
   puede pagar y pedir el reembolso" se convertía en "no tengo esa información" (7 de 8 intentos con la base vectorial en
   "¿Qué seguros aceptan?"). Ahora se mira solo la **primera frase**, que es donde está una negativa real; `NO_DISPONIBLE` se sigue
   buscando en todo el texto. Test añadido a la batería existente.
2. **Arranque en frío del embedding.** La primera consulta tras arrancar superaba el límite de 1 s y esa pregunta se quedaba sin
   recuperación (caía al texto completo, sin romper nada). El webhook calienta el cliente al arrancar (`recuperacion.calentar()`) y la
   evaluación también.
3. **Límite de peticiones por minuto de Gemini.** Al repetir una pregunta cada 2 s aparecieron errores 429. La evaluación espacia las
   preguntas 6 s, como ya hacía.

## Riesgos y mitigación

- **La recuperación pierde información** que el texto completo no perdía (p. ej. una pregunta que necesita dos tablas). Mitigación:
  fragmentos con solape, k holgado, y la evaluación de 27 preguntas comparada con el texto completo (CA-6). Si empeora, se ajusta k y
  el tamaño; si aun así empeora, se deja `completo` por defecto y se documenta con datos.
- **Latencia.** Una llamada más por pregunta. Mitigación: límite propio del embedding y presupuesto total de 4 s; se mide por voz.
- **Cuota.** El embedding consume la cuota gratuita de embeddings, que se mide en T1 (separada de la de generación, a confirmar). La
  evaluación comparativa gasta ~54 peticiones de generación y ~54 embeddings.
- **Índice desincronizado** con `documentos.json` si cambian los datos. Mitigación: test de sincronía y aviso en el README (como el OCR).
- **FAISS en macOS/Windows.** En este equipo (Windows) instala sin compilar. T1 lo confirma al instalarlo; el README lo documenta.
- **Tamaño del índice versionado.** ~50 vectores × 768 floats en texto: unos cientos de KB. Si molesta, se reduce la dimensión.

## Verificación

| Criterio | Cómo se comprueba |
|---|---|
| CA-1 | Test: `fragmentar` cubre los 5 documentos y el índice versionado coincide con `documentos.json` (sincronía y misma dimensión) |
| CA-2, CA-3 | Evaluación con embeddings reales (T6), mirando los fragmentos registrados para "estacionamiento" y "cardiólogo"; y un test del cableado con vectores a mano |
| CA-4 | Evaluación: las 9 preguntas no respondibles siguen sin inventar |
| CA-5 | Test: si `recuperar` lanza una excepción, el prompt lleva todos los documentos |
| CA-6 | `scripts/evaluar_documental.py` en los dos modos, misma sesión; latencia por voz con el cliente de voz |
| CA-7 | Conversación por voz y por Telegram (T7) |
| CA-8 | `uv run pytest` y `uv run ruff check .` en verde, con los tests mínimos nuevos |
| CA-9 | Revisión de los textos listados en "Ficheros afectados" |
