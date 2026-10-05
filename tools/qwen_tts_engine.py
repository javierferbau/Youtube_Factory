#!/usr/bin/env python3
"""
qwen_tts_engine.py
Motor de generación de audio TTS usando Qwen3-TTS (QwenLM) en modo ICL VOICE CLONE.
Clona la voz del archivo de referencia /home/javierferb/n8n/assets/voice_reference.wav
utilizando In-Context Learning (ref_audio + ref_text) y parámetros de baja temperatura (0.2)
para anclar 100% la voz masculina y evitar saltos a voz femenina o voces diferentes.
Soporta vaciado previo de Ollama (keep_alive: 0), aceleración GPU (ROCm) y liberación post-síntesis.
"""

import os
import sys

os.environ["HSA_OVERRIDE_GFX_VERSION"] = "10.3.0"
os.environ["TORCH_BLAS_PREFER_HIPBLASLT"] = "0"
os.environ["MIOPEN_FIND_MODE"] = "FAST"

import gc
import re
import asyncio
import subprocess
import logging
import threading
import numpy as np
import soundfile as sf
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("qwen_tts")

# Modelo de clonación de voz Qwen3-TTS 1.7B Base
QWEN_MODEL_NAME = os.getenv("QWEN_TTS_MODEL", "Qwen/Qwen3-TTS-12Hz-1.7B-Base")
REF_AUDIO_PATH = os.getenv("QWEN_REF_AUDIO", "/home/javierferb/n8n/assets/voice_reference.wav")
REF_TEXT_PROMPT = os.getenv("QWEN_REF_TEXT", "Si buscas calidad de verdad, sin tirar el dinero, este es el modelo que merece la pena comprar. Lo he probado a fondo, y la diferencia en rendimiento se nota desde el primer día.")

_QWEN_MODEL = None
_CLONE_PROMPT = None
_MODEL_LOCK = threading.Lock()

def unload_ollama_vram():
    """Envía señal keep_alive: 0 a Ollama para liberar VRAM solo si el modelo está inactivo."""
    try:
        import time, gc, torch
        ps_res = requests.get("http://localhost:11434/api/ps", timeout=2)
        if ps_res.status_code == 200:
            models = ps_res.json().get("models", [])
            if not models:
                logger.info("Ollama ya está libre de VRAM.")
                return
            model_name = models[0].get("name", "qwen3.8:27b")
            payload = {"model": model_name, "keep_alive": 0}
            requests.post("http://localhost:11434/api/generate", json=payload, timeout=3)
            logger.info(f"Solicitud de liberación de VRAM enviada a Ollama para {model_name} (keep_alive: 0).")
            time.sleep(2.5)
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    except Exception as e:
        logger.debug(f"Ollama no disponible o sin respuesta: {e}")

def release_tts_memory():
    """Libera la VRAM y RAM ocupadas por el modelo Qwen3-TTS tras la síntesis."""
    global _QWEN_MODEL, _CLONE_PROMPT
    with _MODEL_LOCK:
        if _QWEN_MODEL is not None:
            del _QWEN_MODEL
            _QWEN_MODEL = None
            _CLONE_PROMPT = None
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass
            logger.info("Memoria VRAM de Qwen3-TTS liberada correctamente (keep_alive: 0).")

def get_qwen_model_and_prompt():
    global _QWEN_MODEL, _CLONE_PROMPT
    with _MODEL_LOCK:
        if _QWEN_MODEL is None:
            import time, gc, torch
            from qwen_tts import Qwen3TTSModel
            
            unload_ollama_vram()
            device = "cuda" if torch.cuda.is_available() else "cpu"
            dtype = torch.float16 if device == "cuda" else torch.float32
            logger.info(f"Cargando modelo Qwen3-TTS Base ({QWEN_MODEL_NAME}) en {device.upper()} con dtype={dtype}...")
            
            for attempt in range(2):
                try:
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    _QWEN_MODEL = Qwen3TTSModel.from_pretrained(QWEN_MODEL_NAME, device_map=device, dtype=dtype)
                    break
                except Exception as err:
                    if attempt == 0 and "out of memory" in str(err).lower():
                        logger.warning("OOM en intento 1 al cargar Qwen3-TTS. Forzando unload Ollama y reintentando...")
                        unload_ollama_vram()
                        time.sleep(3)
                        gc.collect()
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                    else:
                        raise err

            ref_path = REF_AUDIO_PATH if os.path.exists(REF_AUDIO_PATH) else "/tmp/test_gpu_qwen2.wav"
            logger.info(f"Extrayendo embedding ICL (ref_audio + ref_text) desde: {ref_path}")
            _CLONE_PROMPT = _QWEN_MODEL.create_voice_clone_prompt(
                ref_audio=ref_path,
                ref_text=REF_TEXT_PROMPT,
                x_vector_only_mode=False
            )
    return _QWEN_MODEL, _CLONE_PROMPT

async def synthesize_with_edge_fallback(text: str, output_wav: str, voice: str = "es-ES-AlvaroNeural", rate: str = "+0%"):
    """Fallback en caso de fallo."""
    import edge_tts
    temp_mp3 = output_wav.replace(".wav", "_temp_edge.mp3")
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(temp_mp3)

    subprocess.run(
        ["ffmpeg", "-y", "-i", temp_mp3,
         "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", output_wav],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
    )
    if os.path.exists(temp_mp3):
        os.remove(temp_mp3)

def split_text_into_sentences(text: str, max_chars: int = 220) -> list[str]:
    """Divide un texto largo en bloques de oraciones naturales de hasta max_chars caracteres."""
    raw_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s.strip()]
    if not raw_sentences:
        return [text.strip()]

    chunks = []
    current_chunk = ""

    for s in raw_sentences:
        if len(s) > max_chars:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            subparts = [sp.strip() for sp in re.split(r'(?<=[,;])\s+', s) if sp.strip()]
            for sp in subparts:
                if len(current_chunk) + len(sp) + 1 <= max_chars:
                    current_chunk = f"{current_chunk} {sp}".strip() if current_chunk else sp
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = sp
        else:
            if len(current_chunk) + len(s) + 1 <= max_chars:
                current_chunk = f"{current_chunk} {s}".strip() if current_chunk else s
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = s

    if current_chunk:
        chunks.append(current_chunk)

    return chunks if chunks else [text.strip()]

def synthesize_audio_qwen(text: str, output_wav: str, voice: str = "es-ES-AlvaroNeural", instruct: str = "", language: str = "spanish", auto_release: bool = False):
    """
    Sintetiza audio clonando la voz masculina en modo ICL con baja temperatura para anclaje 100% estable.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_wav)), exist_ok=True)
    qwen_success = False

    try:
        import torch
        model, clone_prompt = get_qwen_model_and_prompt()
        sentences = split_text_into_sentences(text)
        logger.info(f"Sintetizando {len(sentences)} oraciones con CLONACIÓN ICL ESTABLE (Base 1.7B, temp=0.65)...")

        audio_parts = []
        sample_rate = 24000

        with _MODEL_LOCK, torch.inference_mode():
            for idx, sentence in enumerate(sentences):
                logger.info(f"Clonando frase {idx+1}/{len(sentences)}: '{sentence[:40]}...'")
                wavs, sr = model.generate_voice_clone(
                    text=sentence,
                    voice_clone_prompt=clone_prompt,
                    language=language,
                    temperature=0.65,
                    top_k=40,
                    repetition_penalty=1.05
                )
                sample_rate = sr
                audio_parts.append(wavs[0])
                if idx < len(sentences) - 1:
                    silence = np.zeros(int(sr * 0.12), dtype=np.float32)
                    audio_parts.append(silence)

            combined_wav = np.concatenate(audio_parts, axis=0)
            temp_wav = output_wav.replace(".wav", "_raw.wav")
            sf.write(temp_wav, combined_wav, sample_rate)

        subprocess.run(
            ["ffmpeg", "-y", "-i", temp_wav, "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", output_wav],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
        )
        if os.path.exists(temp_wav):
            os.remove(temp_wav)
        qwen_success = True
        logger.info(f"Audio clonado ICL con éxito en: {output_wav}")
    except Exception as e:
        logger.error(f"Error sintetizando con clonación ICL Qwen3-TTS Base: {e}. Activando fallback.")
        qwen_success = False

    if not qwen_success:
        asyncio.run(synthesize_with_edge_fallback(text, output_wav, voice=voice))

    if auto_release:
        release_tts_memory()

if __name__ == "__main__":
    if len(sys.argv) > 2:
        txt = sys.argv[1]
        out = sys.argv[2]
        vc = sys.argv[3] if len(sys.argv) > 3 else "es-ES-AlvaroNeural"
        synthesize_audio_qwen(txt, out, voice=vc, auto_release=True)
        print(f"Proceso finalizado para: {out}")
    else:
        print("Uso: python3 qwen_tts_engine.py \"Texto a sintetizar\" /ruta/salida.wav [voz]")
