# Chat Grupo Médico Visoria

Asistente conversacional por voz para Grupo Médico Visoria, construido con Dialogflow ES, un webhook en FastAPI,
OCR offline con Tesseract y respuestas documentales con Gemini.

> En construcción. El README completo (caso de uso, diagrama, intenciones, decisiones técnicas e instrucciones)
> se redacta en la spec 99. El proceso de desarrollo está en [`specs/`](specs/README.md).

## Requisitos rápidos

- Python 3.12 + [uv](https://docs.astral.sh/uv/)
- Tesseract con idioma español (`brew install tesseract tesseract-lang`)
- Google Cloud CLI y un proyecto con la Dialogflow API habilitada

```bash
uv sync
cp .env.example .env   # y rellenar
```
