# Graph Report - /Users/hylurte/Auditoria  (2026-06-05 — actualizado tras Fase 1)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 12 nodes · 10 edges · 5 communities
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Estado del Pipeline

| Fase | Nodos | Estado | Resultado |
|------|-------|--------|-----------|
| Fase 1 — Audio | 1-4 | ✅ COMPLETADA | 20min llamada, 20.1% silencios eliminados, ES 74.3% |
| Fase 2 — Transcripción | 5-9 | 🔴 Pendiente | Whisper Medium + WhisperX + pyannote |
| Fase 3 — Análisis IA | 10-11 | 🔴 Pendiente | Qwen3-8B + RAG |
| Fase 4 — Salida | 12-13 | 🔴 Pendiente | PDF + PostgreSQL |
| Fase 5 — Docker | 14 | 🔴 Pendiente | Imagen final datacenter |

## God Nodes (más conectados)
- **auditor_avanzado** — nodo central. Recibe el audio de Fase 1 y es documentado por README y doc técnica.

## Surprising Connections
- `fase1_nodo_voxlingua` → `auditor_avanzado_evaluar_llamada_local` (feeds_into, INFERRED): La Fase 1 y el núcleo auditor son **las dos mitades del mismo pipeline** — el audio_vad.wav de Fase 1 es la entrada exacta que necesita evaluar_llamada_local().

## Import Cycles
- None detected.

## Communities (5 total)

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
- `Nodo 1: ffmpeg` — normaliza a WAV 16kHz mono
- `Nodo 2: noisereduce` — reducción de ruido (→ DeepFilterNet 3 en Docker)
- `Nodo 3: Silero VAD v5` — eliminó 20.1% de silencios (1231s → 983s)
- `Nodo 4: VoxLingua107` — detectó ES con 74.3% confianza, sin flags

### Community 4 — Documentación (cohesión: 1.0)
- `docs/documentacion_tecnica.docx` — v1.1, Fase 1 registrada
- `README.md` — repo GitHub: prohylurte/auditoria-digi (privado)

## Próximas conexiones esperadas (Fase 2)
- `notebooks/fase2_transcripcion.ipynb` → Community 5
- `fase2_whisper` → recibe `audio_vad.wav` de `fase1_nodo_voxlingua`
- `fase2_pyannote` → requiere token HuggingFace
