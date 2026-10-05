#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""
generate_youtube_tags.py — Standalone High-Intent YouTube Tag Generator Module.
Executed right before YouTube video upload in n8n workflow.

Reads project_dir/data.json and project_dir/youtube_metadata.json.
Generates rich, high-relevance, unique & non-repetitive YouTube tags (< 30 chars each).
Maximizes character utilization (up to 485 bytes / ~500 chars) for maximum SEO & transactional reach.
Updates youtube_metadata.json with 'tags' list and 'tags_str' comma-separated string.
Outputs JSON to stdout for downstream n8n nodes.
"""
import sys
import os
import json
import re

def generate_tags_for_project(project_dir):
    data_file = os.path.join(project_dir, "data.json")
    meta_file = os.path.join(project_dir, "youtube_metadata.json")
    meta_txt = os.path.join(project_dir, "youtube_metadata.txt")

    data_obj = {}
    if os.path.exists(data_file):
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                data_obj = json.load(f)
        except Exception:
            pass

    meta_obj = {}
    if os.path.exists(meta_file):
        try:
            with open(meta_file, 'r', encoding='utf-8') as f:
                meta_obj = json.load(f)
        except Exception:
            pass

    query = data_obj.get("query", "")
    if not query and project_dir:
        query = os.path.basename(os.path.normpath(project_dir)).replace("_", " ")

    query_clean = query.lower().strip()

    # Extract product list from standard or VS format
    products = data_obj.get("products", [])
    if not products:
        if "product_a" in data_obj:
            products.append(data_obj["product_a"])
        if "product_b" in data_obj:
            products.append(data_obj["product_b"])

    candidate_tags = []

    # 1. Exact query cleanly cut at word boundary (max 30 chars)
    if query_clean:
        if len(query_clean) <= 30:
            candidate_tags.append(query_clean)
        else:
            cut_q = query_clean[:30].rsplit(" ", 1)[0]
            if cut_q:
                candidate_tags.append(cut_q)

    # 2. Extract brand names & VS comparison combinations
    brand_a = ""
    brand_b = ""
    if len(products) >= 1:
        brand_a = products[0].get("brand", "").lower().strip()
    if len(products) >= 2:
        brand_b = products[1].get("brand", "").lower().strip()

    if brand_a and brand_b and brand_a != brand_b:
        candidate_tags.append(f"{brand_a} vs {brand_b}")
        candidate_tags.append(f"{brand_a} o {brand_b}")
        candidate_tags.append(brand_a)
        candidate_tags.append(brand_b)
    elif brand_a:
        candidate_tags.append(brand_a)

    CONNECTORS = {'de', 'del', 'para', 'con', 'en', 'por', 'y', 'la', 'el', 'las', 'los', 'un', 'una', 'a', 'sobre', 'al', 'o', 'e'}
    DISCARD_WORDS = {
        'anterior', 'siguiente', 'diapositivas', 'conjunto', 'patrocinados', 'relacionados', 
        'página', 'genérico', 'generic', 'v', 'w', 'cm', 'mm', 'oz', '220v', '140w', '220w', 
        '400w', '1000w', 'tradu', 'corrigida', 'atualizada', 'curiosidades'
    }

    # 3. Extract key model phrases from product titles
    for p in products:
        p_title = p.get("title", "")
        clean_t = re.sub(r'[^a-zA-Z0-9\sñáéíóúü]', ' ', p_title).strip().lower()
        words = [w for w in clean_t.split() if w not in DISCARD_WORDS and not w.isdigit() and len(w) > 1]
        
        if len(words) >= 2:
            phrase = ' '.join(words[:4]).strip()
            while phrase.split() and phrase.split()[-1] in CONNECTORS:
                phrase = ' '.join(phrase.split()[:-1])
            if len(phrase) >= 5 and len(phrase) <= 30 and phrase not in candidate_tags:
                candidate_tags.append(phrase)

    # 4. High-Intent Transactional Modifiers & Niche Combinations
    query_short = query_clean
    if len(query_short) > 25:
        cut_q = query_clean[:25].rsplit(" ", 1)[0]
        words_q = cut_q.split()
        if words_q and words_q[-1] in CONNECTORS:
            words_q.pop()
        cut_q = " ".join(words_q)
        if len(cut_q) >= 5:
            query_short = cut_q

    candidate_tags.extend([
        f"mejores {query_short}",
        f"{query_short} calidad precio",
        f"{query_short} 2026",
        f"{query_short} opiniones",
        "precio minimo historico",
        "ganga amazon",
        "oferta flash amazon",
        "cual es mejor 2026",
        "merece la pena 2026",
        "cual comprar 2026",
        "comparativa 2026",
        "resena y opinion",
        "merece la pena",
        "guia de compra",
        "ofertas amazon",
        "amazon espana"
    ])

    if brand_a:
        candidate_tags.append(f"{brand_a} opiniones")
    if brand_b:
        candidate_tags.append(f"{brand_b} opiniones")

    channel_name = data_obj.get("channel_name", "")
    if "/" in channel_name:
        channel_name = channel_name.split("/")[0]
    channel_name_clean = channel_name.replace("_", " ").strip().lower()
    if channel_name_clean:
        candidate_tags.append(channel_name_clean[:30])

    # 5. Core category words
    stop_words = {
        "para", "con", "del", "las", "los", "por", "que", "una", "uno", "set",
        "pack", "mini", "sin", "sobre", "entre", "mano", "kit", "varillas",
        "acero", "inoxidable", "electrica", "electricas", "de", "en", "el", "la", "y"
    }
    q_words = [w.lower() for w in re.sub(r'[^a-zA-Z0-9\sñáéíóúü]', ' ', query).split() if len(w) >= 3 and w.lower() not in stop_words]
    for qw in q_words:
        if len(qw) >= 3 and qw not in candidate_tags:
            candidate_tags.append(qw)

    # Sanitization & Byte-Limit Enforcement (YouTube Max 500 chars / 485 bytes strict limit)
    def clean_tag(t_str):
        text = str(t_str).lower().strip()
        text = re.sub(r'[áàäâ]', 'a', text)
        text = re.sub(r'[éèëê]', 'e', text)
        text = re.sub(r'[íìïî]', 'i', text)
        text = re.sub(r'[óòöô]', 'o', text)
        text = re.sub(r'[úùüû]', 'u', text)
        text = re.sub(r'[ñ]', 'n', text)
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        words = text.split()
        while words and words[-1] in CONNECTORS:
            words.pop()
        return " ".join(words)

    # Detectar nicho para tags estacionales cruzados
    niche = data_obj.get("canal_niche") or data_obj.get("niche") or data_obj.get("channel_niche") or ""
    if not niche and project_dir:
        p_low = project_dir.lower()
        for n in ["cocina", "limpieza", "calzado", "zapateria", "libreria", "barberia", "taller"]:
            if n in p_low:
                niche = "calzado" if n == "zapateria" else n
                break

    try:
        from campaign_manager import get_active_campaign, get_niche_campaign_tags
        _camp = get_active_campaign()
        if _camp:
            c_tags = get_niche_campaign_tags(_camp, niche=niche)
            if c_tags:
                candidate_tags = c_tags + candidate_tags
            elif _camp.get("extra_tags"):
                candidate_tags = _camp["extra_tags"] + candidate_tags
    except Exception:
        pass

    unique_tags = []
    total_bytes = 0
    MAX_BYTES = 475  # Límite seguro YouTube es 500 chars / 485 bytes

    for t in candidate_tags:
        clean_t = clean_tag(t)
        if len(clean_t) > 30:
            clean_t = clean_t[:30].rsplit(" ", 1)[0]
        if clean_t and clean_t not in unique_tags and len(clean_t) >= 3 and len(clean_t) <= 30:
            tag_quote_overhead = 2 if ' ' in clean_t else 0
            tag_bytes = len(clean_t.encode('utf-8')) + tag_quote_overhead
            added_bytes = tag_bytes + (1 if unique_tags else 0)
            if total_bytes + added_bytes <= MAX_BYTES:
                unique_tags.append(clean_t)
                total_bytes += added_bytes

    tags_str = ",".join(unique_tags)

    # 6. Update youtube_metadata.json
    meta_obj["tags"] = unique_tags
    meta_obj["tags_str"] = tags_str
    meta_obj["suggested_tags"] = unique_tags

    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump(meta_obj, f, indent=2, ensure_ascii=False)

    # Update txt file if present
    if os.path.exists(meta_txt):
        try:
            with open(meta_txt, 'r', encoding='utf-8') as f:
                txt_content = f.read()
            if "TAGS:" in txt_content:
                txt_content = txt_content.split("TAGS:")[0] + f"TAGS:\n{tags_str}\n"
            else:
                txt_content += f"\n\nTAGS:\n{tags_str}\n"
            with open(meta_txt, 'w', encoding='utf-8') as f:
                f.write(txt_content)
        except Exception:
            pass

    res = {
        "tags": unique_tags,
        "tags_str": tags_str,
        "total_tags_bytes": total_bytes,
        "total_tags_count": len(unique_tags)
    }
    return res

if __name__ == "__main__":
    target_dir = ""
    if len(sys.argv) > 1 and sys.argv[1].strip() and sys.argv[1].strip() != ".":
        candidate = sys.argv[1].strip()
        if os.path.isdir(candidate):
            target_dir = candidate

    if not target_dir and os.path.exists("/tmp/current_project_dir.txt"):
        try:
            with open("/tmp/current_project_dir.txt", "r", encoding="utf-8") as f:
                cand = f.read().strip()
                if os.path.isdir(cand):
                    target_dir = cand
        except Exception:
            pass

    if not target_dir or not os.path.isdir(target_dir):
        target_dir = "."

    output = generate_tags_for_project(target_dir)
    print(json.dumps(output, ensure_ascii=False))
