#!/usr/bin/env python3
"""
kokoro_vs_tts.py
Genera locuciones (TTS) y subtítulos sincronizados (Whisper ASS) específicos para comparativas VS (A vs B).
Estructura de secciones:
- 00_intro (hook)
- 01_producto_a (product_a_overview + product_a_reviews)
- 02_producto_b (product_b_overview + product_b_reviews)
- 03_comparison (comparison)
- 08_outro (outro)
"""

import sys
import os

os.environ["HSA_OVERRIDE_GFX_VERSION"] = "10.3.0"

import json
import argparse
import asyncio
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

ASS_HEADER = """\
[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,52,&H00FFFFFF,&H000000FF,&H00000000,&HB4000000,1,0,0,0,100,100,0,0,1,4,1,2,80,80,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

_WHISPER_MODEL = None

def get_whisper_model():
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        from faster_whisper import WhisperModel
        _WHISPER_MODEL = WhisperModel("base", device="cpu", compute_type="int8", cpu_threads=4, num_workers=2)
    return _WHISPER_MODEL

def format_ass_time(seconds):
    hours   = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs    = seconds % 60
    return f"{hours}:{minutes:02d}:{secs:05.2f}"

def get_audio_duration(file_path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, check=True)
        return float(res.stdout.strip())
    except Exception:
        return 5.0

def build_ass_from_whisper(wav_path, ass_path, words_per_line=5, lang="es"):
    model = get_whisper_model()
    segments, _ = model.transcribe(
        wav_path,
        language=lang,
        word_timestamps=True,
        beam_size=1,
    )

    words = []
    for seg in segments:
        if seg.words:
            for w in seg.words:
                words.append({
                    "word":  w.word.strip(),
                    "start": w.start,
                    "end":   w.end,
                })

    if not words:
        with open(ass_path, 'w', encoding='utf-8') as f:
            f.write(ASS_HEADER)
        return

    lines = []
    i = 0
    while i < len(words):
        group = words[i:i + words_per_line]
        text  = " ".join(w["word"] for w in group)
        start = group[0]["start"]
        if i + words_per_line < len(words):
            end = words[i + words_per_line]["start"]
        else:
            end = group[-1]["end"]
        lines.append((start, end, text.strip()))
        i += words_per_line

    with open(ass_path, 'w', encoding='utf-8') as f:
        f.write(ASS_HEADER)
        for start, end, text in lines:
            clean = text.replace("\n", " ")
            f.write(
                f"Dialogue: 0,{format_ass_time(start)},{format_ass_time(end)},"
                f"Default,,0,0,0,,{clean}\n"
            )

from qwen_tts_engine import synthesize_audio_qwen, synthesize_with_edge_fallback

def synth_and_align(text, wav_path, ass_path, voice="es-ES-AlvaroNeural", words_per_line=5):
    # Isolated subprocess for Qwen3-TTS to protect against ROCm/GPU C-level SIGSEGV crashes
    venv_py = "/home/javierferb/n8n/venv/bin/python3"
    qwen_script = "/home/javierferb/n8n/tools/qwen_tts_engine.py"
    qwen_ok = False

    if os.path.exists(qwen_script) and os.path.exists(venv_py):
        try:
            cmd = [venv_py, qwen_script, text, wav_path, voice]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=180)
            if res.returncode == 0 and os.path.exists(wav_path) and os.path.getsize(wav_path) > 1000:
                qwen_ok = True
            else:
                err_msg = res.stderr.strip()[-300:] if res.stderr else f"Exit code: {res.returncode}"
                print(f"[WARN] Qwen3-TTS falló o abortó ({err_msg}). Activando fallback Edge-TTS...", file=sys.stderr)
        except Exception as e:
            print(f"[WARN] Excepción ejecutando Qwen3-TTS: {e}. Activando fallback Edge-TTS...", file=sys.stderr)

    if not qwen_ok:
        print(f"[INFO] Sintetizando audio con Edge-TTS para: {wav_path}", file=sys.stderr)
        asyncio.run(synthesize_with_edge_fallback(text, wav_path, voice=voice))

    build_ass_from_whisper(wav_path, ass_path, words_per_line=words_per_line)

def generate_vs_tts(script_json_path, voice_name="es-ES-AlvaroNeural"):
    with open(script_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    project_dir = data.get("project_dir", os.path.dirname(script_json_path))
    script = data.get("script", {})

    tasks = []

    product_a = data.get("product_a", {})
    product_b = data.get("product_b", {})
    brand_a = product_a.get("brand", "Marca A")
    brand_b = product_b.get("brand", "Marca B")
    query = data.get("query", "productos").replace("_", " ")

    # 1. Intro (00_intro)
    intro_dir = os.path.join(project_dir, "00_intro")
    os.makedirs(intro_dir, exist_ok=True)
    hook_text = script.get("hook", "").strip()
    if not hook_text:
        hook_text = f"¿Dudas entre {brand_a} o {brand_b} para {query}? Hoy analizamos a fondo ambas opciones con opiniones reales de compradores."
    tasks.append(("hook", hook_text, os.path.join(intro_dir, "audio.wav"), os.path.join(intro_dir, "subtitles.ass"), "00_intro/audio.wav", "00_intro/subtitles.ass"))

    # 2. Product A (01_producto_a)
    dir_a = os.path.join(project_dir, "01_producto_a")
    os.makedirs(dir_a, exist_ok=True)
    text_a = (script.get("product_a_overview", "") + " " + script.get("product_a_reviews", "")).strip()
    if not text_a:
        text_a = f"Analizamos en detalle el contender {brand_a}, un modelo muy popular en Amazon con excelentes valoraciones por su rendimiento y calidad."
    tasks.append(("product_a", text_a, os.path.join(dir_a, "audio.wav"), os.path.join(dir_a, "subtitles.ass"), "01_producto_a/audio.wav", "01_producto_a/subtitles.ass"))

    # 3. Product B (02_producto_b)
    dir_b = os.path.join(project_dir, "02_producto_b")
    os.makedirs(dir_b, exist_ok=True)
    text_b = (script.get("product_b_overview", "") + " " + script.get("product_b_reviews", "")).strip()
    if not text_b:
        text_b = f"Pasamos ahora a su competidor directo: el modelo de {brand_b}, que destaca por su versatilidad y diseño enfocado en la mejor experiencia de uso."
    tasks.append(("product_b", text_b, os.path.join(dir_b, "audio.wav"), os.path.join(dir_b, "subtitles.ass"), "02_producto_b/audio.wav", "02_producto_b/subtitles.ass"))

    # 4. Comparison (03_comparison)
    dir_comp = os.path.join(project_dir, "03_comparison")
    os.makedirs(dir_comp, exist_ok=True)
    text_comp = script.get("comparison", "").strip()
    if not text_comp:
        text_comp = f"Frente a frente, {brand_a} y {brand_b} ofrecen prestaciones de nivel. La elección dependerá de si priorizas el precio o las funciones específicas."
    tasks.append(("comparison", text_comp, os.path.join(dir_comp, "audio.wav"), os.path.join(dir_comp, "subtitles.ass"), "03_comparison/audio.wav", "03_comparison/subtitles.ass"))

    # 5. Outro (08_outro)
    dir_outro = os.path.join(project_dir, "08_outro")
    os.makedirs(dir_outro, exist_ok=True)
    text_outro = script.get("outro", "").strip()
    if not text_outro:
        text_outro = f"¿Cuál elegirías tú: {brand_a} o {brand_b}? Déjanos tu opinión en los comentarios y consulta los enlaces con oferta en la descripción."
    tasks.append(("outro", text_outro, os.path.join(dir_outro, "audio.wav"), os.path.join(dir_outro, "subtitles.ass"), "08_outro/audio.wav", "08_outro/subtitles.ass"))

    def process_task(task):
        key, text, wav_path, ass_path, rel_wav, rel_ass = task
        if os.path.exists(wav_path) and os.path.exists(ass_path) and os.path.getsize(wav_path) > 1000 and os.path.getsize(ass_path) > 50:
            dur = get_audio_duration(wav_path)
            if dur > 1.0:
                print(f"[CACHE TTS] Reutilizando audio existente ({dur:.1f}s) para {key}: {wav_path}")
                return key, rel_wav, rel_ass, dur
        synth_and_align(text, wav_path, ass_path, voice=voice_name)
        dur = get_audio_duration(wav_path)
        return key, rel_wav, rel_ass, dur

    results = {}
    # Sequential execution to prevent ROCm GPU memory collisions / SIGSEGV
    for t in tasks:
        key, rel_wav, rel_ass, dur = process_task(t)
        results[key] = (rel_wav, rel_ass, dur)

    audio_files = {}
    subtitle_files = {}
    durations = {}
    total_dur = 0.0

    for key in ["hook", "product_a", "product_b", "comparison", "outro"]:
        if key in results:
            rel_wav, rel_ass, dur = results[key]
            audio_files[key] = rel_wav
            subtitle_files[key] = rel_ass
            durations[key] = dur
            total_dur += dur

    data["audio_files"] = audio_files
    data["subtitle_files"] = subtitle_files
    data["durations"] = durations
    data["total_audio_duration"] = total_dur

    with open(script_json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    try:
        from qwen_tts_engine import release_tts_memory
        release_tts_memory()
    except Exception:
        pass

    return {
        "status": "success",
        "voice": voice_name,
        "total_duration": total_dur,
        "audio_files": audio_files,
        "subtitle_files": subtitle_files
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TTS y subtítulos para comparativas VS")
    parser.add_argument("--script_json", required=True, help="Ruta al data.json del proyecto")
    parser.add_argument("--voice", default="es-ES-AlvaroNeural", help="Voz de edge_tts")
    args = parser.parse_args()

    res = generate_vs_tts(args.script_json, args.voice)
    print(json.dumps(res, ensure_ascii=False))
