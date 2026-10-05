from reviewer_frame_engine import create_reviewer_card_overlay, get_reviewer_video_filter
#!/usr/bin/env python3
import sys
import os
import json
import subprocess
import argparse
import concurrent.futures

from PIL import Image, ImageDraw, ImageFont

def create_text_badge(text, output_png_path, font_size=34, is_intro=False):
    font_main = ImageFont.truetype('/usr/share/fonts/liberation/LiberationSans-Bold.ttf', font_size)
    font_emoji = ImageFont.truetype('/usr/share/fonts/noto/NotoColorEmoji.ttf', 109)

    items = []
    if is_intro:
        items.append(('emoji', '🏆 '))
        items.append(('text', text))
    else:
        items.append(('emoji', '🔥 '))
        items.append(('text', text))

    drawn_parts = []
    total_w = 0
    max_h = 0

    for kind, content in items:
        if kind == 'emoji':
            icon_img = Image.new('RGBA', (130, 130), (0, 0, 0, 0))
            idraw = ImageDraw.Draw(icon_img)
            idraw.text((0, 0), content.strip(), font=font_emoji, embedded_color=True)
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

    pad_x, pad_y = (45, 22) if is_intro else (35, 18)
    bg_w = total_w + pad_x * 2
    bg_h = max_h + pad_y * 2

    canvas = Image.new('RGBA', (bg_w, bg_h), (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(canvas)

    border_color = (255, 215, 0, 255) if is_intro else (255, 255, 255, 220)
    bg_fill = (0, 0, 0, 215)
    text_color = (255, 230, 0, 255) if is_intro else (255, 255, 255, 255)

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

def render_independent_segment(media_file, audio_file, subtitle_file, output_file, is_video=True, rank=None, title="", price="", rating="", min_duration=0.0, sfx_reveal=None, sfx_swoosh=None, brand="", features=None, niche="cocina"):
    aud_dur = get_audio_duration(audio_file)
    dur = max(aud_dur + 5.0, min_duration)

    title_clean = title[:45].replace("'", "").replace('"', '')
    overlay_txt = f"#{rank} | {title_clean} - {price} [{rating} / 5]" if rank else ""

    big_badge_png = None
    top_badge_png = None
    if overlay_txt:
        seg_dir = os.path.dirname(output_file)
        big_badge_png = os.path.join(seg_dir, "overlay_badge_big.png")
        top_badge_png = os.path.join(seg_dir, "overlay_badge_top.png")
        create_text_badge(overlay_txt, big_badge_png, font_size=42, is_intro=False)
        create_text_badge(overlay_txt, top_badge_png, font_size=28, is_intro=False)

    sub_filter = ""
    if subtitle_file and os.path.exists(subtitle_file):
        sub_esc = subtitle_file.replace(":", "\\:").replace("'", "\\'")
        sub_filter = f"subtitles='{sub_esc}'"

    # --- OPTION 2 REVIEWER FRAME PIP (ANTI-COPYRIGHT FAIR USE) ---
    if rank:
        seg_dir = os.path.dirname(output_file)
        card_overlay_png = os.path.join(seg_dir, f"reviewer_card_{rank}.png")
        create_reviewer_card_overlay(
            card_overlay_png,
            rank=str(rank),
            brand=brand,
            title=title,
            price=price,
            rating=str(rating),
            features=features,
            niche=niche,
            is_vs=False
        )

        video_filter = get_reviewer_video_filter(overlay_idx=2, is_video=is_video, sub_filter=sub_filter)

        if is_video:
            media_input_args = ["-stream_loop", "-1", "-i", media_file]
        else:
            media_input_args = ["-loop", "1", "-i", media_file]

        bg_music_path = "/home/javierferb/n8n/assets/music/background_music.wav"
        use_bg_music = os.path.exists(bg_music_path)
        use_sfx = sfx_reveal and sfx_swoosh and os.path.exists(sfx_reveal) and os.path.exists(sfx_swoosh)
        sfx_input_args = ["-i", sfx_reveal, "-i", sfx_swoosh] if use_sfx else []
        bg_input_args = ["-stream_loop", "-1", "-i", bg_music_path] if use_bg_music else []

        def build_audio_reviewer(nar_idx, bg_idx=None, rev_idx=None, sw_idx=None, swoosh_delay_ms=1200):
            parts = [f"[{nar_idx}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,volume=1.0[nar]"]
            labels = ["[nar]"]
            if rev_idx is not None:
                parts.append(f"[{rev_idx}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,adelay=0|0,volume=3.0[sfx1]")
                parts.append(f"[{sw_idx}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,adelay={swoosh_delay_ms}|{swoosh_delay_ms},volume=3.0[sfx2]")
                labels += ["[sfx1]", "[sfx2]"]
            if bg_idx is not None:
                parts.append(f"[{bg_idx}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,volume=0.15[bgm]")
                labels.append("[bgm]")
            parts.append(f"{''.join(labels)}amix=inputs={len(labels)}:duration=longest:dropout_transition=2:normalize=0[outa]")
            return ";".join(parts)

        if use_sfx:
            bg_idx = 5 if use_bg_music else None
            audio_filter = build_audio_reviewer(1, bg_idx=bg_idx, rev_idx=3, sw_idx=4)
        else:
            bg_idx = 3 if use_bg_music else None
            audio_filter = build_audio_reviewer(1, bg_idx=bg_idx)

        filter_complex = f"{audio_filter};{video_filter}"

        cmd = [
            "ffmpeg", "-y",
            *media_input_args,
            "-i", audio_file,
            "-i", card_overlay_png,
            *sfx_input_args,
            *bg_input_args,
            "-t", f"{dur:.2f}",
            "-r", "25",
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "[outa]",
            "-pix_fmt", "yuv420p",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
            "-ar", "44100", "-ac", "2", "-c:a", "aac", "-b:a", "192k",
            output_file
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return

    # Option 2 Anti-Content ID transformation filter chain (applied to videos and static images):
    # 1. crop=iw*0.90:ih*0.90: 10% center zoom crop to break exact frame matching
    # 2. eq=contrast=1.10:brightness=0.03:saturation=1.15: Distinctive color and tone shift
    color_crop_filter = "crop=iw*0.90:ih*0.90,eq=contrast=1.10:brightness=0.03:saturation=1.15"
    if is_video:
        anti_cid_filters = f"setpts=0.96*PTS,{color_crop_filter}"
    else:
        anti_cid_filters = color_crop_filter

    vf_base = f"{anti_cid_filters},split[main][bg];[bg]scale=480:270:force_original_aspect_ratio=increase,crop=480:270,boxblur=5:2,scale=1920:1080:flags=bicubic[bglur];[main]scale=1920:1080:force_original_aspect_ratio=decrease[fg];[bglur][fg]overlay=(W-w)/2:(H-h)/2"

    # Use correct loop flag: -stream_loop for videos, -loop 1 for images
    if is_video:
        media_input_args = ["-stream_loop", "-1", "-i", media_file]
    else:
        media_input_args = ["-loop", "1", "-i", media_file]

    bg_music_path = "/home/javierferb/n8n/assets/music/background_music.wav"
    use_bg_music = os.path.exists(bg_music_path)

    use_sfx = sfx_reveal and sfx_swoosh and os.path.exists(sfx_reveal) and os.path.exists(sfx_swoosh) and bool(overlay_txt)
    sfx_input_args = ["-i", sfx_reveal, "-i", sfx_swoosh] if use_sfx else []

    # Input index accounting (shifts when bg_music is present)
    # With badges + sfx:  0=media  1=narration  2=big_badge  3=top_badge  4=sfx_reveal  5=sfx_swoosh  [6=bg_music]
    # With badges, no sfx: 0=media  1=narration  2=big_badge  3=top_badge  [4=bg_music]
    # No badges + sfx:    0=media  1=narration  2=sfx_reveal  3=sfx_swoosh  [4=bg_music]
    # No badges, no sfx:  0=media  1=narration  [2=bg_music]

    def build_audio_filter_full(nar_idx, bg_idx=None, rev_idx=None, sw_idx=None, swoosh_delay_ms=1200):
        """Mix narration + optional SFX + optional background music. Duration = longest input."""
        parts = []
        labels = []

        parts.append(f"[{nar_idx}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,volume=1.0[nar]")
        labels.append("[nar]")

        if rev_idx is not None:
            parts.append(f"[{rev_idx}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,adelay=0|0,volume=3.0[sfx1]")
            parts.append(f"[{sw_idx}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,adelay={swoosh_delay_ms}|{swoosh_delay_ms},volume=3.0[sfx2]")
            labels += ["[sfx1]", "[sfx2]"]

        if bg_idx is not None:
            parts.append(f"[{bg_idx}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,volume=0.15[bgm]")
            labels.append("[bgm]")

        n = len(labels)
        parts.append(f"{''.join(labels)}amix=inputs={n}:duration=longest:dropout_transition=2:normalize=0[outa]")
        return ";".join(parts)

    if big_badge_png and os.path.exists(big_badge_png) and top_badge_png and os.path.exists(top_badge_png):
        # 0s - 1.2s: center big product badge
        # 1.2s - 1.8s: transition from center to top-left (40, 40)
        filter_complex = (
            f"[0:v]{vf_base}[bg_vid];"
            f"[bg_vid][2:v]overlay=x='if(lte(t,1.2),(W-w)/2,max(40,(W-w)/2-(t-1.2)*1200))':y='if(lte(t,1.2),(H-h)/2,max(40,(H-h)/2-(t-1.2)*700))':enable='lte(t,1.8)'[vid1];"
            f"[vid1][3:v]overlay=40:40:enable='gte(t,1.8)'"
        )
        if sub_filter:
            filter_complex += f",{sub_filter}"
        filter_complex += "[outv]"

        # Input index: 0=media  1=nar  2=big_badge  3=top_badge  [4=sfx_rev  5=sfx_sw]  [last=bg_music]
        if use_sfx:
            bg_idx = 6 if use_sfx else 4
            audio_filter = build_audio_filter_full(1, bg_idx=(bg_idx if use_bg_music else None), rev_idx=4, sw_idx=5)
        else:
            audio_filter = build_audio_filter_full(1, bg_idx=(4 if use_bg_music else None))
        filter_complex = audio_filter + ";" + filter_complex

        bg_input_args = ["-stream_loop", "-1", "-i", bg_music_path] if use_bg_music else []

        cmd = [
            "ffmpeg", "-y",
            *media_input_args,
            "-i", audio_file,
            "-i", big_badge_png,
            "-i", top_badge_png,
            *sfx_input_args,
            *bg_input_args,
            "-t", f"{dur:.2f}",
            "-r", "25",
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "[outa]",
            "-pix_fmt", "yuv420p",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
            "-ar", "44100", "-ac", "2", "-c:a", "aac", "-b:a", "192k",
            output_file
        ]
    else:
        vf_chain = vf_base + (f",{sub_filter}" if sub_filter else "")

        # Input index: 0=media  1=nar  [2=sfx_rev  3=sfx_sw]  [last=bg_music]
        if use_sfx:
            bg_idx = 4 if use_bg_music else None
            audio_filter = build_audio_filter_full(1, bg_idx=bg_idx, rev_idx=2, sw_idx=3)
        else:
            bg_idx = 2 if use_bg_music else None
            audio_filter = build_audio_filter_full(1, bg_idx=bg_idx)

        bg_input_args = ["-stream_loop", "-1", "-i", bg_music_path] if use_bg_music else []

        cmd = [
            "ffmpeg", "-y",
            *media_input_args,
            "-i", audio_file,
            *sfx_input_args,
            *bg_input_args,
            "-t", f"{dur:.2f}",
            "-r", "25",
            "-vf", vf_chain,
            "-filter_complex", audio_filter,
            "-map", "0:v:0",
            "-map", "[outa]",
            "-pix_fmt", "yuv420p",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
            "-ar", "44100", "-ac", "2", "-c:a", "aac", "-b:a", "192k",
            output_file
        ]

    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)


def concatenate_all_segments(project_dir, segment_files, final_output):
    missing_segments = [s for s in segment_files if not os.path.exists(s) or os.path.getsize(s) < 100000]
    if missing_segments:
        raise RuntimeError(f"Error: Vídeo incompleto. Faltan o están dañados los siguientes segmentos: {missing_segments}")

    concat_list_path = os.path.join(project_dir, "concat_list.txt")
    with open(concat_list_path, 'w', encoding='utf-8') as f:
        for seg in segment_files:
            f.write(f"file '{seg}'\n")

    # Concat streams directly without re-encoding
    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_list_path,
        "-c", "copy",
        final_output
    ]
    subprocess.run(cmd_concat, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    final_dur = get_audio_duration(final_output)
    if final_dur < 240.0:
        raise RuntimeError(f"Duración final del vídeo horizontal insuficiente ({final_dur:.1f}s < 240.0s). Se requiere un mínimo estricto de 4 minutos.")
    return final_output


def render_hook_only(project_dir):
    data_json_path = os.path.join(project_dir, "data.json")
    with open(data_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    intro_dir = os.path.join(project_dir, "00_intro")
    os.makedirs(intro_dir, exist_ok=True)

    hook_audio = os.path.join(intro_dir, "audio.wav")
    if not os.path.exists(hook_audio):
        alt_audio = os.path.join(project_dir, "audio_hook.wav")
        if os.path.exists(alt_audio):
            hook_audio = alt_audio
    hook_sub = os.path.join(intro_dir, "subtitles.ass")
    hook_seg = os.path.join(intro_dir, "segment.mp4")
    if os.path.exists(hook_seg) and os.path.getsize(hook_seg) > 100000 and get_audio_duration(hook_seg) > 10.0:
        print(f"[CACHE RENDER] Reutilizando intro existente: {hook_seg}", flush=True)
        return {"status": "success", "segment": "00_intro/segment.mp4", "file": hook_seg}

    aud_dur = get_audio_duration(hook_audio)
    total_dur = aud_dur

    products = data.get("products", [])
    valid_vids = []

    for p in products:
        rank = p["rank"]
        folder_name = p.get("folder", f"{rank:02d}_producto_{rank}")
        prod_video = os.path.join(project_dir, folder_name, f"product_{rank}.mp4")
        if os.path.exists(prod_video):
            check_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", prod_video]
            res = subprocess.run(check_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0 and res.stdout.strip():
                try:
                    if float(res.stdout.strip()) > 3.0:
                        valid_vids.append(prod_video)
                except ValueError:
                    pass

    if not valid_vids:
        # Fallback to static image if no product videos are found
        hook_img = None
        if products and products[0].get("image_file"):
            hook_img = os.path.join(project_dir, products[0]["image_file"])

        query_txt = data.get("query", "productos").upper().strip()
        hook_title_txt = f"TOP 7 MEJORES {query_txt}"

        if not hook_img or not os.path.exists(hook_img):
            hook_img = os.path.join(intro_dir, "fallback_bg.jpg")
            img = Image.new("RGB", (1920, 1080), color=(20, 20, 20))
            img.save(hook_img)

        render_independent_segment(hook_img, hook_audio, hook_sub, hook_seg, is_video=False, title=hook_title_txt, min_duration=total_dur)
        return {"status": "success", "segment": "00_intro/segment.mp4", "file": hook_seg}

    # Slice ~1s teaser clips from each available product video
    clip_dur = total_dur / len(valid_vids)
    temp_clips = []

    for idx, vfile in enumerate(valid_vids):
        clip_path = os.path.join(intro_dir, f"teaser_{idx}.mp4")
        # Extract clip with blurred background scale
        vf_clip = "split[main][bg];[bg]scale=480:270:force_original_aspect_ratio=increase,crop=480:270,boxblur=5:2,scale=1920:1080:flags=bicubic[bglur];[main]scale=1920:1080:force_original_aspect_ratio=decrease[fg];[bglur][fg]overlay=(W-w)/2:(H-h)/2"
        cmd = [
            "ffmpeg", "-y",
            "-ss", "2",
            "-i", vfile,
            "-t", f"{clip_dur:.2f}",
            "-r", "25",
            "-vf", vf_clip,
            "-an",
            "-pix_fmt", "yuv420p",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
            clip_path
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        temp_clips.append(clip_path)

    # Concat teaser clips into a continuous background video
    concat_list_intro = os.path.join(intro_dir, "concat_teaser.txt")
    with open(concat_list_intro, "w", encoding="utf-8") as f:
        for cpath in temp_clips:
            f.write(f"file '{cpath}'\n")

    raw_teaser = os.path.join(intro_dir, "raw_teaser.mp4")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_list_intro,
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        raw_teaser
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    # Dynamic Intro title banners (Big for center, regular for top)
    query_txt = data.get("query", "productos").upper().strip()
    num_products = len(products) if products else 7
    banner_txt = f"TOP {num_products} MEJORES {query_txt} DE AMAZON"

    big_badge_png = os.path.join(intro_dir, "intro_badge_big.png")
    top_badge_png = os.path.join(intro_dir, "intro_badge_top.png")
    create_text_badge(banner_txt, big_badge_png, font_size=46, is_intro=True)
    create_text_badge(banner_txt, top_badge_png, font_size=32, is_intro=True)

    sub_esc = hook_sub.replace(":", "\\:").replace("'", "\\'") if os.path.exists(hook_sub) else ""
    sub_filter = f"subtitles='{sub_esc}'" if sub_esc else ""

    # SFX paths
    sfx_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "sfx")
    sfx_reveal = os.path.join(sfx_dir, "sfx_reveal.wav")
    sfx_swoosh = os.path.join(sfx_dir, "sfx_swoosh.wav")
    use_sfx = os.path.exists(sfx_reveal) and os.path.exists(sfx_swoosh)

    # Animated transition: center big banner for first 1.5s, smooth y move + scale transition to top header
    # 0s to 1.5s: centered big banner at (H-h)/2
    # 1.5s to 2.2s: transition y from (H-h)/2 to 60, scale down to top banner
    video_filter = (
        f"[0:v][2:v]overlay=x='(W-w)/2':y='if(lte(t,1.5),(H-h)/2,max(60,(H-h)/2-(t-1.5)*650))':enable='lte(t,2.2)'[vid1];"
        f"[vid1][3:v]overlay=x='(W-w)/2':y=60:enable='gte(t,2.2)'"
    )
    if sub_filter:
        video_filter += f",{sub_filter}"
    video_filter += "[outv]"

    if use_sfx:
        # Inputs: 0=raw_teaser(v), 1=hook_audio(a), 2=big_badge(v), 3=top_badge(v), 4=sfx_reveal(a), 5=sfx_swoosh(a)
        # sfx_reveal at t=0ms, sfx_swoosh at t=1500ms
        audio_filter = (
            "[1:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,volume=1.0[nar];"
            "[4:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,adelay=0|0,volume=3.0[sfx1];"
            "[5:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,adelay=1500|1500,volume=3.0[sfx2];"
            "[nar][sfx1][sfx2]amix=inputs=3:duration=first:dropout_transition=0:weights=1 1 1[outa]"
        )
        filter_complex = f"{audio_filter};{video_filter}"
        sfx_inputs = ["-i", sfx_reveal, "-i", sfx_swoosh]
        audio_map = ["[outa]"]
    else:
        filter_complex = video_filter
        sfx_inputs = []
        audio_map = ["1:a:0"]

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", raw_teaser,
        "-i", hook_audio,
        "-i", big_badge_png,
        "-i", top_badge_png,
        *sfx_inputs,
        "-t", f"{total_dur:.2f}",
        "-r", "25",
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", *audio_map,
        "-pix_fmt", "yuv420p",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
        "-ar", "44100", "-ac", "2", "-c:a", "aac", "-b:a", "192k",
        hook_seg
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    # Cleanup temporary files
    for cpath in temp_clips:
        if os.path.exists(cpath):
            os.remove(cpath)
    if os.path.exists(raw_teaser):
        os.remove(raw_teaser)
    if os.path.exists(concat_list_intro):
        os.remove(concat_list_intro)

    return {"status": "success", "segment": "00_intro/segment.mp4", "file": hook_seg}

def render_products_only(project_dir):
    data_json_path = os.path.join(project_dir, "data.json")
    with open(data_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # SFX paths (global assets)
    sfx_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "sfx")
    sfx_reveal_path = os.path.join(sfx_dir, "sfx_reveal.wav")
    sfx_swoosh_path = os.path.join(sfx_dir, "sfx_swoosh.wav")

    products = data.get("products", [])

    def process_single_product(p):
        rank = p["rank"]
        folder_name = p.get("folder", f"{rank:02d}_producto_{rank}")
        prod_dir = os.path.join(project_dir, folder_name)
        os.makedirs(prod_dir, exist_ok=True)

        audio_path = os.path.join(prod_dir, "audio.wav")
        if not os.path.exists(audio_path):
            alt_audio = os.path.join(project_dir, f"audio_product_{rank}.wav")
            if os.path.exists(alt_audio):
                audio_path = alt_audio
        sub_path = os.path.join(prod_dir, "subtitles.ass")
        seg_out = os.path.join(prod_dir, "segment.mp4")

        video_rel = p.get("video_file")
        image_rel = p.get("image_file")

        if video_rel and os.path.exists(os.path.join(project_dir, video_rel)):
            vfull = os.path.join(project_dir, video_rel)
            check_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", vfull]
            res = subprocess.run(check_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0 and res.stdout.strip():
                media_path = vfull
                is_vid = True
            elif image_rel and os.path.exists(os.path.join(project_dir, image_rel)):
                media_path = os.path.join(project_dir, image_rel)
                is_vid = False
            else:
                media_path = None
                is_vid = False
        elif image_rel and os.path.exists(os.path.join(project_dir, image_rel)):
            media_path = os.path.join(project_dir, image_rel)
            is_vid = False
        else:
            media_path = None
            is_vid = False

        if os.path.exists(seg_out) and os.path.getsize(seg_out) > 100000 and get_audio_duration(seg_out) > 10.0:
            print(f"[CACHE RENDER] Reutilizando producto {rank}: {seg_out}", flush=True)
            return (rank, seg_out)

        if media_path is None:
            print(f"[SKIP] Rank {rank} skipped — no video or image available.", flush=True)
            return None

        render_independent_segment(
            media_file=media_path,
            audio_file=audio_path,
            subtitle_file=sub_path,
            output_file=seg_out,
            is_video=is_vid,
            rank=rank,
            title=p.get("title", ""),
            price=p.get("price", ""),
            rating=p.get("rating", ""),
            min_duration=0.0,
            sfx_reveal=sfx_reveal_path,
            sfx_swoosh=sfx_swoosh_path,
            brand=p.get("brand", ""),
            features=p.get("features", []),
            niche=data.get("niche") or data.get("category") or data.get("canal_nombre") or "cocina"
        )
        return (rank, seg_out)

    rendered_map = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_to_product = {executor.submit(process_single_product, p): p for p in products}
        for future in concurrent.futures.as_completed(future_to_product):
            res = future.result()
            if res:
                rank, seg_out = res
                rendered_map[rank] = seg_out

    rendered = [rendered_map[p["rank"]] for p in products if p["rank"] in rendered_map]
    return {"status": "success", "rendered_products_count": len(rendered), "files": rendered}

def render_outro_only(project_dir):
    data_json_path = os.path.join(project_dir, "data.json")
    with open(data_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    outro_dir = os.path.join(project_dir, "08_outro")
    os.makedirs(outro_dir, exist_ok=True)

    outro_audio = os.path.join(outro_dir, "audio.wav")
    if not os.path.exists(outro_audio):
        alt_audio = os.path.join(project_dir, "audio_outro.wav")
        if os.path.exists(alt_audio):
            outro_audio = alt_audio
    outro_sub = os.path.join(outro_dir, "subtitles.ass")
    outro_seg = os.path.join(outro_dir, "segment.mp4")
    if os.path.exists(outro_seg) and os.path.getsize(outro_seg) > 100000 and get_audio_duration(outro_seg) > 10.0:
        print(f"[CACHE RENDER] Reutilizando outro existente: {outro_seg}", flush=True)
        return {"status": "success", "segment": "08_outro/segment.mp4", "file": outro_seg}

    products = data.get("products", [])
    last_img = None
    if products and products[-1].get("image_file"):
        last_img = os.path.join(project_dir, products[-1]["image_file"])

    render_independent_segment(last_img, outro_audio, outro_sub, outro_seg, is_video=False, title="SUSCRÍBETE Y VER ENLACES ABAJO", min_duration=0.0)
    return {"status": "success", "segment": "08_outro/segment.mp4", "file": outro_seg}

def concat_final_only(project_dir):
    data_json_path = os.path.join(project_dir, "data.json")
    with open(data_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    products = data.get("products", [])
    segment_files = [os.path.join(project_dir, "00_intro", "segment.mp4")]
    for p in sorted(products, key=lambda x: x["rank"], reverse=True):
        rank = p["rank"]
        folder_name = p.get("folder", f"{rank:02d}_producto_{rank}")
        segment_files.append(os.path.join(project_dir, folder_name, "segment.mp4"))
    segment_files.append(os.path.join(project_dir, "08_outro", "segment.mp4"))

    final_mp4 = os.path.join(project_dir, "RENDER_FINAL_AMAZON.mp4")
    concatenate_all_segments(project_dir, segment_files, final_mp4)

    return {"status": "success", "final_video": final_mp4, "resolution": "1920x1080"}

def main(project_dir, mode="all"):
    if mode == "hook":
        return render_hook_only(project_dir)
    elif mode == "products":
        return render_products_only(project_dir)
    elif mode == "outro":
        return render_outro_only(project_dir)
    elif mode == "concat":
        return concat_final_only(project_dir)
    else:
        render_hook_only(project_dir)
        render_products_only(project_dir)
        render_outro_only(project_dir)
        return concat_final_only(project_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render Amazon Product Video (16:9 Horizontal)")
    parser.add_argument("--project_dir", required=True, help="Directorio del proyecto")
    parser.add_argument("--mode", default="all", choices=["all", "hook", "products", "outro", "concat"], help="Paso específico de renderizado")
    args = parser.parse_args()

    res = main(args.project_dir, args.mode)
    print(json.dumps(res, ensure_ascii=False))
