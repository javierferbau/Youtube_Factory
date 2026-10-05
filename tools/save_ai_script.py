def extract_json_object(raw_data) -> dict:
    if not raw_data:
        return None
    if isinstance(raw_data, dict):
        return raw_data
    text = str(raw_data).strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"(\{[\s\S]*\})", text)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    return None

#!/usr/bin/env python3
import sys
import os
import json
import re
import subprocess
import argparse
import urllib.request
import urllib.error

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen3.8:27b"

ENGLISH_REJECT_PATTERNS = [
    r"looking for the perfect gift",
    r"wireless headphones",
    r"noise cancellation",
    r"here are the top",
    r"welcome back to our channel",
    r"in this video we are going to",
    r"let's dive into"
]

def is_valid_spanish_script(script_obj: dict, expected_count: int = 7) -> bool:
    if not isinstance(script_obj, dict):
        return False
        
    hook = str(script_obj.get("hook", "")).strip()
    products = script_obj.get("products", [])
    outro = str(script_obj.get("outro", "")).strip()
    
    if len(hook.split()) < 40 or len(outro.split()) < 35:
        return False
        
    for pat in ENGLISH_REJECT_PATTERNS:
        if re.search(pat, hook, re.IGNORECASE) or re.search(pat, outro, re.IGNORECASE):
            return False
            
    if not isinstance(products, list) or len(products) != expected_count:
        return False
        
    for p in products:
        p_str = str(p).strip()
        if len(p_str.split()) < 60:
            return False
        for pat in ENGLISH_REJECT_PATTERNS:
            if re.search(pat, p_str, re.IGNORECASE):
                return False
                
    return True

def generate_script_with_ollama(data: dict, expected_count: int = 7) -> dict:
    query = data.get("query", "productos").strip()
    products = data.get("products", [])
    
    if not products:
        return None
        
    prod_blocks = []
    for p in products[:expected_count]:
        rank = p.get("rank", len(prod_blocks) + 1)
        title = p.get("title", f"Producto {rank}")
        price = p.get("price", "Consultar en Amazon")
        rating = p.get("rating", "4.5")
        rev_count = p.get("review_count", "")
        specs = p.get("specs", {})
        features = p.get("features", [])
        top_reviews = p.get("top_reviews", [])
        
        specs_str = ", ".join([f"{k}: {v}" for k, v in list(specs.items())[:4]]) if specs else "Construcción ergonómica y duradera"
        features_str = " | ".join(features[:2]) if features else "Alto rendimiento comprobado"
        
        rev_quotes = []
        if top_reviews:
            for r in top_reviews[:2]:
                txt = r.get("text", "") or r.get("title", "")
                if txt:
                    rev_quotes.append(txt[:100].strip())
        reviews_str = f"Opiniones reales de clientes: {' // '.join(rev_quotes)}" if rev_quotes else "Opiniones reales: Muy valorado por su fiabilidad"
        
        block = (
            f"PUESTO #{rank}: {title}\n"
            f"- Precio: {price} | Valoración: {rating} ({rev_count})\n"
            f"- Ficha técnica / Materiales: {specs_str}\n"
            f"- Puntos fuertes: {features_str}\n"
            f"- {reviews_str}"
        )
        prod_blocks.append(block)
        
    products_input = "\n\n".join(prod_blocks)
    
    system_prompt = (
        "Eres un guionista profesional en español de España para un canal líder de comparativas de YouTube sobre productos de Amazon.\n"
        "Tu objetivo es redactar un guion extenso, envolvente y con alta psicología de ventas (Loss Aversion, Social Proof y Present Bias).\n"
        "REGLAS CRÍTICAS:\n"
        "1. Idioma: 100% ESPAÑOL DE ESPAÑA. Queda TOTALMENTE PROHIBIDO el inglés o las plantillas genéricas.\n"
        "2. Formato: Devuelve ÚNICAMENTE un objeto JSON válido con las claves: 'hook', 'products', 'outro'.\n"
        f"3. La clave 'products' debe ser un array con exactamente {len(prod_blocks)} strings.\n"
        "4. CADA reseña de producto debe tener MÍNIMO 140 PALABRAS (extensa y detallada), integrando de forma natural los datos reales suministrados (especificaciones, materiales, precio y lo que destacan las opiniones reales).\n"
        "5. El 'hook' debe tener 80-100 palabras explicando el error común al comprar y por qué ver el top. El 'outro' debe tener 60-80 palabras recordando los enlaces de la descripción."
    )
    
    user_prompt = (
        f"Redacta el guion completo para el vídeo ranking de: \"{query}\".\n\n"
        f"Datos reales de los {len(prod_blocks)} productos que debes analizar:\n\n"
        f"{products_input}\n\n"
        "Recuerda: Devuelve solo el JSON válido con: hook, products (array de 7 strings de >140 palabras), outro."
    )
    
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.5,
            "num_predict": 4096
        }
    }
    
    try:
        req = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            content_str = res_data.get("message", {}).get("content", "")
            script_parsed = json.loads(content_str)
            if is_valid_spanish_script(script_parsed, expected_count=len(prod_blocks)):
                return script_parsed
    except Exception as e:
        print(f"[save_ai_script] Ollama local call error/fallback: {e}", file=sys.stderr)
        
    return None

def main():
    parser = argparse.ArgumentParser(description="Guarda el guion y los metadatos iniciales en data.json")
    parser.add_argument("target_path", help="Ruta al proyecto o a data.json")
    parser.add_argument("--affiliate_tag", default="", help="Tag de afiliado de Amazon")
    parser.add_argument("--script_json", default="", help="String JSON o ruta con el guion")
    args, unknown = parser.parse_known_args()

    target_path = args.target_path.strip()
    affiliate_tag = args.affiliate_tag.strip()
    script_arg = args.script_json.strip()
    
    if target_path.endswith(".json"):
        data_json_path = target_path
        project_dir = os.path.dirname(data_json_path)
    else:
        project_dir = target_path
        data_json_path = os.path.join(project_dir, "data.json")

    os.makedirs(project_dir, exist_ok=True)
    try:
        os.chmod(project_dir, 0o777)
    except Exception:
        pass

    data = {}
    if os.path.exists(data_json_path):
        try:
            with open(data_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    if affiliate_tag:
        data["affiliate_tag"] = affiliate_tag

    prods_count = len(data.get("products", [])) or 7

    # 1. Check if valid script provided via --script_json argument or stdin
    script_obj = None
    if script_arg:
        try:
            if os.path.exists(script_arg):
                with open(script_arg, "r", encoding="utf-8") as f:
                    script_obj = json.load(f)
            else:
                script_obj = extract_json_object(script_arg)
        except Exception:
            script_obj = None
    elif not sys.stdin.isatty():
        try:
            raw_stdin = sys.stdin.read().strip()
            if raw_stdin:
                script_obj = extract_json_object(raw_stdin)
        except Exception:
            script_obj = None

    # Check output wrapper if from n8n langchain
    if isinstance(script_obj, dict) and "output" in script_obj and isinstance(script_obj["output"], dict):
        script_obj = script_obj["output"]

    if script_obj and is_valid_spanish_script(script_obj, expected_count=prods_count):
        data["script"] = script_obj
    else:
        # Check existing script in data.json
        existing_script = data.get("script", {})
        if not is_valid_spanish_script(existing_script, expected_count=prods_count):
            # Try direct generation with Ollama local
            ollama_script = generate_script_with_ollama(data, expected_count=prods_count)
            if ollama_script:
                data["script"] = ollama_script
            else:
                data.pop("script", None)

    with open(data_json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    try:
        os.chmod(data_json_path, 0o666)
    except Exception:
        pass

    # Ensure 100% Spanish script with dynamic enrichment if needed
    venv_py = "/home/javierferb/n8n/venv/bin/python3"
    if not os.path.exists(venv_py):
        venv_py = sys.executable

    enricher_path = "/home/javierferb/n8n/tools/script_enricher.py"
    if os.path.exists(enricher_path):
        subprocess.run([venv_py, enricher_path, data_json_path])

if __name__ == "__main__":
    main()
