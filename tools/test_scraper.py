#!/usr/bin/env python3
from curl_cffi import requests
from bs4 import BeautifulSoup
import re

headers = {
    'accept-language': 'es-ES,es;q=0.9,en;q=0.8',
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

session = requests.Session(impersonate='chrome120')
res = session.get('https://www.amazon.es/s?k=freidora+de+aire', headers=headers)
asins = list(set(re.findall(r'data-asin="([A-Z0-9]{10})"', res.text)))
print('ASINs found:', len(asins), asins[:10])

valid_count = 0
for asin in asins:
    if valid_count >= 7:
        break
    prod_url = f'https://www.amazon.es/dp/{asin}'
    try:
        p_resp = session.get(prod_url, headers=headers, timeout=8)
        if p_resp.status_code == 200:
            soup = BeautifulSoup(p_resp.text, 'html.parser')
            title_el = soup.select_one('#productTitle') or soup.select_one('h1')
            title = title_el.text.strip() if title_el else f'Producto {asin}'
            
            rating_el = soup.select_one('.a-icon-alt')
            rating_str = rating_el.text.strip() if rating_el else '4.5'
            
            mp4_matches = re.findall(r'https://[^\s"\']*?\.mp4', p_resp.text)
            has_vid = bool(mp4_matches)
            
            print(f'ASIN: {asin} | Video: {has_vid} | Rating: {rating_str} | Title: {title[:40]}')
            if has_vid:
                valid_count += 1
    except Exception as e:
        print('Error:', e)

print('Total valid products with video:', valid_count)
