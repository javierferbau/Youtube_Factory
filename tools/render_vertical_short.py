#!/usr/bin/env python3
"""
render_vertical_short.py
Renderiza un vídeo vertical en formato 9:16 (1080x1920) de máxima calidad para YouTube Shorts (<60s).
Utiliza el producto ganador (#1), la locución del guion corto y los subtítulos sincrónicos.
"""

import sys
import os
import json
import subprocess
import argparse
from PIL import Image, ImageDraw, ImageFont

def create_vertical_badge(text, output_png_path, font_size=48):
    """Crea una insignia de texto rectangular para la parte superior del vídeo vertical 9:16."""
    try:
        font_main = ImageFont.truetype('/usr/share/fonts/liberation/LiberationSans-Bold.ttf', font_size)
    except Exception:
        font_main = ImageFont.load_default()

    dummy = Image.new('RGBA', (1, 1))
    ddraw = ImageDraw.Draw(dummy)
    bbox = ddraw.textbbox((0, 0), text, font=font_main)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    pad_x, pad_y = 50, 25
    bg_w = tw + pad_x * 2
    bg_h = th + pad_y * 2

    canvas = Image.new('RGBA', (bg_w, bg_h), (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(canvas)

    # Estilo dorado/negro premium
    cdraw.rounded_rectangle([(0, 0), (bg_w - 1, bg_h - 1)], radius=20, fill=(15, 23, 42, 230), outline=(250, 204, 21, 255), width=4)
    cdraw.text((pad_x, pad_y - 4), text, font=font_main, fill=(250, 204, 21, 255))

    canvas.save(output_png_path, 'PNG')
    return output_png_path

def create_bottom_cta_badge(price_text, output_png_path):
    """Crea una insignia inferior llamativa de CTA y precio para retención y clics en Shorts (1080x1920)."""
    try:
        f_price = ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans-Bold.ttf', 38)
        f_cta = ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans-Bold.ttf', 30)
    except Exception:
        f_price = ImageFont.load_default()
        f_cta = ImageFont.load_default()

    canvas_w, canvas_h = 960, 110
    im = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)

    # Sombra del contenedor
    draw.rounded_rectangle([2, 4, canvas_w - 2, canvas_h], radius=22, fill=(0, 0, 0, 190))
    # Contenedor oscuro con borde verde esmeralda brillante
    draw.rounded_rectangle([0, 0, canvas_w - 4, canvas_h - 4], radius=20, fill=(15, 23, 42, 245), outline=(34, 197, 94, 255), width=3)

    clean_p = price_text.strip() if price_text else "OFERTA"
    if "€" not in clean_p and clean_p != "OFERTA":
        clean_p = f"{clean_p}€"
    pb_box = f_price.getbbox(clean_p)
    pw = pb_box[2] - pb_box[0] + 44
    draw.rounded_rectangle([16, 14, 16 + pw, canvas_h - 18], radius=14, fill=(22, 101, 52, 255), outline=(74, 222, 128, 255), width=2)
    draw.text((16 + (pw - (pb_box[2] - pb_box[0])) // 2, 24), clean_p, font=f_price, fill=(255, 255, 255))

    cta_txt = "▼ VER OFERTA EN COMENTARIO FIJADO"
    draw.text((16 + pw + 25, 34), cta_txt, font=f_cta, fill=(250, 204, 21, 255))

    im.save(output_png_path, "PNG")
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

def render_short_vertical(project_dir):
    short_script_path = os.path.join(project_dir, "short_script.json")
    data_json_path = os.path.join(project_dir, "data.json")

    if os.path.exists(short_script_path):
        with open(short_script_path, "r", encoding="utf-8") as f:
            short_data = json.load(f)
    else:
        # Generar short_script.json al vuelo si no existe
        venv_py = "/home/javierferb/n8n/venv/bin/python3"
        subprocess.run([venv_py, "/home/javierferb/n8n/tools/generate_short_script.py", project_dir], check=True)
        with open(short_script_path, "r", encoding="utf-8") as f:
            short_data = json.load(f)

    short_dir = os.path.join(project_dir, "00_short")
    audio_wav = os.path.join(short_dir, "audio.wav")
    subtitles_ass = os.path.join(short_dir, "subtitles.ass")

    # Si no existe el audio del short, sintetizarlo con kokoro_tts
    if not os.path.exists(audio_wav):
        venv_py = "/home/javierferb/n8n/venv/bin/python3"
        subprocess.run([venv_py, "/home/javierferb/n8n/tools/kokoro_tts.py", "--script_json", short_script_path, "--mode", "short"], check=True)

    aud_dur = get_audio_duration(audio_wav)
    # Límite estricto de YouTube Shorts: 59.0 segundos
    video_dur = min(aud_dur + 0.5, 59.0)

    # Localizar archivo de medios del Producto #1 (ganador)
    top_prod = short_data.get("top_product", {})
    vfile = top_prod.get("video_file")
    if vfile and os.path.exists(os.path.join(project_dir, vfile)):
        media_file = os.path.join(project_dir, vfile)
        is_video = True
    else:
        # Fallback a la primera carpeta de producto (01_producto_1)
        prod1_dir = os.path.join(project_dir, "01_producto_1")
        prod1_vfile = os.path.join(prod1_dir, "product_1.mp4")
        prod1_ifile = os.path.join(prod1_dir, "product_1.jpg")
        if os.path.exists(prod1_vfile):
            media_file = prod1_vfile
            is_video = True
        elif os.path.exists(prod1_ifile):
            media_file = prod1_ifile
            is_video = False
        else:
            media_file = None
            is_video = False

    if not media_file:
        print(json.dumps({"error": f"No se encontró archivo de vídeo o imagen para el Short en {project_dir}"}))
        sys.exit(1)

    # Crear insignia superior "Nº 1 TOP CALIDAD 🏆"
    query_name = short_data.get("query", "MEJOR OPCIÓN").upper().strip()
    badge_text = f"Nº 1 TOP {query_name[:25]}"
    top_badge_png = os.path.join(short_dir, "badge_top_short.png")
    create_vertical_badge(badge_text, top_badge_png, font_size=46)

    # Crear insignia inferior de CTA y Precio (y=1550)
    raw_price = top_prod.get("price") or ""
    if not raw_price and os.path.exists(data_json_path):
        try:
            with open(data_json_path, "r", encoding="utf-8") as df:
                d_all = json.load(df)
                raw_price = d_all.get("product_a", {}).get("price") or (d_all.get("products", [{}])[0].get("price", ""))
        except Exception:
            pass
    try:
        from thumbnail_engine import format_clean_price
        clean_price = format_clean_price(raw_price, "OFERTA") if raw_price else "OFERTA"
    except Exception:
        clean_price = str(raw_price).strip() if raw_price else "OFERTA"

    bottom_badge_png = os.path.join(short_dir, "badge_bottom_cta.png")
    create_bottom_cta_badge(clean_price, bottom_badge_png)

    # Subtítulos ASS
    sub_filter = ""
    if os.path.exists(subtitles_ass):
        sub_esc = subtitles_ass.replace(":", r"\:").replace("'", r"\'")
        sub_filter = f"subtitles='{sub_esc}':force_style='MarginV=440'"

    # Filtergraph FFmpeg para 9:16 (1080x1920) con Ken Burns suave en fotos y doble insignia (top y bottom CTA)
    if is_video:
        vf_base = (
            "[0:v]hflip,setpts=0.96*PTS,crop=iw*0.88:ih*0.88,eq=contrast=1.12:brightness=0.03:saturation=1.18,split[main][bg];"
            "[bg]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,boxblur=15:3,scale=1080:1920:flags=bicubic[bglur];"
            "[main]scale=1080:1080:force_original_aspect_ratio=decrease[fg];"
            "[bglur][fg]overlay=(W-w)/2:(H-h)/2[vid0];"
            "[vid0][2:v]overlay=(W-w)/2:180[vid1];"
            "[vid1][3:v]overlay=(W-w)/2:1550"
        )
    else:
        vf_base = (
            "[0:v]crop=iw*0.90:ih*0.90,eq=contrast=1.10:brightness=0.03:saturation=1.15,split[main][bg];"
            "[bg]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,boxblur=15:3,scale=1080:1920:flags=bicubic[bglur];"
            "[main]zoompan=z='min(zoom+0.0012,1.14)':d=700:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1080:fps=30[fg];"
            "[bglur][fg]overlay=(W-w)/2:(H-h)/2[vid0];"
            "[vid0][2:v]overlay=(W-w)/2:180[vid1];"
            "[vid1][3:v]overlay=(W-w)/2:1550"
        )

    if sub_filter:
        vf_base += f",{sub_filter}"
    vf_base += "[outv]"

    # Formatear inputs de entrada
    media_input_args = ["-stream_loop", "-1", "-i", media_file] if is_video else ["-loop", "1", "-i", media_file]

    # Mezcla de audio con música de fondo y audio ducking (sidechaincompress)
    bg_music_path = "/home/javierferb/n8n/assets/music/background_music.wav"
    use_bg_music = os.path.exists(bg_music_path)

    output_short_mp4 = os.path.join(project_dir, "RENDER_FINAL_SHORT_VERTICAL.mp4")

    if use_bg_music:
        # Inputs: 0=media(v), 1=audio_narration(a), 2=top_badge(v), 3=bottom_badge(v), 4=bg_music(a)
        cmd = [
            "ffmpeg", "-y",
            *media_input_args,
            "-i", audio_wav,
            "-i", top_badge_png,
            "-i", bottom_badge_png,
            "-stream_loop", "-1", "-i", bg_music_path,
            "-t", f"{video_dur:.2f}",
            "-r", "30",
            "-filter_complex", (
                f"{vf_base};"
                f"[1:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,volume=1.0,asplit[speech1][speech2];"
                f"[4:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,volume=0.20[music];"
                f"[music][speech1]sidechaincompress=threshold=0.03:ratio=4:attack=80:release=350[ducked_music];"
                f"[speech2][ducked_music]amix=inputs=2:duration=first:dropout_transition=0:weights=1 1[outa]"
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
            *media_input_args,
            "-i", audio_wav,
            "-i", top_badge_png,
            "-i", bottom_badge_png,
            "-t", f"{video_dur:.2f}",
            "-r", "30",
            "-filter_complex", vf_base,
            "-map", "[outv]",
            "-map", "1:a:0",
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
    parser = argparse.ArgumentParser(description="Renderizadior de Vídeo Vertical 9:16 para YouTube Shorts")
    parser.add_argument("--project_dir", required=True, help="Directorio del proyecto")
    args = parser.parse_args()

    render_short_vertical(os.path.abspath(args.project_dir))
