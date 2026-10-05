#!/usr/bin/env python3
"""
fetch_youtube_metrics.py
Consulta las métricas consolidadas, comentarios sin responder y fuentes de tráfico (YouTube Analytics)
de los canales de YouTube vía el workflow dedicado de n8n (usando las credenciales oficiales youTubeOAuth2Api)
y mantiene un histórico detallado en /home/javierferb/n8n/tools/youtube_performance_history.json.
"""

import os
import sys
import json
import urllib.request
import urllib.error
import datetime

WEBHOOK_URL = "http://localhost:5678/webhook/test-yt-metrics"
HISTORY_FILE = "/home/javierferb/n8n/tools/youtube_performance_history.json"

def fetch_live_data():
    req = urllib.request.Request(WEBHOOK_URL, data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except Exception as e:
        return {"error": str(e), "channels": [], "unanswered_comments": []}

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def evaluate_traffic_intent(search_pct):
    """Regla de diagnóstico para tráfico de compra vs entretenimiento pasivo."""
    if search_pct >= 30.0:
        return "ALTA INTENCIÓN DE COMPRA (Cookie Fuerte)"
    elif search_pct >= 20.0:
        return "EN CRECIMIENTO / INDEXANDO"
    else:
        return "AUDIENCIA PASIVA (Afinar SEO)"

def get_channel_growth_report():
    data = fetch_live_data()
    channels = data.get("channels", [])
    if not channels and "error" in data:
        return {"error": f"No se pudieron obtener métricas en vivo de YouTube: {data['error']}", "channels": [], "unanswered_comments": []}

    history = load_history()
    today_str = datetime.date.today().isoformat()

    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "total_unanswered_comments": data.get("total_unanswered_comments", 0),
        "unanswered_comments": data.get("unanswered_comments", []),
        "channels": []
    }

    for ch in channels:
        key = ch.get("channel_key")
        title = ch.get("title")
        custom_url = ch.get("custom_url")
        curr_views = ch.get("views", 0)
        curr_subs = ch.get("subscribers", 0)
        curr_videos = ch.get("videos", 0)
        unanswered_count = ch.get("unanswered_comments_count", 0)
        unanswered_items = ch.get("unanswered_comments", [])

        # Fuentes de tráfico 7d y 28d
        traffic_7d = ch.get("traffic_sources_7d", {
            "search_pct": 25.0,
            "suggested_pct": 55.0,
            "shorts_pct": 20.0,
            "other_pct": 0.0,
            "live": False
        })
        traffic_28d = ch.get("traffic_sources_28d", {
            "search_pct": 25.0,
            "suggested_pct": 55.0,
            "shorts_pct": 20.0,
            "other_pct": 0.0,
            "live": False
        })

        search_pct_7d = float(traffic_7d.get("search_pct", 0.0))
        traffic_eval = evaluate_traffic_intent(search_pct_7d)

        # Histórico
        ch_history = history.setdefault(key, {})
        past_dates = sorted([d for d in ch_history.keys() if d < today_str and not d.startswith("traffic_")], reverse=True)
        prev_entry = ch_history.get(past_dates[0]) if past_dates else None

        delta_views = (curr_views - prev_entry.get("views", 0)) if prev_entry and isinstance(prev_entry, dict) else 0
        delta_subs = (curr_subs - prev_entry.get("subscribers", 0)) if prev_entry and isinstance(prev_entry, dict) else 0
        delta_videos = (curr_videos - prev_entry.get("videos", 0)) if prev_entry and isinstance(prev_entry, dict) else 0

        views_per_video = round(curr_views / curr_videos, 1) if curr_videos > 0 else 0

        channel_obj = {
            "key": key,
            "title": title,
            "custom_url": custom_url,
            "views": curr_views,
            "subscribers": curr_subs,
            "videos": curr_videos,
            "delta_views_24h": delta_views,
            "delta_subs_24h": delta_subs,
            "views_per_video": views_per_video,
            "unanswered_comments_count": unanswered_count,
            "unanswered_comments": unanswered_items,
            "status_evaluation": "ALTA TRACCIÓN" if views_per_video > 100 else ("CRECIENDO" if views_per_video > 30 else "LENTO / EVALUAR REEMPLAZO"),
            "traffic_sources_7d": traffic_7d,
            "traffic_sources_28d": traffic_28d,
            "traffic_quality_evaluation": traffic_eval
        }
        report["channels"].append(channel_obj)

        ch_history[today_str] = {
            "views": curr_views,
            "subscribers": curr_subs,
            "videos": curr_videos,
            "timestamp": datetime.datetime.now().isoformat(),
            "traffic_sources_7d": traffic_7d,
            "traffic_sources_28d": traffic_28d,
            "traffic_intent": traffic_eval
        }

        # Guardar también bloque específico de histórico de evolución de tráfico
        traffic_hist = ch_history.setdefault("traffic_evolution", {})
        traffic_hist[today_str] = {
            "7d": traffic_7d,
            "28d": traffic_28d,
            "eval": traffic_eval
        }

    save_history(history)
    return report

if __name__ == "__main__":
    rep = get_channel_growth_report()
    print(json.dumps(rep, indent=2, ensure_ascii=False))
