# 🎙️ Auditoria DIGI — Sistema Automático de Control de Calidad

Pipeline 100% offline y on-premise para evaluar llamadas comerciales del servicio C2C de DIGI Spain Telecom.

## ¿Qué hace?

Transcribe, diariza y analiza cada llamada de audio de forma automática, generando un informe de auditoría con puntuación sobre 10 según la rúbrica interna de 31 puntos de DIGI.

## Arquitectura

```
ffmpeg → noisereduce/DeepFilterNet 3 → Silero VAD → VoxLingua107
  → Whisper Medium/Large V3 + [Qwen3-ASR → Reconciliador]
  → WhisperX → pyannote
  → vLLM [Qwen3-8B/235B + GLM-5] + BGE-M3/pgvector (RAG)
  → WeasyPrint (PDF) → PostgreSQL
  ← Temporal + Redis (orquestación)
```

## Estado del Proyecto

| Fase | Descripción | Estado | Resultado |
|------|-------------|--------|-----------|
| Fase 1 | Audio: ffmpeg, noisereduce, Silero VAD, VoxLingua107 | ✅ Completada | 20min llamada · 20.1% silencios eliminados · ES 74.3% |
| Fase 2 | Transcripción: faster-whisper, pyannote | ✅ Completada | 2 interlocutores · 3 intervenciones · guion_diarizado.txt |
| Fase 3 | Análisis IA: Qwen3-8B, RAG | ✅ Completada | 30 criterios · 3.57/10 prueba · resultado_fase3.json |
| Fase 4 | Salida: PDF, PostgreSQL | 🔴 Pendiente | — |
| Fase 5 | Docker / Datacenter | 🔴 Pendiente | — |

## Estrategia de Modelos

Se desarrolla con modelos ligeros (Colab) y se sustituyen por los definitivos en Docker sin tocar la arquitectura.

| Nodo | Colab (desarrollo) | Docker (producción) |
|------|--------------------|---------------------|
| Ruido | noisereduce | DeepFilterNet 3 |
| ASR primario | faster-whisper Medium | WhisperX + Large V3 |
| Alineación | stable-ts | WhisperX (word alignment) |
| ASR secundario | *(omitido en v1)* | Qwen3-ASR |
| LLM análisis | Qwen3-8B Q4 (Ollama) | Qwen3-235B (vLLM) |
| LLM verificador | *(omitido en v1)* | GLM-5 |
| Embeddings | BGE-M3 quantizado | BGE-M3 full |

## Estructura

```
auditoria-digi/
├── notebooks/
│   ├── fase1_audio.ipynb          ✅ Completado — Nodos 1-4
│   ├── fase2_transcripcion.ipynb  ✅ Completado — Nodos 5, 8, 9
│   ├── fase3_analisis_ia.ipynb    ✅ Completado — Nodos 10-11
│   └── fase4_salida.ipynb         🔴 Pendiente — Nodos 12-13
├── src/
│   ├── audio/
│   ├── transcripcion/
│   ├── analisis/
│   └── salida/
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
└── docs/
    └── documentacion_tecnica.docx  v1.1
```

## Entorno de Desarrollo

- **Desarrollo:** Google Colab (un notebook por fase, GPU T4)
- **Producción:** Imagen Docker en datacenter Linux + GPU NVIDIA

## Notas de Seguridad

- El token de HuggingFace se introduce en cada sesión via `getpass` — nunca se guarda en el código
- Todos los modelos y datos permanecen on-premise
- Datos de llamadas excluidos del repositorio vía `.gitignore`

---

*Proyecto confidencial — DIGI Spain Telecom S.A.U.*
