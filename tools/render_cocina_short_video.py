#!/usr/bin/env python3
"""
render_cocina_short_video.py
Renderiza un vídeo vertical 9:16 (1080x1920) en formato Split Screen para "Cocina Tecnológica" (<60s).
Mitad superior: Producto A
Mitad inferior: Producto B
Centro: Insignia 3D VS + Banner de cabecera "🍳 Cocina Tecnológica ⚡" + Subtítulos sincronizados.
"""

import sys
import os
import json
import subprocess
import argparse
from PIL import Image, ImageDraw, ImageFont

def create_top_badge(text, output_png_path, font_size=44):
    try:
        font_main = ImageFont.truetype('/usr/share/fonts/liberation/LiberationSans-Bold.ttf', font_size)
    except Exception:
        font_main = ImageFont.load_default()

    dummy = Image.new('RGBA', (1, 1))
    ddraw = ImageDraw.Draw(dummy)
    bbox = ddraw.textbbox((0, 0), text, font=font_main)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    pad_x, pad_y = 40, 20
    bg_w = tw + pad_x * 2
    bg_h = th + pad_y * 2

    canvas = Image.new('RGBA', (bg_w, bg_h), (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(canvas)

    cdraw.rounded_rectangle([(0, 0), (bg_w - 1, bg_h - 1)], radius=18, fill=(20, 15, 10, 235), outline=(255, 165, 0, 255), width=4)
    cdraw.text((pad_x, pad_y - 2), text, font=font_main, fill=(255, 225, 100, 255))

    canvas.save(output_png_path, 'PNG')
    return output_png_path

def create_vs_center_badge(output_png_path, size=200):
    canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(canvas)

    center = size // 2
    radius = (size // 2) - 6

    cdraw.ellipse([(center - radius, center - radius), (center + radius, center + radius)], fill=(25, 18, 12, 245), outline=(255, 140, 0, 255), width=6)

    try:
        font_vs = ImageFont.truetype('/usr/share/fonts/liberation/LiberationSans-Bold.ttf', 80)
    except Exception:
        font_vs = ImageFont.load_default()

    bbox = cdraw.textbbox((0, 0), "VS", font=font_vs)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    cdraw.text((center - tw // 2, center - th // 2 - 8), "VS", font=font_vs, fill=(255, 215, 0, 255))

    canvas.save(output_png_path, 'PNG')
    return output_png_path

def get_audio_duration(file_path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(res.stdout.strip())
    except Exception:
        return 45.0

def locate_product_media(project_dir, folder_name):
    prod_dir = os.path.join(project_dir, folder_name)
    if not os.path.exists(prod_dir):
        return None, False

    for f in os.listdir(prod_dir):
        if f.endswith(".mp4"):
            return os.path.join(prod_dir, f), True

    for f in os.listdir(prod_dir):
        if f.endswith(".jpg") or f.endswith(".png"):
            return os.path.join(prod_dir, f), False

    return None, False

def render_cocina_short(project_dir):
    short_script_path = os.path.join(project_dir, "short_script.json")
    data_json_path = os.path.join(project_dir, "data.json")

    if not os.path.exists(short_script_path):
        venv_py = "/home/javierferb/n8n/venv/bin/python3"
        subprocess.run([venv_py, "/home/javierferb/n8n/tools/save_vs_short_script.py", project_dir], check=True)

    with open(short_script_path, "r", encoding="utf-8") as f:
        short_data = json.load(f)

    data_obj = {}
    if os.path.exists(data_json_path):
        try:
            with open(data_json_path, "r", encoding="utf-8") as f:
                data_obj = json.load(f)
        except Exception:
            pass

    short_dir = os.path.join(project_dir, "00_short")
    os.makedirs(short_dir, exist_ok=True)

    audio_wav = os.path.join(short_dir, "audio.wav")
    subtitles_ass = os.path.join(short_dir, "subtitles.ass")

    if not os.path.exists(audio_wav):
        venv_py = "/home/javierferb/n8n/venv/bin/python3"
        subprocess.run([venv_py, "/home/javierferb/n8n/tools/kokoro_tts.py", "--script_json", short_script_path, "--mode", "short"], check=True)

    aud_dur = get_audio_duration(audio_wav)
    video_dur = min(aud_dur + 0.5, 59.0)

    media_a, is_video_a = locate_product_media(project_dir, "producto_a")
    if not media_a:
        media_a, is_video_a = locate_product_media(project_dir, "01_producto_a")

    media_b, is_video_b = locate_product_media(project_dir, "producto_b")
    if not media_b:
        media_b, is_video_b = locate_product_media(project_dir, "02_producto_b")

    if not media_a or not media_b:
        print(json.dumps({"error": f"Faltan archivos de producto A o B en {project_dir}"}))
        sys.exit(1)

    product_a = data_obj.get("product_a", {})
    product_b = data_obj.get("product_b", {})
    brand_a = (product_a.get("brand", "A")).upper()
    brand_b = (product_b.get("brand", "B")).upper()

    header_text = f"🍳 {brand_a} vs {brand_b} ⚡"
    top_badge_png = os.path.join(short_dir, "badge_top_cocina.png")
    create_top_badge(header_text, top_badge_png, font_size=42)

    vs_badge_png = os.path.join(short_dir, "badge_vs_center.png")
    create_vs_center_badge(vs_badge_png, size=200)

    sub_filter = ""
    if os.path.exists(subtitles_ass):
        sub_esc = subtitles_ass.replace(":", "\\:").replace("'", "\\'")
        sub_filter = f"subtitles='{sub_esc}'"

    args_a = ["-stream_loop", "-1", "-i", media_a] if is_video_a else ["-loop", "1", "-i", media_a]
    args_b = ["-stream_loop", "-1", "-i", media_b] if is_video_b else ["-loop", "1", "-i", media_b]

    filter_graph = (
        "[0:v]hflip,setpts=PTS-STARTPTS,crop=iw*0.88:ih*0.88,scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,eq=contrast=1.12:brightness=0.03:saturation=1.18[topv];"
        "[1:v]hflip,setpts=PTS-STARTPTS,crop=iw*0.88:ih*0.88,scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,eq=contrast=1.12:brightness=0.03:saturation=1.18[botv];"
        "[topv][botv]vstack=inputs=2[splitv];"
        "[splitv][3:v]overlay=(W-w)/2:80[v1];"
        "[v1][4:v]overlay=(W-w)/2:(H-h)/2[v2]"
    )

    if sub_filter:
        filter_graph += f";[v2]{sub_filter}[outv]"
    else:
        filter_graph += ";[v2]null[outv]"

    bg_music_path = "/home/javierferb/n8n/assets/music/background_music.wav"
    use_bg_music = os.path.exists(bg_music_path)
    output_short_mp4 = os.path.join(project_dir, "RENDER_FINAL_SHORT_VERTICAL.mp4")

    if use_bg_music:
        cmd = [
            "ffmpeg", "-y",
            *args_a,
            *args_b,
            "-i", audio_wav,
            "-i", top_badge_png,
            "-i", vs_badge_png,
            "-stream_loop", "-1", "-i", bg_music_path,
            "-t", f"{video_dur:.2f}",
            "-r", "30",
            "-filter_complex", (
                f"{filter_graph};"
                f"[2:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,volume=1.0[speech];"
                f"[5:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,volume=0.10[music];"
                f"[speech][music]amix=inputs=2:duration=first:dropout_transition=0:weights=1 1[outa]"
            ),
            "-map", "[outv]",
            "-map", "[outa]",
            "-pix_fmt", "yuv420p",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
            "-ar", "44100", "-ac", "2", "-c:a", "aac", "-b:a", "192k",
            output_short_mp4
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            *args_a,
            *args_b,
            "-i", audio_wav,
            "-i", top_badge_png,
            "-i", vs_badge_png,
            "-t", f"{video_dur:.2f}",
            "-r", "30",
            "-filter_complex", filter_graph,
            "-map", "[outv]",
            "-map", "2:a:0",
            "-pix_fmt", "yuv420p",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
            "-ar", "44100", "-ac", "2", "-c:a", "aac", "-b:a", "192k",
            output_short_mp4
        ]

    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    print(json.dumps({
        "status": "success",
        "final_video": output_short_mp4,
        "resolution": "1080x1920",
        "duration": video_dur,
        "is_short": True
    }, ensure_ascii=False))

    return output_short_mp4

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Renderizador Vertical Shorts Cocina Tecnológica")
    parser.add_argument("project_dir", help="Directorio del proyecto")
    args = parser.parse_args()

    render_cocina_short(os.path.abspath(args.project_dir))
