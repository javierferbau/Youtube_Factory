from reviewer_frame_engine import create_reviewer_card_overlay, get_reviewer_video_filter
#!/usr/bin/env python3
"""
render_limpieza_video.py
Renderizador horizontal 16:9 (1080p) personalizado para "Limpieza Tecnológica".
Formatos y Secciones:
- 00_intro (Split screen A vs B)
- 01_producto_a (Media loop Producto A)
- 02_producto_b (Media loop Producto B)
- 03_comparison (Split screen A vs B)
- 08_outro (Split screen A vs B)
"""

import sys
import os
import json
import glob
import shutil
import subprocess
import argparse
import concurrent.futures
from PIL import Image, ImageDraw, ImageFont

def create_limpieza_badge(text, output_png_path, font_size=36, is_main_banner=False):
    try:
        font_main = ImageFont.truetype('/usr/share/fonts/liberation/LiberationSans-Bold.ttf', font_size)
        font_emoji = ImageFont.truetype('/usr/share/fonts/noto/NotoColorEmoji.ttf', 109)
    except Exception:
        font_main = ImageFont.load_default()
        font_emoji = ImageFont.load_default()

    items = []
    if is_main_banner:
        items.append(('emoji', '🧹 '))
        items.append(('text', text))
        items.append(('emoji', ' ⚡'))
    else:
        items.append(('emoji', '🧹 '))
        items.append(('text', text))

    drawn_parts = []
    total_w = 0
    max_h = 0

    for item in items:
        kind = item[0]
        content = item[1]
        if kind == 'emoji':
            icon_img = Image.new('RGBA', (120, 120), (0, 0, 0, 0))
            idraw = ImageDraw.Draw(icon_img)
            try:
                idraw.text((0, 0), content.strip(), font=font_emoji, embedded_color=True)
            except Exception:
                pass
            bbox = icon_img.getbbox()
            if bbox:
                icon_img = icon_img.crop(bbox)
            target_h = int(font_size * 1.05)
            target_w = int(icon_img.width * (target_h / icon_img.height)) if icon_img.height > 0 else target_h
            icon_img = icon_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            drawn_parts.append(('image', icon_img))
            total_w += target_w + 12
            max_h = max(max_h, target_h)
        else:
            dummy = Image.new('RGBA', (1, 1))
            ddraw = ImageDraw.Draw(dummy)
            bbox = ddraw.textbbox((0, 0), content, font=font_main)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            drawn_parts.append(('text', content, font_main, tw, th))
            total_w += tw
            max_h = max(max_h, th)

    pad_x, pad_y = (40, 20) if is_main_banner else (30, 16)
    bg_w = total_w + pad_x * 2
    bg_h = max_h + pad_y * 2

    canvas = Image.new('RGBA', (bg_w, bg_h), (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(canvas)

    border_color = (0, 229, 255, 255) if is_main_banner else (0, 160, 255, 240)
    bg_fill = (10, 20, 35, 230)

    cdraw.rounded_rectangle(
        [(0, 0), (bg_w - 1, bg_h - 1)],
        radius=16,
        fill=bg_fill,
        outline=border_color,
        width=4 if is_main_banner else 3
    )

    curr_x = pad_x
    for part in drawn_parts:
        if part[0] == 'image':
            img = part[1]
            y_pos = pad_y + (max_h - img.height) // 2
            canvas.paste(img, (curr_x, y_pos), img)
            curr_x += img.width + 12
        else:
            txt = part[1]
            fnt = part[2]
            th = part[4]
            y_pos = pad_y + (max_h - th) // 2 - 2
            text_color = (255, 255, 255, 255) if is_main_banner else (220, 245, 255, 255)
            cdraw.text((curr_x, y_pos), txt, font=fnt, fill=text_color)
            curr_x += part[3]

    canvas.save(output_png_path, 'PNG')
    return output_png_path

def get_audio_duration(audio_file):
    if not os.path.exists(audio_file):
        return 8.0
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
        return 8.0

def find_media_files(folder_path):
    mp4s = glob.glob(os.path.join(folder_path, "*.mp4"))
    mp4s = [f for f in mp4s if not os.path.basename(f).startswith("segment")]
    jpgs = glob.glob(os.path.join(folder_path, "*.jpg")) + glob.glob(os.path.join(folder_path, "*.jpeg")) + glob.glob(os.path.join(folder_path, "*.png"))
    jpgs = [f for f in jpgs if not os.path.basename(f).startswith("badge")]
    return sorted(mp4s), sorted(jpgs)

def render_limpieza_segment(project_dir, folder_name, badge_text, is_split_screen=False):
    sec_dir = os.path.join(project_dir, folder_name)
    audio_file = os.path.join(sec_dir, "audio.wav")
    ass_file = os.path.join(sec_dir, "subtitles.ass")
    output_file = os.path.join(sec_dir, "segment.mp4")

    duration = get_audio_duration(audio_file)
    badge_png = os.path.join(sec_dir, "badge.png")
    create_limpieza_badge(badge_text, badge_png, font_size=36, is_main_banner=is_split_screen)

    if is_split_screen:
        dir_a = os.path.join(project_dir, "01_producto_a")
        dir_b = os.path.join(project_dir, "02_producto_b")
        mp4s_a, jpgs_a = find_media_files(dir_a)
        mp4s_b, jpgs_b = find_media_files(dir_b)

        source_a = mp4s_a[0] if mp4s_a else (jpgs_a[0] if jpgs_a else None)
        source_b = mp4s_b[0] if mp4s_b else (jpgs_b[0] if jpgs_b else None)

        filter_complex = (
            f"[0:v]hflip,crop=iw*0.88:ih*0.88,loop=loop=-1:size=32767:start=0,scale=960:1080:force_original_aspect_ratio=increase,crop=960:1080,eq=contrast=1.12:brightness=0.03:saturation=1.18[left];"
            f"[1:v]hflip,crop=iw*0.88:ih*0.88,loop=loop=-1:size=32767:start=0,scale=960:1080:force_original_aspect_ratio=increase,crop=960:1080,eq=contrast=1.12:brightness=0.03:saturation=1.18[right];"
            f"[left][right]hstack=inputs=2[bg];"
            f"[2:v]scale=iw:ih[overlay_img];"
            f"[bg][overlay_img]overlay=(W-w)/2:50[video_badge]"
        )

        inputs = ["-i", source_a, "-i", source_b, "-i", badge_png]
    else:
        mp4s, jpgs = find_media_files(sec_dir)
        source = mp4s[0] if mp4s else (jpgs[0] if jpgs else None)
        if not source:
            source = os.path.join(sec_dir, "fallback.png")
            img = Image.new('RGB', (1920, 1080), color=(20, 20, 20))
            img.save(source)

        is_vid = source.endswith(".mp4")
        prod_data = {}
        data_json_path = os.path.join(project_dir, "data.json")
        if os.path.exists(data_json_path):
            try:
                with open(data_json_path, "r", encoding="utf-8") as df:
                    d_obj = json.load(df)
                    prod_data = d_obj.get("product_a" if "producto_a" in folder_name else "product_b", {})
            except Exception:
                pass

        card_png = os.path.join(sec_dir, "reviewer_card_vs.png")
        create_reviewer_card_overlay(
            card_png,
            label=badge_text if badge_text else ("OPCIÓN A" if "producto_a" in folder_name else "OPCIÓN B"),
            brand=prod_data.get("brand", ""),
            title=prod_data.get("title", ""),
            price=prod_data.get("price", ""),
            rating=str(prod_data.get("rating", "4.5")),
            features=prod_data.get("features"),
            niche="limpieza",
            is_vs=True
        )

        inputs = ["-stream_loop", "-1", "-i", source, "-i", card_png] if is_vid else ["-loop", "1", "-i", source, "-i", card_png]

        sub_str = ""
        if os.path.exists(ass_file):
            ass_escaped = ass_file.replace(":", "\\:").replace("'", "\\'")
            sub_str = f"subtitles='{ass_escaped}'"

        filter_complex = get_reviewer_video_filter(overlay_idx=1, is_video=is_vid, sub_filter=sub_str)

    if is_split_screen:
        if os.path.exists(ass_file):
            ass_escaped = ass_file.replace(":", "\\:").replace("'", "\\'")
            filter_complex += f";[video_badge]subtitles='{ass_escaped}'[outv]"
        else:
            filter_complex += ";[video_badge]copy[outv]"

    audio_idx = inputs.count("-i")
    cmd = ["ffmpeg", "-y"]
    cmd.extend(inputs)
    cmd.extend([
        *(["-i", audio_file] if os.path.exists(audio_file) else ["-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono"]),
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", f"{audio_idx}:a",
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-r", "30",
        output_file
    ])

    subprocess.run(cmd, check=True)
    return output_file

def render_single_section(project_dir, folder_name, badge_txt, is_intro, mode="full"):
    if mode == "full":
        return render_limpieza_segment(project_dir, folder_name, badge_txt, is_intro)
    else:
        sec_dir = os.path.join(project_dir, folder_name)
        out_mp4 = os.path.join(sec_dir, "segment.mp4")
        return out_mp4 if os.path.exists(out_mp4) else None

def render_limpieza_project(project_dir, mode="full"):
    data_path = os.path.join(project_dir, "data.json")
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    product_a = data.get("product_a", {})
    product_b = data.get("product_b", {})
    brand_a = product_a.get("brand", "PRODUCTO A").upper()
    brand_b = product_b.get("brand", "PRODUCTO B").upper()

    sections = [
        ("00_intro", f"{brand_a} VS {brand_b} | COMPARATIVA COMPLETA", True),
        ("01_producto_a", f"OPCIÓN A: {brand_a}", False),
        ("02_producto_b", f"OPCIÓN B: {brand_b}", False),
        ("03_comparison", f"COMPARATIVA DIRECTA: {brand_a} VS {brand_b}", True),
        ("08_outro", "¿CUÁL PREFIERES PARA TU HOGAR? | COMENTA A o B", True),
    ]

    rendered_segments_map = {}

    if mode == "full":
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_folder = {
                executor.submit(render_single_section, project_dir, folder_name, badge_txt, is_intro, mode): folder_name
                for folder_name, badge_txt, is_intro in sections
            }
            for future in concurrent.futures.as_completed(future_to_folder):
                folder_name = future_to_folder[future]
                try:
                    res_mp4 = future.result()
                    if res_mp4:
                        rendered_segments_map[folder_name] = res_mp4
                except Exception as e:
                    print(f"Error renderizando sección {folder_name}: {e}")
    else:
        for folder_name, badge_txt, is_intro in sections:
            res_mp4 = render_single_section(project_dir, folder_name, badge_txt, is_intro, mode)
            if res_mp4:
                rendered_segments_map[folder_name] = res_mp4

    rendered_segments = []
    for folder_name, _, _ in sections:
        if folder_name in rendered_segments_map:
            rendered_segments.append(rendered_segments_map[folder_name])

    if not rendered_segments:
        raise RuntimeError("No se pudieron generar ni encontrar segmentos para concatenar.")

    concat_txt = os.path.join(project_dir, "concat.txt")
    with open(concat_txt, "w", encoding="utf-8") as f:
        for seg in rendered_segments:
            f.write(f"file '{seg}'\n")

    final_output = os.path.join(project_dir, "final_video.mp4")
    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_txt,
        "-c", "copy",
        final_output
    ]
    subprocess.run(cmd_concat, check=True)

    # Also create RENDER_FINAL_AMAZON.mp4 for n8n binary node compatibility
    render_final_amazon = os.path.join(project_dir, "RENDER_FINAL_AMAZON.mp4")
    try:
        shutil.copyfile(final_output, render_final_amazon)
    except Exception:
        pass

    print(f"Vídeo horizontal final generado en: {final_output} y {render_final_amazon}")
    return final_output

def main():
    parser = argparse.ArgumentParser(description="Renderizador 16:9 Limpieza Tecnológica")
    parser.add_argument("project_dir", help="Directorio del proyecto")
    parser.add_argument("--mode", default="full", choices=["full", "concat"], help="Modo de renderizado")
    args = parser.parse_args()

    project_dir = os.path.abspath(args.project_dir)
    render_limpieza_project(project_dir, mode=args.mode)

if __name__ == "__main__":
    main()
