# Graph Report - /Users/hylurte/Auditoria  (2026-06-06 — v10: Fase 4 COMPLETADA)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 23 nodes · 22 edges · 8 communities
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Estado del Pipeline

| Fase | Nodos | Estado | Resultado |
|------|-------|--------|-----------|
| Fase 1 — Audio | 1-4 | ✅ COMPLETADA | 20min, 20.1% silencios, ES 74.3% |
| Fase 2 — Transcripción | 5, 8, 9 | ✅ COMPLETADA | 2 interlocutores · 3 intervenciones · guion_diarizado.txt |
| Fase 3 — Análisis IA | 10-11 | ✅ COMPLETADA | Qwen3-8B Q4 · 30 criterios · 3.57/10 llamada prueba |
| Fase 4 — Salida | 12-13 | ✅ COMPLETADA | ReportLab PDF (portada+criterios+resumen) · psycopg2 PostgreSQL |
| Fase 5 — Docker | 14 | 🔴 Pendiente | — |

## Communities (8 total)

### Community 3 — Pipeline Audio Fase 1 ✅
### Community 5 — Pipeline Transcripción Fase 2 ✅
### Community 6 — Pipeline Análisis IA Fase 3 ✅
### Community 7 — Pipeline Salida Fase 4 ✅ COMPLETADA
- `notebooks/fase4_salida.ipynb`
- `Nodo 12: ReportLab PDF` — DIGICanvas (header/footer), portada, tablas criterios, gráficas donut+barras+gauge
- `Nodo 13: psycopg2 PostgreSQL` — INSERT ON CONFLICT, tabla `auditorias`, campo JSONB completo

## Arquitectura PDF (Nodo 12)
- Canvas personalizado: cabecera azul #003087 + línea naranja #FF6600 + pie gris con paginación
- Portada: gauge matplotlib + ficha llamada + notas por sección
- Páginas criterios: tabla 5 columnas (ID·Pregunta·Resp·Punt·Comentario) con alternado azul/blanco
- Resumen final: donut + barras · observaciones · puntos fuertes/áreas mejora en verde/rojo

## Próximas conexiones (Fase 5)
- `Dockerfile` → imagen con GPU NVIDIA + todos los modelos
- `docker-compose.yml` → orchestración con PostgreSQL + Redis
- Auto-detección GPU/VRAM → selección automática Colab-lite vs full
