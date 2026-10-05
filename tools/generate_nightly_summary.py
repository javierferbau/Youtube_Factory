#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""
generate_nightly_summary.py
Genera un resumen consolidado y estructurado por NICHOS de las ejecuciones de n8n entre las 22:00 del día anterior y las 08:00 AM del día actual.
Agrupa por Nicho/Canal, muestra estado (Success/Failed) y títulos publicados en YouTube con iconos.
"""

import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, time, timedelta, timezone

N8N_URL = "http://localhost:5678/api/v1"
def get_n8n_api_key():
    import os
    key = os.getenv("N8N_API_KEY")
    if key:
        return key
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith('N8N_API_KEY='):
                    return line.strip().split('=', 1)[1].strip(' "\'')
    return ""

API_KEY = get_n8n_api_key()
MADRID_TZ = timezone(timedelta(hours=2))

def _api_get(endpoint):
    url = f"{N8N_URL}{endpoint}"
    headers = {"X-N8N-API-KEY": API_KEY}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"API Error fetching {endpoint}: {e}", file=sys.stderr)
        return None

def extract_yt_titles(ex_data):
    titles = []
    run_data = ex_data.get("data", {}).get("resultData", {}).get("runData", {})
    
    # Direct check on upload node sources
    for node_name, node_runs in run_data.items():
        is_yt_upload = any(k in node_name.lower() for k in ['upload youtube', 'upload a video', 'upload short', 'subir youtube'])
        if not is_yt_upload:
            continue
        for run in node_runs:
            for src in run.get('source', []):
                prev_node = src.get('previousNode')
                if prev_node and prev_node in run_data:
                    for prev_run in run_data[prev_node]:
                        prev_out = prev_run.get('data', {}).get('main', [[]])
                        for item in prev_out[0] if prev_out else []:
                            j = item.get('json', {})
                            if 'title' in j and j['title']:
                                titles.append(j['title'])
                            elif 'youtube_title' in j and j['youtube_title']:
                                titles.append(j['youtube_title'])
                            elif 'stdout' in j and 'youtube_title' in str(j['stdout']):
                                try:
                                    m_json = json.loads(j['stdout'])
                                    if 'youtube_title' in m_json:
                                        titles.append(m_json['youtube_title'])
                                except Exception:
                                    pass

    # Fallback check on metadata/parser nodes
    if not titles:
        for node_name, node_runs in run_data.items():
            if any(k in node_name.lower() for k in ['yt parsear', 'metadatos', 'bot response', 'optimizador seo']):
                for run in node_runs:
                    main_out = run.get('data', {}).get('main', [[]])
                    for item in main_out[0] if main_out else []:
                        j = item.get('json', {})
                        if 'title' in j and j['title']:
                            titles.append(j['title'])
                        elif 'youtube_title' in j and j['youtube_title']:
                            titles.append(j['youtube_title'])
                        elif 'stdout' in j and 'youtube_title' in str(j['stdout']):
                            try:
                                m_json = json.loads(j['stdout'])
                                if 'youtube_title' in m_json:
                                    titles.append(m_json['youtube_title'])
                            except Exception:
                                pass

    clean_titles = []
    for t in titles:
        if t and t not in clean_titles:
            clean_titles.append(t)
    return clean_titles

def get_workflow_info_map():
    wf_res = _api_get("/workflows")
    wf_info = {}
    if wf_res and "data" in wf_res:
        for w in wf_res["data"]:
            w_id = w["id"]
            w_name = w["name"]
            niche = "🤖 OTROS WORKFLOWS"
            w_lower = w_name.lower()
            
            if "cocina" in w_lower:
                niche = "🍳 COCINA TECNOLÓGICA"
            elif "limpieza" in w_lower:
                niche = "🧹 LIMPIEZA DEL PUEBLO"
            elif "librería" in w_lower or "libreria" in w_lower:
                niche = "📚 LIBRERÍA DEL PUEBLO"
            elif "calzado" in w_lower or "zapateria" in w_lower or "zapatería" in w_lower:
                niche = "👟 CALZADO DEL PUEBLO"
            elif "draco" in w_lower or "nass" in w_lower or "multicámara" in w_lower or "multicamara" in w_lower:
                niche = "🐶 CANAL DRACO / MASCOTAS"
            
            if niche == "🤖 OTROS WORKFLOWS":
                w_details = _api_get(f"/workflows/{w_id}")
                if w_details:
                    for node in w_details.get("nodes", []):
                        if node.get("name") in ["Configuración Parámetros", "Configuración Parámetros1"]:
                            for v in node.get("parameters", {}).get("values", {}).get("string", []):
                                if v.get("name") in ["channel_name", "canal_nombre"]:
                                    val = (v.get("value") or "").lower()
                                    if "cocina" in val:
                                        niche = "🍳 COCINA TECNOLÓGICA"
                                    elif "limpieza" in val:
                                        niche = "🧹 LIMPIEZA DEL PUEBLO"
                                    elif "librería" in val or "libreria" in val:
                                        niche = "📚 LIBRERÍA DEL PUEBLO"
                                    elif "calzado" in val or "zapater" in val:
                                        niche = "👟 CALZADO DEL PUEBLO"
            
            wf_info[w_id] = {"name": w_name, "niche": niche}
    return wf_info

def generate_report(current_wf_id=None):
    now = datetime.now(MADRID_TZ)
    if now.time() < time(8, 0):
        today = now.date() - timedelta(days=1)
    else:
        today = now.date()
    yesterday = today - timedelta(days=1)

    start_dt = datetime.combine(yesterday, time(22, 0, 0), tzinfo=MADRID_TZ)
    end_dt = datetime.combine(today, time(8, 0, 0), tzinfo=MADRID_TZ)

    # Workflow map
    wf_map = get_workflow_info_map()

    # Fetch executions
    ex_res = _api_get("/executions?limit=250")
    executions = ex_res.get("data", []) if ex_res else []

    niche_groups = {}
    total_count = 0

    for ex in executions:
        started_str = ex.get("startedAt")
        if not started_str:
            continue
        st_dt = datetime.fromisoformat(started_str.replace("Z", "+00:00")).astimezone(MADRID_TZ)
        if start_dt <= st_dt <= end_dt:
            w_id = ex.get("workflowId")
            if w_id == "t1jH9GrGAJDgkLOr" or (current_wf_id and w_id == current_wf_id) or w_id == "xZKfBqQk6RXFq07E":
                continue
            
            info = wf_map.get(w_id, {"name": w_id, "niche": "🤖 OTROS WORKFLOWS"})
            niche_name = info["niche"]
            if niche_name not in niche_groups:
                niche_groups[niche_name] = []
            niche_groups[niche_name].append((st_dt, ex, info["name"]))
            total_count += 1

    header = f"📊 *Resumen de Ejecuciones Nocturnas*\n🗓 *Periodo:* {start_dt.strftime('%d/%m %H:%M')} — {end_dt.strftime('%d/%m %H:%M')}\n"
    try:
        from campaign_manager import get_campaign_status
        camp_info = get_campaign_status(end_dt.date())
        header += f"🎯 *Campaña:* {camp_info}\n"
    except Exception:
        pass

    sections = []
    if not niche_groups:
        sections.append("ℹ️ No se registraron ejecuciones de workflows en este periodo.")
    else:
        # Order niches logically
        ordered_keys = [
            "🍳 COCINA TECNOLÓGICA",
            "🧹 LIMPIEZA DEL PUEBLO",
            "👟 CALZADO DEL PUEBLO",
            "📚 LIBRERÍA DEL PUEBLO",
            "🐶 CANAL DRACO / MASCOTAS",
            "🤖 OTROS WORKFLOWS"
        ]
        
        present_keys = [k for k in ordered_keys if k in niche_groups]
        for k in niche_groups:
            if k not in present_keys:
                present_keys.append(k)

        for niche_name in present_keys:
            items = niche_groups[niche_name]
            items.sort(key=lambda x: x[0])
            group_lines = [f"📌 *{niche_name}*"]
            
            for st_dt, ex, w_name in items:
                status = ex.get("status")
                status_str = "✅ Success" if status == "success" else "❌ Failed" if status == "error" else f"⏳ {status.upper()}"
                time_str = st_dt.strftime("%H:%M")
                group_lines.append(f"• *{w_name}* ({time_str}): {status_str}")
                
                ex_details = _api_get(f"/executions/{ex['id']}?includeData=true")
                if ex_details:
                    yt_titles = extract_yt_titles(ex_details)
                    for title in yt_titles:
                        group_lines.append(f"  🎬 *Título:* {title}")
                        
            sections.append("\n".join(group_lines))

    full_text = header + "\n" + "\n\n_________________________________________\n\n".join(sections)
    return {
        "text": full_text,
        "total_executions": total_count,
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat()
    }

if __name__ == "__main__":
    current_wf = sys.argv[1] if len(sys.argv) > 1 else None
    result = generate_report(current_wf)
    print(json.dumps(result, ensure_ascii=False, indent=2))
