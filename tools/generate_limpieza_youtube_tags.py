#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""
generate_limpieza_youtube_tags.py
Genera etiquetas SEO de alta conversión optimizadas para "Limpieza Tecnológica".
Garantiza un límite máximo de ~485 bytes (límite YouTube de 500 caracteres).
"""

import sys
import os
import json
import re

def clean_tag(tag):
    if not tag:
        return ""
    tag = re.sub(r'[\"\<\>\r\n\t]', '', str(tag))
    tag = re.sub(r'[^a-zA-Z0-9áéíóúñÁÉÍÓÚÑ\s\-_]', '', tag)
    tag = re.sub(r'\s+', ' ', tag).strip(' ,-_')
    if len(tag) > 70:
        tag = tag[:70].strip()
    return tag

def generate_limpieza_tags(project_dir):
    data_path = os.path.join(project_dir, "data.json")
    query = ""
    brand_a = ""
    brand_b = ""

    if os.path.exists(data_path):
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                query = data.get("query", "")
                prod_a = data.get("product_a", {})
                prod_b = data.get("product_b", {})
                brand_a = prod_a.get("brand", "")
                brand_b = prod_b.get("brand", "")
        except Exception:
            pass

    raw_tags = []

    if query:
        raw_tags.append(query)
        raw_tags.append(f"{query} comparativa")
        raw_tags.append(f"{query} opiniones")
        raw_tags.append(f"mejor {query} 2026")

    if brand_a:
        raw_tags.append(brand_a)
    if brand_b:
        raw_tags.append(brand_b)
    if brand_a and brand_b:
        raw_tags.append(f"{brand_a} vs {brand_b}")

    base_niche_tags = [
        "limpieza del pueblo",
        "limpieza tecnologica",
        "robot aspirador autovaciado",
        "aspiradora sin cable opiniones",
        "precio minimo historico",
        "ganga amazon",
        "oferta flash amazon",
        "cual es mejor 2026",
        "merece la pena 2026",
        "hidrolimpiadora alta presion",
        "limpiador tapiceria amazon",
        "fregadora electrica suelos",
        "mopa de vapor para suelos",
        "vaporeta de mano",
        "mejores aspiradoras 2026",
        "aspiradora escoba potente",
        "limpiador de alfombras",
        "aspiradora antiacaros"
    ]
    raw_tags.extend(base_niche_tags)

    try:
        from campaign_manager import get_active_campaign, get_niche_campaign_tags
        _camp = get_active_campaign()
        if _camp:
            c_tags = get_niche_campaign_tags(_camp, niche="limpieza")
            if c_tags:
                raw_tags = c_tags + raw_tags
            elif _camp.get("extra_tags"):
                raw_tags = _camp["extra_tags"] + raw_tags
    except Exception:
        pass

    final_tags = []
    seen = set()
    current_bytes = 0

    MAX_CHARS = 475  # Límite seguro YouTube es 500 chars / 485 bytes
    for t in raw_tags:
        ct = clean_tag(t)
        if not ct or ct.lower() in seen:
            continue
        tag_quote_overhead = 2 if ' ' in ct else 0
        added_len = len(ct.encode('utf-8')) + tag_quote_overhead + (1 if final_tags else 0)
        if current_bytes + added_len > MAX_CHARS:
            break
        final_tags.append(ct)
        seen.add(ct.lower())
        current_bytes += added_len

    tags_str = ",".join(final_tags)

    yt_meta_path = os.path.join(project_dir, "youtube_metadata.json")
    if os.path.exists(yt_meta_path):
        try:
            with open(yt_meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            meta["tags"] = final_tags
            meta["tags_str"] = tags_str
            with open(yt_meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    out_json = {
        "tags": final_tags,
        "tags_str": tags_str,
        "total_tags": len(final_tags),
        "total_bytes": len(tags_str.encode('utf-8'))
    }
    print(json.dumps(out_json, ensure_ascii=False))
    return out_json

def main():
    if len(sys.argv) < 2:
        print("Uso: generate_limpieza_youtube_tags.py <project_dir>")
        sys.exit(1)

    project_dir = os.path.abspath(sys.argv[1])
    generate_limpieza_tags(project_dir)

if __name__ == "__main__":
    main()
