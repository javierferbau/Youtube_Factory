#!/usr/bin/env python3
"""
generate_short_metadata.py
Genera metadatos específicos para la publicación de YouTube Shorts (9:16, <60s).
Incluye etiquetas #Shorts y enlace al vídeo horizontal largo.
"""

import sys
import os
import json
import argparse
import re

def main():
    parser = argparse.ArgumentParser(description="Generador de metadatos de YouTube Shorts")
    parser.add_argument("project_dir", help="Directorio del proyecto")
    parser.add_argument("--affiliate_tag", default="", help="Tag de afiliado Amazon")
    args, unknown = parser.parse_known_args()

    project_dir = os.path.abspath(args.project_dir)
    data_json_path = os.path.join(project_dir, "data.json")

    query = "productos"
    affiliate_tag = args.affiliate_tag.strip()
    video_format = "top7"
    data = {}

    if os.path.exists(data_json_path):
        try:
            with open(data_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                query = data.get("query", "productos").strip()
                video_format = data.get("format", "top7")
                if not affiliate_tag:
                    affiliate_tag = data.get("affiliate_tag", "")
        except Exception:
            pass

    query = query.replace("_", " ").strip()
    clean_q = re.sub(r'^(mejores|aparatos eléctricos de|los mejores)\s+', '', query, flags=re.IGNORECASE).strip().upper()

    # ── TOP N FORMAT (original) ──
    canal_nombre = (data.get("canal_nombre", "") or data.get("channel_name", "")).lower()
    is_cocina = "cocina" in canal_nombre or "cocina" in query.lower() or any(k in query.lower() for k in [
        "freidora", "cafetera", "robot", "batidora", "horno", "olla", "tostadora", "sandwichera"
    ])
    if is_cocina:
        short_title = f"¿Cuál Comprar? Nº 1 {clean_q[:30]} 🏆 #Shorts"
        if len(short_title) > 90:
            short_title = f"¿Cuál Comprar? {clean_q[:25]} 🏆 #Shorts"
    else:
        short_title = f"Nº 1 MEJOR {clean_q} 🏆 #Shorts"
        if len(short_title) > 90:
            short_title = f"TOP 1 {clean_q[:30]} 🏆 #Shorts"

    top_product = None
    prods = data.get("products", [])
    if prods:
        top_product = prods[0]

    prod_url = ""
    if top_product:
        asin = top_product.get("asin", "")
        if asin and affiliate_tag:
            prod_url = f"https://www.amazon.es/dp/{asin}?tag={affiliate_tag}"
        elif top_product.get("product_url"):
            prod_url = top_product.get("product_url")

    desc_lines = [
        f"🔥 ¡El modelo número 1 de {query.lower()} en Amazon España! Mira la comparativa completa de 8 minutos en nuestro canal.",
        ""
    ]
    if prod_url:
        desc_lines.append(f"🔗 Ver precio de oferta en Amazon: {prod_url}")
        desc_lines.append("")
    desc_lines.extend([
        "👍 ¡Suscríbete para más chollos y comparativas exprés!",
        "#Shorts #AmazonAfiliados #MejoresOfertas #Chollos"
    ])

    short_description = "\n".join(desc_lines)
    tags = ["Shorts", "shorts", query.lower(), f"mejores {query.lower()}", "amazon", "chollos"]

    pinned_comment = (f"🔥 Ver precio y descuento del puesto #1 en Amazon: {prod_url}\n\n🎬 ¡Mira la comparativa completa de 8 minutos en nuestro canal!") if prod_url else "🎬 ¡Mira la comparativa completa de 8 minutos en nuestro canal!"
    result = {
        "youtube_title": short_title,
        "youtube_description": short_description,
        "pinned_comment": pinned_comment,
        "tags": tags,
        "is_short": True,
        "query": query
    }

    out_file = os.path.join(project_dir, "short_metadata.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
