#!/usr/bin/env python3
"""
test_metadata_scripts.py
Pruebas unitarias e integrales locales sin lanzar workflows en n8n.
Verifica que save_vs_youtube_metadata.py y generate_vs_short_metadata.py
generen metadatos impecables para todos los nichos de la carpeta Affiliate:
- Cocina Tecnológica
- Limpieza del Pueblo
- Calzado del Pueblo
- Librería Del Pueblo
- Nicho Genérico / Otros
"""

import os
import sys
import json
import tempfile
import subprocess

TEST_CASES = [
    {
        "niche": "Cocina Tecnológica",
        "canal_nombre": "la_cocina_tecnologica_del_pueblo",
        "query": "freidoras de aire de doble cesta",
        "affiliate_tag": "cocina_tag-21",
        "product_a": {
            "title": "Cecotec Freidora de Aire sin Aceite 9 L Cecofry Dual 9000. 2850 W, Doble Cesta con Temperatura Dual",
            "brand": "Cecotec",
            "price": "89,90€",
            "rating": "4.5 de 5 estrellas",
            "asin": "B0B8X9YZ12"
        },
        "product_b": {
            "title": "Cosori Freidora de Aire 8.5L Doble Cesta Dual Blaze con 2 Elementos Calefactores",
            "brand": "Cosori",
            "price": "149,99€",
            "rating": "4.7 de 5 estrellas",
            "asin": "B0C9X8WV34"
        },
        "forbidden_words": ["librería", "libro", "lectura", "literaria", "zapato"]
    },
    {
        "niche": "Limpieza del Pueblo",
        "canal_nombre": "limpiezadelpueblo",
        "query": "aspiradoras de mano sin cable",
        "affiliate_tag": "limpieza_tag-21",
        "product_a": {
            "title": "Aspiradora sin Hilo de Coche 27000Pa Aspiradora para Mascotas 4 en 1",
            "brand": "Aspiradora",
            "price": "32,99€",
            "rating": "4.6 de 5 estrellas",
            "asin": "B0H2DJCPB7"
        },
        "product_b": {
            "title": "Einhell Aspiradora de Mano con batería TE-VC 18 Li solo Power X-Change",
            "brand": "Einhell",
            "price": "65,00€",
            "rating": "4.6 de 5 estrellas",
            "asin": "B0BV288KNZ"
        },
        "forbidden_words": ["librería", "libro", "lectura", "literaria", "cocina"]
    },
    {
        "niche": "Calzado del Pueblo",
        "canal_nombre": "calzadodelpueblo",
        "query": "zapatillas de running para hombre",
        "affiliate_tag": "calzado_tag-21",
        "product_a": {
            "title": "Nike Revolution 6 NN Zapatillas de Running para Hombre",
            "brand": "Nike",
            "price": "54,95€",
            "rating": "4.4 de 5 estrellas",
            "asin": "B091234567"
        },
        "product_b": {
            "title": "Adidas Duramo SL Zapatillas de Entrenamiento para Hombre",
            "brand": "Adidas",
            "price": "49,99€",
            "rating": "4.5 de 5 estrellas",
            "asin": "B098765432"
        },
        "forbidden_words": ["librería", "libro", "lectura", "literaria", "aspiradora"]
    },
    {
        "niche": "Barbería del Pueblo",
        "canal_nombre": "labarberiadelpueblo",
        "query": "afeitadoras electricas hombre",
        "affiliate_tag": "barberia_tag-21",
        "product_a": {
            "title": "Braun Series 9 Pro Afeitadora Eléctrica Hombre",
            "brand": "Braun",
            "price": "299,99€",
            "rating": "4.6 de 5 estrellas",
            "asin": "B09ABC1234"
        },
        "product_b": {
            "title": "Philips Shaver Series 7000 Afeitadora Eléctrica Barba",
            "brand": "Philips",
            "price": "149,99€",
            "rating": "4.5 de 5 estrellas",
            "asin": "B09DEF5678"
        },
        "forbidden_words": ["librería", "libro", "lectura", "cocina", "zapato"]
    },
    {
        "niche": "Librería Del Pueblo",
        "canal_nombre": "libreria_del_pueblo",
        "query": "libros de psicologia",
        "affiliate_tag": "libreria_tag-21",
        "product_a": {
            "title": "El hombre en busca de sentido (Edición Especial)",
            "brand": "Viktor E. Frankl",
            "price": "12,90€",
            "rating": "4.8 de 5 estrellas",
            "asin": "B081111111"
        },
        "product_b": {
            "title": "Cómo hacer que te pasen cosas buenas",
            "brand": "Marian Rojas Estapé",
            "price": "18,90€",
            "rating": "4.7 de 5 estrellas",
            "asin": "B082222222"
        },
        "forbidden_words": ["aspiradora", "freidora", "zapato"]
    },
    {
        "niche": "El Taller Del Pueblo",
        "canal_nombre": "el_taller_del_pueblo",
        "query": "taladros percutores a bateria",
        "affiliate_tag": "taller_tag-21",
        "product_a": {
            "title": "Bosch Professional 18V System Taladro percutor a batería GSB 18V-55",
            "brand": "Bosch Professional",
            "price": "149,99€",
            "rating": "4.7 de 5 estrellas",
            "asin": "B0821J7L8D"
        },
        "product_b": {
            "title": "DeWalt DCD796D2-QW Taladro Percutor a Batería XR 18V con 2 baterías Li-Ion 2.0Ah",
            "brand": "DeWalt",
            "price": "189,00€",
            "rating": "4.6 de 5 estrellas",
            "asin": "B01CK70U6Y"
        },
        "forbidden_words": ["librería", "libro", "lectura", "cocina", "zapato", "afeitadora"]
    }
]

def run_tests():
    print("=== INICIANDO BATERÍA DE PRUEBAS LOCALES DE METADATOS (SIN LANZAR WORKFLOWS) ===\n")
    all_passed = True

    for test in TEST_CASES:
        niche_name = test["niche"]
        print(f"Testing Nicho: [{niche_name}]...")

        with tempfile.TemporaryDirectory() as tmpdir:
            data_content = {
                "query": test["query"],
                "canal_nombre": test["canal_nombre"],
                "affiliate_tag": test["affiliate_tag"],
                "product_a": test["product_a"],
                "product_b": test["product_b"]
            }
            data_file = os.path.join(tmpdir, "data.json")
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump(data_content, f, ensure_ascii=False, indent=2)

            # 1. Test save_vs_youtube_metadata.py
            cmd_vs = ["python3", "/home/javierferb/n8n/tools/save_vs_youtube_metadata.py", tmpdir, "--affiliate_tag", test["affiliate_tag"]]
            res_vs = subprocess.run(cmd_vs, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if res_vs.returncode != 0:
                print(f"❌ FAIL: save_vs_youtube_metadata.py falló con error: {res_vs.stderr}")
                all_passed = False
                continue

            meta_file = os.path.join(tmpdir, "youtube_metadata.json")
            assert os.path.exists(meta_file), "youtube_metadata.json no se creó"
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)

            title = meta.get("youtube_title", "")
            desc = meta.get("youtube_description", "")
            tags_str = meta.get("tags_str", "")

            # Assertions para VS Horizontal
            assert len(title) > 5, "Título demasiado corto"
            assert len(title) <= 95, f"Título excede 95 caracteres: {len(title)}"
            assert len(desc) > 100, "Descripción demasiado corta"
            assert test["affiliate_tag"] in desc, f"Tag afiliado {test['affiliate_tag']} no presente en descripción"

            # Check forbidden words (para evitar mezclas de nichos)
            for word in test["forbidden_words"]:
                assert word.lower() not in desc.lower(), f"Palabra prohibida '{word}' encontrada en descripción de {niche_name}"

            # Check hashtag safety (ningún hashtag individual > 30 chars sin espacios)
            for tag in desc.splitlines()[-1].split():
                if tag.startswith("#"):
                    assert len(tag) <= 35, f"Hashtag demasiado largo ({len(tag)} chars): {tag}"

            print(f"  ✓ Metadatos Horizontal VS OK: Título ({len(title)}c), Desc ({len(desc)}c)")

            # 2. Test generate_vs_short_metadata.py
            cmd_short = ["python3", "/home/javierferb/n8n/tools/generate_vs_short_metadata.py", tmpdir, "--affiliate_tag", test["affiliate_tag"]]
            res_short = subprocess.run(cmd_short, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if res_short.returncode != 0:
                print(f"❌ FAIL: generate_vs_short_metadata.py falló con error: {res_short.stderr}")
                all_passed = False
                continue

            short_meta_file = os.path.join(tmpdir, "short_metadata.json")
            assert os.path.exists(short_meta_file), "short_metadata.json no se creó"
            with open(short_meta_file, "r", encoding="utf-8") as f:
                short_meta = json.load(f)

            stitle = short_meta.get("youtube_title", "")
            sdesc = short_meta.get("youtube_description", "")

            assert len(stitle) > 5, "Título Short corto"
            assert len(stitle) <= 95, f"Título Short excede 95 chars: {len(stitle)}"
            assert len(sdesc) > 30, "Descripción Short corta"
            
            for word in test["forbidden_words"]:
                assert word.lower() not in sdesc.lower(), f"Palabra prohibida '{word}' en Short de {niche_name}"

            print(f"  ✓ Metadatos Vertical Short VS OK: Título ({len(stitle)}c), Desc ({len(sdesc)}c)\n")

    if all_passed:
        print("🎉 TODOS LOS TESTS HAN PASADO CON ÉXITO 100% EMPÍRICO Y CERO ERRORES.")
    else:
        print("❌ ALGUNAS PRUEBAS FALLARON.")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
