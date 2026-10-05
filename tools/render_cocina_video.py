from reviewer_frame_engine import create_reviewer_card_overlay, get_reviewer_video_filter
#!/usr/bin/env python3
"""
render_cocina_video.py
Renderizador horizontal 16:9 (1080p) personalizado para "Cocina Tecnológica".
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
import subprocess
import argparse
import concurrent.futures
from PIL import Image, ImageDraw, ImageFont

def create_cocina_badge(text, output_png_path, font_size=36, is_main_banner=False):
    try:
        font_main = ImageFont.truetype('/usr/share/fonts/liberation/LiberationSans-Bold.ttf', font_size)
        font_emoji = ImageFont.truetype('/usr/share/fonts/noto/NotoColorEmoji.ttf', 109)
    except Exception:
        font_main = ImageFont.load_default()
        font_emoji = ImageFont.load_default()

    items = []
    if is_main_banner:
        items.append(('emoji', '🍳 '))
        items.append(('text', text))
        items.append(('emoji', ' ⚡'))
    else:
        items.append(('emoji', '🍳 '))
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

    border_color = (255, 165, 0, 255) if is_main_banner else (255, 215, 0, 240)
    bg_fill = (20, 15, 10, 225)
    text_color = (255, 225, 100, 255) if is_main_banner else (255, 255, 255, 255)

    cdraw.rounded_rectangle([(0, 0), (bg_w - 1, bg_h - 1)], radius=16, fill=bg_fill, outline=border_color, width=3)

    curr_x = pad_x
    for part in drawn_parts:
        if part[0] == 'image':
            img_part = part[1]
            y_pos = (bg_h - img_part.height) // 2
            canvas.paste(img_part, (curr_x, y_pos), img_part)
            curr_x += img_part.width + 12
        else:
            _, txt, font, tw, th = part
            y_pos = (bg_h - th) // 2 - 3
            cdraw.text((curr_x, y_pos), txt, font=font, fill=text_color)
            curr_x += tw

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
        return 5.0

def find_media_for_product(project_dir, prod_folder_name):
    search_dirs = [
        os.path.join(project_dir, prod_folder_name)
    ]
    if prod_folder_name == "producto_a":
        search_dirs.append(os.path.join(project_dir, "01_producto_a"))
    elif prod_folder_name == "producto_b":
        search_dirs.append(os.path.join(project_dir, "02_producto_b"))

    valid_mp4s = []
    valid_imgs = []
    seen_basenames = set()
    ignored = ["segment.mp4", "RENDER_FINAL", "final_output", "badge", "badge_top", "badge_vs", "temp"]

    for d in search_dirs:
        if not os.path.exists(d):
            continue
        for root, _, files in os.walk(d):
            for file in sorted(files):
                full_path = os.path.join(root, file)
                file_lower = file.lower()
                if any(ign in file_lower for ign in ignored):
                    continue
                if file_lower in seen_basenames:
                    continue
                if file_lower.endswith(".mp4"):
                    seen_basenames.add(file_lower)
                    valid_mp4s.append(full_path)
                elif file_lower.endswith(".jpg") or file_lower.endswith(".jpeg") or file_lower.endswith(".png"):
                    seen_basenames.add(file_lower)
                    valid_imgs.append(full_path)

    if valid_mp4s:
        return valid_mp4s, True
    elif valid_imgs:
        return valid_imgs, False
    return [], False

def build_media_input_args(media_files, is_video, sec_dir, prefix, dur=60.0):
    if not media_files:
        return ["-f", "lavfi", "-i", "color=c=0x1a1008:s=1920x1080:r=30"]

    if len(media_files) == 1:
        single = media_files[0]
        if is_video:
            loops = max(int(dur / 10.0) + 3, 5)
            return ["-stream_loop", str(loops), "-i", single]
        else:
            return ["-loop", "1", "-i", single]

    concat_txt_path = os.path.join(sec_dir, f"{prefix}_loop_list.txt")
    with open(concat_txt_path, "w", encoding="utf-8") as f:
        repeat_count = 30 if is_video else 10
        for _ in range(repeat_count):
            for m in media_files:
                f.write(f"file '{m}'\n")
                if not is_video:
                    f.write("duration 3.0\n")
        if not is_video and media_files:
            f.write(f"file '{media_files[-1]}'\n")

    return ["-f", "concat", "-safe", "0", "-i", concat_txt_path]

def render_cocina_segment(project_dir, folder_name, badge_text, is_intro):
    sec_dir = os.path.join(project_dir, folder_name)
    os.makedirs(sec_dir, exist_ok=True)

    output_file = os.path.join(sec_dir, "segment.mp4")
    audio_file = os.path.join(sec_dir, "audio.wav")
    subtitle_file = os.path.join(sec_dir, "subtitles.ass")

    if not os.path.exists(audio_file):
        return None

    aud_dur = get_audio_duration(audio_file)
    dur = max(aud_dur + 0.5, 4.0)

    badge_png = None
    if badge_text:
        badge_png = os.path.join(sec_dir, "cocina_badge.png")
        create_cocina_badge(badge_text, badge_png, font_size=38, is_main_banner=is_intro)

    sub_filter = ""
    if subtitle_file and os.path.exists(subtitle_file):
        sub_esc = subtitle_file.replace(":", "\\:").replace("'", "\\'")
        sub_filter = f"subtitles='{sub_esc}'"

    bg_music_path = "/home/javierferb/n8n/assets/music/background_music.wav"
    use_bg_music = os.path.exists(bg_music_path)

    is_split_screen = folder_name in ["00_intro", "03_comparison", "08_outro"]

    cmd = ["ffmpeg", "-y", "-loglevel", "error"]

    if is_split_screen:
        media_a, is_vid_a = find_media_for_product(project_dir, "producto_a")
        media_b, is_vid_b = find_media_for_product(project_dir, "producto_b")

        args_a = build_media_input_args(media_a, is_vid_a, sec_dir, "prod_a", dur=dur)
        args_b = build_media_input_args(media_b, is_vid_b, sec_dir, "prod_b", dur=dur)

        cmd.extend(args_a)  # Input 0: Product A
        cmd.extend(args_b)  # Input 1: Product B
        cmd.extend(["-i", audio_file])  # Input 2: Audio narration

        curr_idx = 3
        badge_idx = None
        if badge_png and os.path.exists(badge_png):
            cmd.extend(["-i", badge_png])
            badge_idx = curr_idx
            curr_idx += 1

        bgm_idx = None
        if use_bg_music:
            cmd.extend(["-stream_loop", str(max(int(dur / 60.0) + 2, 3)), "-i", bg_music_path])
            bgm_idx = curr_idx
            curr_idx += 1

        vf = (
            "[0:v]scale=960:1080:force_original_aspect_ratio=increase,crop=960:1080,setsar=1,eq=contrast=1.06:brightness=0.02[leftv];"
            "[1:v]scale=960:1080:force_original_aspect_ratio=increase,crop=960:1080,setsar=1,eq=contrast=1.06:brightness=0.02[rightv];"
            "[leftv][rightv]hstack=inputs=2[basev]"
        )

        if badge_idx is not None:
            vf += f";[basev][{badge_idx}:v]overlay=x=(W-w)/2:y=60[vbadge]"
            v_last = "[vbadge]"
        else:
            v_last = "[basev]"

        if sub_filter:
            vf += f";{v_last}{sub_filter}[outv]"
        else:
            vf += f";{v_last}null[outv]"

    else:
        # Single Product Section — REVIEWER FRAME PIP MODE
        target_prod = "producto_a" if "producto_a" in folder_name else "producto_b"
        media_p, is_vid_p = find_media_for_product(project_dir, target_prod)
        args_p = build_media_input_args(media_p, is_vid_p, sec_dir, target_prod, dur=dur)

        prod_data = {}
        data_json_path = os.path.join(project_dir, "data.json")
        niche_name = "cocina"
        if os.path.exists(data_json_path):
            try:
                with open(data_json_path, "r", encoding="utf-8") as df:
                    d_obj = json.load(df)
                    prod_data = d_obj.get("product_a" if "producto_a" in folder_name else "product_b", {})
                    niche_name = d_obj.get("niche") or d_obj.get("canal_nombre") or "cocina"
            except Exception:
                pass

        label_txt = badge_text if badge_text else ("OPCIÓN A" if "producto_a" in folder_name else "OPCIÓN B")
        card_png = os.path.join(sec_dir, "reviewer_card_vs.png")
        create_reviewer_card_overlay(
            card_png,
            label=label_txt,
            brand=prod_data.get("brand", ""),
            title=prod_data.get("title", ""),
            price=prod_data.get("price", ""),
            rating=str(prod_data.get("rating", "4.5")),
            features=prod_data.get("features"),
            niche=niche_name,
            is_vs=True
        )

        cmd.extend(args_p)  # Input 0: Product Media
        cmd.extend(["-i", audio_file])  # Input 1: Audio narration
        cmd.extend(["-i", card_png])    # Input 2: Reviewer Card Overlay

        curr_idx = 3
        bgm_idx = None
        if use_bg_music:
            cmd.extend(["-stream_loop", str(max(int(dur / 60.0) + 2, 3)), "-i", bg_music_path])
            bgm_idx = curr_idx
            curr_idx += 1

        vf = get_reviewer_video_filter(overlay_idx=2, is_video=is_vid_p, sub_filter=sub_filter)

    aud_idx = 2 if is_split_screen else 1

    if use_bg_music and bgm_idx is not None:
        af = (f"[{aud_idx}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,volume=1.0,asplit[nar1][nar2];"
              f"[{bgm_idx}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,volume=0.20[bgm];"
              f"[bgm][nar1]sidechaincompress=threshold=0.03:ratio=4:attack=80:release=350[ducked_bgm];"
              f"[nar2][ducked_bgm]amix=inputs=2:duration=first:dropout_transition=0:weights=1 1[aout]")
    else:
        af = f"[{aud_idx}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,volume=1.0[aout]"

    full_filter = f"{vf};{af}"

    cmd.extend([
        "-filter_complex", full_filter,
        "-map", "[outv]", "-map", "[aout]",
        "-t", f"{dur:.2f}",
        "-shortest",
        "-max_muxing_queue_size", "1024",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-r", "30",
        output_file
    ])

    try:
        subprocess.run(cmd, check=True, timeout=240)
    except subprocess.TimeoutExpired:
        print(f"[ERROR TIMEOUT] FFmpeg excedió 240s al renderizar {output_file}", file=sys.stderr)
        raise
    return output_file

def render_single_section(project_dir, folder_name, badge_txt, is_intro, mode="full"):
    if mode == "full":
        return render_cocina_segment(project_dir, folder_name, badge_txt, is_intro)
    else:
        sec_dir = os.path.join(project_dir, folder_name)
        out_mp4 = os.path.join(sec_dir, "segment.mp4")
        return out_mp4 if os.path.exists(out_mp4) else None

def render_cocina_project(project_dir, mode="full"):
    data_path = os.path.join(project_dir, "data.json")
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    product_a = data.get("product_a", {})
    product_b = data.get("product_b", {})
    brand_a = product_a.get("brand", "Marca A").upper()
    brand_b = product_b.get("brand", "Marca B").upper()
    price_a = product_a.get("price", "")
    price_b = product_b.get("price", "")

    query = data.get("query", "comparativa cocina").replace("_", " ").upper()

    sections = [
        ("00_intro", f"COCINA TECNOLÓGICA | {brand_a} VS {brand_b}", True),
        ("01_producto_a", f"🍳 {brand_a} - {price_a}", False),
        ("02_producto_b", f"🍳 {brand_b} - {price_b}", False),
        ("03_comparison", f"⚡ {brand_a} VS {brand_b}", True),
        ("08_outro", f"¿CUÁL PREFIERES EN TU COCINA? | COMENTA A o B", True),
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
                    print(f"Error renderizando sección {folder_name}: {e}", file=sys.stderr)
                    raise RuntimeError(f"Fallo crítico renderizando sección obligatoria {folder_name}: {e}")
    else:
        for folder_name, badge_txt, is_intro in sections:
            res_mp4 = render_single_section(project_dir, folder_name, badge_txt, is_intro, mode)
            if res_mp4:
                rendered_segments_map[folder_name] = res_mp4
            else:
                raise RuntimeError(f"Fallo al renderizar sección obligatoria {folder_name}")

    # Comprobación estricta de integridad de todas las secciones
    missing_secs = [f_name for f_name, _, _ in sections if f_name not in rendered_segments_map or not os.path.exists(rendered_segments_map[f_name])]
    if missing_secs:
        raise RuntimeError(f"Integridad incompleta en vídeo Cocina: Faltan secciones clave {missing_secs}")

    rendered_segments = []
    for folder_name, _, _ in sections:
        if folder_name in rendered_segments_map and os.path.exists(rendered_segments_map[folder_name]):
            rendered_segments.append(rendered_segments_map[folder_name])

    if rendered_segments:
        final_mp4 = os.path.join(project_dir, "RENDER_FINAL_AMAZON.mp4")
        concat_list = os.path.join(project_dir, "concat.txt")
        with open(concat_list, "w", encoding="utf-8") as f:
            for seg in rendered_segments:
                f.write(f"file '{seg}'\n")

        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", concat_list,
            "-c", "copy", final_mp4
        ]
        try:
            subprocess.run(cmd, check=True, timeout=180)
        except subprocess.TimeoutExpired:
            print(f"[ERROR TIMEOUT] Concat final excedió 180s en {final_mp4}", file=sys.stderr)
            raise

        final_dur = get_audio_duration(final_mp4)
        if final_dur < 240.0:
            raise RuntimeError(f"Duración final del vídeo Cocina insuficiente ({final_dur:.1f}s < 240.0s). Se requiere un mínimo estricto de 4 minutos.")

        alt_mp4 = os.path.join(project_dir, "final_output.mp4")
        if os.path.exists(final_mp4):
            subprocess.run(["cp", final_mp4, alt_mp4])

        print(json.dumps({"status": "rendered_cocina", "final_output": final_mp4, "duration": round(final_dur, 2), "segments_count": len(rendered_segments)}))
        return final_mp4
    else:
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Renderizador 16:9 Cocina Tecnológica")
    parser.add_argument("project_dir", help="Directorio del proyecto")
    parser.add_argument("--mode", default="full", choices=["full", "concat"], help="Modo de renderizado")
    args = parser.parse_args()

    project_dir = os.path.abspath(args.project_dir)
    render_cocina_project(project_dir, mode=args.mode)

if __name__ == "__main__":
    main()
