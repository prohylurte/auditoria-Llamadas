# 🎙️ Auditoria DIGI — Sistema Automático de Control de Calidad

Pipeline 100% offline y on-premise para evaluar llamadas comerciales del servicio C2C de DIGI Spain Telecom.

## ¿Qué hace?

Transcribe, diariza y analiza cada llamada de audio de forma automática, generando un informe de auditoría con puntuación sobre 10 según la rúbrica interna de 31 puntos de DIGI.

## Arquitectura

```
ffmpeg → DeepFilterNet 3 → Silero VAD → VoxLingua107
  → Whisper + Qwen3-ASR → Reconciliador
  → WhisperX → pyannote
  → vLLM [Qwen3-235B + GLM-5] + BGE-M3/pgvector (RAG)
  → WeasyPrint (PDF) → PostgreSQL
  ← Temporal + Redis (orquestación)
```

## Estado del Proyecto

| Fase | Descripción | Estado |
|------|-------------|--------|
| Fase 1 | Audio: ffmpeg, DeepFilterNet, VAD, LID | 🔴 En desarrollo |
| Fase 2 | Transcripción: Whisper, WhisperX, pyannote | 🟡 Parcial |
| Fase 3 | Análisis IA: vLLM, RAG | 🟡 Parcial |
| Fase 4 | Salida: PDF, PostgreSQL | 🔴 Pendiente |
| Fase 5 | Docker / Datacenter | 🔴 Pendiente |

## Estructura

```
auditoria-digi/
├── notebooks/
│   ├── fase1_audio.ipynb
│   ├── fase2_transcripcion.ipynb
│   ├── fase3_analisis_ia.ipynb
│   └── fase4_salida.ipynb
├── src/
│   ├── audio/
│   ├── transcripcion/
│   ├── analisis/
│   └── salida/
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
└── docs/
    └── documentacion_tecnica.docx
```

## Entorno de Desarrollo

- **Desarrollo:** Google Colab (un notebook por fase)
- **Producción:** Imagen Docker en datacenter Linux + GPU NVIDIA

## Estrategia de Modelos

Se desarrolla con modelos ligeros (v1) y se actualiza a los modelos finales sin cambiar la arquitectura.

| Nodo | v1 (desarrollo) | vFinal (datacenter) |
|------|-----------------|---------------------|
| ASR primario | Whisper Medium | Whisper Large V3 |
| LLM análisis | Qwen3-8B Q4 | Qwen3-235B (vLLM) |
| Embeddings | BGE-M3 quantizado | BGE-M3 full |

---

*Proyecto confidencial — DIGI Spain Telecom S.A.U.*
