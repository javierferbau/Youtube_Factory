#!/usr/bin/env python3
import sys
import os
import json
import argparse
import re
import html
import subprocess
import math
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from curl_cffi import requests
from bs4 import BeautifulSoup

KNOWN_BRANDS = [
    'moulinex', 'cosori', 'ninja', 'cecotec', 'philips', 'princess',
    'aigostar', 'xiaomi', 'taurus', 'russell hobbs', 'ufesa', 'cecofry',
    'instant', 'innsky', 'proscenic', 'ikohs', 'create', 'fridja', 'mellerware',
    'krups', 'delonghi', 'melitta', 'neretva', 'outin', 'wmf', 'bonsenkitchen', 'jata',
    'nike', 'adidas', 'puma', 'asics', 'salomon', 'skechers', 'new balance', 'under armour',
    'mizuno', 'brooks', 'saucony', 'merrell', 'columbia', 'hoka', 'vans', 'converse',
    'reebok', 'clarks', 'timberland', 'panama jack', 'geox', 'crocs', 'camper', 'pikolinos',
    'fluchos', 'callaghan', 'pitillos', 'saguaro', 'whitin', 'feethit', 'joma', 'munich',
    'chiruca', 'bestard', 'la sportiva', 'scarpa', 'boreal', 'salewa', 'bellota', 'safeyear',
    'sparco', 'u-power', 'caterpillar', 'cat', 'dunlop', 'helly hansen', 'birkenstock', 'arrigo bello', 'rockport'
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
    
    for fk in UNRELATED_FURNITURE_KEYWORDS:
        if fk in t_lower and fk not in q_lower:
            return False

    for acc in FOOTWEAR_ACCESSORY_REJECT_KEYWORDS:
        if acc in t_lower and acc not in q_lower:
            return False

    is_footwear_context = any(k in q_lower for k in [
        'zapat', 'bota', 'botin', 'calzado', 'sandalia', 'chancla', 'pie de gato',
        'mocasin', 'mocasín', 'nautico', 'náutico', 'sneaker', 'bamba', 'zueco',
        'pala', 'running', 'trail', 'padel', 'tenis', 'basket', 'crossfit', 'trekking',
        'u-power', 'upower', 'sparco', 'bellota', 'panter', 'cofra', 'diadora', 'safety', 's1p', 's3'
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
        for acc in BOOK_ACCESSORY_REJECT_KEYWORDS:
            if re.search(r'\b' + acc + r'\b', t_lower):
                return False
        return True

    q_words = [w for w in re.findall(r'\b\w+\b', q_lower) if w not in GENERIC_STOPWORDS and len(w) > 3]
    if not q_words:
        return True
        
    for w in q_words:
        stem = w[:4]
        if stem in t_lower:
            return True
            
    return False

def get_product_category_type(title, query=""):
    t = title.lower()
    q = query.lower()
    if any(k in t for k in ['pie de gato', 'pies de gato', 'escalada deportiva', 'boulder']):
        return 'footwear_climbing'
    if any(k in t for k in ['bota', 'botas', 'botin', 'botines', 'boot', 'boots', 'chelsea']):
        return 'footwear_boots'
    if any(k in t for k in ['sandalia', 'sandalias', 'chancla', 'chanclas', 'zueco', 'zuecos', 'clog', 'crocs', 'flip flop', 'pala']):
        return 'footwear_sandals'
    if any(k in t for k in ['zapato de vestir', 'zapatos de vestir', 'mocasín', 'mocasines', 'moccasin', 'nautico', 'nauticos', 'náutico', 'náuticos', 'oxford', 'derby']):
        return 'footwear_dress'
    if any(k in t for k in ['zapatilla', 'zapatillas', 'sneaker', 'sneakers', 'bamba', 'bambas', 'running', 'trail', 'padel', 'tenis', 'basket', 'crossfit', 'fitness', 'caminar', 'deportivas']):
        return 'footwear_sneakers'
    if any(k in t for k in ['zapato', 'zapatos']):
        return 'footwear_shoes'
        
    for kw in ['freidora', 'cafetera', 'robot aspirador', 'aspiradora', 'hidrolimpiadora', 'batidora', 'tostadora', 'olla', 'horno', 'microondas']:
        if kw in t or kw in q:
            return f'appliance_{kw}'
            
    return 'generic'

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
    vse_direct = re.findall(r"https://m\.media-amazon\.com/images/S/vse-vms-transcoding-artifact[^\"]+?\.mp4", decoded_html)
    all_candidates = list(set(stream_matches + vse_direct))
    
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
        if "closedCaptions" in v_url or "al-eu-" in v_url or "/al-" in v_url or v_url.endswith(".vtt"):
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

def extract_reviews_from_soup(soup, is_positive):
    reviews = []
    review_divs = soup.select('.review')
    for div in review_divs:
        title_el = div.select_one('.review-title span') or div.select_one('.review-title')
        text_el = div.select_one('.review-text-content span') or div.select_one('.review-text')
        stars_el = div.select_one('.a-icon-alt')
        author_el = div.select_one('.a-profile-name')
        
        if title_el and text_el and stars_el:
            stars = parse_rating(stars_el.text)
            if (is_positive and stars >= 4) or (not is_positive and stars <= 3):
                title = title_el.text.strip()
                title = re.sub(r'^\d[.,]\d de 5 estrellas\s+', '', title)
                text = text_el.text.strip()
                author = author_el.text.strip() if author_el else "Cliente Amazon"
                reviews.append({
                    "stars": stars,
                    "title": title,
                    "text": text,
                    "author": author,
                    "synthetic": False
                })
        if len(reviews) >= 3:
            break
    return reviews

def generate_synthetic_reviews(is_positive):
    reviews = []
    for i in range(3):
        if is_positive:
            reviews.append({
                "stars": float(random.choice([4.0, 5.0])),
                "title": "Buen producto",
                "text": "Cumple con su función y la calidad es buena. Lo recomiendo totalmente.",
                "author": "Cliente Satisfecho",
                "synthetic": True
            })
        else:
            reviews.append({
                "stars": float(random.choice([1.0, 2.0, 3.0])),
                "title": "Podría mejorar",
                "text": "Tiene algunos fallos y no funciona tan bien como esperaba según la descripción.",
                "author": "Usuario Amazon",
                "synthetic": True
            })
    return reviews

def scrape_reviews(asin, session, headers, filter_star, product_soup):
    is_pos = filter_star == 'positive'
    url = f"https://www.amazon.es/product-reviews/{asin}/?filterByStar={filter_star}&sortBy=recent"
    
    time.sleep(random.uniform(1.0, 2.0))
    resp = safe_get(session, url, headers=headers, timeout=10)
    
    reviews = []
    if resp and resp.status_code == 200:
        soup = BeautifulSoup(resp.text, 'html.parser')
        reviews = extract_reviews_from_soup(soup, is_pos)
        
    if len(reviews) < 3 and product_soup:
        page_reviews = extract_reviews_from_soup(product_soup, is_pos)
        for r in page_reviews:
            if len(reviews) >= 3: break
            if r['text'] not in [x['text'] for x in reviews]:
                reviews.append(r)
        
    if len(reviews) < 3:
        synth = generate_synthetic_reviews(is_pos)
        for s in synth:
            if len(reviews) >= 3: break
            reviews.append(s)
            
    return reviews[:3]


def process_asin(asin, session, headers, search_query):
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

        price_el = (
            soup.select_one('#kindle-price') or 
            soup.select_one('.a-price .a-offscreen') or 
            soup.select_one('#priceblock_ourprice') or 
            soup.select_one('.apexPriceToPay .a-offscreen') or
            soup.select_one('#price') or
            soup.select_one('.slot-price')
        )
        price = price_el.text.strip() if price_el else "Consultar en Amazon"
        
        rating_el = soup.select_one('.a-icon-alt')
        rating_raw = rating_el.text.strip() if rating_el else "4.5"
        rating_num = parse_rating(rating_raw)
        
        if rating_num > 0 and rating_num < 3.5:
            return None
            
        review_count = 0
        rc_el = soup.select_one('#acrCustomerReviewText')
        if rc_el:
            rc_text = rc_el.text.strip().replace('.', '').replace(',', '')
            match = re.search(r'(\d+)', rc_text)
            if match:
                review_count = int(match.group(1))
            
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
            "brand": brand,
            "price": price,
            "rating_raw": rating_raw,
            "rating_num": rating_num,
            "review_count": review_count,
            "video_url": product_video_url,
            "img_url": img_url,
            "product_url": prod_url,
            "html": p_resp.text
        }
    except Exception:
        return None


def scrape_amazon_vs(query, canal_nombre, base_dir="/home/javierferb/ia-lab-files/videos/edicion_ia", affiliate_tag=None):
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

    # Soporte para duelos francotirador Modelo A vs Modelo B
    search_queries = []
    if " vs " in query.lower() or " versus " in query.lower():
        parts = re.split(r'\s+(?:vs|versus)\s+', query, flags=re.IGNORECASE)
        if len(parts) == 2:
            search_queries.extend([parts[0].strip(), parts[1].strip()])
    search_queries.append(query)

    is_book_query = any(k in query.lower() for k in [
        'libro', 'novela', 'literatura', 'kindle', 'ensayo', 'comic', 'lectura', 
        'editorial', 'autor', 'ficcion', 'ebook', 'historia', 'biografia', 'fantasia',
        'misterio', 'desarrollo', 'filosofia', 'salud', 'terror', 'emprendimiento', 'poesia'
    ])

    for sq in search_queries:
        if len(qualified_raw) >= 16:
            break
        search_term = f"{sq} kindle" if (is_book_query and 'kindle' not in sq.lower()) else sq
        for page in range(1, 4):
            if len(qualified_raw) >= 16:
                break
            search_url = f"https://www.amazon.es/s?k={requests.utils.quote(search_term)}&page={page}"
            try:
                response = safe_get(session, search_url, headers=headers, timeout=10)
                if not response or response.status_code != 200:
                    continue

                search_soup = BeautifulSoup(response.text, 'html.parser')
                dom_asins = [div.get('data-asin').strip() for div in search_soup.select('div[data-asin]') if div.get('data-asin') and len(div.get('data-asin').strip()) == 10]
                seen_p = set()
                page_asins = [a for a in dom_asins if not (a in seen_p or seen_p.add(a))]
                if not page_asins:
                    page_asins = list(dict.fromkeys(re.findall(r'[B0-9][A-Z0-9]{9}', response.text)))[:25]
                new_asins = [a for a in page_asins if a not in seen_asins]
                if len(new_asins) < 2 and len(qualified_raw) < 2:
                    new_asins = page_asins

                for a in new_asins:
                    seen_asins.add(a)

                with ThreadPoolExecutor(max_workers=8) as executor:
                    futures = [executor.submit(process_asin, asin, session, headers, sq) for asin in new_asins[:10]]
                    for f in as_completed(futures):
                        res = f.result()
                        if res and res not in qualified_raw:
                            qualified_raw.append(res)
            except Exception:
                pass

    # Score y ordenación: priorizar productos con vídeo real descargable y alto rating
    qualified_raw.sort(key=lambda x: (1 if x.get("video_url") else 0, x["rating_num"] * math.log(x["review_count"] + 1)), reverse=True)

    top_2 = []
    # 0. Duelo Francotirador con 2 marcas explícitas (ej: Mizuno vs Brooks, Cosori vs Cecotec)
    target_brands = []
    for b in KNOWN_BRANDS:
        if re.search(r'\b' + re.escape(b) + r'\b', query.lower()):
            target_brands.append(b)

    if len(target_brands) >= 2:
        b1, b2 = target_brands[0], target_brands[1]
        p1 = next((p for p in qualified_raw if p.get("brand", "").lower() == b1), None)
        p2 = next((p for p in qualified_raw if p.get("brand", "").lower() == b2 and (not p1 or p["asin"] != p1["asin"])), None)
        if p1 and p2 and p1["asin"] != p2["asin"]:
            top_2 = [p1, p2]

    # 0b. Si la query tenía " vs " y se identificaron dos sub-queries:
    if len(top_2) < 2 and len(search_queries) >= 3:
        sq_a, sq_b = search_queries[0].lower(), search_queries[1].lower()
        p1 = next((p for p in qualified_raw if any(w in p["title"].lower() for w in sq_a.split() if len(w) > 3)), None)
        p2 = next((p for p in qualified_raw if (not p1 or p["asin"] != p1["asin"]) and any(w in p["title"].lower() for w in sq_b.split() if len(w) > 3)), None)
        if p1 and p2 and p1["asin"] != p2["asin"]:
            top_2 = [p1, p2]

    # 1. Emparejamiento por subcategoría idéntica y marca distinta
    if len(top_2) < 2 and qualified_raw:
        prod_a = qualified_raw[0]
        cat_a = get_product_category_type(prod_a["title"], query)
        cand_b = None
        for p in qualified_raw[1:]:
            brand_p = p.get("brand", "").lower()
            brand_a = prod_a.get("brand", "").lower()
            if brand_p and brand_p != brand_a and p["asin"] != prod_a["asin"]:
                cat_p = get_product_category_type(p["title"], query)
                if cat_a == cat_p:
                    cand_b = p
                    break
        if cand_b:
            top_2 = [prod_a, cand_b]

    # 2. Emparejamiento por categoría compatible y marca distinta
    if len(top_2) < 2 and qualified_raw:
        prod_a = qualified_raw[0]
        cand_b = None
        for p in qualified_raw[1:]:
            if p["asin"] != prod_a["asin"] and p.get("brand", "").lower() != prod_a.get("brand", "").lower():
                cand_b = p
                break
        if cand_b:
            top_2 = [prod_a, cand_b]

    # 3. Emparejamiento con cualquier par disponible de qualified_raw
    if len(top_2) < 2 and len(qualified_raw) >= 2:
        top_2 = [qualified_raw[0], qualified_raw[1]]

    # 4. Fallback a búsqueda de categoría del nicho si falta alguno
    if len(top_2) < 2:
        if "zapat" in canal_nombre.lower() or "calzado" in canal_nombre.lower():
            niche_query = "zapatillas running hombre mas vendidas"
        elif "cocina" in canal_nombre.lower():
            niche_query = "freidora de aire sin aceite mas vendida"
        elif "limpieza" in canal_nombre.lower():
            niche_query = "robot aspirador y friegasuelos mas vendido"
        elif "barber" in canal_nombre.lower():
            niche_query = "afeitadora cortapelos hombre mas vendida"
        elif "librer" in canal_nombre.lower():
            niche_query = "novelas mas vendidas libros"
        else:
            niche_query = f"{query} mas vendidos"

        cat_url = f"https://www.amazon.es/s?k={requests.utils.quote(niche_query)}"
        cat_resp = safe_get(session, cat_url, headers=headers, timeout=10)
        if cat_resp and cat_resp.status_code == 200:
            cat_soup = BeautifulSoup(cat_resp.text, 'html.parser')
            cat_asins = [d.get('data-asin').strip() for d in cat_soup.select('div[data-asin]') if d.get('data-asin') and len(d.get('data-asin').strip()) == 10]
            if not cat_asins:
                cat_asins = list(dict.fromkeys(re.findall(r'[B0-9][A-Z0-9]{9}', cat_resp.text)))[:12]
            with ThreadPoolExecutor(max_workers=6) as executor:
                futures = [executor.submit(process_asin, asin, session, headers, niche_query) for asin in cat_asins[:10]]
                for f in as_completed(futures):
                    res = f.result()
                    if res:
                        if not top_2:
                            top_2.append(res)
                        elif top_2[0]["asin"] != res["asin"] and len(top_2) < 2:
                            top_2.append(res)
                        if len(top_2) == 2:
                            break

    # 5. Fallback final garantizado: Evergreen ASINs por nicho
    if len(top_2) < 2:
        niche_evergreens = {
            "zapat": ["B0F2FQ3XT3", "B0DZCQM8WX", "B091234567", "B0CDFQRXTF"],
            "calzado": ["B0F2FQ3XT3", "B0DZCQM8WX", "B091234567", "B0CDFQRXTF"],
            "cocina": ["B077MLZZVM", "B0CDFQRXTF", "B01MR32LQT", "B099RP68P2"],
            "limpieza": ["B0BV288KNZ", "B0H2DJCPB7", "B08N5WRWNW"],
            "librer": ["B08N5WRWNW", "B09SWW583J", "B077MLZZVM"],
            "barber": ["B0F38G7D6B", "B0F2MS12WR", "B0BB5MDXFN"],
        }
        cand_eg = []
        for k_niche, asins in niche_evergreens.items():
            if k_niche in canal_nombre.lower():
                cand_eg = asins
                break
        if not cand_eg:
            cand_eg = ["B077MLZZVM", "B0CDFQRXTF", "B01MR32LQT", "B099RP68P2"]

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(process_asin, asin, session, headers, "") for asin in cand_eg]
            for f in as_completed(futures):
                res = f.result()
                if res:
                    if not top_2:
                        top_2.append(res)
                    elif top_2[0]["asin"] != res["asin"] and len(top_2) < 2:
                        top_2.append(res)
                    if len(top_2) == 2:
                        break

    if len(top_2) < 2:
        print(json.dumps({"error": f"[SCRAPER FATAL] Imposible obtener 2 productos válidos para query: {query}"}))
        sys.exit(1)

    result_data = {
        "query": query,
        "format": "vs",
        "canal_nombre": canal_nombre,
        "project_dir": project_dir,
    }
    
    prod_dirs = ["producto_a", "producto_b"]
    prod_keys = ["product_a", "product_b"]

    import shutil
    for i, p in enumerate(top_2):
        if i > 1: break
        folder_name = prod_dirs[i]
        alias_name = f"0{i+1}_{folder_name}"
        prod_key = prod_keys[i]
        prod_dir = os.path.join(project_dir, folder_name)
        alias_dir = os.path.join(project_dir, alias_name)
        os.makedirs(prod_dir, exist_ok=True)
        os.makedirs(alias_dir, exist_ok=True)
        
        v_filename = None
        if p.get("video_url"):
            v_path = os.path.join(prod_dir, f"{prod_key}.mp4")
            success = download_product_video(p["video_url"], v_path)
            if success:
                v_filename = f"{folder_name}/{prod_key}.mp4"

        # Fallback a imagen estatica descartado por regla de negocio: solo videos reales de Amazon
                
        i_filename = None
        if p["img_url"]:
            try:
                i_res = session.get(p["img_url"], timeout=8)
                if i_res.status_code == 200:
                    i_path = os.path.join(prod_dir, f"{prod_key}.jpg")
                    with open(i_path, 'wb') as f:
                        f.write(i_res.content)
                    i_filename = f"{folder_name}/{prod_key}.jpg"
            except Exception:
                pass
                
        try:
            if v_filename and os.path.exists(os.path.join(prod_dir, f"{prod_key}.mp4")):
                shutil.copy2(os.path.join(prod_dir, f"{prod_key}.mp4"), os.path.join(alias_dir, f"{prod_key}.mp4"))
            if i_filename and os.path.exists(os.path.join(prod_dir, f"{prod_key}.jpg")):
                shutil.copy2(os.path.join(prod_dir, f"{prod_key}.jpg"), os.path.join(alias_dir, f"{prod_key}.jpg"))
        except Exception:
            pass
        # Reviews
        product_soup = BeautifulSoup(p["html"], 'html.parser')
        pos_reviews = scrape_reviews(p["asin"], session, headers, "positive", product_soup)
        # using 'critical' as the filter for negative reviews on amazon
        neg_reviews = scrape_reviews(p["asin"], session, headers, "critical", product_soup)
        
        affiliate_url = p["product_url"]
        if affiliate_tag:
            affiliate_url += f"?tag={affiliate_tag}"
            
        result_data[prod_key] = {
            "asin": p["asin"],
            "title": p["title"],
            "brand": p["brand"],
            "price": p["price"],
            "rating": p["rating_raw"],
            "rating_num": p["rating_num"],
            "video_file": v_filename,
            "image_file": i_filename,
            "product_url": affiliate_url,
            "positive_reviews": pos_reviews,
            "negative_reviews": neg_reviews
        }
        used_asins.add(p["asin"])

    save_channel_history(history_file, used_topics, used_asins)
    
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
    parser = argparse.ArgumentParser(description="Amazon A vs B Video & Reviews Scraper")
    parser.add_argument("--query", required=True, help="Palabra clave de búsqueda")
    parser.add_argument("--canal", required=True, help="Nombre de la carpeta del canal")
    parser.add_argument("--base_dir", default="/home/javierferb/ia-lab-files/videos/edicion_ia", help="Ruta base del NAS o almacenamiento local")
    parser.add_argument("--affiliate_tag", help="Etiqueta de afiliados de Amazon (opcional)")
    
    args = parser.parse_args()
    
    res = scrape_amazon_vs(args.query, args.canal, args.base_dir, args.affiliate_tag)
    print(json.dumps(res, ensure_ascii=False))
