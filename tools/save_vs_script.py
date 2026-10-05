#!/usr/bin/env python3
"""
save_vs_script.py
Guarda el guion y los metadatos iniciales para el formato VS en data.json y ejecuta vs_script_enricher.py.
Preserva rigurosamente product_a, product_b y query provenientes del scraper.
"""
import sys, os, json, subprocess, argparse, re

def parse_ai_json(text):
    if not text:
        return {}
    if isinstance(text, dict):
        return text
    s = str(text).strip()
    s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.MULTILINE)
    s = re.sub(r"\s*```$", "", s, flags=re.MULTILINE)
    s = s.strip()
    try:
        res = json.loads(s)
        if isinstance(res, dict):
            return res.get("output", res)
    except Exception:
        pass
    m = re.search(r"(\{[\s\S]*\})", s)
    if m:
        try:
            res = json.loads(m.group(1))
            if isinstance(res, dict):
                return res.get("output", res)
        except Exception:
            pass
    return {}

def main():
    parser = argparse.ArgumentParser(description="Guarda el guion VS y llama a vs_script_enricher.py")
    parser.add_argument("target_path", help="Ruta al proyecto o a data.json")
    parser.add_argument("--affiliate_tag", default="", help="Tag de afiliado de Amazon")
    parser.add_argument("--script_json", default="", help="JSON string con el guion")
    args, unknown = parser.parse_known_args()

    target_path = args.target_path.strip()
    affiliate_tag = args.affiliate_tag.strip()
    script_json = args.script_json.strip()
    
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
    data["format"] = "vs"

    payload_stdin = {}
    if not sys.stdin.isatty():
        try:
            stdin_text = sys.stdin.read().strip()
            if stdin_text:
                parsed_stdin = parse_ai_json(stdin_text)
                if isinstance(parsed_stdin, dict):
                    payload_stdin = parsed_stdin
        except Exception:
            pass

    # Merge scraper fields from stdin if present
    for k in ["product_a", "product_b", "query", "project_dir", "canal_nombre"]:
        if k in payload_stdin and payload_stdin[k]:
            data[k] = payload_stdin[k]

    # Extract script
    script_obj = None
    if script_json:
        script_obj = parse_ai_json(script_json)
    elif "script" in payload_stdin and isinstance(payload_stdin["script"], dict):
        script_obj = payload_stdin["script"]
    elif "hook" in payload_stdin or "product_a_overview" in payload_stdin:
        script_obj = payload_stdin

    if isinstance(script_obj, dict) and script_obj:
        data["script"] = script_obj

    with open(data_json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    try:
        os.chmod(data_json_path, 0o666)
    except Exception:
        pass

    venv_py = "/home/javierferb/n8n/venv/bin/python3"
    if not os.path.exists(venv_py):
        venv_py = sys.executable

    subprocess.run([
        venv_py,
        "/home/javierferb/n8n/tools/vs_script_enricher.py",
        data_json_path
    ])

if __name__ == "__main__":
    main()
