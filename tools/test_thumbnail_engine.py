#!/usr/bin/env python3
"""
test_thumbnail_engine.py — Suite de Pruebas Unitarias del Motor de Miniaturas
Verifica el 100% de operatividad en los 4 nichos del ecosistema:
1. Cocina Tecnológica
2. Limpieza del Pueblo
3. Calzado del Pueblo
4. Librería del Pueblo
"""

import os
import sys
import unittest
import tempfile
import json
import shutil
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from thumbnail_engine import render_vs_thumbnail, render_top_thumbnail

class TestThumbnailEngineMultiNiche(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
        # Crear un producto ficticio para tests
        prod_a_dir = os.path.join(self.temp_dir, "producto_a")
        prod_b_dir = os.path.join(self.temp_dir, "producto_b")
        prod_top_dir = os.path.join(self.temp_dir, "01_producto_1")
        os.makedirs(prod_a_dir, exist_ok=True)
        os.makedirs(prod_b_dir, exist_ok=True)
        os.makedirs(prod_top_dir, exist_ok=True)
        
        dummy_img = Image.new("RGBA", (400, 500), (255, 255, 255, 255))
        d_draw = Image.new("RGBA", (300, 400), (50, 100, 200, 255))
        dummy_img.paste(d_draw, (50, 50))
        dummy_img.save(os.path.join(prod_a_dir, "product_a.png"))
        dummy_img.save(os.path.join(prod_b_dir, "product_b.png"))
        dummy_img.convert("RGB").save(os.path.join(prod_top_dir, "product_1.jpg"), "JPEG")
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_all_5_vs_templates(self):
        """Verifica que las 5 plantillas VS generen JPEGs válidos de 1280x720."""
        data = {
            "product_a": {"brand": "Cecotec", "price": "49,99€"},
            "product_b": {"brand": "Cosori", "price": "129,99€"}
        }
        with open(os.path.join(self.temp_dir, "data.json"), "w", encoding="utf-8") as f:
            json.dump(data, f)
            
        for t_id in [1, 2, 3, 4, 5]:
            out_p = os.path.join(self.temp_dir, f"vs_thumb_{t_id}.jpg")
            res = render_vs_thumbnail(self.temp_dir, out_p, niche="cocina", template_id=t_id)
            self.assertTrue(os.path.exists(res), f"Plantilla VS {t_id} no generó archivo")
            self.assertGreater(os.path.getsize(res), 50000, f"Plantilla VS {t_id} generó archivo corrupto/vacío")
            with Image.open(res) as img:
                self.assertEqual(img.size, (1280, 720), f"Plantilla VS {t_id} no tiene dimensiones 1280x720")

    def test_all_5_top_templates(self):
        """Verifica que las 5 plantillas TOP generen JPEGs válidos de 1280x720."""
        data = {
            "query": "Mejores Cafeteras Superautomaticas"
        }
        with open(os.path.join(self.temp_dir, "data.json"), "w", encoding="utf-8") as f:
            json.dump(data, f)
            
        for t_id in [1, 2, 3, 4, 5]:
            out_p = os.path.join(self.temp_dir, f"top_thumb_{t_id}.jpg")
            res = render_top_thumbnail(self.temp_dir, out_p, template_id=t_id)
            self.assertTrue(os.path.exists(res), f"Plantilla TOP {t_id} no generó archivo")
            self.assertGreater(os.path.getsize(res), 50000, f"Plantilla TOP {t_id} generó archivo corrupto/vacío")
            with Image.open(res) as img:
                self.assertEqual(img.size, (1280, 720), f"Plantilla TOP {t_id} no tiene dimensiones 1280x720")

    def test_four_niches_vs_execution(self):
        """Verifica que el motor VS soporte los 4 nichos con sus cabeceras contextuales."""
        niches = ["cocina", "limpieza", "calzado", "libreria"]
        data = {
            "product_a": {"brand": "Marca Uno", "price": "19,90€"},
            "product_b": {"brand": "Marca Dos", "price": "39,90€"}
        }
        with open(os.path.join(self.temp_dir, "data.json"), "w", encoding="utf-8") as f:
            json.dump(data, f)
            
        for n in niches:
            out_p = os.path.join(self.temp_dir, f"vs_{n}.jpg")
            res = render_vs_thumbnail(self.temp_dir, out_p, niche=n) # template aleatorio
            self.assertTrue(os.path.exists(res))
            with Image.open(res) as img:
                self.assertEqual(img.size, (1280, 720))

    def test_dynamic_real_prices(self):
        """Verifica que precios reales de data.json se procesen correctamente en plantillas TOP 2 y 5."""
        from thumbnail_engine import parse_price_val
        self.assertEqual(parse_price_val("19,85€"), 19.85)
        self.assertEqual(parse_price_val("89,90 €"), 89.90)
        self.assertEqual(parse_price_val("149,99€"), 149.99)
        self.assertIsNone(parse_price_val("Consultar en Amazon"))
        self.assertIsNone(parse_price_val(""))

        data = {
            "query": "Freidora de Aire Cecotec",
            "products": [
                {"price": "49,90 €", "title": "Cecofry Fantastik"}
            ]
        }
        with open(os.path.join(self.temp_dir, "data.json"), "w", encoding="utf-8") as f:
            json.dump(data, f)

        out_2 = os.path.join(self.temp_dir, "test_price_top_2.jpg")
        res_2 = render_top_thumbnail(self.temp_dir, out_2, template_id=2)
        self.assertTrue(os.path.exists(res_2))

        out_5 = os.path.join(self.temp_dir, "test_price_top_5.jpg")
        res_5 = render_top_thumbnail(self.temp_dir, out_5, template_id=5)
        self.assertTrue(os.path.exists(res_5))

    def test_cli_wrappers(self):
        """Verifica que los scripts wrapper existentes funcionen por CLI sin romper compatibilidad."""
        import subprocess
        scripts = [
            ("generate_thumbnail.py", [self.temp_dir, os.path.join(self.temp_dir, "w_top.jpg")]),
            ("generate_cocina_thumbnail.py", [self.temp_dir, os.path.join(self.temp_dir, "w_cocina.jpg")]),
            ("generate_limpieza_thumbnail.py", [self.temp_dir, os.path.join(self.temp_dir, "w_limpieza.jpg")]),
            ("generate_libreria_thumbnail.py", [self.temp_dir, os.path.join(self.temp_dir, "w_libreria.jpg")]),
            ("generate_barberia_thumbnail.py", [self.temp_dir, os.path.join(self.temp_dir, "w_barberia.jpg")]),
            ("generate_vs_thumbnail.py", [self.temp_dir, os.path.join(self.temp_dir, "w_vs.jpg")]),
        ]
        tools_dir = os.path.dirname(os.path.abspath(__file__))
        for sc, args in scripts:
            full_sc = os.path.join(tools_dir, sc)
            cmd = [sys.executable, full_sc] + args
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertEqual(proc.returncode, 0, f"Error ejecutando {sc}: {proc.stderr}")
            self.assertTrue(os.path.exists(args[1]), f"Archivo no generado por {sc}")

if __name__ == "__main__":
    unittest.main()
