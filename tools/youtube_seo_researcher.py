#!/usr/bin/env python3
"""
youtube_seo_researcher.py
Investigación automatizada de keywords YouTube para optimización SEO.
Usa YouTube Autocomplete API (gratuito, sin API key) + clasificación de intención.
Sin dependencias externas — solo stdlib.
"""

import sys
import os
import json
import re
import time
import argparse
import urllib.request
import urllib.parse
from collections import Counter

SUGGEST_URL = "https://suggestqueries.google.com/complete/search"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

SPANISH_MODIFIERS = {
    "questions": ["cómo", "qué", "cuál", "por qué", "para qué", "cuánto cuesta"],
    "prepositions": ["para", "con", "sin", "en"],
    "commercial": ["mejor", "mejores", "vs", "comparativa", "opiniones", "precio", "barata", "calidad precio", "2026", "top", "ranking"],
    "troubleshooting": ["limpiar", "arreglar", "no calienta", "error", "primer uso", "trucos"],
}

INTENT_PATTERNS = {
    "Informational": re.compile(
        r"\b(c[oó]mo|qu[eé]|receta|recetas|tutorial|gu[ií]a|paso a paso|trucos|primer uso|funciona|hacer|preparar)\b", re.I
    ),
    "Commercial": re.compile(
        r"\b(mejor|mejores|top|vs|versus|comparativa|opiniones|review|an[aá]lisis|merece la pena|vale la pena|calidad precio|ranking)\b", re.I
    ),
    "Transactional": re.compile(
        r"\b(comprar|precio|barat[oa]s?|oferta|descuento|rebajas|costo|en amazon|mediamarkt|lidl|carrefour|d[oó]nde)\b", re.I
    ),
    "Troubleshooting": re.compile(
        r"\b(arreglar|reparar|no enciende|no calienta|error|problema|limpiar|humo|olor|desarmar)\b", re.I
    ),
}

def fetch_autocomplete(query, lang="es", country="ES"):
    params = urllib.parse.urlencode({
        "client": "firefox",
        "ds": "yt",
        "hl": lang,
        "gl": country,
        "q": query,
    })
    url = f"{SUGGEST_URL}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data[1] if len(data) > 1 else []
    except Exception:
        return []

def expand_keywords(seed, product_titles=None, lang="es", country="ES"):
    queries = [seed]

    for c in "abcdefghijklmnopqrstuvwxyz":
        queries.append(f"{seed} {c}")

    for group in SPANISH_MODIFIERS.values():
        for mod in group:
            queries.append(f"{seed} {mod}")
            queries.append(f"{mod} {seed}")

    if product_titles:
        for title in product_titles:
            words = [w for w in title.split() if len(w) > 2][:3]
            short_name = " ".join(words)
            queries.append(f"{short_name} opiniones")
            queries.append(f"{short_name} review")
            queries.append(f"{short_name} vs")

    all_keywords = set()
    for i, q in enumerate(queries):
        suggestions = fetch_autocomplete(q, lang, country)
        for s in suggestions:
            all_keywords.add(s.strip().lower())
        if (i + 1) % 15 == 0:
            time.sleep(0.5)

    return all_keywords

def classify_intent(keyword):
    for intent, pattern in INTENT_PATTERNS.items():
        if pattern.search(keyword):
            return intent
    return "General"

def score_keywords(keywords, seed):
    scored = []
    seed_lower = seed.lower()
    for kw in keywords:
        score = 0
        intent = classify_intent(kw)

        if seed_lower in kw:
            score += 3
        if intent == "Commercial":
            score += 2
        elif intent == "Transactional":
            score += 1

        word_count = len(kw.split())
        if 3 <= word_count <= 8:
            score += 1

        scored.append({"keyword": kw, "intent": intent, "score": score})

    scored.sort(key=lambda x: (-x["score"], x["keyword"]))
    return scored

def extract_top_tags(scored_keywords, seed, max_tags=15):
    tags = []
    seen_lower = set()

    tags.append(seed.lower())
    seen_lower.add(seed.lower())

    for item in scored_keywords:
        if len(tags) >= max_tags:
            break
        kw = item["keyword"]
        if kw not in seen_lower and item["intent"] in ("Commercial", "Transactional"):
            tags.append(kw)
            seen_lower.add(kw)

    for item in scored_keywords:
        if len(tags) >= max_tags:
            break
        kw = item["keyword"]
        if kw not in seen_lower:
            tags.append(kw)
            seen_lower.add(kw)

    return tags[:max_tags]

def summarize_intents(scored_keywords):
    intent_counts = Counter(item["intent"] for item in scored_keywords)
    total = len(scored_keywords)
    summary = {}
    for intent, count in intent_counts.most_common():
        summary[intent] = {
            "count": count,
            "percentage": round(count / total * 100, 1) if total > 0 else 0,
            "top_keywords": [
                item["keyword"]
                for item in scored_keywords
                if item["intent"] == intent
            ][:8],
        }
    return summary

def research(project_dir):
    data_json = os.path.join(project_dir, "data.json")
    if not os.path.exists(data_json):
        print(f"ERROR: data.json no encontrado en {project_dir}", file=sys.stderr)
        sys.exit(1)

    with open(data_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    query = data.get("query", "productos")
    products = data.get("products", [])
    product_titles = [p.get("title", "")[:60] for p in products if p.get("title")]

    all_keywords = expand_keywords(query, product_titles)
    scored = score_keywords(all_keywords, query)
    tags = extract_top_tags(scored, query)
    intent_summary = summarize_intents(scored)
    dominant_intent = max(intent_summary, key=lambda k: intent_summary[k]["count"]) if intent_summary else "General"

    result = {
        "query": query,
        "total_keywords_found": len(all_keywords),
        "dominant_intent": dominant_intent,
        "intent_summary": intent_summary,
        "tags": tags,
        "suggested_tags": tags,
        "top_keywords": [item["keyword"] for item in scored[:30]],
        "scored_keywords": scored[:50],
    }

    out_path = os.path.join(project_dir, "seo_keywords.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps(result, ensure_ascii=False))
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube SEO Keyword Researcher")
    parser.add_argument("--project_dir", required=True, help="Directorio del proyecto con data.json")
    args = parser.parse_args()
    research(args.project_dir)
