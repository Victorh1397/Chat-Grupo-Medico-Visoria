# Spec 04 — Documentos sintéticos y pipeline OCR offline

- **Estado:** Hecha
- **Rúbrica:** OCR, validación con regex y respuesta documental (3 pts): esta spec cubre la **extracción** y la **validación**;
  la consulta con Gemini y el control de alucinaciones son la spec 05. Mejora opcional: documentos complejos (tablas).
- **Depende de:** [Spec 01](../01-caso-de-uso/spec.md) (catálogo D1–D5), [Spec 03](../03-webhook-fastapi/spec.md) (`webhook/datos.py`)

## Problema / objetivo

Vicky debe responder preguntas frecuentes a partir de documentos de la clínica que **no existen**. Esta spec:
1. **Crea** los 5 documentos D1–D5 como **imágenes** que simulan papeles escaneados (sin capa de texto).
2. Los **procesa una sola vez con OCR** (Tesseract, español) con un preprocesado de imagen justificado.
3. **Valida y extrae** campos del texto reconocido con **expresiones regulares** (importes, horarios, teléfonos, fechas).
4. **Guarda** el resultado en `ocr/salida/documentos.json`, que el webhook cargará al arrancar (spec 05).

## Alcance

**Incluye**
- Script que genera las 5 imágenes a partir de un contenido de referencia y, para D2 y D3, de los datos del webhook (`webhook/datos.py`).
- Efecto de documento escaneado: escala de grises con tono de papel, ligera inclinación, ruido y desenfoque.
- Script OCR offline: preprocesado, OCR con Tesseract, normalización, extracción con regex y medición de la calidad.
- Comprobación de coherencia: los precios y horarios **extraídos por OCR** de D2 y D3 coinciden con los del webhook.
- Tests de las regex y de la coherencia del JSON.

**Fuera de alcance**
- Uso del texto por el LLM y control de alucinaciones (spec 05).
- Base de datos vectorial (spec 10).
- OCR en tiempo real: el OCR **nunca** se ejecuta dentro de una petición del webhook (límite de 5 s).

## Documentos

Todos llevan cabecera "Grupo Médico Visoria" y el pie *"Documento ficticio elaborado con fines académicos"*.

| # | Documento | Contenido | Parte | Formato |
|---|---|---|---|---|
| D1 | Preguntas frecuentes | Dirección, cómo llegar (metro y autobús), estacionamiento, horario general, teléfonos, formas de pago, qué traer a la consulta | General | Texto en preguntas y respuestas |
| D2 | Tarifario de consultas | Especialidad, médico y precio único en USD (igual para primera vez y control), con fecha de vigencia | Por médico | **Tabla** |
| D3 | Horarios de los médicos | Especialidad, médico, días y horas | Por médico | **Tabla** |
| D4 | Preparación para exámenes | Indicaciones por especialidad (curva de glucosa, PSA, biopsia de piel, valoración preoperatoria, prueba de esfuerzo, fondo de ojo con dilatación) | Por especialidad | Secciones |
| D5 | Seguros y reglamento | Aseguradoras aceptadas (ficticias), copagos, política de cancelación (24 h), llegada 15 min antes, acompañantes, menores de edad | General | Texto con listas |

**Datos generales** (todos ficticios):
- Dirección: Av. Principal de Los Palos Grandes, Torre Visoria, piso 3, Caracas. Metro: estación Altamira (10 minutos a pie).
- Teléfonos: (0212) 555-0142 y WhatsApp (0414) 555-0187.
- Estacionamiento propio en el sótano: gratuito las 2 primeras horas para pacientes.
- Formas de pago: efectivo en dólares, tarjetas de débito y crédito, pago móvil y transferencia.
- Aseguradoras ficticias: Seguros Araguaney, Cumbre Azul Seguros, Salud Llanera y Previsión Caribe.

## Requisitos

### R1. Generación de los documentos
1. Un script genera `ocr/documentos/D1_…jpg` … `D5_…jpg` (imágenes JPEG como las de un escáner, 150 ppp, tamaño carta).
2. D2 y D3 se generan **desde `webhook/datos.py`**: si cambia un precio o un horario, se regeneran y Vicky no se contradice.
3. Cada imagen simula un escaneo: tono de papel, inclinación de 0,5–1,5°, ruido y ligero desenfoque. Las imágenes no tienen capa de texto: extraer su texto **es** OCR.
4. El texto de referencia de cada documento se guarda aparte (`ocr/referencia/`) solo para **medir** la calidad del OCR; nunca se usa como sustituto del OCR.

### R2. OCR offline
1. Un script procesa todas las imágenes de `ocr/documentos/` con Tesseract (`spa`).
2. **Preprocesado** antes del OCR, cada paso justificado en el README: escala de grises, ampliación, corrección de inclinación, binarización. Para las tablas se usa el modo de segmentación de página adecuado.
3. Se ejecuta **una sola vez** (o al cambiar los documentos), nunca desde el webhook.

### R3. Validación y extracción con regex
1. Sobre una **copia normalizada** del texto (corrigiendo confusiones típicas del OCR solo donde se esperan cifras: O/0, l/1, S/5), se extraen:
   - **Importes:** `40 USD`, `$ 40`, `40 dólares`.
   - **Horarios:** `8:00 - 12:00`, `14:00 a 18:00`.
   - **Teléfonos venezolanos:** `(0212) 555-0142`, `0414-555-0187`.
   - **Fechas:** `01/09/2026`.
2. De D2 se extraen los pares **médico → precio** y de D3 los pares **médico → horario**, y se **validan** contra `webhook/datos.py`. Cualquier discrepancia se informa.
3. La normalización es **destructiva** ("Oftalmología" → "0ftalm0l0gía"), así que solo se aplica a la copia que pasa por las regex. Lo que se
   guarda para el LLM es el **texto OCR original**, tanto si en la spec 05 se le da completo como si se trocea en una base vectorial (spec 10):
   ```
   imagen → OCR → texto original ─┬─► copia normalizada → regex → validación
                                  └─► documentos.json → (completo o fragmentos de la base vectorial) → LLM
   ```

### R4. Salida
`ocr/salida/documentos.json`, versionado en git (el webhook no necesitará Tesseract), con, por documento: id, título, archivo,
texto OCR, campos extraídos, resultado de la validación y calidad (similitud con el texto de referencia).

### R5. Informe
El script imprime un resumen por documento: caracteres, similitud con la referencia, campos extraídos y discrepancias.

## Criterios de aceptación

- **CA-1.** Existen 5 imágenes JPEG en `ocr/documentos/`, sin capa de texto, con aspecto de documento escaneado.
- **CA-2.** El OCR procesa las 5 imágenes sin errores en menos de 1 minuto en total.
- **CA-3.** La similitud media entre el texto OCR y la referencia es **≥ 90 %**; ningún documento por debajo del 85 %.
- **CA-4.** La regex de importes extrae los 12 precios de D2 y **todos coinciden** con `webhook/datos.py`.
- **CA-5.** La regex de horarios extrae los horarios de los 12 médicos de D3 y coinciden con `webhook/datos.py`.
- **CA-6.** Se extraen los teléfonos de D1 y la fecha de vigencia de D2.
- **CA-7.** `ocr/salida/documentos.json` contiene los 5 documentos con texto, campos extraídos, validación y calidad.
- **CA-8.** Los tests de las regex (con ejemplos con errores típicos de OCR) y de coherencia del JSON pasan con `uv run pytest`, sin necesidad de Tesseract.
- **CA-9.** Todos los datos de los documentos son ficticios y así lo indica cada documento.

## Decisiones técnicas

| Tema | Decisión | Motivo |
|---|---|---|
| Origen de los documentos | Generados por código como imágenes con efecto de escaneo | No existen; el enunciado exige que sean imágenes (sin capa de texto) |
| Motor OCR | Tesseract 5 con `spa` (ya instalado) | Visto en clase, local, gratuito y rápido; las tablas sencillas se leen bien con el modo de segmentación adecuado |
| Calidad | Similitud con el texto de referencia | Permite justificar el preprocesado con números en el README |
| Coherencia | Validar los datos extraídos de D2 y D3 contra `webhook/datos.py` | Demuestra la validación con regex y garantiza que Vicky no se contradiga |
| Formato de salida | JSON versionado | El webhook lo carga al arrancar sin depender de Tesseract |

## Decisiones del autor

- Datos generales propuestos: aprobados.
- Imágenes generadas por código.
