#!/usr/bin/env python3
"""
thumbnail_engine.py — Motor Centralizado de Miniaturas Pillow 2.0 (Mobile First)
Implementa las 5 plantillas aprobadas para VS y las 5 para TOP con rotación dinámica,
fondos atmosféricos por nicho (taller, barbería, zapatería, cocina),
halo de luz centrado geométricamente, tipografía Anton con contorno duro,
sombra de contacto fotorrealista anclada (solape 10-15px sin flotación),
escala agresiva Mobile First (50-58% ancho) y soporte de glifos/emojis sin tofu boxes.
"""

import os
import sys
import json
import random
import re
import shutil
from typing import Optional, Dict, Any, List, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

W, H = 1280, 720

FONT_ANTON = "/home/javierferb/n8n/assets/fonts/Anton-Regular.ttf"
FONT_DEJAVU = "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"
FONT_EMOJI = "/usr/share/fonts/noto/NotoColorEmoji.ttf"

_cached_emoji_font = None

def get_font(size: int) -> ImageFont.ImageFont:
    if os.path.exists(FONT_ANTON):
        try:
            return ImageFont.truetype(FONT_ANTON, size)
        except Exception:
            pass
    if os.path.exists(FONT_DEJAVU):
        try:
            return ImageFont.truetype(FONT_DEJAVU, size)
        except Exception:
            pass
    return ImageFont.load_default()

def get_symbol_image(char: str, target_size: int = 30, fill_color: Tuple[int, int, int] = (255, 255, 255)) -> Optional[Image.Image]:
    """Renderiza glifos tipográficos (★, ✔, ✖, ✓, ⚔️) o emojis a color (⚡, 🥊, 🏆, 🔥, etc.) sin tofu boxes."""
    global _cached_emoji_font
    
    # 1. Glifos vectoriales tipográficos comunes
    if char in ['★', '✔', '✖', '✓', '✦', '▲', '▼', '►', '◄']:
        if os.path.exists(FONT_DEJAVU):
            try:
                df = ImageFont.truetype(FONT_DEJAVU, int(target_size * 1.6))
                im2 = Image.new('RGBA', (target_size * 3, target_size * 3), (0, 0, 0, 0))
                d2 = ImageDraw.Draw(im2)
                d2.text((5, 5), char, font=df, fill=fill_color)
                bbox2 = im2.getbbox()
                if bbox2:
                    im2 = im2.crop(bbox2)
                    im2.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)
                    return im2
            except Exception:
                pass

    # 2. Emojis nativos a color (strike fija 109px de NotoColorEmoji)
    if os.path.exists(FONT_EMOJI):
        try:
            if _cached_emoji_font is None:
                _cached_emoji_font = ImageFont.truetype(FONT_EMOJI, 109)
            im = Image.new('RGBA', (140, 140), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            d.text((10, 10), char, font=_cached_emoji_font, embedded_color=True)
            bbox = im.getbbox()
            if bbox:
                im = im.crop(bbox)
                im.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)
                return im
        except Exception:
            pass

    return None

def is_symbol_or_emoji(s: str) -> bool:
    """Determina con precisión si una cadena es un emoji o glifo (nunca precios o números)."""
    if not s or len(s) > 4:
        return False
    if any(c.isdigit() or c in '€$£¥¿?!¡.,;:-_#' or ('a' <= c.lower() <= 'z') for c in s):
        return False
    return any(ord(c) > 127 for c in s) or s in ['★', '✔', '✖', '✓', '✦', '▲', '▼', '►', '◄']

def draw_pill_smart(base_im: Image.Image, x: int, y: int, text: str, font: ImageFont.ImageFont,
                    bg: Tuple[int, int, int] = (235, 30, 30), fg: Tuple[int, int, int] = (255, 255, 255),
                    pad: Tuple[int, int] = (18, 7), radius: int = 10,
                    border_color: Optional[Tuple[int, int, int]] = None, border_w: int = 2) -> Tuple[int, int]:
    """Dibuja una píldora con soporte transparente para icono/emoji inicial y borde de alto contraste."""
    tokens = text.split(' ', 1)
    icon_img = None
    label_text = text
    
    # Caso A: El texto completo es un glifo o emoji (ej. '⚔️', '★', '🔥')
    if len(tokens) == 1 and is_symbol_or_emoji(text):
        icon_img = get_symbol_image(text, target_size=int(font.size * 1.1), fill_color=fg)
        if icon_img:
            label_text = ""
    # Caso B: Icono + texto (ej. '⚡ DUELO DEFINITIVO')
    elif len(tokens) == 2 and is_symbol_or_emoji(tokens[0]):
        sym = tokens[0]
        icon_img = get_symbol_image(sym, target_size=int(font.size * 0.9), fill_color=fg)
        if icon_img:
            label_text = tokens[1]
            
    if label_text:
        bbox = font.getbbox(label_text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
    else:
        bbox = (0, 0, 0, 0)
        tw = 0
        th = icon_img.size[1] if icon_img else font.size
    
    icon_w = icon_img.size[0] if icon_img else 0
    icon_gap = 10 if (icon_img and label_text) else 0
    
    total_w = pad[0] + icon_w + icon_gap + tw + pad[0]
    total_h = max(th, icon_img.size[1] if icon_img else 0) + pad[1] * 2
    
    draw = ImageDraw.Draw(base_im)
    if border_color and border_w > 0:
        draw.rounded_rectangle([x - border_w, y - border_w, x + total_w + border_w, y + total_h + border_w],
                               radius=radius + border_w, fill=border_color)
    draw.rounded_rectangle([x, y, x + total_w, y + total_h], radius=radius, fill=bg)
    
    cur_x = x + pad[0]
    if icon_img:
        icon_y = y + (total_h - icon_img.size[1]) // 2
        base_im.paste(icon_img, (cur_x, icon_y), icon_img)
        cur_x += icon_w + icon_gap
        
    if label_text:
        text_y = y + pad[1] - bbox[1]
        draw.text((cur_x - bbox[0], text_y), label_text, font=font, fill=fg)
    return total_w, total_h

def draw_decision_badge(im: Image.Image, badge_type: str = "winner", x: int = 60, y: int = 60):
    """Pastilla flotante compacta en esquina superior (Social Proof o Loss Aversion)."""
    if badge_type == "winner":
        draw_pill_smart(im, x, y, "★ 4.8 (+12K)", get_font(30), bg=(255, 215, 0), fg=(0, 0, 0),
                        pad=(16, 6), radius=12, border_color=(255, 255, 255), border_w=2)
    elif badge_type == "warning":
        draw_pill_smart(im, x, y, "⚠️ CUIDADO", get_font(30), bg=(235, 30, 30), fg=(255, 255, 255),
                        pad=(16, 6), radius=12, border_color=(255, 215, 0), border_w=2)
    elif badge_type == "top1":
        draw_pill_smart(im, x, y, "🏆 Nº 1 TOP", get_font(30), bg=(0, 200, 85), fg=(0, 0, 0),
                        pad=(16, 6), radius=12, border_color=(255, 255, 255), border_w=2)
    else:
        draw_pill_smart(im, x, y, "★ TOP VENTAS", get_font(30), bg=(255, 180, 0), fg=(0, 0, 0),
                        pad=(16, 6), radius=12, border_color=(255, 255, 255), border_w=2)

def parse_price_val(p_str: Any) -> Optional[float]:
    """Extrae un valor numérico float de una cadena o número de precio de Amazon."""
    if p_str is None:
        return None
    if isinstance(p_str, (int, float)):
        return float(p_str) if p_str > 0 else None
    if not isinstance(p_str, str):
        return None
    clean = p_str.replace(' ', ' ').replace('€', '').strip()
    m = re.search(r'(\d+)(?:[.,](\d{1,2}))?', clean)
    if m:
        integer_part = m.group(1)
        decimal_part = m.group(2) if m.group(2) else '00'
        try:
            val = float(f"{integer_part}.{decimal_part}")
            return val if val > 0 else None
        except Exception:
            return None
    return None

def format_clean_price(p_str: str, default_fallback: str = "79€") -> str:
    """Convierte cadena de precio sucia en formato limpio para choque visual (ej. '129€')."""
    val = parse_price_val(p_str)
    if val and val > 0:
        return f"{int(round(val))}€"
    return default_fallback

def draw_strikethrough_price_pill(im: Image.Image, x: int, y: int, old_price: str, new_price: str,
                                  savings_label: str = "-40%", bg: Tuple[int, int, int] = (14, 20, 24),
                                  border_color: Tuple[int, int, int] = (0, 220, 120), radius: int = 12) -> Tuple[int, int]:
    """Insignia compuesta de Chollo con precio antiguo tachado y nuevo precio brillante."""
    f_old = get_font(32)
    f_new = get_font(46)
    f_save = get_font(26)
    
    obbox = f_old.getbbox(old_price)
    ow = obbox[2] - obbox[0]
    oh = obbox[3] - obbox[1]
    
    nbbox = f_new.getbbox(new_price)
    nw = nbbox[2] - nbbox[0]
    nh = nbbox[3] - nbbox[1]
    
    sbbox = f_save.getbbox(savings_label)
    sw = sbbox[2] - sbbox[0]
    sh = sbbox[3] - sbbox[1]
    
    pad_x = 22
    pad_y = 10
    gap = 16
    
    s_pad_x = 14
    s_pad_y = 5
    s_pill_w = sw + s_pad_x * 2
    s_pill_h = sh + s_pad_y * 2
    
    total_w = pad_x + ow + gap + nw + gap + s_pill_w + pad_x
    max_h = max(oh, nh, s_pill_h)
    total_h = max_h + pad_y * 2
    
    draw = ImageDraw.Draw(im)
    draw.rounded_rectangle([x - 2, y - 2, x + total_w + 2, y + total_h + 2], radius=radius + 2, fill=border_color)
    draw.rounded_rectangle([x, y, x + total_w, y + total_h], radius=radius, fill=bg)
    
    cur_x = x + pad_x
    old_y = y + (total_h - oh) // 2 - obbox[1]
    draw.text((cur_x - obbox[0], old_y), old_price, font=f_old, fill=(155, 160, 175))
    
    line_y = y + total_h // 2
    draw.line([(cur_x - 3, line_y + 5), (cur_x + ow + 3, line_y - 5)], fill=(235, 30, 30), width=4)
    
    cur_x += ow + gap
    new_y = y + (total_h - nh) // 2 - nbbox[1]
    draw.text((cur_x - nbbox[0], new_y), new_price, font=f_new, fill=(255, 230, 0))
    
    cur_x += nw + gap
    s_pill_y = y + (total_h - s_pill_h) // 2
    draw.rounded_rectangle([cur_x, s_pill_y, cur_x + s_pill_w, s_pill_y + s_pill_h], radius=8, fill=(185, 28, 28))
    s_text_y = s_pill_y + s_pad_y - sbbox[1]
    draw.text((cur_x + s_pad_x - sbbox[0], s_text_y), savings_label, font=f_save, fill=(255, 255, 255))
    return total_w, total_h

def draw_muapi_text(draw: ImageDraw.ImageDraw, x: int, y: int, items: List[Tuple[str, ImageFont.ImageFont, Tuple[int, int, int]]],
                    stroke_w: int = 14, shadow_dist: int = 9, line_spacing: int = 16):
    """Pila tipográfica de alto impacto con trazo negro grueso y sombra dura para móvil."""
    cur_y = y
    for text, fnt, col in items:
        bbox = fnt.getbbox(text)
        th = bbox[3] - bbox[1]
        
        # Sombra dura exterior
        if shadow_dist > 0:
            for dx in range(-stroke_w, stroke_w + 1):
                for dy in range(-stroke_w, stroke_w + 1):
                    draw.text((x + shadow_dist + dx - bbox[0], cur_y + shadow_dist + dy - bbox[1]), text, font=fnt, fill=(0, 0, 0, 255))
        # Contorno negro macizo
        for dx in range(-stroke_w, stroke_w + 1):
            for dy in range(-stroke_w, stroke_w + 1):
                if dx*dx + dy*dy <= stroke_w*stroke_w:
                    draw.text((x + dx - bbox[0], cur_y + dy - bbox[1]), text, font=fnt, fill=(0, 0, 0, 255))
        # Relleno del color seleccionado
        draw.text((x - bbox[0], cur_y - bbox[1]), text, font=fnt, fill=col)
        cur_y += th + line_spacing

def create_contact_shadow(product_bbox: Tuple[int, int, int, int], canvas_size: Tuple[int, int] = (W, H),
                          intensity: int = 180, blur_radius: int = 18) -> Image.Image:
    """
    Genera una sombra elíptica fotorrealista deformada matemáticamente bajo la base del producto.
    product_bbox: (x, y, w, h). Solape de 12px dentro del borde inferior para evitar flotación.
    """
    px, py, pw, ph = product_bbox
    shadow_layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    d = ImageDraw.Draw(shadow_layer)

    base_center_x = px + pw // 2
    # Solapamiento exacto de 12px dentro del borde inferior del producto
    base_center_y = py + ph - 12

    # 1. Capa de Oclusión Ambiental Profunda (muy oscura, estrecha, contacto directo)
    occ_rx = int(pw * 0.40)
    occ_ry = max(8, int(ph * 0.045))
    d.ellipse([base_center_x - occ_rx, base_center_y - occ_ry,
               base_center_x + occ_rx, base_center_y + occ_ry],
              fill=(0, 0, 0, min(255, int(intensity * 1.15))))

    # 2. Capa de Contacto Directo Principal
    main_rx = int(pw * 0.48)
    main_ry = max(14, int(ph * 0.085))
    d.ellipse([base_center_x - main_rx, base_center_y - main_ry,
               base_center_x + main_rx, base_center_y + main_ry],
              fill=(0, 0, 0, intensity))

    # 3. Capa de Dispersión Suave (degradado hacia los extremos)
    disp_rx = int(pw * 0.58)
    disp_ry = max(20, int(ph * 0.13))
    d.ellipse([base_center_x - disp_rx, base_center_y - disp_ry,
               base_center_x + disp_rx, base_center_y + disp_ry],
              fill=(0, 0, 0, int(intensity * 0.45)))

    return shadow_layer.filter(ImageFilter.GaussianBlur(blur_radius))

def create_product_glow(px: int, py: int, pw: int, ph: int, color: Tuple[int, int, int, int],
                        blur_r: int = 65, core_scale: float = 0.5, outer_scale: float = 1.1) -> Image.Image:
    """Calcula matemáticamente el halo de luz concéntrico exactamente tras el producto."""
    cx = px + pw // 2
    cy = py + ph // 2
    rx = int(pw * outer_scale * 0.5)
    ry = int(ph * outer_scale * 0.5)
    
    glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=color)
    
    core_r_x = int(rx * core_scale)
    core_r_y = int(ry * core_scale)
    core_col = (
        min(255, color[0] + 35),
        min(255, color[1] + 35),
        min(255, color[2] + 35),
        min(255, int(color[3] * 1.4))
    )
    d.ellipse([cx - core_r_x, cy - core_r_y, cx + core_r_x, cy + core_r_y], fill=core_col)
    return glow.filter(ImageFilter.GaussianBlur(blur_r))

def create_niche_background(niche: str = "general", canvas_size: Tuple[int, int] = (W, H)) -> Image.Image:
    """
    Fondos atmosféricos específicos por nicho:
    1. Intenta generar un fondo cinemático 3D fotorrealista con ComfyUI local (AMD ROCm).
    2. Fallback resiliente a fondo procedimental 2D si ComfyUI está apagado o excede timeout.
    """
    cw, ch = canvas_size
    n_lower = str(niche).lower()

    # 1. Intento de fondo cinemático IA con ComfyUI local (fallback 100% seguro)
    if os.environ.get("USE_COMFYUI_BACKDROP", "1").lower() in ("1", "true", "yes"):
        try:
            tools_dir = os.path.dirname(os.path.abspath(__file__))
            if tools_dir not in sys.path:
                sys.path.insert(0, tools_dir)
            from comfyui_backdrop_generator import generate_niche_backdrop
            backdrop_path = generate_niche_backdrop(niche, target_size=canvas_size)
            if backdrop_path and os.path.exists(backdrop_path):
                ai_bg = Image.open(backdrop_path).convert("RGBA")
                if ai_bg.size != canvas_size:
                    ai_bg = ai_bg.resize(canvas_size, Image.Resampling.LANCZOS)
                
                # Gradiente viñeta oscuro lateral izquierdo para garantizar contraste del texto/título (Mobile-First)
                overlay = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
                d_over = ImageDraw.Draw(overlay)
                vignette_w = int(cw * 0.46)  # de X=0 a X≈580px
                for x in range(vignette_w):
                    ratio = (1.0 - (x / vignette_w)) ** 1.25
                    alpha = int(200 * ratio)  # Hasta 78% opacidad en el borde izquierdo
                    d_over.line([(x, 0), (x, ch)], fill=(0, 0, 0, alpha))
                
                # Viñeta oscura inferior para anclaje de productos y sombras de contacto
                vignette_h = int(ch * 0.25)
                y_start = ch - vignette_h
                for y in range(y_start, ch):
                    alpha = int(130 * ((y - y_start) / vignette_h))
                    d_over.line([(0, y), (cw, y)], fill=(0, 0, 0, alpha))
                
                return Image.alpha_composite(ai_bg, overlay)
        except Exception as e:
            logger.debug("[thumbnail_engine] Fallback a fondo 2D procedimental: %s", e)
    
    if any(k in n_lower for k in ["taller", "bricolaje", "herramienta"]):
        bg = Image.new("RGBA", canvas_size, (16, 17, 20, 255))
        draw = ImageDraw.Draw(bg)
        step = 32
        for gx in range(20, cw, step):
            for gy in range(20, ch, step):
                draw.ellipse([gx - 2, gy - 2, gx + 2, gy + 2], fill=(8, 9, 11, 230))
                draw.ellipse([gx - 1, gy - 1, gx + 1, gy + 1], fill=(4, 5, 6, 255))
                draw.point((gx, gy + 3), fill=(40, 42, 48, 120))
        spot = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        d_spot = ImageDraw.Draw(spot)
        d_spot.ellipse([cw // 2 - 450, -150, cw // 2 + 450, ch - 80], fill=(245, 166, 35, 80))
        d_spot.ellipse([cw // 2 - 200, -50, cw // 2 + 200, ch // 2 + 50], fill=(255, 195, 80, 55))
        spot = spot.filter(ImageFilter.GaussianBlur(95))
        return Image.alpha_composite(bg, spot)

    elif any(k in n_lower for k in ["barber", "afeitad", "pelo", "cabello"]):
        bg = Image.new("RGBA", canvas_size, (15, 15, 17, 255))
        spot = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        d_spot = ImageDraw.Draw(spot)
        d_spot.ellipse([cw - 600, -100, cw + 200, ch - 50], fill=(212, 175, 55, 70))
        d_spot.ellipse([cw - 400, 50, cw, ch // 2], fill=(245, 215, 110, 50))
        d_spot.ellipse([-150, 100, 400, ch], fill=(120, 95, 30, 40))
        spot = spot.filter(ImageFilter.GaussianBlur(110))
        return Image.alpha_composite(bg, spot)

    elif any(k in n_lower for k in ["zapateria", "calzado", "zapatill", "running"]):
        bg = Image.new("RGBA", canvas_size, (14, 16, 22, 255))
        spot = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        d_spot = ImageDraw.Draw(spot)
        d_spot.ellipse([cw - 500, -100, cw + 200, ch], fill=(0, 200, 255, 60))
        d_spot.ellipse([cw // 2, 50, cw + 100, ch - 50], fill=(255, 215, 0, 45))
        spot = spot.filter(ImageFilter.GaussianBlur(100))
        return Image.alpha_composite(bg, spot)

    elif any(k in n_lower for k in ["cocina", "receta", "electro"]):
        bg = Image.new("RGBA", canvas_size, (18, 16, 15, 255))
        spot = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        d_spot = ImageDraw.Draw(spot)
        d_spot.ellipse([cw - 550, -100, cw + 150, ch], fill=(240, 140, 30, 65))
        spot = spot.filter(ImageFilter.GaussianBlur(100))
        return Image.alpha_composite(bg, spot)

    else:
        bg = Image.new("RGBA", canvas_size, (14, 15, 18, 255))
        spot = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        d_spot = ImageDraw.Draw(spot)
        d_spot.ellipse([cw - 500, -50, cw + 200, ch], fill=(255, 215, 0, 50))
        spot = spot.filter(ImageFilter.GaussianBlur(100))
        return Image.alpha_composite(bg, spot)

def sanitize_text(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"[^\w\s\d\-_·:¿?¡!€$%&/().,+*áéíóúÁÉÍÓÚñÑüÜ]", "", str(text))
    return re.sub(r"\s+", " ", cleaned).strip()

def level_shoe_product(pil_img: Image.Image) -> Image.Image:
    """Nivela calzado con inclinación excesiva para un asentamiento natural horizontal (≤ 8º)."""
    try:
        import numpy as np
        if pil_img.mode != "RGBA":
            pil_img = pil_img.convert("RGBA")
        alpha = np.array(pil_img)[:, :, 3]
        y_coords, x_coords = np.where(alpha > 100)
        if len(x_coords) < 100:
            return pil_img
        coords = np.vstack([x_coords - np.mean(x_coords), y_coords - np.mean(y_coords)])
        cov = np.cov(coords)
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        vx, vy = eigenvectors[:, 1]
        angle_deg = np.degrees(np.arctan2(float(vy), float(vx)))
        if angle_deg > 90:
            angle_deg -= 180
        elif angle_deg < -90:
            angle_deg += 180
        if abs(angle_deg) > 15:
            target = -6.0 if angle_deg < 0 else 6.0
            rotation = angle_deg - target
            rotated = pil_img.rotate(rotation, resample=Image.Resampling.BICUBIC, expand=True)
            bbox = rotated.getbbox()
            return rotated.crop(bbox) if bbox else rotated
    except Exception as e:
        logger.debug("[level_shoe_product] %s", e)
    return pil_img

def smart_exterior_cutout(pil_img: Image.Image) -> Image.Image:
    """Recorte inteligente de fondo blanco y sombras de suelo mediante rembg AI con fallback morfológico."""
    # 1. Si ya viene con canal alfa y tiene zonas transparentes significativas (>5%), recortar bbox directo
    if pil_img.mode == "RGBA":
        try:
            import numpy as np
            alpha_ch = np.array(pil_img)[:, :, 3]
            if np.mean(alpha_ch < 240) > 0.05:
                bbox = pil_img.getbbox()
                return pil_img.crop(bbox) if bbox else pil_img
        except Exception:
            pass

    # 2. IA de segmentación rembg (elimina sombras de suelo, reflejos de mesa y halos)
    try:
        import rembg
        res = rembg.remove(pil_img)
        bbox = res.getbbox()
        if bbox:
            cropped = res.crop(bbox)
            # Limpieza fina de base inferior (autocrop de restos residuales semitransparentes en base)
            import numpy as np
            arr_a = np.array(cropped)
            if arr_a.shape[0] > 10 and arr_a.shape[2] == 4:
                bottom_alpha = arr_a[-2:, :, 3]
                if np.mean(bottom_alpha > 0) < 0.20:
                    cropped = cropped.crop((0, 0, cropped.width, cropped.height - 2))
            return cropped
    except Exception as e:
        logger.debug("[smart_exterior_cutout] rembg fallback a scipy: %s", e)

    # 3. Fallback morfológico scipy
    try:
        import numpy as np
        from scipy.ndimage import label, binary_dilation
        
        img = pil_img.convert("RGB")
        w, h = img.size
        arr = np.array(img)
        is_white = (arr[:, :, 0] > 230) & (arr[:, :, 1] > 230) & (arr[:, :, 2] > 230)
        labeled, _ = label(is_white)
        
        border_labels = set()
        border_labels.update(labeled[0, :])
        border_labels.update(labeled[h - 1, :])
        border_labels.update(labeled[:, 0])
        border_labels.update(labeled[:, w - 1])
        border_labels.discard(0)
        
        bg_mask = np.isin(labeled, list(border_labels))
        bg_mask = binary_dilation(bg_mask, iterations=2)
        prod_mask = ~bg_mask
        
        alpha = (prod_mask.astype(np.uint8) * 255)
        alpha_img = Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(0.8))
        
        res = img.convert("RGBA")
        res.putalpha(alpha_img)
        bbox = res.getbbox()
        return res.crop(bbox) if bbox else res
    except Exception:
        raw = pil_img.convert("RGBA")
        datas = raw.getdata()
        newData = []
        for item in datas:
            if item[0] > 235 and item[1] > 235 and item[2] > 235:
                newData.append((255, 255, 255, 0))
            else:
                newData.append(item)
        raw.putdata(newData)
        bbox = raw.getbbox()
        return raw.crop(bbox) if bbox else raw

def enhance_img(img: Image.Image, sat: float = 1.35, cont: float = 1.25) -> Image.Image:
    enh_s = ImageEnhance.Color(img.convert("RGB"))
    img_s = enh_s.enhance(sat)
    enh_c = ImageEnhance.Contrast(img_s)
    img_c = enh_c.enhance(cont)
    if img.mode == "RGBA":
        r, g, b = img_c.split()
        return Image.merge("RGBA", (r, g, b, img.split()[3]))
    return img_c

def _get_active_campaign():
    try:
        from campaign_manager import get_active_campaign
        return get_active_campaign()
    except Exception:
        return None

# ==============================================================================
# LAS 5 PLANTILLAS SELECCIONADAS PARA FORMATO VS (CON PRICE CLASH Y SOMBRA)
# ==============================================================================

def render_vs_template_1(img_a, img_b, brand_a, brand_b, camp, niche, price_a="", price_b=""):
    """VS-01: Neon Clash (Oro vs Cian, Sombra fotorrealista y Choque de Precios)."""
    im = create_niche_background(niche)
    
    p1 = enhance_img(img_a).copy()
    p1.thumbnail((360, 360), Image.Resampling.LANCZOS)
    p1_x, p1_y = 510, 180
    p1_w, p1_h = p1.size
    
    p2 = enhance_img(img_b).copy()
    p2.thumbnail((360, 360), Image.Resampling.LANCZOS)
    p2_x, p2_y = 890, 180
    p2_w, p2_h = p2.size
    
    shadow1 = create_contact_shadow((p1_x, p1_y, p1_w, p1_h), (W, H), intensity=180, blur_radius=18)
    shadow2 = create_contact_shadow((p2_x, p2_y, p2_w, p2_h), (W, H), intensity=180, blur_radius=18)
    im = Image.alpha_composite(im, shadow1)
    im = Image.alpha_composite(im, shadow2)

    glow1 = create_product_glow(p1_x, p1_y, p1_w, p1_h, (255, 200, 0, 85), blur_r=70)
    glow2 = create_product_glow(p2_x, p2_y, p2_w, p2_h, (0, 210, 255, 85), blur_r=70)
    im = Image.alpha_composite(im, glow1)
    im = Image.alpha_composite(im, glow2)
    im.paste(p1, (p1_x, p1_y), p1)
    im.paste(p2, (p2_x, p2_y), p2)
    
    # Choque de Precios en base
    pa_str = format_clean_price(price_a, "79€")
    pb_str = format_clean_price(price_b, "129€")
    draw_pill_smart(im, p1_x + (p1_w - 130)//2, p1_y + p1_h - 25, pa_str, get_font(38),
                    bg=(240, 160, 10), fg=(0, 0, 0), pad=(16, 6), radius=10, border_color=(255, 255, 255), border_w=2)
    draw_pill_smart(im, p2_x + (p2_w - 130)//2, p2_y + p2_h - 25, pb_str, get_font(38),
                    bg=(0, 180, 230), fg=(0, 0, 0), pad=(16, 6), radius=10, border_color=(255, 255, 255), border_w=2)
    
    draw_pill_smart(im, 845, 290, "⚔️", get_font(52), bg=(20, 20, 25), fg=(255, 230, 0), pad=(14, 6), radius=16, border_color=(255, 215, 0), border_w=2)
    draw_decision_badge(im, "winner", 50, 70)
    
    # Titular principal (3 PALABRAS)
    draw = ImageDraw.Draw(im)
    text_items = [
        ("DUELO", get_font(120), (255, 255, 255)),
        ("DEFINITIVO", get_font(130), (255, 230, 0))
    ]
    draw_muapi_text(draw, 50, 160, text_items, stroke_w=14, shadow_dist=10)
    draw_pill_smart(im, 50, 560, "¿CUÁL MERECE LA PENA?", get_font(26), bg=(20, 24, 30), fg=(255, 255, 255), pad=(16, 6), radius=8)
    return im.convert("RGB")

def render_vs_template_2(img_a, img_b, brand_a, brand_b, camp, niche, price_a="", price_b=""):
    """VS-02: Loss Aversion / Dilema ('ERROR FATAL')."""
    im = create_niche_background(niche)
    
    p1 = enhance_img(img_a).copy()
    p1.thumbnail((360, 360), Image.Resampling.LANCZOS)
    p1_x, p1_y = 510, 180
    p1_w, p1_h = p1.size
    
    p2 = enhance_img(img_b).copy()
    p2.thumbnail((360, 360), Image.Resampling.LANCZOS)
    p2_x, p2_y = 890, 180
    p2_w, p2_h = p2.size
    
    shadow1 = create_contact_shadow((p1_x, p1_y, p1_w, p1_h), (W, H), intensity=180, blur_radius=18)
    shadow2 = create_contact_shadow((p2_x, p2_y, p2_w, p2_h), (W, H), intensity=180, blur_radius=18)
    im = Image.alpha_composite(im, shadow1)
    im = Image.alpha_composite(im, shadow2)

    glow1 = create_product_glow(p1_x, p1_y, p1_w, p1_h, (255, 40, 40, 85), blur_r=70)
    glow2 = create_product_glow(p2_x, p2_y, p2_w, p2_h, (255, 200, 0, 75), blur_r=70)
    im = Image.alpha_composite(im, glow1)
    im = Image.alpha_composite(im, glow2)
    im.paste(p1, (p1_x, p1_y), p1)
    im.paste(p2, (p2_x, p2_y), p2)
    
    pa_str = format_clean_price(price_a, "49€")
    pb_str = format_clean_price(price_b, "89€")
    draw_pill_smart(im, p1_x + (p1_w - 130)//2, p1_y + p1_h - 25, pa_str, get_font(38),
                    bg=(220, 30, 30), fg=(255, 255, 255), pad=(16, 6), radius=10, border_color=(255, 255, 255), border_w=2)
    draw_pill_smart(im, p2_x + (p2_w - 130)//2, p2_y + p2_h - 25, pb_str, get_font(38),
                    bg=(0, 200, 100), fg=(0, 0, 0), pad=(16, 6), radius=10, border_color=(255, 255, 255), border_w=2)
    
    draw_pill_smart(im, 845, 290, "VS", get_font(46), bg=(20, 20, 25), fg=(255, 255, 255), pad=(14, 6), radius=14, border_color=(235, 30, 30), border_w=2)
    draw_decision_badge(im, "warning", 50, 70)
        
    draw = ImageDraw.Draw(im)
    text_items = [
        ("¡NO ELIJAS", get_font(115), (255, 255, 255)),
        ("A CIEGAS!", get_font(125), (255, 50, 50))
    ]
    draw_muapi_text(draw, 50, 160, text_items, stroke_w=14, shadow_dist=10)
    draw_pill_smart(im, 50, 560, "UNA DE ELLAS TIENE TRAMPA", get_font(26), bg=(35, 20, 20), fg=(255, 100, 100), pad=(16, 6), radius=8)
    return im.convert("RGB")

def render_vs_template_3(img_a, img_b, brand_a, brand_b, camp, niche, price_a="", price_b=""):
    """VS-03: Sello Veredicto ('EL VEREDICTO')."""
    im = create_niche_background(niche)
    
    p1 = enhance_img(img_a).copy()
    p1.thumbnail((360, 360), Image.Resampling.LANCZOS)
    p1_x, p1_y = 510, 180
    p1_w, p1_h = p1.size
    
    p2 = enhance_img(img_b).copy()
    p2.thumbnail((360, 360), Image.Resampling.LANCZOS)
    p2_x, p2_y = 890, 180
    p2_w, p2_h = p2.size
    
    shadow1 = create_contact_shadow((p1_x, p1_y, p1_w, p1_h), (W, H), intensity=180, blur_radius=18)
    shadow2 = create_contact_shadow((p2_x, p2_y, p2_w, p2_h), (W, H), intensity=180, blur_radius=18)
    im = Image.alpha_composite(im, shadow1)
    im = Image.alpha_composite(im, shadow2)

    glow1 = create_product_glow(p1_x, p1_y, p1_w, p1_h, (255, 215, 0, 75), blur_r=70)
    glow2 = create_product_glow(p2_x, p2_y, p2_w, p2_h, (255, 215, 0, 75), blur_r=70)
    im = Image.alpha_composite(im, glow1)
    im = Image.alpha_composite(im, glow2)
    im.paste(p1, (p1_x, p1_y), p1)
    im.paste(p2, (p2_x, p2_y), p2)
    
    pa_str = format_clean_price(price_a, "89€")
    pb_str = format_clean_price(price_b, "149€")
    draw_pill_smart(im, p1_x + (p1_w - 130)//2, p1_y + p1_h - 25, pa_str, get_font(38),
                    bg=(30, 35, 45), fg=(255, 255, 255), pad=(16, 6), radius=10, border_color=(255, 215, 0), border_w=2)
    draw_pill_smart(im, p2_x + (p2_w - 130)//2, p2_y + p2_h - 25, pb_str, get_font(38),
                    bg=(30, 35, 45), fg=(255, 255, 255), pad=(16, 6), radius=10, border_color=(255, 215, 0), border_w=2)
    
    draw_pill_smart(im, 845, 290, "VS", get_font(46), bg=(20, 20, 25), fg=(255, 215, 0), pad=(14, 6), radius=14, border_color=(255, 215, 0), border_w=2)
    draw_pill_smart(im, 50, 70, "⚖️ COMPARATIVA REAL", get_font(30), bg=(255, 215, 0), fg=(0, 0, 0), pad=(18, 6), radius=10)
        
    draw = ImageDraw.Draw(im)
    text_items = [
        ("EL GRAN", get_font(120), (255, 255, 255)),
        ("VEREDICTO", get_font(130), (255, 230, 0))
    ]
    draw_muapi_text(draw, 50, 160, text_items, stroke_w=14, shadow_dist=10)
    draw_pill_smart(im, 50, 560, "TRAS 30 DÍAS DE PRUEBA", get_font(26), bg=(25, 28, 35), fg=(255, 215, 0), pad=(16, 6), radius=8)
    return im.convert("RGB")

def render_vs_template_4(img_a, img_b, brand_a, brand_b, camp, niche, price_a="", price_b=""):
    """VS-04: Test de Potencia ('TEST DE POTENCIA')."""
    im = create_niche_background(niche)
    
    p1 = enhance_img(img_a).copy()
    p1.thumbnail((360, 360), Image.Resampling.LANCZOS)
    p1_x, p1_y = 510, 180
    p1_w, p1_h = p1.size
    
    p2 = enhance_img(img_b).copy()
    p2.thumbnail((360, 360), Image.Resampling.LANCZOS)
    p2_x, p2_y = 890, 180
    p2_w, p2_h = p2.size
    
    shadow1 = create_contact_shadow((p1_x, p1_y, p1_w, p1_h), (W, H), intensity=180, blur_radius=18)
    shadow2 = create_contact_shadow((p2_x, p2_y, p2_w, p2_h), (W, H), intensity=180, blur_radius=18)
    im = Image.alpha_composite(im, shadow1)
    im = Image.alpha_composite(im, shadow2)

    glow1 = create_product_glow(p1_x, p1_y, p1_w, p1_h, (255, 60, 0, 80), blur_r=70)
    glow2 = create_product_glow(p2_x, p2_y, p2_w, p2_h, (0, 160, 255, 80), blur_r=70)
    im = Image.alpha_composite(im, glow1)
    im = Image.alpha_composite(im, glow2)
    im.paste(p1, (p1_x, p1_y), p1)
    im.paste(p2, (p2_x, p2_y), p2)
    
    pa_str = format_clean_price(price_a, "59€")
    pb_str = format_clean_price(price_b, "119€")
    draw_pill_smart(im, p1_x + (p1_w - 130)//2, p1_y + p1_h - 25, pa_str, get_font(38),
                    bg=(240, 40, 10), fg=(255, 255, 255), pad=(16, 6), radius=10, border_color=(255, 255, 255), border_w=2)
    draw_pill_smart(im, p2_x + (p2_w - 130)//2, p2_y + p2_h - 25, pb_str, get_font(38),
                    bg=(0, 130, 240), fg=(255, 255, 255), pad=(16, 6), radius=10, border_color=(255, 255, 255), border_w=2)
    
    draw_pill_smart(im, 845, 290, "VS", get_font(46), bg=(20, 20, 25), fg=(255, 255, 255), pad=(14, 6), radius=14, border_color=(255, 100, 0), border_w=2)
    draw_pill_smart(im, 50, 70, "⚡ CHOQUE DIRECTO", get_font(30), bg=(255, 100, 0), fg=(255, 255, 255), pad=(18, 6), radius=10)
        
    draw = ImageDraw.Draw(im)
    text_items = [
        ("TEST DE", get_font(115), (255, 255, 255)),
        ("POTENCIA", get_font(125), (255, 230, 0)),
        ("2026", get_font(105), (255, 255, 255))
    ]
    draw_muapi_text(draw, 50, 150, text_items, stroke_w=14, shadow_dist=10)
    draw_pill_smart(im, 50, 560, "¿SE NOTA LA DIFERENCIA?", get_font(26), bg=(30, 30, 40), fg=(255, 255, 255), pad=(16, 6), radius=8)
    return im.convert("RGB")

def render_vs_template_5(img_a, img_b, brand_a, brand_b, camp, niche, price_a="", price_b=""):
    """VS-05: Showdown Round Final ('BATALLA FINAL')."""
    im = create_niche_background(niche)
    
    p1 = enhance_img(img_a).copy()
    p1.thumbnail((360, 360), Image.Resampling.LANCZOS)
    p1_x, p1_y = 510, 180
    p1_w, p1_h = p1.size
    
    p2 = enhance_img(img_b).copy()
    p2.thumbnail((360, 360), Image.Resampling.LANCZOS)
    p2_x, p2_y = 890, 180
    p2_w, p2_h = p2.size
    
    shadow1 = create_contact_shadow((p1_x, p1_y, p1_w, p1_h), (W, H), intensity=180, blur_radius=18)
    shadow2 = create_contact_shadow((p2_x, p2_y, p2_w, p2_h), (W, H), intensity=180, blur_radius=18)
    im = Image.alpha_composite(im, shadow1)
    im = Image.alpha_composite(im, shadow2)

    glow1 = create_product_glow(p1_x, p1_y, p1_w, p1_h, (255, 215, 0, 75), blur_r=70)
    glow2 = create_product_glow(p2_x, p2_y, p2_w, p2_h, (255, 215, 0, 75), blur_r=70)
    im = Image.alpha_composite(im, glow1)
    im = Image.alpha_composite(im, glow2)
    im.paste(p1, (p1_x, p1_y), p1)
    im.paste(p2, (p2_x, p2_y), p2)
    
    pa_str = format_clean_price(price_a, "69€")
    pb_str = format_clean_price(price_b, "99€")
    draw_pill_smart(im, p1_x + (p1_w - 130)//2, p1_y + p1_h - 25, pa_str, get_font(38),
                    bg=(20, 20, 25), fg=(255, 215, 0), pad=(16, 6), radius=10, border_color=(255, 215, 0), border_w=2)
    draw_pill_smart(im, p2_x + (p2_w - 130)//2, p2_y + p2_h - 25, pb_str, get_font(38),
                    bg=(20, 20, 25), fg=(255, 215, 0), pad=(16, 6), radius=10, border_color=(255, 215, 0), border_w=2)
    
    draw_pill_smart(im, 845, 290, "VS", get_font(46), bg=(0, 0, 0), fg=(255, 230, 0), pad=(14, 6), radius=14, border_color=(255, 230, 0), border_w=3)
    draw_pill_smart(im, 50, 70, "🔥 ROUND FINAL", get_font(30), bg=(255, 215, 0), fg=(0, 0, 0), pad=(18, 6), radius=10)
        
    draw = ImageDraw.Draw(im)
    text_items = [
        ("BATALLA", get_font(110), (255, 255, 255)),
        ("TOTAL", get_font(115), (255, 230, 0)),
        ("2026", get_font(110), (255, 255, 255))
    ]
    draw_muapi_text(draw, 50, 150, text_items, stroke_w=14, shadow_dist=10)
    draw_pill_smart(im, 50, 560, "¿QUIÉN MANDA HOY?", get_font(26), bg=(25, 30, 35), fg=(255, 230, 0), pad=(16, 6), radius=8)
    return im.convert("RGB")

# ==============================================================================
# LAS 5 PLANTILLAS SELECCIONADAS PARA FORMATO TOP (CON SOMBRA Y BADGES)
# ==============================================================================

def render_top_template_1(hero_img, category_words, camp, niche="cocina"):
    """TOP-01: Dominant Hero King ('ESTA ES LA MEJOR'). Mobile First agresivo."""
    im = create_niche_background(niche)
    
    bbox = hero_img.getbbox()
    p = hero_img.crop(bbox) if bbox else hero_img
    p = enhance_img(p).copy()
    p.thumbnail((720, 520), Image.Resampling.LANCZOS)
    pw, ph = p.size
    
    px = max(520, min(1260 - pw, 920 - pw // 2))
    py = 620 - ph
    
    # Sombra de contacto fotorrealista anclada (solape 12px)
    shadow = create_contact_shadow((px, py, pw, ph), (W, H), intensity=180, blur_radius=18)
    im = Image.alpha_composite(im, shadow)

    glow = create_product_glow(px, py, pw, ph, (255, 180, 20, 85), blur_r=75, outer_scale=1.2)
    im = Image.alpha_composite(im, glow)
    im.paste(p, (px, py), p)
    
    draw_decision_badge(im, "top1", 60, 70)
    draw_pill_smart(im, 60, 545, "✔ CALIDAD / PRECIO IMBATIBLE", get_font(28), bg=(0, 200, 85), fg=(0, 0, 0), pad=(18, 6), radius=10)
    draw_pill_smart(im, 980, 70, "#1 RECOMENDADA", get_font(32), bg=(255, 210, 0), fg=(0, 0, 0), pad=(16, 6), radius=12)
    
    # Titular principal (4 PALABRAS)
    draw = ImageDraw.Draw(im)
    text_items = [
        ("ESTA ES", get_font(115), (255, 255, 255)),
        ("LA MEJOR", get_font(125), (255, 230, 0))
    ]
    draw_muapi_text(draw, 60, 160, text_items, stroke_w=14, shadow_dist=10)
    return im.convert("RGB")

def render_top_template_2(hero_img, category_words, camp, price="", niche="cocina"):
    """TOP-02: Price Drop / Chollo ('EL GRAN CHOLLO'). Mobile First agresivo."""
    im = create_niche_background(niche)
    
    bbox = hero_img.getbbox()
    p = hero_img.crop(bbox) if bbox else hero_img
    p = enhance_img(p).copy()
    p.thumbnail((720, 520), Image.Resampling.LANCZOS)
    pw, ph = p.size
    
    px = max(520, min(1260 - pw, 920 - pw // 2))
    py = 620 - ph
    
    shadow = create_contact_shadow((px, py, pw, ph), (W, H), intensity=180, blur_radius=18)
    im = Image.alpha_composite(im, shadow)

    glow = create_product_glow(px, py, pw, ph, (0, 220, 120, 85), blur_r=75, outer_scale=1.2)
    im = Image.alpha_composite(im, glow)
    im.paste(p, (px, py), p)
    
    draw_decision_badge(im, "winner", 60, 70)
        
    p_val = parse_price_val(price)
    if p_val and p_val > 0:
        new_val = int(round(p_val))
        if new_val < 1:
            new_val = 1
        new_price_str = f"{new_val}€"
        old_val = max(int(round(new_val * 1.40)), new_val + 5)
        old_price_str = f"{old_val}€"
        diff = old_val - new_val
        pct = int(round((diff / old_val) * 100))
        dto_str = f"-{pct}% DTO."
        ahorras_str = f"AHORRAS {diff}€"
    else:
        old_price_str = '189€'
        new_price_str = '79€'
        dto_str = '-58% DTO.'
        ahorras_str = "AHORRAS 110€"

    draw_strikethrough_price_pill(im, 60, 545, old_price_str, new_price_str, dto_str, bg=(14, 25, 20), border_color=(0, 220, 120), radius=12)
    draw_pill_smart(im, 980, 70, ahorras_str, get_font(30), bg=(235, 30, 30), fg=(255, 255, 255), pad=(16, 6), radius=12)
    
    # Titular principal (3 PALABRAS)
    draw = ImageDraw.Draw(im)
    text_items = [
        ("EL GRAN", get_font(120), (255, 255, 255)),
        ("CHOLLO", get_font(135), (255, 230, 0))
    ]
    draw_muapi_text(draw, 60, 160, text_items, stroke_w=14, shadow_dist=10)
    return im.convert("RGB")

def render_top_template_3(hero_img, category_words, camp, num_prods: int = 7, niche="cocina"):
    """TOP-03: Podium Top 3 ('LOS 3 MEJORES')."""
    im = create_niche_background(niche)
    
    bbox = hero_img.getbbox()
    p_base = hero_img.crop(bbox) if bbox else hero_img
    
    p1 = enhance_img(p_base).copy()
    p1.thumbnail((460, 460), Image.Resampling.LANCZOS)
    p1_w, p1_h = p1.size
    p1_x = 740
    p1_y = 620 - p1_h
    
    p2 = p_base.copy().resize((int(p_base.width * 0.72), int(p_base.height * 0.72)), Image.Resampling.LANCZOS)
    p2.thumbnail((350, 350), Image.Resampling.LANCZOS)
    p2_w, p2_h = p2.size
    p2_x = 580
    p2_y = 620 - p2_h
    
    p3 = p_base.copy().resize((int(p_base.width * 0.65), int(p_base.height * 0.65)), Image.Resampling.LANCZOS)
    p3.thumbnail((330, 330), Image.Resampling.LANCZOS)
    p3_w, p3_h = p3.size
    p3_x = 970
    p3_y = 620 - p3_h
    
    # Sombras de contacto ancladas para el podio
    im = Image.alpha_composite(im, create_contact_shadow((p2_x, p2_y, p2_w, p2_h), (W, H), intensity=160, blur_radius=18))
    im = Image.alpha_composite(im, create_contact_shadow((p3_x, p3_y, p3_w, p3_h), (W, H), intensity=160, blur_radius=18))
    im = Image.alpha_composite(im, create_contact_shadow((p1_x, p1_y, p1_w, p1_h), (W, H), intensity=180, blur_radius=20))

    glow = create_product_glow(p1_x, p1_y, p1_w, p1_h, (255, 190, 0, 90), blur_r=80, outer_scale=1.35)
    im = Image.alpha_composite(im, glow)
    im.paste(p2, (p2_x, p2_y), p2)
    im.paste(p3, (p3_x, p3_y), p3)
    im.paste(p1, (p1_x, p1_y), p1)
    
    draw_decision_badge(im, "top1", 60, 70)
    draw_pill_smart(im, 60, 545, "ORO · PLATA · BRONCE", get_font(28), bg=(30, 30, 35), fg=(255, 215, 0), pad=(18, 6), radius=10)
    draw_pill_smart(im, 880, 60, "#1 GANADOR", get_font(32), bg=(255, 215, 0), fg=(0, 0, 0), pad=(16, 6), radius=10)
    
    # Titular principal (3 PALABRAS)
    draw = ImageDraw.Draw(im)
    text_items = [
        ("LOS 3", get_font(120), (255, 255, 255)),
        ("MEJORES", get_font(130), (255, 230, 0)),
        ("DE 2026", get_font(105), (255, 255, 255))
    ]
    draw_muapi_text(draw, 60, 150, text_items, stroke_w=14, shadow_dist=10)
    return im.convert("RGB")

def render_top_template_4(hero_img, category_words, camp, niche="cocina"):
    """TOP-04: Loss Aversion / Warning ('¡NO LA COMPRES AÚN!'). Mobile First agresivo."""
    im = create_niche_background(niche)
    
    bbox = hero_img.getbbox()
    p = hero_img.crop(bbox) if bbox else hero_img
    p = enhance_img(p).copy()
    p.thumbnail((720, 520), Image.Resampling.LANCZOS)
    pw, ph = p.size
    
    px = max(520, min(1260 - pw, 920 - pw // 2))
    py = 620 - ph
    
    shadow = create_contact_shadow((px, py, pw, ph), (W, H), intensity=180, blur_radius=18)
    im = Image.alpha_composite(im, shadow)

    glow = create_product_glow(px, py, pw, ph, (255, 45, 45, 85), blur_r=75, outer_scale=1.2)
    im = Image.alpha_composite(im, glow)
    im.paste(p, (px, py), p)
    
    draw_decision_badge(im, "warning", 60, 70)
    draw_pill_smart(im, 60, 545, "MIRA ESTO ANTES DE PAGAR", get_font(28), bg=(35, 20, 20), fg=(255, 80, 80), pad=(18, 6), radius=10)
    draw_pill_smart(im, 980, 70, "⚠️ AVISO", get_font(32), bg=(235, 30, 30), fg=(255, 255, 255), pad=(16, 6), radius=10)
    
    # Titular principal (4 PALABRAS)
    draw = ImageDraw.Draw(im)
    text_items = [
        ("¡NO LA", get_font(115), (255, 255, 255)),
        ("COMPRES", get_font(125), (255, 50, 50)),
        ("AÚN!", get_font(115), (255, 255, 255))
    ]
    draw_muapi_text(draw, 60, 150, text_items, stroke_w=14, shadow_dist=10)
    return im.convert("RGB")

def render_top_template_5(hero_img, category_words, camp, price="", niche="cocina"):
    """TOP-05: Budget Winner ('TOP CALIDAD PRECIO'). Mobile First agresivo."""
    im = create_niche_background(niche)
    
    bbox = hero_img.getbbox()
    p = hero_img.crop(bbox) if bbox else hero_img
    p = enhance_img(p).copy()
    p.thumbnail((720, 520), Image.Resampling.LANCZOS)
    pw, ph = p.size
    
    px = max(520, min(1260 - pw, 920 - pw // 2))
    py = 620 - ph
    
    shadow = create_contact_shadow((px, py, pw, ph), (W, H), intensity=180, blur_radius=18)
    im = Image.alpha_composite(im, shadow)

    glow = create_product_glow(px, py, pw, ph, (0, 220, 200, 85), blur_r=75, outer_scale=1.2)
    im = Image.alpha_composite(im, glow)
    im.paste(p, (px, py), p)
    
    draw_decision_badge(im, "winner", 60, 70)
        
    p_val = parse_price_val(price)
    if p_val and p_val > 0:
        new_val = int(round(p_val))
        solo_str = f"SOLO {new_val}€"
        if new_val < 30:
            sub_threshold = 30
        elif new_val < 50:
            sub_threshold = 50
        elif new_val < 100:
            sub_threshold = 100
        else:
            sub_threshold = ((new_val // 50) + 1) * 50
        sub_str = f"POR MENOS DE {sub_threshold}€"
    else:
        solo_str = "SOLO 39€"
        sub_str = "POR MENOS DE 50€"

    draw_pill_smart(im, 60, 545, sub_str, get_font(28), bg=(0, 200, 180), fg=(0, 0, 0), pad=(18, 6), radius=10)
    draw_pill_smart(im, 980, 70, solo_str, get_font(32), bg=(255, 230, 0), fg=(0, 0, 0), pad=(16, 6), radius=12)
    
    # Titular principal (3 PALABRAS)
    draw = ImageDraw.Draw(im)
    text_items = [
        ("TOP CALIDAD", get_font(115), (255, 255, 255)),
        ("Y PRECIO", get_font(125), (255, 230, 0))
    ]
    draw_muapi_text(draw, 60, 160, text_items, stroke_w=14, shadow_dist=10)
    return im.convert("RGB")

def render_vs_thumbnail(project_dir: str, output_path: Optional[str] = None,
                        niche: str = "cocina", template_id: Optional[int] = None) -> str:
    """Genera miniatura para comparativas VS con Pillow 2.0 rotando entre las plantillas aprobadas."""
    if not output_path:
        output_path = os.path.join(project_dir, "thumbnail.jpg")
        
    data_file = os.path.join(project_dir, "data.json")
    brand_a, brand_b = "Opción A", "Opción B"
    price_a, price_b = "", ""
    if os.path.exists(data_file):
        try:
            with open(data_file, "r", encoding="utf-8") as f:
                d = json.load(f)
                brand_a = d.get("product_a", {}).get("brand", "Opción A")
                brand_b = d.get("product_b", {}).get("brand", "Opción B")
                price_a = d.get("product_a", {}).get("price", "")
                price_b = d.get("product_b", {}).get("price", "")
                if not niche or niche == "cocina":
                    cand_niche = d.get("canal_niche") or d.get("niche") or d.get("channel_niche")
                    if cand_niche:
                        niche = cand_niche
        except Exception:
            pass
            
    def find_img(folder_names):
        for fol in folder_names:
            p_dir = os.path.join(project_dir, fol)
            if os.path.isdir(p_dir):
                for fn in sorted(os.listdir(p_dir)):
                    if fn.lower().startswith("product") and any(fn.lower().endswith(f".{ext}") for ext in ["png", "jpg", "jpeg", "webp"]):
                        return os.path.join(p_dir, fn)
                for fn in sorted(os.listdir(p_dir)):
                    if any(fn.lower().endswith(f".{ext}") for ext in ["png", "jpg", "jpeg", "webp"]):
                        if "badge" not in fn.lower() and "overlay" not in fn.lower():
                            return os.path.join(p_dir, fn)
            for ext in ["png", "jpg", "jpeg", "webp"]:
                p_direct = os.path.join(project_dir, f"{fol}.{ext}")
                if os.path.exists(p_direct):
                    return p_direct
        # Fallback de búsqueda amplia si folder_names es para A o B
        first_letter = 'a' if any('a' in f or '1' in f for f in folder_names) else 'b'
        for root, dirs, files in os.walk(project_dir):
            for fn in sorted(files):
                if any(fn.lower().endswith(f".{ext}") for ext in ["png", "jpg", "jpeg", "webp"]):
                    if f"_{first_letter}" in fn.lower() and "badge" not in fn.lower():
                        return os.path.join(root, fn)
        return None
    
    p_a_path = find_img(["producto_a", "01_producto_a", "01_producto_1", "product_a"])
    p_b_path = find_img(["producto_b", "02_producto_b", "02_producto_2", "product_b"])
    
    if p_a_path and os.path.exists(p_a_path):
        raw_a = Image.open(p_a_path)
        cut_a = smart_exterior_cutout(raw_a)
    else:
        # Fallback seguro con degradado de silueta
        cut_a = Image.new("RGBA", (360, 360), (40, 42, 48, 255))
        
    if p_b_path and os.path.exists(p_b_path):
        raw_b = Image.open(p_b_path)
        cut_b = smart_exterior_cutout(raw_b)
    else:
        cut_b = Image.new("RGBA", (360, 360), (40, 42, 48, 255))
        
    if any(k in str(niche).lower() for k in ["calzado", "zapateria", "zapatill"]):
        cut_a = level_shoe_product(cut_a)
        cut_b = level_shoe_product(cut_b)
        
    camp = _get_active_campaign()
    
    if template_id is None or template_id not in [1, 2, 3, 4, 5]:
        template_id = random.choice([1, 2, 3, 4, 5])
        
    if template_id == 1:
        final_img = render_vs_template_1(cut_a, cut_b, brand_a, brand_b, camp, niche, price_a, price_b)
    elif template_id == 2:
        final_img = render_vs_template_2(cut_a, cut_b, brand_a, brand_b, camp, niche, price_a, price_b)
    elif template_id == 3:
        final_img = render_vs_template_3(cut_a, cut_b, brand_a, brand_b, camp, niche, price_a, price_b)
    elif template_id == 4:
        final_img = render_vs_template_4(cut_a, cut_b, brand_a, brand_b, camp, niche, price_a, price_b)
    else:
        final_img = render_vs_template_5(cut_a, cut_b, brand_a, brand_b, camp, niche, price_a, price_b)
        
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    final_img.save(output_path, "JPEG", quality=95)
    
    temp_thumb = "/home/javierferb/ia-lab-files/temp_yt_thumbnail.jpg"
    try:
        os.makedirs(os.path.dirname(temp_thumb), exist_ok=True)
        shutil.copyfile(output_path, temp_thumb)
    except Exception:
        pass
        
    print(f"SUCCESS: VS Thumbnail (Template {template_id}, Niche: {niche}) saved to {output_path}")
    return output_path

def render_top_thumbnail(project_dir: str, output_path: Optional[str] = None,
                         template_id: Optional[int] = None, niche: str = "cocina") -> str:
    """Genera miniatura para rankings TOP con Pillow 2.0 rotando entre las plantillas aprobadas."""
    if not output_path:
        output_path = os.path.join(project_dir, "thumbnail.jpg")
        
    data_file = os.path.join(project_dir, "data.json")
    query = ""
    top_price = ""
    num_prods = 7
    if os.path.exists(data_file):
        try:
            with open(data_file, "r", encoding="utf-8") as f:
                d = json.load(f)
                query = d.get("query", "")
                prods = d.get("products", [])
                if isinstance(prods, list) and len(prods) > 0:
                    num_prods = len(prods)
                    if isinstance(prods[0], dict):
                        top_price = str(prods[0].get("price", ""))
                elif isinstance(d.get("product_1"), dict):
                    top_price = str(d.get("product_1", {}).get("price", ""))
                elif isinstance(d.get("product_a"), dict):
                    top_price = str(d.get("product_a", {}).get("price", ""))
                cand_niche = d.get("canal_niche") or d.get("niche") or d.get("channel_niche")
                if cand_niche:
                    niche = cand_niche
        except Exception:
            pass
    if not query and project_dir:
        query = os.path.basename(os.path.normpath(project_dir)).replace("_", " ")
        
    clean_q = sanitize_text(query).upper()
    category_words = clean_q.split() if clean_q else ["PRODUCTOS"]
    
    def find_top_hero_img(pdir):
        subdirs = ["01_producto_1", "producto_1", "01_producto_a", "producto_a", "product_1", "product_a"]
        for sd in subdirs:
            target_dir = os.path.join(pdir, sd)
            if os.path.isdir(target_dir):
                for fn in sorted(os.listdir(target_dir)):
                    if fn.lower().startswith("product") and any(fn.lower().endswith(f".{e}") for e in ["jpg", "jpeg", "png", "webp"]):
                        return os.path.join(target_dir, fn)
                for fn in sorted(os.listdir(target_dir)):
                    if any(fn.lower().endswith(f".{e}") for e in ["jpg", "jpeg", "png", "webp"]):
                        if "badge" not in fn.lower() and "overlay" not in fn.lower():
                            return os.path.join(target_dir, fn)
        for fn in sorted(os.listdir(pdir)):
            if fn.lower().startswith("product") and any(fn.lower().endswith(f".{e}") for e in ["jpg", "jpeg", "png", "webp"]):
                return os.path.join(pdir, fn)
        for root, dirs, files in os.walk(pdir):
            for fn in sorted(files):
                if any(fn.lower().endswith(f".{e}") for e in ["jpg", "jpeg", "png", "webp"]):
                    if "badge" not in fn.lower() and "thumb" not in fn.lower() and "overlay" not in fn.lower():
                        return os.path.join(root, fn)
        return None

    p1_path = find_top_hero_img(project_dir)
    if p1_path:
        raw_hero = Image.open(p1_path)
        cut_hero = smart_exterior_cutout(raw_hero)
    else:
        cut_hero = Image.new("RGBA", (650, 520), (40, 42, 48, 255))
        
    if any(k in str(niche).lower() for k in ["calzado", "zapateria", "zapatill"]):
        cut_hero = level_shoe_product(cut_hero)
        
    camp = _get_active_campaign()
    
    if template_id is None or template_id not in [1, 2, 3, 4, 5]:
        template_id = random.choice([1, 2, 3, 4, 5])
        
    if template_id == 1:
        final_img = render_top_template_1(cut_hero, category_words, camp, niche=niche)
    elif template_id == 2:
        final_img = render_top_template_2(cut_hero, category_words, camp, price=top_price, niche=niche)
    elif template_id == 3:
        final_img = render_top_template_3(cut_hero, category_words, camp, num_prods=num_prods, niche=niche)
    elif template_id == 4:
        final_img = render_top_template_4(cut_hero, category_words, camp, niche=niche)
    else:
        final_img = render_top_template_5(cut_hero, category_words, camp, price=top_price, niche=niche)
        
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    final_img.save(output_path, "JPEG", quality=95)
    
    temp_thumb = "/home/javierferb/ia-lab-files/temp_yt_thumbnail.jpg"
    try:
        os.makedirs(os.path.dirname(temp_thumb), exist_ok=True)
        shutil.copyfile(output_path, temp_thumb)
    except Exception:
        pass
        
    print(f"SUCCESS: TOP Thumbnail (Template {template_id}, Niche: {niche}) saved to {output_path}")
    return output_path

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: thumbnail_engine.py <project_dir> [output_path] [vs|top] [template_id] [niche]", file=sys.stderr)
        sys.exit(1)
        
    p_dir = os.path.abspath(sys.argv[1])
    out_p = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2].strip() else None
    fmt = sys.argv[3].lower() if len(sys.argv) > 3 and sys.argv[3].strip() else "top"
    t_id = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].strip().isdigit() else None
    niche_arg = sys.argv[5].lower() if len(sys.argv) > 5 and sys.argv[5].strip() else "cocina"
    
    if fmt == "vs":
        render_vs_thumbnail(p_dir, out_p, niche=niche_arg, template_id=t_id)
    else:
        render_top_thumbnail(p_dir, out_p, template_id=t_id, niche=niche_arg)
