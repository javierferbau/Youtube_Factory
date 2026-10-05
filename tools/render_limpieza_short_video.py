#!/usr/bin/env python3
"""
render_limpieza_short_video.py
Renderiza un vídeo vertical 9:16 (1080x1920) en formato Split Screen para "Limpieza Tecnológica" (<60s).
Mitad superior: Producto A
Mitad inferior: Producto B
Centro: Insignia 3D VS + Banner de cabecera "🧹 Limpieza Tecnológica ⚡" + Subtítulos sincronizados.
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

    cdraw.rounded_rectangle([(0, 0), (bg_w - 1, bg_h - 1)], radius=18, fill=(10, 20, 35, 235), outline=(0, 229, 255, 255), width=4)
    cdraw.text((pad_x, pad_y - 2), text, font=font_main, fill=(220, 245, 255, 255))

    canvas.save(output_png_path, 'PNG')
    return output_png_path

def create_vs_center_badge(output_png_path, size=200):
    canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(canvas)

    center = size // 2
    radius = (size // 2) - 6

    cdraw.ellipse([(center - radius, center - radius), (center + radius, center + radius)], fill=(12, 22, 38, 245), outline=(0, 200, 255, 255), width=6)

    try:
        font_vs = ImageFont.truetype('/usr/share/fonts/liberation/LiberationSans-Bold.ttf', 80)
    except Exception:
        font_vs = ImageFont.load_default()

    bbox = cdraw.textbbox((0, 0), "VS", font=font_vs)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    cdraw.text((center - tw // 2, center - th // 2 - 8), "VS", font=font_vs, fill=(0, 229, 255, 255))

    canvas.save(output_png_path, 'PNG')
    return output_png_path

def get_audio_duration(audio_file):
    if not os.path.exists(audio_file):
        return 35.0
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_file
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(res.stdout.strip())
    except Exception:
        return 35.0

def find_media(folder_path):
    import glob
    mp4s = glob.glob(os.path.join(folder_path, "*.mp4"))
    mp4s = [f for f in mp4s if not os.path.basename(f).startswith("segment") and not os.path.basename(f).startswith("short")]
    jpgs = glob.glob(os.path.join(folder_path, "*.jpg")) + glob.glob(os.path.join(folder_path, "*.jpeg")) + glob.glob(os.path.join(folder_path, "*.png"))
    jpgs = [f for f in jpgs if not os.path.basename(f).startswith("badge") and not os.path.basename(f).startswith("top_badge") and not os.path.basename(f).startswith("vs_badge")]
    return sorted(mp4s), sorted(jpgs)

def render_limpieza_short(project_dir):
    audio_file = os.path.join(project_dir, "short_audio.wav")
    if not os.path.exists(audio_file):
        audio_file = os.path.join(project_dir, "00_intro", "audio.wav")

    ass_file = os.path.join(project_dir, "short_subtitles.ass")
    if not os.path.exists(ass_file):
        ass_file = os.path.join(project_dir, "00_intro", "subtitles.ass")

    duration = get_audio_duration(audio_file)

    dir_a = os.path.join(project_dir, "01_producto_a")
    dir_b = os.path.join(project_dir, "02_producto_b")

    mp4s_a, jpgs_a = find_media(dir_a)
    mp4s_b, jpgs_b = find_media(dir_b)

    source_a = mp4s_a[0] if mp4s_a else (jpgs_a[0] if jpgs_a else None)
    source_b = mp4s_b[0] if mp4s_b else (jpgs_b[0] if jpgs_b else None)

    top_badge_png = os.path.join(project_dir, "top_badge.png")
    vs_badge_png = os.path.join(project_dir, "vs_badge.png")

    create_top_badge("🧹 LIMPIEZA TECNOLÓGICA ⚡", top_badge_png, font_size=44)
    create_vs_center_badge(vs_badge_png, size=220)

    filter_complex = (
        f"[0:v]hflip,crop=iw*0.88:ih*0.88,loop=loop=-1:size=32767:start=0,scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,eq=contrast=1.12:brightness=0.03:saturation=1.18[top];"
        f"[1:v]hflip,crop=iw*0.88:ih*0.88,loop=loop=-1:size=32767:start=0,scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,eq=contrast=1.12:brightness=0.03:saturation=1.18[bottom];"
        f"[top][bottom]vstack=inputs=2[bg];"
        f"[2:v]scale=iw:ih[top_overlay];"
        f"[3:v]scale=iw:ih[vs_overlay];"
        f"[bg][top_overlay]overlay=(W-w)/2:80[v1];"
        f"[v1][vs_overlay]overlay=(W-w)/2:(H-h)/2[v2]"
    )

    if os.path.exists(ass_file):
        ass_escaped = ass_file.replace(":", "\\:").replace("'", "\\'")
        filter_complex += f";[v2]subtitles='{ass_escaped}'[outv]"
    else:
        filter_complex += f";[v2]copy[outv]"

    output_short = os.path.join(project_dir, "short_video.mp4")

    cmd = [
        "ffmpeg", "-y",
        "-i", source_a,
        "-i", source_b,
        "-i", top_badge_png,
        "-i", vs_badge_png,
        *(["-i", audio_file] if os.path.exists(audio_file) else ["-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono"]),
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "4:a",
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-r", "30",
        output_short
    ]

    subprocess.run(cmd, check=True)

    # Also create RENDER_FINAL_SHORT_VERTICAL.mp4 for n8n binary node compatibility
    render_final_short = os.path.join(project_dir, "RENDER_FINAL_SHORT_VERTICAL.mp4")
    try:
        import shutil
        shutil.copyfile(output_short, render_final_short)
    except Exception:
        pass

    print(f"Short 9:16 generado en: {output_short} y {render_final_short}")
    return output_short

def main():
    parser = argparse.ArgumentParser(description="Renderizador Vertical 9:16 Shorts Limpieza Tecnológica")
    parser.add_argument("project_dir", help="Directorio del proyecto")
    args = parser.parse_args()

    project_dir = os.path.abspath(args.project_dir)
    render_limpieza_short(project_dir)

if __name__ == "__main__":
    main()
