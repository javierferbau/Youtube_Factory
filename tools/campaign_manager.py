#!/usr/bin/env python3
"""
campaign_manager.py — Motor Autónomo de Campañas Comerciales y Estacionales
Calcula automáticamente las fechas de eventos comerciales (Black Friday, Prime Day, Rebajas, etc.)
y activa campañas exactamente 7 días antes de su inicio (D-7), volviendo solo a modo normal al finalizar.
Aplica de forma centralizada:
- Badges visuales en miniaturas (Pillow)
- Prefijos y hooks en títulos de YouTube (<95 caracteres)
- Tags SEO de alta intención comercial (<480 bytes)
- Información de estado para el reporte matinal de Telegram
"""

import os
import json
import re
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "campaign_config.json")

FONT_PATHS = [
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/TTF/OpenSans-Bold.ttf",
]

def _load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _get_4th_friday(year: int, month: int = 11) -> date:
    """Calcula el 4º viernes de un mes dado (Black Friday)."""
    first_day = date(year, month, 1)
    friday_offset = (4 - first_day.weekday()) % 7
    return first_day + timedelta(days=friday_offset + 21)

def _get_1st_sunday(year: int, month: int = 5) -> date:
    """Calcula el 1er domingo de un mes (Día de la Madre en España)."""
    first_day = date(year, month, 1)
    sun_offset = (6 - first_day.weekday()) % 7
    return first_day + timedelta(days=sun_offset)

def _get_1st_tuesday(year: int, month: int = 10) -> date:
    """Calcula el 1er martes de un mes dado."""
    first_day = date(year, month, 1)
    tue_offset = (1 - first_day.weekday()) % 7
    return first_day + timedelta(days=tue_offset)

def _get_2nd_tuesday(year: int, month: int = 7) -> date:
    """Calcula el 2º martes de un mes (Amazon Prime Day típico)."""
    first_day = date(year, month, 1)
    tue_offset = (1 - first_day.weekday()) % 7
    return first_day + timedelta(days=tue_offset + 7)

def get_registered_campaigns(year: int) -> List[Dict[str, Any]]:
    """Devuelve la definición de todas las campañas estacionales para el año indicado."""
    
    # 1. Black Friday & Cyber Monday
    bf_friday = _get_4th_friday(year, 11)
    cyber_monday = bf_friday + timedelta(days=3)
    bf_start = bf_friday - timedelta(days=7) # D-7

    # 2. Prime Day Verano (mediados de julio)
    prime_tue = _get_2nd_tuesday(year, 7)
    prime_wed = prime_tue + timedelta(days=1)
    prime_start = prime_tue - timedelta(days=7) # D-7

    # 3. Fiesta Ofertas Prime Otoño (6-7 Octubre oficial en 2026, ofertas anticipadas desde 1 Oct)
    prime_oct_tue = _get_1st_tuesday(year, 10)
    prime_oct_wed = prime_oct_tue + timedelta(days=1)
    prime_oct_start = prime_oct_tue - timedelta(days=7) # Activa ofertas anticipadas

    # 4. Día del Padre (19 marzo)
    padre_day = date(year, 3, 19)
    padre_start = padre_day - timedelta(days=7)

    # 5. Día de la Madre (1er domingo de mayo)
    madre_day = _get_1st_sunday(year, 5)
    madre_start = madre_day - timedelta(days=7)

    # 6. Ofertas de Primavera (Amazon Spring Deals: 20-25 marzo)
    spring_start = date(year, 3, 15)
    spring_end = date(year, 3, 25)

    # 7. Vuelta al Cole / Trabajo (01 sep - 15 sep, activa 25 ago - 15 sep)
    cole_start = date(year, 8, 25)
    cole_end = date(year, 9, 15)

    # 8. Navidad y Reyes (20 dic - 05 ene, activa 13 dic - 05 ene)
    navidad_start = date(year, 12, 13)
    navidad_end = date(year, 12, 31)
    reyes_start = date(year, 1, 1)
    reyes_end = date(year, 1, 5)

    # 9. Rebajas de Invierno (01 ene - 15 ene, activa 25 dic - 15 ene)
    rebajas_start = date(year, 1, 1)
    rebajas_end = date(year, 1, 15)

    campaigns = [
        {
            "id": "black_friday",
            "name": f"Black Friday & Cyber Monday {year}",
            "start_date": bf_start,
            "end_date": cyber_monday,
            "badge_text": "ESPECIAL BLACK FRIDAY",
            "badge_bg": (185, 28, 28, 255),       # Crimson Red
            "badge_border": (250, 204, 21, 255),   # Gold
            "badge_text_color": (255, 255, 255),
            "title_prefix": "🔥 [BLACK FRIDAY]",
            "extra_tags": [f"black friday {year}", "ofertas black friday", "chollos black friday", f"cyber monday {year}"]
        },
        {
            "id": "prime_day",
            "name": f"Amazon Prime Day {year}",
            "start_date": prime_start,
            "end_date": prime_wed,
            "badge_text": "ESPECIAL PRIME DAY",
            "badge_bg": (0, 168, 225, 255),       # Amazon Prime Blue
            "badge_border": (250, 204, 21, 255),   # Gold
            "badge_text_color": (255, 255, 255),
            "title_prefix": "⚡ [PRIME DAY]",
            "extra_tags": [f"prime day {year}", "amazon prime day", "ofertas prime day", f"chollos prime day {year}"]
        },
        {
            "id": "fiesta_prime",
            "name": f"Fiesta de Ofertas Prime {year}",
            "start_date": prime_oct_start,
            "end_date": prime_oct_wed,
            "badge_text": "FIESTA DE OFERTAS PRIME",
            "badge_bg": (0, 115, 230, 255),       # Azul Eléctrico Amazon Prime Oficial
            "badge_border": (250, 204, 21, 255),   # Borde Oro #FACC15
            "badge_text_color": (255, 255, 255),
            "title_prefix": "⚡ [OFERTAS PRIME]",
            "extra_tags": ["ofertas prime", "fiesta ofertas prime", "amazon prime ofertas", f"chollos amazon {year}", "ofertas anticipadas"]
        },
        {
            "id": "vuelta_al_cole",
            "name": f"Vuelta al Cole & Trabajo {year}",
            "start_date": cole_start,
            "end_date": cole_end,
            "badge_text": "ESPECIAL VUELTA AL COLE",
            "badge_bg": (250, 204, 21, 255),       # Amarillo Oro Oficial
            "badge_border": (255, 255, 255, 255),   # Borde Blanco
            "badge_text_color": (10, 10, 12),
            "title_prefix": "🎒 [VUELTA AL COLE]",
            "extra_tags": ["vuelta al cole", f"ofertas septiembre {year}", "chollos amazon"]
        },
        {
            "id": "rebajas_enero",
            "name": f"Rebajas de Invierno {year}",
            "start_date": rebajas_start,
            "end_date": rebajas_end,
            "badge_text": "SUPER REBAJAS DE ENERO",
            "badge_bg": (229, 57, 53, 255),       # Red Sale
            "badge_border": (255, 255, 255, 255),
            "badge_text_color": (255, 255, 255),
            "title_prefix": "🏷️ [SUPER REBAJAS]",
            "extra_tags": [f"rebajas {year}", "rebajas de enero", "ofertas y descuentos"]
        },
        {
            "id": "dia_del_padre",
            "name": f"Especial Día del Padre {year}",
            "start_date": padre_start,
            "end_date": padre_day,
            "badge_text": "ESPECIAL DÍA DEL PADRE",
            "badge_bg": (30, 58, 138, 255),       # Deep Blue
            "badge_border": (255, 255, 255, 255),
            "badge_text_color": (10, 10, 12),
            "title_prefix": "👔 [DÍA DEL PADRE]",
            "extra_tags": ["regalos dia del padre", "ideas dia del padre", f"regalos hombre {year}"]
        },
        {
            "id": "dia_de_la_madre",
            "name": f"Especial Día de la Madre {year}",
            "start_date": madre_start,
            "end_date": madre_day,
            "badge_text": "ESPECIAL DÍA DE LA MADRE",
            "badge_bg": (219, 39, 119, 255),      # Pink / Rose
            "badge_border": (255, 255, 255, 255),
            "badge_text_color": (255, 255, 255),
            "title_prefix": "💐 [DÍA DE LA MADRE]",
            "extra_tags": ["regalos dia de la madre", "ideas dia de la madre", f"regalos mujer {year}"]
        },
        {
            "id": "spring_deals",
            "name": f"Ofertas de Primavera {year}",
            "start_date": spring_start,
            "end_date": spring_end,
            "badge_text": "OFERTAS DE PRIMAVERA",
            "badge_bg": (13, 148, 136, 255),      # Teal Spring
            "badge_border": (255, 255, 255, 255),
            "badge_text_color": (10, 10, 12),
            "title_prefix": "🌸 [OFERTAS PRIMAVERA]",
            "extra_tags": ["ofertas de primavera", "amazon spring deals", f"chollos primavera {year}"]
        },
        {
            "id": "navidad",
            "name": f"Especial Regalos Navidad & Reyes {year}",
            "start_date": navidad_start,
            "end_date": navidad_end,
            "badge_text": "GUÍA REGALOS NAVIDAD",
            "badge_bg": (21, 128, 61, 255),       # Christmas Green
            "badge_border": (250, 204, 21, 255),   # Gold
            "badge_text_color": (255, 255, 255),
            "title_prefix": "🎁 [GUÍA REGALOS]",
            "extra_tags": ["regalos de navidad", "ideas regalo reyes", f"mejores regalos {year}"]
        }
    ]
    return campaigns

def get_active_campaign(target_date: Optional[date] = None) -> Optional[Dict[str, Any]]:
    """
    Devuelve la campaña comercial activa para la fecha indicada (o hoy por defecto).
    Si no hay ninguna campaña activa, devuelve None.
    """
    cfg = _load_config()
    if cfg.get("disabled", False):
        return None

    if target_date is None:
        target_date = datetime.now().date()
    elif isinstance(target_date, datetime):
        target_date = target_date.date()

    # 1. Comprobar si hay un override manual forzado en campaign_config.json
    forced_id = cfg.get("force_campaign")
    if forced_id:
        campaigns = get_registered_campaigns(target_date.year)
        for c in campaigns:
            if c["id"] == forced_id:
                res = c.copy()
                res["is_forced"] = True
                res["days_remaining"] = max(0, (c["end_date"] - target_date).days)
                return res

    # 2. Comprobar calendario automático
    campaigns = get_registered_campaigns(target_date.year)
    for c in campaigns:
        if c["start_date"] <= target_date <= c["end_date"]:
            res = c.copy()
            res["is_forced"] = False
            res["days_remaining"] = max(0, (c["end_date"] - target_date).days)
            return res

    return None

def apply_campaign_title(title: str, campaign: Optional[dict] = None, max_len: int = 95) -> str:
    """
    Aplica el prefijo de la campaña al título garantizando el límite de caracteres (<95).
    Si campaign es None, devuelve el título original.
    """
    if not campaign or not campaign.get("title_prefix"):
        return title[:max_len]

    prefix = campaign["title_prefix"].strip()
    clean_t = title.strip()

    # Evitar duplicar el prefijo si ya lo contiene
    if prefix.lower() in clean_t.lower() or campaign.get("id", "") in clean_t.lower():
        return clean_t[:max_len]

    combined = f"{prefix} {clean_t}"
    if len(combined) <= max_len:
        return combined

    # Cortar respetando palabras
    budget = max_len - len(prefix) - 1
    if budget > 20:
        cut_t = clean_t[:budget].rsplit(" ", 1)[0].strip()
        return f"{prefix} {cut_t}"
    return combined[:max_len]

def get_niche_campaign_tags(campaign: Optional[dict], niche: str = "") -> List[str]:
    """
    Genera tags estacionales cruzados de alta intención comercial según el nicho y evento activo.
    """
    if not campaign:
        return []
    cid = campaign.get("id", "").lower()
    year = datetime.now().year
    n_low = (niche or "").lower()
    base_tags = list(campaign.get("extra_tags", []))
    niche_tags = []

    if any(k in n_low for k in ["calzado", "zapateria", "zapatill", "running"]):
        if cid == "black_friday":
            niche_tags = ["ofertas black friday calzado", "zapatillas black friday", "chollos zapatillas running", f"calzado black friday {year}"]
        elif "prime" in cid:
            niche_tags = ["prime day zapatillas", "ofertas calzado amazon", "chollos zapatillas running"]
        elif cid == "rebajas_enero":
            niche_tags = ["rebajas zapatillas", "calzado en rebajas", "ofertas calzado running"]
        else:
            niche_tags = ["ofertas calzado", "chollos zapatillas", "descuentos zapatillas running"]

    elif any(k in n_low for k in ["taller", "bricolaje", "herramienta"]):
        if cid == "black_friday":
            niche_tags = ["black friday herramientas", "taladros black friday", f"chollos bricolaje {year}", "herramientas en oferta"]
        elif "prime" in cid:
            niche_tags = ["prime day herramientas", "taladros prime day", "ofertas bricolaje amazon"]
        else:
            niche_tags = ["ofertas herramientas", "chollos bricolaje", "taladros en oferta"]

    elif any(k in n_low for k in ["barber", "afeitad", "pelo", "cabello"]):
        if cid == "black_friday":
            niche_tags = ["black friday afeitadoras", "cortapelos black friday", "ofertas cuidado barba", f"afeitadoras black friday {year}"]
        elif "prime" in cid:
            niche_tags = ["prime day afeitadoras", "ofertas cortapelos prime", "cuidado barba amazon"]
        else:
            niche_tags = ["ofertas afeitadoras", "chollos cortapelos", "cuidado barba ofertas"]

    elif any(k in n_low for k in ["cocina", "receta", "electro"]):
        if cid == "black_friday":
            niche_tags = ["black friday freidoras de aire", "cafeteras black friday", "chollos cocina amazon", f"electrodomesticos black friday {year}"]
        elif "prime" in cid:
            niche_tags = ["prime day cocina", "cafeteras prime day", "freidoras de aire prime day"]
        else:
            niche_tags = ["ofertas cocina amazon", "chollos electrodomesticos", "descuentos cocina"]

    elif any(k in n_low for k in ["limpieza", "aspirador"]):
        if cid == "black_friday":
            niche_tags = ["black friday aspiradoras", "robot aspirador black friday", "chollos limpieza hogar"]
        elif "prime" in cid:
            niche_tags = ["prime day aspiradoras", "robot aspirador prime day", "ofertas limpieza amazon"]
        else:
            niche_tags = ["ofertas aspiradoras", "chollos robot aspirador", "limpieza hogar ofertas"]

    elif any(k in n_low for k in ["libreria", "libro"]):
        if cid == "black_friday":
            niche_tags = ["libros black friday", "ofertas libros amazon", "novelas recomendadas oferta"]
        else:
            niche_tags = ["ofertas libros", "mejores novelas oferta", "chollos libros amazon"]

    return niche_tags + base_tags

def apply_campaign_tags(tags: List[str], campaign: Optional[dict] = None, max_bytes: int = 475, niche: str = "") -> List[str]:
    """
    Inyecta las etiquetas prioritarias de la campaña (cruzadas por nicho) al principio de la lista de tags
    respetando el límite estricto de bytes de la API de YouTube (default 475 bytes).
    """
    if not campaign:
        return tags

    extra = get_niche_campaign_tags(campaign, niche=niche)
    if not extra:
        extra = campaign.get("extra_tags", [])
    merged = []
    seen = set()

    for t in extra:
        clean = re.sub(r'[^a-zA-Z0-9áéíóúñÁÉÍÓÚÑ -_]', '', str(t)).strip()
        clean = re.sub(r'[^a-zA-Z0-9áéíóúñÁÉÍÓÚÑ\s\-_]', '', clean)
        clean = re.sub(r'\s+', ' ', clean).strip(' ,-_')
        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            merged.append(clean)

    for t in tags:
        clean = re.sub(r'[^a-zA-Z0-9áéíóúñÁÉÍÓÚÑ -_]', '', str(t)).strip()
        clean = re.sub(r'[^a-zA-Z0-9áéíóúñÁÉÍÓÚÑ\s\-_]', '', clean)
        clean = re.sub(r'\s+', ' ', clean).strip(' ,-_')
        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            merged.append(clean)

    final_tags = []
    current_bytes = 0
    for t in merged:
        tag_quote_overhead = 2 if ' ' in t else 0
        added_len = len(t.encode('utf-8')) + tag_quote_overhead + (1 if final_tags else 0)
        if current_bytes + added_len > max_bytes:
            break
        final_tags.append(t)
        current_bytes += added_len

    return final_tags

def get_campaign_vs_header(campaign: Optional[dict], niche: str = "cocina") -> str:
    """
    Devuelve el texto formateado para la cabecera superior en miniaturas VS durante una campaña.
    Garantiza compatibilidad 100% libre de emojis que causen caracteres rotos o tofu boxes.
    """
    if not campaign:
        return ""
    
    cid = campaign.get("id", "").lower()
    name_map = {
        "black_friday": "BLACK FRIDAY",
        "prime_day": "PRIME DAY",
        "fiesta_prime": "FIESTA PRIME",
        "vuelta_al_cole": "VUELTA AL COLE",
        "rebajas_enero": "REBAJAS DE ENERO",
        "dia_del_padre": "DÍA DEL PADRE",
        "dia_de_la_madre": "DÍA DE LA MADRE",
        "spring_deals": "OFERTAS PRIMAVERA",
        "navidad": "REGALOS NAVIDAD",
    }
    short_name = name_map.get(cid)
    if not short_name:
        raw_text = campaign.get("badge_text", "OFERTAS")
        short_name = re.sub(r"[^\w\s\d\-_·:¿?¡!€$%&/().,+*áéíóúÁÉÍÓÚñÑüÜ]", "", raw_text).strip()
        if short_name.startswith("ESPECIAL "):
            short_name = short_name[9:].strip()

    niche_lower = (niche or "").lower()
    if "cocina" in niche_lower:
        return f"{short_name} · ¿CUÁL COMPRAR?"
    elif "limpieza" in niche_lower:
        return f"{short_name} · ¿CUÁL ES MEJOR?"
    elif "libreria" in niche_lower or "libro" in niche_lower:
        return f"{short_name} · ¿QUÉ LIBRO LEER?"
    elif "zapateria" in niche_lower or "calzado" in niche_lower or "zapat" in niche_lower:
        return f"{short_name} · ¿CUÁL ELEGIR?"
    else:
        return f"{short_name} · ¿CUÁL ELEGIR?"

def draw_campaign_badge(image, campaign: Optional[dict] = None, pos_y: int = 25, is_vs: bool = False, niche: str = ""):
    """
    Estampa un badge estilizado de la campaña comercial sobre una imagen Pillow.
    Si campaign es None, devuelve la imagen sin tocar.
    Garantiza compatibilidad tipográfica 100% libre de caracteres emoji no soportados.
    """
    if not campaign or not campaign.get("badge_text"):
        return image

    try:
        from PIL import ImageDraw, ImageFont
    except ImportError:
        return image

    raw_text = str(campaign.get("badge_text", "OFERTA COMERCIAL"))
    if is_vs:
        badge_text = get_campaign_vs_header(campaign, niche) or raw_text
    else:
        badge_text = raw_text

    # Sanitizar agresivamente cualquier emoji residual para evitar cajas vacías o tofu
    badge_text = re.sub(r"[^\w\s\d\-_·:¿?¡!€$%&/().,+*áéíóúÁÉÍÓÚñÑüÜ]", "", badge_text).strip()
    if not badge_text:
        return image

    font = None
    target_font_size = 34 if len(badge_text) > 22 else 38
    for fp in FONT_PATHS:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, target_font_size)
                break
            except Exception:
                pass
    if not font:
        font = ImageFont.load_default()

    bg_color = campaign.get("badge_bg", (185, 28, 28, 255))
    border_color = campaign.get("badge_border", (250, 204, 21, 255))
    text_color = campaign.get("badge_text_color", (255, 255, 255))

    img_w, img_h = image.size
    draw = ImageDraw.Draw(image)

    bbox = draw.textbbox((0, 0), badge_text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Escalar hacia abajo si sobrepasa el límite visual de 900px
    if text_w > 820:
        for fp in FONT_PATHS:
            if os.path.exists(fp):
                try:
                    font = ImageFont.truetype(fp, 30)
                    bbox = draw.textbbox((0, 0), badge_text, font=font)
                    text_w = bbox[2] - bbox[0]
                    text_h = bbox[3] - bbox[1]
                    break
                except Exception:
                    pass

    px, py = 45, 16
    bw = text_w + px * 2
    bh = text_h + py * 2
    bx = (img_w - bw) // 2
    by = pos_y

    # Sombra del badge
    draw.rounded_rectangle([bx - 4, by + 4, bx + bw + 4, by + bh + 8], radius=16, fill=(0, 0, 0, 190))
    # Pastilla de la campaña
    draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=16, fill=bg_color, outline=border_color, width=4)
    # Texto
    tx = bx + px - bbox[0]
    ty = by + py - bbox[1] - 2
    draw.text((tx, ty), badge_text, fill=text_color, font=font)

    return image

def set_forced_campaign(campaign_id: Optional[str]) -> None:
    cfg = _load_config()
    if campaign_id:
        cfg["force_campaign"] = campaign_id
    else:
        cfg.pop("force_campaign", None)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def clear_forced_campaign() -> None:
    set_forced_campaign(None)

def get_campaign_status(target_date: Optional[date] = None) -> str:
    """Devuelve un texto descriptivo listo para ser incluido en el resumen matinal de Telegram."""
    c = get_active_campaign(target_date)
    if not c:
        return "Ninguna (Modo Normal Evergreen)"
    end_str = c["end_date"].strftime("%d/%m")
    mode_str = " (Forzado manual)" if c.get("is_forced") else " (Automático D-7)"
    return f"{c['name']} (Activa hasta {end_str}){mode_str}"

if __name__ == "__main__":
    import sys
    print("=== ESTADO DEL MOTOR AUTÓNOMO DE CAMPAÑAS ===")
    today = datetime.now().date()
    camp = get_active_campaign(today)
    if camp:
        print(f"Estado Hoy ({today}): [CAMPAÑA ACTIVA]")
        print(f" - Nombre: {camp['name']}")
        print(f" - Prefijo título: {camp['title_prefix']}")
        print(f" - Badge texto: {camp['badge_text']}")
        print(f" - Días restantes: {camp.get('days_remaining')}")
        print(f" - Tags: {', '.join(camp['extra_tags'])}")
    else:
        print(f"Estado Hoy ({today}): [MODO NORMAL EVERGREEN]")
        print(" - Ninguna campaña activa en esta fecha.")
    print(f"Resumen Telegram: {get_campaign_status(today)}")
