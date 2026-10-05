#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""
generate_libreria_youtube_tags.py
Genera etiquetas SEO de alta conversión optimizadas dinámicamente según la temática concreta del libro.
Garantiza un límite máximo de ~485 bytes (límite YouTube de 500 caracteres).
"""

import sys
import os
import json
import re

def clean_tag(tag):
    if not tag:
        return ""
    tag = re.sub(r'[#<>"\r\n\t]', '', str(tag))
    tag = re.sub(r'[^a-zA-Z0-9áéíóúñÁÉÍÓÚÑ\s\-_]', '', tag)
    tag = re.sub(r'\s+', ' ', tag).strip(' ,-_')
    if len(tag) > 70:
        tag = tag[:70].strip()
    return tag

def clean_book_title(title):
    if not title:
        return ""
    t = str(title).strip()
    t = re.sub(r'[\r\n\t]+', ' ', t)
    t = re.sub(r'\s*\([^)]*Spanish Edition[^)]*\)', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s*\[Edición Kindle\]', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s*:?\s*Edición Kindle', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s*:?\s*Tapa dura', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s*:?\s*Tapa blanda', '', t, flags=re.IGNORECASE)
    if ":" in t and len(t) > 35:
        t = t.split(":")[0].strip()
    if "-" in t and len(t) > 35:
        t = t.split("-")[0].strip()
    return t.strip()

def generate_libreria_tags(project_dir):
    data_path = os.path.join(project_dir, "data.json")
    query = ""
    brand_a = ""
    brand_b = ""
    title_a = ""
    title_b = ""

    if os.path.exists(data_path):
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                query = data.get("query", "").replace("_", " ").strip()
                prod_a = data.get("product_a", {})
                prod_b = data.get("product_b", {})
                brand_a = prod_a.get("brand", "")
                brand_b = prod_b.get("brand", "")
                title_a = clean_book_title(prod_a.get("title", ""))
                title_b = clean_book_title(prod_b.get("title", ""))
        except Exception:
            pass

    tags = []

    # 1. Tags neutros de libros (sin hashtags, no permitidos por YouTube API)
    tags.extend(["libros", "lectura recomendada", "mejores libros", "resumen de libros"])

    # Temática si existe
    if query:
        clean_q_tag = clean_tag(query)
        if clean_q_tag and clean_q_tag not in tags:
            tags.append(clean_q_tag)

    # 2. Tags directos de la búsqueda/temática
    if query:
        tags.append(clean_tag(query))
        tags.append(clean_tag(f"{query} recomendados"))
        tags.append(clean_tag(f"{query} opiniones"))
        tags.append(clean_tag(f"mejores {query} 2026"))

    # 3. Tags de títulos y autores reales
    if title_a:
        tags.append(clean_tag(title_a[:35]))
    if title_b:
        tags.append(clean_tag(title_b[:35]))
    if brand_a and "librería" not in brand_a.lower():
        tags.append(clean_tag(brand_a[:30]))
    if brand_b and "librería" not in brand_b.lower():
        tags.append(clean_tag(brand_b[:30]))
    if title_a and title_b:
        tags.append(clean_tag(f"{title_a[:20]} vs {title_b[:20]}"))

    # 4. Tags generales de libros adaptados dinámicamente
    general_tags = [
        "libreria del pueblo",
        "resumen de libros",
        "recomendaciones de lectura",
        "precio minimo historico",
        "ganga amazon",
        "oferta flash amazon",
        "cual es mejor 2026",
        "merece la pena 2026",
        "que libro leer",
        "mejores libros 2026",
        "analisis de libros",
        "comparativa de libros"
    ]

    for gt in general_tags:
        clean_gt = clean_tag(gt)
        if clean_gt not in tags:
            tags.append(clean_gt)

    try:
        from campaign_manager import get_active_campaign, get_niche_campaign_tags
        _camp = get_active_campaign()
        if _camp:
            c_tags = get_niche_campaign_tags(_camp, niche="libreria")
            if c_tags:
                camp_tags = [clean_tag(ct) for ct in c_tags if clean_tag(ct)]
                tags = camp_tags + [t for t in tags if t not in camp_tags]
            elif _camp.get("extra_tags"):
                camp_tags = [clean_tag(ct) for ct in _camp["extra_tags"] if clean_tag(ct)]
                tags = camp_tags + [t for t in tags if t not in camp_tags]
    except Exception:
        pass

    # 5. Truncar respetando estricto límite de ~480 bytes en UTF-8
    final_tags = []
    current_bytes = 0

    MAX_CHARS = 475  # Límite seguro YouTube es 500 chars / 485 bytes
    for t in tags:
        if not t:
            continue
        tag_quote_overhead = 2 if ' ' in t else 0
        added_len = len(t.encode('utf-8')) + tag_quote_overhead + (1 if final_tags else 0)
        if current_bytes + added_len > MAX_CHARS:
            break
        final_tags.append(t)
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
        print("Uso: generate_libreria_youtube_tags.py <project_dir>")
        sys.exit(1)

    project_dir = os.path.abspath(sys.argv[1])
    generate_libreria_tags(project_dir)

if __name__ == "__main__":
    main()
