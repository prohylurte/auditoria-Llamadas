# ============================================================
# DIGI Auditoría Pipeline — Imagen Docker con CUDA
# ============================================================
# Base: CUDA 12.1 + cuDNN 8 + Ubuntu 22.04
# GPU mínima: 6 GB VRAM (Qwen3-8B 4-bit)
# GPU recomendada: 24+ GB VRAM (Qwen3-72B 4-bit vía vLLM)
# ============================================================

FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

# ── Metadatos ────────────────────────────────────────────────
LABEL maintainer="DIGI Spain Telecom"
LABEL description="Pipeline de auditoría de llamadas: Fase1 (audio) → Fase2 (transcripción) → Fase3 (análisis IA) → Fase4 (PDF + BD)"
LABEL version="1.0"

# ── Variables de entorno base ────────────────────────────────
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1

# Directorios del pipeline
ENV AUDIO_DIR=/app/audio
ENV OUTPUT_DIR=/app/output
ENV MODELS_DIR=/app/models

# HuggingFace — pasar en tiempo de ejecución, nunca en imagen
# docker run -e HF_TOKEN=hf_xxx ...
ENV HF_TOKEN=""
ENV HF_HOME=/app/models/huggingface

# ── Dependencias del sistema ──────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Audio
    ffmpeg \
    libsndfile1 \
    # Python
    python3.10 \
    python3.10-dev \
    python3-pip \
    # Utilidades
    git \
    curl \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Asegurar que python3 apunta a 3.10
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1 \
    && update-alternatives --install /usr/bin/python  python  /usr/bin/python3.10 1

# ── Directorio de trabajo ─────────────────────────────────────
WORKDIR /app

# ── requirements.txt (copiado primero para cache de capas) ────
COPY requirements.txt .

# ── Dependencias Python ───────────────────────────────────────
# 1. PyTorch con CUDA 12.1
RUN pip3 install --upgrade pip && \
    pip3 install torch==2.2.2 torchaudio==2.2.2 --index-url https://download.pytorch.org/whl/cu121

# 2. Resto de dependencias
RUN pip3 install -r requirements.txt

# ── Código fuente del pipeline ────────────────────────────────
COPY pipeline.py .
COPY auditor_avanzado.py .
COPY principal.py .
COPY transcriptor.py .
COPY notebooks/ ./notebooks/

# ── Crear directorios de trabajo ─────────────────────────────
RUN mkdir -p $AUDIO_DIR $OUTPUT_DIR $MODELS_DIR

# ── Healthcheck ───────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import torch; assert torch.cuda.is_available(), 'CUDA no disponible'" || exit 1

# ── Punto de entrada ──────────────────────────────────────────
# Uso: docker run ... auditoria-digi python pipeline.py audio/llamada.ogg
ENTRYPOINT ["python3", "pipeline.py"]
CMD ["--help"]
