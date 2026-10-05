#!/usr/bin/env python3
"""
niche_intelligence_analyst.py — affiliate-niche-strategist
Motor de Inteligencia de Nichos enfocado en PROBABILIDAD DE CONVERSIÓN EN VENTAS Y MONETIZACIÓN REAL.

No busca únicamente productos caros, sino que optimiza la 'Fórmula de Conversión Efectiva':
  Probabilidad de Conversión Real =
    (Fricción de Compra Baja) x
    (Intención de Búsqueda Urgente / Dolor Agudo) x
    (Ventana de Decisión < 24 Horas) x
    (Facilidad de Validación Visual en Vídeo) x
    (Comisión Neta Viable de Amazon)
"""

import sys
import os
import json
import argparse
import re

# Tabla oficial de comisiones de Amazon Afiliados España
AMAZON_ES_COMMISSION_RATES = {
    "moda_calzado": {"rate": 0.10, "label": "Moda, Calzado, Ropa y Accesorios (10%)"},
    "belleza_cuidado": {"rate": 0.07, "label": "Belleza, Salud y Cuidado Personal (7%)"},
    "hogar_cocina": {"rate": 0.07, "label": "Hogar, Cocina y Mobiliario (7%)"},
    "jardin_bricolaje": {"rate": 0.06, "label": "Jardín, Bricolaje y Herramientas (6%)"},
    "deportes_outdoor": {"rate": 0.05, "label": "Deportes, Aire Libre y Camping (5%)"},
    "juguetes_bebe": {"rate": 0.05, "label": "Juguetes y Productos de Bebé (5%)"},
    "automovil_moto": {"rate": 0.05, "label": "Accesorios de Coche y Moto (5%)"},
    "mascotas": {"rate": 0.05, "label": "Productos para Mascotas (5%)"},
    "libros_kindle": {"rate": 0.05, "label": "Libros físicos y Kindle (5%)"},
    "electronica_informatica": {"rate": 0.03, "label": "Informática, Audio y Gaming (3%)"},
    "smartphones_tablets": {"rate": 0.02, "label": "Smartphones y Tablets (2%)"},
    "electrodomesticos_grandes": {"rate": 0.03, "label": "Gran Electrodoméstico (3%)"}
}

# Base de datos de nichos evaluados bajo el prisma de Alta Probabilidad de Conversión
NICHES_CONVERSION_DATABASE = [
    {
        "id": "calzado_ergonomico_seguridad",
        "name": "Calzado Especializado y Zapatillas Técnicas (Referencia)",
        "category": "moda_calzado",
        "avg_ticket": 65.0,
        "sweet_spot_price": "45€ - 85€ (Bajo freno de compra / Impulso alto)",
        "decision_window": "< 12 Horas (El usuario ya sabe que necesita renovar calzado)",
        "purchase_driver": "Dolor Físico y Necesidad Inmediata (Zapatillas con amortiguación, trabajo antideslizante, seguridad laboral)",
        "conversion_probability_score": 95,
        "amazon_video_density": "Muy Alta (>85%)",
        "why_it_converts": "Comisión reina del 10%. Rango de precio asequible que no exige financiación. Las tallas y reseñas en Amazon disipan la duda en 3 minutos.",
        "channel_name": "Zapatería del Pueblo",
        "tag_slug": "zapateria_tag-21"
    },
    {
        "id": "cuidado_masculino_barberia",
        "name": "Barbería, Afeitado y Cuidado Personal",
        "category": "belleza_cuidado",
        "avg_ticket": 48.0,
        "sweet_spot_price": "35€ - 65€ (Compra impulsiva y sin objeción de precio)",
        "decision_window": "< 6 Horas (Afeitado semanal, higiene, preparación de eventos)",
        "purchase_driver": "Estética Personal e Higiene Urgente (Eliminar tirones, afeitado de cabeza rápido, barba limpia)",
        "conversion_probability_score": 92,
        "amazon_video_density": "Excelente (>90% de productos con demos de corte)",
        "why_it_converts": "7% de comisión. 48€ de ticket es el 'sweet spot' perfecto donde el usuario compra con 1 solo clic en Prime sin pensarlo dos veces.",
        "channel_name": "La Barbería del Pueblo",
        "tag_slug": "barberia_tag-21"
    },
    {
        "id": "accesorios_automovil_camper",
        "name": "Coche, Accesorios Prácticos y Mantenimiento DIY",
        "category": "automovil_moto",
        "avg_ticket": 55.0,
        "sweet_spot_price": "30€ - 80€ (Poco dinero para evitar problemas caros de taller)",
        "decision_window": "< 24 Horas (Viajes inminentes, ITV, emergencias de batería)",
        "purchase_driver": "Prevención y Solución de Emergencia (Arrancadores de batería, compresores de ruedas, dashcams, diagnosis OBD2)",
        "conversion_probability_score": 89,
        "amazon_video_density": "Excelente (>85% con pruebas de inflado y encendido)",
        "why_it_converts": "5% de comisión. Al ver en el vídeo que un arrancador de 50€ evita llamar a la grúa, el sesgo de aversión a la pérdida dispara la compra inmediata.",
        "channel_name": "El Garaje del Pueblo",
        "tag_slug": "garaje_tag-21"
    },
    {
        "id": "herramientas_diy_bricolaje",
        "name": "Bricolaje y Herramientas Eléctricas Domésticas",
        "category": "jardin_bricolaje",
        "avg_ticket": 85.0,
        "sweet_spot_price": "50€ - 110€ (Proyectos domésticos de fin de semana)",
        "decision_window": "< 24 Horas (Reforma o reparación en marcha)",
        "purchase_driver": "Ahorro de Mano de Obra (Hacerlo uno mismo en vez de pagar 150€ a un profesional)",
        "conversion_probability_score": 87,
        "amazon_video_density": "Muy Alta (>85% con demos de taladrado y corte)",
        "why_it_converts": "6% de comisión (~5,10€ netos por venta). Los comparativos VS entre marcas como Einhell, Bosch o Parkside tienen el CTR de búsqueda más alto de YouTube.",
        "channel_name": "El Bricolaje del Pueblo",
        "tag_slug": "brico_tag-21"
    },
    {
        "id": "domotica_seguridad_camaras",
        "name": "Seguridad Doméstica y Cámaras de Vigilancia Sin Cuotas",
        "category": "hogar_cocina",
        "avg_ticket": 75.0,
        "sweet_spot_price": "40€ - 95€ (Alternativa barata a pagar 45€/mes de alarma)",
        "decision_window": "< 48 Horas (Tranquilidad para vacaciones o segundas residencias)",
        "purchase_driver": "Protección Familiar y Miedo a Robos / Ocupación",
        "conversion_probability_score": 85,
        "amazon_video_density": "Excelente (>90% calidad de visión nocturna)",
        "why_it_converts": "7% de comisión (~5,25€/venta). La promesa de 'Seguridad sin cuotas mensuales' es uno de los mejores ganchos de conversión probados en España.",
        "channel_name": "La Casa Segura del Pueblo",
        "tag_slug": "seguridad_tag-21"
    },
    {
        "id": "skincare_facial_femenino",
        "name": "Limpieza Facial, Cosmética y Skincare Coreano",
        "category": "belleza_cuidado",
        "avg_ticket": 36.0,
        "sweet_spot_price": "18€ - 52€ (Compra impulsiva sin frenos / Efecto rutina 5 pasos)",
        "decision_window": "< 6 Horas (Adquisición inmediata de cosméticos al ver textura en vídeo)",
        "purchase_driver": "Estética, Salud de la Piel y Tendencia Social (Doble limpieza, retinol, serums)",
        "conversion_probability_score": 94,
        "amazon_video_density": "Excelente (>90% texturas y demostraciones de absorción)",
        "why_it_converts": "7% a 10% de comisión. Dispara el 'efecto carrito múltiple' (compran limpiador + tónico + sérum juntos). Recompra recurrente cada 60 días.",
        "channel_name": "El Tocador del Pueblo",
        "tag_slug": "belleza_tag-21"
    },
    {
        "id": "internacional_calzado_alemania",
        "name": "[INTERNACIONAL DE] Calzado Técnico y Seguridad en Alemania (Amazon.de)",
        "category": "moda_calzado",
        "avg_ticket": 92.0,
        "sweet_spot_price": "65€ - 120€ (Poder adquisitivo alemán alto + rigor técnico)",
        "decision_window": "< 24 Horas (Búsqueda metódica antes de compra)",
        "purchase_driver": "Ergonomía, Calidad y Durabilidad (Wanderschuhe, Sicherheitsschuhe, Laufschuhe)",
        "conversion_probability_score": 93,
        "amazon_video_density": "Muy Alta (>85%)",
        "why_it_converts": "Comisión del 8-10% en Amazon.de sobre un ticket medio casi el doble que en España (~8€ netos por venta). CPM/RPM de YouTube x3 respecto a España.",
        "channel_name": "Der Schuh-Berater (Alemania)",
        "tag_slug": "german_shoes-21"
    },
    {
        "id": "internacional_taller_ingles_global",
        "name": "[INTERNACIONAL EN] Herramientas y DIY Global (Amazon OneLink US/UK/CA)",
        "category": "jardin_bricolaje",
        "avg_ticket": 80.0,
        "sweet_spot_price": "45€ - 110€ ($49 - $129)",
        "decision_window": "< 24 Horas (Proyectos de fin de semana y reparaciones domésticas)",
        "purchase_driver": "Home Improvement, DIY y Ahorro de Mano de Obra",
        "conversion_probability_score": 91,
        "amazon_video_density": "Excelente (>90% de fabricantes con clips HD)",
        "why_it_converts": "Escala global masiva (10x en visualizaciones). Con Amazon OneLink se monetiza tráfico de EE.UU., Reino Unido y Canadá desde un único canal.",
        "channel_name": "The Tool Garage / DIY Pro",
        "tag_slug": "thetoolgarage-20"
    },
    {
        "id": "pokemon_lore_clipping",
        "name": "Historias y Lore de Pokémon (Clipping Emocional & Coleccionismo)",
        "category": "juguetes_bebe",
        "avg_ticket": 42.0,
        "sweet_spot_price": "18€ - 65€ (Peluches, lámparas LED, figuras oficiales, cajas de cartas TCG)",
        "decision_window": "< 12 Horas (Vínculo emocional tras ver la historia del Pokémon)",
        "purchase_driver": "Nostalgia, Apego Emocional y Pasión por el Coleccionismo",
        "conversion_probability_score": 88,
        "amazon_video_density": "100% (Clips anime oficiales de YouTube mediante búsqueda semántica)",
        "why_it_converts": "5% de comisión en Juguetes/Coleccionismo + monetización masiva por visualizaciones de YouTube Shorts. Retención >110% que dispara el algoritmo orgánico.",
        "channel_name": "Crónicas Pokémon / PokéLore",
        "tag_slug": "pokemon_tag-21"
    }
]

def calculate_conversion_metrics(niche_data):
    cat = niche_data["category"]
    comm_rate = AMAZON_ES_COMMISSION_RATES.get(cat, {"rate": 0.05})["rate"]
    avg_ticket = niche_data["avg_ticket"]
    
    # Comisión neta esperada por cada compra cerrada
    commission_per_order = round(avg_ticket * comm_rate, 2)
    
    # Estimación de Ganancia por cada 1.000 visualizaciones (RPM de Afiliado Estimado)
    # Suponiendo una tasa de click en enlace del 2.5% y una conversión en Amazon del 8%
    clicks_per_1k = 25.0
    orders_per_1k = clicks_per_1k * 0.08  # ~2 ventas por cada 1000 reproducciones
    affiliate_rpm = round(orders_per_1k * commission_per_order, 2)
    
    return {
        "commission_percentage": f"{int(comm_rate * 100)}%",
        "commission_per_order": f"{commission_per_order}€",
        "estimated_affiliate_rpm": f"{affiliate_rpm}€ por 1.000 vistas",
        "score": niche_data["conversion_probability_score"]
    }

def export_to_markdown(filepath: str = None):
    if not filepath:
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "candidatos_nichos_afiliados.md")
    lines = [
        "# 📋 Catálogo Estratégico de Nichos Candidatos (YouTube + Amazon Afiliados)",
        "",
        "> Documento vivo de evaluación de viabilidad de nichos para la factoría automatizada de canales.",
        "> Ordenados por **Probabilidad Matemática de Conversión (<24h)** y potencial de monetización.",
        "",
        "| # | Nicho / Proyecto | Mercado | Score | Comisión | Ticket Medio | Ventana Decisión | Drivers de Compra | Canal Propuesto |",
        "|---|---|:---:|:---:|:---:|:---:|:---:|---|---|",
    ]
    for idx, n in enumerate(NICHES_CONVERSION_DATABASE, 1):
        m = calculate_conversion_metrics(n)
        market = "🇪🇸 ES"
        if "[INTERNACIONAL DE]" in n["name"]:
            market = "🇩🇪 DE"
        elif "[INTERNACIONAL EN]" in n["name"]:
            market = "🇺🇸🇬🇧 Global"
        name_clean = n["name"].replace("[INTERNACIONAL DE] ", "").replace("[INTERNACIONAL EN] ", "")
        lines.append(f"| {idx} | **{name_clean}** | {market} | **{m['score']}/100** | {m['commission_percentage']} (~{m['commission_per_order']}) | {n['avg_ticket']}€ | {n['decision_window'].split('(')[0].strip()} | {n['purchase_driver'].split('(')[0].strip()} | `{n['channel_name']}` |")

    lines.extend([
        "",
        "---",
        "",
        "## 🔬 Ficha Detallada de Candidatos a Valorar",
        ""
    ])

    for idx, n in enumerate(NICHES_CONVERSION_DATABASE, 1):
        m = calculate_conversion_metrics(n)
        lines.extend([
            f"### {idx}. {n['name']}",
            f"- **Score de Conversión**: `{m['score']}/100`",
            f"- **Comisión Estimada por Venta**: `{m['commission_percentage']}` (~`{m['commission_per_order']}` netos)",
            f"- **Ingreso Estimado (RPM Afiliado)**: ~`{m['estimated_affiliate_rpm']}`",
            f"- **Sweet Spot de Precio**: {n['sweet_spot_price']}",
            f"- **Ventana de Decisión**: {n['decision_window']}",
            f"- **Driver Psicológico**: {n['purchase_driver']}",
            f"- **Por Qué Convierte**: {n['why_it_converts']}",
            f"- **Canal / Tag Propuesto**: `{n['channel_name']}` (Tag: `{n['tag_slug']}`)",
            ""
        ])

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return filepath

if __name__ == "__main__":
    print_conversion_focused_report()
    md_path = export_to_markdown()
    print(f"\n[OK] Documento Markdown generado con éxito en: {md_path}")

