#!/usr/bin/env python3
"""
random_vs_topic.py — Generates a high-intent commercial comparison topic (A vs B specific models).
Implements the Sniper High-Intent Strategy: targeted exact rival battles that buyers actively search on Amazon.
"""
import sys, os, json, urllib.request, re, argparse, random, time

def sanitize_slug(text):
    text = str(text).lower().strip()
    text = re.sub(r'[áàäâ]', 'a', text)
    text = re.sub(r'[éèëê]', 'e', text)
    text = re.sub(r'[íìïî]', 'i', text)
    text = re.sub(r'[óòöô]', 'o', text)
    text = re.sub(r'[úùüû]', 'u', text)
    text = re.sub(r'[ñ]', 'n', text)
    text = re.sub(r'[^a-z0-9\_]', '_', text)
    text = re.sub(r'_+', '_', text).strip('_')
    return text

def load_channel_history(channel_dir):
    os.makedirs(channel_dir, exist_ok=True)
    history_file = os.path.join(channel_dir, "history.json")
    used_topics = set()
    used_asins = set()
    if os.path.exists(channel_dir):
        for item in os.listdir(channel_dir):
            item_path = os.path.join(channel_dir, item)
            if os.path.isdir(item_path):
                slug = sanitize_slug(item)
                if slug:
                    used_topics.add(slug)
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                hdata = json.load(f)
                for t in hdata.get("used_topics", []):
                    slug = sanitize_slug(t)
                    if slug:
                        used_topics.add(slug)
                for a in hdata.get("used_asins", []):
                    used_asins.add(a.strip())
        except Exception:
            pass
    return history_file, used_topics, used_asins

def save_channel_history(history_file, used_topics, used_asins):
    channel_dir = os.path.dirname(history_file)
    data = {
        "used_topics": sorted(list(used_topics)),
        "used_asins": sorted(list(used_asins))
    }
    try:
        if os.path.exists(channel_dir):
            os.chmod(channel_dir, 0o777)
    except Exception:
        pass
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    try:
        os.chmod(history_file, 0o666)
    except Exception:
        pass

# ---------------------------------------------------------------------------
# High-Intent Exact Rival Battles per Niche (Sniper Strategy)
# ---------------------------------------------------------------------------

FALLBACK_BARBERIA_VS = [
    "Philips OneBlade vs Braun Series XT5",
    "Braun Series 3 vs Braun Series 5",
    "Wahl Magic Clip vs Wahl Super Taper",
    "Remington HC5810 vs Cecotec Bamba PrecisionCare",
    "Philips Serie 5000 vs Serie 7000",
    "Hatteker Cortapelos vs Surker Profesional",
    "Braun Series 7 vs Braun Series 9",
    "Panasonic Arc5 vs Braun Series 9",
    "Philips Multigroom 7000 vs Braun All-in-One Series 7",
    "BaBylissPRO Skeleton vs Wahl Detailer",
    "Cecotec Bamba PrecisionCare Pro vs Remington Colour Cut",
    "Braun Series 8 vs Philips Shaver Series 9000",
    "Panasonic ER-DGP82 vs Wahl Senior Cordless",
    "Philips OneBlade Pro vs Braun Series XT5 Face",
    "Wahl Beret vs Wahl Detailer Cordless"
]

FALLBACK_FOOTWEAR_VS = [
    "Skechers Arch Fit vs Skechers Go Walk",
    "Salomon Speedcross 6 vs Hoka Speedgoat 5",
    "Bellota Comfort vs U-Power Red Lion",
    "Nike Pegasus 40 vs Asics Novablast 4",
    "Brooks Ghost 15 vs Nike Pegasus 40",
    "Adidas Ultraboost Light vs Nike Invincible 3",
    "New Balance Fresh Foam 1080 vs Asics Nimbus 26",
    "La Sportiva Ultra Raptor II vs Salomon XA Pro 3D",
    "Chiruca Urales vs Bestard Breithorn",
    "Puma Safety Velocity vs U-Power Point",
    "Vans Old Skool vs Converse Chuck Taylor All Star",
    "Under Armour Charged Assert vs Nike Revolution 6",
    "Mizuno Wave Rider 27 vs Brooks Ghost 15",
    "Hoka Clifton 9 vs Asics Novablast 4",
    "Saucony Ride 17 vs Brooks Ghost 15"
]

FALLBACK_APPLIANCES_VS = [
    "Cosori Dual Blaze vs Cecotec Cecofry Dual 9000",
    "De'Longhi Magnifica S vs Philips Serie 2200",
    "Cecotec Mambo Touch vs Moulinex ClickChef",
    "Cosori Turbo Blaze vs Ninja Air Fryer MAX Pro",
    "De'Longhi Dedica EC685 vs Cecotec Cafelizzia 790",
    "Braun Minipimer 9 vs Bosch MaxoMixx 1000W",
    "Ninja DualZone AF300EU vs Cosori Dual Basket",
    "Krups Roma EA8108 vs De'Longhi Magnifica S",
    "Instant Pot Pro vs Moulinex Turbo Cuisine",
    "Cecotec Cecofry Bombastik vs Cosori 5.5L",
    "Philips Airfryer Serie 5000 vs Cosori Pro LE",
    "Taurus Mycook One vs Cecotec Mambo 10090",
    "Krups Nespresso Inissia vs De'Longhi Vertuo Pop",
    "Rowenta Silence Force vs Cecotec Conga PopStar",
    "Severin Espumador vs Nespresso Aeroccino 4"
]

FALLBACK_BOOKS_VS = [
    "Hábitos Atómicos vs El Poder de los Hábitos",
    "Padre Rico Padre Pobre vs El Hombre más Rico de Babilonia",
    "Sapiens vs Homo Deus",
    "El Monje que Vendió su Ferrari vs Las 48 Leyes del Poder",
    "1984 vs Un Mundo Feliz",
    "Dune vs Fundación",
    "La Psicología del Dinero vs Los Secretos de la Mente Millonaria"
]

FALLBACK_CLEANING_VS = [
    "Roborock Q7 Max vs Dreame D10 Plus",
    "Dyson V15 Detect vs Rowenta X-Force Flex 14.60",
    "Kärcher K4 Power Control vs Bosch EasyAquatak 120",
    "Bissell SpotClean Pro vs Cecotec Conga PopStar 3000",
    "Polti Vaporetto Smart 30 vs Kärcher SC3 EasyFix"
]

FALLBACK_TALLER_VS = [
    "Bosch Professional GSB 18V-21 vs Einhell TE-CD 18/48 Li-i",
    "Einhell Power X-Change vs Parkside Performance 20V",
    "Bosch Home and Garden EasyImpact 18V vs Einhell TC-CD 18/35",
    "Mannesmann M98430 215 piezas vs Workpro 165 piezas",
    "DeWalt DCD796D2 vs Makita DHP482Z",
    "Black and Decker BDCDD12 vs Bosch EasyDrill 1200",
    "Worx WX372 vs Stanley FatMax V20",
    "Bosch Professional GWS 7-125 vs Einhell TE-AG 18/115 Li",
    "Mini motosierra Seesii 6 pulgadas vs Saker Mini Motosierra",
    "Nivel laser Huepar 3D vs Bosch Quigo 3",
    "Dremel 3000 vs Dremel 4250",
    "Lijadora de banda Einhell TE-BS 8540 E vs Bosch PBS 75 A",
    "Sierra circular Bosch PKS 55 A vs Einhell TC-CS 1400",
    "Pistola de calor Einhell TE-HA 2000 E vs Bosch UniversalHeat 600",
    "Taladro atornillador Teccpo 60Nm vs Hychika 60Nm"
]

FALLBACK_GENERIC_VS = [
    "Sony WH-1000XM5 vs Bose QuietComfort Ultra",
    "Apple Watch Series 9 vs Garmin Venu 3",
    "Kindle Paperwhite vs Kobo Clara 2E",
    "Logitech MX Master 3S vs Razer Pro Click",
    "Samsung Galaxy Tab S9 vs Apple iPad Air M2"
]

def main():
    parser = argparse.ArgumentParser(description="High-Intent VS Topic Generator for A vs B YouTube videos")
    parser.add_argument("--channel_name", default="Canal YouTube")
    parser.add_argument("--channel_niche", default="Productos de Amazon")
    parser.add_argument("--base_dir", default="/home/javierferb/ia-lab-files/videos/edicion_ia")
    args, unknown = parser.parse_known_args()

    channel_name = args.channel_name
    channel_niche = args.channel_niche
    base_dir = args.base_dir

    if "{" in channel_name or len(channel_name) < 2:
        channel_name = "Canal YouTube"
    if "{" in channel_niche or len(channel_niche) < 2:
        channel_niche = "Productos de Amazon"

    channel_slug = sanitize_slug(channel_name)
    channel_dir = os.path.join(base_dir, channel_slug)

    history_file, used_topics, used_asins = load_channel_history(channel_dir)

    niche_lower = channel_niche.lower()
    is_taller = any(kw in niche_lower for kw in [
        "taller", "bricolaje", "herramienta", "taladro", "amoladora", "motosierra", "bosch", "einhell", "atornillador"
    ])
    is_barberia = any(kw in niche_lower for kw in [
        "barberia", "afeitado", "barba", "cortapelo", "afeitadora", "cuidado masculino", "pelo"
    ])
    is_footwear = any(kw in niche_lower for kw in [
        "calzado", "zapato", "zapatilla", "bota", "sandalia", "deportivo", "running"
    ])
    is_books = any(kw in niche_lower for kw in [
        "libro", "novela", "literatura", "kindle", "lectura"
    ])
    is_cleaning = any(kw in niche_lower for kw in [
        "limpieza", "aspirador", "aspiradora", "fregador", "mopa"
    ])
    is_appliance = any(kw in niche_lower for kw in [
        "cocina", "electrodomestico", "aparato", "hogar", "freidora", "cafetera"
    ])

    if is_taller:
        pool = FALLBACK_TALLER_VS
        niche_instruction = "DUELO DE MODELOS EXACTOS DE HERRAMIENTAS Y BRICOLAJE (ej: 'Bosch Professional GSB 18V vs Einhell TE-CD 18/48', 'Mannesmann 215 piezas vs Workpro', 'Einhell Power X-Change vs Parkside')"
    elif is_barberia:
        pool = FALLBACK_BARBERIA_VS
        niche_instruction = "DUELO DE MODELOS EXACTOS DE BARBERÍA/AFEITADO (ej: 'Philips OneBlade vs Braun Series XT5', 'Braun Series 3 vs Braun Series 5', 'Wahl Magic Clip vs Wahl Super Taper')"
    elif is_footwear:
        pool = FALLBACK_FOOTWEAR_VS
        niche_instruction = "DUELO DE MODELOS EXACTOS DE CALZADO/ZAPATILLAS (ej: 'Skechers Arch Fit vs Skechers Go Walk', 'Salomon Speedcross 6 vs Hoka Speedgoat 5', 'Bellota Comfort vs U-Power Red Lion')"
    elif is_appliance:
        pool = FALLBACK_APPLIANCES_VS
        niche_instruction = "DUELO DE MODELOS EXACTOS DE COCINA/ELECTRODOMÉSTICOS (ej: 'Cosori 5.5L vs Cecotec Cecofry 5.5L', 'Ninja DualZone vs Cecofry Dual 9000', 'De\\'Longhi Magnifica S vs Philips Serie 2200')"
    elif is_books:
        pool = FALLBACK_BOOKS_VS
        niche_instruction = "DUELO DE 2 LIBROS RIVALES EXACTOS (ej: 'Hábitos Atómicos vs El Poder de los Hábitos')"
    elif is_cleaning:
        pool = FALLBACK_CLEANING_VS
        niche_instruction = "DUELO DE 2 MODELOS RIVALES EXACTOS DE LIMPIEZA (ej: 'Roborock Q7 Max vs Dreame D10 Plus')"
    else:
        pool = FALLBACK_GENERIC_VS
        niche_instruction = "DUELO DE 2 MODELOS COMERCIALES RIVALES EXACTOS (formato 'Modelo A vs Modelo B')"

    chosen_topic = None
    ollama_url = "http://127.0.0.1:11434/api/chat"

    # Ollama Sniper Prompt: Forces exact recognizable commercial model battles
    for attempt in range(1):
        used_topics_list = list(used_topics)
        sample_used = random.sample(used_topics_list, min(len(used_topics_list), 15))
        used_topics_str = ", ".join(sample_used) if sample_used else "ninguno"

        messages = [
            {
                "role": "system",
                "content": (
                    f"Eres el estratega jefe de compras y afiliación en YouTube para el canal \"{channel_name}\". "
                    f"Tu misión es proponer un {niche_instruction} del nicho \"{channel_niche}\". "
                    f"REGLA DE ORO DE ALTA INTENCIÓN DE COMPRA: Debes proponer OBLIGATORIAMENTE dos modelos comerciales específicos y reconocibles "
                    f"que compitan directamente en Amazon España (ejemplo estricto: 'Modelo A vs Modelo B'). "
                    f"PROHIBIDO TERMINANTEMENTE proponer categorías genéricas o abstractas (como 'afeitadoras rotativas' o 'zapatillas running'). "
                    f"El usuario debe tener la tarjeta de crédito en la mano dudando entre ambos modelos concretos. "
                    f"NO repitas estos duelos ya grabados: [{used_topics_str}]. "
                    f"Responde ÚNICAMENTE en JSON con la clave 'topic': {{\"topic\": \"Modelo A vs Modelo B\"}}."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Nicho: \"{channel_niche}\". Genera un duelo comercial de alta intención de compra entre 2 modelos específicos rivales para Amazon."
                )
            }
        ]

        try:
            req_data = json.dumps({
                "model": "qwen3.8:27b",
                "messages": messages,
                "format": "json",
                "stream": False,
                "options": {"temperature": 0.5}
            }).encode("utf-8")

            req = urllib.request.Request(ollama_url, data=req_data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=12) as res:
                res_json = json.loads(res.read().decode("utf-8"))
                content_str = res_json.get("message", {}).get("content", "").strip()
                parsed_topic = json.loads(content_str).get("topic", "").strip()
                parsed_slug = sanitize_slug(parsed_topic)

                # Validar que contenga 'vs' y sea un duelo específico
                if (" vs " in parsed_topic.lower() and len(parsed_topic) > 6
                        and parsed_slug not in used_topics):
                    chosen_topic = parsed_topic
                    break
        except Exception:
            pass

    # Fallback to curated high-intent pools
    if not chosen_topic:
        shuffled = list(pool)
        random.shuffle(shuffled)
        for fb in shuffled:
            fb_slug = sanitize_slug(fb)
            if fb_slug not in used_topics:
                chosen_topic = fb
                break

    if not chosen_topic:
        chosen_topic = random.choice(pool)

    chosen_topic = str(chosen_topic).replace("_", " ").strip()
    video_slug = sanitize_slug(chosen_topic) + "_vs"

    used_topics.add(video_slug)
    save_channel_history(history_file, used_topics, used_asins)

    video_dir = os.path.join(channel_dir, video_slug)
    os.makedirs(video_dir, exist_ok=True)

    result = {
        "channel_name": channel_name,
        "channel_slug": channel_slug,
        "channel_niche": channel_niche,
        "search_query": chosen_topic,
        "video_slug": video_slug,
        "canal_nombre": f"{channel_slug}/{video_slug}",
        "channel_dir": channel_dir,
        "video_dir": video_dir,
        "format": "vs"
    }
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
