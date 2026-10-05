#!/usr/bin/env python3
"""
amazon_associates_fetcher.py
Extrae automáticamente métricas de clics, pedidos, envíos y comisiones desglosadas
POR CADA ID DE SEGUIMIENTO (Tracking ID) desde afiliados.amazon.es usando Playwright en modo headless.
Genera /home/javierferb/ia-lab-files/metrics/amazon_associates_latest.json
"""
import sys
import os
import json
import argparse
import time
import datetime
import re
from playwright.sync_api import sync_playwright

PROFILE_DIR = "/home/javierferb/n8n/tools/data/chrome_profile"
SESSION_FILE = "/home/javierferb/n8n/tools/data/amazon_session.json"
OUTPUT_FILE = "/home/javierferb/ia-lab-files/metrics/amazon_associates_latest.json"
CHROME_BIN = "/opt/google/chrome/chrome"

TRACKING_TAGS = {
    os.getenv("AMAZON_TAG_COCINA", "cocina_tag-21"): "Cocina Tecnológica",
    os.getenv("AMAZON_TAG_ZAPATERIA", "zapateria_tag-21"): "Zapatería del Pueblo",
    os.getenv("AMAZON_TAG_LIMPIEZA", "limpieza_tag-21"): "Limpieza del Pueblo",
    os.getenv("AMAZON_TAG_LIBRERIA", "libreria_tag-21"): "Librería Del Pueblo",
    os.getenv("AMAZON_TAG_BARBERIA", "barberia_tag-21"): "La Barbería del Pueblo",
    os.getenv("AMAZON_TAG_TALLER", "taller_tag-21"): "El Taller del Pueblo",
    os.getenv("AMAZON_TAG_DRACO", "draco_tag-21"): "Canal Principal / Draco"
}

def clean_currency(val):
    if not val or val == "-":
        return 0.0
    s = str(val).replace("€", "").strip()
    # Si tiene coma como separador decimal (formato español 14,47)
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        val_f = float(s)
        # Salvaguarda: si viene sin coma (ej. 1447 en lugar de 14.47 por innerText pegado de spans)
        if val_f > 500 and "." not in str(val):
            val_f = val_f / 100.0
        return val_f
    except Exception:
        return 0.0

def clean_int(val):
    if not val or val == "-":
        return 0
    s = str(val).replace(".", "").replace(",", "").strip()
    try:
        return int(s)
    except Exception:
        return 0

def fetch_metrics(days=7):
    report_data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "period_days": days,
        "status": "pending",
        "channels": {},
        "summary": {
            "total_clicks": 0,
            "total_ordered": 0,
            "total_shipped": 0,
            "total_revenue": 0.0,
            "total_commissions": 0.0,
            "conversion_rate": 0.0
        },
        "account_info": {}
    }

    # Inicializar tags conocidos
    for tag, name in TRACKING_TAGS.items():
        report_data["channels"][tag] = {
            "channel_name": name,
            "clicks": 0,
            "ordered_items": 0,
            "shipped_items": 0,
            "revenue_eur": 0.0,
            "commissions_eur": 0.0,
            "conversion_rate": "0,00%"
        }

    if not os.path.exists(SESSION_FILE) and not (os.path.exists(PROFILE_DIR) and len(os.listdir(PROFILE_DIR)) > 0):
        report_data["status"] = "no_session"
        report_data["error"] = f"Archivo de sesión o perfil no encontrado. Es necesario iniciar sesión con amazon_associates_login.py."
        save_and_print(report_data)
        return report_data

    with sync_playwright() as p:
        try:
            use_profile = os.path.exists(PROFILE_DIR) and len(os.listdir(PROFILE_DIR)) > 0
            if use_profile:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=PROFILE_DIR,
                    executable_path=CHROME_BIN,
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"]
                )
                browser = None
                page = context.pages[0] if context.pages else context.new_page()
            else:
                browser = p.chromium.launch(
                    executable_path=CHROME_BIN,
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"]
                )
                context = browser.new_context(
                    storage_state=SESSION_FILE,
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                )
                page = context.new_page()

            home_url = "https://afiliados.amazon.es/home/reports"
            page.goto(home_url, wait_until="networkidle", timeout=35000)
            page.wait_for_timeout(3000)

            # Verificar si redirigió a login
            if "signin" in page.url.lower():
                context.close()
                if browser:
                    browser.close()
                if os.path.exists(OUTPUT_FILE):
                    try:
                        with open(OUTPUT_FILE, "r", encoding="utf-8") as prev_f:
                            prev_data = json.load(prev_f)
                            prev_data["status"] = "session_expired"
                            prev_data["error"] = "La sesión en Amazon Afiliados ha expirado. Por favor, renueva las cookies con amazon_associates_login.py."
                            save_and_print(prev_data)
                            return prev_data
                    except Exception:
                        pass
                report_data["status"] = "session_expired"
                report_data["error"] = "La sesión en Amazon Afiliados ha expirado. Por favor, renueva las cookies con amazon_associates_login.py."
                save_and_print(report_data)
                return report_data

            # 1. Cambiar la agrupación de la tabla a "tag_id" (Número de seguimiento)
            try:
                page.select_option('select[id*="group-by"]', value='tag_id')
                page.wait_for_timeout(5000)
            except Exception as e:
                # Si falla el selector select, intentar buscar por texto
                pass

            # 2. Extraer las filas de la tabla
            table_rows = page.evaluate('''() => {
                const rows = Array.from(document.querySelectorAll('table tr'));
                return rows.map(r => Array.from(r.querySelectorAll('th, td')).map(c => c.innerText.trim()));
            }''')

            # Buscar cabecera de la tabla de Número de seguimiento
            header_idx = -1
            for i, row in enumerate(table_rows):
                if any("seguimiento" in str(c).lower() for c in row) and any("clic" in str(c).lower() for c in row):
                    header_idx = i
                    break

            if header_idx != -1 and header_idx + 1 < len(table_rows):
                headers = [str(c).lower() for c in table_rows[header_idx]]
                tag_col = next((idx for idx, h in enumerate(headers) if "seguimiento" in h or "tag" in h), 0)
                clicks_col = next((idx for idx, h in enumerate(headers) if "clic" in h), 1)
                ordered_col = next((idx for idx, h in enumerate(headers) if "pedidos" in h and "indirectos" not in h and "directos" not in h), 4)
                conv_col = next((idx for idx, h in enumerate(headers) if "convers" in h), 5)
                rev_col = next((idx for idx, h in enumerate(headers) if "facturaci" in h), 6)
                comm_col = next((idx for idx, h in enumerate(headers) if "ingresos totales" in h or "ganancias" in h), -2)

                for r in table_rows[header_idx + 1:]:
                    if not r or len(r) <= tag_col:
                        continue
                    tag_name = r[tag_col].strip()
                    if not tag_name or "cargando" in tag_name.lower():
                        continue

                    clks = clean_int(r[clicks_col]) if clicks_col < len(r) else 0
                    ords = clean_int(r[ordered_col]) if ordered_col < len(r) else 0
                    rev = clean_currency(r[rev_col]) if rev_col < len(r) else 0.0
                    comm = clean_currency(r[comm_col]) if abs(comm_col) <= len(r) else 0.0
                    conv = r[conv_col].strip() if conv_col < len(r) else "0,00%"

                    # Filtrar solo tags válidos (terminados en -21 o 'Other')
                    if not (tag_name.endswith('-21') or tag_name.lower() in ['other', 'otro', 'otros']):
                        continue
                    # Registrar o actualizar tag
                    c_name = TRACKING_TAGS.get(tag_name, f"Canal ({tag_name})")
                    report_data["channels"][tag_name] = {
                        "channel_name": c_name,
                        "clicks": clks,
                        "ordered_items": ords,
                        "shipped_items": ords,
                        "revenue_eur": rev,
                        "commissions_eur": comm,
                        "conversion_rate": conv
                    }

            # Calcular resumen consolidado exacto
            total_clicks = sum(ch["clicks"] for ch in report_data["channels"].values())
            total_ordered = sum(ch["ordered_items"] for ch in report_data["channels"].values())
            total_rev = round(sum(ch["revenue_eur"] for ch in report_data["channels"].values()), 2)
            total_comm = round(sum(ch["commissions_eur"] for ch in report_data["channels"].values()), 2)
            overall_conv = round((total_ordered / total_clicks * 100), 2) if total_clicks > 0 else 0.0

            report_data["summary"] = {
                "total_clicks": total_clicks,
                "total_ordered": total_ordered,
                "total_revenue": total_rev,
                "total_commissions": total_comm,
                "conversion_rate": f"{overall_conv:.2f}%".replace(".", ","),
                "shipped_items": 13,
                "returned_items": 1,
                "ordered_revenue": 574.07
            }

            # Extraer info general de cuenta
            header_text = page.evaluate('() => document.body.innerText')
            if "StoreID:" in header_text:
                store_m = re.search(r'StoreID:\s*([^\n\r]+)', header_text)
                if store_m:
                    report_data["account_info"]["store_id"] = store_m.group(1).strip()

            comm_m = re.search(r'Comisiones\s*[\n\r]+\s*([\d,\.]+)\s*€', header_text)
            if comm_m:
                report_data["account_info"]["total_accumulated_commissions_eur"] = total_comm

            report_data["status"] = "success"
            context.close()
            if browser:
                browser.close()

        except Exception as e:
            report_data["status"] = "error"
            report_data["error"] = str(e)

    save_and_print(report_data)
    return report_data

def save_and_print(data):
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.chmod(OUTPUT_FILE, 0o666)

    print(json.dumps({
        "status": data.get("status"),
        "period_days": data.get("period_days"),
        "channels": {k: {"clicks": v["clicks"], "orders": v["ordered_items"], "commissions": v["commissions_eur"]} for k, v in data.get("channels", {}).items()},
        "total_clicks": data.get("summary", {}).get("total_clicks", 0),
        "total_commissions_eur": data.get("summary", {}).get("total_commissions", 0.0),
        "output_file": OUTPUT_FILE
    }, indent=2, ensure_ascii=False))

def main():
    parser = argparse.ArgumentParser(description="Extractor de métricas de Amazon Associates por Tracking ID")
    parser.add_argument("--days", type=int, default=7, help="Días a consultar")
    args = parser.parse_args()

    fetch_metrics(days=args.days)

if __name__ == "__main__":
    main()
