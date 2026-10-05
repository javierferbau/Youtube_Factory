#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""
generate_cocina_youtube_tags.py
Genera etiquetas SEO de alta conversión optimizadas para "Cocina Tecnológica".
Garantiza un límite máximo de ~485 bytes (límite YouTube de 500 caracteres).
"""

import sys
import os
import json
import re

def clean_tag(tag):
    tag = re.sub(r'[^a-zA-Z0-9áéíóúñÁÉÍÓÚÑ\s\-_]', '', tag)
    return tag.strip()

def generate_cocina_tags(project_dir):
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
                query = data.get("query", "")
                prod_a = data.get("product_a", {})
                prod_b = data.get("product_b", {})
                brand_a = prod_a.get("brand", "")
                brand_b = prod_b.get("brand", "")
                title_a = prod_a.get("title", "")
                title_b = prod_b.get("title", "")
        except Exception:
            pass

    tags = []

    # 1. Tags directos de la búsqueda
    if query:
        tags.append(clean_tag(query))
        tags.append(clean_tag(f"{query} comparativa"))
        tags.append(clean_tag(f"{query} opinioes"))
        tags.append(clean_tag(f"mejor {query} 2026"))

    # 2. Tags de marcas y modelos
    if brand_a:
        tags.append(clean_tag(brand_a))
    if brand_b:
        tags.append(clean_tag(brand_b))
    if brand_a and brand_b:
        tags.append(clean_tag(f"{brand_a} vs {brand_b}"))

    # 3. Tags generales de alta conversión en Cocina Tecnológica
    base_niche_tags = [
        "cocina tecnologica",
        "electrodomesticos cocina",
        "freidora de aire sin aceite",
        "robot de cocina opiniones",
        "recetas airfryer",
        "precio minimo historico",
        "ganga amazon",
        "oferta flash amazon",
        "cual es mejor 2026",
        "merece la pena 2026",
        "electrodomesticos amazon",
        "cual comprar 2026",
        "calidad precio",
        "mejores electrodomesticos",
        "guia de compra cocina",
        "ofertas amazon cocina"
    ]
    
    for t in base_niche_tags:
        tags.append(t)

    try:
        from campaign_manager import get_active_campaign, get_niche_campaign_tags
        _camp = get_active_campaign()
        if _camp:
            c_tags = get_niche_campaign_tags(_camp, niche="cocina")
            if c_tags:
                tags = [clean_tag(ct) for ct in c_tags if clean_tag(ct)] + tags
            elif _camp.get("extra_tags"):
                tags = [clean_tag(ct) for ct in _camp["extra_tags"] if clean_tag(ct)] + tags
    except Exception:
        pass

    # Eliminar duplicados preservando el orden
    seen = set()
    unique_tags = []
    for t in tags:
        t_lower = t.lower()
        if t_lower and t_lower not in seen:
            seen.add(t_lower)
            unique_tags.append(t)

    # Ajustar longitud a < 380 caracteres (respetando comillas de YouTube)
    final_tags = []
    current_length = 0
    MAX_CHARS = 475  # Límite seguro YouTube es 500 chars / 485 bytes

    for t in unique_tags:
        tag_quote_overhead = 2 if ' ' in t else 0
        added_len = len(t.encode('utf-8')) + tag_quote_overhead + (1 if final_tags else 0)
        if current_length + added_len > MAX_CHARS:
            break
        final_tags.append(t)
        current_length += added_len

    output_str = ",".join(final_tags)
    return output_str

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: generate_cocina_youtube_tags.py <project_dir>")
        sys.exit(1)

    project_dir = os.path.abspath(sys.argv[1])
    tags_str = generate_cocina_tags(project_dir)
    print(tags_str)
