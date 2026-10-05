import threading
#!/usr/bin/env python3
import sys
import os
import json
import argparse
import re
import html
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from curl_cffi import requests
from bs4 import BeautifulSoup

KNOWN_BRANDS = [
    'bosch', 'einhell', 'makita', 'dewalt', 'stanley', 'black+decker', 'black & decker',
    'parkside', 'worx', 'ryobi', 'milwaukee', 'dremel', 'mannesmann', 'workpro',
    'teccpo', 'tacklife', 'hychika', 'bellota', 'stayer', 'fartools', 'cecotec',
    'hitachi', 'hikoki', 'festool', 'metabo', 'aeg', 'seeii', 'seesii', 'saker'
]

FOOTWEAR_ACCESSORY_REJECT_KEYWORDS = [
    'toallita', 'toallitas', 'toalla', 'toallas', 'wipe', 'wipes',
    'limpiador', 'limpiadora', 'limpiadores', 'limpiadoras', 'limpieza',
    'kit de limpieza', 'crep protect', 'tarrago', 'jason markk', 'cepillo', 'cepillos',
    'goma de borrar', 'betun', 'betún', 'crema para zapatos', 'crema de calzado',
    'grasa de caballo', 'cera para zapatos', 'tinte para calzado', 'spray impermeabilizante',
    'impermeabilizante', 'protector de calzado', 'desodorante para calzado', 'desodorante de zapatos',
    'ambientador para calzado', 'polvos para pies', 'bicarbonato',
    'calcetin', 'calcetines', 'media', 'medias', 'sock', 'socks', 'panti', 'pantys', 'pantimedias',
    'cordon', 'cordones', 'agujeta', 'agujetas', 'shoelace', 'shoelaces', 'laces',
    'plantilla', 'plantillas', 'insole', 'insoles', 'alza', 'alzas', 'talonera', 'taloneras',
    'separador de dedos', 'corrector de juanetes', 'almohadilla metatarsal', 'protector de talon',
    'horma', 'hormas', 'tensor', 'tensores', 'shoe tree', 'shoetree', 'calzador', 'calzadores', 'shoe horn',
    'tacos de repuesto', 'clavos de atletismo', 'clavos de repuesto',
    'funda para calzado', 'bolsa de zapatos', 'bolsa para calzado', 'bolsa para zapatillas', 'shoe bag',
    'zapatero', 'zapatera', 'organizador de zapatos', 'estanteria para zapatos', 'caja de zapatos', 'cajas de zapatos',
    'shoe rack', 'shoe storage',
    'espinillera', 'espinilleras', 'rodillera', 'rodilleras', 'tobillera', 'tobilleras',
    'grapadora', 'grapadoras', 'grapas', 'perforadora', 'taladro',
    'soporte en forma de l', 'placa qr', 'dslr', 'tripode', 'trípode', 'cámara', 'camara',
    'ronin', 'gimbal', 'micrófono', 'grabacion', 'grabación'
]

FOOTWEAR_REQUIRED_TERMS = [
    'zapatilla', 'zapatillas', 'zapato', 'zapatos',
    'bota', 'botas', 'botin', 'botines', 'mocasín', 'mocasines', 'moccasin',
    'sandalia', 'sandalias', 'sandal', 'sandals', 'chancla', 'chanclas', 'flip flop',
    'nautico', 'nauticos', 'náutico', 'náuticos', 'pie de gato', 'pies de gato',
    'sneaker', 'sneakers', 'bamba', 'bambas', 'zueco', 'zuecos', 'clog', 'clogs',
    'escarpin', 'escarpines', 'alpargata', 'alpargatas', 'espadrille', 'espadrilles',
    'pantufla', 'pantuflas', 'babucha', 'babuchas', 'calzado'
]

ACCESSORY_KEYWORDS = [
    'molde', 'moldes', 'papel', 'accesorios', 'accesorio', 'funda',
    'limpiador', 'rejilla', 'pinzas', 'pulverizador', 'aceitera', 'alfombrilla',
    'termofusible', 'recambio', 'recambios', 'repuesto', 'repuestos', 'cable', 'cables', 'tapa', 'tapas', 'filtro', 'filtros'
]

UNRELATED_FURNITURE_KEYWORDS = [
    'escritorio', 'silla', 'sofa', 'sofá', 'cama', 'colchon', 'colchón', 
    'armario', 'estanteria', 'estantería', 'mueble', 'soporte monitor', 
    'soporte tv', 'soporte para tv', 'televisor', 'pantalla', 'cortina', 'zapatero', 
    'perchero', 'cabecero', 'mesita de noche', 'libreria', 'librería', 'cojin', 
    'cojín', 'edredon', 'edredón', 'almohada'
]

GENERIC_STOPWORDS = {
    'de', 'del', 'para', 'con', 'en', 'los', 'las', 'un', 'una', 'y', 'el', 'la', 
    'por', 'a', 'electrico', 'electrica', 'electricos', 'electricas', 'portatil', 
    'portatiles', 'top', 'mejores', '2026', '2025', '2024', 'mejores', 'mejor', 'guia', 'mesa'
}

BOOK_ACCESSORY_REJECT_KEYWORDS = [
    'funda', 'fundas', 'protector', 'carcasa', 'cargador', 'soporte', 
    'cristal', 'cable', 'bateria', 'batería', 'estuche', 'bolso', 
    'luz para kindle', 'luz de lectura', 'atril', 'pegatina', 'pegatinas',
    'correa', 'adaptador', 'hub', 'skin', 'skins'
]

def clean_slug(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text.strip('_')

def parse_rating(rating_str):
    if not rating_str:
        return 0.0
    match = re.search(r'([0-9]+[.,][0-9]+|[0-9]+)', rating_str)
    if match:
        val = match.group(1).replace(',', '.')
        try:
            return float(val)
        except ValueError:
            return 0.0
    return 0.0

def is_actual_appliance(title, query=""):
    t = title.lower()
    q = query.lower()

    for acc in FOOTWEAR_ACCESSORY_REJECT_KEYWORDS:
        if acc in t and acc not in q:
            return False

    is_book_context = any(k in q or k in t for k in [
        'libro', 'novela', 'literatura', 'kindle', 'ensayo', 'comic', 'lectura', 
        'editorial', 'autor', 'ficcion', 'ebook', 'tapa dura', 'tapa blanda', 'edicion'
    ])
    
    if is_book_context:
        for acc in BOOK_ACCESSORY_REJECT_KEYWORDS:
            if re.search(r'\b' + acc + r'\b', t):
                return False

    for acc in ACCESSORY_KEYWORDS:
        if acc in ['tapa', 'tapas'] and ('tapa dura' in t or 'tapa blanda' in t or is_book_context):
            continue
        if re.search(r'\b' + acc + r'\b', t) and acc not in q:
            return False
    return True

def is_product_relevant(title, query):
    t_lower = title.lower()
    q_lower = query.lower()
    
    # 1. Reject explicit unrelated furniture/home items unless query asks for them
    for fk in UNRELATED_FURNITURE_KEYWORDS:
        if fk in t_lower and fk not in q_lower:
            return False

    for acc in FOOTWEAR_ACCESSORY_REJECT_KEYWORDS:
        if acc in t_lower and acc not in q_lower:
            return False

    is_footwear_context = any(k in q_lower for k in [
        'zapat', 'bota', 'botin', 'calzado', 'sandalia', 'chancla', 'pie de gato',
        'mocasin', 'mocasín', 'nautico', 'náutico', 'sneaker', 'bamba', 'zueco',
        'pala', 'running', 'trail', 'padel', 'tenis', 'basket', 'crossfit', 'trekking'
    ])
    if is_footwear_context:
        has_shoe_term = any(term in t_lower for term in FOOTWEAR_REQUIRED_TERMS)
        if not has_shoe_term:
            return False
            
    is_book_context = any(k in q_lower or k in t_lower for k in [
        'libro', 'novela', 'literatura', 'kindle', 'ensayo', 'comic', 'lectura', 
        'editorial', 'autor', 'ficcion', 'ebook', 'historia', 'biografia', 'fantasia',
        'misterio', 'desarrollo', 'filosofia', 'salud', 'terror', 'emprendimiento', 'poesia'
    ])
    if is_book_context:
        # Check that it is actually a book/eBook and not a non-book device
        for acc in BOOK_ACCESSORY_REJECT_KEYWORDS:
            if re.search(r'\b' + acc + r'\b', t_lower):
                return False
        return True

    # 1.5 Contexto Taller y Bricolaje: rechazar estrictamente barbacoa, pelo, dientes, cocina
    is_taller_context = any(k in q_lower for k in [
        'taller', 'madera', 'herramienta', 'taladro', 'sierra', 'lijadora', 'cepilladora',
        'fresadora', 'amoladora', 'radial', 'soldador', 'atornillador', 'ingletadora',
        'cepillo electrico para madera', 'cepillos electricos para madera', 'bricolaje'
    ]) or True  # En este scraper de taller, el contexto base siempre es taller
    if is_taller_context:
        TALLER_REJECT_KEYWORDS = [
            'barbacoa', 'parrilla', 'bbq', 'pelo', 'cabello', 'afeitad', 'afeitadora',
            'cortapelo', 'depilad', 'barba', 'dientes', 'dental', 'cocina', 'vajilla',
            'sarten', 'sartén', 'olla', 'cacerola', 'aspirador', 'colchon', 'colchón',
            'mascota', 'perro', 'gato', 'inodoro', 'fregadero', 'limpiador de poros',
            'champú', 'maquillaje', 'cosmetica', 'cosmética'
        ]
        for rej in TALLER_REJECT_KEYWORDS:
            if re.search(r'\b' + rej + r'\b', t_lower) and rej not in q_lower:
                return False

    is_cleaning_context = any(k in q_lower for k in [
        'aspirador', 'aspiradora', 'hidrolimpiador', 'hidrolimpiadora', 'vaporeta',
        'limpiador a vapor', 'limpieza a vapor', 'vaporizador', 'fregadora',
        'mopa electrica', 'robot aspirador', 'conga', 'roomba'
    ])
    if is_cleaning_context:
        CLEANING_REJECT_KEYWORDS = [
            'raspador', 'raspadores', 'rasqueta', 'rasquetas', 'cuchillas', 'cuchilla',
            'cuchillas de plastico', 'cuchillas de plástico', 'hojas de repuesto',
            'quitar pegatinas', 'quitar etiquetas', 'estropajo', 'estropajos',
            'bayeta', 'bayetas', 'paño de microfibra', 'paños de microfibra',
            'fregona manual', 'cubo de fregar', 'escoba manual', 'recogedor', 'plumero',
            'descalcificador', 'bolsas de repuesto', 'recambio de bolsas', 'pegamento',
            'soplador', 'soplador de aire', 'aire comprimido', 'kit de limpieza de camara', 'limpieza de camara'
        ]
        for rej in CLEANING_REJECT_KEYWORDS:
            if rej in t_lower and rej not in q_lower:
                return False
        if any(v in q_lower for v in ['vapor', 'vaporeta', 'steam', 'azulejos y juntas']):
            has_steam_term = any(v in t_lower for v in ['vapor', 'vaporeta', 'steam', 'bar', 'bares'])
            if not has_steam_term:
                return False

    # 2. Extract core concept words from query
    q_words = [w for w in re.findall(r'\b\w+\b', q_lower) if w not in GENERIC_STOPWORDS and len(w) > 3]
    if not q_words:
        return True
        
    # Check if title matches at least one core word or its 4-letter prefix stem
    for w in q_words:
        stem = w[:4]
        if stem in t_lower:
            return True
            
    return False

def get_product_brand(title):
    t = title.lower()
    for b in KNOWN_BRANDS:
        if b in t:
            return b
    first_word = t.split()[0] if t.split() else "desconocido"
    if first_word in ['el', 'la', 'los', 'las', 'un', 'una', 'del', 'de', 'en', 'con', 'por', 'mejores', 'top']:
        return t[:35]
    return first_word

def get_normalized_signature(title):
    t = title.lower()
    t = re.sub(r'\b(gris|negro|blanco|piedra|dorada|salvia|rojo|azul|inox|black|silver|verde|amarillo)\b', '', t)
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    ignore_words = [
        'freidora', 'aire', 'con', 'para', 'personas', 'portatil', 'aceite', 'sin', 'serie', 'series',
        'libro', 'libros', 'novela', 'novelas', 'edicion', 'version', 'kindle', 'tapa', 'dura', 'blanda', 'ebook', 'papel'
    ]
    tokens = set([w for w in t.split() if len(w) > 2 and w not in ignore_words])
    return tokens

def load_channel_history(channel_dir):
    os.makedirs(channel_dir, exist_ok=True)
    history_file = os.path.join(channel_dir, "history.json")
    used_topics = set()
    used_asins = set()

    if os.path.exists(channel_dir):
        for item in os.listdir(channel_dir):
            item_path = os.path.join(channel_dir, item)
            if os.path.isdir(item_path):
                slug = clean_slug(item)
                if slug:
                    used_topics.add(slug)
    
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                hdata = json.load(f)
                for t in hdata.get("used_topics", []):
                    slug = clean_slug(t)
                    if slug:
                        used_topics.add(slug)
                for a in hdata.get("used_asins", []):
                    used_asins.add(a.strip())
        except Exception:
            pass
            
    return history_file, used_topics, used_asins

def save_channel_history(history_file, used_topics, used_asins):
    data = {
        "used_topics": sorted(list(used_topics)),
        "used_asins": sorted(list(used_asins))
    }
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def extract_relevant_product_video(html_text, product_brand, search_query):
    decoded_html = html.unescape(html_text.replace("\\/", "/"))
    pattern = r"\"(?:videoURL|videoUrl|videoPreviewAssets|mediaUrl|url)\"\s*:\s*\"(https://[^\"]+?\.(?:mp4|m3u8)[^\"]*)\""
    stream_matches = re.findall(pattern, decoded_html, re.IGNORECASE)
    s3_direct = re.findall(r"https://m\.media-amazon\.com/images/S/[^\s\"'\\]+?\.(?:mp4|m3u8)", decoded_html)
    all_candidates = list(set(stream_matches + s3_direct))
    
    brand_clean = (product_brand or "").lower().strip()
    query_tokens = [w for w in (search_query or "").lower().split() if len(w) > 3]
    
    unrelated_categories = [
        "sandwichera", "freidora", "tostadora", "batidora", "envasadora", "horno", "plancha", "exprimidor",
        "cortacesped", "cortacésped", "cesped", "césped", "mower", "lawn", "jardin", "jardín", "desbrozadora",
        "motosierra", "piscina", "hidrolimpiadora", "ventilador", "calefactor", "deshumidificador", "zapato",
        "zapatilla", "bota", "sandalia", "libro", "novela", "colchon", "almohada"
    ]
    search_cats = [c for c in unrelated_categories if c in (search_query or "").lower()]
    
    valid_videos = []
    for v_url in all_candidates:
        if "closedcaptions" in v_url.lower() or v_url.lower().endswith(".vtt") or "/vtt/" in v_url.lower() or "thumbnail" in v_url.lower():
            continue
        v_lower = v_url.lower()
        if any(c in v_lower for c in unrelated_categories if c not in search_cats):
            continue
            
        score = 1
        if "videopreview" in v_lower:
            score += 4
        if "default.jobtemplate.mp4" in v_lower or "default.jobtemplate.hls.m3u8" in v_lower:
            score += 5
        if brand_clean and brand_clean in v_lower:
            score += 10
        for tok in query_tokens:
            if tok in v_lower:
                score += 3
        valid_videos.append((score, v_url))
        
    if valid_videos:
        valid_videos.sort(key=lambda x: x[0], reverse=True)
        return valid_videos[0][1]
    return None

def safe_get(session, url, headers=None, timeout=12):
    try:
        resp = session.get(url, headers=headers, timeout=timeout)
        if resp and resp.status_code == 200:
            bm_match = re.search(r"URL='([^']+?)'", resp.text)
            if bm_match:
                redirect_url = 'https://www.amazon.es' + html.unescape(bm_match.group(1))
                resp = session.get(redirect_url, headers=headers, timeout=timeout)
        return resp
    except Exception:
        return None

def extract_product_price(soup):
    price_selectors = [
        '#corePriceDisplay_desktop_feature_div .a-price .a-offscreen',
        '#corePrice_desktop .a-price .a-offscreen',
        '.apexPriceToPay .a-offscreen',
        '.priceToPay span.a-offscreen',
        'span.a-price span.a-offscreen',
        '#priceblock_ourprice',
        '#priceblock_dealprice',
        '#priceblock_saleprice',
        '#kindle-price',
        '#price_inside_buybox',
        '.priceToPay',
        '#price',
        '.slot-price',
        '.a-price'
    ]
    for sel in price_selectors:
        el = soup.select_one(sel)
        if el:
            txt = el.text.strip()
            if not txt:
                continue
            m = re.search(r'([0-9]+[.,][0-9]{2}\s*€|€\s*[0-9]+[.,][0-9]{2})', txt)
            if m:
                return m.group(1).replace(' ', ' ')
            if '€' in txt:
                clean_p = re.sub(r'[^\d.,€\s]', '', txt).replace(' ', ' ').strip().split()
                if clean_p and any(c.isdigit() for c in clean_p[0]):
                    return clean_p[0]
    return 'Consultar en Amazon'

def extract_product_features(soup):
    bullets = []
    bullet_selectors = [
        '#feature-bullets ul li span.a-list-item',
        '#featurebullets_feature_div ul li span.a-list-item',
        '#productFactsDesktopExpander ul li',
        '#productFactsDesktop_feature_div ul li'
    ]
    for b_sel in bullet_selectors:
        for li in soup.select(b_sel):
            t = li.text.strip()
            if t and len(t) > 12 and not any(ign in t.lower() for ign in ['garantía', 'aviso legal', 'para más información', 'acerca de este artículo', 'consulte la tabla', 'mida su pie', 'medir la longitud', 'segunda imagen', 'tabla de tallas']):
                t_clean = re.sub(r'\s+', ' ', t).strip()
                if t_clean not in bullets:
                    bullets.append(t_clean)
    return bullets[:4]

def extract_product_specs(soup):
    specs = {}
    for tr in soup.select('#productOverview_feature_div tr, #productOverview_feature_div .po-row'):
        tds = tr.select('td, th, .po-label, .po-value')
        if len(tds) >= 2:
            k = tds[0].text.strip()
            v = tds[1].text.strip()
            if k and v and len(k) < 60:
                specs[k] = v
    if not specs or len(specs) < 3:
        for row in soup.select('#productFactsDesktopExpander .a-fixed-left-grid, #productFactsDesktop_feature_div .a-fixed-left-grid'):
            cols = row.select('.a-col-left, .a-col-right')
            if len(cols) >= 2:
                k = cols[0].text.strip()
                v = cols[1].text.strip()
                if k and v and k not in specs:
                    specs[k] = v
    if not specs:
        for li in soup.select('#detailBullets_feature_div ul li span.a-list-item'):
            parts = li.text.split(':', 1)
            if len(parts) == 2:
                k = parts[0].replace('‎', '').replace('‏', '').strip()
                v = parts[1].replace('‎', '').replace('‏', '').strip()
                if k and v and not any(ign in k.lower() for ign in ['opiniones', 'clasificación', 'asin', 'dimensiones del paquete', 'fabricante']):
                    specs[k] = v
    return specs

def extract_product_description(soup):
    desc_el = soup.select_one('#productDescription p, #productDescription_feature_div #productDescription, #productDescription, #aplus, #aplus_feature_div p')
    if desc_el:
        clean_d = re.sub(r'\s+', ' ', desc_el.text).strip()
        clean_d = re.sub(r'^(descripción del producto|más información del producto)\s*', '', clean_d, flags=re.IGNORECASE).strip()
        return clean_d[:300]
    return ''


def extract_product_rating(soup):
    rating_selectors = [
        '#acrPopover .a-icon-alt',
        '#averageCustomerReviews .a-icon-alt',
        'span[data-hook="rating-out-of-text"]',
        'i.a-icon-star span.a-icon-alt',
        'i.a-icon-star-small span.a-icon-alt',
        '#cm-cr-dp-review-summary .a-icon-alt'
    ]
    for sel in rating_selectors:
        el = soup.select_one(sel)
        if el:
            txt = el.text.strip()
            m = re.search(r'([0-9]+[.,][0-9]+)\s+de\s+5', txt)
            if m:
                val = m.group(1).replace(',', '.')
                return f"{m.group(1)} de 5 estrellas", float(val)

    for el in soup.select('.a-icon-alt'):
        txt = el.text.strip()
        m = re.search(r'([0-9]+[.,][0-9]+)\s+de\s+5', txt)
        if m:
            val = m.group(1).replace(',', '.')
            return f"{m.group(1)} de 5 estrellas", float(val)

    return "4.5 de 5 estrellas", 4.5

def extract_product_reviews(soup):
    rev_count_el = soup.select_one('#acrCustomerReviewText, [data-hook="total-review-count"]')
    rev_count = re.sub(r'[^\d.,]', '', rev_count_el.text.strip()) if rev_count_el else ''
    
    reviews = []
    for r_el in soup.select('[data-hook="review"]')[:3]:
        t_el = r_el.select_one('[data-hook="reviewTitle"], [data-hook="review-title"]')
        s_el = r_el.select_one('[data-hook="review-star-rating"]')
        b_el = r_el.select_one('[data-hook="reviewText"] p span, [data-hook="reviewText"] span, [data-hook="reviewRichContentContainer"] p')
        r_t = t_el.text.strip() if t_el else ''
        r_t = re.sub(r'^[0-9]+[.,][0-9]+\s+de\s+[0-9]+\s+estrellas\s*', '', r_t)
        r_s = s_el.text.strip() if s_el else ''
        r_b = b_el.text.strip() if b_el else ''
        r_b = r_b.replace('Brief content visible, double tap to read full content.', '').replace('Full content visible, double tap to read brief content.', '').replace('Leer másLeer menos', '').strip()
        r_b = re.sub(r'\s+', ' ', r_b)
        t_low = ' ' + (r_b + ' ' + r_t).lower() + ' '
        non_es = any(w in t_low for w in [' molto ', ' sono ', ' qulità ', ' adeguati ', ' molto ', ' prima del ', ' sehr ', ' nicht ', ' très ', ' avec '])
        has_es = any(w in t_low for w in [' el ', ' la ', ' de ', ' en ', ' un ', ' una ', ' que ', ' es ', ' con ', ' para ', ' muy ', ' bien ', ' son ', ' me '])
        if non_es and not has_es:
            continue
        if r_b or r_t:
            reviews.append({'title': r_t, 'rating': r_s, 'text': r_b[:250]})
    return rev_count, reviews


_thread_local = threading.local()

def get_thread_session():
    if not hasattr(_thread_local, 'session'):
        _thread_local.session = requests.Session(impersonate="chrome120")
    return _thread_local.session

def process_asin(asin, headers, search_query, session=None):
    if session is None:
        session = get_thread_session()
    prod_url = f"https://www.amazon.es/dp/{asin}"
    try:
        p_resp = safe_get(session, prod_url, headers=headers, timeout=12)
        if not p_resp or p_resp.status_code != 200:
            return None
            
        soup = BeautifulSoup(p_resp.text, 'html.parser')
        
        title_el = soup.select_one('#productTitle') or soup.select_one('h1')
        title = title_el.text.strip() if title_el else f"Producto {asin}"
        
        if not is_actual_appliance(title, search_query):
            return None

        if not is_product_relevant(title, search_query):
            return None

        price = extract_product_price(soup)
        features = extract_product_features(soup)
        specs = extract_product_specs(soup)
        desc_snippet = extract_product_description(soup)
        review_count, top_reviews = extract_product_reviews(soup)
        
        rating_raw, rating_num = extract_product_rating(soup)
        
        if rating_num > 0 and rating_num < 4.0:
            return None
            
        img_el = (
            soup.select_one('#landingImage') or 
            soup.select_one('#imgBlkFront') or 
            soup.select_one('#ebooksImgBlkFront') or 
            soup.select_one('img.s-image') or 
            soup.select_one('#litb-canvas-img-result') or 
            soup.select_one('#main-image')
        )
        img_url = None
        if img_el:
            if img_el.get('data-old-hires'):
                img_url = img_el.get('data-old-hires')
            elif img_el.get('src'):
                img_url = img_el.get('src')
            elif img_el.get('data-a-dynamic-image'):
                try:
                    dyn_dict = json.loads(img_el.get('data-a-dynamic-image'))
                    if isinstance(dyn_dict, dict) and dyn_dict:
                        img_url = list(dyn_dict.keys())[0]
                except Exception:
                    pass
        
        brand = get_product_brand(title)
        product_video_url = extract_relevant_product_video(p_resp.text, brand, search_query)
        
        # Disabled blind video fallback to prevent cross-selling unrelated category videos (e.g. lawnmowers/cortacesped)

        # Regla de negocio estricta: Descartar producto si no tiene video real en Amazon
        if not product_video_url:
            return None
            
        return {
            "asin": asin,
            "title": title,
            "price": price,
            "rating_raw": rating_raw,
            "rating_num": rating_num,
            "video_url": product_video_url,
            "img_url": img_url,
            "product_url": prod_url,
            "features": features,
            "specs": specs,
            "description_snippet": desc_snippet,
            "review_count": review_count,
            "top_reviews": top_reviews
        }
    except Exception:
        return None

def download_product_video(video_url, output_path):
    cmd = [
        "ffmpeg", "-y",
        "-i", video_url,
        "-c", "copy",
        "-an",
        output_path
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 100000

def create_video_from_image(img_url, session, output_path, duration=15):
    try:
        i_res = session.get(img_url, timeout=8)
        if i_res.status_code != 200:
            return False
        temp_img = output_path + ".temp.jpg"
        with open(temp_img, 'wb') as f:
            f.write(i_res.content)
            
        cmd = [
            'ffmpeg', '-y', '-loop', '1',
            '-i', temp_img,
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '20',
            '-t', str(duration),
            '-pix_fmt', 'yuv420p',
            '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black',
            output_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(temp_img):
            try:
                os.remove(temp_img)
            except Exception:
                pass
        return res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 50000
    except Exception:
        return False

def scrape_amazon(query, canal_nombre, base_dir="/home/javierferb/ia-lab-files/videos/edicion_ia", limit=7, affiliate_tag="taller_tag-21"):
    if not query or len(str(query).strip()) < 3:
        print(json.dumps({"error": "[SCRAPER ERROR] search query is empty or invalid (< 3 chars). Aborting to prevent invalid products."}))
        sys.exit(1)
    if not canal_nombre or len(str(canal_nombre).strip()) < 2:
        print(json.dumps({"error": "[SCRAPER ERROR] canal_nombre is empty or invalid. Aborting to prevent saving to root."}))
        sys.exit(1)
    query_slug = clean_slug(query)
    
    project_dir = os.path.join(base_dir, canal_nombre)
    try:
        os.makedirs(project_dir, exist_ok=True)
    except Exception:
        base_dir = "/home/javierferb/ia-lab-files/videos/edicion_ia"
        project_dir = os.path.join(base_dir, canal_nombre)
        os.makedirs(project_dir, exist_ok=True)

    channel_dir = os.path.dirname(project_dir)
    history_file, used_topics, used_asins = load_channel_history(channel_dir)

    intro_dir = os.path.join(project_dir, "00_intro")
    outro_dir = os.path.join(project_dir, "08_outro")
    os.makedirs(intro_dir, exist_ok=True)
    os.makedirs(outro_dir, exist_ok=True)

    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'accept-language': 'es-ES,es;q=0.9,en;q=0.8',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    session = requests.Session(impersonate="chrome120")
    
    qualified_raw = []
    seen_asins = set(used_asins)

    is_book_query = any(k in query.lower() for k in [
        'libro', 'novela', 'literatura', 'kindle', 'ensayo', 'comic', 'lectura', 
        'editorial', 'autor', 'ficcion', 'ebook', 'historia', 'biografia', 'fantasia',
        'misterio', 'desarrollo', 'filosofia', 'salud', 'terror', 'emprendimiento', 'poesia'
    ])
    search_term = f"{query} kindle" if (is_book_query and 'kindle' not in query.lower()) else query

    for page in range(1, 13):
        if len(qualified_raw) >= max(limit * 2, 8):
            break
        search_url = f"https://www.amazon.es/s?k={requests.utils.quote(search_term)}&page={page}"
        response = safe_get(session, search_url, headers=headers, timeout=12)
        if not response or response.status_code != 200:
            continue

        search_soup = BeautifulSoup(response.text, 'html.parser')
        dom_asins = [div.get('data-asin').strip() for div in search_soup.select('div[data-asin]') if div.get('data-asin') and len(div.get('data-asin').strip()) == 10]
        seen_p = set()
        page_asins = [a for a in dom_asins if not (a in seen_p or seen_p.add(a))]
        if not page_asins:
            raw_asins = list(set(re.findall(r'B0[A-Z0-9]{8}', response.text)))
            page_asins = raw_asins[:25]
        else:
            page_asins = page_asins[:25]

        new_asins = [a for a in page_asins if a not in seen_asins]
        if len(new_asins) < 2 and len(qualified_raw) < limit:
            new_asins = page_asins
            
        for a in new_asins:
            seen_asins.add(a)
                    
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(process_asin, asin, headers, query, session) for asin in new_asins]
            for f in as_completed(futures):
                res = f.result()
                if res:
                    qualified_raw.append(res)
                    if len(qualified_raw) >= max(limit * 2, 8):
                        break

    if len(qualified_raw) < limit:
        canal_low = canal_nombre.lower()
        if 'limpiez' in canal_low:
            ev_asins = ["B09B3Y1X9F", "B084G211T7", "B08CVX7WNP", "B099KCYF1Q", "B07P46B9S1"]
        elif 'zapat' in canal_low:
            ev_asins = ["B08NVN7W5J", "B07P5J2WLM", "B08V5C56LM", "B093L4B8VT", "B07R9L73B7"]
        elif 'librer' in canal_low:
            ev_asins = ["B085G3G2CY", "B0062XBS32", "B09S3YXPRZ", "B078XH916T", "B007HPS120"]
        else:
            ev_asins = ["B07N8N6C8T", "B0936FGLQT", "B0892BCFCS", "B08B8Z4V79", "B091CRZQ69"]
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(process_asin, asin, headers, query, session) for asin in ev_asins]
            for f in as_completed(futures):
                res = f.result()
                if res and res not in qualified_raw:
                    qualified_raw.append(res)

    if is_book_query:
        def book_kindle_score(item):
            t_low = item["title"].lower()
            score = 0
            if 'kindle' in t_low or 'ebook' in t_low:
                score += 20
            if 'tapa dura' in t_low or 'tapa blanda' in t_low or 'edición' in t_low or 'edicion' in t_low:
                score += 10
            return score
        qualified_raw.sort(key=book_kindle_score, reverse=True)

    selected_raw = []
    seen_brands = {}
    seen_signatures = []

    for p in qualified_raw:
        title = p["title"]
        brand = get_product_brand(title)
        sig = get_normalized_signature(title)

        if seen_brands.get(brand, 0) >= 1:
            continue

        is_similar = False
        for s in seen_signatures:
            overlap = sig.intersection(s)
            if len(sig) > 0 and (len(overlap) / len(sig)) >= 0.5:
                is_similar = True
                break

        if is_similar:
            continue

        seen_brands[brand] = seen_brands.get(brand, 0) + 1
        seen_signatures.append(sig)
        selected_raw.append(p)

        if len(selected_raw) >= limit:
            break

    if len(selected_raw) < limit:
        for p in qualified_raw:
            if p in selected_raw:
                continue
            title = p["title"]
            brand = get_product_brand(title)
            sig = get_normalized_signature(title)

            if seen_brands.get(brand, 0) >= 2:
                continue

            is_similar = False
            for s in seen_signatures:
                overlap = sig.intersection(s)
                if len(sig) > 0 and (len(overlap) / len(sig)) >= 0.6:
                    is_similar = True
                    break

            if not is_similar:
                seen_brands[brand] = seen_brands.get(brand, 0) + 1
                seen_signatures.append(sig)
                selected_raw.append(p)

            if len(selected_raw) >= limit:
                break

    candidates_pool = list(selected_raw)
    for p in qualified_raw:
        if p not in candidates_pool:
            candidates_pool.append(p)

    products = []
    rank = 1
    for p in candidates_pool:
        if rank > limit:
            break

        prod_folder_name = f"{rank:02d}_producto_{rank}"
        prod_dir = os.path.join(project_dir, prod_folder_name)
        os.makedirs(prod_dir, exist_ok=True)

        v_filename = None
        if p.get("video_url"):
            v_path = os.path.join(prod_dir, f"product_{rank}.mp4")
            success = download_product_video(p["video_url"], v_path)
            if success:
                v_filename = os.path.join(prod_folder_name, f"product_{rank}.mp4")
                
        # Fallback a imagen estatica descartado por regla de negocio: solo videos reales de Amazon

        if not v_filename:
            try:
                import shutil
                shutil.rmtree(prod_dir, ignore_errors=True)
            except Exception:
                pass
            continue

        i_filename = None
        if p["img_url"]:
            try:
                i_res = session.get(p["img_url"], timeout=8)
                if i_res.status_code == 200:
                    i_path = os.path.join(prod_dir, f"product_{rank}.jpg")
                    with open(i_path, 'wb') as f:
                        f.write(i_res.content)
                    i_filename = os.path.join(prod_folder_name, f"product_{rank}.jpg")
            except Exception:
                pass

        products.append({
            "rank": rank,
            "folder": prod_folder_name,
            "asin": p["asin"],
            "title": p["title"],
            "price": p["price"],
            "rating": p["rating_raw"],
            "rating_num": p["rating_num"],
            "features": p.get("features", []),
            "specs": p.get("specs", {}),
            "description_snippet": p.get("description_snippet", ""),
            "review_count": p.get("review_count", ""),
            "top_reviews": p.get("top_reviews", []),
            "has_video": True,
            "video_file": v_filename,
            "image_file": i_filename,
            "product_url": p["product_url"]
        })
        
        used_asins.add(p["asin"])
        rank += 1

    save_channel_history(history_file, used_topics, used_asins)

    result_data = {
        "query": query,
        "canal_nombre": canal_nombre,
        "project_dir": project_dir,
        "affiliate_tag": affiliate_tag or "taller_tag-21",
        "products": products
    }
    
    data_json_path = os.path.join(project_dir, "data.json")
    try:
        os.chmod(project_dir, 0o777)
    except Exception:
        pass
    with open(data_json_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    try:
        os.chmod(data_json_path, 0o666)
    except Exception:
        pass
        
    return result_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Amazon Video & Metadata Scraper")
    parser.add_argument("--query", required=True, help="Palabra clave de búsqueda")
    parser.add_argument("--canal", required=True, help="Nombre de la carpeta del canal")
    parser.add_argument("--base_dir", default="/home/javierferb/ia-lab-files/videos/edicion_ia", help="Ruta base del NAS o almacenamiento local")
    parser.add_argument("--limit", type=int, default=7, help="Número de productos")
    parser.add_argument("--affiliate_tag", default="taller_tag-21", help="Tag de afiliado Amazon")
    
    args = parser.parse_args()
    
    res = scrape_amazon(args.query, args.canal, args.base_dir, args.limit, args.affiliate_tag)
    print(json.dumps(res, ensure_ascii=False))
