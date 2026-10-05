#!/usr/bin/env python3
# amazon_libreria_scraper.py
# Scraper especializado en comparativas VS (2 libros) para "Librería Del Pueblo".

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

BOOK_ACCESSORY_KEYWORDS = [
    'funda', 'fundas', 'protector', 'carcasa', 'cargador', 'soporte',
    'cristal', 'cable', 'bateria', 'batería', 'estuche', 'bolso',
    'luz para kindle', 'luz de lectura', 'atril', 'pegatina', 'pegatinas',
    'marcapaginas', 'marcapáginas', 'bolígrafo', 'marcador', 'e-reader', 'ereader',
    'meta quest', 'vr', 'gafas', 'auriculares', 'consola', 'videojuego', 'pantalla',
    'teclado', 'raton', 'tarjeta', 'disco duro', 'memoria', 'altavoz', 'camara',
    'camiseta', 'camisetas', 'sudadera', 'sudaderas', 'ropa', 't-shirt', 'tshirt',
    'disfraz', 'disfraces', 'merchandising', 'taza', 'tazas', 'figura', 'figuras',
    'funkopop', 'funko', 'poster', 'póster', 'mochila', 'mochilas', 'gorra', 'gorras',
    'calcetines', 'pijama', 'pijamas', 'juguete', 'juguetes', 'peluche', 'peluches',
    'llavero', 'llaveros', 'cuadro', 'lienzo', 'parche', 'cojín', 'cojin', 'manta',
    'botella', 'botellas', 'cantimplora', 'termo', 'termos', 'vaso', 'vasos', 'water bottle', 'bottle', 'insulated',
    'sierra', 'caladora', 'taladro', 'lijadora', 'atornillador', 'amoladora', 'martillo', 'herramienta', 'herramientas', 'bricolaje', 'bosch', 'dewalt', 'makita', 'einhell', 'black+decker', 'ferreteria', 'ferretería', 'maletin', 'maletín', 'caja de herramientas', 'destornillador', 'aspiradora', 'freidora', 'cafetera', 'batidora', 'microondas', 'lavavajillas', 'electrodomestico', 'electrodoméstico'
]

SYNTHETIC_POSITIVE_REVIEWS = [
    {"title": "Lectura transformadora y práctica", "text": "Un libro indispensable que cambia la forma de abordar los hábitos y las finanzas. Explicaciones claras y lecciones aplicables desde la primera página."},
    {"title": "Muy recomendado e inspirador", "text": "Escrito con un lenguaje fluido, directo y profundo. Aporta reflexiones de alto impacto para el crecimiento personal y profesional."},
    {"title": "Una obra maestra de su género", "text": "Excelente estructuración de conceptos. Combina investigación, ejemplos reales y estrategias completamente accionables."}
]

SYNTHETIC_CRITICAL_REVIEWS = [
    {"title": "Requiere lectura pausada", "text": "El contenido es denso en algunos capítulos y requiere tomar notas y reflexionar para asimilar todas sus enseñanzas."},
    {"title": "Edición física con tipografía algo reducida", "text": "Aunque el contenido es brillante, el tamaño de letra en la edición impresa puede resultar algo ajustado para lecturas prolongadas."}
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

def clean_book_title(title):
    t = title.strip()
    t = re.sub(r'\s*\([^)]*Spanish Edition[^)]*\)', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s*\[Edición Kindle\]', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s*\[Kindle Edition\]', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s*:?\s*Edición Kindle', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s*:?\s*Tapa dura', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s*:?\s*Tapa blanda', '', t, flags=re.IGNORECASE)
    return t.strip()

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

def is_accessory(title):
    t_lower = title.lower()
    for acc in BOOK_ACCESSORY_KEYWORDS:
        if re.search(r'\b' + re.escape(acc) + r'\b', t_lower):
            return True
    if re.search(r'\b(\d+gb|\d+\s*gb|ram|wifi|bluetooth|pantalla|batería|mah|realidad virtual|meta quest|headset|consola|videojuego|procesador)\b', t_lower):
        return True
    return False

def get_book_signature(title):
    t = title.lower()
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    ignore_words = {'libro', 'libros', 'novela', 'novelas', 'edicion', 'version', 'kindle', 'tapa', 'dura', 'blanda', 'ebook', 'papel', 'spanish', 'edition', 'pack', 'gb', '128gb', '256gb', '64gb', '32gb', '128', '256', '64', '32'}
    tokens = set([w for w in t.split() if len(w) > 2 and w not in ignore_words])
    return tokens

def extract_author_or_publisher(soup, title):
    byline = soup.select_one('#bylineInfo') or soup.select_one('.author') or soup.select_one('.contributorNameID')
    if byline:
        author_link = byline.select_one('a.a-link-normal')
        if author_link:
            txt = author_link.text.strip()
        else:
            txt = byline.text.strip()
        
        txt = re.sub(r'[\r\n\t]+', ' ', txt)
        txt = re.sub(r'\s*\([^)]*\)', '', txt).strip()
        txt = re.sub(r'^(de|por|autor:?)\s*', '', txt, flags=re.IGNORECASE).strip()
        txt = re.sub(r'\s*formato:.*$', '', txt, flags=re.IGNORECASE).strip()
        txt = re.sub(r'\s*edición:.*$', '', txt, flags=re.IGNORECASE).strip()
        txt = re.sub(r'\s+', ' ', txt).strip()
        if txt and len(txt) < 40 and not any(kw in txt.lower() for kw in ['tapa', 'kindle', 'audible', 'formato', 'versión', 'edición']):
            return txt
    m = re.search(r'de\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)', title)
    if m:
        return m.group(1).strip()
    return "Librería Del Pueblo"

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
                    m = re.search(r'(\d+[,\.]?\d*)', rating_elem.text)
                    if m: r_num = float(m.group(1).replace(',', '.'))
                if review_type == "positive" and r_num >= 4.0 and len(text) > 20:
                    reviews.append({"title": "Opinión de lector", "text": text[:300]})
                elif review_type == "critical" and r_num <= 3.0 and len(text) > 20:
                    reviews.append({"title": "Aspecto a considerar", "text": text[:300]})

    if len(reviews) >= 2:
        return reviews[:3]

    synth_pool = SYNTHETIC_POSITIVE_REVIEWS if review_type == "positive" else SYNTHETIC_CRITICAL_REVIEWS
    for s in synth_pool:
        if len(reviews) >= 3: break
        reviews.append(s)

    return reviews[:3]

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

def parse_book_page(asin, session, headers):
    prod_url = f"https://www.amazon.es/dp/{asin}"
    try:
        p_resp = session.get(prod_url, headers=headers, timeout=12)
        if p_resp.status_code != 200:
            return None
        bm_match = re.search(r"URL='([^']+?)'", p_resp.text)
        if bm_match:
            redirect_url = 'https://www.amazon.es' + html.unescape(bm_match.group(1))
            p_resp = session.get(redirect_url, headers=headers, timeout=12)

        p_soup = BeautifulSoup(p_resp.text, 'html.parser')

        title_elem = p_soup.find('span', {'id': 'productTitle'}) or p_soup.find('h1')
        if not title_elem:
            return None
        raw_title = title_elem.text.strip()
        if is_accessory(raw_title):
            return None

        # Check Amazon category breadcrumbs & reject non-book categories
        breadcrumbs_el = p_soup.select_one('#wayfinding-breadcrumbs_feature_div') or p_soup.select_one('.a-breadcrumb') or p_soup.select_one('#wayfinding-breadcrumbs_container')
        if breadcrumbs_el:
            bc_txt = breadcrumbs_el.text.lower()
            if any(cat in bc_txt for cat in ['salud y cuidado', 'alimentación', 'alimentacion', 'belleza', 'hogar', 'deportes', 'supermercado', 'electrónica', 'electronica', 'informática', 'informatica', 'videojuegos']):
                return None

        title = clean_book_title(raw_title)

        rating_num = 4.5
        rating_raw = "4.5 de 5 estrellas"
        rating_elem = p_soup.find('span', {'class': 'a-icon-alt'})
        if rating_elem:
            rating_raw = rating_elem.text.strip()
            m = re.search(r'(\d+[,\.]?\d*)', rating_raw)
            if m:
                rating_num = float(m.group(1).replace(',', '.'))

        if rating_num < 3.8:
            return None

        review_count = 100
        rv_elem = p_soup.find('span', {'id': 'acrCustomerReviewText'})
        if rv_elem:
            rv_text = rv_elem.text.replace('.', '').replace(',', '')
            m = re.search(r'(\d+)', rv_text)
            if m:
                review_count = int(m.group(1))

        price = "Consultar precio"
        price_elem = (
            p_soup.select_one('#kindle-price') or
            p_soup.select_one('.a-price .a-offscreen') or
            p_soup.select_one('#priceblock_ourprice') or
            p_soup.select_one('.apexPriceToPay .a-offscreen') or
            p_soup.find('span', {'class': 'a-price-whole'})
        )
        if price_elem:
            raw_p = price_elem.text.strip().replace('\n', '').replace('.', '')
            if raw_p:
                if not raw_p.endswith('€'):
                    price = raw_p + "€"
                else:
                    price = raw_p

        img_url = None
        img_elem = (
            p_soup.find('img', {'id': 'ebooksImgBlkFront'}) or
            p_soup.find('img', {'id': 'imgBlkFront'}) or
            p_soup.find('img', {'id': 'landingImage'}) or
            p_soup.find('img', {'class': 's-image'})
        )
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

        author = extract_author_or_publisher(p_soup, raw_title)

        synopsis = ""
        descr_el = p_soup.select_one('#bookDescription_feature_div') or p_soup.select_one('#productDescription')
        if descr_el:
            synopsis = descr_el.text.strip()[:400]

        return {
            "asin": asin,
            "title": title,
            "brand": author,
            "price": price,
            "rating_raw": rating_raw,
            "rating_num": rating_num,
            "review_count": review_count,
            "synopsis": synopsis,
            "img_url": img_url,
            "video_url": None,
            "product_url": prod_url,
            "html": p_resp.text,
            "specs": {
                "autor": author,
                "idioma": "Español",
                "formato": "Tapa blanda / Kindle"
            }
        }
    except Exception:
        return None

def scrape_amazon_libreria(query, canal_nombre="Librería Del Pueblo", base_dir="/home/javierferb/ia-lab-files/videos/edicion_ia/libreria_del_pueblo", tag_to_use="libreria_tag-21"):
    query_slug = sanitize_slug(query)
    clean_canal = canal_nombre.strip("/")

    if clean_canal.endswith(f"{query_slug}_vs") or clean_canal.endswith("_vs"):
        project_dir = os.path.join(base_dir, clean_canal)
    elif "libreria_del_pueblo" in base_dir.lower():
        project_dir = os.path.join(base_dir, f"{query_slug}_vs")
    else:
        project_dir = os.path.join(base_dir, "libreria_del_pueblo", f"{query_slug}_vs")

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

    def _get_page_asins(session, url, headers):
        try:
            resp = session.get(url, headers=headers, timeout=12)
            if resp.status_code != 200:
                return []
            bm_match = re.search(r"URL='([^']+?)'", resp.text)
            if bm_match:
                redirect_url = 'https://www.amazon.es' + html.unescape(bm_match.group(1))
                resp = session.get(redirect_url, headers=headers, timeout=12)
            soup = BeautifulSoup(resp.text, 'html.parser')
            dom_asins = [div.get('data-asin').strip() for div in soup.select('div[data-asin]') if div.get('data-asin') and len(div.get('data-asin').strip()) == 10]
            seen_set = set()
            page_asins = [a for a in dom_asins if not (a in seen_set or seen_set.add(a))]
            if not page_asins:
                raw_asins = list(set(re.findall(r'[B0-9][A-Z0-9]{9}', resp.text)))
                page_asins = raw_asins[:25]
            return page_asins
        except Exception:
            return []

    search_indices = ['stripbooks', 'digital-text']
    for idx in search_indices:
        if len(qualified_raw) >= 8:
            break
        for page in range(1, 4):
            if len(qualified_raw) >= 8:
                break
            search_url = f"https://www.amazon.es/s?k={requests.utils.quote(query)}&i={idx}&page={page}"
            page_asins = _get_page_asins(session, search_url, headers)
            if not page_asins:
                continue

            new_asins = [a for a in page_asins if a not in seen_asins]
            if len(new_asins) < 2 and len(qualified_raw) < 2:
                new_asins = page_asins

            for a in new_asins:
                seen_asins.add(a)

            with ThreadPoolExecutor(max_workers=6) as executor:
                futures = [executor.submit(parse_book_page, asin, session, headers) for asin in new_asins]
                for f in as_completed(futures):
                    res = f.result()
                    if res:
                        qualified_raw.append(res)

    if len(qualified_raw) < 2:
        fb_query = f"{query} mas vendidos"
        fb_url = f"https://www.amazon.es/s?k={requests.utils.quote(fb_query)}&i=stripbooks"
        try:
            fb_resp = session.get(fb_url, headers=headers, timeout=10)
            fb_asins = list(set(re.findall(r'B0[A-Z0-9]{8}', fb_resp.text)))
            with ThreadPoolExecutor(max_workers=6) as executor:
                futures = [executor.submit(parse_book_page, asin, session, headers) for asin in fb_asins[:8]]
                for f in as_completed(futures):
                    res = f.result()
                    if res and res not in qualified_raw:
                        qualified_raw.append(res)
        except Exception:
            pass

    if len(qualified_raw) < 2:
        # Fallback secundario a los libros más vendidos generales de la temática/librería
        fb_query_2 = "libros de desarrollo personal y finanzas mas vendidos"
        fb_url_2 = f"https://www.amazon.es/s?k={requests.utils.quote(fb_query_2)}&i=stripbooks"
        try:
            fb_resp_2 = session.get(fb_url_2, headers=headers, timeout=10)
            fb_asins_2 = list(set(re.findall(r'B0[A-Z0-9]{8}', fb_resp_2.text)))
            with ThreadPoolExecutor(max_workers=6) as executor:
                futures = [executor.submit(parse_book_page, asin, session, headers) for asin in fb_asins_2[:8]]
                for f in as_completed(futures):
                    res = f.result()
                    if res and res not in qualified_raw:
                        qualified_raw.append(res)
        except Exception:
            pass

    if len(qualified_raw) < 2:
        evergreen_asins = ["B085G3G2CY", "B0062XBS32", "B09S3YXPRZ", "B078XH916T", "B007HPS120"]
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(parse_book_page, asin, session, headers) for asin in evergreen_asins]
            for f in as_completed(futures):
                res = f.result()
                if res and res not in qualified_raw:
                    qualified_raw.append(res)

    if len(qualified_raw) < 2:
        raise RuntimeError(f"El scraper de librería no encontró libros suficientes para: '{query}'")

    qualified_raw.sort(key=lambda x: (x["rating_num"] * math.log(x["review_count"] + 1)), reverse=True)

    top_2 = []
    if qualified_raw:
        top_2.append(qualified_raw[0])
        sig_a = get_book_signature(qualified_raw[0]["title"])
        for p in qualified_raw[1:]:
            sig_b = get_book_signature(p["title"])
            overlap = sig_a.intersection(sig_b)
            max_len = max(len(sig_a), len(sig_b), 1)
            if (len(overlap) / max_len) < 0.4:
                top_2.append(p)
                break

    if len(top_2) < 2 and len(qualified_raw) >= 2:
        top_2 = qualified_raw[:2]
    if len(top_2) < 2:
        for ev in ["B085G3G2CY", "B0062XBS32", "B09S3YXPRZ", "B078XH916T", "B007HPS120"]:
            if not top_2 or ev != top_2[0]["asin"]:
                ev_res = parse_book_page(ev, session, headers)
                if ev_res:
                    top_2.append(ev_res)
                    if len(top_2) == 2:
                        break

    prod_dirs = ["01_producto_a", "02_producto_b"]
    prod_keys = ["product_a", "product_b"]

    tag_to_use = tag_to_use or "libreria_tag-21"
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
        alias_name = folder_name.replace("01_", "").replace("02_", "")
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
        if os.path.exists(i_path):
            created_v = create_static_video_from_image(i_path, v_path, duration=10.0)
            if created_v:
                v_filename = f"{folder_name}/{prod_key}.mp4"

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
    parser = argparse.ArgumentParser(description="Scraper Librería Del Pueblo VS")
    parser.add_argument("--query", required=True, help="Búsqueda o temática")
    parser.add_argument("--canal", default="Librería Del Pueblo", help="Nombre del canal")
    parser.add_argument("--base_dir", default="/home/javierferb/ia-lab-files/videos/edicion_ia/libreria_del_pueblo", help="Directorio base")
    parser.add_argument("--affiliate_tag", default="libreria_tag-21", help="Tag de afiliado")

    args = parser.parse_args()

    res = scrape_amazon_libreria(args.query, args.canal, args.base_dir, args.affiliate_tag)
    print(json.dumps(res, ensure_ascii=False))
