#!/usr/bin/env python3
"""
FFprobe Media Inspector
Safely probes video and audio files to return structured metadata in JSON.
"""

import sys
import json
import subprocess

def probe_file(file_path):
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        
        summary = {
            "filename": data.get("format", {}).get("filename"),
            "duration": float(data.get("format", {}).get("duration", 0)),
            "size_mb": round(int(data.get("format", {}).get("size", 0)) / (1024 * 1024), 2),
            "bit_rate_kbps": round(int(data.get("format", {}).get("bit_rate", 0)) / 1000, 2),
            "streams": []
        }
        for s in data.get("streams", []):
            st = {
                "index": s.get("index"),
                "codec_type": s.get("codec_type"),
                "codec_name": s.get("codec_name"),
            }
            if s.get("codec_type") == "video":
                st["width"] = s.get("width")
                st["height"] = s.get("height")
                st["r_frame_rate"] = s.get("r_frame_rate")
                st["aspect_ratio"] = s.get("display_aspect_ratio")
            elif s.get("codec_type") == "audio":
                st["channels"] = s.get("channels")
                st["sample_rate"] = s.get("sample_rate")
            summary["streams"].append(st)
            
        print(json.dumps(summary, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ffprobe_helper.py <path_to_media_file>")
        sys.exit(1)
    probe_file(sys.argv[1])
