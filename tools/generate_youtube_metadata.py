#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""
generate_youtube_metadata.py
Genera título y descripción optimizados para YouTube a partir de data.json.
Los productos se muestran en orden de cuenta atrás (mayor rank → menor rank).
Los enlaces son los de Amazon directos; el usuario los convertirá a afiliados.
"""

import sys
import os
import json
import argparse
import re
from datetime import datetime

# ── Emojis de posición para el countdown ──────────────────────────────────────
RANK_EMOJIS = {
    1: "🥇", 2: "🥈", 3: "🥉",
    4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 7: "7️⃣",
    8: "8️⃣", 9: "9️⃣", 10: "🔟",
}

def rank_emoji(rank: int) -> str:
    return RANK_EMOJIS.get(rank, f"#{rank}")

def clean_title(title: str, max_len: int = 80) -> str:
    """Acorta el título del producto para que quede limpio en la descripción."""
    if len(title) <= max_len:
        return title
    # Corta en el último espacio antes del límite
    cut = title[:max_len].rsplit(" ", 1)[0]
    return cut + "…"

def generate_youtube_title(data: dict) -> str:
    """
    Genera un título llamativo y optimizado para YouTube (< 95 caracteres max API limit).
    Combina psicología de Loss Aversion, Curiosity y SEO transaccional de alto CTR.
    """
    import re
    query = data.get("query", "productos").strip().replace("_", " ")
    clean_q = re.sub(r'^(mejores|aparatos eléctricos de|los mejores)\s+', '', query, flags=re.IGNORECASE).strip().upper()
    n = len(data.get("products", [])) or 7
    year = datetime.now().year

    canal_nombre = (data.get("canal_nombre", "") or data.get("channel_name", "")).lower()
    query_lower = query.lower()
    is_cocina = "cocina" in canal_nombre or "cocina" in query_lower or any(k in query_lower for k in [
        "freidora", "cafetera", "robot", "batidora", "horno", "olla", "tostadora", "sandwichera",
        "plancha", "arrocera", "licuadora", "picadora", "espumador", "crepera", "parrilla"
    ])

    if is_cocina:
        # Modificadores de alta conversión exigidos para Cocina:
        # '¿Cuál Comprar?', 'Precio y Opiniones Reales', 'Duelo Calidad Precio 2026', 'No Tires Tu Dinero'
        cand_buy = f"¿Cuál Comprar? TOP {n} {clean_q} ({year}) 🏆"
        cand_duel = f"TOP {n} {clean_q}: Duelo Calidad Precio {year} 🏆"
        cand_warn = f"No Tires Tu Dinero: TOP {n} {clean_q} ({year}) 🏆"
        cand_opinions = f"TOP {n} {clean_q} (Precio y Opiniones Reales) 🏆"

        if len(cand_buy) <= 90:
            res_t = cand_buy
        elif len(cand_duel) <= 90:
            res_t = cand_duel
        elif len(cand_warn) <= 90:
            res_t = cand_warn
        elif len(cand_opinions) <= 90:
            res_t = cand_opinions
        else:
            max_q_len = max(10, 90 - len(f"¿Cuál Comprar? TOP {n}  ({year}) 🏆"))
            short_q = clean_q[:max_q_len].rsplit(" ", 1)[0]
            res_t = f"¿Cuál Comprar? TOP {n} {short_q} ({year}) 🏆"
    else:
        cand1 = f"NO Compres {clean_q} sin Ver Esto (TOP {n} {year}) 🏆"
        cand2 = f"TOP {n} MEJORES {clean_q} {year} (Calidad/Precio) 🏆"
        title_cand = f"TOP {n} MEJORES {clean_q} {year} 🏆"

        if len(cand1) <= 90:
            res_t = cand1
        elif len(cand2) <= 90:
            res_t = cand2
        elif len(title_cand) <= 90:
            res_t = title_cand
        else:
            max_q_len = max(10, 90 - len(f"TOP {n} MEJORES  {year} 🏆"))
            short_q = clean_q[:max_q_len].rsplit(" ", 1)[0]
            res_t = f"TOP {n} MEJORES {short_q} {year} 🏆"

    try:
        from campaign_manager import get_active_campaign, apply_campaign_title
        _camp = get_active_campaign()
        if _camp:
            res_t = apply_campaign_title(res_t, _camp, max_len=95)
    except Exception:
        pass
    return res_t[:95]

def build_affiliate_url(product_url: str, affiliate_tag: str) -> str:
    """Convierte una URL de Amazon en link de afiliado si se proporciona el tag."""
    if not affiliate_tag:
        return product_url
    import re
    asin_match = re.search(r'/dp/([A-Z0-9]{10})', product_url)
    if asin_match:
        asin = asin_match.group(1)
        return f"https://www.amazon.es/dp/{asin}?tag={affiliate_tag}"
    sep = "&" if "?" in product_url else "?"
    return f"{product_url}{sep}tag={affiliate_tag}"


def extract_description_highlights(p: dict) -> list:
    """Extrae hasta 2 puntos fuertes para la descripción de YouTube."""
    highlights = []
    features = p.get('features', [])
    if isinstance(features, list) and features:
        for f in features:
            txt = re.sub(r'\s+', ' ', str(f)).strip().rstrip('.')
            if len(txt) > 15 and not any(ign in txt.lower() for ign in ['garantía', 'aviso', 'política', 'más información']) and txt not in highlights:
                if len(txt) > 90:
                    txt = txt[:90].rsplit(' ', 1)[0]
                highlights.append(txt)
                if len(highlights) >= 2:
                    break

    if len(highlights) < 2 and isinstance(p.get('specs'), dict):
        specs = p.get('specs', {})
        spec_items = []
        for k, v in specs.items():
            if not k or not v: continue
            k_c = str(k).strip()
            v_c = str(v).strip()
            if len(k_c) < 30 and len(v_c) < 35 and not any(ign in k_c.lower() for ign in ['opiniones', 'clasificación', 'asin', 'dimensiones', 'fabricante']):
                spec_items.append(f"{k_c}: {v_c}")
            if len(spec_items) >= 2:
                break
        if spec_items:
            highlights.append(" | ".join(spec_items))

    return highlights[:2]

def extract_community_verdict(p: dict) -> str:
    """Extrae o resume la opinión de la comunidad de compradores verificados."""
    top_reviews = p.get('top_reviews', [])
    if isinstance(top_reviews, list) and top_reviews:
        for r in top_reviews:
            if not isinstance(r, dict): continue
            text = str(r.get('text', '')).strip()
            title = str(r.get('title', '')).strip()
            cand = text if len(text) > 20 else title
            cand = cand.replace('Leer másLeer menos', '').replace('Super ', 'Súper ').strip()
            if len(cand) > 15:
                cand_clean = re.sub(r'\s+', ' ', cand)
                if len(cand_clean) > 120:
                    cand_clean = cand_clean[:120].rsplit(' ', 1)[0] + '…'
                return cand_clean
    return "Muy valorado por su fiabilidad, confort de uso y gran relación calidad-precio."

def generate_youtube_description(data: dict, affiliate_tag: str = "") -> str:
    """
    Genera la descripción completa de YouTube con:
    - Meta descripción inicial (<160 chars) optimizada para SEO / AI Overviews
    - Sección de timestamps (si hay duración en data.json)
    - Lista de productos con link y precio
    - Disclaimer de afiliados y CTA
    """
    products = data.get("products", [])
    query = data.get("query", "productos")
    sorted_products = sorted(products, key=lambda x: x.get("rank", 1), reverse=True)

    lines = []
    # Above-the-fold mobile winner banner (máxima conversión móvil inmediata)
    top_winner = next((p for p in products if p.get("rank") == 1), None)
    if top_winner:
        top_u = build_affiliate_url(top_winner.get("product_url", ""), affiliate_tag)
        top_title = clean_title(top_winner.get("title", "Ganador #1"), 45)
        lines.append(f"⭐ MEJOR OPCIÓN CALIDAD/PRECIO (#1 {top_title}): {top_u}")
        lines.append("⬇️ Despliega abajo para ver los 7 modelos y precios actualizados ⬇️")
        lines.append("")

    # Meta descripción (<160 chars para SERP / AI Overview snippet)
    lines.append(f"¿Buscas los mejores {query.lower()} de Amazon España? Comparativa exhaustiva 2026 con opiniones y precios actualizados para elegir bien.")
    lines.append("")

    durations = data.get("durations", {})
    hook_dur = durations.get("hook", 0)
    product_durs = durations.get("products", [])

    if hook_dur and product_durs:
        lines.append("⏱️ ÍNDICE DEL VÍDEO")
        lines.append("─" * 40)

        def fmt_time(seconds: float) -> str:
            s = int(seconds)
            return f"{s // 60}:{s % 60:02d}"

        cursor = 0.0
        lines.append(f"{fmt_time(cursor)} 🎬 Introducción")
        cursor += hook_dur

        rank_to_dur = {}
        for i, dur in enumerate(product_durs):
            rank_to_dur[i + 1] = dur

        for p in sorted_products:
            rank = p.get("rank", 1)
            dur = rank_to_dur.get(rank, 0)
            short = clean_title(p.get("title", ""), 55)
            lines.append(f"{fmt_time(cursor)} {rank_emoji(rank)} Puesto #{rank} — {short}")
            cursor += dur

        outro_dur = durations.get("outro", 0)
        lines.append(f"{fmt_time(cursor)} 🎤 Conclusión y enlaces")
        lines.append("")

    # Lista de productos
    lines.append("🛒 PRODUCTOS DEL RANKING")
    lines.append("─" * 40)
    lines.append("")

    for p in sorted_products:
        rank = p.get("rank", 1)
        emoji = rank_emoji(rank)
        title = clean_title(p.get("title", f"Producto #{rank}"), 80)
        price = p.get("price", "")
        rating = p.get("rating", "")
        url = p.get("product_url", "")

        lines.append(f"{emoji} PUESTO #{rank} — {title}")
        if price and price.lower() != "consultar en amazon":
            lines.append(f"   💰 Precio aprox: {price}")
        if rating:
            lines.append(f"   ⭐ Valoración: {rating}")
            
        highlights = extract_description_highlights(p)
        for h in highlights:
            lines.append(f"   ✓ {h}")
            
        verdict = extract_community_verdict(p)
        if verdict:
            lines.append(f"   💬 Opinión de la comunidad: {verdict}")
            
        if url:
            affiliate_url = build_affiliate_url(url, affiliate_tag)
            lines.append(f"   🔗 {affiliate_url}")
        lines.append("")

    # Call to action & aviso afiliados
    lines.append("─" * 40)
    lines.append("👍 Si te ha sido útil, ¡dale al LIKE y SUSCRÍBETE para no perderte más rankings!")
    lines.append("🔔 Activa la campanita para recibir notificaciones de nuevos vídeos.")
    lines.append("")
    lines.append("📌 AVISO DE AFILIADOS")
    lines.append("Este vídeo contiene enlaces de afiliado de Amazon. Si compras a través de ellos, recibo una pequeña comisión sin coste adicional para ti. Gracias por apoyar el canal.")

    return "\n".join(lines)

def generate_pinned_comment(data: dict, affiliate_tag: str = "") -> str:
    """Genera un comentario fijado de alta conversión con enlaces directos para móvil."""
    products = data.get("products", [])
    query = data.get("query", "productos").strip().replace("_", " ")
    sorted_prods = sorted(products, key=lambda x: x.get("rank", 1))
    c_lines = [
        f"🔥 ENLACES CON DESCUENTO ACTIVO Y OFERTAS ({query.upper()} 2026):",
        ""
    ]
    for p in sorted_prods:
        rank = p.get("rank", 1)
        emoji = rank_emoji(rank)
        title = clean_title(p.get("title", f"Producto #{rank}"), 40)
        raw_url = p.get("product_url", "")
        aff_url = build_affiliate_url(raw_url, affiliate_tag)
        price = p.get("price", "")
        price_txt = f" [{price}]" if price and "consultar" not in price.lower() else ""
        c_lines.append(f"{emoji} Puesto #{rank} ({title}){price_txt}: {aff_url}")
    c_lines.append("")
    c_lines.append("⚠️ NOTA: Los precios y cupones de descuento en Amazon España varían constantemente. Revisa el enlace para ver el precio actualizado.")
    c_lines.append("💬 ¿Cuál es tu modelo favorito del top? ¡Déjanos tu opinión en los comentarios!")
    return "\n".join(c_lines)


def main(project_dir: str, output_file: str = None, affiliate_tag: str = ""):
    data_json = os.path.join(project_dir, "data.json")
    if not os.path.exists(data_json):
        print(f"ERROR: No se encontró data.json en {project_dir}", file=sys.stderr)
        sys.exit(1)

    with open(data_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    title = generate_youtube_title(data)
    description = generate_youtube_description(data, affiliate_tag=affiliate_tag)


    pinned_comment = generate_pinned_comment(data, affiliate_tag)
    result = {
        "youtube_title": title,
        "youtube_description": description,
        "pinned_comment": pinned_comment,
        "product_links": [
            {
                "rank": p["rank"],
                "title": p["title"],
                "price": p.get("price", ""),
                "rating": p.get("rating", ""),
                "asin": p.get("asin", ""),
                "url": p.get("product_url", ""),
            }
            for p in sorted(data.get("products", []), key=lambda x: x["rank"], reverse=True)
        ]
    }

    # Save to file (preserve existing tags or keys if present)
    out_path = output_file or os.path.join(project_dir, "youtube_metadata.json")
    existing_meta = {}
    if os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                existing_meta = json.load(f)
        except Exception:
            pass

    existing_meta.update(result)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(existing_meta, f, ensure_ascii=False, indent=2)

    # Also save a human-readable .txt for easy copy-paste
    txt_path = out_path.replace(".json", ".txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("═" * 60 + "\n")
        f.write("TÍTULO DE YOUTUBE\n")
        f.write("═" * 60 + "\n")
        f.write(title + "\n\n")
        f.write("═" * 60 + "\n")
        f.write("DESCRIPCIÓN DE YOUTUBE\n")
        f.write("═" * 60 + "\n")
        f.write(description + "\n")

    print(json.dumps(result, ensure_ascii=False))
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genera metadatos de YouTube desde data.json")
    parser.add_argument("--project_dir", required=True, help="Directorio del proyecto (contiene data.json)")
    parser.add_argument("--output", default=None, help="Ruta de salida del JSON (opcional)")
    parser.add_argument("--affiliate_tag", default="", help="Tag de afiliado Amazon (ej: cocina_tag-21)")
    args = parser.parse_args()
    main(args.project_dir, args.output, args.affiliate_tag)
