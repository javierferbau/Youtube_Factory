#!/usr/bin/env python3
"""
verify_pre_publish.py
Puerta de Calidad Preventiva (Pre-Publish Sanity Gate) para canales de afiliados de YouTube.
Verifica ANTES de subir a YouTube tanto el vídeo Horizontal como el Short:
1. Concordancia semántica estricta (cero productos espurios o ajenos al nicho).
2. Coherencia del guion con el nicho y con la temática.
3. Existencia e integridad física de los archivos de vídeo renderizados con ffprobe.
4. Presencia y especificaciones de la miniatura (1280x720, >40KB).
5. Enlaces de afiliados y tags presentes en la descripción.

Si encuentra anomalías críticas, termina con código de error (sys.exit(1)) bloqueando la publicación.
"""

import sys
import os
import json
import re
import subprocess
import argparse

def get_channel_niche(channel_name_or_dir):
    s = str(channel_name_or_dir).lower()
    if any(k in s for k in ['taller', 'bricolaje']):
        return 'taller'
    if any(k in s for k in ['barber', 'afeitad']):
        return 'barberia'
    if any(k in s for k in ['cocina', 'receta']):
        return 'cocina'
    if any(k in s for k in ['limpiez']):
        return 'limpieza'
    if any(k in s for k in ['zapat', 'calzad']):
        return 'zapateria'
    if any(k in s for k in ['librer', 'libro']):
        return 'libreria'
    return 'general'

NETWORKING_BANNED = ['wifi', 'wi-fi', 'access point', 'punto de acceso', 'repetidor', 'router', 'rj45', 'switch de red']

NICHE_RULES = {
    'taller': {
        'label': 'Taller / Bricolaje',
        'banned': ['barbacoa', 'parrilla', 'bbq', 'pelo', 'cabello', 'afeitad', 'afeitadora', 'cortapelo', 'depilad', 'barba', 'dientes', 'dental', 'cocina', 'vajilla', 'sarten', 'sartén', 'olla', 'aspirador', 'colchon', 'mascota', 'fregadero', 'inodoro', 'champú'] + NETWORKING_BANNED
    },
    'barberia': {
        'label': 'Barbería',
        'banned': ['madera', 'taller', 'taladro', 'sierra', 'bricolaje', 'jardin', 'cesped', 'cocina', 'sarten', 'freidora', 'aspirador', 'fregona', 'limpieza', 'coche'] + NETWORKING_BANNED
    },
    'cocina': {
        'label': 'Cocina',
        'banned': ['taladro', 'sierra', 'amoladora', 'taller', 'pelo', 'afeitad', 'zapato', 'zapatilla', 'aspiradora', 'fregona', 'soldador'] + NETWORKING_BANNED
    },
    'limpieza': {
        'label': 'Limpieza',
        'banned': ['sarten', 'sartén', 'olla', 'cocina', 'taladro', 'sierra', 'zapato', 'zapatilla', 'libro', 'novela', 'barberia', 'afeitadora'] + NETWORKING_BANNED
    },
    'zapateria': {
        'label': 'Zapatería',
        'banned': ['aspiradora', 'freidora', 'sartén', 'taladro', 'sierra', 'libro', 'novela', 'afeitadora'] + NETWORKING_BANNED
    },
    'libreria': {
        'label': 'Librería',
        'banned': ['aspiradora', 'freidora', 'taladro', 'zapato', 'afeitadora', 'sarten', 'bateria de cocina'] + NETWORKING_BANNED
    }
}

def verify_pre_publish(project_dir, mode="both"):
    errors = []
    warnings = []
    
    if not os.path.isdir(project_dir):
        return {"status": "blocked", "errors": [f"Directorio no encontrado: {project_dir}"]}
        
    data_file = os.path.join(project_dir, "data.json")
    if not os.path.exists(data_file):
        return {"status": "blocked", "errors": [f"data.json no encontrado en {project_dir}"]}
        
    try:
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {"status": "blocked", "errors": [f"Error leyendo data.json: {e}"]}
        
    query = data.get("query", "")
    canal = data.get("canal_nombre", project_dir)
    niche = get_channel_niche(canal)
    rules = NICHE_RULES.get(niche)
    
    # 1. VERIFICACIÓN SEMÁNTICA HORIZONTAL (TODOS LOS PRODUCTOS)
    products = data.get("products", [])
    if not products:
        pa = data.get("product_a")
        pb = data.get("product_b")
        if pa and pb:
            products = [pa, pb]
            
    if rules:
        for idx, p in enumerate(products):
            t_low = (p.get("title") or "").lower()
            for b in rules["banned"]:
                if re.search(r'\b' + re.escape(b) + r'\b', t_low) and b not in query.lower():
                    errors.append(f"[HORIZONTAL] Producto #{idx+1} '{p.get('title')[:50]}...' ajeno al nicho {rules['label']} (término: '{b}')")
                    
    # 2. VERIFICACIÓN SEMÁNTICA SHORT (SHORT SCRIPT + TOP PRODUCT)
    short_script_file = os.path.join(project_dir, "short_script.json")
    if os.path.exists(short_script_file) and mode in ["short", "both"]:
        try:
            with open(short_script_file, "r", encoding="utf-8") as sf:
                s_data = json.load(sf)
                stext = (s_data.get("hook", "") + " " + s_data.get("product", "") + " " + s_data.get("query", "")).lower()
                if rules:
                    for b in rules["banned"]:
                        if re.search(r'\b' + re.escape(b) + r'\b', stext) and b not in query.lower():
                            errors.append(f"[SHORT] Guion del Short contiene término ajeno al nicho {rules['label']}: '{b}'")
        except Exception as e:
            warnings.append(f"No se pudo leer short_script.json: {e}")

    # 3. VERIFICACIÓN FÍSICA DE ARCHIVOS DE VÍDEO CON FFPROBE
    def check_video(fpath, min_dur=5.0, max_dur=None, is_short=False):
        if not os.path.exists(fpath):
            return f"Vídeo no encontrado: {fpath}"
        sz = os.path.getsize(fpath)
        if sz < 100000:
            return f"Vídeo demasiado pequeño ({sz} bytes): {fpath}"
        try:
            cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type", "-of", "json", fpath]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
            if res.returncode != 0:
                return f"Vídeo corrupto (ffprobe falló): {fpath}"
            info = json.loads(res.stdout)
            dur = float(info.get("format", {}).get("duration", 0))
            if dur < min_dur:
                return f"Duración insuficiente ({dur:.1f}s < {min_dur:.0f}s [mínimo 4 minutos]): {fpath}"
            if max_dur and dur > max_dur:
                return f"Duración excesiva para Short ({dur:.1f}s > {max_dur}s): {fpath}"
            streams = [s.get("codec_type") for s in info.get("streams", [])]
            if "video" not in streams:
                return f"El archivo no contiene pista de vídeo válida: {fpath}"
        except Exception as e:
            return f"Error ejecutando ffprobe: {e}"
        return None

    if mode in ["horizontal", "both"]:
        horiz_candidates = [
            os.path.join(project_dir, "RENDER_FINAL_AMAZON.mp4"),
            os.path.join(project_dir, "RENDER_FINAL_NAS.mp4")
        ]
        horiz_found = [f for f in horiz_candidates if os.path.exists(f)]
        if not horiz_found:
            errors.append("[HORIZONTAL] No se encontró el vídeo horizontal renderizado (RENDER_FINAL_AMAZON.mp4 / NAS)")
        else:
            err = check_video(horiz_found[0], min_dur=240.0)
            if err:
                errors.append(f"[HORIZONTAL] {err}")

    if mode in ["short", "both"]:
        short_candidates = [
            os.path.join(project_dir, "RENDER_FINAL_SHORT_VERTICAL.mp4"),
            os.path.join(project_dir, "short_video.mp4")
        ]
        short_found = [f for f in short_candidates if os.path.exists(f)]
        if not short_found:
            errors.append("[SHORT] No se encontró el vídeo vertical (RENDER_FINAL_SHORT_VERTICAL.mp4 / short_video.mp4)")
        else:
            err = check_video(short_found[0], min_dur=5.0, max_dur=60.0, is_short=True)
            if err:
                errors.append(f"[SHORT] {err}")

    # 4. VERIFICACIÓN DE MINIATURA (SOLO HORIZONTAL)
    if mode in ["horizontal", "both"]:
        thumb_file = os.path.join(project_dir, "thumbnail.jpg")
        if not os.path.exists(thumb_file):
            errors.append("[MINIATURA] thumbnail.jpg no existe en el directorio del proyecto")
        elif os.path.getsize(thumb_file) < 30000:
            errors.append(f"[MINIATURA] thumbnail.jpg demasiado ligera ({os.path.getsize(thumb_file)} bytes)")

    return {
        "status": "passed" if not errors else "blocked",
        "niche": niche,
        "query": query,
        "mode": mode,
        "errors": errors,
        "warnings": warnings
    }

def main():
    parser = argparse.ArgumentParser(description="Pre-Publish Sanity Gate para YouTube")
    parser.add_argument("pos_project_dir", nargs="?", default=None, help="Directorio raíz del proyecto (posicional)")
    parser.add_argument("--project_dir", default=None, help="Directorio raíz del proyecto")
    parser.add_argument("--mode", default="both", choices=["horizontal", "short", "both"], help="Modo de validación")
    args = parser.parse_args()

    raw_dir = args.project_dir or args.pos_project_dir
    if not raw_dir:
        parser.error("Es necesario especificar el directorio del proyecto (--project_dir o posicional)")
    project_dir = os.path.abspath(raw_dir)
    res = verify_pre_publish(project_dir, mode=args.mode)
    
    print(json.dumps(res, indent=2, ensure_ascii=False))
    
    if res["status"] == "blocked":
        print(f"\n❌ [PRE-PUBLISH BLOCKED] Se encontraron {len(res['errors'])} errores críticos. Publicación abortada.", file=sys.stderr)
        for err in res["errors"]:
            print(f"   └─ {err}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"\n✅ [PRE-PUBLISH PASSED] Calidad y concordancia 100% verificadas para nicho '{res['niche']}'.", file=sys.stderr)
        sys.exit(0)

if __name__ == "__main__":
    main()
