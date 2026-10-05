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

    # Auto-detección inteligente: Formato TOP vs VS
    is_vs = False
    data_path = os.path.join(project_dir, "data.json")
    if os.path.exists(data_path):
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                d = json.load(f)
                fmt = str(d.get("format", "")).lower()
                if fmt == "vs" or "product_a" in d:
                    is_vs = True
                elif fmt == "top" or "products" in d or "product_1" in d:
                    is_vs = False
        except Exception:
            pass
    else:
        base = os.path.basename(project_dir).lower()
        if "_vs" in base or " vs " in base or os.path.exists(os.path.join(project_dir, "01_producto_a")):
            is_vs = True

    if is_vs:
        render_vs_thumbnail(project_dir, output_path, niche="barberia", template_id=template_id)
    else:
        render_top_thumbnail(project_dir, output_path, template_id=template_id)
