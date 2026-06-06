# Graph Report - /Users/hylurte/Auditoria  (2026-06-06 — v9: Rúbrica enriquecida con Condiciones Generales)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 20 nodes · 20 edges · 7 communities
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Estado del Pipeline

| Fase | Nodos | Estado | Resultado |
|------|-------|--------|-----------|
| Fase 1 — Audio | 1-4 | ✅ COMPLETADA | 20min, 20.1% silencios, ES 74.3% |
| Fase 2 — Transcripción | 5, 8, 9 | ✅ COMPLETADA  | 2 interlocutores · 3 intervenciones · guion_diarizado.txt |
| Fase 3 — Análisis IA | 10-11 | ✅ COMPLETADA | Qwen3-8B Q4 · 30 criterios · 3.57/10 llamada prueba · resultado_fase3.json |
| Fase 4 — Salida | 12-13 | 🔴 Pendiente | — |
| Fase 5 — Docker | 14 | 🔴 Pendiente | — |

## Actualización v9 — Base de Conocimiento DIGI

Condiciones Generales DIGI (Tarifa v.14.8, mayo 2026) analizadas e integradas en la rúbrica:

| Criterio | Enriquecimiento |
|----------|----------------|
| `ps2` | Portabilidad: 1 día hábil (02:00-06:00); umbral uso no razonable (>30× o >150 números) |
| `ao3` | Precios completos (3€–15€ móvil; 10€–30€ fibra); permanencia 3 meses; router depósito; IVA incluido |
| `ao4` | 10 ventajas estrella documentadas: precio, red Movistar, datos acumulables, DIGI-DIGI gratis, 3 meses permanencia, instalación gratis, router depósito, descuentos combo, datos reducidos, facturación por segundos |
| `ao5` | Tabla de precios de referencia + guía de cálculo de ahorro (€/mes y €/año) con ejemplo concreto |
| `cl2` | Plazos oficiales: portabilidad 1 día hábil; router mensajería; penalización 50€ router no devuelto |

Archivo de conocimiento generado: `docs/rubrica_digi_conocimiento.json`

## God Nodes (más conectados)
- **auditor_avanzado** — recibe el guión de Fase 2 y es documentado por README y doc técnica.

## Surprising Connections
- `fase1_nodo_voxlingua` → `fase2_nodo_whisper` (receives_from): Fase 1 y Fase 2 son un pipeline continuo — `audio_vad.wav` fluye directamente de una a otra.
- `fase2_nodo_pyannote` → `auditor_avanzado_evaluar_llamada_local` (feeds_into, INFERRED): El guión diarizado de Fase 2 es la entrada exacta del auditor — tres comunidades forman una sola cadena.

## Import Cycles
- None detected.

## Communities (7 total)

### Community 0 — Motor de Auditoría (cohesión: 0.67) — prototipo de referencia
- `auditor_avanzado.py`
- `evaluar_llamada_local()` — L20
- `auditar_directorio_masivo()` — L200

### Community 1 — Punto de Entrada (cohesión: 1.0) ⚠️ vacío
- `principal.py`

### Community 2 — Transcriptor (cohesión: 1.0) ⚠️ vacío
- `transcriptor.py`

### Community 3 — Pipeline Audio Fase 1 (cohesión: 0.90) ✅ COMPLETADA
- `notebooks/fase1_audio.ipynb`
- `Nodo 1: ffmpeg` — WAV 16kHz mono
- `Nodo 2: noisereduce` (→ DeepFilterNet 3 en Docker)
- `Nodo 3: Silero VAD` — 1231s → 983s (20.1% reducción)
- `Nodo 4: VoxLingua107` — ES, 74.3%, sin flags

### Community 4 — Documentación (cohesión: 1.0)
- `docs/documentacion_tecnica.docx` — v1.1
- `docs/rubrica_digi_conocimiento.json` — v1.0 (Condiciones Generales v.14.8)
- `README.md` — v2, estado actualizado por fase

### Community 5 — Pipeline Transcripción Fase 2 (cohesión: 0.90) ✅ COMPLETADA
- `notebooks/fase2_transcripcion.ipynb`
- `Nodo 5: faster-whisper Medium` ✓ — ASR sin conflicto NumPy 2.x
- `Nodo 8: word_timestamps nativos de faster-whisper` ✓ — sin dependencias externas
- `Nodo 9: pyannote 3.1` ✓ — fix use_auth_token → token (API nueva)

### Community 6 — Pipeline Análisis IA Fase 3 (cohesión: 0.90) ✅ COMPLETADA
- `notebooks/fase3_analisis_ia.ipynb`
- `Nodo 10: Qwen3-8B Q4` — LLM auditor (4-bit T4; Docker: Qwen3-235B vLLM)
- `Nodo 11: Rúbrica DIGI + Puntuación Dinámica` — 30 criterios, pesos N/A-aware, resultado_fase3.json
- **Rúbrica enriquecida** — guías ps2, ao3, ao4, ao5, cl2 actualizadas con Condiciones Generales

## Próximas conexiones esperadas (Fase 4)
- `notebooks/fase4_salida.ipynb` → Community 7
- `fase4_pdf` → WeasyPrint → replicar formato informe DIGI (tablas azules, gráficas)
- `fase4_postgres` → INSERT resultado en PostgreSQL
