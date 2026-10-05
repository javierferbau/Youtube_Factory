#!/usr/bin/env python3
"""
delete_youtube_video.py
Elimina vídeos erróneos de YouTube usando el workflow oficial autenticado de n8n
(usando las credenciales OAuth2 oficiales de cada uno de los 6 canales de afiliados).
"""

import sys
import os
import json
import argparse
import urllib.request
import urllib.error

WEBHOOK_URL = "http://localhost:5678/webhook/delete-yt-video"

def delete_video(channel, video_id):
    channel = channel.lower().strip()
    video_id = video_id.strip()

    payload = {
        "channel": channel,
        "video_id": video_id
    }

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        WEBHOOK_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {"success": True, "data": data}
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        return {"success": False, "error": f"HTTP {e.code}: {err_msg}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Elimina un vídeo de YouTube usando OAuth2 oficial.")
    parser.add_argument("--channel", required=True, choices=["cocina", "limpieza", "libreria", "zapateria", "barberia", "taller"], help="Canal de YouTube")
    parser.add_argument("--video_id", required=True, help="ID del vídeo de YouTube a eliminar")
    args = parser.parse_args()

    print(f"🗑️ Solicitando eliminación del vídeo '{args.video_id}' en el canal '{args.channel}'...")
    res = delete_video(args.channel, args.video_id)
    if res["success"]:
        print(f"✅ VÍDEO ELIMINADO EXITOSAMENTE DE YOUTUBE: {json.dumps(res['data'], indent=2)}")
        sys.exit(0)
    else:
        print(f"❌ Error al eliminar el vídeo: {res['error']}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
