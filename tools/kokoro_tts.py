#!/usr/bin/env python3
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

def generate_tts_and_subtitles(script_json_path, voice_name="es-ES-AlvaroNeural"):
    with open(script_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    project_dir = data.get("project_dir", os.path.dirname(script_json_path))
    query       = data.get("query", "productos").strip().lower()
    script      = data.get("script", {})

    tasks = []

    # 1. Intro (00_intro)
    intro_dir = os.path.join(project_dir, "00_intro")
    os.makedirs(intro_dir, exist_ok=True)
    hook_text = script.get("hook", "").strip()
    if not hook_text:
        hook_text = f"Bienvenido a nuestro ranking definitivo de los 7 mejores {query} de Amazon con mejor valoración."
    hook_wav = os.path.join(intro_dir, "audio.wav")
    hook_ass = os.path.join(intro_dir, "subtitles.ass")
    tasks.append(("hook", hook_text, hook_wav, hook_ass, os.path.join("00_intro", "audio.wav"), os.path.join("00_intro", "subtitles.ass")))

    # 2. Products
    products_script = script.get("products", [])
    products_info   = data.get("products", [])

    for idx in range(max(len(products_script), len(products_info))):
        rank             = idx + 1
        prod_folder_name = f"{rank:02d}_producto_{rank}"
        prod_dir         = os.path.join(project_dir, prod_folder_name)
        os.makedirs(prod_dir, exist_ok=True)

        p_text = products_script[idx].strip() if idx < len(products_script) and isinstance(products_script[idx], str) else ""
        p_info = products_info[idx]   if idx < len(products_info)   else {}

        if not p_text:
            title  = p_info.get("title",  f"Producto {rank}")
            price  = p_info.get("price",  "Consultar precio")
            rating = p_info.get("rating", "4.5")
            p_text = (
                f"En el puesto número {rank} del ranking destacamos este increíble modelo de {query}: {title}. "
                f"Cuenta con una excelente valoración de {rating} estrellas en Amazon y un precio competitivo de aproximadamente {price}. "
                f"Sin duda es una opción ideal por sus prestaciones, durabilidad y facilidad de uso."
            )

        p_wav = os.path.join(prod_dir, "audio.wav")
        p_ass = os.path.join(prod_dir, "subtitles.ass")
        tasks.append((f"product_{rank}", p_text, p_wav, p_ass, os.path.join(prod_folder_name, "audio.wav"), os.path.join(prod_folder_name, "subtitles.ass")))

    # 3. Outro (08_outro)
    outro_dir = os.path.join(project_dir, "08_outro")
    os.makedirs(outro_dir, exist_ok=True)
    outro_text = script.get("outro", "").strip()
    if not outro_text:
        outro_text = (
            f"Encuentra todos los enlaces directos a cada uno de estos {query} en la descripción del vídeo. "
            f"No olvides dar a me gusta y suscribirte para más rankings de productos."
        )
    outro_wav = os.path.join(outro_dir, "audio.wav")
    outro_ass = os.path.join(outro_dir, "subtitles.ass")
    tasks.append(("outro", outro_text, outro_wav, outro_ass, os.path.join("08_outro", "audio.wav"), os.path.join("08_outro", "subtitles.ass")))

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

    audio_files    = {}
    subtitle_files = {}
    durations      = {}
    current_time   = 0.0

    if "hook" in results:
        rel_wav, rel_ass, dur = results["hook"]
        audio_files["hook"]    = rel_wav
        subtitle_files["hook"] = rel_ass
        durations["hook"]      = dur
        current_time          += dur

    prod_durations = []
    for idx in range(max(len(products_script), len(products_info))):
        rank = idx + 1
        key = f"product_{rank}"
        if key in results:
            rel_wav, rel_ass, dur = results[key]
            audio_files[key]    = rel_wav
            subtitle_files[key] = rel_ass
            prod_durations.append(dur)
            current_time += dur
    durations["products"] = prod_durations

    if "outro" in results:
        rel_wav, rel_ass, dur = results["outro"]
        audio_files["outro"]    = rel_wav
        subtitle_files["outro"] = rel_ass
        durations["outro"]      = dur
        current_time           += dur

    data["audio_files"]          = audio_files
    data["subtitle_files"]       = subtitle_files
    data["durations"]            = durations
    data["total_audio_duration"] = current_time

    with open(script_json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    try:
        from qwen_tts_engine import release_tts_memory
        release_tts_memory()
    except Exception:
        pass

    return {
        "status":         "success",
        "voice":          voice_name,
        "total_duration": current_time,
        "audio_files":    audio_files,
        "subtitle_files": subtitle_files,
    }

def generate_short_tts_and_subtitles(short_script_path, voice_name="es-ES-AlvaroNeural"):
    with open(short_script_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    project_dir = os.path.dirname(short_script_path)
    full_text = data.get("full_text", "").strip()

    short_dir = os.path.join(project_dir, "00_short")
    os.makedirs(short_dir, exist_ok=True)

    wav_path = os.path.join(short_dir, "audio.wav")
    ass_path = os.path.join(short_dir, "subtitles.ass")

    ASS_HEADER_VERTICAL = """\
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,68,&H00FFFFFF,&H000000FF,&H00000000,&HB4000000,1,0,0,0,100,100,0,0,1,5,2,2,60,60,260,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    synth_and_align(full_text, wav_path, ass_path, voice=voice_name, words_per_line=4)

    if os.path.exists(ass_path):
        with open(ass_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        dialogue_lines = [l for l in lines if l.startswith("Dialogue:")]
        with open(ass_path, 'w', encoding='utf-8') as f:
            f.write(ASS_HEADER_VERTICAL)
            f.writelines(dialogue_lines)

    dur = get_audio_duration(wav_path)
    data["audio_file"] = os.path.join("00_short", "audio.wav")
    data["subtitle_file"] = os.path.join("00_short", "subtitles.ass")
    data["duration"] = dur

    with open(short_script_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {
        "status": "success",
        "mode": "short",
        "voice": voice_name,
        "duration": dur,
        "audio_file": wav_path,
        "subtitle_file": ass_path
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Spanish TTS + faster-whisper subtitle sync generator")
    parser.add_argument("--script_json", required=True, help="Ruta al data.json o short_script.json del proyecto")
    parser.add_argument("--voice", default="es-ES-AlvaroNeural", help="Voz de edge_tts (es-ES-AlvaroNeural)")
    parser.add_argument("--mode", default="all", choices=["all", "short"], help="Modo: all (vídeo largo) o short (vídeo corto 9:16)")
    args = parser.parse_args()

    if args.mode == "short" or "short_script" in args.script_json:
        res = generate_short_tts_and_subtitles(args.script_json, args.voice)
    else:
        res = generate_tts_and_subtitles(args.script_json, args.voice)

    print(json.dumps(res, ensure_ascii=False))
