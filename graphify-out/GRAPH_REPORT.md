# Graph Report - /Users/hylurte/Auditoria  (2026-06-06 — v12: Fase 5 Docker + pipeline.py CLI)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 25 nodes · 31 edges · 9 communities
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Estado del Pipeline

| Fase | Nodos | Estado | Resultado |
|------|-------|--------|-----------|
| Fase 1 — Audio | 1-4 | ✅ COMPLETADA | 20min, 20.1% silencios, ES 74.3% |
| Fase 2 — Transcripción | 5, 8, 9 | ✅ COMPLETADA | 2 interlocutores · 3 intervenciones · guion_diarizado.txt |
| Fase 3 — Análisis IA | 10-11 | ✅ COMPLETADA | Qwen3-8B Q4 · 30 criterios · 3.57/10 llamada prueba |
| Fase 4 — Salida | 12-13 | ✅ COMPLETADA v2 | PDF formato real DIGI (3 págs) · psycopg2 PostgreSQL |
| Fase 5 — Docker | 14-16 | ✅ COMPLETADA | Dockerfile CUDA + pipeline.py CLI + auto-detección VRAM |

## Communities (9 total)

### Community 3 — Pipeline Audio Fase 1 ✅
### Community 5 — Pipeline Transcripción Fase 2 ✅
### Community 6 — Pipeline Análisis IA Fase 3 ✅
### Community 7 — Pipeline Salida Fase 4 ✅ COMPLETADA v2 — Formato real DIGI
- `notebooks/fase4_salida.ipynb` (v2_final_formato_real_digi)
- `Nodo 12: ReportLab PDF` — formato exacto de informes reales DIGI Spain Telecom:
  - Página 1: Resumen de Rendimiento (asesor, nota grande, tabla detalle, estadísticas Si/No/N/A/Críticos KO)
  - Página 2: Ficha (ID grabación, fecha, tipificación, nota) + Tabla Estructura de la llamada (4 cols)
  - Página 3: Tabla Actitud/Comunicación + Feedback Adicional (Observaciones + Puntos Fuertes + Áreas de Mejora)
  - Filas "No" con fondo rojo #FDECEA · Puntuación en formato español (0,10)
  - Header/footer: barra azul #003087 + franja naranja #FF6600
- `Nodo 13: psycopg2 PostgreSQL` — INSERT ON CONFLICT idempotente

### Community 8 — Fase 5 Docker ✅ COMPLETADA
- `Dockerfile` — imagen base nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04
  - ffmpeg, Python 3.10, PyTorch 2.2.2 (cu121)
  - Todas las dependencias: faster-whisper, pyannote 3.1, bitsandbytes, transformers, reportlab, psycopg2
  - HF_TOKEN solo via variable de entorno (nunca en imagen)
  - HEALTHCHECK: torch.cuda.is_available()
- `pipeline.py` — orquestador CLI Fases 1→2→3→4:
  - Uso: `python pipeline.py audio/llamada.ogg --asesor "Maria Garcia"`
  - Auto-detección VRAM: <8GB→Qwen3-8B, 8-20GB→Qwen3-14B, >20GB→Qwen3-72B
  - `--info-gpu` para ver GPU/VRAM/modelo elegido
  - `--modelo qwen3-8b/14b/72b` para forzar modelo
  - Log estructurado con tiempos por fase
- `docker-compose.yml` — GPU passthrough (nvidia-container-toolkit), volúmenes audio/output/models
- `requirements.txt` — dependencias versionadas, PyTorch instalado por separado (cu121)
- `.dockerignore` — excluye audio, modelos, .git y secretos
