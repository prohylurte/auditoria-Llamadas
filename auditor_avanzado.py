import os
import whisperx
import time
import gc 
import glob
import shutil
import random
from concurrent.futures import ProcessPoolExecutor, as_completed
from ollama import Client

# =========================================================================
# 🛡️ MODO SEGURIDAD ESTRICTA (100% OFFLINE / ON-PREMISE)
# =========================================================================
os.environ["HF_HUB_OFFLINE"] = "0"  #<--------------- Provicional para descargar las dependencias (1) 
os.environ["DISABLE_TELEMETRY"] = "1"

# IP del servidor Nginx (El Balanceador de Carga)
IP_BALANCEADOR_NGINX = "http://localhost:11434"

def evaluar_llamada_local(ruta_audio, directorio_base_salida):
    print(f"🛡️ Iniciando análisis de {os.path.basename(ruta_audio)}...")
    inicio_total = time.time()

    # 1. TRANSCRIPCIÓN BASE (Procesamiento en GPU)
    device = "cuda"
    batch_size = 8
    compute_type = "int8"

    print("🎙️ 1/4: Transcribiendo audio base (Modelo Local)...")
    modelo_stt = whisperx.load_model("base", device, compute_type=compute_type)
    audio = whisperx.load_audio(ruta_audio)
    resultado = modelo_stt.transcribe(audio, batch_size=batch_size)
    
    del modelo_stt
    gc.collect()

    # 2. ALINEACIÓN
    print("⏱️ 2/4: Alineando palabras (Modelo Local)...")
    modelo_align, metadata = whisperx.load_align_model(language_code=resultado["language"], device=device)
    resultado = whisperx.align(resultado["segments"], modelo_align, metadata, audio, device, return_char_alignments=False)
    
    del modelo_align
    gc.collect()

    # 3. DIARIZACIÓN
    print("👥 3/4: Separando interlocutores (Leyendo desde disco duro)...")
    token_falso_offline = "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" #<---------------- Borrar una vez descargada las dependencias
    diarize_model = whisperx.diarize.DiarizationPipeline(token=token_falso_offline, device=device)
    diarize_segments = diarize_model(audio)
    
    resultado_final = whisperx.assign_word_speakers(diarize_segments, resultado)

    transcripcion_formateada = ""
    for segmento in resultado_final["segments"]:
        speaker = segmento.get('speaker', 'Desconocido')
        texto = segmento['text'].strip()
        transcripcion_formateada += f"[{speaker}]: {texto}\n"

    print("✅ Análisis de audio completado.\n")

    # 4. EVALUACIÓN Y PERFILADO CON IA (Enrutando a Nginx)
    print("🤖 4/4: Pasando transcripción a Llama 3 (Vía Nginx)...")
    
    prompt = f"""
    
    SISTEMA: ACTÚA COMO EL AUDITOR MAESTRO DE CALIDAD DE DIGI SPAIN TELECOM S.A.U.
OBJETIVO PRINCIPAL:
Tu función es evaluar transcripciones de llamadas comerciales en texto plano (generadas por Whisper) correspondientes a agentes del servicio C2C de DIGI. Debes emitir un informe de auditoría detallado, riguroso y objetivo, calculando una nota final sobre 10. Evaluarás estrictamente en base a los criterios, pesos y normativas que se detallan a continuación. No inventes parámetros fuera de esta rúbrica.
BASE DE CONOCIMIENTO Y NORMATIVA CONTRACTUAL DIGI
El agente debe cumplir con informar correctamente al cliente sobre estos puntos si aplican a la venta. Si el agente da información contraria u omite detalles críticos, penaliza en "Información correcta y completa" y "Evita el maltrato/Información no veraz":
Políticas de Seguridad (Estricto): Este paso es EXCLUSIVO para clientes ya existentes que desean añadir servicios a su contrato actual. Solo en este caso, el agente está obligado a pasar las políticas de seguridad solicitando exactamente: DNI, Nombre completo, Teléfono de contacto y los 4 últimos dígitos del IBAN. Si es un cliente nuevo, este paso no aplica.
Políticas de Privacidad (Textual): Antes de enviar finalmente el pedido al cliente con lo que desea contratar, el agente debe leer de forma textual la siguiente cláusula: "Declaras y aceptas que los datos introducidos en este formulario son exactos y veraces y DIGI podrá activar el servicio contratado para su prestación dentro del periodo de desistimiento". Las preguntas sobre notificaciones comerciales se evalúan con mayor flexibilidad, ya que son opcionales para el cliente.
Permanencia (Fibra): Existe un compromiso de permanencia de 3 meses (90 días naturales) en Tarifas DIGI Net. Penalización por baja anticipada: 100€ prorrateados. Las líneas móviles NO tienen permanencia.
Equipos: Router y ONT se entregan en régimen de depósito. Si no se devuelven en 15 días tras la baja, penalización de 50€ (o 150€ para equipos XGS-PON de 10Gb).
Plazos (Información al cliente): Legalmente la instalación de fibra es en un máximo de 60 días, pero el agente debe informar al cliente los siguientes plazos reales: 2 a 15 días naturales para Fibra de territorio nacional y 2 a 7 días naturales para Fibra SMART. La portabilidad móvil es en 1 día hábil (48-72h habitualmente informadas al cliente).
Tarifas y Productos Estándar:
Móviles SIN Fibra:
ILIMITODO: 1 línea 10€ / 2 líneas 8€ cada una / 3 o más líneas 6€ cada una.
50 GB y llamadas ilimitadas: 7€.
25 GB y 100 min (llamadas nacionales e internacionales): 5€.
5 GB y 100 min (llamadas nacionales): 3€.
Móviles CON Fibra (DIGI Net):
ILIMITODO: 1 línea 8€ / 2 líneas 6€ cada una / 3 o más líneas 5€ cada una.
50 GB y llamadas ilimitadas: 5€.
25 GB y 100 min (llamadas nacionales e internacionales): 3€.
5 GB y 100 min (llamadas nacionales): 2€.
Fibra SMART: 500Mb (10€), 750Mb (15€), 1Gb (20€), PRO-DIGI 10Gb (25€).
Fibra Estándar: 300Mb (25€), 1Gb (30€).
Roaming: En la UE sujeto a política de uso razonable. Excluidas llamadas a tarificación especial.
RÚBRICA DE EVALUACIÓN Y DISTRIBUCIÓN DE PESOS
Evalúa cada uno de los siguientes ítems. Si un ítem no aplica a la casuística de la llamada, márcalo como N/A (No Aplica) y redistribuye su peso proporcionalmente entre los demás ítems para que la nota máxima posible siempre sea 10.
1. Estructura de la llamada (Peso total aprox: 6.5 puntos)
Presentación:
El asesor hace un uso correcto del saludo corporativo. (Peso: 0.15)
Política de seguridad:
Identificación Correcta/Completa en política de seguridad. (SOLO YA CLIENTES: DNI, Nombre, Teléfono, 4 últimos dígitos IBAN. Si es cliente nuevo = N/A). (Peso: 0.15)
Sondeo:
Realiza verificaciones previas a la contratación (comprobar paquetes/pedidos/cobertura). (Peso: 0.30)
Averigua la necesidad de su cliente mediante preguntas de sondeo (No usar perfil netamente consultivo, debe indagar). (Peso: 0.50)
Conoce los hábitos de consumo con preguntas de sondeo. (Peso: 0.50)
Ha sido capaz de conocer lo que paga el cliente en su actual operador. (Peso: 0.50)
Asignación de oferta:
Consulta de cobertura (Imprescindible en fijos/fibra). (Peso: 0.40)
El agente orienta a su cliente hacia venta valor y máximos productos (VENTA CRUZADA - vital ofrecer móvil si pide fibra, o TV si pide fibra). (Peso: 0.50)
Información correcta y completa (producto, precios exactos y permanencia según normativa). (Peso: 0.70)
Pone en valor las características estrella de DIGI (Precio final, cobertura Movistar, Acumular Mb). (Peso: 0.40)
Cuantifica el ahorro mensual/anual haciendo ver al cliente el beneficio. (Peso: 0.30)
Cierre de la venta:
El asesor orienta el cierre en primera llamada, evitando agendar innecesariamente. (Peso: 1.35)
Rebate objeciones de manera correcta. (Peso: 0.50)
Realiza un cierre directo (no dejar silencios tras la oferta). (Peso: 1.25)
Toma de datos y registro:
Reformula los datos críticos a fin de evitar rechazos (Móvil, titular, DNI, email, cuenta). (Peso: 0.40)
Codificación/Tipificación correcta (asumir correcto si el flujo indica que el asesor guía la firma y proceso final). (Peso: 0.20)
Cierre de la llamada:
Reformula los acuerdos alcanzados en la oferta comercial (Resumen del pedido antes de la firma). (Peso: 0.40)
Lectura de Políticas de Privacidad: Lee textualmente la cláusula obligatoria antes de enviar el pedido. (Peso: 0.30)
Informa de próximos pasos (plazos instalación correctos 2-15 o 2-7 días/portabilidad, recepción SMS/Email). (Peso: 0.30)
Despedida corporativa y dejar locución legal. (Peso: 0.15)
2. Actitud / Comunicación (Peso total aprox: 3.5 puntos)
Trato al cliente:
Personaliza la llamada (Usa el nombre del cliente). (Peso: 0.20)
Gestión y ayuda en el proceso de firma (Acompañamiento). (Peso: 0.30)
Actitud empática, cercana, amable y cortés. (Peso: 0.40)
Evita el maltrato - Información no veraz (Transparencia total). (Peso: 0.60)
Gestión de esperas:
Adecuada gestión de los tiempos de espera (silencios justificados). (Peso: 0.40)
Estructura correctamente la llamada evitando dilatarla. (Peso: 0.30)
Capacidad de comunicación:
Vocabulario correcto, adaptado, sin muletillas. (Peso: 0.40)
Transmite imagen positiva de la marca/productos DIGI. (Peso: 0.40)
Dirige la llamada evitando interrumpir. (Peso: 0.30)
Aplica el procedimiento correcto. (Peso: 0.20)
INSTRUCCIONES DE EJECUCIÓN (OUTPUT REQUERIDO)
Analiza el <TEXTO_TRANSCRIPCION> y genera la respuesta estrictamente con la siguiente estructura Markdown:
1. METADATOS DE LA LLAMADA
Tipificación inferida: (Venta Realizada Nuevo Cliente, Venta Realizada Ya Cliente, No Venta - Precio, Solo Info, etc.)
Nota Final Calculada: [0.00 / 10.00]
2. EVALUACIÓN DETALLADA POR ÍTEM (El "Por qué" argumentado)
Genera una tabla o lista desglosando CADA UNO de los 31 puntos de la rúbrica.
Formato por ítem: [Nombre del Ítem] | [Puntuación Asignada / Peso Máximo o N/A] | [Justificación y Argumentación]
Regla estricta 1: Debes argumentar el porqué de la nota dada en TODOS los ítems, citando hechos específicos de la transcripción (ej. "Nota máxima porque ofreció correctamente la tarifa de 25GB con fibra por 3€").
Regla estricta 2: Si otorgas una nota de 0 en cualquier punto de la auditoría, debes explicar explícitamente la razón del fallo y el impacto que esto tiene en la calidad de la llamada o el incumplimiento legal (ej. "Nota 0 porque el agente omitió leer textualmente las políticas de privacidad antes de enviar el pedido, lo cual es un requisito legal", o "Nota 0 porque informó 60 días para la instalación en lugar de especificar 2 a 7 días para Fibra Smart").
3. FEEDBACK PARA EL SUPERVISOR (GUÍA DE COACHING)
Dirígete al supervisor encargado de realizar la auditoría, entregando un análisis profundo, humano y detallado de la gestión del agente (no actúes como una simple plantilla). Este informe formará la base para el control de calidad interno.
Análisis de Ejecución (Cómo fue la llamada y cómo se ejecutó): Describe la dinámica real de la interacción. ¿Fue un agente pasivo, limitándose a tomar notas como un perfil puramente consultivo? ¿O tomó las riendas comerciales? Evalúa el ritmo, la seguridad, la gestión de las políticas (seguridad y privacidad) y el control de la conversación.
El "Deber Ser" (Cómo debió haber sido mejor): Explica de manera didáctica cómo el agente debió abordar las deficiencias detectadas. Por ejemplo: "Al tratarse de un cliente ya existente, debió solicitar rigurosamente los 4 datos de seguridad. Además, en lugar de preguntar '¿qué tarifa quieres?', debió realizar un sondeo sobre sus nuevos hábitos de consumo para ejecutar una Venta Cruzada efectiva".
Puntos Fuertes del Asesor: Lo que hizo excepcionalmente bien, destacando habilidades naturales o apego al proceso. (Si no hay, indica "Sin puntos fuertes destacables").
Áreas de Mejora Urgentes y Consejo de Liderazgo: Señala los comportamientos críticos que el supervisor debe trabajar de inmediato con el agente y sugiere un enfoque para el roleplay o el plan de acción (ej. trabajar la naturalidad al leer el texto legal de privacidad o entrenar el rebote de objeciones).
<TEXTO_TRANSCRIPCION>
{{TEXTO_WHISPER}}
</TEXTO_TRANSCRIPCION>

    """

    cliente_ollama = Client(host=IP_BALANCEADOR_NGINX)
    
    try:
        respuesta = cliente_ollama.chat(model='llama3', messages=[
            {
                'role': 'user',
                'content': prompt
            }
        ])
        evaluacion_final = respuesta['message']['content']
    except Exception as e:
        print(f"⚠️ Error de conexión con el clúster de Llama 3: {e}")
        raise RuntimeError("Fallo en la inferencia del LLM")
    
    # =========================================================================
    # ENRUTAMIENTO DE CARPETAS Y ESCRITURA
    # =========================================================================
    nombre_base = os.path.basename(ruta_audio).replace('.m4a', '').replace('.mp3', '').replace('.ogg', '')
    partes_nombre = nombre_base.split('_')
    nombre_agente = partes_nombre[0] if len(partes_nombre) > 0 else "Agentes_Sin_Asignar"
    
    ruta_carpeta_agente = os.path.join(directorio_base_salida, nombre_agente)
    os.makedirs(ruta_carpeta_agente, exist_ok=True)
    nombre_archivo_salida = os.path.join(ruta_carpeta_agente, f"Reporte_Seguro_{nombre_base}.md")
    
    with open(nombre_archivo_salida, "w", encoding="utf-8") as f:
        f.write(f"# 🔒 REPORTE DE AUDITORÍA (MODO PRIVADO ON-PREMISE)\n")
        f.write(f"**Archivo analizado:** `{ruta_audio}`\n")
        f.write(f"**Agente Asignado:** {nombre_agente}\n")
        f.write(f"**Fecha:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"---\n\n")
        f.write(f"## 1. Guion Diarizado\n")
        f.write(f"```text\n{transcripcion_formateada}\n```\n")
        f.write(f"---\n\n")
        f.write(f"## 2. Análisis y Evaluación Comercial\n\n")
        f.write(f"{evaluacion_final}\n")

    fin_total = time.time()
    print(f"✅ ¡ÉXITO! {nombre_base} procesado en {round(fin_total - inicio_total, 1)}s.")
    return True

# =========================================================================
# ORQUESTADOR DE COLA ATÓMICA (ZERO-INFRA)
# =========================================================================
def auditar_directorio_masivo(directorio_entrada, directorio_salida, max_workers=4):
    patron_busqueda = os.path.join(directorio_entrada, "*.ogg")
    archivos_audio = glob.glob(patron_busqueda)
    
    random.shuffle(archivos_audio)
    total_archivos = len(archivos_audio)
    
    if total_archivos == 0:
        print("📭 No hay llamadas nuevas en la bandeja de entrada.")
        return

    print(f"🚀 Iniciando orquestación de {total_archivos} llamadas disponibles...")
    
    carpeta_proceso = os.path.join(directorio_entrada, "en_proceso")
    carpeta_completados = os.path.join(directorio_entrada, "completados")
    
    os.makedirs(directorio_salida, exist_ok=True)
    os.makedirs(carpeta_proceso, exist_ok=True)
    os.makedirs(carpeta_completados, exist_ok=True)

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futuros = {}
        
        for audio_original in archivos_audio:
            nombre_archivo = os.path.basename(audio_original)
            ruta_proceso = os.path.join(carpeta_proceso, nombre_archivo)
            
            try:
                # Bloqueo atómico: Solo un servidor puede mover el archivo con éxito
                os.rename(audio_original, ruta_proceso)
                futuros[executor.submit(evaluar_llamada_local, ruta_proceso, directorio_salida)] = ruta_proceso
                
            except (FileNotFoundError, FileExistsError):
                continue

        for futuro in as_completed(futuros):
            archivo_procesado = futuros[futuro]
            try:
                futuro.result()
                shutil.move(archivo_procesado, os.path.join(carpeta_completados, os.path.basename(archivo_procesado)))
                
            except Exception as e:
                print(f"❌ Error crítico procesando {archivo_procesado}: {e}")
                # En caso de fallo (ej. GPU Out of Memory), el archivo vuelve a la cola general
                os.rename(archivo_procesado, os.path.join(directorio_entrada, os.path.basename(archivo_procesado)))

if __name__ == "__main__":
    CARPETA_LLAMADAS_ENTRANTES = "./llamadas_pendientes"
    CARPETA_REPORTES_AGENTES = "./reportes_agentes"
    
    # Ajustar según la VRAM disponible en la máquina física
    HILOS_SIMULTANEOS = 4 
    
    try:
        auditar_directorio_masivo(CARPETA_LLAMADAS_ENTRANTES, CARPETA_REPORTES_AGENTES, max_workers=HILOS_SIMULTANEOS)
    except Exception as e:
        print(f"❌ Ocurrió un error en el orquestador maestro: {e}")