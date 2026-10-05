#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""
save_vs_youtube_metadata.py
Formatea y guarda metadatos de YouTube específicos para vídeos comparativos A vs B.
Soporta automáticamente todas las temáticas y canales (Cocina, Limpieza, Calzado, Librería, etc.).
"""
import sys
import os
import json
import re
import argparse

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
    if ":" in t and len(t) > 30:
        t = t.split(":")[0].strip()
    if "-" in t and len(t) > 30:
        t = t.split("-")[0].strip()
    if "," in t and len(t) > 30:
        t = t.split(",")[0].strip()
    return t.strip()

def enforce_affiliate_tags_in_text(text: str, tag: str) -> str:
    if not tag:
        return text
    def repl(m):
        asin = m.group(1)
        return f"https://www.amazon.es/dp/{asin}?tag={tag}"
    return re.sub(r'https?://(?:www\.)?amazon\.es/dp/([A-Z0-9]{10})(?:\?[^\s\n]*)?', repl, text)

def get_niche_config(canal_nombre, query):
    canal_lower = (canal_nombre or "").lower()
    query_lower = (query or "").lower()
    
    if "barberia" in canal_lower or "afeitad" in query_lower or "barba" in query_lower or "cortapelo" in query_lower:
        return {
            "channel_brand": "La Barbería del Pueblo",
            "unit_word": "máquinas de afeitar y cortapelos",
            "section_header": "🛒 MODELOS DE AFEITADO COMPARADOS",
            "cta_sub": "👍 ¡Regálanos un LIKE y SUSCRÍBETE a La Barbería del Pueblo para más comparativas!",
            "comment_ask": "💬 ¿Cuál de estas dos máquinas prefieres para tu afeitado? ¡Déjanos tu voto A o B en los comentarios!",
            "hashtags": "#LaBarberíaDelPueblo #Afeitado #Cortapelos #Amazon"
        }
    elif "cocina" in canal_lower or "cocina" in query_lower or "freidora" in query_lower or "robot" in query_lower or "gofrera" in query_lower:
        return {
            "channel_brand": "La Cocina Tecnológica del Pueblo",
            "unit_word": "electrodomésticos y aparatos de cocina",
            "section_header": "🛒 PRODUCTOS COMPARADOS EN EL VÍDEO",
            "cta_sub": "👍 ¡Regálanos un LIKE y SUSCRÍBETE a La Cocina Tecnológica del Pueblo para más comparativas!",
            "comment_ask": "💬 ¿Cuál de estos dos productos prefieres para tu cocina? ¡Déjanos tu voto A o B en los comentarios!",
            "hashtags": "#CocinaTecnológica #Electrodomésticos #Comparativa #Amazon"
        }
    elif "limpieza" in canal_lower or "limpieza" in query_lower or "aspiradora" in query_lower or "vaporeta" in query_lower or "mopa" in query_lower:
        return {
            "channel_brand": "Limpieza del Pueblo",
            "unit_word": "aparatos de limpieza y hogar",
            "section_header": "🛒 PRODUCTOS DE LIMPIEZA COMPARADOS",
            "cta_sub": "👍 ¡Regálanos un LIKE y SUSCRÍBETE a Limpieza del Pueblo para más comparativas!",
            "comment_ask": "💬 ¿Cuál de estos dos productos encaja mejor en tu hogar? ¡Déjanos tu voto A o B en los comentarios!",
            "hashtags": "#LimpiezaDelPueblo #AparatosDeLimpieza #Comparativa #Amazon"
        }
    elif "calzado" in canal_lower or "zapato" in query_lower or "zapatillas" in query_lower or "botas" in query_lower:
        return {
            "channel_brand": "Calzado del Pueblo",
            "unit_word": "modelos de calzado",
            "section_header": "🛒 ZAPATOS COMPARADOS EN EL VÍDEO",
            "cta_sub": "👍 ¡Regálanos un LIKE y SUSCRÍBETE a Calzado del Pueblo para más comparativas!",
            "comment_ask": "💬 ¿Cuál de estos dos pares de zapatos te gusta más? ¡Déjanos tu voto A o B en los comentarios!",
            "hashtags": "#CalzadoDelPueblo #Zapatos #Comparativa #Amazon"
        }
    elif "librería" in canal_lower or "libro" in query_lower or "libreria" in canal_lower:
        return {
            "channel_brand": "Librería Del Pueblo",
            "unit_word": "libros y lecturas",
            "section_header": "🛒 LIBROS COMPARADOS EN EL VÍDEO",
            "cta_sub": "👍 ¡Regálanos un LIKE y SUSCRÍBETE a Librería Del Pueblo para más comparativas literarias!",
            "comment_ask": "💬 ¿Cuál de estos dos libros te llama más la atención? ¡Déjanos tu voto A o B en los comentarios!",
            "hashtags": "#LibreriaDelPueblo #Libros #ComparativaLiteraria #Amazon"
        }
    elif "taller" in canal_lower or "herramienta" in query_lower or "taladro" in query_lower or "sierra" in query_lower or "cepillo" in query_lower or "lijadora" in query_lower:
        return {
            "channel_brand": "El Taller Del Pueblo",
            "unit_word": "herramientas y maquinaria de taller",
            "section_header": "🛒 HERRAMIENTAS COMPARADAS EN EL VÍDEO",
            "cta_sub": "👍 ¡Regálanos un LIKE y SUSCRÍBETE a El Taller Del Pueblo para más comparativas de herramientas!",
            "comment_ask": "💬 ¿Cuál de estas dos herramientas prefieres para tus proyectos? ¡Déjanos tu voto A o B en los comentarios!",
            "hashtags": "#ElTallerDelPueblo #Herramientas #Bricolaje #Comparativa #Amazon"
        }
    else:
        brand = canal_nombre.replace("_", " ").title() if canal_nombre else "Comparativas Amazon"
        return {
            "channel_brand": brand,
            "unit_word": query if query else "productos",
            "section_header": "🛒 PRODUCTOS COMPARADOS EN EL VÍDEO",
            "cta_sub": f"👍 ¡Regálanos un LIKE y SUSCRÍBETE a {brand} para más comparativas!",
            "comment_ask": "💬 ¿Cuál de estos dos productos elegirías tú? ¡Déjanos tu voto A o B en los comentarios!",
            "hashtags": "#Comparativa #Amazon #Afiliados"
        }

def make_safe_tag(text, max_len=20):
    clean = re.sub(r'[^a-zA-Z0-9]', '', text or "")
    return clean[:max_len] if clean else ""

def main():
    parser = argparse.ArgumentParser(description="Formatea y guarda metadatos de YouTube para comparativas VS")
    parser.add_argument("project_dir", nargs="?", default=".", help="Directorio del proyecto")
    parser.add_argument("--affiliate_tag", default="", help="Tag de afiliado de Amazon")
    args, unknown = parser.parse_known_args()

    project_dir = args.project_dir.strip()
    tag_arg = args.affiliate_tag.strip()

    meta_file = os.path.join(project_dir, "youtube_metadata.json")
    meta_txt = os.path.join(project_dir, "youtube_metadata.txt")
    data_file = os.path.join(project_dir, "data.json")

    data_obj = {}
    if os.path.exists(data_file):
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                data_obj = json.load(f)
        except Exception:
            pass

    query = clean_text(data_obj.get("query", "").replace("_", " "))
    canal_nombre = data_obj.get("canal_nombre", "") or data_obj.get("channel_name", "")
    affiliate_tag = tag_arg or data_obj.get("affiliate_tag", "")

    niche = get_niche_config(canal_nombre, query)

    product_a = data_obj.get("product_a", {})
    product_b = data_obj.get("product_b", {})
    
    brand_a = clean_brand_name(product_a.get("brand", ""))
    brand_b = clean_brand_name(product_b.get("brand", ""))
    
    title_a = clean_product_title(product_a.get("title", "Producto A"))
    title_b = clean_product_title(product_b.get("title", "Producto B"))

    canal_lower = (canal_nombre or "").lower()
    query_lower = (query or "").lower()
    is_cocina = "cocina" in canal_lower or "cocina" in query_lower or any(k in query_lower for k in [
        "freidora", "cafetera", "robot", "batidora", "horno", "olla", "tostadora", "sandwichera",
        "plancha", "arrocera", "licuadora", "picadora", "espumador", "crepera", "parrilla"
    ])

    if is_cocina:
        # Modificadores de alta conversión para Cocina:
        # '¿Cuál Comprar?', 'Precio y Opiniones Reales', 'Duelo Calidad Precio 2026', 'No Tires Tu Dinero'
        cand_buy = f"{brand_a} vs {brand_b}: ¿Cuál Comprar? (2026) ⚔️"
        cand_duel = f"{brand_a} vs {brand_b}: Duelo Calidad Precio 2026 ⚔️"
        cand_money = f"No Tires Tu Dinero: {brand_a} vs {brand_b} (2026) ⚔️"
        cand_opinions = f"{brand_a} vs {brand_b}: Precio y Opiniones Reales ⚔️"

        if brand_a and brand_b and brand_a.lower() != brand_b.lower():
            if len(cand_buy) <= 90:
                title = cand_buy
            elif len(cand_duel) <= 90:
                title = cand_duel
            elif len(cand_money) <= 90:
                title = cand_money
            elif len(cand_opinions) <= 90:
                title = cand_opinions
            else:
                title = f"{brand_a} vs {brand_b}: ¿Cuál Comprar? ⚔️"
        else:
            title = f"{title_a[:30]} vs {title_b[:30]}: ¿Cuál Comprar? ⚔️"
    else:
        cand_duel = f"{brand_a} vs {brand_b}: ¿Cuál Merece Más la Pena? (2026) ⚔️"
        cand_warn = f"NO Elijas entre {brand_a} y {brand_b} sin Ver Esto (2026) ⚔️"
        if brand_a and brand_b and brand_a.lower() != brand_b.lower() and len(cand_warn) <= 90:
            title = cand_warn
        elif brand_a and brand_b and brand_a.lower() != brand_b.lower() and len(cand_duel) <= 90:
            title = cand_duel
        elif len(f"{title_a[:35]} vs {title_b[:35]} ⚔️ COMPARATIVA 2026") <= 90:
            title = f"{title_a[:35]} vs {title_b[:35]} ⚔️ COMPARATIVA 2026"
        else:
            title = f"{title_a[:28]} vs {title_b[:28]} ⚔️ Comparativa {query.title()}"

    title = clean_text(title)[:95]
    try:
        from campaign_manager import get_active_campaign, apply_campaign_title
        _camp = get_active_campaign()
        if _camp:
            title = apply_campaign_title(title, _camp, max_len=95)
    except Exception:
        pass

    asin_a = product_a.get("asin", "")
    asin_b = product_b.get("asin", "")
    url_a = f"https://www.amazon.es/dp/{asin_a}?tag={affiliate_tag}" if asin_a and affiliate_tag else product_a.get("product_url", "")
    url_b = f"https://www.amazon.es/dp/{asin_b}?tag={affiliate_tag}" if asin_b and affiliate_tag else product_b.get("product_url", "")

    label_a = f"{title_a} ({brand_a})" if brand_a else title_a
    label_b = f"{title_b} ({brand_b})" if brand_b else title_b

    tag_a_clean = make_safe_tag(brand_a or title_a)
    tag_b_clean = make_safe_tag(brand_b or title_b)
    safe_hashtags = f"#{tag_a_clean}vs{tag_b_clean} {niche['hashtags']}" if tag_a_clean and tag_b_clean else niche['hashtags']

    desc_lines = [
        f"🔥 ENLACES OFICIALES CON OFERTA ACTIVA (Amazon 2026):",
        f"👉 Opción A ({label_a}): {url_a}",
        f"👉 Opción B ({label_b}): {url_b}",
        f"⬇️ Despliega abajo para ver el análisis técnico y opiniones reales ⬇️",
        "",
        f"⚔️ COMPARATIVA FRENTE A FRENTE: {label_a} vs {label_b}",
        f"Analizamos en profundidad dos de las mejores opciones de {niche['unit_word']} en Amazon España ({query}): puntos fuertes, características clave, opiniones de compradores y cuál merece la pena comprar.",
        "",
        "⏱️ ÍNDICE DEL VÍDEO",
        "────────────────────────────────────────",
        "0:00 🎬 Introducción y Planteamiento",
        f"0:45 🅰️ Análisis en profundidad: {label_a}",
        f"2:30 💬 Opiniones y valoraciones reales: {title_a}",
        f"4:15 🅱️ Análisis en profundidad: {label_b}",
        f"6:00 💬 Opiniones y valoraciones reales: {title_b}",
        "7:45 ⚔️ Comparativa cara a cara y Recomendación final",
        "",
        niche['section_header'],
        "────────────────────────────────────────",
        f"🅰️ OPCIÓN A: {title_a} — {brand_a if brand_a else niche['channel_brand']}",
        f"   💰 Precio aprox: {product_a.get('price', 'Consultar')}",
        f"   ⭐ Valoración: {product_a.get('rating', '4.5')}",
        f"   🔗 Ver en Amazon: {url_a}",
        "",
        f"🅱️ OPCIÓN B: {title_b} — {brand_b if brand_b else niche['channel_brand']}",
        f"   💰 Precio aprox: {product_b.get('price', 'Consultar')}",
        f"   ⭐ Valoración: {product_b.get('rating', '4.5')}",
        f"   🔗 Ver en Amazon: {url_b}",
        "",
        "────────────────────────────────────────",
        niche['comment_ask'],
        niche['cta_sub'],
        "",
        "📌 AVISO DE AFILIADOS",
        "Este vídeo contiene enlaces de afiliado de Amazon. Si compras a través de ellos, recibo una pequeña comisión sin coste adicional para ti. Gracias por apoyar el canal.",
        "",
        safe_hashtags
    ]

    description = "\n".join(desc_lines)
    if affiliate_tag:
        description = enforce_affiliate_tags_in_text(description, affiliate_tag)

    raw_tags = [
        query.lower(), f"{query.lower()} comparativa", f"{query.lower()} opiniones", f"mejor {query.lower()} 2026",
        title_a[:35], title_b[:35], f"{title_a[:20]} vs {title_b[:20]}",
        niche['channel_brand'].lower(), "resena y opinion", "guia de compra"
    ]
    if brand_a: raw_tags.append(brand_a)
    if brand_b: raw_tags.append(brand_b)

    tags = [clean_text(t) for t in raw_tags if clean_text(t)]
    tags_str = ",".join(tags)

    pinned_comment = (
        f"🥇 MEJOR OPCIÓN CALIDAD/PRECIO:\n"
        f"👉 {title_a}: {url_a}\n\n"
        f"⚡ MÁXIMA POTENCIA / GAMA TOP:\n"
        f"👉 {title_b}: {url_b}\n\n"
        "📌 Los precios y ofertas pueden cambiar según disponibilidad de Amazon Prime."
    )
    meta_out = {
        "youtube_title": title,
        "youtube_description": description,
        "pinned_comment": pinned_comment,
        "query": query,
        "title": title,
        "description": description,
        "tags": tags,
        "tags_str": tags_str
    }

    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump(meta_out, f, indent=2, ensure_ascii=False)

    with open(meta_txt, 'w', encoding='utf-8') as f:
        f.write(f"TÍTULO:\n{title}\n\nDESCRIPCIÓN:\n{description}\n")

    print(json.dumps(meta_out, ensure_ascii=False))

if __name__ == "__main__":
    main()
