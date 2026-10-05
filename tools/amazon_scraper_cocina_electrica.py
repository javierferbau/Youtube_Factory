#!/usr/bin/env python3
# amazon_scraper_cocina_electrica.py
# Versión específica para el nicho "aparatos eléctricos de cocina".
# Filtrado estricto: solo acepta aparatos eléctricos de cocina con vídeo real.
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
    'moulinex', 'cosori', 'ninja', 'cecotec', 'philips', 'princess',
    'aigostar', 'xiaomi', 'taurus', 'russell hobbs', 'ufesa', 'cecofry',
    'instant', 'innsky', 'proscenic', 'ikohs', 'create', 'fridja', 'mellerware',
    'krups', 'delonghi', 'melitta', 'neretva', 'outin', 'wmf', 'bonsenkitchen', 'jata',
    'bestron', 'lacor', 'klarstein', 'solac', 'bra', 'orbegozo', 'fagor', 'seb',
    'tefal', 'bosch', 'siemens', 'braun', 'kenwood', 'kitchenaid', 'smeg'
]

# Palabras que indican accesorios o consumibles → rechazar siempre
ACCESSORY_KEYWORDS = [
    'molde', 'moldes', 'papel', 'accesorios', 'accesorio', 'funda',
    'limpiador', 'rejilla', 'pinzas', 'pulverizador', 'aceitera', 'alfombrilla',
    'termofusible', 'recambio', 'recambios', 'repuesto', 'repuestos',
    'cable', 'cables', 'filtro', 'filtros'
]

# Productos alimenticios → rechazar siempre (no son aparatos)
FOOD_KEYWORDS = [
    'barritas', 'barrita', 'chocolate negro', 'tableta', 'tabletas', 'cacao en polvo',
    'cobertura', 'bombones', 'pralinés', 'trufas', 'caramelo', 'keto', 'proteína',
    'crema de cacao', 'nutella', 'café en grano', 'café molido', 'té', 'infusión',
    'galletas', 'cereales', 'mermelada', 'sirope', 'vainilla', 'canela',
    'peanut', 'cacahuetes', 'almendras', 'nueces', 'fudge', 'nicks'
]

# Tipos de producto NO eléctricos de cocina → rechazar si no están en la query
NON_APPLIANCE_TYPES = [
    'escritorio', 'silla', 'sofa', 'sofá', 'cama', 'colchon', 'colchón',
    'armario', 'estanteria', 'mueble', 'televisor', 'cortina',
    'cojin', 'edredon', 'almohada',
    # Items de cocina pasivos (no eléctricos)
    'bol', 'bols', 'cuenco', 'cuencos', 'bandeja', 'bandejas',
    'cuchillo', 'cuchillos', 'tabla de cortar', 'espátula', 'espátulas',
    'taza', 'tazas', 'vaso', 'vasos', 'plato', 'platos', 'cazo', 'cazuela',
]

GENERIC_STOPWORDS = {
    'de', 'del', 'para', 'con', 'en', 'los', 'las', 'un', 'una', 'y', 'el', 'la',
    'por', 'a', 'electrico', 'electrica', 'electricos', 'electricas', 'portatil',
    'portatiles', 'top', 'mejores', '2026', '2025', '2024', 'mejor', 'guia', 'mesa'
}

# Palabras clave que DEBEN aparecer en el título para considerarlo del nicho
# Se construyen dinámicamente desde la query, pero estos son los stems mínimos del nicho
NICHE_REQUIRED_DEVICE_WORDS = [
    'chocolatera', 'chocolateras',
    'freidora', 'freidoras',
    'airfryer', 'air fryer',
    'batidora', 'batidoras',
    'licuadora', 'licuadoras',
    'exprimidor', 'exprimidores',
    'tostadora', 'tostadoras',
    'cafetera', 'cafeteras',
    'hervidor', 'hervidora',
    'sandwichera', 'sandwicheras',
    'gofrera', 'gofreras',
    'plancha', 'planchas',
    'horno', 'hornos',
    'microondas',
    'robot de cocina', 'robot cocina',
    'amasadora', 'amasadoras',
    'yogurtera', 'yogurteras',
    'deshidratador', 'deshidratadora',
    'picadora', 'picadoras',
    'pelador', 'peladora', 'peladores',
    'descorazonador', 'descorazonadores',
    'cortamanzanas', 'cortador', 'cortadores',
    'enfriador', 'enfriadores',
    'enfriabotellas',
    'espumador', 'espumadores',
    'vaporizador', 'vaporera', 'vaporeras',
    'slow cooker', 'olla programable',
    'thermomix', 'procesador de alimentos',
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
    """Lowercase + remove accents for robust matching."""
    import unicodedata
    return unicodedata.normalize('NFD', text.lower()).encode('ascii', 'ignore').decode('utf-8')

def is_actual_appliance(title, query=""):
    """Rechaza accesorios, alimentos y no-aparatos."""
    t = _normalize(title)

    # Rechazar productos alimenticios (word boundary para evitar falsos positivos)
    for food in FOOD_KEYWORDS:
        pattern = r'\b' + re.escape(_normalize(food)) + r'\b'
        if re.search(pattern, t):
            return False

    # Rechazar accesorios
    for acc in ACCESSORY_KEYWORDS:
        if re.search(r'\b' + re.escape(acc) + r'\b', t):
            return False

    # Rechazar objetos pasivos / muebles si no están en la query
    q = _normalize(query)
    for non_appl in NON_APPLIANCE_TYPES:
        kw = _normalize(non_appl)
        pattern = r'\b' + re.escape(kw) + r'\b'
        if re.search(pattern, t) and not re.search(pattern, q):
            return False

    return True

def is_product_relevant(title, query):
    """Valida relevancia estricta para nicho aparatos eléctricos de cocina."""
    t = _normalize(title)
    q = _normalize(query)

    # 1. Rechazar no-cocina absolutos (word boundary)
    for non_appl in NON_APPLIANCE_TYPES:
        kw = _normalize(non_appl)
        p = r'\b' + re.escape(kw) + r'\b'
        if re.search(p, t) and not re.search(p, q):
            return False

    # 2. Extraer palabras clave de la query (sin stopwords, longitud > 3)
    q_words = [w for w in re.findall(r'\b\w+\b', q) if w not in GENERIC_STOPWORDS and len(w) > 3]
    if not q_words:
        return True

    # 3. Coincidencia exacta de palabra completa
    matches = sum(1 for w in q_words if re.search(r'\b' + re.escape(w) + r'\b', t))
    if matches >= min(2, len(q_words)):
        return True

    # 3b. Coincidencia por stem de 4 caracteres para derivaciones (ej: pelar -> pelador, descorazonar -> descorazonador)
    stem_matches = sum(1 for w in q_words if w[:4] in t)
    if stem_matches >= min(2, len(q_words)):
        return True

    # 4. Fallback: aparato conocido del nicho + al menos un stem de palabra de query
    for device in NICHE_REQUIRED_DEVICE_WORDS:
        if _normalize(device) in t:
            for w in q_words:
                stem = w[:4]
                if stem in t:
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
    decoded_html = html.unescape(html_text.replace('\\/', '/'))
    pattern = r'\{[^\}]*?\"videoURL\"\s*:\s*\"(https://[^\"]+?)\"[^\}]*?\}'
    matches = re.finditer(pattern, decoded_html)
    
    brand_clean = product_brand.lower().strip()
    query_tokens = [w for w in search_query.lower().split() if len(w) > 3]
    
    unrelated_categories = [
        'sandwichera', 'freidora', 'tostadora', 'batidora', 'envasadora', 'horno', 'plancha', 'exprimidor',
        'cortacesped', 'cortacésped', 'cesped', 'césped', 'mower', 'lawn', 'jardin', 'jardín', 'desbrozadora',
        'motosierra', 'piscina', 'hidrolimpiadora', 'ventilador', 'calefactor', 'deshumidificador', 'zapato',
        'zapatilla', 'bota', 'sandalia', 'libro', 'novela', 'colchon', 'almohada'
    ]
    search_cats = [c for c in unrelated_categories if c in search_query.lower()]
    
    candidates = []
    for m in matches:
        obj_str = m.group(0)
        v_url = m.group(1)
        
        if 'closedCaptions' in v_url or 'al-eu-' in v_url or '/al-' in v_url:
            continue
            
        # Skip customer uploaded reviews which frequently feature wrong/unrelated products
        if any(cr in obj_lower for cr in ['customervideo', 'reviewvideo', 'customer video', 'reseña de cliente', 'opinión de cliente', 'opinion de cliente']):
            continue
            
        obj_lower = obj_str.lower()
        
        has_unrelated = False
        for c in unrelated_categories:
            if c not in search_cats and c in obj_lower:
                has_unrelated = True
                break
        if has_unrelated:
            continue
            
        score = 0
        if brand_clean and brand_clean in obj_lower:
            score += 10
        for tok in query_tokens:
            if tok in obj_lower:
                score += 3
        if 'default.jobtemplate.hls.m3u8' in v_url:
            score += 5
            
        candidates.append((score, v_url))
        
    candidates.sort(key=lambda x: x[0], reverse=True)
    if candidates and candidates[0][0] > 0:
        return candidates[0][1]
    return None

def process_asin(asin, session, headers, search_query):
    prod_url = f"https://www.amazon.es/dp/{asin}"
    try:
        p_resp = session.get(prod_url, headers=headers, timeout=10)
        if p_resp.status_code != 200:
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
            "product_url": prod_url
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

def scrape_amazon(query, canal_nombre, base_dir="/home/javierferb/ia-lab-files/videos/edicion_ia", limit=7):
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
        if len(qualified_raw) >= limit * 5:
            break
        search_url = f"https://www.amazon.es/s?k={requests.utils.quote(search_term)}&page={page}"
        response = session.get(search_url, headers=headers)
        
        if response.status_code != 200:
            continue

        bm_match = re.search(r'URL=\'([^\']+?)\'', response.text)
        if bm_match:
            redirect_url = 'https://www.amazon.es' + bm_match.group(1)
            response = session.get(redirect_url, headers=headers)

        page_asins = list(set(re.findall(r'B0[A-Z0-9]{8}', response.text)))
        new_asins = [a for a in page_asins if a not in seen_asins]
        if len(new_asins) < 2 and len(qualified_raw) < limit:
            new_asins = page_asins
            
        for a in new_asins:
            seen_asins.add(a)
                    
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_asin, asin, session, headers, query) for asin in new_asins]
            for f in as_completed(futures):
                res = f.result()
                if res:
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
        if p["video_url"]:
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
            "has_video": True,
            "video_file": v_filename,
            "image_file": i_filename,
            "product_url": p["product_url"]
        })
        
        used_asins.add(p["asin"])
        rank += 1

    save_channel_history(history_file, used_topics, used_asins)

    if not products:
        raise RuntimeError(f"El scraper no encontró productos válidos en Amazon para la búsqueda: '{query}'")

    result_data = {
        "query": query,
        "canal_nombre": canal_nombre,
        "project_dir": project_dir,
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
    
    args = parser.parse_args()
    
    res = scrape_amazon(args.query, args.canal, args.base_dir, args.limit)
    print(json.dumps(res, ensure_ascii=False))
