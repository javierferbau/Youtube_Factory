#!/usr/bin/env python3
"""
amazon_cocina_scraper.py
Scraper especializado y blindado para comparativas VS (2 productos) en "La Cocina Tecnológica".
Garantiza homogeneidad absoluta: ambos productos pertenecen estrictamente a la MISMA subcategoría.
Previene emparejamientos absurdos (ej: zapato vs toallita, freidora vs molde, cuchillo vs afilador).
Soporta marcas distintas (Brand A vs Brand B) y rescate inteligente con Akamai delay (5.2s).
"""
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
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from curl_cffi import requests
from bs4 import BeautifulSoup

KNOWN_BRANDS = [
    'moulinex', 'cosori', 'ninja', 'cecotec', 'philips', 'princess',
    'aigostar', 'xiaomi', 'taurus', 'russell hobbs', 'ufesa', 'cecofry',
    'instant', 'innsky', 'proscenic', 'ikohs', 'create', 'fridja', 'mellerware',
    'krups', 'delonghi', "de'longhi", 'melitta', 'neretva', 'outin', 'wmf', 'bonsenkitchen', 'jata',
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
    'top', 'mejores', 'mejor', 'calidad', 'precio', '2024', '2025', '2026', 'guia', 'acero', 'inoxidable', 'vs'
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

FOOD_KEYWORDS = [
    'barritas', 'barrita', 'chocolate negro', 'tableta', 'tabletas', 'cacao en polvo',
    'cobertura', 'bombones', 'pralinés', 'trufas', 'caramelo', 'keto', 'proteína',
    'crema de cacao', 'nutella', 'café en grano', 'café molido', 'té', 'infusión',
    'galletas', 'cereales', 'mermelada', 'sirope', 'vainilla', 'canela',
    'peanut', 'cacahuetes', 'almendras', 'nueces', 'fudge'
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
        "triggers": [r'\bfreidora.*aire\b', r'\bair fryer\b', r'\bairfryer\b', r'\bcecofry\b', r'\bfreidora sin aceite\b', r'\bcosori\b', r'\baerofryer\b', r'\bdual blaze\b', r'\bdualzone\b'],
        "required": ['freidora de aire', 'freidora sin aceite', 'air fryer', 'airfryer', 'cecofry', 'dual zone', 'cosori', 'aerofryer', 'dual blaze', 'dualzone'],
        "forbidden": ['papel', 'molde', 'rejilla', 'pulverizador', 'alfombrilla', 'aceitera', 'accesorios'],
        "synonym_queries": ["freidora de aire digital", "air fryer gran capacidad", "freidora sin aceite"]
    },
    {
        "id": "cafetera",
        "triggers": [r'\bcafetera(s)?\b', r'\bespresso\b', r'\bexpreso\b', r'\bsuperautomatica\b', r'\bcafelizzia\b', r'\bdedica\b', r'\bmagnifica\b', r'\binissia\b', r'\bvertuo\b', r'\bnespresso\b'],
        "required": ['cafetera', 'cafeteras', 'espresso', 'expreso', 'coffee maker', 'espresso maker', 'coffee machine', 'superautomática', 'superautomatica', 'cafetera express', 'cafelizzia', 'dedica', 'magnifica', 'inissia', 'vertuo', 'delonghi', "de'longhi"],
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

def _normalize(text):
    import unicodedata
    return unicodedata.normalize('NFD', text.lower()).encode('ascii', 'ignore').decode('utf-8')

def detect_kitchen_subcategory(query):
    q_low = query.lower()
    for subcat in KITCHEN_SUBCATEGORIES:
        if subcat["id"] == "cuchillos" and any(k in q_low for k in ['afilador', 'chaira', 'piedra de afilar']):
            continue
        for pattern in subcat["triggers"]:
            if re.search(pattern, q_low):
                return subcat
    
    known_brands_flat = set(KNOWN_BRANDS) | {b.replace("'", "") for b in KNOWN_BRANDS}
    words = [w for w in re.findall(r'\b\w+\b', q_low) if w not in KITCHEN_STOPWORDS and w not in known_brands_flat and len(w) > 3]
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

    for acc in GLOBAL_ACCESSORY_REJECT_KEYWORDS:
        if acc in t_low and acc not in q_low:
            return False

    t_norm = _normalize(title)
    for food in FOOD_KEYWORDS:
        pattern = r'\b' + re.escape(_normalize(food)) + r'\b'
        if re.search(pattern, t_norm):
            return False

    if not subcat:
        q_words = [w for w in re.findall(r'\b\w+\b', q_low) if w not in KITCHEN_STOPWORDS and len(w) > 3]
        return any(w[:4] in t_low for w in q_words)

    for forb in subcat.get("forbidden", []):
        if forb in t_low and forb not in q_low:
            return False

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
    try:
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def extract_kitchen_specs(soup, title, html_text):
    text_blob = soup.get_text(" ", strip=True) + " " + title
    text_lower = text_blob.lower()
    
    capacity = None
    m_cap = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:l|litros|litro)\b', text_lower)
    if m_cap:
        capacity = f"{m_cap.group(1).replace(',', '.')} L"
        
    power = None
    m_pow = re.search(r'(\d{3,4})\s*(?:w|watios|vatios)\b', text_lower)
    if m_pow:
        power = f"{m_pow.group(1)} W"
        
    dishwasher = False
    if any(k in text_lower for k in ['lavavajillas', 'lavavajilla', 'apto para lavavajillas', 'dishwasher safe']):
        dishwasher = True
        
    presets = None
    m_pres = re.search(r'(\d+)\s*(?:programas|funciones|modos)\b', text_lower)
    if m_pres:
        presets = f"{m_pres.group(1)} programas"
        
    return {
        "capacity": capacity or "N/D",
        "power": power or "N/D",
        "dishwasher_safe": dishwasher,
        "presets": presets or "N/D"
    }

def extract_relevant_product_video(html_text, product_brand, search_query):
    decoded_html = html.unescape(html_text.replace("\\/", "/"))
    pattern = r'"(?:videoURL|videoUrl|videoPreviewAssets|mediaUrl|url)"\s*:\s*"(https://[^"]+?\.(?:mp4|m3u8)[^"]*)"'
    stream_matches = re.findall(pattern, decoded_html, re.IGNORECASE)
    vse_direct = re.findall(r'https://m\.media-amazon\.com/images/S/vse-vms-transcoding-artifact[^"]+?\.mp4', decoded_html)
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
                "title": "Excelente electrodoméstico",
                "text": "Funciona a la perfección, ahorra tiempo en la cocina y la calidad de los acabados es notable.",
                "author": "Cocinero Satisfecho",
                "synthetic": True
            })
        else:
            reviews.append({
                "stars": float(random.choice([1.0, 2.0, 3.0])),
                "title": "Aspectos a mejorar",
                "text": "Es algo ruidoso y la limpieza requiere más esfuerzo del esperado.",
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

def process_asin(asin, session, headers, search_query, subcat):
    prod_url = f"https://www.amazon.es/dp/{asin}"
    try:
        p_resp = safe_get(session, prod_url, headers=headers, timeout=12)
        if not p_resp or p_resp.status_code != 200:
            return None
            
        soup = BeautifulSoup(p_resp.text, 'html.parser')
        
        title_el = soup.select_one('#productTitle') or soup.select_one('h1')
        title = title_el.text.strip() if title_el else f"Producto {asin}"
        
        # Validar subcategoría estricta
        if not is_product_valid_for_subcat(title, subcat, search_query):
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
        
        if rating_num > 0 and rating_num < 3.8:
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
        
        if not product_video_url:
            return None
            
        specs = extract_kitchen_specs(soup, title, p_resp.text)

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
            "html": p_resp.text,
            "specs": specs,
            "subcat_id": subcat["id"] if subcat else "kitchen"
        }
    except Exception:
        return None

def scrape_amazon_cocina(query, canal_nombre, base_dir="/home/javierferb/ia-lab-files/videos/edicion_ia", affiliate_tag=None):
    query_slug = clean_slug(query)
    
    if canal_nombre.endswith(f"{query_slug}_vs") or canal_nombre.endswith("_vs"):
        project_dir = os.path.join(base_dir, canal_nombre)
    else:
        project_dir = os.path.join(base_dir, canal_nombre, f"{query_slug}_vs")
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
    
    # 1. Identificar Subcategoría estricta
    subcat = detect_kitchen_subcategory(query)
    print(f"[COCINA VS] Query: '{query}' -> Subcategoría identificada: '{subcat['id'] if subcat else 'None'}'", file=sys.stderr)

    # Detectar si hay marcas explícitas en la query (ej: cecotec vs cosori)
    q_low = query.lower()
    target_brands = []
    for b in KNOWN_BRANDS:
        if re.search(r'\b' + re.escape(b) + r'\b', q_low):
            target_brands.append(b)

    qualified_raw = []
    seen_asins = set(used_asins)

    # 2. Búsqueda iterativa en Amazon (soporte duelos francotirador A vs B)
    search_queries = []
    if " vs " in query.lower():
        parts = re.split(r'\s+vs\s+', query, flags=re.IGNORECASE)
        if len(parts) == 2:
            search_queries.extend([parts[0].strip(), parts[1].strip()])
    search_queries.append(query)
    if subcat and subcat.get("synonym_queries"):
        search_queries.extend(subcat["synonym_queries"][:2])

    for s_q in search_queries:
        if len(qualified_raw) >= 6:
            break
        for page in range(1, 3):
            if len(qualified_raw) >= 6:
                break
            search_url = f"https://www.amazon.es/s?k={requests.utils.quote(s_q)}&page={page}"
            response = safe_get(session, search_url, headers=headers, timeout=12)
            if not response or response.status_code != 200:
                continue

            soup_search = BeautifulSoup(response.text, 'html.parser')
            soup_asins = [d.get('data-asin').strip() for d in soup_search.select('div[data-asin]') if d.get('data-asin') and len(d.get('data-asin').strip()) == 10]
            regex_asins = list(set(re.findall(r'B0[A-Z0-9]{8}', response.text)))
            page_asins = list(dict.fromkeys(soup_asins + regex_asins))
            new_asins = [a for a in page_asins if a not in seen_asins]
            for a in new_asins:
                seen_asins.add(a)

            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(process_asin, asin, session, headers, query, subcat) for asin in new_asins[:15]]
                for f in as_completed(futures):
                    res = f.result()
                    if res:
                        qualified_raw.append(res)

    # 3. Fallback inteligente: mantenerse estrictamente en la misma subcategoría si se detectó
    if len(qualified_raw) < 2:
        if subcat and subcat.get("synonym_queries"):
            fallback_query = subcat["synonym_queries"][0]
            fb_subcat = subcat
        else:
            fallback_query = "freidoras de aire sin aceite cecotec cosori"
            fb_subcat = detect_kitchen_subcategory(fallback_query)
        fb_url = f"https://www.amazon.es/s?k={requests.utils.quote(fallback_query)}"
        fb_resp = safe_get(session, fb_url, headers=headers, timeout=12)
        if fb_resp and fb_resp.status_code == 200:
            fb_asins = list(set(re.findall(r'B0[A-Z0-9]{8}', fb_resp.text)))
            with ThreadPoolExecutor(max_workers=6) as executor:
                futures = [executor.submit(process_asin, asin, session, headers, fallback_query, fb_subcat) for asin in fb_asins[:12]]
                for f in as_completed(futures):
                    res = f.result()
                    if res:
                        qualified_raw.append(res)

    # Ordenar por puntuación de calidad
    qualified_raw.sort(key=lambda x: x["rating_num"] * math.log(x["review_count"] + 1), reverse=True)

    # 4. Selección homogénea de 2 productos con marcas distintas
    top_2 = []
    if len(target_brands) >= 2:
        b1, b2 = target_brands[0], target_brands[1]
        p1 = next((p for p in qualified_raw if p["brand"] == b1), None)
        p2 = next((p for p in qualified_raw if p["brand"] == b2), None)
        if p1 and p2 and p1["asin"] != p2["asin"]:
            top_2 = [p1, p2]

    if len(top_2) < 2:
        # Seleccionar 2 productos de marcas distintas dentro de la MISMA subcategoría
        seen_brands = set()
        candidate_pair = []
        for p in qualified_raw:
            if p["brand"] not in seen_brands:
                seen_brands.add(p["brand"])
                candidate_pair.append(p)
            if len(candidate_pair) == 2:
                break
        if len(candidate_pair) == 2:
            top_2 = candidate_pair

    # Si sólo hay una marca pero diferentes ASINs de la misma subcategoría
    if len(top_2) < 2 and len(qualified_raw) >= 2:
        top_2 = [qualified_raw[0], qualified_raw[1]]

    tag_to_use = affiliate_tag or "cocina_tag-21"
    result_data = {
        "query": query,
        "format": "vs",
        "canal_nombre": canal_nombre,
        "project_dir": project_dir,
        "affiliate_tag": tag_to_use,
        "subcategory": subcat["id"] if subcat else "kitchen"
    }

    prod_dirs = ["producto_a", "producto_b"]
    prod_keys = ["product_a", "product_b"]
    products_array = []

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
                
        i_filename = None
        if p.get("img_url"):
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

        product_soup = BeautifulSoup(p["html"], 'html.parser')
        pos_reviews = scrape_reviews(p["asin"], session, headers, "positive", product_soup)
        neg_reviews = scrape_reviews(p["asin"], session, headers, "critical", product_soup)
        
        affiliate_url = p["product_url"]
        if tag_to_use:
            affiliate_url += f"?tag={tag_to_use}"
            
        p_data = {
            "rank": i + 1,
            "folder": folder_name,
            "asin": p["asin"],
            "title": p["title"],
            "brand": p["brand"],
            "price": p["price"],
            "rating": p["rating_raw"],
            "rating_num": p["rating_num"],
            "specs": p["specs"],
            "has_video": bool(v_filename),
            "video_file": v_filename,
            "image_file": i_filename,
            "product_url": affiliate_url,
            "positive_reviews": pos_reviews,
            "negative_reviews": neg_reviews,
            "subcat_id": p.get("subcat_id")
        }
        result_data[prod_key] = p_data
        products_array.append(p_data)
        used_asins.add(p["asin"])

    result_data["products"] = products_array
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
    parser = argparse.ArgumentParser(description="Scraper Cocina Tecnológica VS Blindado")
    parser.add_argument("--query", required=True, help="Búsqueda o temática")
    parser.add_argument("--canal", default="la_cocina_tecnologica_del_pueblo", help="Nombre del canal/carpeta")
    parser.add_argument("--base_dir", default="/home/javierferb/ia-lab-files/videos/edicion_ia/cocina_tecnologica", help="Directorio base")
    parser.add_argument("--affiliate_tag", default="cocina_tag-21", help="Tag de afiliado")
    
    args = parser.parse_args()
    
    res = scrape_amazon_cocina(args.query, args.canal, args.base_dir, args.affiliate_tag)
    print(json.dumps(res, ensure_ascii=False))
