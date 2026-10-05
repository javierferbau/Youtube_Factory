#!/usr/bin/env python3
"""
ComfyUI Backdrop Generator for YouTube Thumbnails
Generates cinematic 3D backgrounds via local ComfyUI API on AMD GPU (ROCm).
Resilient with 15s timeout and automatic fallback.
"""

import os
import sys
import time
import json
import random
import logging
import urllib.request
import urllib.error
from typing import Optional
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("comfyui_backdrop")

COMFYUI_HOST = os.environ.get("COMFYUI_HOST", "http://127.0.0.1:8188")
COMFYUI_OUTPUT_DIR = os.environ.get("COMFYUI_OUTPUT_DIR", "/home/javierferb/ComfyUI/output")
DEFAULT_MODEL = "dreamshaper_8.safetensors"
TIMEOUT_SECONDS = 15.0

NICHE_PROMPTS = {
    "taller": (
        "cinematic 3d dark craftsman tool workshop, heavy dark oak workbench, "
        "dark pegboard tool wall hanging organized wrenches and screwdrivers with soft background bokeh, "
        "dramatic moody low-key industrial studio spotlight on workbench, dark aesthetic, "
        "ultra detailed 8k octane render, empty workbench surface in foreground"
    ),
    "barberia": (
        "cinematic 3d luxury modern barber shop interior, dark wood and polished copper background "
        "with soft bokeh, elegant warm studio rim lighting, ultra detailed 8k octane render, "
        "minimalist masculine aesthetic"
    ),
    "calzado": (
        "cinematic 3d futuristic sports running track and podium, dark sleek concrete floor with "
        "wet reflections, neon cyan and orange rim lighting, dramatic depth of field, "
        "ultra detailed 8k octane render"
    ),
    "zapateria": (
        "cinematic 3d futuristic sports running track and podium, dark sleek concrete floor with "
        "wet reflections, neon cyan and orange rim lighting, dramatic depth of field, "
        "ultra detailed 8k octane render"
    ),
    "cocina": (
        "cinematic 3d luxury dark slate kitchen countertop, premium minimalist culinary studio "
        "background with soft bokeh, subtle warm rim lighting, steam and smoke particles, "
        "ultra detailed 8k octane render"
    ),
    "limpieza": (
        "cinematic 3d modern luxury living room with clean polished dark wood floors, "
        "dramatic moody studio lighting, dark accent wall on the left with soft shadows, "
        "elegant minimalist interior design in soft background bokeh, ultra detailed 8k octane render"
    ),
    "libreria": (
        "cinematic 3d antique cozy library with tall dark oak bookshelves, warm ambient glowing study lamp, "
        "moody atmospheric dust motes, soft bokeh, ultra detailed 8k octane render"
    ),
}

DEFAULT_PROMPT = (
    "cinematic 3d dark minimalist product studio stage, polished dark surface with subtle reflections, "
    "moody atmospheric dramatic studio lighting, soft bokeh background, ultra detailed 8k octane render"
)

NEGATIVE_PROMPT = (
    "cars, car, vehicle, automotive, automobile, supercar, sports car, wheels, tires, mechanics, garage, parking, "
    "bright white windows, blown out highlights, overexposed, high key, white wall, "
    "people, person, man, woman, face, hands, fingers, text, watermark, logo, brand, typography, "
    "deformed, blurry, ugly, noisy, oversaturated, low quality, duplicate, cartoon"
)


def is_comfyui_available(timeout: float = 1.5) -> bool:
    """Verifica si el servidor de ComfyUI está respondiendo."""
    try:
        req = urllib.request.Request(f"{COMFYUI_HOST}/system_stats")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def get_prompt_for_niche(niche: str) -> str:
    """Devuelve el prompt cinemático correspondiente según nicho."""
    n_lower = str(niche).lower().strip()
    for key, prompt in NICHE_PROMPTS.items():
        if key in n_lower:
            return prompt
    # Keyword matches
    if any(k in n_lower for k in ["herramienta", "brico", "mecanic"]):
        return NICHE_PROMPTS["taller"]
    if any(k in n_lower for k in ["afeitad", "pelo", "cabello"]):
        return NICHE_PROMPTS["barberia"]
    if any(k in n_lower for k in ["zapat", "running", "sneaker", "bota"]):
        return NICHE_PROMPTS["calzado"]
    if any(k in n_lower for k in ["receta", "electro", "sarten", "cuchillo", "freidora"]):
        return NICHE_PROMPTS["cocina"]
    if any(k in n_lower for k in ["aspirad", "hidro", "fregona"]):
        return NICHE_PROMPTS["limpieza"]
    if any(k in n_lower for k in ["libro", "novela", "lectura"]):
        return NICHE_PROMPTS["libreria"]
    return DEFAULT_PROMPT


def build_workflow(positive_prompt: str, seed: int, width: int = 1024, height: int = 576, steps: int = 14) -> dict:
    """Construye el JSON de workflow para la API de ComfyUI."""
    return {
        "prompt": {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": DEFAULT_MODEL
                }
            },
            "2": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": positive_prompt,
                    "clip": ["1", 1]
                }
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": NEGATIVE_PROMPT,
                    "clip": ["1", 1]
                }
            },
            "4": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": 1
                }
            },
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": steps,
                    "cfg": 6.5,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["4", 0]
                }
            },
            "6": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["5", 0],
                    "vae": ["1", 2]
                }
            },
            "7": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": f"backdrop_{seed}",
                    "images": ["6", 0]
                }
            }
        }
    }


def generate_niche_backdrop(
    niche: str,
    output_path: Optional[str] = None,
    timeout: float = TIMEOUT_SECONDS,
    target_size: tuple = (1280, 720)
) -> Optional[str]:
    """
    Genera un fondo cinemático 3D usando ComfyUI local.
    Devuelve la ruta al archivo generado, o None si ComfyUI falla o excede el timeout.
    """
    start_time = time.time()
    try:
        # 1. Comprobación rápida de disponibilidad
        if not is_comfyui_available(timeout=1.5):
            logger.warning("[ComfyUI] Servidor no responde en %s. Activando fallback.", COMFYUI_HOST)
            return None

        prompt_text = get_prompt_for_niche(niche)
        seed = random.randint(100000, 999999999)
        workflow = build_workflow(prompt_text, seed, width=1024, height=576, steps=14)

        # 2. Enviar prompt a ComfyUI
        req_data = json.dumps(workflow).encode("utf-8")
        req = urllib.request.Request(
            f"{COMFYUI_HOST}/prompt",
            data=req_data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))

        prompt_id = res_json.get("prompt_id")
        if not prompt_id:
            logger.warning("[ComfyUI] No se obtuvo prompt_id de la API.")
            return None

        logger.info("[ComfyUI] Prompt %s encolado para nicho '%s' (seed=%d)", prompt_id, niche, seed)

        # 3. Monitorear hasta finalización con timeout estricto
        image_info = None
        while time.time() - start_time < timeout:
            time.sleep(0.4)
            try:
                hist_req = urllib.request.Request(f"{COMFYUI_HOST}/history/{prompt_id}")
                with urllib.request.urlopen(hist_req, timeout=2.0) as h_resp:
                    history = json.loads(h_resp.read().decode("utf-8"))
                if prompt_id in history:
                    outputs = history[prompt_id].get("outputs", {})
                    if "7" in outputs and "images" in outputs["7"] and len(outputs["7"]["images"]) > 0:
                        image_info = outputs["7"]["images"][0]
                        break
            except Exception as e:
                logger.debug("[ComfyUI] Error consultando historial: %s", e)

        if not image_info:
            logger.warning("[ComfyUI] Timeout de %.1fs excedido generando fondo para nicho '%s'. Fallback.", timeout, niche)
            return None

        filename = image_info.get("filename")
        subfolder = image_info.get("subfolder", "")
        img_type = image_info.get("type", "output")

        # 4. Obtener imagen (directa desde disco si existe, o vía HTTP /view)
        local_disk_path = os.path.join(COMFYUI_OUTPUT_DIR, subfolder, filename) if COMFYUI_OUTPUT_DIR else None
        img_pil = None
        if local_disk_path and os.path.exists(local_disk_path):
            img_pil = Image.open(local_disk_path)
        else:
            view_url = f"{COMFYUI_HOST}/view?filename={filename}&subfolder={subfolder}&type={img_type}"
            with urllib.request.urlopen(view_url, timeout=4.0) as v_resp:
                from io import BytesIO
                img_pil = Image.open(BytesIO(v_resp.read()))

        if img_pil is None:
            logger.warning("[ComfyUI] No se pudo leer la imagen generada.")
            return None

        # 5. Redimensionar a target_size (1280x720) y guardar
        img_pil = img_pil.convert("RGB")
        if img_pil.size != target_size:
            img_pil = img_pil.resize(target_size, Image.Resampling.LANCZOS)

        if not output_path:
            cache_dir = "/tmp/comfy_backdrops"
            os.makedirs(cache_dir, exist_ok=True)
            output_path = os.path.join(cache_dir, f"backdrop_{niche}_{seed}.jpg")
        else:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        img_pil.save(output_path, "JPEG", quality=95)
        elapsed = time.time() - start_time
        logger.info("[ComfyUI] Fondo cinemático generado en %.2fs: %s", elapsed, output_path)
        return output_path

    except Exception as e:
        logger.warning("[ComfyUI] Error inesperado en generador de fondos: %s. Activando fallback.", e)
        return None


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ComfyUI Backdrop Generator")
    parser.add_argument("--niche", default="taller", help="Nicho temático")
    parser.add_argument("--output", default="/home/javierferb/n8n/tools/test_output/test_comfy_taller.jpg", help="Ruta archivo de salida")
    args = parser.parse_args()

    res = generate_niche_backdrop(args.niche, args.output)
    if res and os.path.exists(res):
        print(f"SUCCESS: {res}")
        sys.exit(0)
    else:
        print("FAILED or FALLBACK needed")
        sys.exit(1)
