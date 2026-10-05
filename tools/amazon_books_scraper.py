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

# Strict Book & Kindle Scraper for Amazon Spanish Market ("Librería Del Pueblo")

BOOK_ACCESSORY_REJECT_KEYWORDS = [
    'funda', 'fundas', 'protector', 'carcasa', 'cargador', 'soporte', 
    'cristal', 'cable', 'bateria', 'batería', 'estuche', 'bolso', 
    'luz para kindle', 'luz de lectura', 'atril', 'pegatina', 'pegatinas',
    'correa', 'adaptador', 'hub', 'skin', 'skins', 'e-reader', 'ereader',
    'passaporte', 'marcapaginas', 'marcapáginas', 'bolígrafo', 'marcador',
    'perro', 'perros', 'gato', 'gatos', 'mascota', 'mascotas', 'alimento',
    'pienso', 'comida', 'suplemento', 'champú', 'limpiador', 'pocketbook',
    'kobo', 'tolino', 'onyx boox', 'nook', 'e-ink', 'eink', 'leche',
    'probiótico', 'probiotico', 'prebiótico', 'prebiotico', 'proteína',
    'proteina', 'vainilla', 'sticks', 'puleva', 'ensure', 'nutrivigor',
    'cápsula', 'capsula', 'comprimido', 'pastilla', 'jarabe', 'complemento',
    'medibiotix', 'gasteel', 'vitamina', 'batido', 'ashwagandha', 'extracto',
    'magnesio', 'creatina', 'omega', 'colágeno', 'colageno', 'formato xxl',
    'camiseta', 'camisetas', 'sudadera', 'sudaderas', 'ropa', 't-shirt', 'tshirt',
    'disfraz', 'disfraces', 'merchandising', 'taza', 'tazas', 'figura', 'figuras',
    'funkopop', 'funko', 'poster', 'póster', 'mochila', 'mochilas', 'gorra', 'gorras',
    'calcetines', 'pijama', 'pijamas', 'juguete', 'juguetes', 'peluche', 'peluches',
    'llavero', 'llaveros', 'cuadro', 'lienzo', 'parche', 'cojín', 'cojin', 'manta',
    'toalla', 'alfombra', 'agenda', 'calendario', 'puzzle', 'puzle', 'juego de mesa',
    'baraja', 'cartas', 'videojuego', 'consola', 'merch', 'botella', 'botellas',
    'cantimplora', 'termo', 'termos', 'vaso', 'vasos', 'water bottle', 'bottle', 'insulated',
    'sierra', 'caladora', 'taladro', 'lijadora', 'atornillador', 'amoladora', 'martillo', 'herramienta', 'herramientas', 'bricolaje', 'bosch', 'dewalt', 'makita', 'einhell', 'black+decker', 'ferreteria', 'ferretería', 'maletin', 'maletín', 'caja de herramientas', 'destornillador', 'aspiradora', 'freidora', 'cafetera', 'batidora', 'microondas', 'lavavajillas', 'electrodomestico', 'electrodoméstico'
]

GENERIC_STOPWORDS = {
    'de', 'del', 'para', 'con', 'en', 'los', 'las', 'un', 'una', 'y', 'el', 'la', 
    'por', 'a', 'top', 'mejores', '2026', '2025', '2024', 'mejores', 'mejor', 'guia',
    'novela', 'novelas', 'libro', 'libros', 'mas', 'más', 'vendidos', 'vendidas'
}

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

def is_actual_book(title):
    t = title.lower()
    for acc in BOOK_ACCESSORY_REJECT_KEYWORDS:
        if acc in t:
            return False
    # Hardware specs check (e-readers)
    if re.search(r'\b(8gb|16gb|32gb|64gb|usb-c|wi-fi|wifi|e-ink|eink|pocketbook|kobo|tolino|onyx boox)\b', t):
        return False
    # Consumables / Supplements / Grocery specs check
    if re.search(r'(\bpack\b|\d+g\b|\d+kg\b|\d+ml\b|\d+l\b|sticks|comprimidos|cápsulas|capsulas|dosis)', t):
        return False
    if any(lang in t for lang in ['portuguese edition', 'tradução', 'edição', 'edicao', 'versao original']):
        return False
    return True

def clean_book_title(title):
    # Remove clutter tags from title for clean YouTube presentation
    t = title.strip()
    t = re.sub(r'\s*\([^)]*Spanish Edition[^)]*\)', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s*\[Edición Kindle\]', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s*\[Kindle Edition\]', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s*:?\s*Edición Kindle', '', t, flags=re.IGNORECASE)
    return t.strip()

def get_normalized_book_signature(title):
    t = title.lower()
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    ignore_words = [
        'libro', 'libros', 'novela', 'novelas', 'edicion', 'version', 'kindle', 
        'tapa', 'dura', 'blanda', 'ebook', 'papel', 'spanish', 'edition', 'serie', 'volumen'
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

def process_book_asin(asin, session, headers, search_query):
    prod_url = f"https://www.amazon.es/dp/{asin}"
    try:
        p_resp = safe_get(session, prod_url, headers=headers, timeout=12)
        if not p_resp or p_resp.status_code != 200:
            return None
            
        soup = BeautifulSoup(p_resp.text, 'html.parser')
        
        title_el = soup.select_one('#productTitle') or soup.select_one('h1')
        raw_title = title_el.text.strip() if title_el else f"Libro {asin}"
        
        # Check Amazon category breadcrumbs & reject non-book categories (Salud, Alimentación, Belleza)
        breadcrumbs_el = soup.select_one('#wayfinding-breadcrumbs_feature_div') or soup.select_one('.a-breadcrumb') or soup.select_one('#wayfinding-breadcrumbs_container')
        if breadcrumbs_el:
            bc_txt = breadcrumbs_el.text.lower()
            if any(cat in bc_txt for cat in ['bricolaje', 'herramientas', 'ferretería', 'ferreteria', 'industria', 'jardín', 'jardin', 'salud y cuidado', 'alimentación', 'alimentacion', 'belleza', 'hogar', 'deportes', 'supermercado', 'droguería', 'ropa', 'moda', 'juguetes', 'videojuegos', 'electrónica', 'electronica', 'merchandising', 'textil', 'marroquinería']):
                return None

        if not is_actual_book(raw_title):
            return None

        title = clean_book_title(raw_title)

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
            soup.select_one('#ebooksImgBlkFront') or 
            soup.select_one('#imgBlkFront') or 
            soup.select_one('#landingImage') or 
            soup.select_one('img.s-image') or 
            soup.select_one('#litb-canvas-img-result') or 
            soup.select_one('#main-image')
        )
        img_url = None
        if img_el:
            if img_el.get('data-old-hires'):
                img_url = img_el.get('data-old-hires')
            elif img_el.get('src'):
                img_url = img_url = img_el.get('src')
            elif img_el.get('data-a-dynamic-image'):
                try:
                    dyn_dict = json.loads(img_el.get('data-a-dynamic-image'))
                    if isinstance(dyn_dict, dict) and dyn_dict:
                        img_url = list(dyn_dict.keys())[0]
                except Exception:
                    pass
        
        # Check for book video or create HD cover fallback
        product_video_url = None
        clean_text = html.unescape(p_resp.text.replace('\\/', '/'))
        all_stream_urls = re.findall(r'https://[a-zA-Z0-9\.\-\_\/]+?\.(?:mp4|m3u8)', clean_text)
        for url in all_stream_urls:
            if ('vse-vms' in url or 'vse-' in url) and 'closedCaptions' not in url:
                product_video_url = url
                break

        if not product_video_url and not img_url:
            return None
            
        is_kindle = 'kindle' in raw_title.lower() or 'ebook' in raw_title.lower() or 'digital' in raw_title.lower()
        
        return {
            "asin": asin,
            "title": title,
            "raw_title": raw_title,
            "price": price,
            "rating_raw": rating_raw,
            "rating_num": rating_num,
            "is_kindle": is_kindle,
            "video_url": product_video_url,
            "img_url": img_url,
            "product_url": prod_url
        }
    except Exception:
        return None

def scrape_amazon_books(query, canal_nombre, base_dir="/home/javierferb/ia-lab-files/videos/edicion_ia", limit=7):
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

    # Clean query to core keywords (remove stopwords like 'libros', 'de', 'y', 'para')
    words = [w for w in re.sub(r'[^a-zA-Z0-9\sñáéíóúü]', ' ', query).split() if len(w) >= 3 and w.lower() not in GENERIC_STOPWORDS]
    search_term = ' '.join(words) if words else query

    # Search both Kindle store (i=digital-text) and Books store (i=stripbooks)
    search_indices = ['digital-text', 'stripbooks']
    
    for idx in search_indices:
        if len(qualified_raw) >= limit * 5:
            break
        for page in range(1, 8):
            if len(qualified_raw) >= limit * 5:
                break
            search_url = f"https://www.amazon.es/s?k={requests.utils.quote(search_term)}&i={idx}&page={page}"
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
                futures = [executor.submit(process_book_asin, asin, session, headers, query) for asin in new_asins]
                for f in as_completed(futures):
                    res = f.result()
                    if res:
                        qualified_raw.append(res)

    if len(qualified_raw) < limit:
        ev_asins = ["B085G3G2CY", "B0062XBS32", "B09S3YXPRZ", "B078XH916T", "B007HPS120", "8497992018"]
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(process_book_asin, asin, session, headers, query) for asin in ev_asins]
            for f in as_completed(futures):
                res = f.result()
                if res and res not in qualified_raw:
                    qualified_raw.append(res)

    # Sort Kindle versions first
    def book_priority_sort(b):
        score = 0
        if b["is_kindle"]:
            score += 50
        if b["rating_num"] >= 4.5:
            score += 20
        return score

    qualified_raw.sort(key=book_priority_sort, reverse=True)

    selected_raw = []
    seen_signatures = []

    for p in qualified_raw:
        title = p["title"]
        sig = get_normalized_book_signature(title)

        is_similar = False
        for s in seen_signatures:
            overlap = sig.intersection(s)
            if len(sig) > 0 and (len(overlap) / len(sig)) >= 0.5:
                is_similar = True
                break

        if is_similar:
            continue

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

        if not v_filename and p["img_url"]:
            v_path = os.path.join(prod_dir, f"product_{rank}.mp4")
            success = create_video_from_image(p["img_url"], session, v_path)
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
            "is_kindle": p["is_kindle"],
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
    parser = argparse.ArgumentParser(description="Dedicated Amazon Books & Kindle Scraper")
    parser.add_argument("--query", required=True, help="Palabra clave de búsqueda de libros")
    parser.add_argument("--canal", required=True, help="Nombre de la carpeta del canal")
    parser.add_argument("--base_dir", default="/home/javierferb/ia-lab-files/videos/edicion_ia", help="Ruta base del almacenamiento")
    parser.add_argument("--limit", type=int, default=7, help="Número de libros")
    
    args = parser.parse_args()
    
    res = scrape_amazon_books(args.query, args.canal, args.base_dir, args.limit)
    print(json.dumps(res, ensure_ascii=False))
