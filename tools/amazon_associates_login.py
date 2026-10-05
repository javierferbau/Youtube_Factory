#!/usr/bin/env python3
"""
amazon_associates_login.py
Inicia sesión en Amazon Associates España (afiliados.amazon.es) usando un perfil persistente
de Chrome (user_data_dir) para preservar IndexedDB, huella de dispositivo y tokens de confianza.
"""
import sys
import os
import json
import argparse
import time
from playwright.sync_api import sync_playwright

PROFILE_DIR = "/home/javierferb/n8n/tools/data/chrome_profile"
SESSION_FILE = "/home/javierferb/n8n/tools/data/amazon_session.json"
CHROME_BIN = "/opt/google/chrome/chrome"

def login_interactive():
    print("=" * 65)
    print("🔑 ASISTENTE DE AUTENTICACIÓN PERSISTENTE - AMAZON AFILIADOS")
    print("=" * 65)
    print(f"[*] Perfil persistente: {PROFILE_DIR}")
    os.makedirs(PROFILE_DIR, exist_ok=True)
    
    # Asegurar DISPLAY si no está definido en el subshell
    if "DISPLAY" not in os.environ and os.path.exists("/tmp/.X11-unix/X1"):
        os.environ["DISPLAY"] = ":1"
    if "WAYLAND_DISPLAY" not in os.environ:
        os.environ["WAYLAND_DISPLAY"] = "wayland-1"

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            executable_path=CHROME_BIN,
            headless=False,
            no_viewport=True,
            args=[
                "--start-maximized",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        
        # Inyectar cookies previas si existen para no reescribir email
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, "r", encoding="utf-8") as sf:
                    s_data = json.load(sf)
                    cookies = s_data.get("cookies", [])
                    if cookies:
                        context.add_cookies(cookies)
                        print(f"[*] Inyectadas {len(cookies)} cookies existentes en el perfil.")
            except Exception:
                pass

        page = context.pages[0] if context.pages else context.new_page()

        target_url = "https://afiliados.amazon.es/home/reports"
        print(f"[*] Navegando a: {target_url}")
        page.goto(target_url)

        print("\n👉 ACCIÓN REQUERIDA EN LA VENTANA DE CHROME:")
        print("   1. Introduce tu contraseña y marca la casilla: [x] 'Recuérdame / Mantener sesión'.")
        print("   2. Si te pide 2FA/OTP, introduce el código y marca 'No volver a pedir en este dispositivo'.")
        print("   3. Cuando cargue el panel de afiliados (/home/reports), el perfil se guardará automáticamente.\n")

        logged_in = False
        start_time = time.time()
        timeout_seconds = 300  # 5 minutos

        while time.time() - start_time < timeout_seconds:
            try:
                curr_url = page.url
                if "afiliados.amazon.es" in curr_url and "/home" in curr_url and "signin" not in curr_url:
                    page.wait_for_timeout(3000)
                    logged_in = True
                    break
            except Exception:
                pass
            time.sleep(1)

        if not logged_in:
            print("[!] Timeout o navegación pendiente.")
            ans = input("¿Has completado el login en la ventana de Chrome? (s/n): ")
            if ans.strip().lower() in ["s", "si", "y", "yes"]:
                logged_in = True

        if logged_in:
            # Guardar backup de storageState también
            os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
            context.storage_state(path=SESSION_FILE)
            os.chmod(SESSION_FILE, 0o600)
            print(f"\n✅ PERFIL PERSISTENTE CONFIGURADO Y CONSERVADO en:")
            print(f"   {PROFILE_DIR}")
            print(f"   Backup de sesión: {SESSION_FILE}")
            print("   Las consultas automáticas diarias ya no requerirán intervención interactiva.")
        else:
            print("\n❌ No se detectó inicio de sesión completado.")

        context.close()

if __name__ == '__main__':
    login_interactive()
