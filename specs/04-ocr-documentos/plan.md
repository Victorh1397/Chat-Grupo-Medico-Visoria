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
5. **Quitar las líneas de las tablas**: tramos rectos de tinta mucho más largos que una letra (horizontales ≥ 1/30 del ancho,
   verticales ≥ 60 px), ampliando la máscara 4 px porque los bordes escaneados son irregulares. *Añadido tras la primera prueba*:
   sin él, Tesseract confundía las celdas con letras.
6. Tesseract `lang="spa"`, `--psm 6` (bloque uniforme; funciona con las tablas de una fila por médico).

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

## Tratamiento de errores de OCR
- Confusiones de caracteres en cifras (O/0, l/1, S/5, B/8): corrección solo en fragmentos con dígitos, sobre una copia para las regex.
- Confusión "rn" → "m" ("viemes", "Hemández") y letras perdidas ("vienes"): los nombres de médicos y los días se comparan por parecido
  (`difflib`, umbrales 0,85 y 0,75), no por igualdad exacta. La validación sí detecta un precio u horario realmente distinto.
- El texto que se guarda para el LLM es el OCR original, sin estas correcciones.

## Resultados (19/10/2026)

Similitud con el texto de referencia al ir añadiendo pasos (`uv run python -m ocr.ocr --comparar`):

| Preprocesado | D1 | D2 | D3 | D4 | D5 | Media |
|---|---|---|---|---|---|---|
| Sin preprocesado | 99,9 % | 59,4 % | 49,9 % | 99,8 % | 99,9 % | 81,8 % |
| + grises | 99,8 % | 85,3 % | 50,4 % | 99,9 % | 99,9 % | 87,0 % |
| + ampliar | 99,9 % | 60,8 % | 45,5 % | 99,8 % | 99,9 % | 81,2 % |
| + enderezar | 99,9 % | 63,1 % | 45,6 % | 99,9 % | 99,9 % | 81,7 % |
| + binarizar | 99,9 % | 64,8 % | 45,6 % | 99,8 % | 99,9 % | 82,0 % |
| **+ quitar líneas** | **99,9 %** | **99,9 %** | **99,4 %** | **99,8 %** | **99,9 %** | **99,8 %** |

- En texto corrido Tesseract acierta casi todo sin ayuda; **las tablas dependen de quitar las líneas** (que exige binarizar antes).
- Prueba de ablación sobre las tablas con líneas quitadas: sin enderezar D2 99,7 % / D3 99,4 %; sin ampliar 99,3 % / 99,2 %.
  Ampliar y enderezar aportan poco en estos documentos, pero se mantienen como margen ante escaneos reales más torcidos o con letra pequeña.
- Validación contra `webhook/datos.py`: precios 12/12 y horarios 12/12 (tras la tolerancia a "rn"→"m"). Teléfonos de D1 y fecha de
  vigencia de D2 extraídos. Tiempo total del OCR: 4,3 s.

## Verificación
- `uv run python -m ocr.generar_documentos` → 5 PNG (CA-1).
- `uv run python -m ocr.ocr` → informe con similitud (CA-3), validación de D2/D3 (CA-4, CA-5), teléfonos y fecha (CA-6), JSON (CA-7), tiempo (CA-2).
- `uv run python -m ocr.ocr --comparar` → tabla de similitud con y sin preprocesado para el README.
- `uv run pytest` (CA-8).
