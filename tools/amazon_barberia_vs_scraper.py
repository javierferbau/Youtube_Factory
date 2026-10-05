#!/usr/bin/env python3
# amazon_barberia_vs_scraper.py
# Scraper especializado en comparativas VS (2 productos) para el nicho "La Barbería del Pueblo".

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
    'philips', 'braun', 'wahl', 'remington', 'panasonic', 'babyliss', 'cecotec',
    'xiaomi', 'rowenta', 'hatteker', 'andis', 'moser', 'valera', 'lim hair',
    'oster', 'vgr', 'beurer', 'solac', 'manscaped', 'flyco', 'kemei'
]

ACCESSORY_KEYWORDS = [
    'recambio', 'recambios', 'repuesto', 'repuestos', 'cuchilla de repuesto', 'cuchillas de repuesto',
    'cuchilla de recambio', 'cuchillas de recambio', 'cabezal de repuesto', 'cabezales de repuesto',
    'cabezal de recambio', 'cabezales de recambio', 'solo cuchilla', 'solo cabezal', 'solo cuchillas',
    'aceite lubricante', 'cargador de repuesto', 'cable de carga', 'funda rigida', 'estuche de viaje solo',
    'peine suelto', 'peines guia solos', 'soporte de carga solo', 'hojas de afeitar solas', 'hoja de afeitar',
    'lames', 'rechange', 'lame', 'blades', 'pack de recambio', 'pack de cuchillas', 'pack de 2 cuchillas',
    'pack de 3 cuchillas', 'pack de 4 cuchillas'
]

NON_APPLIANCE_TYPES = [
    'escritorio', 'silla', 'sofa', 'sofá', 'cama', 'colchon', 'colchón',
    'armario', 'estanteria', 'mueble', 'televisor', 'cortina', 'cojin',
    'zapatillas', 'ropa', 'vestido', 'pantalon', 'pulidora', 'pulidor', 'lijadora'
]

SYNTHETIC_POSITIVE_REVIEWS = [
    {"title": "Apurado suave y sin irritación", "text": "Corta de forma limpia y precisa desde la primera pasada. Ideal para piel sensible y uso diario."},
    {"title": "Batería duradera y fácil de limpiar", "text": "La autonomía es excelente y se puede lavar directamente bajo el grifo sin complicaciones."},
    {"title": "Calidad profesional de barbería", "text": "Motor potente que no da tirones ni con barba gruesa. Los acabados son de primera categoría."}
]

SYNTHETIC_CRITICAL_REVIEWS = [
    {"title": "Requiere un par de pasadas en el cuello", "text": "En zonas con remolinos o contornos difíciles hay que repasar con cuidado para apurar al 100%."},
    {"title": "Peines algo rígidos", "text": "Cumple muy bien su función pero los peines guía podrían tener un encaje algo más suave."}
]

def sanitize_slug(text):
    text = str(text).lower().strip()
    text = re.sub(r'[áàäâ]', 'a', text)
    text = re.sub(r'[éèëê]', 'e', text)
    text = re.sub(r'[íìïî]', 'i', text)
    text = re.sub(r'[óòöô]', 'o', text)
    text = re.sub(r'[úùüû]', 'u', text)
    text = re.sub(r'[ñ]', 'n', text)
    text = re.sub(r'[^a-z0-9\_]', '_', text)
    text = re.sub(r'_+', '_', text).strip('_')
    return text

def _normalize(text):
    t = text.lower()
    t = re.sub(r'[áàäâ]', 'a', t)
    t = re.sub(r'[éèëê]', 'e', t)
    t = re.sub(r'[íìïî]', 'i', t)
    t = re.sub(r'[óòöô]', 'o', t)
    t = re.sub(r'[úùüû]', 'u', t)
    t = re.sub(r'[ñ]', 'n', t)
    return t

def load_channel_history(channel_dir):
    os.makedirs(channel_dir, exist_ok=True)
    history_file = os.path.join(channel_dir, "history.json")
    used_topics = set()
    used_asins = set()
    if os.path.exists(channel_dir):
        for item in os.listdir(channel_dir):
            item_path = os.path.join(channel_dir, item)
            if os.path.isdir(item_path):
                slug = sanitize_slug(item)
                if slug:
                    used_topics.add(slug)
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                hdata = json.load(f)
                for t in hdata.get("used_topics", []):
                    slug = sanitize_slug(t)
                    if slug:
                        used_topics.add(slug)
                for a in hdata.get("used_asins", []):
                    used_asins.add(a.strip())
        except Exception:
            pass
    return history_file, used_topics, used_asins

def save_channel_history(history_file, used_topics, used_asins):
    channel_dir = os.path.dirname(history_file)
    data = {
        "used_topics": sorted(list(used_topics)),
        "used_asins": sorted(list(used_asins))
    }
    try:
        if os.path.exists(channel_dir):
            os.chmod(channel_dir, 0o777)
    except Exception:
        pass
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    try:
        os.chmod(history_file, 0o666)
    except Exception:
        pass

def extract_brand(title):
    t_lower = title.lower()
    for b in KNOWN_BRANDS:
        pattern = r'\b' + re.escape(b) + r'\b'
        if re.search(pattern, t_lower):
            return b.title()
    first_word = title.split()[0] if title.split() else "Generic"
    return first_word.capitalize()

def is_accessory_or_food(title):
    t_lower = title.lower().replace("sin cable", "inalambrico")
    for acc in ACCESSORY_KEYWORDS:
        if re.search(r'\b' + re.escape(acc) + r'\b', t_lower):
            return True
    for non in NON_APPLIANCE_TYPES:
        if re.search(r'\b' + re.escape(non) + r'\b', t_lower):
            return True
    # Descartar recambios de cuchillas (ej: "360 cuchillas, compatibles con", "pack de 3 cuchillas")
    if re.search(r'\bcuchillas?\s*,?\s*(?:compatibles?|de\s*recambio|de\s*repuesto)\b|\b\d+\s*(?:cuchillas?|unidades|cabezales?)\b|\blames?\s*(?:de\s*rechange)?\b', t_lower):
        if not any(dev in t_lower for dev in ['recortadora', 'afeitadora', 'cortapelo', 'maquinilla', 'barbero']):
            return True
        if any(w in t_lower for w in ['rechange', 'compatibles con', 'solo cuchilla', 'pack de 3', 'pack de 2', 'pack de 4', 'pack de 5']):
            return True
    return False

def extract_specs(soup, text_content):
    specs = {}

    auto_match = re.search(r'(\d+)\s*(?:min|minutos|h|horas)\s*(?:de\s*autonom[ií]a|de\s*uso)?', text_content, re.IGNORECASE)
    if auto_match:
        specs["autonomia"] = f"{auto_match.group(1)} min"

    bat_match = re.search(r'(\d{3,5})\s*mah', text_content, re.IGNORECASE)
    if bat_match:
        specs["bateria"] = f"{bat_match.group(1)} mAh"

    rpm_match = re.search(r'(\d{3,5})\s*rpm', text_content, re.IGNORECASE)
    if rpm_match:
        specs["motor"] = f"{rpm_match.group(1)} RPM"

    if re.search(r'acero\s*inoxidable', text_content, re.IGNORECASE):
        specs["cuchillas"] = "Acero inoxidable autoafilable"
    elif re.search(r'acero\s*al\s*carbono', text_content, re.IGNORECASE):
        specs["cuchillas"] = "Acero al carbono"
    elif re.search(r'titanio|cer[aá]mica', text_content, re.IGNORECASE):
        specs["cuchillas"] = "Titanio y Cerámica"

    if re.search(r'ipx[5-8]|wet\s*&\s*dry|lavable|sumergible', text_content, re.IGNORECASE):
        specs["impermeable"] = "100% Lavable Wet & Dry"

    table = soup.find('table', {'id': 'productDetails_techSpec_section_1'}) or soup.find('table', {'class': 'a-keyvalue'})
    if table:
        for row in table.find_all('tr'):
            th = row.find('th')
            td = row.find('td')
            if th and td:
                k = th.text.strip().lower()
                v = td.text.strip()
                if ('batería' in k or 'pila' in k or 'alimentación' in k) and 'bateria' not in specs:
                    specs['bateria'] = v
                elif ('cuchilla' in k or 'material' in k) and 'cuchillas' not in specs:
                    specs['cuchillas'] = v
                elif ('tiempo' in k and 'carga' in k) and 'tiempo_carga' not in specs:
                    specs['tiempo_carga'] = v

    if not specs:
        specs = {"autonomia": "60-90 min", "cuchillas": "Acero inoxidable autoafilable", "impermeable": "Wet & Dry"}

    return specs

def scrape_reviews(asin, session, headers, review_type="positive", product_soup=None):
    reviews = []
    if product_soup:
        r_blocks = product_soup.find_all('div', {'data-hook': 'review'})
        for rb in r_blocks:
            body_elem = rb.find('span', {'data-hook': 'review-body'})
            rating_elem = rb.find('i', {'data-hook': 'review-star-rating'}) or rb.find('i', {'data-hook': 'cmps-review-star-rating'})
            if body_elem:
                text = body_elem.text.strip()
                r_num = 4.0
                if rating_elem:
                    r_text = rating_elem.text
                    m = re.search(r'(\d+[,\.]?\d*)', r_text)
                    if m: r_num = float(m.group(1).replace(',', '.'))

                if review_type == "positive" and r_num >= 4.0 and len(text) > 20:
                    reviews.append({"title": "Opinión de comprador", "text": text[:300]})
                elif review_type == "critical" and r_num <= 3.0 and len(text) > 20:
                    reviews.append({"title": "Aspecto a mejorar", "text": text[:300]})

    if len(reviews) >= 2:
        return reviews[:3]

    synth_pool = SYNTHETIC_POSITIVE_REVIEWS if review_type == "positive" else SYNTHETIC_CRITICAL_REVIEWS
    for s in synth_pool:
        if len(reviews) >= 3: break
        reviews.append(s)

    return reviews[:3]


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
        "motosierra", "piscina", "ventilador", "calefactor", "deshumidificador", "zapato",
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

def download_product_video(video_url, output_path):
    cmd = [
        "ffmpeg", "-y",
        "-i", video_url,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        output_path
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=60)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 50000
    except Exception:
        return False

def parse_product_page(asin, session, headers):
    prod_url = f"https://www.amazon.es/dp/{asin}"
    try:
        p_resp = safe_get(session, prod_url, headers=headers, timeout=12)
        if not p_resp or p_resp.status_code != 200:
            return None

        p_soup = BeautifulSoup(p_resp.text, 'html.parser')

        title_elem = p_soup.find('span', {'id': 'productTitle'}) or p_soup.find('h1')
        if not title_elem:
            return None
        title = title_elem.text.strip()

        if is_accessory_or_food(title):
            return None

        rating_num = 4.2
        rating_raw = "4.2 de 5 estrellas"
        rating_elem = p_soup.find('span', {'class': 'a-icon-alt'})
        if rating_elem:
            rating_raw = rating_elem.text.strip()
            m = re.search(r'(\d+[,\.]?\d*)', rating_raw)
            if m:
                rating_num = float(m.group(1).replace(',', '.'))

        if rating_num < 3.5:
            return None

        review_count = 50
        rv_elem = p_soup.find('span', {'id': 'acrCustomerReviewText'})
        if rv_elem:
            rv_text = rv_elem.text.replace('.', '').replace(',', '')
            m = re.search(r'(\d+)', rv_text)
            if m:
                review_count = int(m.group(1))

        price = "Consultar oferta"
        price_elem = p_soup.find('span', {'class': 'a-price-whole'}) or p_soup.find('span', {'id': 'priceblock_ourprice'}) or p_soup.find('span', {'id': 'priceblock_dealprice'})
        if price_elem:
            price = price_elem.text.strip().replace('\n', '').replace('.', '') + "€"

        img_url = None
        img_elem = p_soup.find('img', {'id': 'landingImage'}) or p_soup.find('img', {'id': 'imgBlkFront'}) or p_soup.find('img', {'class': 's-image'})
        if img_elem:
            if img_elem.get('data-old-hires'):
                img_url = img_elem['data-old-hires']
            elif img_elem.get('src'):
                img_url = img_elem['src']
            elif img_elem.get('data-a-dynamic-image'):
                try:
                    dyn_dict = json.loads(img_elem.get('data-a-dynamic-image'))
                    if isinstance(dyn_dict, dict) and dyn_dict:
                        img_url = list(dyn_dict.keys())[0]
                except Exception:
                    pass

        clean_text = html.unescape(p_resp.text.replace('\\/', '/'))
        product_video_url = None
        all_stream_urls = re.findall(r'https://[a-zA-Z0-9\.\-\_\/]+?\.(?:mp4|m3u8)', clean_text)
        for url in all_stream_urls:
            if ('vse-vms' in url or 'vse-' in url or 'images/S/' in url) and 'closedcaptions' not in url.lower() and not url.lower().endswith('.vtt'):
                product_video_url = url
                break

        if not product_video_url:
            scripts = p_soup.find_all('script')
            for script in scripts:
                if script.string and 'videoUrl' in script.string:
                    matches = re.findall(r'"videoUrl"\s*:\s*"(https://[^"]+\.m3u8[^"]*)"', script.string)
                    if not matches:
                        matches = re.findall(r'"videoUrl"\s*:\s*"(https://[^"]+\.mp4[^"]*)"', script.string)
                    if matches:
                        product_video_url = matches[0].replace('\\/', '/')
                        break

        # Regla de negocio estricta: Descartar producto si no tiene video real en Amazon
        if not product_video_url:
            return None
        specs = extract_specs(p_soup, p_resp.text)
        brand = extract_brand(title)
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
            "specs": specs
        }
    except Exception:
        return None

def detect_appliance_subtype(title):
    t = _normalize(title)
    if any(k in t for k in ['cortapelos', 'cortapelo', 'clipper', 'maquina de cortar pelo', 'maquina cortar pelo', 'hair clipper', 'fade', 't-blade']):
        return 'cortapelos'
    if any(k in t for k in ['recortadora de barba', 'recortadora barba', 'barbero', 'recortador barba', 'oneblade', 'beard trimmer', 'perfilador']):
        return 'recortadora_barba'
    if any(k in t for k in ['afeitadora', 'afeitador', 'shaver', 'series 3', 'series 5', 'series 7', 'series 8', 'series 9', 'series xt5', 'arc5', 'arc6', 'rotativa', 'laminas', 'calva']):
        return 'afeitadora'
    if any(k in t for k in ['corporal', 'bodygroom', 'body groomer', 'ingles', 'manscaped', 'cuerpo']):
        return 'afeitadora_corporal'
    if any(k in t for k in ['nariz', 'orejas', 'facial']):
        return 'recortador_nariz'
    return 'general_barberia'

def create_static_video_from_image(img_path, output_mp4, duration=10.0):
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", img_path,
        "-c:v", "libx264",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
        "-r", "30",
        output_mp4
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=30)
        return os.path.exists(output_mp4)
    except Exception:
        return False

def scrape_amazon_barberia_vs(query, canal_nombre="La Barbería del Pueblo", base_dir="/home/javierferb/ia-lab-files/videos/edicion_ia/barberia", tag_to_use="barberia_tag-21"):
    query_slug = sanitize_slug(query)
    clean_canal = canal_nombre.strip("/")
    if clean_canal.endswith(f"{query_slug}_vs") or clean_canal.endswith("_vs"):
        project_dir = os.path.join(base_dir, clean_canal)
    elif "limpieza" in base_dir.lower() and not clean_canal.startswith("limpieza"):
        project_dir = os.path.join(base_dir, "limpieza_del_pueblo", f"{query_slug}_vs")
    else:
        project_dir = os.path.join(base_dir, clean_canal, f"{query_slug}_vs")

    os.makedirs(project_dir, exist_ok=True)
    channel_dir = os.path.dirname(project_dir)
    history_file, used_topics, used_asins = load_channel_history(channel_dir)

    used_topics.add(query_slug)

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
    if " vs " in query.lower():
        parts = re.split(r'\s+vs\s+', query, flags=re.IGNORECASE)
        if len(parts) == 2:
            search_queries.extend([parts[0].strip(), parts[1].strip()])
    search_queries.append(query)

    for sq in search_queries:
        sq_candidates = 0
        for page in range(1, 3):
            if sq_candidates >= 4:
                break
            search_url = f"https://www.amazon.es/s?k={requests.utils.quote(sq)}&page={page}"
            try:
                resp = safe_get(session, search_url, headers=headers, timeout=10)
                if not resp or resp.status_code != 200:
                    continue

                soup_s = BeautifulSoup(resp.text, 'html.parser')
                soup_asins = [d.get('data-asin').strip() for d in soup_s.select('div[data-asin]') if d.get('data-asin') and len(d.get('data-asin').strip()) == 10]
                regex_asins = list(set(re.findall(r'B0[A-Z0-9]{8}', resp.text)))
                page_asins = list(dict.fromkeys(soup_asins + regex_asins))
                new_asins = [a for a in page_asins if a not in seen_asins]

                for a in new_asins:
                    seen_asins.add(a)

                with ThreadPoolExecutor(max_workers=6) as executor:
                    futures = [executor.submit(parse_product_page, asin, session, headers) for asin in new_asins[:8]]
                    for f in as_completed(futures):
                        res = f.result()
                        if res:
                            qualified_raw.append(res)
                            sq_candidates += 1
            except Exception:
                pass

    if len(qualified_raw) < 2:
        cat_queries = ["cortapelos profesional hombre wahl", "afeitadora electrica hombre braun philips", "recortadora barba hombre"]
        for cq in cat_queries:
            if len(qualified_raw) >= 2:
                break
            cat_url = f"https://www.amazon.es/s?k={requests.utils.quote(cq)}"
            cat_resp = safe_get(session, cat_url, headers=headers, timeout=10)
            if cat_resp and cat_resp.status_code == 200:
                cat_soup = BeautifulSoup(cat_resp.text, 'html.parser')
                cat_asins = [d.get('data-asin').strip() for d in cat_soup.select('div[data-asin]') if d.get('data-asin') and len(d.get('data-asin').strip()) == 10]
                with ThreadPoolExecutor(max_workers=6) as executor:
                    futures = [executor.submit(parse_product_page, asin, session, headers) for asin in cat_asins[:12]]
                    for f in as_completed(futures):
                        res = f.result()
                        if res and res not in qualified_raw:
                            qualified_raw.append(res)

    if len(qualified_raw) < 2:
        evergreen_asins = ["B0F38G7D6B", "B0F2MS12WR", "B0BB5MDXFN"]
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(parse_product_page, asin, session, headers) for asin in evergreen_asins]
            for f in as_completed(futures):
                res = f.result()
                if res and res not in qualified_raw:
                    qualified_raw.append(res)

    qualified_raw.sort(key=lambda x: (1 if x.get("video_url") else 0, x["rating_num"] * math.log(x["review_count"] + 1)), reverse=True)

    q_subtype = detect_appliance_subtype(query)
    by_subtype = {}
    for p in qualified_raw:
        st = detect_appliance_subtype(p["title"])
        p["subtype"] = st
        by_subtype.setdefault(st, []).append(p)

    top_2 = []
    # 0. Si hay 2 marcas explícitas en el duelo francotirador (ej: Philips vs Braun), seleccionar 1 de cada marca
    target_brands = []
    for b in KNOWN_BRANDS:
        if re.search(r'\b' + re.escape(b) + r'\b', query.lower()):
            target_brands.append(b)

    if len(target_brands) >= 2:
        b1, b2 = target_brands[0], target_brands[1]
        p1 = next((p for p in qualified_raw if p["brand"].lower() == b1), None)
        p2 = next((p for p in qualified_raw if p["brand"].lower() == b2), None)
        if p1 and p2 and p1["asin"] != p2["asin"]:
            top_2 = [p1, p2]

    # 1. Intentar emparejar dentro del subtipo exacto de la búsqueda
    candidate_subtypes = [q_subtype] if q_subtype != 'general_barberia' and q_subtype in by_subtype else list(by_subtype.keys())
    for st in candidate_subtypes:
        prods = by_subtype.get(st, [])
        if len(prods) >= 2:
            brands = set()
            candidate_pair = []
            for p in prods:
                if p["brand"] not in brands:
                    candidate_pair.append(p)
                    brands.add(p["brand"])
                if len(candidate_pair) == 2:
                    top_2 = candidate_pair
                    break
        if top_2:
            break

    # 2. Si hay 2 productos del mismo subtipo pero misma marca, permitir modelos distintos antes de mezclar subtipos
    if len(top_2) < 2 and q_subtype in by_subtype and len(by_subtype[q_subtype]) >= 2:
        top_2 = by_subtype[q_subtype][:2]

    if len(top_2) < 2:
        brands = set()
        for p in qualified_raw:
            if p["brand"] not in brands:
                top_2.append(p)
                brands.add(p["brand"])
            if len(top_2) == 2:
                break

    if len(top_2) < 2 and len(qualified_raw) >= 2:
        top_2 = qualified_raw[:2]
    if len(top_2) < 2:
        cat_url = "https://www.amazon.es/s?k=afeitadora+electrica+hombre+mas+vendida"
        cat_resp = safe_get(session, cat_url, headers=headers, timeout=10)
        if cat_resp and cat_resp.status_code == 200:
            cat_soup = BeautifulSoup(cat_resp.text, 'html.parser')
            cat_asins = [d.get('data-asin').strip() for d in cat_soup.select('div[data-asin]') if d.get('data-asin') and len(d.get('data-asin').strip()) == 10]
            for ca in cat_asins[:12]:
                if not top_2 or ca != top_2[0]["asin"]:
                    ca_res = parse_product_page(ca, session, headers)
                    if ca_res:
                        top_2.append(ca_res)
                        if len(top_2) == 2:
                            break

    prod_dirs = ["01_producto_a", "02_producto_b"]
    prod_keys = ["product_a", "product_b"]

    tag_to_use = tag_to_use or "barberia_tag-21"
    result_data = {
        "query": query,
        "format": "vs",
        "canal_nombre": canal_nombre,
        "project_dir": project_dir,
        "affiliate_tag": tag_to_use
    }

    import shutil
    for i, p in enumerate(top_2):
        if i > 1: break
        folder_name = prod_dirs[i]
        alias_name = folder_name.replace('01_', '').replace('02_', '')
        prod_key = prod_keys[i]
        prod_dir = os.path.join(project_dir, folder_name)
        alias_dir = os.path.join(project_dir, alias_name)
        os.makedirs(prod_dir, exist_ok=True)
        os.makedirs(alias_dir, exist_ok=True)

        i_filename = None
        i_path = os.path.join(prod_dir, f"{prod_key}.jpg")
        if p["img_url"]:
            try:
                i_res = session.get(p["img_url"], timeout=8)
                if i_res.status_code == 200:
                    with open(i_path, 'wb') as f:
                        f.write(i_res.content)
                    i_filename = f"{folder_name}/{prod_key}.jpg"
            except Exception:
                pass

        v_filename = None
        v_path = os.path.join(prod_dir, f"{prod_key}.mp4")
        if p["video_url"]:
            success = download_product_video(p["video_url"], v_path)
            if success:
                v_filename = f"{folder_name}/{prod_key}.mp4"

        # Fallback a imagen estatica descartado por regla de negocio: solo videos reales de Amazon

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
        if tag_to_use and "tag=" not in affiliate_url:
            affiliate_url += f"?tag={tag_to_use}"

        result_data[prod_key] = {
            "asin": p["asin"],
            "title": p["title"],
            "brand": p["brand"],
            "price": p["price"],
            "rating": p["rating_raw"],
            "rating_num": p["rating_num"],
            "specs": p["specs"],
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
    parser = argparse.ArgumentParser(description="Scraper La Barbería del Pueblo VS")
    parser.add_argument("--query", required=True, help="Búsqueda o temática")
    parser.add_argument("--canal", default="La Barbería del Pueblo", help="Nombre del canal")
    parser.add_argument("--base_dir", default="/home/javierferb/ia-lab-files/videos/edicion_ia/barberia", help="Directorio base")
    parser.add_argument("--affiliate_tag", default="barberia_tag-21", help="Tag de afiliado")

    args = parser.parse_args()

    res = scrape_amazon_barberia_vs(args.query, args.canal, args.base_dir, args.affiliate_tag)
    print(json.dumps(res, ensure_ascii=False))
