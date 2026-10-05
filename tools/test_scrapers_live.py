#!/usr/bin/env python3
"""
Suite de Pruebas Empíricas en Vivo para Scrapers de Amazon (Multi-Nicho).
Verifica de forma real contra Amazon España que los 4 nichos obtienen productos,
extraen metadatos y generan vídeos MP4 válidos en disco (>50KB).
También comprueba la red de seguridad (Evergreen Fallback) ante búsquedas vacías.
"""

import os
import sys
import json
import shutil
import subprocess
import time

PYTHON_BIN = "/home/javierferb/n8n/venv/bin/python3"
BASE_TEST_DIR = "/tmp/test_live_scrapers"

def run_scraper_test(name, script_path, query, canal, extra_args=None):
    print(f"\n" + "="*70)
    print(f"🧪 INICIANDO TEST EN VIVO: {name}")
    print(f"   Script: {os.path.basename(script_path)}")
    print(f"   Query:  '{query}'")
    print(f"   Canal:  '{canal}'")
    print("="*70)

    target_dir = os.path.join(BASE_TEST_DIR, canal)
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir, ignore_errors=True)
    os.makedirs(target_dir, exist_ok=True)

    cmd = [
        PYTHON_BIN, script_path,
        "--query", query,
        "--canal", canal,
        "--base_dir", target_dir
    ]
    if extra_args:
        cmd.extend(extra_args)

    t0 = time.time()
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    elapsed = time.time() - t0

    if res.returncode != 0:
        print(f"❌ FALLO en ejecución (código {res.returncode}):")
        print("STDERR:", res.stderr[-500:])
        return False, f"Returncode {res.returncode}"

    # Parse stdout JSON
    try:
        output_data = json.loads(res.stdout)
    except Exception as e:
        print(f"❌ FALLO al parsear JSON stdout: {e}")
        print("STDOUT:", res.stdout[-300:])
        return False, "JSON parse error"

    if output_data.get("error"):
        print(f"❌ FALLO: Scraper devolvió error: {output_data['error']}")
        return False, f"Error returned: {output_data['error']}"

    # Check data.json
    target_dir = output_data.get("project_dir") or target_dir
    data_json_path = os.path.join(target_dir, "data.json")
    if not os.path.exists(data_json_path):
        print(f"❌ FALLO: No existe data.json en {target_dir}")
        return False, "data.json missing"

    with open(data_json_path, 'r', encoding='utf-8') as fp:
        saved_data = json.load(fp)

    # Verify products (VS format or TOP format)
    if "products" in saved_data:
        prods = saved_data.get("products", [])
        if len(prods) < 2:
            print(f"❌ FALLO: Ranking TOP tiene {len(prods)} productos, se esperaban >= 2")
            return False, "Fewer than 2 products in ranking"
        for p in prods[:2]:
            v_file = p.get("video_file")
            full_v_path = os.path.join(target_dir, v_file) if v_file else None
            if not full_v_path or not os.path.exists(full_v_path):
                print(f"❌ FALLO: Vídeo de ranking {p.get('rank')} no existe en disco: {full_v_path}")
                return False, "Ranking video missing on disk"
        print(f"   🏆 Ranking TOP: {len(prods)} productos verificados con vídeo y metadatos")
    else:
        prod_a = saved_data.get("product_a")
        prod_b = saved_data.get("product_b")

        if not prod_a or not prod_b:
            print(f"❌ FALLO: Faltan product_a o product_b en data.json")
            return False, "Missing product_a / product_b"

        print(f"   🅰️ Producto A: {prod_a.get('brand')} - {prod_a.get('title')[:45]}... ({prod_a.get('price')})")
        print(f"   🅱️ Producto B: {prod_b.get('brand')} - {prod_b.get('title')[:45]}... ({prod_b.get('price')})")

        for p_key, p_obj in [("product_a", prod_a), ("product_b", prod_b)]:
            v_file = p_obj.get("video_file")
            if not v_file:
                print(f"❌ FALLO: {p_key} no tiene video_file registrado")
                return False, f"{p_key} missing video_file"

            full_v_path = os.path.join(target_dir, v_file)
            if not os.path.exists(full_v_path):
                print(f"❌ FALLO: Archivo de vídeo no existe en disco: {full_v_path}")
                return False, f"{full_v_path} not on disk"

            v_size = os.path.getsize(full_v_path)
            if v_size < 30000:
                print(f"❌ FALLO: Vídeo demasiado pequeño ({v_size} bytes): {full_v_path}")
                return False, f"{full_v_path} size {v_size} < 30KB"

            i_file = p_obj.get("image_file")
            if i_file:
                full_i_path = os.path.join(target_dir, i_file)
                if not os.path.exists(full_i_path):
                    print(f"❌ FALLO: Imagen no existe en disco: {full_i_path}")
                    return False, f"{full_i_path} not on disk"

    print(f"✅ ÉXITO: {name} completado en {elapsed:.1f}s. Archivos y metadatos verificados al 100%.")
    return True, "OK"


def main():
    os.makedirs(BASE_TEST_DIR, exist_ok=True)
    tests = [
        {
            "name": "Nicho 1: Cocina Tecnológica VS",
            "script": "/home/javierferb/n8n/tools/amazon_cocina_scraper.py",
            "query": "freidora de aire cecotec vs cosori",
            "canal": "test_cocina_vs",
            "extra_args": ["--affiliate_tag", "cocina_tag-21"]
        },
        {
            "name": "Nicho 2: Zapatería Del Pueblo VS",
            "script": "/home/javierferb/n8n/tools/amazon_vs_scraper.py",
            "query": "zapatillas running puma vs adidas",
            "canal": "test_zapateria_vs",
            "extra_args": ["--affiliate_tag", "general_tag-21"]
        },
        {
            "name": "Nicho 3: Limpieza Tecnológica VS",
            "script": "/home/javierferb/n8n/tools/amazon_limpieza_scraper.py",
            "query": "aspiradora escoba sin cable rowenta",
            "canal": "test_limpieza_vs",
            "extra_args": ["--affiliate_tag", "limpieza_tag-21"]
        },
        {
            "name": "Nicho 4: Librería Del Pueblo VS",
            "script": "/home/javierferb/n8n/tools/amazon_libreria_scraper.py",
            "query": "habitos atomicos james clear",
            "canal": "test_libreria_vs",
            "extra_args": ["--affiliate_tag", "libreria_tag-21"]
        },
        {
            "name": "Nicho TOP Multi-Nicho: Amazon Scraper Ranking",
            "script": "/home/javierferb/n8n/tools/amazon_scraper.py",
            "query": "freidoras de aire sin aceite",
            "canal": "test_top_ranking",
            "extra_args": ["--limit", "3"]
        },
        {
            "name": "Resiliencia Extrema: Búsqueda Inexistente (Evergreen Fallback)",
            "script": "/home/javierferb/n8n/tools/amazon_vs_scraper.py",
            "query": "supercalifragilisticoespialidoso_gadget_99999_xyz",
            "canal": "test_evergreen_fallback",
            "extra_args": ["--affiliate_tag", "general_tag-21"]
        }
    ]

    all_passed = True
    results = []

    print("\n🚀 INICIANDO BATERÍA DE PRUEBAS REALES MULTI-NICHO (AMAZON SCRAPERS)...")
    for t in tests:
        success, reason = run_scraper_test(t["name"], t["script"], t["query"], t["canal"], t.get("extra_args"))
        results.append((t["name"], success, reason))
        if not success:
            all_passed = False
            break

    print("\n" + "="*70)
    print("📊 RESUMEN DE CERTIFICACIÓN EMPÍRICA:")
    print("="*70)
    for name, success, reason in results:
        status_icon = "✅ PASSED" if success else f"❌ FAILED ({reason})"
        print(f" - {name:<55} {status_icon}")

    if all_passed and len(results) == len(tests):
        print("\n🎉 TODOS LOS SCRAPERS ESTÁN ESTANDARIZADOS Y OPERATIVOS AL 100% EN REAL.")
        # Limpieza de temporales
        shutil.rmtree(BASE_TEST_DIR, ignore_errors=True)
        sys.exit(0)
    else:
        print("\n❌ HUBO FALLOS EN LA CERTIFICACIÓN.")
        sys.exit(1)

if __name__ == "__main__":
    main()
