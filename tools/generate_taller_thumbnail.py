#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from thumbnail_engine import render_vs_thumbnail

if __name__ == "__main__":
    p_arg = sys.argv[1] if (len(sys.argv) > 1 and sys.argv[1].strip()) else ""
    if not p_arg or not os.path.exists(p_arg):
        print(f"ERROR: project_dir '{p_arg}' no existe", file=sys.stderr)
        sys.exit(1)

    project_dir = os.path.abspath(p_arg)
    output_path = sys.argv[2] if (len(sys.argv) > 2 and sys.argv[2].strip()) else os.path.join(project_dir, "thumbnail.jpg")
    template_id = int(sys.argv[3]) if (len(sys.argv) > 3 and sys.argv[3].strip().isdigit()) else None

    render_vs_thumbnail(project_dir, output_path, niche="taller", template_id=template_id)
