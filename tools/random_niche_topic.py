#!/usr/bin/env python3
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

# Comprehensive fallback list of 115+ distinct household kitchen appliance niches
FALLBACK_BOOKS = [
    "novelas negras y de misterio mas vendidas",
    "libros de desarrollo personal y productividad",
    "novelas de ciencia ficcion imprescindibles",
    "libros de historia de espana recomendados",
    "novelas romanticas de ficcion juvenil",
    "libros de finanzas personales e inversion",
    "novelas de fantasia epica mas valoradas",
    "libros de psicologia y comportamiento humano",
    "biografias y memorias mas inspiradoras",
    "novelas historicas mas vendidas en amazon",
    "libros de filosofia practica para el dia a dia",
    "comics y novelas graficas imprescindibles",
    "libros de salud nutricion y bienestar",
    "novelas de terror y suspense psicologico",
    "libros de emprendimiento y negocios digitales"
]

FALLBACK_APPLIANCES = [
    "mejores freidoras de aire calidad precio 2026",
    "cafeteras superautomaticas con molinillo integrado",
    "freidoras de aire de doble cesta independientes",
    "robots de cocina multifuncion alternativas a thermomix",
    "cafeteras express manuales de 20 bares",
    "batidoras de mano profesionales 1200w picahielo",
    "ollas a presion electricas programables multifuncion",
    "hornos de sobremesa freidora de aire conveccion",
    "tostadoras de ranura ancha acero inoxidable",
    "envasadoras al vacio domesticas para alimentos secos y humedos",
    "planchas de asar electricas antiadherentes sin pfoa",
    "licuadoras de prensado en frio para zumos naturales",
    "picadoras de carne y verduras electricas de acero",
    "espumadores de leche automaticos para capuchino",
    "hervidores de agua electricos con selector de temperatura",
    "parrillas electricas grill de contacto para carne",
    "creperas electricas con termostato regulable",
    "sandwicheras grill 3 en 1 con placas desmontables",
    "arrocera electrica japonesa multifuncion",
    "procesadores de alimentos para amasar y cortar"
]

FALLBACK_FOOTWEAR = [
    "zapatillas de running con maxima amortiguacion",
    "botas de montana impermeables gore tex",
    "zapatos de seguridad ligeros con puntera de composite",
    "zapatillas de padel con suela de espiga",
    "zapatos de vestir comodos para hombre",
    "sandalias de senderismo para mujer",
    "botas de futbol para cesped artificial",
    "zapatillas de baloncesto de caña alta",
    "zapatillas de entrenamiento crossfit",
    "mocasines de piel comodos para hombre",
    "zapatillas de trail running con agarre extremo",
    "zapatillas de estar por casa con plantilla viscoelastica",
    "botas militares tacticas y de combate",
    "zapatillas minimalistas barefoot para caminar",
    "zapatos ortopedicos comodos para mujer",
    "zapatillas casual de vestir estilo urbano",
    "pies de gato para escalada deportiva",
    "botas de nieve impermeables y termicas",
    "zapatillas de tenis para pista dura",
    "zapatillas con camara de aire para andar",
    "zapatillas de ciclismo de carretera para calas",
    "botas de moto de cuero con protecciones",
    "zapatos de trabajo antideslizantes para hosteleria",
    "chanclas de pala ergonomicas para piscina",
    "zapatillas de balonmano y voleibol para pista cubierta",
    "botas de agua impermeables para lluvia",
    "zapatos de plataforma comodos para mujer",
    "zapatillas de skate de suela plana de goma",
    "botines de piel para mujer estilo chelsea",
    "zapatillas deportivas con velcro para personas mayores",
    "zapatillas de trekking ligeras para caminatas",
    "zapatos nauticos de cuero para hombre",
    "botas de equitacion e hipica",
    "zapatillas slip on sin cordones comodas",
    "zapatos de baile de salon con suela de ante",
    "zapatillas de atletismo con clavos",
    "botas de caza impermeables camuflaje",
    "zapatos de descanso post entrenamiento",
    "zapatillas transpirables para verano",
    "botines con tacon ancho y comodo",
    "zapatillas de marcha nordica",
    "zapatos para diabeticos con horma ancha",
    "sandalias de piel estilo bio con plantilla anatomica",
    "botas de trabajo de construccion con plantilla antiperforacion",
    "zapatillas de gimnasio para levantar pesas",
    "zapatos de camarero comodos e impermeables",
    "zapatillas retro vintage estilo anos 80",
    "zapatos mary jane comodos para mujer",
    "botas panama de piel estilo clasico",
    "zapatillas de senderismo con amortiguacion eva"
]


FALLBACK_CLEANING = [
    "robot aspirador fregador con base de autovaciado",
    "aspiradora sin cable de gran potencia de succion",
    "aspiradora escoba electrica con filtro hepa",
    "vaporizador de limpieza a presion para hogar",
    "limpiador de cristales robotico automatico",
    "hidrolimpiadora de alta presion para terraza y coche",
    "limpiador de tapicerias y sofás portatil",
    "aspiradora de mano sin cable para coche y hogar",
    "mopa de vapor multifuncion para suelos de madera",
    "robot aspirador economico con mapeo laser",
    "aspiradora industrial de agua y seco",
    "limpiador ultrasónico para joyas y gafas",
    "fregadora de suelos electrica inalambrica",
    "aspiradora antiacaros con luz uv para colchones",
    "quitapelusas electrico recargable para ropa y sofás",
    "barredora manual y electrica para exteriores",
    "aspiradora para pelos de mascotas con cepillo antiquedades",
    "limpiador a vapor de mano para azulejos y juntas",
    "mopa electrica giratoria para abrillantado de suelos",
    "aspiradora de cenizas electrica para chimeneas"
]


FALLBACK_BARBERIA = [
    "afeitadoras de cabeza calva ergonomicas",
    "recortadoras de barba para hombre profesionales",
    "cortapelos profesionales inalambricos de titanio",
    "afeitadoras electricas rotativas resistentes al agua",
    "afeitadoras electricas de laminas de precision",
    "maquinas de afeitar corporales para hombre",
    "recortadores de nariz y orejas lavables",
    "maquinas de afeitar vintage estilo barbero",
    "afeitadoras resistentes al agua ipx7 para ducha",
    "recortadoras de precision para contornos y patillas",
    "cortapelos con motor magnetico potente",
    "afeitadoras de viaje compactas usb c",
    "maquinillas de afeitar clasicas de doble filo",
    "recortadoras hibridas para cara y cuerpo",
    "afeitadoras para piel sensible con cabezal antirritacion",
    "maquinas cortapelo con peines guia magneticos",
    "recortadoras de barba con aspiracion de pelos",
    "afeitadoras con estacion de autolimpieza",
    "navajas de afeitar de barbero con mango de madera",
    "cepillos termicos electricos para barba",
]


FALLBACK_TALLER = [
    "taladros percutores a bateria para hormigon",
    "amoladoras angulares a bateria 18v",
    "mini motosierras a bateria para poda",
    "maletines de herramientas completos con carraca",
    "atornilladores de impacto potentes",
    "sierras de calar pendulares con guia laser",
    "niveles laser autonivelantes 360 grados",
    "lijadoras orbitales y de banda para madera",
    "sierras circulares de mano con disco de precision",
    "pistolas de calor electricas para decapar",
    "cajas de herramientas con ruedas profesionales",
    "multiherramientas oscilantes a bateria",
    "ingletadoras telescopicas para madera",
    "taladros atornilladores compactos 12v",
    "remachadoras electricas y manuales reforzadas",
    "grapadoras y clavadoras electricas a bateria",
    "juegos de llaves de vaso y carraca de cromo vanadio",
    "compresores de aire portatiles para taller",
    "cepillos electricos para madera con tope paralelo",
    "fresadoras de superficie para carpinteria"
]


def main():
    parser = argparse.ArgumentParser(description="Universal Random Topic Generator for YouTube Channels")
    parser.add_argument("--channel_name", default="Canal YouTube")
    parser.add_argument("--channel_niche", default="Aparatos eléctricos de cocina para el hogar")
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

    chosen_topic = None
    ollama_url = "http://127.0.0.1:11434/api/chat"
    
    # Try with Ollama to get an unused topic (60s timeout for 27B model)
    for attempt in range(2):
        used_topics_list = list(used_topics)
        sample_used = random.sample(used_topics_list, min(len(used_topics_list), 15))
        used_topics_str = ", ".join(sample_used) if sample_used else "ninguno"
        
        messages = [
            {
                "role": "system",
                "content": f"Eres un asistente experto en analítica de mercado y canales de YouTube. Propón un TIPO DE PRODUCTO ESPECÍFICO del nicho \"{channel_niche}\" para un ranking comercial de afiliados. NO repitas NINGUNO de estos temas ya usados: [{used_topics_str}]. Responde ÚNICAMENTE en JSON: {{\"topic\": \"nombre del producto\"}}."
            },
            {
                "role": "user",
                "content": f"Nicho del canal: \"{channel_niche}\". Genera un nuevo tipo de producto específico de este nicho que NUNCA se haya usado."
            }
        ]
        
        try:
            req_data = json.dumps({
                "model": "qwen3.8:27b",
                "messages": messages,
                "format": "json",
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 40}
            }).encode("utf-8")
            
            req = urllib.request.Request(ollama_url, data=req_data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as res:
                res_json = json.loads(res.read().decode("utf-8"))
                content_str = res_json.get("message", {}).get("content", "").strip()
                parsed_topic = json.loads(content_str).get("topic", "").strip().lower()
                parsed_slug = sanitize_slug(parsed_topic)
                
                # Sanity check: no numbers or timestamp suffixes in topic name
                parsed_topic_clean = re.sub(r'\b\d{4,}\b', '', parsed_topic).strip()
                
                if parsed_topic_clean and len(parsed_topic_clean) > 3 and "productos" not in parsed_topic_clean and parsed_slug not in used_topics:
                    chosen_topic = parsed_topic_clean
        except Exception:
            pass

    # Select fallback pool based on channel_niche keywords
    is_taller = any(kw in channel_niche.lower() for kw in ["taller", "bricolaje", "herramienta", "taladro", "amoladora", "motosierra", "bosch", "einhell"])
    is_barberia = any(kw in channel_niche.lower() for kw in ["barberia", "afeitado", "barba", "cortapelo", "afeitadora", "cuidado masculino", "pelo"])
    is_books = any(kw in channel_niche.lower() for kw in ["libro", "novela", "literatura", "ensayo", "comic", "lectura", "kindle", "escritor", "biografia", "ficcion", "libreria"])
    is_footwear = any(kw in channel_niche.lower() for kw in ["calzado", "zapato", "zapatilla", "bota", "sandalia"])
    is_cleaning = any(kw in channel_niche.lower() for kw in ["limpieza", "aspirador", "aspiradora", "vaporizador", "hidrolimpiadora", "fregador", "mopa"])
    if is_taller:
        active_fallback_pool = FALLBACK_TALLER
    elif is_barberia:
        active_fallback_pool = FALLBACK_BARBERIA
    elif is_books:
        active_fallback_pool = FALLBACK_BOOKS
    elif is_footwear:
        active_fallback_pool = FALLBACK_FOOTWEAR
    elif is_cleaning:
        active_fallback_pool = FALLBACK_CLEANING
    else:
        active_fallback_pool = FALLBACK_APPLIANCES

    # Fallback pool check if Ollama failed or produced a duplicate
    if not chosen_topic:
        shuffled_fallbacks = list(active_fallback_pool)
        random.shuffle(shuffled_fallbacks)
        for fb in shuffled_fallbacks:
            fb_slug = sanitize_slug(fb)
            if fb_slug not in used_topics:
                chosen_topic = fb
                break

    # Absolute fallback: pick random fallback from pool (NEVER append timestamp numbers!)
    if not chosen_topic:
        chosen_topic = random.choice(active_fallback_pool)

    chosen_topic = str(chosen_topic).replace("_", " ").strip()
    video_slug = sanitize_slug(chosen_topic)
    
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
        "video_dir": video_dir
    }
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
