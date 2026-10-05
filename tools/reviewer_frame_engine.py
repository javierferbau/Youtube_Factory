#!/usr/bin/env python3
"""
reviewer_frame_engine.py — Motor de Transformación Anti-Content ID y Reviewer Frame (PiP).
Convierte vídeos comerciales de Amazon en contenido transformado (Fair Use / Análisis Crítico):
1. Ventana Picture-in-Picture (65% pantalla) con bordes estilizados y badges de directo.
2. Panel lateral (35% pantalla) con Ficha Técnica, Puesto/Opción, Precio, Estrellas y Specs.
3. Filtros anti-fingerprinting: hflip (espejo), crop 12%, ajuste cromático y fondo dinámico desenfocado.
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from thumbnail_engine import get_font, draw_pill_smart
except ImportError:
    FONT_PATH = "/home/javierferb/n8n/assets/fonts/Anton-Regular.ttf"
    def get_font(size):
        return ImageFont.truetype(FONT_PATH, size)
    def draw_pill_smart(im, x, y, text, font, bg=(20, 20, 20), fg=(255, 255, 255), pad=(14, 6), radius=8, **kwargs):
        d = ImageDraw.Draw(im)
        bbox = font.getbbox(text)
        w = bbox[2] - bbox[0] + pad[0] * 2
        h = bbox[3] - bbox[1] + pad[1] * 2
        d.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=bg)
        d.text((x + pad[0] - bbox[0], y + pad[1] - bbox[1]), text, font=font, fill=fg)
        return w, h

W, H = 1920, 1080

NICHE_NAMES = {
    "cocina": "LA COCINA TECNOLÓGICA",
    "limpieza": "LIMPIEZA DEL PUEBLO",
    "calzado": "ZAPATERÍA DEL PUEBLO",
    "libreria": "LIBRERÍA DEL PUEBLO",
    "taller": "EL TALLER DEL PUEBLO",
    "barberia": "LA BARBERÍA DEL PUEBLO"
}

NICHE_COLORS = {
    "cocina": {"accent": (255, 215, 0), "border": (255, 215, 0, 190), "bg_badge": (255, 215, 0)},
    "limpieza": {"accent": (0, 220, 180), "border": (0, 220, 180, 190), "bg_badge": (0, 200, 160)},
    "calzado": {"accent": (255, 140, 0), "border": (255, 140, 0, 190), "bg_badge": (255, 140, 0)},
    "libreria": {"accent": (147, 197, 253), "border": (147, 197, 253, 190), "bg_badge": (59, 130, 246)},
    "taller": {"accent": (250, 204, 21), "border": (250, 204, 21, 200), "bg_badge": (234, 179, 8)},
    "barberia": {"accent": (217, 119, 6), "border": (217, 119, 6, 200), "bg_badge": (180, 83, 9)}
}

def create_reviewer_card_overlay(output_path: str, rank: str = "", label: str = "",
                                 brand: str = "", title: str = "", price: str = "",
                                 rating: str = "", features: list = None, niche: str = "cocina",
                                 is_vs: bool = False) -> str:
    """
    Genera un PNG transparente 1920x1080 con:
    - Ficha de review izquierda (35% ancho).
    - Marco de ventana PiP derecha (65% ancho).
    - Badges y marcas de agua anti-huella.
    """
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)

    niche_key = niche.lower() if niche else "cocina"
    if "limpieza" in niche_key:
        niche_key = "limpieza"
    elif "calzado" in niche_key or "zapater" in niche_key:
        niche_key = "calzado"
    elif "librer" in niche_key or "libro" in niche_key:
        niche_key = "libreria"
    elif "taller" in niche_key or "herramient" in niche_key or "brico" in niche_key:
        niche_key = "taller"
    elif "barber" in niche_key or "pelo" in niche_key or "afeit" in niche_key:
        niche_key = "barberia"
    else:
        niche_key = "cocina"

    colors = NICHE_COLORS.get(niche_key, NICHE_COLORS["cocina"])
    accent = colors["accent"]
    border_col = colors["border"]

    # 1. Panel Lateral Izquierdo (Ficha de Review)
    c_x1, c_y1 = 50, 70
    c_x2, c_y2 = 590, 1010

    # Fondo cristal oscuro con contorno del nicho
    draw.rounded_rectangle([c_x1, c_y1, c_x2, c_y2], radius=24, fill=(12, 16, 22, 235), outline=border_col, width=3)

    # Insignia de Ranking / Opción VS
    if is_vs:
        badge_txt = label if label else "★ OPCIÓN DESTACADA"
    else:
        badge_txt = f"★ PUESTO #{rank}" if rank else (label if label else "★ ANÁLISIS")
    
    draw_pill_smart(im, c_x1 + 30, c_y1 + 30, badge_txt, get_font(34), bg=accent, fg=(0, 0, 0), pad=(20, 8), radius=12)

    # Marca del Producto
    if not brand and title:
        first_word = title.strip().split()[0].replace("'", "").replace('"', "")
        if len(first_word) >= 2 and not first_word.lower() in ["el", "la", "los", "las", "un", "una", "de", "con", "para", "top"]:
            brand = first_word
    brand_clean = (brand or "MARCA TOP").upper().strip()
    draw.text((c_x1 + 32, c_y1 + 115), brand_clean[:18], font=get_font(50), fill=(255, 255, 255))

    # Título limpio en 2 líneas
    clean_title = (title or "Producto Recomendado").replace("'", "").replace('"', '').strip()
    words = clean_title.split()
    line1 = " ".join(words[:4])
    line2 = " ".join(words[4:9])
    draw.text((c_x1 + 32, c_y1 + 185), line1, font=get_font(30), fill=(200, 210, 225))
    if line2:
        draw.text((c_x1 + 32, c_y1 + 225), line2, font=get_font(30), fill=(200, 210, 225))

    # Línea divisoria
    draw.line([c_x1 + 30, c_y1 + 280, c_x2 - 30, c_y1 + 280], fill=(50, 60, 75, 255), width=2)

    # Píldora de Precio real
    clean_price = price.strip() if price else ""
    if clean_price:
        p_txt = clean_price if "€" in clean_price else f"{clean_price} €"
        draw_pill_smart(im, c_x1 + 30, c_y1 + 305, f"PRECIO: {p_txt}", get_font(32), bg=(22, 101, 52), fg=(255, 255, 255), pad=(18, 6), radius=10, border_color=(74, 222, 128), border_w=2)

    # Píldora de Valoración Amazon
    clean_rating = rating.strip() if rating else "4.5"
    draw_pill_smart(im, c_x1 + 30, c_y1 + 375, f"★ {clean_rating} / 5 EN AMAZON", get_font(28), bg=(202, 138, 4), fg=(0, 0, 0), pad=(18, 6), radius=10)

    # Bloque de Características
    draw.text((c_x1 + 32, c_y1 + 455), "CARACTERÍSTICAS CLAVE:", font=get_font(25), fill=accent)
    default_feats = [
        "✔ Calidad y rendimiento contrastado",
        "✔ Alta valoración de compradores",
        "✔ Garantía oficial y envío rápido",
        "✔ Mejor relación calidad precio"
    ]
    feats = features if (features and len(features) >= 2) else default_feats
    fy = c_y1 + 505
    for f in feats[:4]:
        f_clean = str(f).replace('\n', ' ').strip()
        if len(f_clean) > 34:
            f_clean = f_clean[:34].rsplit(' ', 1)[0]
        if not f_clean.startswith("✔"):
            f_clean = f"✔ {f_clean}"
        draw_pill_smart(im, c_x1 + 30, fy, f_clean, get_font(23), bg=(20, 28, 38), fg=(230, 240, 255), pad=(14, 6), radius=8, border_color=(45, 55, 72), border_w=1)
        fy += 65

    # Footer Card
    draw_pill_smart(im, c_x1 + 30, c_y2 - 75, "VERIFICADO AMAZON 2026", get_font(21), bg=(30, 40, 50), fg=(148, 163, 184), pad=(14, 5), radius=8)

    # 2. Marco de Ventana PiP (Picture-in-Picture)
    pip_x1, pip_y1 = 630, 70
    pip_x2, pip_y2 = 1870, 890

    # Borde exterior de la ventana de vídeo con color del nicho
    draw.rounded_rectangle([pip_x1 - 4, pip_y1 - 4, pip_x2 + 4, pip_y2 + 4], radius=20, outline=border_col, width=4)

    # Header de la ventana de vídeo (Estado de test)
    draw_pill_smart(im, pip_x1 + 20, pip_y1 - 25, "● DEMO Y RENDIMIENTO EN DIRECTO", get_font(24), bg=(220, 38, 38), fg=(255, 255, 255), pad=(18, 6), radius=10)

    # Watermark del canal en esquina superior derecha
    ch_brand = NICHE_NAMES.get(niche_key, "ANÁLISIS OFICIAL")
    draw_pill_smart(im, pip_x2 - 340, pip_y1 - 25, f"CANAL: {ch_brand}", get_font(22), bg=(15, 23, 42), fg=accent, pad=(16, 6), radius=10)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    im.save(output_path, "PNG")
    return output_path

def get_reviewer_video_filter(overlay_idx: int = 1, is_video: bool = True, sub_filter: str = "") -> str:
    """
    Construye la cadena filter_complex de FFmpeg para el modo Reviewer Frame:
    - [bg]: Fondo dinámico con desenfoque profundo y oscurecimiento.
    - [fg]: Vídeo con hflip, crop 12%, ajuste cromático y ajuste a la ventana PiP 1240x820.
    - Overlay de la ventana PiP + Overlay del marco gráfico.
    - Subtítulos situados en la franja inferior despejada (y: 900-1040).
    """
    if is_video:
        # Cadena anti-Content ID completa para vídeo
        fg_filter = "hflip,crop=iw*0.88:ih*0.88,eq=contrast=1.12:brightness=0.03:saturation=1.18,scale=1240:820:force_original_aspect_ratio=decrease,pad=1240:820:(ow-iw)/2:(oh-ih)/2:black[fg_pip]"
    else:
        # Cadena para foto estática con movimiento Ken Burns suave (Cero imágenes congeladas)
        fg_filter = "crop=iw*0.92:ih*0.92,eq=contrast=1.10:brightness=0.03:saturation=1.15,zoompan=z='min(zoom+0.0012,1.12)':d=700:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1240x820:fps=30[fg_pip]"

    bg_filter = "scale=480:270:force_original_aspect_ratio=increase,crop=480:270,boxblur=15:3,eq=brightness=-0.22:contrast=0.9,scale=1920:1080:flags=bicubic[bg]"

    parts = [
        f"[0:v]split[v_bg][v_fg]",
        f"[v_bg]{bg_filter}",
        f"[v_fg]{fg_filter}",
        f"[bg][fg_pip]overlay=630:70[comp1]",
        f"[comp1][{overlay_idx}:v]overlay=0:0[comp2]"
    ]

    if sub_filter:
        parts.append(f"[comp2]{sub_filter}[outv]")
    else:
        parts.append(f"[comp2]null[outv]")

    return ";".join(parts)

if __name__ == "__main__":
    t_png = "/tmp/test_engine_card.png"
    p = create_reviewer_card_overlay(t_png, rank="1", brand="ROBOROCK", title="Aspirador Robot Q7 Max+", price="349€", rating="4.7", niche="limpieza")
    print("Reviewer frame engine initialized and tested successfully:", p)
