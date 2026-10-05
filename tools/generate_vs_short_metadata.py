#!/usr/bin/env python3
"""
generate_vs_short_metadata.py
Genera metadatos específicos para la publicación de YouTube Shorts (9:16, <60s) en formato VS.
Soporta dinámicamente cualquier nicho (Cocina, Limpieza, Calzado, Librería, etc.).
"""

import sys
import os
import json
import argparse
import re

def clean_text(text):
    if not text:
        return ""
    s = str(text).strip()
    s = re.sub(r'[\r\n\t]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def clean_brand_name(name):
    if not name:
        return ""
    s = str(name).strip()
    s = re.sub(r'[\r\n\t]+', ' ', s)
    s = re.sub(r'\s*\([^)]*\)', '', s)
    s = re.sub(r'^(de|por|marca:?|autor:?)\s*', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s*formato:.*$', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s*edición:.*$', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def clean_product_title(title):
    if not title:
        return "Producto"
    t = str(title).strip()
    t = re.sub(r'[\r\n\t]+', ' ', t)
    t = re.sub(r'\s*\([^)]*Spanish Edition[^)]*\)', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s*\[Edición Kindle\]', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s*:?\s*Edición Kindle', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s*:?\s*Tapa dura', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s*:?\s*Tapa blanda', '', t, flags=re.IGNORECASE)
    if ":" in t and len(t) > 25:
        t = t.split(":")[0].strip()
    if "-" in t and len(t) > 25:
        t = t.split("-")[0].strip()
    if "," in t and len(t) > 25:
        t = t.split(",")[0].strip()
    return t.strip()

def get_niche_config(canal_nombre, query):
    canal_lower = (canal_nombre or "").lower()
    query_lower = (query or "").lower()
    
    if "cocina" in canal_lower or "cocina" in query_lower or "freidora" in query_lower or "robot" in query_lower:
        return {
            "channel_brand": "La Cocina Tecnológica del Pueblo",
            "cta_sub": "👍 ¡Suscríbete a La Cocina Tecnológica del Pueblo para más comparativas!",
            "hashtags": "#Shorts #Cocina #Comparativa #AvsB #AmazonAfiliados"
        }
    elif "limpieza" in canal_lower or "limpieza" in query_lower or "aspiradora" in query_lower or "vaporeta" in query_lower:
        return {
            "channel_brand": "Limpieza del Pueblo",
            "cta_sub": "👍 ¡Suscríbete a Limpieza del Pueblo para más comparativas!",
            "hashtags": "#Shorts #Limpieza #Comparativa #AvsB #AmazonAfiliados"
        }
    elif "calzado" in canal_lower or "zapato" in query_lower or "zapatillas" in query_lower:
        return {
            "channel_brand": "Calzado del Pueblo",
            "cta_sub": "👍 ¡Suscríbete a Calzado del Pueblo para más comparativas!",
            "hashtags": "#Shorts #Calzado #Comparativa #AvsB #AmazonAfiliados"
        }
    elif "librería" in canal_lower or "libro" in query_lower or "libreria" in canal_lower:
        return {
            "channel_brand": "Librería Del Pueblo",
            "cta_sub": "👍 ¡Suscríbete a Librería Del Pueblo para más comparativas!",
            "hashtags": "#Shorts #ComparativaLiteraria #AvsB #AmazonAfiliados"
        }
    elif "barberia" in canal_lower or "afeitad" in query_lower or "barba" in query_lower or "cortapelo" in query_lower:
        return {
            "channel_brand": "La Barbería del Pueblo",
            "cta_sub": "👍 ¡Suscríbete a La Barbería del Pueblo para más comparativas!",
            "hashtags": "#Shorts #Barbería #Afeitado #Comparativa #AvsB #AmazonAfiliados"
        }
    elif "taller" in canal_lower or "herramienta" in query_lower or "taladro" in query_lower or "sierra" in query_lower or "cepillo" in query_lower:
        return {
            "channel_brand": "El Taller Del Pueblo",
            "cta_sub": "👍 ¡Suscríbete a El Taller Del Pueblo para más comparativas de herramientas!",
            "hashtags": "#Shorts #Herramientas #Bricolaje #Comparativa #AvsB #AmazonAfiliados"
        }
    else:
        brand = canal_nombre.replace("_", " ").title() if canal_nombre else "Comparativas Amazon"
        return {
            "channel_brand": brand,
            "cta_sub": f"👍 ¡Suscríbete a {brand} para más comparativas!",
            "hashtags": "#Shorts #Comparativa #AvsB #AmazonAfiliados"
        }

def main():
    parser = argparse.ArgumentParser(description="Generador de metadatos de YouTube Shorts para VS")
    parser.add_argument("project_dir", help="Directorio del proyecto")
    parser.add_argument("--affiliate_tag", default="", help="Tag de afiliado Amazon")
    args, unknown = parser.parse_known_args()

    project_dir = os.path.abspath(args.project_dir)
    data_json_path = os.path.join(project_dir, "data.json")

    query = "productos"
    affiliate_tag = args.affiliate_tag.strip()
    data = {}

    if os.path.exists(data_json_path):
        try:
            with open(data_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                query = data.get("query", "productos").strip()
                if not affiliate_tag:
                    affiliate_tag = data.get("affiliate_tag", "")
        except Exception:
            pass

    query = clean_text(query.replace("_", " "))
    canal_nombre = data.get("canal_nombre", "") or data.get("channel_name", "")
    niche = get_niche_config(canal_nombre, query)

    product_a = data.get("product_a", {})
    product_b = data.get("product_b", {})
    brand_a = clean_brand_name(product_a.get("brand", ""))
    brand_b = clean_brand_name(product_b.get("brand", ""))
    title_a = clean_product_title(product_a.get("title", "Producto A"))
    title_b = clean_product_title(product_b.get("title", "Producto B"))

    canal_lower = (canal_nombre or "").lower()
    query_lower = (query or "").lower()
    is_cocina = "cocina" in canal_lower or "cocina" in query_lower or any(k in query_lower for k in [
        "freidora", "cafetera", "robot", "batidora", "horno", "olla", "tostadora", "sandwichera"
    ])
    if is_cocina:
        short_title = f"{title_a[:22]} vs {title_b[:22]}: ¿Cuál Comprar? ⚡ #Shorts"
        short_title = clean_text(short_title)
        if len(short_title) > 90:
            short_title = f"{brand_a or title_a[:16]} vs {brand_b or title_b[:16]}: ¿Cuál Comprar? #Shorts"
    else:
        short_title = f"{title_a} vs {title_b} en 60s ⚡ #Shorts"
        short_title = clean_text(short_title)
        if len(short_title) > 90:
            short_title = f"{title_a[:25]} vs {title_b[:25]} ⚡ #Shorts"

    url_a = ""
    url_b = ""
    asin_a = product_a.get("asin", "")
    asin_b = product_b.get("asin", "")
    if asin_a and affiliate_tag:
        url_a = f"https://www.amazon.es/dp/{asin_a}?tag={affiliate_tag}"
    if asin_b and affiliate_tag:
        url_b = f"https://www.amazon.es/dp/{asin_b}?tag={affiliate_tag}"

    label_a = f"{title_a} ({brand_a})" if brand_a else title_a
    label_b = f"{title_b} ({brand_b})" if brand_b else title_b

    desc_lines = [
        f"⚔️ {label_a} vs {label_b}",
        f"¿Cuál de estos dos productos elegirías TÚ? ¡Comenta A o B!",
        ""
    ]
    if url_a:
        desc_lines.append(f"🅰️ Ver {title_a[:25]} en Amazon: {url_a}")
    if url_b:
        desc_lines.append(f"🅱️ Ver {title_b[:25]} en Amazon: {url_b}")
    desc_lines.extend([
        "",
        niche['cta_sub'],
        niche['hashtags']
    ])

    short_description = "\n".join(desc_lines)
    raw_tags = [
        "Shorts", "shorts", f"{title_a[:20]} vs {title_b[:20]}",
        query.lower(), "comparativa amazon", "amazon", niche['channel_brand'].lower()
    ]
    if brand_a: raw_tags.append(brand_a)
    if brand_b: raw_tags.append(brand_b)

    tags = [clean_text(t) for t in raw_tags if clean_text(t)]

    pinned_comment = f"🔥 ¿Cuál elegirías tú?\n👉 Opción A ({title_a[:25]}): {url_a}\n👉 Opción B ({title_b[:25]}): {url_b}\n\n🎬 ¡Mira la comparativa de 8 min completa en el canal!"
    result = {
        "title": short_title,
        "youtube_title": short_title,
        "youtube_description": short_description,
        "pinned_comment": pinned_comment,
        "description": short_description,
        "tags": tags,
        "tags_str": ",".join(tags),
        "is_short": True,
        "query": query
    }

    out_file = os.path.join(project_dir, "short_metadata.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
