#!/usr/bin/env python3
import sys
import os
import json
import re

def clean_sentence_end(text: str) -> str:
    text = re.sub(r'\s+', ' ', text).strip().rstrip('.,;:/-')
    dangling = {'y', 'e', 'o', 'u', 'de', 'del', 'con', 'en', 'para', 'por', 'a', 'que', 'su', 'sus', 'al', 'el', 'la', 'los', 'las'}
    words = text.split()
    while words and words[-1].lower().rstrip('.,;:/-') in dangling:
        words.pop()
    return " ".join(words).strip('.,;:/- ')

def clean_product_title(title: str, max_len: int = 48) -> str:
    t = re.sub(r'\(.*?\)', '', title)
    t = re.sub(r'\[.*?\]', '', t)
    t = re.sub(r'[：:]', ' - ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    if len(t) <= max_len:
        cut = t
    else:
        cut = t[:max_len].rsplit(' ', 1)[0]
    return clean_sentence_end(cut)

def format_price_phrase(price) -> str:
    p = str(price).strip()
    if not p or p.lower() in ["consultar en amazon", "consultar precio", "none", "null", ""]:
        return "un precio muy ajustado disponible en la descripción"
    if "€" in p or any(c.isdigit() for c in p):
        return f"un precio aproximado de {p}"
    return "un precio muy competitivo en Amazon"

def format_specs_phrase(specs) -> str:
    if not specs or not isinstance(specs, dict):
        return ""
    valid = []
    for k, v in specs.items():
        if not k or not v:
            continue
        k_clean = str(k).strip()
        v_clean = str(v).strip().replace(',', ', ')
        v_clean = re.sub(r'\s+', ' ', v_clean)
        k_norm = re.sub(r'^(material de la|material del|material|tipo de|estilo de)\s+', '', k_clean, flags=re.IGNORECASE).strip()
        if k_norm and len(k_norm) < 25 and len(v_clean) < 35 and not any(ign in k_norm.lower() for ign in ['opiniones', 'clasificación', 'asin', 'dimensiones', 'fabricante', 'departamento']):
            valid.append(f"{k_norm.lower()} de {v_clean}")
    if not valid:
        return ""
    chosen = valid[:2]
    if len(chosen) == 1:
        return f"Destaca por su {chosen[0]}."
    return f"Sobresale por su {chosen[0]} y {chosen[1]}."

def format_features_phrase(features, desc_snippet="") -> str:
    if features and isinstance(features, list):
        cleaned = [re.sub(r'\s+', ' ', f).strip().rstrip('.') for f in features if len(f.strip()) > 15]
        if cleaned:
            feat = cleaned[0]
            feat = re.sub(r'^[^:：]{3,25}[:：]\s*', '', feat)
            if len(feat) > 95:
                feat = feat[:95].rsplit(' ', 1)[0]
            feat = clean_sentence_end(feat)
            if feat:
                return f"Ofrece {feat.lower()}."
    if desc_snippet:
        d = re.sub(r'\s+', ' ', desc_snippet).strip().rstrip('.')
        if len(d) > 95:
            d = d[:95].rsplit(' ', 1)[0]
        d = clean_sentence_end(d)
        if d:
            return f"Destaca por estar concebido para {d.lower()}."
    return "Ofrece un diseño ergonómico y resistente para uso continuo diario."

def format_reviews_phrase(top_reviews, rating, review_count) -> str:
    r_clean = str(rating).strip()
    if "de 5" in r_clean or "sobre 5" in r_clean:
        rating_str = r_clean
    elif r_clean:
        rating_str = f"{r_clean} sobre 5 estrellas"
    else:
        rating_str = "excelentes valoraciones"
    clean_count = re.sub(r'[^\d.,]', '', str(review_count)).strip()
    count_str = f"con más de {clean_count} opiniones" if clean_count else "muy respaldado por sus compradores"
    base_social = f"Acumula {rating_str} en Amazon, {count_str}."
    if top_reviews and isinstance(top_reviews, list):
        for r in top_reviews[:1]:
            if not isinstance(r, dict):
                continue
            text = r.get("text", "").strip()
            title = r.get("title", "").strip()
            phrase = text if len(text) > 15 else title
            phrase = phrase.replace("Leer másLeer menos", "").replace("Super ", "Súper ").strip()
            if len(phrase) > 15:
                clean_p = re.sub(r'\s+', ' ', phrase)
                if len(clean_p) > 75:
                    clean_p = clean_p[:75].rsplit(' ', 1)[0]
                clean_p = clean_sentence_end(clean_p)
                if clean_p:
                    return f"{base_social} Quienes lo usan destacan que '{clean_p.rstrip('.')}'."
    return f"{base_social} La mayoría de usuarios confirma su gran fiabilidad desde la primera semana."

OPENING_TEMPLATES = {
    1: "Llegamos al puesto número 1 con la {title}, la opción ganadora de nuestro ranking.",
    2: "En el puesto número 2 destaca con fuerza la {title}.",
    3: "Ocupando la tercera posición tenemos la {title}.",
    4: "Avanzamos al puesto número 4 analizando la {title}.",
    5: "En la quinta posición encontramos la {title}.",
    6: "Continuamos en el puesto número 6 con la {title}.",
    7: "Arrancamos en el puesto número 7 analizando la {title}."
}

CLOSING_TEMPLATES = [
    "Una elección inteligente para uso diario. Comprueba el stock en el enlace directo de la descripción.",
    "Solución equilibrada con materiales contrastados. Revisa la oferta activa abajo en el primer comentario.",
    "Excelente relación calidad precio en su gama. Consulta las opiniones completas en la descripción del vídeo."
]

def build_product_review(prod_info: dict, rank: int, query_title: str) -> str:
    raw_title = prod_info.get("title", f"Producto {rank}")
    short_title = clean_product_title(raw_title, max_len=45)
    price = prod_info.get("price", "Consultar en Amazon")
    rating = prod_info.get("rating", "4.5")
    review_count = prod_info.get("review_count", "")
    specs = prod_info.get("specs", {})
    features = prod_info.get("features", [])
    desc_snippet = prod_info.get("description_snippet", "")
    top_reviews = prod_info.get("top_reviews", [])
    
    price_phrase = format_price_phrase(price)
    specs_phrase = format_specs_phrase(specs)
    features_phrase = format_features_phrase(features, desc_snippet)
    reviews_phrase = format_reviews_phrase(top_reviews, rating, review_count)
    
    opening = OPENING_TEMPLATES.get(rank, f"En el puesto número {rank} encontramos la {short_title}.").format(title=short_title)
    closing = CLOSING_TEMPLATES[(rank - 1) % len(CLOSING_TEMPLATES)]
    
    highlight = reviews_phrase
    if specs_phrase:
        highlight += " " + specs_phrase
    else:
        highlight += " " + features_phrase

    parts = [
        opening,
        f"Se presenta con {price_phrase}, siendo muy atractiva por su fiabilidad demostrada.",
        highlight,
        closing
    ]
    
    full_text = " ".join(parts)
    words = full_text.split()
    
    if len(words) < 70:
        boost = "Una compra muy recomendada para quienes buscan el máximo rendimiento sin complicaciones."
        parts.insert(-1, boost)
        full_text = " ".join(parts)
        words = full_text.split()
        
    if len(words) > 85:
        sentences = re.split(r'(?<=[.?!])\s+', full_text)
        accum = []
        c = 0
        for s in sentences:
            s_words = len(s.split())
            if c + s_words <= 85 or len(accum) < 2:
                accum.append(s)
                c += s_words
            else:
                break
        if not any(cls_key in " ".join(accum) for cls_key in ["enlace", "comentario", "descripción", "opiniones", "oferta"]):
            accum.append(closing)
        full_text = " ".join(accum)
        words = full_text.split()
        if len(words) > 88 and len(accum) > 2:
            accum.pop(-2)
            full_text = " ".join(accum)
            
    return full_text

def main():
    if len(sys.argv) < 2:
        sys.exit(1)
    data_json_path = sys.argv[1]
    if not os.path.exists(data_json_path):
        sys.exit(1)
        
    with open(data_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    query = data.get("query", "productos").strip()
    query_title = query.lower()
    
    script = data.get("script", {})
    hook = script.get("hook", "").strip()
    products_script = script.get("products", [])
    outro = script.get("outro", "").strip()
    
    if not hook or len(hook.split()) < 35 or len(hook.split()) > 65 or "Looking for the perfect gift" in hook:
        hook = (
            f"Antes de gastar dinero en {query_title}, no compres a ciegas. "
            f"Analizamos más de 30 opciones en Amazon España para seleccionar los 7 modelos que merecen la pena en 2026. "
            f"Tienes los enlaces de descuento en el primer comentario fijado. "
            f"¡Comenzamos con el puesto 7!"
        )
        
    prods_info = data.get("products", [])
    enriched_products = []
    
    for i in range(len(prods_info)):
        prod_info = prods_info[i]
        rank = prod_info.get("rank", i + 1)
        curr_text = ""
        if i < len(products_script) and isinstance(products_script[i], str):
            c_cand = products_script[i].strip()
            if 65 <= len(c_cand.split()) <= 88 and "Looking for the perfect gift" not in c_cand and "precio aproximado de ," not in c_cand and "flexible y." not in c_cand:
                curr_text = c_cand
        if not curr_text:
            curr_text = build_product_review(prod_info, rank, query_title)
        enriched_products.append(curr_text)
        
    if not outro or len(outro.split()) < 30 or len(outro.split()) > 60 or "Looking for the perfect gift" in outro:
        outro = (
            f"Hasta aquí nuestro top 7 de {query_title} para 2026. "
            f"Tienes los enlaces directos y ofertas en tiempo real en el primer comentario fijado y en la descripción. "
            f"Comprueba el stock antes de que se agote y dinos tu favorito en comentarios."
        )
        
    data["script"] = {
        "hook": hook,
        "products": enriched_products,
        "outro": outro
    }
    
    with open(data_json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    hook_words = len(hook.split())
    prods_words = [len(p.split()) for p in enriched_products]
    outro_words = len(outro.split())
    total_words = hook_words + sum(prods_words) + outro_words
    
    print(json.dumps({
        "status": "enriched",
        "query": query,
        "hook_words": hook_words,
        "products_words": prods_words,
        "outro_words": outro_words,
        "total_words": total_words,
        "est_minutes": round(total_words / 135, 2)
    }))

if __name__ == "__main__":
    main()
