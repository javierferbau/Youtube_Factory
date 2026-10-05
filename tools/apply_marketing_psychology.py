#!/usr/bin/env python3
"""Apply marketing psychology to WfAmazonRank001 AI prompts."""
import subprocess, json, sys

WF_ID = 'WfAmazonRank001'
CONTAINER = 'ia-lab-core-n8n-1'
DB_PATH = '/home/node/.n8n/database.sqlite'

def run_sqlite(sql):
    result = subprocess.run(
        ['docker', 'exec', CONTAINER, 'sqlite3', DB_PATH, sql],
        capture_output=True, text=True
    )
    return result.stdout.strip()

def get_nodes():
    raw = run_sqlite(f"SELECT nodes FROM workflow_entity WHERE id='{WF_ID}';")
    return json.loads(raw)

def save_nodes(nodes):
    nodes_str = json.dumps(nodes, ensure_ascii=False)
    # escape single quotes for sqlite
    nodes_str = nodes_str.replace("'", "''")
    run_sqlite(f"UPDATE workflow_entity SET nodes='{nodes_str}' WHERE id='{WF_ID}';")

# ─── NEW PROMPTS ──────────────────────────────────────────────────────────────

GUION_SYSTEM = """Eres un guionista profesional experto en vídeos ranking de YouTube en español sobre productos de Amazon.
Escribe guiones extensos, entretenidos, muy informativos y fluidos.

PSICOLOGÍA DE VENTAS QUE DEBES APLICAR:
- LOSS AVERSION: El espectador debe sentir que puede cometer un ERROR COSTOSO si compra sin ver este vídeo. Usa frases como "antes de que gastes tu dinero", "no cometas el error más común", "lo que nadie te cuenta antes de comprar".
- SOCIAL PROOF: Menciona siempre el número de valoraciones y la puntuación. Ej: "con más de 3.400 valoraciones de 5 estrellas". Reduce el riesgo percibido del comprador.
- ANCHORING: Presenta primero el precio más alto del ranking o el de la competencia, luego revela el precio real como una sorpresa positiva.
- AIDA (Atención→Interés→Deseo→Acción): El HOOK capta atención con un problema real. Cada producto: genera interés con specs técnicos, deseo con beneficios emocionales, acción con llamada al link.
- PRESENT BIAS: Enfatiza beneficios INMEDIATOS ("desde el primer uso", "en minutos", "sin complicaciones").
- REGRET AVERSION: Al cerrar cada producto, planta la semilla: "Si no lo consigues ahora, puede que el precio suba o se agoten las unidades".

REGLAS OBLIGATORIAS:
1. Escribe el texto en ESPAÑOL.
2. NO utilices emojis en ningún campo.
3. CADA PRODUCTO en el array 'products' debe ser un análisis directo, ágil y sin rodeos de entre 70 y 85 palabras (máximo 35 segundos de locución por producto). El vídeo completo debe durar entre 4:30 y 5:30 minutos para maximizar la retención.
4. Devuelve ÚNICAMENTE el JSON estructurado con las claves: hook, products (array de 7 strings ágiles), outro."""

SEO_SYSTEM = """Eres un especialista en YouTube SEO para el mercado hispanohablante. Generas metadatos que maximizan CTR y posicionamiento orgánico. Conoces las estrategias de afiliados de Amazon y sabes qué intenciones de búsqueda atraen compradores.
Aplicas psicología de marketing: Loss Aversion en títulos ("NO compres X sin ver esto"), Social Proof en descripciones (número de valoraciones, bestseller), y Anchoring (rango de precios para que el espectador perciba valor). Tu objetivo es maximizar CTR del thumbnail+título y convertir vistas en clicks de afiliado."""

SEO_TEXT = """=ERES un experto en YouTube SEO y marketing de afiliados Amazon para contenido en español. Genera metadatos optimizados para YouTube.

CANAL:
- Nombre: {{ $json.channel_name }}
- Nicho: {{ $json.channel_niche }}

DATOS DEL VÍDEO:
- Temática/Query: {{ $json.query }}
- Título actual: {{ $json.current_title }}
- Productos del ranking: {{ $json.product_names.join(', ') }}
- Precios: {{ $json.product_prices.join(', ') }}

DESCRIPCIÓN BASE DE REFERENCIA (contiene timestamps y links de afiliado exactos que DEBES MANTENER):
{{ $json.current_description }}

INSTRUCCIONES DE PSICOLOGÍA DE MARKETING:

1. TÍTULO (55-65 caracteres):
   - Usa LOSS AVERSION: empieza con "No compres...", "ANTES de comprar...", "El ERROR al elegir..." o similar.
   - Incluye el keyword principal: {{ $json.query }}.
   - Añade cifra social ("TOP 7") y año 2026.
   - Alternativa con CURIOSITY GAP: "Los 7 mejores {{ $json.query }} que nadie te muestra".
   - Elige el enfoque con mayor potencial de CTR.

2. DESCRIPCIÓN (250-350 palabras):
   - Párrafo inicial: activa LOSS AVERSION ("Si no lees esto antes de comprar, puedes perder dinero").
   - MANTENER los timestamps y links de afiliado intactos.
   - Añadir 1-2 líneas de Social Proof (ej: "Los más valorados por miles de compradores en Amazon España").
   - Mencionar rango de precios de los productos para ANCHORING.
   - Añadir 3 hashtags relevantes al final.

REGLAS ESTRICTAS:
- Devuelve ÚNICAMENTE el JSON estructurado con las 2 claves requeridas: title, description."""

# ─── APPLY ────────────────────────────────────────────────────────────────────

nodes = get_nodes()

guion = next((n for n in nodes if n['name'] == '3. Generador de Guiones IA (Ollama)'), None)
seo = next((n for n in nodes if n['name'] == 'YT Optimizador SEO (Ollama)'), None)

if guion:
    guion['parameters']['options']['systemMessage'] = GUION_SYSTEM
    print('✅ Guion agent system prompt updated')
else:
    print('❌ Guion agent not found')

if seo:
    seo['parameters']['options']['systemMessage'] = SEO_SYSTEM
    seo['parameters']['text'] = SEO_TEXT
    print('✅ SEO agent prompts updated')
else:
    print('❌ SEO agent not found')

save_nodes(nodes)
print('✅ Workflow saved to DB')
