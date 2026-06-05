# Graph Report - /Users/hylurte/Auditoria  (2026-06-05)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 12 nodes · 10 edges · 5 communities
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
- **auditor_avanzado** — conectado a documentación (README, docx) y recibe el audio procesado de Fase 1. Nodo central del proyecto.

## Surprising Connections (you probably didn't know these)
- `fase1_nodo_voxlingua` → `auditor_avanzado_evaluar_llamada_local` (feeds_into, INFERRED): El último nodo del notebook de Fase 1 entrega directamente el audio listo a la función principal del auditor. La Fase 1 y el núcleo de auditoría son **dos mitades del mismo pipeline**.

## Import Cycles
- None detected.

## Communities (5 total)

### Community 0 — Motor de Auditoría (cohesión: 0.67)
- `auditor_avanzado.py` — prototipo funcional, punto de referencia
- `evaluar_llamada_local()` — procesa un archivo de audio completo
- `auditar_directorio_masivo()` — orquesta el procesado en paralelo

### Community 1 — Punto de Entrada (cohesión: 1.0) ⚠️ vacío
- `principal.py` — pendiente de implementar

### Community 2 — Transcriptor (cohesión: 1.0) ⚠️ vacío
- `transcriptor.py` — pendiente de implementar

### Community 3 — Pipeline Audio - Fase 1 (cohesión: 0.80)
- `notebooks/fase1_audio.ipynb` — notebook Colab con los 4 nodos de audio
- `Nodo 1: ffmpeg` — decodifica y normaliza el audio a WAV 16kHz mono
- `Nodo 2: DeepFilterNet 3` — elimina ruido de fondo (telefonía 8kHz)
- `Nodo 3: Silero VAD v5` — recorta silencios, reduce alucinaciones ASR
- `Nodo 4: VoxLingua107` — detecta idioma, genera flag si no coincide

### Community 4 — Documentación (cohesión: 1.0)
- `docs/documentacion_tecnica.docx` — documento técnico vivo v1.0
- `README.md` — entrada del repositorio GitHub

## Suggested Questions
- ¿Cómo se conecta la salida de `resultado_fase1.json` del notebook con la entrada de `evaluar_llamada_local()`?
- ¿Cuándo se implementarán `principal.py` y `transcriptor.py` para unificar el pipeline?
- ¿La Fase 2 (transcripción) irá en un notebook separado o se fusionará con Fase 1?
