#!/usr/bin/env python3
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from thumbnail_engine import render_vs_thumbnail, render_top_thumbnail

if __name__ == "__main__":
    p_arg = sys.argv[1] if (len(sys.argv) > 1 and sys.argv[1].strip()) else ""
    if not p_arg or not os.path.exists(p_arg):
        print(f"ERROR: project_dir '{p_arg}' no existe", file=sys.stderr)
        sys.exit(1)

    project_dir = os.path.abspath(p_arg)
    output_path = sys.argv[2] if (len(sys.argv) > 2 and sys.argv[2].strip()) else os.path.join(project_dir, "thumbnail.jpg")
    template_id = int(sys.argv[3]) if (len(sys.argv) > 3 and sys.argv[3].strip().isdigit()) else None

    # Detectar nicho si está presente en ruta o datos
    p_low = project_dir.lower()
    niche = ""
    for n in ["cocina", "limpieza", "calzado", "zapateria", "libreria", "barberia", "taller"]:
        if n in p_low:
            niche = "calzado" if n == "zapateria" else n
            break

    # Auto-detección: si es formato TOP, despachar a render_top_thumbnail
    is_top = False
    data_path = os.path.join(project_dir, "data.json")
    if os.path.exists(data_path):
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                d = json.load(f)
                fmt = str(d.get("format", "")).lower()
                if fmt == "top" or ("products" in d and "product_a" not in d):
                    is_top = True
        except Exception:
            pass

    if is_top:
        render_top_thumbnail(project_dir, output_path, template_id=template_id)
    else:
        render_vs_thumbnail(project_dir, output_path, niche=niche, template_id=template_id)
