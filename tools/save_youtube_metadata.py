#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""
save_youtube_metadata.py — Formats and saves YouTube title & description.
Reads Ollama-generated metadata from youtube_metadata.json, builds description
with affiliate links, timestamps, and FTC disclosure, and saves to file.
Tag generation has been decoupled into generate_youtube_tags.py.
"""
import sys
import os
import json
import re

import argparse

parser = argparse.ArgumentParser(description="Formatea y guarda metadatos de YouTube")
parser.add_argument("project_dir", nargs="?", default=".", help="Directorio del proyecto")
parser.add_argument("--affiliate_tag", default="", help="Tag de afiliado de Amazon")
args, unknown = parser.parse_known_args()

project_dir = args.project_dir.strip()
tag_arg = args.affiliate_tag.strip()

meta_file = os.path.join(project_dir, "youtube_metadata.json")
meta_txt = os.path.join(project_dir, "youtube_metadata.txt")
data_file = os.path.join(project_dir, "data.json")

# Load project data
data_obj = {}
if os.path.exists(data_file):
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data_obj = json.load(f)
    except Exception:
        pass

def parse_ai_json(val):
    if not val:
        return {}
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        s = val.strip()
        s = re.sub(r'^```(?:json)?\s*', '', s, flags=re.IGNORECASE)
        s = re.sub(r'\s*```$', '', s)
        s = s.strip()
        try:
            return json.loads(s)
        except Exception:
            match = re.search(r'(\{[\s\S]*\})', s)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
    return {}

def load_meta_file(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
    except Exception:
        return {}

    parsed = parse_ai_json(content)
    if isinstance(parsed, dict):
        for k in ["output", "text", "content"]:
            if k in parsed:
                inner = parse_ai_json(parsed[k])
                if isinstance(inner, dict):
                    return inner
    return parsed if isinstance(parsed, dict) else {}

def enforce_affiliate_tags_in_text(text: str, tag: str) -> str:
    """Asegura que todos los enlaces de Amazon en el texto lleven ?tag={tag}."""
    if not tag:
        return text
    def repl(m):
        asin = m.group(1)
        return f"https://www.amazon.es/dp/{asin}?tag={tag}"
    return re.sub(r'https?://(?:www\.)?amazon\.es/dp/([A-Z0-9]{10})(?:\?[^\s\n]*)?', repl, text)

# Load existing Ollama-generated metadata
ollama_meta = load_meta_file(meta_file)

query = data_obj.get("query", "")
if not query and project_dir:
    query = os.path.basename(os.path.normpath(project_dir))
query = query.replace("_", " ").strip()

affiliate_tag = tag_arg or data_obj.get("affiliate_tag", "")
channel_name = data_obj.get("channel_name", "")
products = data_obj.get("products", [])
video_format = data_obj.get("format", "top7")
product_a = data_obj.get("product_a", {})
product_b = data_obj.get("product_b", {})

# Use Ollama-generated title if available and valid, otherwise build complete title (<95 chars)
raw_title = ollama_meta.get("title", ollama_meta.get("youtube_title", "")).strip()
if not raw_title or raw_title.endswith("...") or raw_title == "TOP 7 MEJORES...":
    clean_q = re.sub(r'^(mejores|top|los mejores|las mejores)\s+', '', query, flags=re.IGNORECASE).strip().upper()
    n = len(products) or 7
    title = f"TOP {n} MEJORES {clean_q} EN AMAZON 2026 🏆 | Guía Completa"
else:
    title = raw_title

if len(title) > 95:
    title = title[:92].rsplit(" ", 1)[0]
try:
    from campaign_manager import get_active_campaign, apply_campaign_title
    _camp = get_active_campaign()
    if _camp:
        title = apply_campaign_title(title, _camp, max_len=95)
except Exception:
    pass

# 1. Extract Ollama intro hook if present
ollama_desc = ollama_meta.get("description", ollama_meta.get("youtube_description", "")).strip()
ollama_desc = ollama_desc.replace("_", " ").strip()

# Clean Ollama description to remove hallucinated dummy placeholder sections
clean_ollama_lines = []
stop_keywords = ["LINKS DE COMPRA", "PRODUCTOS DEL RANKING", "ÍNDICE DEL VÍDEO", "TIMESTAMPS:", "En este vídeo:"]

for line in ollama_desc.split("\n"):
    line_str = line.strip()
    if any(kw in line_str for kw in stop_keywords):
        break
    if "[link]" in line_str.lower() or "[producto]" in line_str.lower() or "[precio]" in line_str.lower():
        continue
    clean_ollama_lines.append(line)

ollama_desc = "\n".join(clean_ollama_lines).strip()

if not ollama_desc or len(ollama_desc) < 30:
    clean_q_desc = query.replace("_", " ").strip()
    ollama_desc = f"¿Buscas los mejores {clean_q_desc} de Amazon España? Comparativa exhaustiva 2026 con opiniones y precios actualizados para elegir bien."

hashtag_clean = re.sub(r'[^a-zA-Z0-9]', '', query.title())

# 2. Build description for TOP N FORMAT
desc_lines = [
    ollama_desc,
    "",
    "⏱️ ÍNDICE DEL VÍDEO",
    "────────────────────────────────────────",
    "0:00 🎬 Introducción"
]

sec_offset = 45
emojis = ["7️⃣", "6️⃣", "5️⃣", "4️⃣", "🥉", "🥈", "🥇"]
for idx, p in enumerate(products, 1):
    p_title = p.get("title", f"Producto #{idx}")
    m = sec_offset // 60
    s = sec_offset % 60
    emoji_num = emojis[idx - 1] if idx <= len(emojis) else f"#{idx}"
    desc_lines.append(f"{m}:{s:02d} {emoji_num} Puesto #{idx} — {p_title[:55]}")
    sec_offset += 65

desc_lines.extend([
    f"{sec_offset//60}:{sec_offset%60:02d} 🎤 Conclusión y enlaces",
    "",
    "🛒 PRODUCTOS DEL RANKING",
    "────────────────────────────────────────"
])

for idx, p in enumerate(products, 1):
    p_title = p.get("title", f"Producto #{idx}")
    p_price = p.get("price", "")
    p_rating = p.get("rating", "")
    p_asin = p.get("asin", "")
    p_url = p.get("url", "")

    if p_asin:
        clean_url = f"https://www.amazon.es/dp/{p_asin}?tag={affiliate_tag}" if affiliate_tag else f"https://www.amazon.es/dp/{p_asin}"
    elif p_url:
        clean_url = re.sub(r'\?tag=.*$', '', p_url).rstrip('/')
        if affiliate_tag:
            clean_url += f"?tag={affiliate_tag}"
    else:
        clean_url = ""

    emoji_num = emojis[idx - 1] if idx <= len(emojis) else f"#{idx}"
    desc_lines.append(f"{emoji_num} PUESTO #{idx} — {p_title}")
    if p_price:
        desc_lines.append(f"   💰 Precio aprox: {p_price}")
    if p_rating:
        desc_lines.append(f"   ⭐ Valoración: {p_rating}")
    if clean_url:
        desc_lines.append(f"   🔗 {clean_url}")
    desc_lines.append("")

hashtags_str = f"#{hashtag_clean} #AmazonAfiliados #MejoresOfertas"

desc_lines.extend([
    "────────────────────────────────────────",
    "👍 Si te ha sido útil, ¡dale al LIKE y SUSCRÍBETE para no perderte más rankings!",
    "🔔 Activa la campanita para recibir notificaciones de nuevos vídeos.",
    "",
    "📌 AVISO DE AFILIADOS",
    "Este vídeo contiene enlaces de afiliado de Amazon. Si compras a través de ellos, recibo una pequeña comisión sin coste adicional para ti. Gracias por apoyar el canal.",
    "",
    hashtags_str
])
description = "\n".join(desc_lines)

# Enforce affiliate tag on all Amazon URLs in description
if affiliate_tag:
    description = enforce_affiliate_tags_in_text(description, affiliate_tag)

# Enforce strict YouTube 5000 character limit (truncate at 4900 to be 100% safe)
if len(description) > 4900:
    description = description[:4890].rsplit("\n", 1)[0] + "\n\n#AmazonAfiliados #MejoresOfertas"

# Preserve existing tags if present in ollama_meta
existing_tags = ollama_meta.get("tags", [])

# Build high-converting pinned comment
pinned_comment = ollama_meta.get("pinned_comment", "").strip()
if not pinned_comment:
    c_lines = [
        f"🔥 ENLACES CON DESCUENTO ACTIVO Y OFERTAS ({query.upper()} 2026):",
        ""
    ]
    for idx, p in enumerate(products, 1):
        p_title = p.get("title", f"Producto #{idx}")[:40].strip()
        p_price = p.get("price", "")
        p_asin = p.get("asin", "")
        p_url = p.get("url", "")
        if p_asin:
            clean_u = f"https://www.amazon.es/dp/{p_asin}?tag={affiliate_tag}" if affiliate_tag else f"https://www.amazon.es/dp/{p_asin}"
        elif p_url:
            clean_u = re.sub(r'\?tag=.*$', '', p_url).rstrip('/')
            if affiliate_tag: clean_u += f"?tag={affiliate_tag}"
        else:
            clean_u = ""
        emoji_num = emojis[idx - 1] if idx <= len(emojis) else f"#{idx}"
        price_txt = f" [{p_price}]" if p_price and "consultar" not in p_price.lower() else ""
        if clean_u:
            c_lines.append(f"{emoji_num} Puesto #{idx} ({p_title}){price_txt}: {clean_u}")
    c_lines.append("")
    c_lines.append("⚠️ NOTA: Los precios y cupones de descuento en Amazon España varían constantemente. Revisa el enlace para ver el precio actualizado.")
    c_lines.append("💬 ¿Cuál es tu modelo favorito del top? ¡Déjanos tu opinión en los comentarios!")
    pinned_comment = "\n".join(c_lines)

if affiliate_tag:
    pinned_comment = enforce_affiliate_tags_in_text(pinned_comment, affiliate_tag)

meta_out = {
    "youtube_title": title,
    "youtube_description": description,
    "query": query,
    "title": title,
    "description": description,
    "pinned_comment": pinned_comment
}
if existing_tags:
    meta_out["tags"] = existing_tags

with open(meta_file, 'w', encoding='utf-8') as f:
    json.dump(meta_out, f, indent=2, ensure_ascii=False)

try:
    with open('/tmp/current_project_dir.txt', 'w', encoding='utf-8') as f:
        f.write(os.path.abspath(project_dir))
except Exception:
    pass

with open(meta_txt, 'w', encoding='utf-8') as f:
    f.write(f"TÍTULO:\n{title}\n\nDESCRIPCIÓN:\n{description}\n")

print(json.dumps(meta_out, ensure_ascii=False))
