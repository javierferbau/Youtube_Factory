#!/usr/bin/env python3
from curl_cffi import requests
import re

headers = {
    "accept-language": "es-ES,es;q=0.9,en;q=0.8",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
s = requests.Session(impersonate="chrome120")

for asin in ["B0FNYCH1VL", "B0BFB3Q7SD", "B0GC69WYZ3", "B0FDKTQ17D", "B0DGLFBT67"]:
    r = s.get(f"https://www.amazon.es/dp/{asin}", headers=headers)
    all_mp4s = re.findall(r'https://[^"\'\s\\]+?\.mp4', r.text)
    video_mp4s = [u for u in all_mp4s if 'closedCaptions' not in u and ('al-eu' in u or 'vse' in u or 'images/S' in u)]
    print(f"ASIN: {asin} -> Video MP4s count: {len(video_mp4s)}")
    if video_mp4s:
        print("  Real MP4:", video_mp4s[0])
