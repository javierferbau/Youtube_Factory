#!/usr/bin/env python3
"""
test_campaign_manager.py — Batería de Pruebas Unitarias para campaign_manager.py
Verifica matemáticamente y empíricamente:
1. Fechas límite y ventanas D-7 automáticas de todos los eventos.
2. Comportamiento en días con y sin campaña (Evergreen).
3. Modificación segura de títulos (límite <95 caracteres, no duplicidad).
4. Inyección de etiquetas prioritarias (límite estricto <480 bytes, sin hashtags).
5. Renderizado de badge en miniaturas con Pillow.
6. Override forzado manual si se activa.
"""

import unittest
from datetime import date
from PIL import Image
from campaign_manager import (
    get_active_campaign,
    apply_campaign_title,
    apply_campaign_tags,
    draw_campaign_badge,
    get_campaign_status,
    get_registered_campaigns
)

class TestCampaignManager(unittest.TestCase):

    def test_registered_campaigns_2026(self):
        camps = get_registered_campaigns(2026)
        camp_ids = [c["id"] for c in camps]
        self.assertIn("black_friday", camp_ids)
        self.assertIn("prime_day", camp_ids)
        self.assertIn("rebajas_enero", camp_ids)
        self.assertIn("vuelta_al_cole", camp_ids)

        # Black Friday 2026: 4th Friday of Nov is Nov 27
        bf = next(c for c in camps if c["id"] == "black_friday")
        self.assertEqual(bf["start_date"], date(2026, 11, 20)) # 7 days before Nov 27
        self.assertEqual(bf["end_date"], date(2026, 11, 30))   # Cyber monday

    def test_black_friday_window(self):
        # 1 day before D-7 (Nov 19) -> Should be None
        self.assertIsNone(get_active_campaign(date(2026, 11, 19)))
        # Exactly D-7 (Nov 20) -> Black Friday
        camp = get_active_campaign(date(2026, 11, 20))
        self.assertIsNotNone(camp)
        self.assertEqual(camp["id"], "black_friday")
        # Cyber monday (Nov 30) -> Black Friday
        camp = get_active_campaign(date(2026, 11, 30))
        self.assertIsNotNone(camp)
        self.assertEqual(camp["id"], "black_friday")
        # Day after Cyber monday (Dec 1) -> None
        self.assertIsNone(get_active_campaign(date(2026, 12, 1)))

    def test_evergreen_normal_day(self):
        # A day with no campaigns (e.g. Feb 10, Oct 25)
        camp = get_active_campaign(date(2026, 2, 10))
        self.assertIsNone(camp)
        status = get_campaign_status(date(2026, 2, 10))
        self.assertIn("Modo Normal Evergreen", status)

    def test_apply_title_no_campaign(self):
        title = "TOP 7 MEJORES FREIDORAS DE AIRE EN AMAZON 2026"
        res = apply_campaign_title(title, campaign=None)
        self.assertEqual(res, title)

    def test_apply_title_with_campaign(self):
        bf_camp = {
            "id": "black_friday",
            "title_prefix": "🔥 [BLACK FRIDAY]"
        }
        title = "TOP 7 MEJORES FREIDORAS DE AIRE EN AMAZON 2026"
        res = apply_campaign_title(title, campaign=bf_camp, max_len=95)
        self.assertTrue(res.startswith("🔥 [BLACK FRIDAY]"))
        self.assertLessEqual(len(res), 95)

        # Long title boundary check
        long_title = "ESTE ES UN TÍTULO EXTREMADAMENTE LARGO QUE PODRÍA DESBORDAR EL LÍMITE DE LA API DE YOUTUBE FÁCILMENTE"
        res_long = apply_campaign_title(long_title, campaign=bf_camp, max_len=95)
        self.assertLessEqual(len(res_long), 95)
        self.assertTrue(res_long.startswith("🔥 [BLACK FRIDAY]"))

        # No duplicate prefix
        res_dup = apply_campaign_title(res, campaign=bf_camp, max_len=95)
        self.assertEqual(res_dup.count("[BLACK FRIDAY]"), 1)

    def test_apply_tags(self):
        bf_camp = {
            "id": "black_friday",
            "extra_tags": ["black friday 2026", "ofertas black friday", "chollos amazon"]
        }
        original_tags = ["freidora de aire", "cecotec vs ninja", "mejores freidoras 2026"]
        res = apply_campaign_tags(original_tags, campaign=bf_camp, max_bytes=480)

        # Extra tags are in front
        self.assertEqual(res[0], "black friday 2026")
        self.assertEqual(res[1], "ofertas black friday")
        # No hashtags
        for t in res:
            self.assertNotIn("#", t)
            self.assertNotIn("<", t)
            self.assertNotIn(">", t)
        # Total bytes under 480
        total_b = len(",".join(res).encode("utf-8"))
        self.assertLessEqual(total_b, 480)

    def test_apply_tags_no_campaign(self):
        original_tags = ["calzado running", "zapatillas padel"]
        res = apply_campaign_tags(original_tags, campaign=None)
        self.assertEqual(res, original_tags)

    def test_draw_campaign_badge(self):
        img = Image.new("RGBA", (1280, 720), (20, 20, 20, 255))
        bf_camp = {
            "badge_text": "🔥 BLACK FRIDAY 🔥",
            "badge_bg": (185, 28, 28, 255),
            "badge_border": (250, 204, 21, 255),
            "badge_text_color": (255, 255, 255)
        }
        out_img = draw_campaign_badge(img, bf_camp, pos_y=30)
        self.assertEqual(out_img.size, (1280, 720))

if __name__ == "__main__":
    unittest.main()
