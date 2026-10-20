# Tareas 06 — Voz de extremo a extremo

Plan: [plan.md](plan.md)

- [x] T1. Verificación técnica (Claude): ¿el TTS interpreta SSML del webhook?, ¿llega el payload `canal` al webhook?, ¿qué voces `es-US` femeninas funcionan? → decidir SSML o plan B
- [x] T2. Muestras de audio de las voces candidatas con la misma frase (Claude) → **elección de la voz (tú)**: `es-US-Chirp3-HD-Aoede`
- [x] T3. `webhook/ssml.py` + canal en `webhook/dialogflow.py` y `main.py` + tests (Claude)
- [x] T4. `webhook/numeros.py` + uso en la recogida de la cédula + tests (Claude)
- [x] T5. `voz/grabacion.py` (fin por silencio) + tests con señales sintéticas (Claude)
- [x] T6. `voz/cliente_voz.py`: bucle, pistas de frases, voz elegida, `--texto`, latencias y registro de sesión (Claude)
- [ ] T7. Permiso de micrófono para VS Code y primera prueba hablada corta (tú)
- [ ] T8. Conversación modelo completa por voz (tú hablas; Claude analiza el registro) y ajustes
- [ ] T9. Comprobar en el simulador de Dialogflow que no aparecen etiquetas SSML (tú o Claude)
- [ ] T10. Actualizar `specs/README.md` y commit `feat(06): …` (Claude)
