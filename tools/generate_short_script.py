#!/usr/bin/env python3
"""
generate_short_script.py
Genera un guion corto (<50 segundos / ~110 palabras) enfocado en el producto #1 (ganador)
y derivando tráfico al vídeo horizontal completo de 8+ minutos.
Sigue los principios de marketing-psychology y copywriting-hooks.
"""

import sys
import os
import json
import argparse
import re

def main():
    parser = argparse.ArgumentParser(description="Generador de guiones cortos para YouTube Shorts (9:16)")
    parser.add_argument("project_dir", help="Directorio del proyecto que contiene data.json")
    args, unknown = parser.parse_known_args()

    project_dir = os.path.abspath(args.project_dir)
    data_json_path = os.path.join(project_dir, "data.json")

    if not os.path.exists(data_json_path):
        print(json.dumps({"error": f"No se encontró data.json en {project_dir}"}))
        sys.exit(1)

    with open(data_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    query = data.get("query", "productos").strip()
    query_title = query.lower()
    products = data.get("products", [])

    # Obtener el producto #1 (rank 1)
    top_product = None
    for p in products:
        if p.get("rank") == 1:
            top_product = p
            break
    if not top_product and products:
        top_product = products[0]

    top_title = top_product.get("title", f"el modelo número 1 de {query_title}") if top_product else f"el modelo número 1 de {query_title}"
    # Acortar título para locución si es muy largo
    if len(top_title) > 60:
        top_title = top_title[:55].rsplit(" ", 1)[0]

    top_price = top_product.get("price", "un precio excelente") if top_product else "un precio excelente"
    top_rating = top_product.get("rating", "4.8") if top_product else "4.8"
    if "sobre 5" not in top_rating and "estrellas" not in top_rating:
        top_rating = f"{top_rating} sobre 5 estrellas"

    # 1. Hook (Loss Aversion + Curiosity Gap, ~15-20 palabras)
    hook = (
        f"Antes de comprar {query_title}, no cometas el error de elegir a ciegas. "
        f"Hay una opción que destaca claramente sobre el resto en Amazon en 2026."
    )

    # 2. Review Exprés del Producto #1 (Social Proof + Specs, ~60-70 palabras)
    review = (
        f"La opción número 1 de nuestro ranking es la {top_title}. "
        f"Acumula una sobresaliente valoración de {top_rating} y cientos de opiniones de compradores reales. "
        f"Destaca por su potencia optimizada, materiales duraderos y un rendimiento impecable desde el primer uso por unos {top_price}. "
        f"Es la compra más inteligente si buscas calidad sin pagar de más."
    )

    # 3. Outro / CTA para derivar al vídeo largo (Present Bias + Call to Action, ~25-30 palabras)
    outro = (
        f"¿Quieres ver los 7 mejores modelos comparados al detalle? "
        f"Tienes el vídeo completo de 8 minutos y los enlaces de oferta en el primer comentario y en la descripción. "
        f"¡Suscríbete para no perderte el próximo chollo!"
    )

    full_text = f"{hook} {review} {outro}"
    words = full_text.split()
    total_words = len(words)
    est_seconds = round(total_words / 2.3, 1)  # ~138 palabras/min en Kokoro TTS = ~45-50s

    short_script = {
        "query": query,
        "hook": hook,
        "product": review,
        "outro": outro,
        "full_text": full_text,
        "total_words": total_words,
        "est_seconds": est_seconds,
        "top_product": {
            "title": top_product.get("title", "") if top_product else "",
            "price": top_price,
            "rating": top_rating,
            "asin": top_product.get("asin", "") if top_product else "",
            "image_file": top_product.get("image_file", "") if top_product else "",
            "video_file": top_product.get("video_file", "") if top_product else ""
        }
    }

    output_path = os.path.join(project_dir, "short_script.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(short_script, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "status": "success",
        "script_file": output_path,
        "total_words": total_words,
        "est_seconds": est_seconds
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
