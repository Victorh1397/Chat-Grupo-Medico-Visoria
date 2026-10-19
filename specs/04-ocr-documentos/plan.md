# Plan 04 — Documentos sintéticos y pipeline OCR offline

Implementa: [spec.md](spec.md)

## Enfoque

Tres piezas separadas para poder probarlas por separado:
1. **Contenido** de los documentos como bloques (título, párrafos, listas, tablas). D2 y D3 se construyen desde `webhook/datos.py`.
2. **Generación**: Pillow dibuja cada documento en una página tamaño carta y le aplica un efecto de escaneo. Se guarda también el texto de referencia.
3. **OCR**: preprocesado + Tesseract + extracción y validación con regex + JSON de salida. Parte de `webhook_dialogflow/ocr.py` de clase
   (`leer_documento`, `PATRONES`, `extraer_datos`, `normalizar_ocr`) ampliándolo.

## Ficheros

| Fichero | Contenido |
|---|---|
| `ocr/contenido.py` | Bloques de D1–D5 y datos generales (dirección, teléfonos, pagos, aseguradoras) |
| `ocr/generar_documentos.py` | Dibujo con Pillow (tipografía Arial del sistema), tablas con líneas, cabecera y pie; efecto de escaneo con semilla fija (reproducible); escribe `ocr/documentos/*.png` y `ocr/referencia/*.txt` |
| `ocr/extraccion.py` | Regex (importes, horarios, teléfonos, fechas, pares médico→precio y médico→horario), normalización solo para regex y validación contra `webhook/datos.py`. Sin dependencia de Tesseract |
| `ocr/ocr.py` | Preprocesado, OCR, similitud con la referencia, informe y `ocr/salida/documentos.json`; opción `--comparar` para medir el efecto del preprocesado |
| `tests/test_ocr_extraccion.py` | Regex con errores típicos de OCR, validación y coherencia del JSON |

## Diseño

### Efecto de escaneo
Fondo de papel (gris cálido), rotación de 0,5–1,5° (sentido alterno), ruido gaussiano, desenfoque ligero (radio ~0,6) y
pérdida de nitidez por reescalado. Semilla fija por documento para que las imágenes sean reproducibles.

### Preprocesado del OCR (cada paso se justifica midiendo la similitud)
1. Escala de grises.
2. Ampliación ×2 (Tesseract rinde mejor con letras de ~30 px de alto).
3. Corrección de inclinación: se prueban ángulos de −3° a 3° y se elige el que maximiza la varianza del perfil horizontal (las líneas de texto quedan horizontales).
4. Binarización con umbral de Otsu (separa tinta y papel aunque el fondo no sea blanco).
5. Tesseract `lang="spa"`, `--psm 6` (bloque uniforme; funciona con las tablas de una fila por médico).

### Regex
- Importes: `(\d{1,4})\s*(?:USD|\$|d[oó]lares)` y `\$\s*(\d{1,4})`.
- Horarios: `(\d{1,2}):(\d{2})\s*(?:-|–|a)\s*(\d{1,2}):(\d{2})`.
- Teléfonos: `\(?0(?:2\d{2}|4\d{2})\)?[\s-]?\d{3}-?\d{4}`.
- Fechas: `\b\d{1,2}/\d{1,2}/\d{4}\b`.
- Pares: por línea, `(Dra?\.)\s+(<nombre>)` + importe (D2) o + días + horario (D3).
- Normalización solo para regex: en tokens que ya contienen dígitos, `O→0`, `o→0`, `l/I→1`, `S→5`, `B→8`.

### Similitud
`difflib.SequenceMatcher` sobre ambos textos con espacios normalizados; se informa por documento y la media.

## Riesgos y mitigación

| Riesgo | Mitigación |
|---|---|
| Las líneas de las tablas se leen como `|` o `l` | Regex tolerantes; separadores ignorados al extraer pares |
| Acentos mal reconocidos | `lang="spa"`; la similitud lo cuantifica |
| Tesseract no disponible en otra máquina | `documentos.json` versionado; los tests no requieren Tesseract |

## Verificación
- `uv run python -m ocr.generar_documentos` → 5 PNG (CA-1).
- `uv run python -m ocr.ocr` → informe con similitud (CA-3), validación de D2/D3 (CA-4, CA-5), teléfonos y fecha (CA-6), JSON (CA-7), tiempo (CA-2).
- `uv run python -m ocr.ocr --comparar` → tabla de similitud con y sin preprocesado para el README.
- `uv run pytest` (CA-8).
