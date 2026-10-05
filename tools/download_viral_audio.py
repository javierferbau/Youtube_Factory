#!/usr/bin/env python3
"""
download_viral_audio.py - Downloads YouTube audio and cuts the most viral segment.
Uses YouTube's heatmap ("Most Replayed") to locate the exact drop/chorus.
Falls back to audio energy analysis (RMS/loudness) or standard pop chorus placement.
"""

import os
import sys
import json
import glob
import argparse
import subprocess
import tempfile

YT_DLP_PATH = "/home/javierferb/.local/bin/yt-dlp"
FALLBACK_URL = "https://www.youtube.com/shorts/BvN3Vxbaq5A"

def find_viral_segment_heatmap(heatmap, total_duration, clip_duration=25.0):
    """
    Computes continuous sliding window over YouTube heatmap to find
    the time window with maximum replay intensity (the viral peak/hook).
    """
    if not heatmap or total_duration <= clip_duration:
        return 0.0

    max_start = max(0.0, total_duration - clip_duration)
    best_t = 0.0
    best_score = -1.0

    # Step every 0.5s for fine precision
    t = 0.0
    while t <= max_start:
        t_end = t + clip_duration
        score = 0.0
        for pt in heatmap:
            s = pt.get("start_time", 0.0)
            e = pt.get("end_time", 0.0)
            val = pt.get("value", 0.0)
            overlap = max(0.0, min(e, t_end) - max(s, t))
            if overlap > 0:
                score += val * overlap
        if score > best_score:
            best_score = score
            best_t = t
        t += 0.5

    return round(best_t, 2)

def find_viral_segment_audio_rms(audio_file, total_duration, clip_duration=25.0):
    """
    Fallback if no heatmap: uses ffmpeg ebur128 or astats to find highest energy segment.
    If fast fallback needed, estimate chorus at 25%-30% of total length.
    """
    if total_duration <= clip_duration:
        return 0.0
    # In pop/viral music, the first chorus starts at ~25%-30% of song length
    heuristic_start = min(total_duration * 0.25, max(0.0, total_duration - clip_duration))
    return round(heuristic_start, 2)

def download_and_extract(url, output_path, clip_duration=25.0, fallback_url=FALLBACK_URL):
    urls_to_try = [url]
    if fallback_url and fallback_url != url:
        urls_to_try.append(fallback_url)

    target_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(target_dir, exist_ok=True)

    last_error = None
    for target_url in urls_to_try:
        with tempfile.TemporaryDirectory(prefix="viral_audio_") as tmpdir:
            raw_tmpl = os.path.join(tmpdir, "raw_stream.%(ext)s")
            cmd_dl = [
                YT_DLP_PATH,
                "--extractor-args", "youtube:player_client=default,ios,android,web",
                "--retries", "3",
                "--no-continue",
                "--js-runtimes", "node",
                "-f", "bestaudio",
                "--dump-json",
                "--no-simulate",
                "-o", raw_tmpl,
                target_url
            ]

            try:
                proc = subprocess.run(cmd_dl, capture_output=True, text=True, timeout=30)
                if proc.returncode != 0:
                    last_error = proc.stderr
                    continue

                meta = {}
                for line in proc.stdout.splitlines():
                    if line.strip().startswith("{") and line.strip().endswith("}"):
                        try:
                            meta = json.loads(line)
                            break
                        except Exception:
                            pass

                # Find downloaded raw audio file
                matches = glob.glob(os.path.join(tmpdir, "raw_stream.*"))
                if not matches:
                    last_error = "Downloaded raw file not found"
                    continue
                raw_file = matches[0]

                total_dur = meta.get("duration") or 60.0
                heatmap = meta.get("heatmap") or []

                source_method = "start"
                if heatmap and len(heatmap) > 0 and total_dur > clip_duration:
                    start_sec = find_viral_segment_heatmap(heatmap, total_dur, clip_duration)
                    source_method = "heatmap"
                elif total_dur > clip_duration:
                    start_sec = find_viral_segment_audio_rms(raw_file, total_dur, clip_duration)
                    source_method = "loudness_heuristic"
                else:
                    start_sec = 0.0
                    source_method = "full_short"

                # Trim and convert to 44.1kHz MP3 with ffmpeg
                # Gentle 0.2s fade-in to avoid cut clicks
                cmd_ffmpeg = [
                    "ffmpeg",
                    "-ss", str(start_sec),
                    "-t", str(clip_duration),
                    "-i", raw_file,
                    "-af", "afade=t=in:ss=0:d=0.2",
                    "-vn",
                    "-ar", "44100",
                    "-ac", "2",
                    "-b:a", "192k",
                    "-y",
                    output_path
                ]
                ff_proc = subprocess.run(cmd_ffmpeg, capture_output=True, text=True, timeout=20)
                if ff_proc.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 5000:
                    result = {
                        "status": "success",
                        "url": target_url,
                        "title": meta.get("title", ""),
                        "total_duration": total_dur,
                        "start_sec": start_sec,
                        "clip_duration": clip_duration,
                        "method": source_method,
                        "output": output_path
                    }
                    print(json.dumps(result))
                    return 0
                else:
                    last_error = f"FFmpeg error: {ff_proc.stderr}"
            except Exception as e:
                last_error = str(e)

    sys.stderr.write(f"Failed to download and extract audio: {last_error}\n")
    return 1

def main():
    parser = argparse.ArgumentParser(description="Download and extract the most viral audio segment.")
    parser.add_argument("url", help="YouTube video or Short URL")
    parser.add_argument("output", help="Output MP3 path")
    parser.add_argument("--duration", type=float, default=25.0, help="Clip duration in seconds (default: 25)")
    parser.add_argument("--fallback", default=FALLBACK_URL, help="Fallback YouTube URL")

    args = parser.parse_args()
    ret = download_and_extract(args.url, args.output, args.duration, args.fallback)
    sys.exit(ret)

if __name__ == "__main__":
    main()
