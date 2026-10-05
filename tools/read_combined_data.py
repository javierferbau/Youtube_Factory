#!/usr/bin/env python3
import sys
import os
import json
import re
import unicodedata
from amazon_paapi_helper import get_short_amazon_url

import argparse

parser = argparse.ArgumentParser(description="Lee datos del proyecto y genera metadatos combinados para Ollama")
parser.add_argument("project_dir", nargs="?", default="", help="Directorio del proyecto")
parser.add_argument("--affiliate_tag", default="", help="Tag de afiliado de Amazon")
args, unknown = parser.parse_known_args()

project_dir = args.project_dir.strip()
tag_arg = args.affiliate_tag.strip()

data_file = os.path.join(project_dir, "data.json")
meta_file = os.path.join(project_dir, "youtube_metadata.json")
meta_txt = os.path.join(project_dir, "youtube_metadata.txt")

data_obj = {}
if os.path.exists(data_file):
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data_obj = json.load(f)
    except Exception:
        pass

query = data_obj.get("query", "")
if not query and project_dir:
    query = os.path.basename(os.path.normpath(project_dir)).replace("_", " ")

affiliate_tag = tag_arg or data_obj.get("affiliate_tag", "")
channel_name = data_obj.get("channel_name", "")
products = data_obj.get("products", [])

query = query.replace("_", " ").strip()

title = f"TOP 7 MEJORES {query.upper()} EN AMAZON 2026 🏆 | Guía Completa"
if len(title) > 95:
    title = title[:92].rsplit(' ', 1)[0]

desc_lines = [
    f"¿Buscas los mejores {query} de Amazon? En este vídeo hemos comparado y analizado las mejores opciones del mercado para que no pierdas tiempo ni dinero.",
    "",
    "⏱️ ÍNDICE DEL VÍDEO",
    "────────────────────────────────────────",
    "0:00 🎬 Introducción"
]

sec_offset = 6
for idx, p in enumerate(products, 1):
    p_title = p.get("title", f"Producto #{idx}")
    m = sec_offset // 60
    s = sec_offset % 60
    desc_lines.append(f"{m}:{s:02d} Puesto #{idx} — {p_title[:55]}")
    sec_offset += 60

desc_lines.extend([
    f"{sec_offset//60}:{sec_offset%60:02d} 🎤 Conclusión y enlaces",
    "",
    "🛒 PRODUCTOS DEL RANKING",
    "────────────────────────────────────────"
])

for idx, p in enumerate(products, 1):
    p_title = p.get("title", f"Producto #{idx}")
    p_price = p.get("price", "")
    p_asin = p.get("asin", "")
    p_url = p.get("url", "")
    
    if p_asin:
        clean_url = get_short_amazon_url(p_asin, affiliate_tag)
    elif p_url:
        clean_url = re.sub(r'\?tag=.*$', '', p_url).rstrip('/') + f"?tag={affiliate_tag}"
    else:
        clean_url = ""

    desc_lines.append(f"✅ PUESTO #{idx} — {p_title}")
    if p_price:
        desc_lines.append(f"   💰 Precio aprox: {p_price}")
    if clean_url:
        desc_lines.append(f"   🔗 {clean_url}")
    desc_lines.append("")

desc_lines.extend([
    "────────────────────────────────────────",
    "👍 Si te ha sido útil, ¡dale al LIKE y SUSCRÍBETE para no perderte más rankings!",
    "🔔 Activa la campanita para recibir notificaciones de nuevos vídeos.",
    "",
    "📌 AVISO DE AFILIADOS",
    "Este vídeo contiene enlaces de afiliado de Amazon. Si compras a través de ellos, recibo una pequeña comisión sin coste adicional para ti. Gracias por apoyar el canal."
])

description = "\n".join(desc_lines)

def sanitize_tag(s):
    s = unicodedata.normalize('NFD', str(s))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[^a-zA-Z0-9\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip().lower()
    return s

tags = []

for p in products:
    p_title = p.get("title", "")
    if p_title:
        clean_p_title = re.sub(r'[\(\),\|:\+\-\.\/]', ' ', p_title).strip()
        words = clean_p_title.split()
        if len(words) >= 2:
            brand_model = f"{words[0]} {words[1]}"
            tags.append(brand_model)
        if len(words) >= 3 and words[2].lower() not in ('de', 'con', 'para', 'en', 'el', 'la', 'los', 'las', 'un', 'una', 'y', 'o', 'sin'):
            tags.append(f"{words[0]} {words[1]} {words[2]}")

query_clean = query.lower().strip()
if query_clean:
    tags.extend([
        query_clean,
        f"mejores {query_clean}",
        f"{query_clean} amazon",
        f"comprar {query_clean}",
        f"{query_clean} 2026",
        f"analisis {query_clean}",
        f"guia de compra {query_clean}",
        f"opinion {query_clean}"
    ])

tags.append("amazon espana")
if channel_name:
    tags.append(channel_name.lower())

unique_tags = []
total_chars = 0
for t in tags:
    st = sanitize_tag(t)
    if st and len(st) > 2 and st not in unique_tags:
        b_len = len(st.encode('utf-8')) + 1
        if total_chars + b_len <= 380:
            unique_tags.append(st)
            total_chars += b_len

product_names = [p.get("title", "") for p in products]
product_prices = [str(p.get("price", "")) for p in products]

meta_out = {
    "youtube_title": title,
    "youtube_description": description,
    "tags": unique_tags,
    "query": query,
    "title": title,
    "description": description
}

with open(meta_file, 'w', encoding='utf-8') as f:
    json.dump(meta_out, f, indent=2, ensure_ascii=False)

with open(meta_txt, 'w', encoding='utf-8') as f:
    f.write(f"TÍTULO:\n{title}\n\nDESCRIPCIÓN:\n{description}\n\nTAGS:\n{', '.join(unique_tags)}\n")

out = {
    "query": query,
    "current_title": title,
    "current_description": description,
    "product_names": product_names,
    "product_prices": product_prices,
    "top_keywords_str": f"{query}, ofertas {query}, comprar {query}",
    "suggested_tags_str": ", ".join(unique_tags),
    "tags": unique_tags,
    "project_dir": project_dir,
    "affiliate_tag": affiliate_tag
}

print(json.dumps(out, ensure_ascii=False))
