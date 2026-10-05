#!/usr/bin/env python3
"""
amazon_cocina_top_scraper.py
Scraper especializado y blindado para rankings TOP (hasta 7 productos) en "La Cocina Tecnológica".
Garantiza homogeneidad absoluta: los 7 productos pertenecen estrictamente a la MISMA subcategoría.
Rechaza jeringas de asado en sifones, accesorios sueltos, recambios y herramientas cruzadas.
"""

import sys
import os
import json
import argparse
import re
import html
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from curl_cffi import requests
from bs4 import BeautifulSoup

KNOWN_BRANDS = [
    'moulinex', 'cosori', 'ninja', 'cecotec', 'philips', 'princess',
    'aigostar', 'xiaomi', 'taurus', 'russell hobbs', 'ufesa', 'cecofry',
    'instant', 'innsky', 'proscenic', 'ikohs', 'create', 'fridja', 'mellerware',
    'krups', 'delonghi', 'melitta', 'neretva', 'outin', 'wmf', 'bonsenkitchen', 'jata',
    'bestron', 'lacor', 'klarstein', 'solac', 'bra', 'orbegozo', 'fagor', 'seb',
    'tefal', 'bosch', 'siemens', 'braun', 'kenwood', 'kitchenaid', 'smeg',
    'le creuset', 'zwilling', 'arcos', 'lekue', 'severin', 'oster', 'bialetti',
    'de buyer', 'berghoff', 'silikomart', 'vitamix', 'magimix', 'thermomix',
    'b-ars', 'isi', 'mosa', 'mastrad', 'ibili', 'cuisinart', 'monix'
]

KITCHEN_STOPWORDS = {
    'de', 'del', 'para', 'con', 'en', 'los', 'las', 'un', 'una', 'y', 'el', 'la', 'por', 'a',
    'cocina', 'cocinar', 'cocinas', 'reposteria', 'repostería', 'gastronomia', 'gastronomía',
    'culinario', 'culinaria', 'chef', 'hogar', 'casa', 'mesa', 'comida', 'plato', 'receta', 'recetas',
    'electrico', 'electrica', 'electricos', 'electricas', 'manual', 'profesional', 'domestico', 'domestica',
    'top', 'mejores', 'mejor', 'calidad', 'precio', '2024', '2025', '2026', 'guia', 'acero', 'inoxidable'
}

GLOBAL_ACCESSORY_REJECT_KEYWORDS = [
    'molde de silicona', 'moldes de silicona', 'papel para freidora', 'papel pergamino',
    'rejilla para freidora', 'alfombrilla de silicona', 'pulverizador de aceite', 'aceitera pulverizador',
    'pastillas descalcificadoras', 'descalcificador', 'filtro de agua para cafetera', 'filtros de cafetera',
    'bolsas de vacio solas', 'rollos de vacio', 'rollos gofrados', 'recambio de bolsas',
    'funda protectora', 'bolsa de transporte', 'funda para',
    'cargas de sifon', 'cargas de n2o', 'capsulas de n2o', 'cápsulas de n2o', 'solo cargas', 'solo cápsulas',
    'recambio de boquillas', 'piezas de repuesto', 'cuchilla de repuesto', 'vaso de repuesto',
    'grapadora', 'soporte monitor', 'tripode', 'dslr',
    'silicona para baño', 'silicona blanca', 'pattex', 'impermeabilizante', 'sellador invisible',
    'sellador de fugas', 'sellador de juntas', 'revestimiento impermeable', 'sellador de roscas',
    'sellador acrilico', 'masilla', 'pegamento'
]

# Definición exhaustiva de Subcategorías de Cocina
KITCHEN_SUBCATEGORIES = [
    {
        "id": "sifon_cocina",
        "triggers": [r'\bsifon(es)?\b', r'\bsifón(es)?\b', r'\bcrema batida\b', r'\bdispensador.*(nata|espuma|crema)\b'],
        "required": ['sifón', 'sifon', 'dispensador de nata', 'dispensador de crema', 'dispensador crema', 'dispensador de espumas', 'whipper', 'cream dispenser', 'montador de nata'],
        "forbidden": ['jeringa', 'jeringuilla', 'baster', 'inyector', 'mechador', 'cargas de', 'cápsulas de n2o', 'capsulas n2o', 'solo cápsulas', 'solo cargas', 'aguja'],
        "synonym_queries": ["sifon de cocina espumas", "sifon nata reposteria profesional", "dispensador crema batida sifon"]
    },
    {
        "id": "freidora_aire",
        "triggers": [r'\bfreidora.*aire\b', r'\bair fryer\b', r'\bairfryer\b', r'\bcecofry\b', r'\bfreidora sin aceite\b'],
        "required": ['freidora de aire', 'freidora sin aceite', 'air fryer', 'airfryer', 'cecofry', 'dual zone'],
        "forbidden": ['papel', 'molde', 'rejilla', 'pulverizador', 'alfombrilla', 'aceitera', 'accesorios'],
        "synonym_queries": ["freidora de aire digital", "air fryer gran capacidad", "freidora sin aceite"]
    },
    {
        "id": "cafetera",
        "triggers": [r'\bcafetera(s)?\b', r'\bespresso\b', r'\bexpreso\b', r'\bsuperautomatica\b'],
        "required": ['cafetera', 'cafeteras', 'espresso', 'expreso', 'coffee maker', 'espresso maker', 'coffee machine', 'superautomática', 'superautomatica', 'cafetera express', 'cafelizzia'],
        "forbidden": ['pastillas descalcificadoras', 'descalcificador', 'filtro de agua para cafetera', 'portacapsulas', 'solo cápsulas', 'solo capsulas'],
        "synonym_queries": ["cafetera espresso automatica", "cafetera superautomatica", "cafetera de goteo"]
    },
    {
        "id": "batidora_vaso",
        "triggers": [r'\bbatidora de vaso\b', r'\bsmoothie\b', r'\bblender\b'],
        "required": ['batidora de vaso', 'smoothie maker', 'blender', 'batidora americana'],
        "forbidden": ['batidora de mano', 'batidora de brazo', 'minipimer', 'amasadora', 'cuchilla de repuesto'],
        "synonym_queries": ["batidora de vaso americana", "blender smoothie potente"]
    },
    {
        "id": "batidora_mano",
        "triggers": [r'\bbatidora de mano\b', r'\bbatidora de brazo\b', r'\bminipimer\b', r'\bhand blender\b'],
        "required": ['batidora de mano', 'batidora de brazo', 'minipimer', 'hand blender'],
        "forbidden": ['batidora de vaso', 'amasadora de pan'],
        "synonym_queries": ["batidora de mano potente", "batidora de brazo minipimer"]
    },
    {
        "id": "amasadora",
        "triggers": [r'\bamasadora\b', r'\bbatidora amasadora\b', r'\bstand mixer\b', r'\brobot reposteria\b'],
        "required": ['amasadora', 'batidora amasadora', 'stand mixer', 'robot reposteria'],
        "forbidden": ['batidora de mano', 'batidora de vaso'],
        "synonym_queries": ["batidora amasadora reposteria", "amasadora de pan bol"]
    },
    {
        "id": "cuchillos",
        "triggers": [r'\bcuchillo(s)?\b', r'\bsantoku\b', r'\bset de cuchillos\b', r'\bjuego de cuchillos\b'],
        "required": ['cuchillo', 'cuchillos', 'santoku', 'chef knife', 'bloque de cuchillos', 'taco de cuchillos', 'juego de cuchillos', 'set de cuchillos'],
        "forbidden": ['afilador', 'afiladores', 'chaira', 'chairas', 'piedra de afilar', 'piedra afilar', 'funda para cuchillos', 'tabla de cortar', 'soporte magnetico'],
        "synonym_queries": ["juego de cuchillos de cocina chef", "cuchillos cocina japoneses santoku"]
    },
    {
        "id": "afilador",
        "triggers": [r'\bafilador(es)?\b', r'\bchaira(s)?\b', r'\bpiedra de afilar\b'],
        "required": ['afilador', 'afiladores', 'chaira', 'chairas', 'piedra de afilar', 'knife sharpener'],
        "forbidden": ['juego de cuchillos', 'set de cuchillos', 'bloque de cuchillos', 'taco de cuchillos', 'cuchillo santoku', 'cuchillo de chef', 'cuchillo jamonero', 'cuchillo panero'],
        "synonym_queries": ["afilador de cuchillos manual y electrico", "piedra de afilar cuchillos cocina"]
    },
    {
        "id": "sartenes",
        "triggers": [r'\bsart[eé]n(es)?\b', r'\bwok\b', r'\bcrepera\b'],
        "required": ['sartén', 'sarten', 'sartenes', 'wok', 'crepera', 'skillet', 'frying pan'],
        "forbidden": ['tapa para sarten', 'protectores de sartenes', 'protector de sartenes', 'protectores de fieltro', 'mango de repuesto'],
        "synonym_queries": ["sartenes induccion antiadherentes", "juego de sartenes cocina"]
    },
    {
        "id": "ollas",
        "triggers": [r'\bolla(s)?\b', r'\bolla express\b', r'\bolla a presi[oó]n\b', r'\bcacerola(s)?\b', r'\bcocotte\b'],
        "required": ['olla', 'ollas', 'cacerola', 'cacerolas', 'cocotte', 'cazuela', 'pressure cooker'],
        "forbidden": ['valvula de repuesto', 'válvula de repuesto', 'junta para olla', 'junta de goma', 'junta de silicona', 'goma para olla', 'valvula de seguridad'],
        "synonym_queries": ["olla a presion rapida express", "bateria de ollas cocina"]
    },
    {
        "id": "tostadora",
        "triggers": [r'\btostador(a)?(s)?\b'],
        "required": ['tostadora', 'tostador', 'toaster'],
        "forbidden": ['pinzas para tostadora', 'funda tostadora'],
        "synonym_queries": ["tostadora de pan ranura ancha", "tostador acero inoxidable"]
    },
    {
        "id": "envasadora_vacio",
        "triggers": [r'\benvasadora(s)?\b', r'\bselladora.*vacio\b', r'\bsellador(a)?.*bolsa(s)?\b'],
        "required": ['envasadora', 'selladora', 'sellador', 'máquina selladora', 'maquina selladora', 'sellador térmico', 'selladora térmica', 'vacuum sealer'],
        "forbidden": ['rollos de bolsas', 'bolsas de vacío', 'recambio bolsas', 'pattex', 'impermeabilizante', 'silicona', 'sellador de roscas', 'sellador invisible'],
        "synonym_queries": ["envasadora al vacio domestica alimentos", "selladora al vacio profesional"]
    },
    {
        "id": "bascula",
        "triggers": [r'\bb[aá]scula(s)?\b', r'\bbalanza digital\b', r'\bpeso de cocina\b'],
        "required": ['báscula', 'bascula', 'balanza', 'peso de cocina', 'kitchen scale'],
        "forbidden": ['pilas', 'pesa de calibracion'],
        "synonym_queries": ["bascula digital de cocina precision", "balanza de alimentos digital"]
    },
    {
        "id": "picadora",
        "triggers": [r'\bpicadora(s)?\b', r'\btrituradora de alimentos\b'],
        "required": ['picadora', 'picador', 'triturador de alimentos', 'chopper', 'meat grinder'],
        "forbidden": [],
        "synonym_queries": ["picadora electrica de alimentos verduras carne"]
    },
    {
        "id": "sandwichera_gofrera",
        "triggers": [r'\bsandwichera(s)?\b', r'\bgofrera(s)?\b'],
        "required": ['sandwichera', 'gofrera', 'waffle maker', 'sandwich maker'],
        "forbidden": [],
        "synonym_queries": ["sandwichera placas intercambiables 3 en 1", "gofrera electrica"]
    },
    {
        "id": "hervidor",
        "triggers": [r'\bhervidor(es)?\b', r'\bkettle\b'],
        "required": ['hervidor', 'tetera eléctrica', 'water kettle', 'hervidor de agua'],
        "forbidden": [],
        "synonym_queries": ["hervidor de agua electrico acero inoxidable"]
    },
    {
        "id": "parrilla_grill",
        "triggers": [r'\bparrilla(s)?\b', r'\bgrill\b', r'\bplancha de asar\b', r'\braclette\b'],
        "required": ['parrilla', 'plancha de asar', 'grill', 'raclette', 'contact grill'],
        "forbidden": ['induccion sola', 'aluminio fundido sin resistencia', 'plancha para gas'],
        "synonym_queries": ["plancha de asar electrica antiadherente", "grill electrico panini"]
    },
    {
        "id": "mandolina",
        "triggers": [r'\bmandolina(s)?\b', r'\bcortador de verduras\b', r'\bespiralizador\b'],
        "required": ['mandolina', 'cortador de verduras', 'espiralizador', 'vegetable slicer'],
        "forbidden": ['guantes anticorte solos'],
        "synonym_queries": ["mandolina de cocina profesional corte regulable", "cortador de verduras multifuncion"]
    },
    {
        "id": "soplete",
        "triggers": [r'\bsoplete(s)?\b'],
        "required": ['soplete', 'kitchen torch', 'blow torch'],
        "forbidden": ['bombonas de gas solas'],
        "synonym_queries": ["soplete de cocina reposteria profesional gas"]
    },
    {
        "id": "triturador_basura",
        "triggers": [r'\btriturador.*(basura|desperdicio|fregadero|comida|alimento)\b', r'\bdisposer\b', r'\btriturador(es)?\b'],
        "required": ['triturador', 'trituradora', 'trituradores', 'desperdicios', 'triturador de basura', 'triturador de alimentos', 'garbage disposal', 'food waste'],
        "forbidden": ['picadora de carne', 'trituradora de papel', 'batidora'],
        "synonym_queries": ["triturador de desperdicios cocina fregadero", "triturador de basura para fregadero"]
    },
    {
        "id": "jeringa_asado",
        "triggers": [r'\bjeringa.*(carne|asado|adobo|pavo)\b', r'\bmechador\b', r'\binyector de carne\b'],
        "required": ['jeringa de cocina', 'jeringa de carne', 'inyector de carne', 'mechador', 'meat injector', 'baster'],
        "forbidden": ['sifón', 'sifon', 'cafetera', 'freidora'],
        "synonym_queries": ["jeringa de cocina para carne asados marinados"]
    }
]

def clean_slug(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text.strip('_')

def detect_kitchen_subcategory(query):
    q_low = query.lower()
    # Check specific tools/accessories first before broad categories (e.g. afilador before cuchillos)
    for subcat in KITCHEN_SUBCATEGORIES:
        if subcat["id"] == "cuchillos" and any(k in q_low for k in ['afilador', 'chaira', 'piedra de afilar']):
            continue
        for pattern in subcat["triggers"]:
            if re.search(pattern, q_low):
                return subcat
    
    # Fallback dinámico: extraer el sustantivo principal (Head Noun) con variantes de número
    words = [w for w in re.findall(r'\b\w+\b', q_low) if w not in KITCHEN_STOPWORDS and len(w) > 3]
    if words:
        head_noun = words[0]
        variants = {head_noun}
        if head_noun.endswith('es') and len(head_noun) > 4:
            variants.add(head_noun[:-2])
        elif head_noun.endswith('s') and len(head_noun) > 3:
            variants.add(head_noun[:-1])
        return {
            "id": f"dynamic_{head_noun}",
            "triggers": [r'\b' + head_noun + r'\b'],
            "required": list(variants),
            "forbidden": ['jeringa', 'grapadora', 'funda', 'pattex', 'silicona'],
            "synonym_queries": [f"{head_noun} cocina profesional", f"{list(variants)[-1]} de cocina"]
        }
    return None

def is_product_valid_for_subcat(title, subcat, original_query):
    t_low = title.lower()
    q_low = original_query.lower()

    # 1. Rechazo global de accesorios genéricos (a menos que la query los pida)
    for acc in GLOBAL_ACCESSORY_REJECT_KEYWORDS:
        if acc in t_low and acc not in q_low:
            return False

    if not subcat:
        # Si no hay subcategoría detectada, al menos debe coincidir con alguna palabra clave nuclear
        q_words = [w for w in re.findall(r'\b\w+\b', q_low) if w not in KITCHEN_STOPWORDS and len(w) > 3]
        return any(w[:4] in t_low for w in q_words)

    # 2. Rechazo explícito de términos prohibidos de la subcategoría
    for forb in subcat.get("forbidden", []):
        if forb in t_low and forb not in q_low:
            return False

    # 3. Exigencia estricta: al menos un término requerido DEBE aparecer en el título
    req_terms = subcat.get("required", [])
    has_req = False
    for term in req_terms:
        if term in t_low:
            has_req = True
            break
        if term.endswith('es') and len(term) > 4 and term[:-2] in t_low:
            has_req = True
            break
        if term.endswith('s') and len(term) > 3 and term[:-1] in t_low:
            has_req = True
            break
    return has_req

def get_product_brand(title):
    t = title.lower()
    for b in KNOWN_BRANDS:
        if b in t:
            return b
    first_word = t.split()[0] if t.split() else "desconocido"
    if first_word in ['el', 'la', 'los', 'las', 'un', 'una', 'del', 'de', 'en', 'con', 'por', 'mejores', 'top']:
        return t[:35]
    return first_word

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

def safe_get(session, url, headers=None, timeout=15, retries=3):
    for i in range(retries):
        try:
            resp = session.get(url, headers=headers, timeout=timeout)
            if resp and resp.status_code == 200:
                bm_match = re.search(r"URL='([^']+?)'", resp.text)
                if bm_match:
                    redirect_url = 'https://www.amazon.es' + html.unescape(bm_match.group(1))
                    time.sleep(5.2)
                    resp = session.get(redirect_url, headers=headers, timeout=timeout)
                if resp and len(resp.text) > 10000:
                    return resp
            time.sleep(1.0 * (i + 1))
        except Exception:
            time.sleep(1.0 * (i + 1))
    return None

def download_product_video(video_url, output_path):
    if not video_url:
        return False
    try:
        cmd = [
            'ffmpeg', '-y',
            '-headers', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n',
            '-i', video_url,
            '-c', 'copy',
            '-an',
            output_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=40)
        if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 50000:
            return True
    except Exception:
        pass

    try:
        cmd2 = [
            'ffmpeg', '-y',
            '-headers', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n',
            '-i', video_url,
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '22',
            '-an',
            output_path
        ]
        res2 = subprocess.run(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=50)
        return res2.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 50000
    except Exception:
        return False

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


def process_asin(asin, headers, query, session, subcat):
    try:
        detail_url = f"https://www.amazon.es/dp/{asin}"
        p_resp = safe_get(session, detail_url, headers=headers, timeout=12)
        if not p_resp or p_resp.status_code != 200:
            return None

        soup = BeautifulSoup(p_resp.text, 'html.parser')
        title_el = soup.select_one('#productTitle') or soup.select_one('h1')
        title = title_el.text.strip() if title_el else f"Producto {asin}"

        # Validación estricta de subcategoría
        if not is_product_valid_for_subcat(title, subcat, query):
            return None

        brand = get_product_brand(title)
        video_url = extract_relevant_product_video(p_resp.text, brand, query)
        if not video_url:
            return None

        # Precio
        price = "Consultar en Amazon"
        p_whole = soup.select_one('.a-price-whole')
        p_frac = soup.select_one('.a-price-fraction')
        if p_whole:
            price = f"{p_whole.text.strip().replace('.', '')},{p_frac.text.strip() if p_frac else '00'}€"

        # Rating
        rating_raw = "4.3 de 5 estrellas"
        rating_num = 4.3
        r_el = soup.select_one('span[data-hook="rating-out-of-text"]') or soup.select_one('.a-icon-alt')
        if r_el:
            rating_raw = r_el.text.strip()
            rating_num = parse_rating(rating_raw)

        # Imagen
        img_url = None
        img_el = soup.select_one('#landingImage') or soup.select_one('#imgBlkFront')
        if img_el:
            img_url = img_el.get('src') or img_el.get('data-old-hires')

        # Features
        features = []
        fb = soup.select('#feature-bullets li span.a-list-item')
        for f in fb[:4]:
            t = f.text.strip()
            if t and len(t) > 10 and not t.startswith(('Marca:', 'Fabricante:', 'ASIN:')):
                features.append(t)

        # Specs
        specs = {}
        for row in soup.select('#productDetails_techSpec_section_1 tr, #prodDetails tr'):
            th = row.select_one('th')
            td = row.select_one('td')
            if th and td:
                k = th.text.strip()
                v = td.text.strip()
                if k and v and len(specs) < 6:
                    specs[k] = v

        # Review count
        rc_el = soup.select_one('#acrCustomerReviewText')
        review_count = rc_el.text.strip() if rc_el else "100+ valoraciones"

        return {
            "asin": asin,
            "title": title,
            "price": price,
            "rating_raw": rating_raw,
            "rating_num": rating_num,
            "img_url": img_url,
            "video_url": video_url,
            "features": features,
            "specs": specs,
            "review_count": review_count,
            "product_url": f"https://www.amazon.es/dp/{asin}",
            "subcat_id": subcat["id"] if subcat else "generic"
        }
    except Exception:
        return None

def scrape_amazon_cocina_top(query, canal_nombre, base_dir="/home/javierferb/ia-lab-files/videos/edicion_ia", limit=7):
    if not query or len(str(query).strip()) < 3:
        print(json.dumps({"error": "[SCRAPER ERROR] search query is empty or invalid (< 3 chars). Aborting to prevent invalid products."}))
        sys.exit(1)
    if not canal_nombre or len(str(canal_nombre).strip()) < 2:
        print(json.dumps({"error": "[SCRAPER ERROR] canal_nombre is empty or invalid. Aborting to prevent saving to root."}))
        sys.exit(1)

    subcat = detect_kitchen_subcategory(query)
    subcat_name = subcat["id"] if subcat else "generico"
    print(f"[COCINA SCRAPER] Query: '{query}' -> Subcategoría identificada: '{subcat_name}'", file=sys.stderr)

    project_dir = os.path.join(base_dir, canal_nombre)
    os.makedirs(project_dir, exist_ok=True)

    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'accept-language': 'es-ES,es;q=0.9,en;q=0.8',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    session = requests.Session(impersonate="chrome120")

    search_queries = [query]
    if subcat and subcat.get("synonym_queries"):
        for syn in subcat["synonym_queries"]:
            if syn.lower() not in [sq.lower() for sq in search_queries]:
                search_queries.append(syn)

    qualified_raw = []
    seen_asins = set()

    for sq in search_queries:
        if len(qualified_raw) >= max(limit * 2, 8):
            break
        print(f"[COCINA SCRAPER] Explorando búsqueda en Amazon: '{sq}'", file=sys.stderr)
        for page in range(1, 6):
            if len(qualified_raw) >= max(limit * 2, 8):
                break
            search_url = f"https://www.amazon.es/s?k={requests.utils.quote(sq)}&page={page}"
            response = safe_get(session, search_url, headers=headers, timeout=12)
            if not response or response.status_code != 200:
                continue

            search_soup = BeautifulSoup(response.text, 'html.parser')
            dom_asins = [div.get('data-asin').strip() for div in search_soup.select('div[data-asin]') if div.get('data-asin') and len(div.get('data-asin').strip()) == 10]
            new_asins = [a for a in dom_asins if a not in seen_asins]
            for a in new_asins:
                seen_asins.add(a)

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(process_asin, a, headers, query, session, subcat) for a in new_asins[:15]]
                for f in as_completed(futures):
                    res = f.result()
                    if res and res not in qualified_raw:
                        # Doble verificación: producto debe pertenecer a la misma subcategoría
                        if subcat and res["subcat_id"] == subcat["id"]:
                            qualified_raw.append(res)
                            print(f"  [ACEPTADO {subcat_name}] {res['title'][:60]} ({res['asin']})", file=sys.stderr)
                            if len(qualified_raw) >= max(limit * 2, 8):
                                break

    if len(qualified_raw) < 2:
        print(json.dumps({
            "error": f"[SCRAPER ERROR] No se encontraron suficientes productos con vídeo real para la subcategoría '{subcat_name}'. Encontrados: {len(qualified_raw)}. Abortando para evitar mezclar productos incongruentes."
        }))
        sys.exit(1)

    # Crear pool priorizando diversidad de marcas pero incluyendo todos los calificados
    candidates_pool = []
    seen_brands = set()
    for p in qualified_raw:
        brand = get_product_brand(p["title"])
        if brand not in seen_brands:
            seen_brands.add(brand)
            candidates_pool.append(p)

    for p in qualified_raw:
        if p not in candidates_pool:
            candidates_pool.append(p)

    # Descarga de vídeos iterando sobre todo el pool hasta completar el cupo
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

        if not v_filename:
            try:
                import shutil
                shutil.rmtree(prod_dir, ignore_errors=True)
            except Exception:
                pass
            continue

        i_filename = None
        if p.get("img_url"):
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
            "description_snippet": p.get("title", ""),
            "review_count": p.get("review_count", ""),
            "has_video": True,
            "video_file": v_filename,
            "image_file": i_filename,
            "product_url": p["product_url"],
            "subcat_id": p.get("subcat_id")
        })
        rank += 1

    if len(products) < 2:
        print(json.dumps({
            "error": f"[SCRAPER ERROR] Falló la descarga de vídeos para los productos de '{subcat_name}'. Mínimo requerido 2, descargados {len(products)}."
        }))
        sys.exit(1)

    result_data = {
        "query": query,
        "canal_nombre": canal_nombre,
        "project_dir": project_dir,
        "products": products,
        "subcategory": subcat_name
    }

    data_json_path = os.path.join(project_dir, "data.json")
    try:
        os.chmod(project_dir, 0o777)
    except Exception:
        pass
    with open(data_json_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    print(json.dumps(result_data, ensure_ascii=False))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper Cocina TOP Amazon Especializado y Blindado")
    parser.add_argument("--query", type=str, required=True, help="Término de búsqueda")
    parser.add_argument("--canal", type=str, required=True, help="Nombre del canal/subcarpeta")
    parser.add_argument("--base_dir", type=str, default="/home/javierferb/ia-lab-files/videos/edicion_ia", help="Directorio base")
    parser.add_argument("--limit", type=int, default=7, help="Número de productos")
    args = parser.parse_args()

    scrape_amazon_cocina_top(args.query, args.canal, args.base_dir, args.limit)
