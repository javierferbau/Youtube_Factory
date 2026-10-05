#!/usr/bin/env python3
"""
vs_script_enricher.py
Garantiza que el guion para comparativas VS (A vs B) tenga una duración óptima de 4 a 5 MINUTOS (700 a 850 palabras).
Elimina el relleno inflado artificialmente a 8-10 min, mejorando radicalmente la retención y el APV.
Inserta Micro-CTAs verbales estratégicos hacia el primer comentario fijado:
  1. Al inicio del análisis (Minuto ~1:00, tras la intro/arranque de Producto A).
  2. En el veredicto / outro final invitando a comprobar disponibilidad y oferta.
"""
import sys, os, json, re

def clean_author_name(name):
    if not name:
        return "Autor"
    s = str(name).strip()
    s = re.sub(r'[\r\n\t]+', ' ', s)
    s = re.sub(r'\s*\([^)]*\)', '', s)
    s = re.sub(r'^(de|por|autor:?)\s*', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s*formato:.*$', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s*edición:.*$', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s+', ' ', s).strip()
    return s if s else "Autor"

def clean_duplicates(text):
    """Elimina frases duplicadas consecutivas o repetidas."""
    if not text:
        return ""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    unique_sentences = []
    seen = set()
    for s in sentences:
        s_clean = s.strip().lower()
        if s_clean and s_clean not in seen:
            seen.add(s_clean)
            unique_sentences.append(s.strip())
    return " ".join(unique_sentences)

def fit_section(text, target_words, fallback_paragraphs, enforce_first_anchor=None):
    """
    Ajusta una sección al rango objetivo de palabras de forma concisa y directa.
    Si el texto base es muy corto, añade párrafos de respaldo sin inflar.
    Si enforce_first_anchor está definido y no aparece, lo añade orgánicamente.
    """
    text = clean_duplicates(text)
    
    if enforce_first_anchor and enforce_first_anchor.lower() not in text.lower():
        text = (enforce_first_anchor + " " + text).strip() if text else enforce_first_anchor

    words = text.split()
    if len(words) < target_words:
        for p in fallback_paragraphs:
            if p and p.strip() and p.strip().lower() not in text.lower():
                text = (text + " " + p.strip()).strip()
                text = clean_duplicates(text)
                if len(text.split()) >= target_words:
                    break

    # Si supera excesivamente el target (+35 palabras), acotar con suavidad respetando frases completas
    curr_words = text.split()
    if len(curr_words) > target_words + 35:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        trimmed = []
        count = 0
        for s in sentences:
            trimmed.append(s)
            count += len(s.split())
            if count >= target_words:
                break
        text = " ".join(trimmed).strip()

    return text

def main():
    if len(sys.argv) < 2:
        sys.exit(1)
        
    data_json_path = sys.argv[1]
    if not os.path.exists(data_json_path):
        sys.exit(1)
        
    with open(data_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    query = data.get("query", "productos").strip()
    query_title = query.lower()
    
    product_a = data.get("product_a", {})
    product_b = data.get("product_b", {})
    
    title_a = product_a.get("title", "Producto A")
    brand_a = clean_author_name(product_a.get("brand", "Marca A")).upper()
    price_a = product_a.get("price", "Consultar precio")
    rating_a = product_a.get("rating", "4.5 estrellas")
    good_reviews_a = product_a.get("positive_reviews") or product_a.get("good_reviews") or []
    bad_reviews_a = product_a.get("negative_reviews") or product_a.get("bad_reviews") or []

    title_b = product_b.get("title", "Producto B")
    brand_b = clean_author_name(product_b.get("brand", "Marca B")).upper()
    price_b = product_b.get("price", "Consultar precio")
    rating_b = product_b.get("rating", "4.6 estrellas")
    good_reviews_b = product_b.get("positive_reviews") or product_b.get("good_reviews") or []
    bad_reviews_b = product_b.get("negative_reviews") or product_b.get("bad_reviews") or []

    script = data.get("script", {})

    is_book_channel = (
        "libreria_del_pueblo" in data_json_path.lower() or 
        "librería" in data.get("canal_nombre", "").lower() or 
        "libro" in query_title or "novela" in query_title or "lectura" in query_title
    )
    is_barberia = (
        "barberia" in data_json_path.lower() or 
        "barbería" in data.get("canal_nombre", "").lower() or 
        any(k in query_title for k in ["afeit", "barba", "pelo", "corte", "blade", "trimmer", "cortapelo"])
    )
    is_footwear = (
        "zapateria" in data_json_path.lower() or 
        "calzado" in data.get("canal_nombre", "").lower() or "zapateria" in data.get("canal_nombre", "").lower() or 
        any(k in query_title for k in ["zapatilla", "bota", "zapato", "running", "crossfit", "trail", "seguridad"])
    )
    is_appliance = (
        "cocina" in data_json_path.lower() or "cocina" in data.get("canal_nombre", "").lower() or 
        any(k in query_title for k in ["freidora", "cafetera", "batidora", "robot", "cocina", "olla", "grill"])
    )

    if is_barberia:
        dolor_a = "el afeitado diario más apurado a ras de piel y sin irritación"
        beneficio_b = "máxima versatilidad para recortar barba densa y perfilar contornos"
    elif is_footwear:
        dolor_a = "máxima estabilidad, soporte duradero y confort en largas jornadas"
        beneficio_b = "ligereza extrema y una amortiguación ultra reactiva en cada pisada"
    elif is_appliance:
        dolor_a = "la mejor relación calidad precio, rapidez y facilidad de limpieza"
        beneficio_b = "máxima potencia, mayor capacidad y acabados profesionales de gama alta"
    elif is_book_channel:
        dolor_a = "un manual estructurado, reflexivo y profundo para dominar la materia"
        beneficio_b = "una lectura amena, motivadora y de rápida asimilación práctica"
    else:
        dolor_a = "máxima solidez estructural, fiabilidad y resistencia comprobada"
        beneficio_b = "ligereza, facilidad de uso continuo y ajustar el presupuesto"

    veredicto_binario = f"Veredicto definitivo: Si tu prioridad es {dolor_a}, el ganador indiscutible es {brand_a}. Pero si buscas {beneficio_b}, ve directo a por {brand_b}. Comprueba si sigue el cupón o la oferta activa en el primer comentario fijado aquí abajo."

    # Micro-CTAs explícitos
    micro_cta_intro = "Recuerda que tienes los enlaces directos con el descuento actualizado de ambos modelos en el primer comentario fijado aquí abajo."
    micro_cta_outro = "¿Con cuál te quedas tú? Te he dejado el enlace oficial con la mejor oferta en el comentario fijado para que compruebes disponibilidad."

    default_pos_a = "Los lectores destacan la claridad explicativa y el gran impacto transformador de sus lecciones en la vida diaria." if is_book_channel else "Los compradores destacan su excelente calidad de construcción, la comodidad de uso diario y su gran fiabilidad técnica."
    default_neg_a = "Algunos lectores comentan que requiere una lectura pausada y reflexiva para asimilar todos sus conceptos." if is_book_channel else "Algunos compradores señalan que requiere revisar bien las especificaciones y medidas para sacarle el máximo partido."

    default_pos_b = "Los lectores elogian lo ameno, dinámico y motivador de su lectura desde el primer capítulo." if is_book_channel else "Los usuarios elogian su ligereza, versatilidad en cualquier situación y su ajustada relación calidad precio."
    default_neg_b = "Algunas opiniones sugieren tomar notas prácticas para no perder el hilo entre los ejemplos." if is_book_channel else "Algunas opiniones sugieren comprobar con atención las opciones de ajuste antes del primer uso."

    pos_str_a = " ".join([f"Los usuarios confirman: {r.get('text', '') if isinstance(r, dict) else r}" for r in good_reviews_a[:2]]) if good_reviews_a else default_pos_a
    neg_str_a = " ".join([f"Entre los aspectos a mejorar señalan: {r.get('text', '') if isinstance(r, dict) else r}" for r in bad_reviews_a[:1]]) if bad_reviews_a else default_neg_a
    
    pos_str_b = " ".join([f"Las valoraciones positivas señalan: {r.get('text', '') if isinstance(r, dict) else r}" for r in good_reviews_b[:2]]) if good_reviews_b else default_pos_b
    neg_str_b = " ".join([f"Por su parte, las advertencias críticas indican: {r.get('text', '') if isinstance(r, dict) else r}" for r in bad_reviews_b[:1]]) if bad_reviews_b else default_neg_b

    if is_book_channel:
        # HOOK (~90 palabras)
        hook = script.get("hook", "").strip()
        has_la = any(k in hook.lower() for k in ["error", "cuidado", "antes de comprar", "ahorrarte", "no compres", "gastes tu dinero", "decepción", "decepcion", "fallos", "tirar el dinero"])
        if not has_la or len(hook.split()) < 40:
            hook = ""
        hook_paragraphs = [
            f"¡Cuidado antes de elegir tu próxima lectura! Decidir a ciegas entre la obra de {brand_a} o la propuesta de {brand_b} puede hacerte tirar el dinero si no conoces sus diferencias clave y ritmo narrativo.",
            f"Ambos títulos encabezan los puestos de honor en Amazon España en 2026 y acumulan miles de valoraciones, pero esconden enfoques radicalmente distintos según lo que busques aprender o disfrutar.",
            f"En este cara a cara directo desglosamos sus ideas principales, ventajas reales y opiniones de lectores para que compres con total acierto y no pierdas ni un minuto en lecturas equivocadas.",
            f"Quédate con nosotros hasta el veredicto final para descubrir cuál encaja a la perfección con tu ritmo de lectura."
        ]
        hook = fit_section(hook, 85, hook_paragraphs)

        # PRODUCT A OVERVIEW (~125 palabras, con Micro-CTA)
        a_overview = script.get("product_a_overview", "").strip()
        a_overview_paragraphs = [
            f"{micro_cta_intro}",
            f"Comenzamos con la propuesta de {brand_a}, con la obra {title_a}.",
            f"Este título se comercializa en Amazon con un precio habitual de {price_a} y mantiene una sólida puntuación media de {rating_a}.",
            f"{brand_a} destaca por una estructura metódica y rigurosa, aportando conceptos profundos con ejemplos bien documentados que invitan a una reflexión seria.",
            f"Su redacción está sumamente cuidada, lo que convierte a este libro en una referencia imprescindible para quienes buscan dominar la materia paso a paso con rigor.",
            f"Cada capítulo aporta herramientas aplicables que justifican por qué se ha consolidado como un auténtico superventas en las listas literarias."
        ]
        a_overview = fit_section(a_overview, 120, a_overview_paragraphs, enforce_first_anchor=micro_cta_intro)

        # PRODUCT A REVIEWS (~100 palabras)
        a_reviews = script.get("product_a_reviews", "").strip()
        a_reviews_paragraphs = [
            f"Pasemos a analizar las opiniones reales de lectores verificados sobre {brand_a}: {pos_str_a}",
            f"En cuanto a las observaciones críticas de la comunidad lectora: {neg_str_a}",
            f"En conjunto, la percepción general confirma que es un texto denso y enriquecedor, ideal para quienes buscan conclusiones sólidas y aplicables a largo plazo.",
            f"La mayoría de los compradores coincide en que el valor que aporta compensa con creces el tiempo dedicado a su lectura reflexiva."
        ]
        a_reviews = fit_section(a_reviews, 95, a_reviews_paragraphs)

        # PRODUCT B OVERVIEW (~125 palabras)
        b_overview = script.get("product_b_overview", "").strip()
        b_overview_paragraphs = [
            f"Llega el turno de la alternativa directa de {brand_b}, titulada {title_b}.",
            f"Cuenta con una valoración media en Amazon de {rating_b} estrellas y se encuentra habitualmente a un precio de {price_b}.",
            f"A diferencia del enfoque anterior, la obra de {brand_b} apuesta por una narrativa mucho más fresca, dinámica y de rápida absorción.",
            f"Sus capítulos breves y anécdotas prácticas permiten avanzar a buen ritmo sin sobrecargar de teoría, siendo una opción magnífica para lectores que priorizan agilidad y motivación inmediata desde las primeras páginas.",
            f"Una alternativa moderna y vibrante diseñada para inspirarte y poner en práctica sus conclusiones desde el primer día."
        ]
        b_overview = fit_section(b_overview, 120, b_overview_paragraphs)

        # PRODUCT B REVIEWS (~100 palabras)
        b_reviews = script.get("product_b_reviews", "").strip()
        b_reviews_paragraphs = [
            f"Comprobemos ahora qué opinan quienes ya han completado la lectura de {brand_b}: {pos_str_b}",
            f"Respecto a los puntos que podrían mejorar según los compradores: {neg_str_b}",
            f"La valoración global resalta su capacidad de enganchar y transmitir aprendizajes claros sin tecnicismos innecesarios.",
            f"Los lectores aseguran que su ritmo ágil facilita terminarlo en pocos días, convirtiéndose en un libro de cabecera muy accesible."
        ]
        b_reviews = fit_section(b_reviews, 95, b_reviews_paragraphs)

        # COMPARISON (~125 palabras)
        comparison = script.get("comparison", "").strip()
        comparison_paragraphs = [
            f"Poniendo ambas obras frente a frente en esta comparativa de {query_title}, la decisión final depende de tus metas de lectura.",
            f"Si buscas un manual profundo, detallado y reflexivo para estudiar con calma, {brand_a} por {price_a} es la compra perfecta.",
            f"Si por el contrario prefieres una lectura estimulante, directa al grano y de fácil asimilación en tus ratos libres, {brand_b} por {price_b} responderá mejor a tus expectativas.",
            f"Ambos títulos justifican plenamente su inversión en Amazon según el momento formativo o de ocio en el que te encuentres.",
            f"Revisar tus hábitos de lectura habituales será la clave determinante para elegir el compañero ideal en tus próximas sesiones."
        ]
        comparison = fit_section(comparison, 120, comparison_paragraphs)

        # OUTRO (~85 palabras, con Veredicto Binario Contundente)
        outro = script.get("outro", "").strip()
        for weak in ["ambas son buenas opciones", "ambos son buenas opciones", "ambos son buenos", "cualquiera de los dos", "depende de tus gustos", "no declares un ganador"]:
            outro = re.sub(re.escape(weak), "", outro, flags=re.IGNORECASE)
        outro_paragraphs = [
            veredicto_binario,
            f"Cuéntanos abajo en la caja de comentarios cuál encaja mejor con tu perfil de lectura.",
            f"Si este análisis directo te ha servido de ayuda, apóyanos con un Like y suscríbete para más recomendaciones literarias contrastadas."
        ]
        outro = fit_section(outro, 80, outro_paragraphs, enforce_first_anchor=veredicto_binario)

    else:
        # Standard generic hardware / appliance / footwear / tech
        # HOOK (~90 palabras)
        hook = script.get("hook", "").strip()
        has_la = any(k in hook.lower() for k in ["error", "cuidado", "antes de comprar", "ahorrarte", "no compres", "gastes tu dinero", "decepción", "decepcion", "fallos", "tirar el dinero"])
        if not has_la or len(hook.split()) < 40:
            hook = ""
        hook_paragraphs = [
            f"¡Cuidado antes de comprar! Elegir a ciegas entre {brand_a} y {brand_b} puede hacerte tirar el dinero si no conoces sus diferencias técnicas clave y fallos reales.",
            f"Ambos modelos lideran las listas de ventas en Amazon España en 2026 con miles de reseñas positivas, pero responden a necesidades, hábitos de uso y presupuestos muy distintos.",
            f"En esta comparativa directa analizamos sus prestaciones a fondo y las opiniones reales de usuarios para que aciertes de pleno y no cometas un error innecesario.",
            f"Quédate con nosotros porque desgranamos cada punto fuerte y debilidad para que compres con total seguridad."
        ]
        hook = fit_section(hook, 85, hook_paragraphs)

        # PRODUCT A OVERVIEW (~125 palabras, con Micro-CTA)
        a_overview = script.get("product_a_overview", "").strip()
        a_overview_paragraphs = [
            f"{micro_cta_intro}",
            f"Arrancamos el análisis con el modelo de {brand_a}, concretamente {title_a}.",
            f"Se posiciona en Amazon con un precio aproximado de {price_a} y una destacada puntuación media de {rating_a} sobre 5 estrellas.",
            f"{brand_a} ha priorizado una construcción con materiales resistentes y acabados de gran nivel, pensados para soportar un uso continuo sin perder rendimiento.",
            f"Su diseño combina una notable comodidad con un funcionamiento eficiente y equilibrado, convirtiéndolo en un referente para quienes valoran ante todo fiabilidad y durabilidad a largo plazo.",
            f"Cuenta con detalles ergonómicos muy cuidados que facilitan su aprovechamiento al máximo en cualquier rutina diaria exigente."
        ]
        a_overview = fit_section(a_overview, 120, a_overview_paragraphs, enforce_first_anchor=micro_cta_intro)

        # PRODUCT A REVIEWS (~100 palabras)
        a_reviews = script.get("product_a_reviews", "").strip()
        a_reviews_paragraphs = [
            f"Analizando las opiniones de compradores verificados en Amazon sobre {brand_a}: {pos_str_a}",
            f"En cuanto a las objeciones y puntos críticos señalados por los usuarios: {neg_str_a}",
            f"Un desglose objetivo que te permite valorar con datos reales si sus especificaciones cumplen exactamente con tus expectativas diarias.",
            f"Varios usuarios coinciden en que, siguiendo las pautas de uso recomendadas, su comportamiento mecánico y eficacia se mantienen intactos con el paso de los meses."
        ]
        a_reviews = fit_section(a_reviews, 95, a_reviews_paragraphs)

        # PRODUCT B OVERVIEW (~125 palabras)
        b_overview = script.get("product_b_overview", "").strip()
        b_overview_paragraphs = [
            f"Turno ahora para su principal competidor: el modelo de {brand_b}, denominado {title_b}.",
            f"Cuenta con una valoración media en Amazon de {rating_b} estrellas y suele rondar un precio de referencia de {price_b}.",
            f"La propuesta de {brand_b} apuesta por un planteamiento más ligero, moderno y versátil, facilitando un manejo intuitivo desde el primer minuto.",
            f"Es la elección predilecta para usuarios dinámicos que buscan rapidez de uso, estética cuidada y una excelente relación calidad precio sin complicaciones técnicas.",
            f"Su ingeniería prioriza la practicidad cotidiana, logrando un equilibrio sobresaliente entre coste ajustado y prestaciones avanzadas."
        ]
        b_overview = fit_section(b_overview, 120, b_overview_paragraphs)

        # PRODUCT B REVIEWS (~100 palabras)
        b_reviews = script.get("product_b_reviews", "").strip()
        b_reviews_paragraphs = [
            f"Revisando las valoraciones de clientes tras meses de uso con {brand_b}: {pos_str_b}",
            f"En el lado crítico, las advertencias más comunes reportadas señalan: {neg_str_b}",
            f"Información transparente y sin filtros comerciales para que compares ambos productos con criterio profesional.",
            f"La inmensa mayoría de compradores destaca la agilidad y confort de este modelo frente a opciones tradicionales más pesadas de su segmento."
        ]
        b_reviews = fit_section(b_reviews, 95, b_reviews_paragraphs)

        # COMPARISON (~125 palabras)
        comparison = script.get("comparison", "").strip()
        comparison_paragraphs = [
            f"Poniendo ambos modelos frente a frente en esta comparativa de {query_title}, la decisión depende exclusivamente de tus prioridades.",
            f"Si tu objetivo es la máxima solidez estructural, resistencia y un rendimiento constante y fiable, el modelo de {brand_a} por {price_a} es tu mejor elección.",
            f"Si prefieres mayor versatilidad, ligereza y optimizar tu presupuesto al céntimo, la propuesta de {brand_b} por {price_b} te resultará más atractiva.",
            f"Ambos modelos justifican plenamente su inversión en Amazon dentro de sus respectivas categorías de precio.",
            f"Evalúa detenidamente la intensidad de uso que piensas darle para rentabilizar al máximo cada euro invertido."
        ]
        comparison = fit_section(comparison, 120, comparison_paragraphs)

        # OUTRO (~85 palabras, con Veredicto Binario Contundente)
        outro = script.get("outro", "").strip()
        for weak in ["ambas son buenas opciones", "ambos son buenas opciones", "ambos son buenos", "cualquiera de los dos", "depende de tus gustos", "no declares un ganador"]:
            outro = re.sub(re.escape(weak), "", outro, flags=re.IGNORECASE)
        outro_paragraphs = [
            veredicto_binario,
            f"Déjanos en comentarios cuál encaja mejor con tus necesidades reales.",
            f"Si este cara a cara te ha ahorrado tiempo y dinero, déjanos un Like y suscríbete para estar al día de las mejores ofertas activas de Amazon."
        ]
        outro = fit_section(outro, 80, outro_paragraphs, enforce_first_anchor=veredicto_binario)

    data["script"] = {
        "hook": hook,
        "product_a_overview": a_overview,
        "product_a_reviews": a_reviews,
        "product_b_overview": b_overview,
        "product_b_reviews": b_reviews,
        "comparison": comparison,
        "outro": outro
    }

    with open(data_json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    all_texts = [hook, a_overview, a_reviews, b_overview, b_reviews, comparison, outro]
    total_words = sum(len(t.split()) for t in all_texts)
    est_minutes = round(total_words / 165, 2)  # Kokoro 1.05x speed: ~165 words/min
    print(json.dumps({
        "status": "enriched_vs",
        "query": query,
        "total_words": total_words,
        "est_minutes": est_minutes,
        "is_book_channel": is_book_channel,
        "target_range": "700-850 words (4:00 - 4:45 min)"
    }))

if __name__ == "__main__":
    main()
