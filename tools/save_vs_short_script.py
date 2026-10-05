#!/usr/bin/env python3
"""
save_vs_short_script.py
Parsea la salida del nodo LLM de Short y guarda short_script.json para comparativas VS.
"""

import sys
import os
import json
import argparse

def parse_ai_json(val):
    if not val:
        return {}
    if isinstance(val, dict):
        return val
    s = str(val).strip()
    # Remove code blocks
    if s.startswith("```"):
        lines = s.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    try:
        return json.loads(s)
    except Exception:
        import re
        m = re.search(r"(\{[\s\S]*\})", s)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
    return {}

def main():
    parser = argparse.ArgumentParser(description="Guarda el guion de Short VS en formato JSON")
    parser.add_argument("project_dir", help="Directorio del proyecto")
    args, unknown = parser.parse_known_args()

    project_dir = os.path.abspath(args.project_dir)
    data_json_path = os.path.join(project_dir, "data.json")

    # Leer stdin si viene de n8n
    input_str = ""
    if not sys.stdin.isatty():
        input_str = sys.stdin.read().strip()

    parsed_input = parse_ai_json(input_str)

    data_obj = {}
    if os.path.exists(data_json_path):
        try:
            with open(data_json_path, "r", encoding="utf-8") as f:
                data_obj = json.load(f)
        except Exception:
            pass

    # Extraer campos de guion corto
    output_dict = parsed_input.get("output", {})
    if isinstance(output_dict, str):
        output_dict = parse_ai_json(output_dict)
    if not isinstance(output_dict, dict):
        output_dict = {}

    hook = parsed_input.get("hook") or output_dict.get("hook", "")
    prod = parsed_input.get("product") or output_dict.get("product", "")
    outro = parsed_input.get("outro") or output_dict.get("outro", "")

    # Fallbacks si no vinieron en el JSON
    product_a = data_obj.get("product_a", {})
    product_b = data_obj.get("product_b", {})
    brand_a = product_a.get("brand", "Marca A")
    brand_b = product_b.get("brand", "Marca B")
    query = data_obj.get("query", "productos").strip()

    if not hook:
        hook = f"¿Dudas entre {brand_a} o {brand_b}? Antes de comprar en Amazon, no cometas el error de elegir a ciegas."
    if not prod:
        prod = f"{brand_a} ofrece máxima durabilidad y prestaciones de gama alta, mientras que {brand_b} destaca por su relación calidad precio inigualable."
    if not outro:
        outro = f"¿Cuál elegirías tú? Comenta A o B. Mira la comparativa completa de 8 minutos en la descripción."

    full_text = f"{hook} {prod} {outro}".strip()
    words = len(full_text.split())

    short_data = {
        "query": query,
        "hook": hook,
        "product": prod,
        "outro": outro,
        "full_text": full_text,
        "total_words": words,
        "product_a": product_a,
        "product_b": product_b,
        "project_dir": project_dir
    }

    out_file = os.path.join(project_dir, "short_script.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(short_data, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "status": "ok",
        "script_file": out_file,
        "words": words
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
