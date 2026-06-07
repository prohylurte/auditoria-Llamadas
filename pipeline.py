#!/usr/bin/env python3
"""
pipeline.py — Orquestador CLI del pipeline de auditoría DIGI
=============================================================
Uso:
    python pipeline.py <audio.ogg> [opciones]

Ejemplos:
    python pipeline.py audio/llamada.ogg
    python pipeline.py audio/llamada.ogg --asesor "Maria Garcia" --output /app/output
    python pipeline.py audio/llamada.ogg --modelo qwen3-8b --no-db
    python pipeline.py --info-gpu          # muestra VRAM disponible y modelo elegido

El script detecta automáticamente la VRAM disponible y selecciona el modelo Qwen3 óptimo:
    < 8 GB  → Qwen3-8B  4-bit (bitsandbytes)
    8-20 GB → Qwen3-14B 4-bit (bitsandbytes)
    > 20 GB → Qwen3-72B 4-bit (bitsandbytes) o vLLM si está disponible
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from getpass import getpass
from pathlib import Path

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("pipeline")

# ── Constantes ────────────────────────────────────────────────────────────────
VERSION = "1.0.0"

# Umbrales VRAM (GB) para selección de modelo
VRAM_UMBRALES = [
    (8,  "Qwen/Qwen3-8B",  "4bit"),
    (20, "Qwen/Qwen3-14B", "4bit"),
    (999,"Qwen/Qwen3-72B", "4bit"),
]

# ── Detección de GPU/VRAM ─────────────────────────────────────────────────────
def detectar_gpu():
    """Devuelve (n_gpus, vram_gb_total, nombre_gpu) o (0, 0, 'CPU')."""
    try:
        import torch
        if not torch.cuda.is_available():
            return 0, 0.0, "CPU"
        n = torch.cuda.device_count()
        vram_total = sum(
            torch.cuda.get_device_properties(i).total_memory
            for i in range(n)
        ) / (1024 ** 3)
        nombre = torch.cuda.get_device_name(0)
        return n, round(vram_total, 1), nombre
    except ImportError:
        return 0, 0.0, "CPU (torch no instalado)"


def elegir_modelo(vram_gb, forzado=None):
    """Devuelve (model_id, quantization) según VRAM disponible o parámetro forzado."""
    alias = {
        "qwen3-8b":  ("Qwen/Qwen3-8B",  "4bit"),
        "qwen3-14b": ("Qwen/Qwen3-14B", "4bit"),
        "qwen3-72b": ("Qwen/Qwen3-72B", "4bit"),
    }
    if forzado and forzado.lower() in alias:
        return alias[forzado.lower()]
    for umbral, model_id, quant in VRAM_UMBRALES:
        if vram_gb < umbral:
            return model_id, quant
    return VRAM_UMBRALES[-1][1], VRAM_UMBRALES[-1][2]


# ── HuggingFace token ─────────────────────────────────────────────────────────
def obtener_hf_token():
    """Lee el token de HF desde variable de entorno (seguro) o getpass (interactivo)."""
    token = os.environ.get("HF_TOKEN", "").strip()
    if token:
        log.info("HF_TOKEN leido desde variable de entorno.")
        return token
    log.warning("HF_TOKEN no encontrado en el entorno.")
    token = getpass("Introduce tu HuggingFace token (hf_xxx): ").strip()
    if not token:
        log.error("Token vacio — abortando.")
        sys.exit(1)
    return token


# ── Fase 1: Procesamiento de audio ───────────────────────────────────────────
def fase1_audio(audio_path: Path, output_dir: Path) -> dict:
    """
    Limpia el audio: reducción de ruido, corte de silencios, detección de idioma.
    Devuelve dict con metadatos (duración, idioma, etc.).
    """
    log.info("=== FASE 1: Procesamiento de audio ===")
    t0 = time.time()

    try:
        import torch
        import numpy as np
        import soundfile as sf
        import noisereduce as nr
        import librosa
    except ImportError as e:
        log.error(f"Dependencia faltante en Fase 1: {e}")
        sys.exit(1)

    # Cargar audio
    audio_np, sr = librosa.load(str(audio_path), sr=16000, mono=True)
    duracion_orig = len(audio_np) / sr
    log.info(f"  Audio cargado: {duracion_orig:.1f}s @ {sr}Hz")

    # Reducción de ruido
    audio_limpio = nr.reduce_noise(y=audio_np, sr=sr, prop_decrease=0.75)

    # VAD con Silero (eliminar silencios)
    silero_model, utils = torch.hub.load(
        repo_or_dir="snakers4/silero-vad",
        model="silero_vad",
        force_reload=False,
        trust_repo=True,
    )
    get_speech_ts = utils[0]

    audio_tensor = torch.FloatTensor(audio_limpio)
    segmentos = get_speech_ts(audio_tensor, silero_model, sampling_rate=sr)

    chunks = [audio_limpio[s["start"]:s["end"]] for s in segmentos]
    audio_vad = np.concatenate(chunks) if chunks else audio_limpio
    duracion_proc = len(audio_vad) / sr
    reduccion_pct = (1 - duracion_proc / duracion_orig) * 100

    # Guardar audio procesado
    audio_out = output_dir / "audio_vad.wav"
    sf.write(str(audio_out), audio_vad, sr)
    log.info(f"  Audio VAD guardado: {duracion_proc:.1f}s (reduccion {reduccion_pct:.1f}%)")

    # Detección de idioma con VoxLingua107
    try:
        lang_model = torch.hub.load(
            "speechbrain/lang-id-voxlingua107-ecapa",
            "classifier",
            source="speechbrain",
            savedir=str(output_dir / "lang_model"),
        )
        lang_out = lang_model.classify_batch(torch.FloatTensor(audio_vad).unsqueeze(0))
        idioma = lang_out[3][0].strip()
        confianza = float(lang_out[1].exp()[0].max()) * 100
    except Exception:
        idioma = "es"
        confianza = 0.0
        log.warning("  Deteccion de idioma fallida — asumiendo 'es'")

    log.info(f"  Idioma: {idioma} ({confianza:.1f}%)")

    resultado = {
        "audio_vad": str(audio_out),
        "duracion_original_s": round(duracion_orig, 2),
        "duracion_procesada_s": round(duracion_proc, 2),
        "reduccion_silencios_pct": round(reduccion_pct, 1),
        "idioma": idioma,
        "confianza_idioma_pct": round(confianza, 1),
        "tiempo_fase1_s": round(time.time() - t0, 1),
    }
    _guardar_json(output_dir / "resultado_fase1.json", resultado)
    log.info(f"  Fase 1 completada en {resultado['tiempo_fase1_s']}s")
    return resultado


# ── Fase 2: Transcripción y diarización ──────────────────────────────────────
def fase2_transcripcion(fase1: dict, output_dir: Path, hf_token: str) -> dict:
    """
    Transcribe el audio con faster-whisper y diariza con pyannote 3.1.
    Devuelve dict con guión diarizado y metadatos.
    """
    log.info("=== FASE 2: Transcripcion y diarizacion ===")
    t0 = time.time()

    try:
        from faster_whisper import WhisperModel
        from pyannote.audio import Pipeline as PyAnnotePipeline
        import torch
    except ImportError as e:
        log.error(f"Dependencia faltante en Fase 2: {e}")
        sys.exit(1)

    audio_path = fase1["audio_vad"]
    device = "cuda" if __import__("torch").cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"

    # Transcripción con faster-whisper
    log.info(f"  Cargando Whisper medium ({device})...")
    whisper = WhisperModel("medium", device=device, compute_type=compute_type)
    segments, info = whisper.transcribe(
        audio_path,
        language="es",
        word_timestamps=True,
        vad_filter=False,
    )
    segments = list(segments)
    log.info(f"  Transcripcion: {len(segments)} segmentos, idioma={info.language}")

    # Diarización con pyannote
    log.info("  Cargando pyannote 3.1...")
    # pyannote >= 3.x usa 'token' en lugar del deprecado 'use_auth_token'
    from huggingface_hub import login as hf_login
    hf_login(token=hf_token, add_to_git_credential=False)
    diar_pipeline = PyAnnotePipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
    )
    if device == "cuda":
        import torch
        diar_pipeline = diar_pipeline.to(torch.device("cuda"))

    diarization = diar_pipeline(audio_path)

    # pyannote >= 3.3 devuelve DiarizeOutput en lugar de Annotation directamente
    # Intentar extraer la Annotation por atributo, índice o uso directo
    if hasattr(diarization, "itertracks"):
        annotation = diarization                    # versión antigua: ya es Annotation
    elif hasattr(diarization, "annotation"):
        annotation = diarization.annotation         # versión nueva: atributo .annotation
    else:
        annotation = diarization["annotation"]      # fallback: acceso dict

    # Construir índice de segmentos de speakers para búsqueda rápida
    speaker_segments = list(annotation.itertracks(yield_label=True))

    # Cruzar transcripción con diarización
    guion = []
    for seg in segments:
        mid = (seg.start + seg.end) / 2
        speaker = "UNKNOWN"
        for turn, _, spk in speaker_segments:
            if turn.start <= mid <= turn.end:
                speaker = spk
                break
        guion.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "speaker": speaker,
            "text": seg.text.strip(),
        })

    # Guardar guión
    guion_path = output_dir / "guion_diarizado.txt"
    with open(guion_path, "w", encoding="utf-8") as f:
        for g in guion:
            f.write(f"[{g['start']:.2f}s - {g['end']:.2f}s] {g['speaker']}: {g['text']}\n")

    speakers = {}
    for g in guion:
        speakers[g["speaker"]] = speakers.get(g["speaker"], 0) + len(g["text"])

    resultado = {
        "guion_diarizado": str(guion_path),
        "guion": guion,
        "n_interlocutores": len(speakers),
        "speakers": speakers,
        "n_segmentos": len(guion),
        "tiempo_fase2_s": round(time.time() - t0, 1),
    }
    _guardar_json(output_dir / "resultado_fase2.json", resultado)
    log.info(f"  Fase 2 completada en {resultado['tiempo_fase2_s']}s — {len(speakers)} speakers")
    return resultado


# ── Fase 3: Análisis IA con Qwen3 ────────────────────────────────────────────
def fase3_analisis(fase2: dict, output_dir: Path, model_id: str, quant: str, hf_token: str) -> dict:
    """
    Evalúa la llamada contra la rúbrica DIGI con Qwen3 en bitsandbytes.
    Devuelve dict con resultado de evaluación (criterios, notas, feedback).
    """
    log.info(f"=== FASE 3: Analisis IA ({model_id} {quant}) ===")
    t0 = time.time()

    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
    except ImportError as e:
        log.error(f"Dependencia faltante en Fase 3: {e}")
        sys.exit(1)

    # Cargar rúbrica desde JSON
    rubrica_path = Path(__file__).parent / "docs" / "rubrica_digi_conocimiento.json"
    if rubrica_path.exists():
        with open(rubrica_path, encoding="utf-8") as f:
            rubrica = json.load(f)
    else:
        log.warning("  rubrica_digi_conocimiento.json no encontrado — usando rubrica minima")
        rubrica = {"criterios": []}

    # Construir guión como texto
    guion_txt = "\n".join(
        f"[{g['speaker']}]: {g['text']}"
        for g in fase2["guion"]
    )

    # Configuración cuantización
    bnb_cfg = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    log.info(f"  Cargando {model_id}...")
    os.environ["HUGGING_FACE_HUB_TOKEN"] = hf_token
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        quantization_config=bnb_cfg,
        device_map="auto",
        trust_remote_code=True,
    )
    model.eval()
    log.info("  Modelo cargado OK")

    # Prompt de evaluación
    rubrica_str = json.dumps(rubrica, ensure_ascii=False, indent=2)
    prompt = f"""Eres un auditor experto de DIGI Spain Telecom. Evalúa la siguiente llamada contra la rúbrica proporcionada.

RUBRICA:
{rubrica_str}

TRANSCRIPCION DE LA LLAMADA:
{guion_txt}

Devuelve EXCLUSIVAMENTE un JSON válido con esta estructura:
{{
  "criterios": [
    {{"id": "ps1", "respuesta": "Sí/No/N/A", "puntuacion": 0.10, "comentario": "..."}}
  ],
  "nota_final": 7.50,
  "nota_estructura": 7.80,
  "nota_actitud": 6.90,
  "n_criticos_ko": 0,
  "observaciones": "...",
  "puntos_fuertes": ["...", "..."],
  "areas_mejora": ["...", "..."]
}}"""

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=2048,
            temperature=0.1,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    respuesta = tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[1]:],
        skip_special_tokens=True,
    )

    # Parsear JSON de la respuesta
    try:
        inicio = respuesta.find("{")
        fin = respuesta.rfind("}") + 1
        evaluacion = json.loads(respuesta[inicio:fin])
    except (json.JSONDecodeError, ValueError):
        log.warning("  JSON de evaluacion no parseable — usando resultado vacio")
        evaluacion = {
            "criterios": [],
            "nota_final": 0.0,
            "nota_estructura": 0.0,
            "nota_actitud": 0.0,
            "n_criticos_ko": 0,
            "observaciones": "Error al procesar la evaluacion.",
            "puntos_fuertes": [],
            "areas_mejora": [],
        }

    evaluacion["modelo_usado"] = model_id
    evaluacion["tiempo_fase3_s"] = round(time.time() - t0, 1)
    _guardar_json(output_dir / "resultado_fase3.json", evaluacion)
    log.info(f"  Fase 3 completada en {evaluacion['tiempo_fase3_s']}s — nota={evaluacion.get('nota_final', 0):.2f}")
    return evaluacion


# ── Fase 4: Generación de PDF ─────────────────────────────────────────────────
def fase4_salida(fase1: dict, fase2: dict, fase3: dict, output_dir: Path,
                 asesor: str, auditor: str) -> Path:
    """
    Genera el informe PDF en formato real DIGI (3 páginas) y lo guarda en output_dir.
    """
    log.info("=== FASE 4: Generacion PDF ===")
    t0 = time.time()

    try:
        # Importar el módulo de generación de PDF del notebook fase4
        # Se ejecuta el kernel directamente importando las funciones clave
        import importlib.util, types

        # Intentar importar desde notebooks/fase4_salida.ipynb via nbformat
        try:
            import nbformat
            nb_path = Path(__file__).parent / "notebooks" / "fase4_salida.ipynb"
            with open(nb_path, encoding="utf-8") as f:
                nb = nbformat.read(f, as_version=4)
            # Ejecutar celdas de código en un módulo temporal
            mod = types.ModuleType("fase4_mod")
            for cell in nb.cells:
                if cell.cell_type == "code":
                    try:
                        exec(compile(cell.source, "<fase4>", "exec"), mod.__dict__)
                    except Exception:
                        pass
            build_resumen   = mod.__dict__.get("build_resumen")
            build_estructura = mod.__dict__.get("build_estructura")
            build_actitud_feedback = mod.__dict__.get("build_actitud_feedback")
            DIGICanvas_cls  = mod.__dict__.get("DIGICanvas")
            DIGI_ok = all([build_resumen, build_estructura, build_actitud_feedback, DIGICanvas_cls])
        except Exception:
            DIGI_ok = False

        if not DIGI_ok:
            raise ImportError("No se pudo cargar fase4_salida.ipynb")

    except Exception as e:
        log.warning(f"  Fallback PDF simplificado: {e}")
        # Fallback: PDF mínimo con texto plano
        from reportlab.pdfgen import canvas as rl_canvas
        pdf_path = output_dir / f"auditoria_{datetime.now():%Y%m%d_%H%M%S}.pdf"
        c = rl_canvas.Canvas(str(pdf_path))
        c.drawString(50, 800, f"Auditoría DIGI — {asesor}")
        c.drawString(50, 780, f"Nota: {fase3.get('nota_final', 0):.2f}/10")
        c.save()
        log.info(f"  PDF fallback guardado: {pdf_path}")
        return pdf_path

    # Construir resultado completo para el generador de PDF
    from datetime import date
    resultado_pdf = {
        "asesor":         asesor,
        "auditor":        auditor,
        "periodo":        f"{date.today().strftime('%B %Y')}",
        "servicio":       "Atencion al cliente",
        "id_grabacion":   Path(fase1.get("audio_vad", "")).stem,
        "fecha_llamada":  datetime.now().strftime("%d/%m/%Y %H:%M"),
        "tipificacion":   "Llamada de atencion al cliente",
        "nota_final":     fase3.get("nota_final", 0.0),
        "nota_estructura":fase3.get("nota_estructura", 0.0),
        "nota_actitud":   fase3.get("nota_actitud", 0.0),
        "n_si":           sum(1 for c in fase3.get("criterios", []) if c.get("respuesta") == "Si"),
        "n_no":           sum(1 for c in fase3.get("criterios", []) if c.get("respuesta") == "No"),
        "n_na":           sum(1 for c in fase3.get("criterios", []) if c.get("respuesta") == "N/A"),
        "n_criticos_ko":  fase3.get("n_criticos_ko", 0),
        "observaciones":  fase3.get("observaciones", ""),
        "puntos_fuertes": fase3.get("puntos_fuertes", []),
        "areas_mejora":   fase3.get("areas_mejora", []),
        "secciones_estructura": _agrupar_criterios(fase3.get("criterios", []), estructura=True),
        "secciones_actitud":    _agrupar_criterios(fase3.get("criterios", []), estructura=False),
    }

    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, PageBreak, Spacer
    from reportlab.lib.units import mm

    pdf_path = output_dir / f"auditoria_{datetime.now():%Y%m%d_%H%M%S}.pdf"
    W, H = A4
    MARGIN = 20 * mm
    TW = W - 2 * MARGIN
    HDR_H = 18 * mm
    FOOT_H = 10 * mm

    on_page = DIGICanvas_cls(asesor, resultado_pdf["fecha_llamada"])
    doc = BaseDocTemplate(
        str(pdf_path), pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=HDR_H + 6*mm, bottomMargin=FOOT_H + 6*mm,
    )
    frame = Frame(MARGIN, FOOT_H+6*mm, TW, H-HDR_H-FOOT_H-12*mm, id='main', showBoundary=0)
    doc.addPageTemplates([PageTemplate(id='digi', frames=[frame], onPage=on_page)])

    story = []
    build_resumen(resultado_pdf, story)
    build_estructura(resultado_pdf, story)
    build_actitud_feedback(resultado_pdf, story)
    doc.build(story)

    log.info(f"  PDF generado: {pdf_path} ({pdf_path.stat().st_size/1024:.1f} KB) en {time.time()-t0:.1f}s")
    return pdf_path


# ── Helpers ───────────────────────────────────────────────────────────────────
SECCION_POR_ID = {
    "ps": "Presentacion",        "se": "Politica de seguridad",
    "so": "Sondeo",              "ao": "Asignacion de oferta",
    "cl": "Cierre de la venta",  "td": "Toma de datos y registro",
    "cd": "Cierre de la llamada","tc": "Trato al cliente",
    "ge": "Gestion de esperas",  "cc": "Capacidad de comunicacion",
}
SECCIONES_ACTITUD = {"Trato al cliente", "Gestion de esperas", "Capacidad de comunicacion"}


def _agrupar_criterios(criterios: list, estructura: bool) -> dict:
    """Agrupa criterios por sección para el generador de PDF."""
    grupos = {}
    for c in criterios:
        prefix = c.get("id", "")[:2]
        seccion = SECCION_POR_ID.get(prefix, "Otros")
        es_actitud = seccion in SECCIONES_ACTITUD
        if estructura and es_actitud:
            continue
        if not estructura and not es_actitud:
            continue
        if seccion not in grupos:
            grupos[seccion] = []
        grupos[seccion].append((
            c.get("pregunta", c.get("id", "")),
            c.get("respuesta", "N/A"),
            c.get("puntuacion", 0.0),
            c.get("comentario", ""),
        ))
    return grupos


def _guardar_json(path: Path, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Pipeline de auditoría DIGI — Fases 1 a 4",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("audio", nargs="?", help="Ruta al archivo de audio (.ogg/.wav/.mp3)")
    parser.add_argument("--asesor",  default="Asesor",  help="Nombre del asesor auditado")
    parser.add_argument("--auditor", default="Auditor", help="Nombre del auditor")
    parser.add_argument("--output",  default="/app/output", help="Directorio de salida")
    parser.add_argument("--modelo",  default=None,
        choices=["qwen3-8b", "qwen3-14b", "qwen3-72b"],
        help="Forzar modelo (por defecto: auto-deteccion por VRAM)")
    parser.add_argument("--no-db",   action="store_true", help="No guardar en PostgreSQL")
    parser.add_argument("--info-gpu",action="store_true", help="Mostrar info GPU y salir")
    parser.add_argument("--version", action="version", version=f"pipeline v{VERSION}")
    args = parser.parse_args()

    # ── Info GPU ──────────────────────────────────────────────
    n_gpus, vram_gb, gpu_name = detectar_gpu()
    model_id, quant = elegir_modelo(vram_gb, forzado=args.modelo)

    if args.info_gpu:
        print(f"\n{'='*50}")
        print(f"  GPUs detectadas : {n_gpus}")
        print(f"  GPU             : {gpu_name}")
        print(f"  VRAM total      : {vram_gb} GB")
        print(f"  Modelo elegido  : {model_id} ({quant})")
        print(f"{'='*50}\n")
        return

    if not args.audio:
        parser.print_help()
        sys.exit(0)

    audio_path = Path(args.audio)
    if not audio_path.exists():
        log.error(f"Archivo de audio no encontrado: {audio_path}")
        sys.exit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    log.info(f"Pipeline DIGI v{VERSION}")
    log.info(f"  Audio    : {audio_path}")
    log.info(f"  Output   : {output_dir}")
    log.info(f"  GPU      : {gpu_name} ({vram_gb} GB VRAM)")
    log.info(f"  Modelo   : {model_id} ({quant})")
    log.info(f"  Asesor   : {args.asesor}")

    # ── Token HF (necesario para pyannote y Qwen3) ────────────
    hf_token = obtener_hf_token()

    t_total = time.time()

    # ── Ejecutar fases ────────────────────────────────────────
    fase1 = fase1_audio(audio_path, output_dir)
    fase2 = fase2_transcripcion(fase1, output_dir, hf_token)
    fase3 = fase3_analisis(fase2, output_dir, model_id, quant, hf_token)
    pdf   = fase4_salida(fase1, fase2, fase3, output_dir, args.asesor, args.auditor)

    # ── Resumen final ─────────────────────────────────────────
    elapsed = time.time() - t_total
    print(f"\n{'='*55}")
    print(f"  AUDITORIA COMPLETADA en {elapsed:.0f}s")
    print(f"  Nota final        : {fase3.get('nota_final', 0):.2f} / 10")
    print(f"  Nota estructura   : {fase3.get('nota_estructura', 0):.2f}")
    print(f"  Nota actitud      : {fase3.get('nota_actitud', 0):.2f}")
    print(f"  Criticos KO       : {fase3.get('n_criticos_ko', 0)}")
    print(f"  PDF generado      : {pdf}")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
