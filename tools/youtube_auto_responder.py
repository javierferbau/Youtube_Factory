#!/usr/bin/env python3
"""
youtube_auto_responder.py
Auto-respondedor inteligente de comentarios de YouTube para los 6 canales de afiliados.
- Obtiene comentarios sin responder vía n8n.
- Genera respuestas empáticas y orientadas a conversión con Ollama (Qwen 3.8 27B).
- Publica las respuestas en YouTube mediante el workflow n8n (usando las credenciales oficiales).
- Mantiene registro en answered_comments_history.json para evitar duplicados.
"""

import os
import sys
import json
import urllib.request
import urllib.error
import datetime

REPLY_WEBHOOK_URL = "http://localhost:5678/webhook/reply-yt-comment"
METRICS_WEBHOOK_URL = "http://localhost:5678/webhook/test-yt-metrics"
HISTORY_FILE = "/home/javierferb/n8n/tools/answered_comments_history.json"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"

CHANNEL_PERSONAS = {
    "Zapateria": {
        "name": "Zapatería del Pueblo",
        "role": "zapatero experto y apasionado del calzado cómodo, zapatillas y botas de montaña",
        "style": "cercano, servicial, de pueblo, recomendando mirar la descripción o comentario fijado si buscan tallas, ofertas o precios."
    },
    "Barberia": {
        "name": "La Barbería del Pueblo",
        "role": "barbero tradicional experto en afeitado, máquinas cortapelos y cuidado masculino",
        "style": "profesional, directo, de confianza, aconsejando el mejor modelo y recordando que los enlaces con descuento están en el comentario fijado."
    },
    "Cocina": {
        "name": "Cocina Tecnológica",
        "role": "cocinero apasionado de los electrodomésticos y recetas prácticas",
        "style": "entusiasta, alegre, animando a disfrutar de la cocina y recordando que las ofertas de las freidoras/cafeteras están en el comentario fijado."
    },
    "Taller": {
        "name": "El Taller del Pueblo",
        "role": "manitas y mecánico de toda la vida experto en herramientas de bricolaje",
        "style": "práctico, campechano, animando al trabajo bien hecho y recordando que las ofertas están fijadas en el vídeo."
    },
    "Limpieza": {
        "name": "Limpieza del Pueblo",
        "role": "experto en trucos del hogar, robots aspiradores y limpieza eficaz",
        "style": "amable, servicial, ahorrando tiempo de limpieza y recomendando el enlace fijado para comprar."
    },
    "Libreria": {
        "name": "Librería del Pueblo",
        "role": "librero de pueblo apasionado de la lectura y el crecimiento personal",
        "style": "culto, cálido, recomendando buenas lecturas e indicando que el libro está en el enlace fijado."
    }
}

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

def fetch_unanswered_comments():
    req = urllib.request.Request(METRICS_WEBHOOK_URL, data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("unanswered_comments", [])
    except Exception as e:
        print(f"Error obteniendo comentarios: {e}", file=sys.stderr)
        return []

def generate_ai_reply(channel_key, author, user_comment):
    persona = CHANNEL_PERSONAS.get(channel_key, {
        "name": "Canal",
        "role": "creador del canal",
        "style": "amable y agradecido"
    })

    system_prompt = (
        f"Eres el creador de YouTube del canal '{persona['name']}' ({persona['role']}). "
        f"Tu tono es {persona['style']}. "
        f"Responde al comentario de un seguidor llamado @{author}. "
        f"REGLAS ESTRICTAS:\n"
        f"1. Máximo 1 o 2 frases cortas y muy naturales.\n"
        f"2. Da las gracias de corazón y sé muy cercano.\n"
        f"3. Si el usuario muestra interés en comprar, conseguir o saber precio/modelo, menciónale amablemente que tiene el enlace con la oferta oficial en el primer comentario fijado de este vídeo.\n"
        f"4. Si el comentario es muy breve (ej: 'Ia', 'ok', emojis), dale un saludo cariñoso y pregúntale en qué le puedes ayudar.\n"
        f"5. NO uses saludos formales robóticos como 'Estimado'. Responde directamente el texto sin comillas."
    )

    try:
        req_data = json.dumps({
            "model": "qwen3.8:27b",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Comentario de @{author.lstrip('@')}: \"{user_comment}\""}
            ],
            "stream": False,
            "options": {"temperature": 0.6, "num_predict": 70}
        }).encode("utf-8")

        req = urllib.request.Request(OLLAMA_URL, data=req_data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=35) as res:
            res_json = json.loads(res.read().decode("utf-8"))
            reply_text = res_json.get("message", {}).get("content", "").strip().strip('"')
            if reply_text and len(reply_text) > 5:
                return reply_text
    except Exception as e:
        print(f"Error generando respuesta con Ollama: {e}", file=sys.stderr)

    # Fallbacks humanos de alta calidad según canal
    if "Zapateria" in channel_key:
        return f"¡Hola @{author.lstrip('@')}! Muchísimas gracias por el apoyo. Tienes el enlace directo con la oferta y tallas en el comentario fijado del vídeo. ¡Un abrazo!"
    elif "Barberia" in channel_key:
        return f"¡Hola @{author.lstrip('@')}! Gracias por pasarte por el canal. Si buscas el modelo o precio, tienes el enlace directo en el comentario fijado. ¡Saludos!"
    elif "Cocina" in channel_key:
        return f"¡Muchísimas gracias @{author.lstrip('@')}! Tienes la oferta activa y detalles del aparato en el comentario fijado. ¡A disfrutar cocinando!"
    else:
        return f"¡Hola @{author.lstrip('@')}! Muchas gracias por tu comentario y por apoyar el canal. ¡Un saludo enorme!"

def post_reply_via_n8n(channel_key, comment_id, reply_text):
    payload = {
        "channel_key": channel_key,
        "comment_id": comment_id,
        "reply_text": reply_text
    }
    req = urllib.request.Request(
        REPLY_WEBHOOK_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return True, data
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        return False, f"HTTP {e.code}: {err_msg}"
    except Exception as e:
        return False, str(e)

def run_auto_responder(dry_run=False):
    print("=== INICIANDO AUTO-RESPONDEDOR INTELIGENTE DE YOUTUBE ===")
    unanswered = fetch_unanswered_comments()
    history = load_history()
    
    pending_to_process = []
    for c in unanswered:
        cid = c.get("comment_id")
        if cid and cid not in history:
            pending_to_process.append(c)

    print(f"Comentarios detectados: {len(unanswered)} | Nuevos por responder: {len(pending_to_process)}")
    
    if not pending_to_process:
        print("✓ Todos los comentarios ya han sido respondidos previamente.")
        return {"processed": 0, "replies": []}

    results = []
    for c in pending_to_process:
        cid = c.get("comment_id")
        ch_key = c.get("channel_key")
        author = c.get("author", "amigo")
        text = c.get("text", "")
        vid = c.get("video_id")

        print(f"\nProcesando [{ch_key}] @{author}: \"{text}\"")
        reply_text = generate_ai_reply(ch_key, author, text)
        print(f"  └─ Respuesta generada: \"{reply_text}\"")

        if dry_run:
            print("  (Dry run activado - no se publica en YouTube)")
            results.append({
                "channel_key": ch_key,
                "comment_id": cid,
                "author": author,
                "reply": reply_text,
                "status": "dry_run"
            })
            continue

        success, res = post_reply_via_n8n(ch_key, cid, reply_text)
        if success:
            print(f"  ✓ ¡Publicado con éxito en YouTube!")
            history[cid] = {
                "channel_key": ch_key,
                "author": author,
                "original_text": text,
                "reply_text": reply_text,
                "answered_at": datetime.datetime.now().isoformat()
            }
            results.append({
                "channel_key": ch_key,
                "comment_id": cid,
                "author": author,
                "reply": reply_text,
                "status": "published"
            })
        else:
            print(f"  ❌ Error publicando en YouTube: {res}")
            results.append({
                "channel_key": ch_key,
                "comment_id": cid,
                "author": author,
                "reply": reply_text,
                "status": "error",
                "error": str(res)
            })

    save_history(history)
    return {"processed": len(results), "replies": results}

if __name__ == "__main__":
    dry_run_arg = "--dry-run" in sys.argv
    res = run_auto_responder(dry_run=dry_run_arg)
    print("\nResumen final:", json.dumps(res, indent=2, ensure_ascii=False))
