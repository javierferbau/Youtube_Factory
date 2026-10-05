#!/usr/bin/env python3
import os
import sys
import subprocess
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from thumbnail_engine import get_font, get_symbol_image, draw_pill_smart

W, H = 1920, 1080

def create_reviewer_card_overlay(output_path, rank="1", brand="BOSCH", title="Robot MUM 5 1000W",
                                 price="283,99€", rating="4.4", features=None, niche="cocina"):
    """Genera el marco de review gráfico transparente (1920x1080) en PNG."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)

    # 1. Panel Lateral Izquierdo (Ficha de Review)
    card_x1, card_y1 = 50, 70
    card_x2, card_y2 = 590, 1010
    
    # Fondo cristal oscuro
    draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=24, fill=(12, 16, 22, 235), outline=(255, 215, 0, 180), width=3)

    # Insignia de Ranking
    rank_txt = f"★ PUESTO #{rank}" if rank else "★ ANÁLISIS"
    draw_pill_smart(im, card_x1 + 30, card_y1 + 30, rank_txt, get_font(36), bg=(255, 215, 0), fg=(0, 0, 0), pad=(20, 8), radius=12)

    # Marca y Título
    f_brand = get_font(52)
    f_title = get_font(32)
    draw.text((card_x1 + 32, card_y1 + 115), brand.upper()[:16], font=f_brand, fill=(255, 255, 255))
    
    # Título en 2 líneas max
    words = title.split()
    line1 = " ".join(words[:4])
    line2 = " ".join(words[4:9])
    draw.text((card_x1 + 32, card_y1 + 185), line1, font=f_title, fill=(200, 210, 225))
    if line2:
        draw.text((card_x1 + 32, card_y1 + 225), line2, font=f_title, fill=(200, 210, 225))

    # Divisor
    draw.line([card_x1 + 30, card_y1 + 285, card_x2 - 30, card_y1 + 285], fill=(50, 60, 75, 255), width=2)

    # Píldora de Precio
    if price:
        draw_pill_smart(im, card_x1 + 30, card_y1 + 310, f"PRECIO: {price}", get_font(34), bg=(22, 101, 52), fg=(255, 255, 255), pad=(18, 6), radius=10, border_color=(74, 222, 128), border_w=2)

    # Píldora de Valoración
    if rating:
        draw_pill_smart(im, card_x1 + 30, card_y1 + 380, f"★ {rating} / 5 EN AMAZON", get_font(30), bg=(202, 138, 4), fg=(0, 0, 0), pad=(18, 6), radius=10)

    # Puntos Clave / Características
    draw.text((card_x1 + 32, card_y1 + 465), "CARACTERÍSTICAS CLAVE:", font=get_font(26), fill=(255, 215, 0))
    default_feats = [
        "✔ Potencia y rendimiento profesional",
        "✔ Accesorios completos incluidos",
        "✔ Fácil limpieza y mantenimiento",
        "✔ Máxima durabilidad garantizada"
    ]
    feats = features if features and len(features) >= 2 else default_feats
    fy = card_y1 + 515
    for f in feats[:4]:
        draw_pill_smart(im, card_x1 + 30, fy, f[:32], get_font(24), bg=(20, 28, 38), fg=(230, 240, 255), pad=(14, 6), radius=8, border_color=(45, 55, 72), border_w=1)
        fy += 65

    # Footer Card
    draw_pill_smart(im, card_x1 + 30, card_y2 - 75, "VERIFICADO AMAZON 2026", get_font(22), bg=(30, 40, 50), fg=(148, 163, 184), pad=(14, 5), radius=8)

    # 2. Marco de Ventana PiP (Picture-in-Picture)
    pip_x1, pip_y1 = 630, 70
    pip_x2, pip_y2 = 1870, 890
    
    # Borde exterior de la ventana de vídeo
    draw.rounded_rectangle([pip_x1 - 4, pip_y1 - 4, pip_x2 + 4, pip_y2 + 4], radius=20, outline=(255, 215, 0, 200), width=4)

    # Header de la ventana de vídeo
    draw_pill_smart(im, pip_x1 + 20, pip_y1 - 25, "● DEMO Y RENDIMIENTO EN DIRECTO", get_font(24), bg=(220, 38, 38), fg=(255, 255, 255), pad=(18, 6), radius=10)

    # Watermark del canal
    niche_names = {
        "cocina": "LA COCINA TECNOLÓGICA",
        "limpieza": "LIMPIEZA DEL PUEBLO",
        "calzado": "ZAPATERÍA DEL PUEBLO",
        "libreria": "LIBRERÍA DEL PUEBLO"
    }
    ch_name = niche_names.get(niche.lower(), "REVIEW OFICIAL")
    draw_pill_smart(im, pip_x2 - 320, pip_y1 - 25, f"CANAL: {ch_name}", get_font(22), bg=(15, 23, 42), fg=(255, 215, 0), pad=(16, 6), radius=10)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    im.save(output_path, "PNG")
    print(f"Reviewer overlay saved: {output_path}")
    return output_path

if __name__ == "__main__":
    out_png = "/home/javierferb/.gemini/antigravity/brain/580d2633-4ee0-4c17-bcaf-fff9422f1bb3/reviewer_card_overlay_test.png"
    create_reviewer_card_overlay(out_png, rank="1", brand="BOSCH", title="Robot de Cocina MUM 5 1000W", price="283,99€", rating="4.4")
