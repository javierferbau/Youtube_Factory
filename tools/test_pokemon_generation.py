#!/usr/bin/env python3
"""
test_pokemon_generation.py
Genera 3 muestras de arte cinemático de Pokémon vía ComfyUI local en GPU AMD Radeon (ROCm).
Mide tiempos de inferencia y guarda resultados en test_output/pokemon_tests/.
"""

import os
import sys
import time
import json
import random
import urllib.request
from PIL import Image
from io import BytesIO

COMFYUI_HOST = "http://127.0.0.1:8188"
COMFYUI_OUTPUT_DIR = "/home/javierferb/ComfyUI/output"
CHECKPOINT_NAME = "dreamshaper_8.safetensors"
OUTPUT_DIR = "/home/javierferb/n8n/tools/test_output/pokemon_tests"
ARTIFACT_DIR = "/home/javierferb/.gemini/antigravity/brain/580d2633-4ee0-4c17-bcaf-fff9422f1bb3"

os.makedirs(OUTPUT_DIR, exist_ok=True)

SCENES = [
    {
        "filename": "01_gengar_rain.jpg",
        "name": "Gengar en callejón lluvioso",
        "positive": "cinematic anime film still, gengar pokemon sitting in a dark rainy alleyway at night, glowing sinister eyes, purple shadow aura, puddles with neon reflections, makoto shinkai and studio ghibli aesthetic, volumetric lighting, masterpiece, 8k",
        "negative": "deformed, extra limbs, bad anatomy, blurry, cartoonish, low resolution, multiple heads, human, signature, watermark",
        "seed": 42081512
    },
    {
        "filename": "02_cubone_campfire.jpg",
        "name": "Cubone melancólico en fogata",
        "positive": "emotional cinematic anime still, single cubone pokemon sitting near a small campfire at dusk, wearing bone skull mask, holding bone club, sad and nostalgic atmosphere, warm glowing firelight, highly detailed fantasy digital painting, 8k",
        "negative": "human, girl, boy, deformed, extra arms, bad skull, duplicate, blurry, low quality, signature, watermark",
        "seed": 71829341
    },
    {
        "filename": "03_charizard_storm.jpg",
        "name": "Charizard en tormenta de montaña",
        "positive": "epic cinematic anime shot of charizard pokemon roaring on top of a stormy mountain cliff, flame tail burning bright in the rain, dramatic lightning in dark clouds, dynamic action angle, masterpiece, 8k",
        "negative": "deformed wings, extra legs, bad face, blurry, lowres, text, watermark, signature, duplicate",
        "seed": 93018247
    }
]

def build_workflow(positive_prompt: str, negative_prompt: str, seed: int, width: int = 896, height: int = 512, steps: int = 22, cfg: float = 7.0):
    return {
        "prompt": {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": CHECKPOINT_NAME
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
                    "text": negative_prompt,
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
                    "cfg": cfg,
                    "sampler_name": "euler_ancestral",
                    "scheduler": "karras",
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
                    "filename_prefix": f"pokemon_{seed}",
                    "images": ["6", 0]
                }
            }
        }
    }

def generate_image(scene: dict, target_size=(1280, 720)):
    start_time = time.time()
    workflow = build_workflow(
        positive_prompt=scene["positive"],
        negative_prompt=scene["negative"],
        seed=scene["seed"],
        width=896,
        height=512,
        steps=22,
        cfg=7.0
    )

    req_data = json.dumps(workflow).encode("utf-8")
    req = urllib.request.Request(f"{COMFYUI_HOST}/prompt", data=req_data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        res = json.loads(resp.read().decode("utf-8"))

    prompt_id = res.get("prompt_id")
    if not prompt_id:
        raise RuntimeError("No se obtuvo prompt_id de ComfyUI")

    # Polling hasta que finalice
    image_info = None
    timeout = 60.0
    while time.time() - start_time < timeout:
        time.sleep(0.5)
        try:
            hist_req = urllib.request.Request(f"{COMFYUI_HOST}/history/{prompt_id}")
            with urllib.request.urlopen(hist_req, timeout=3.0) as h_resp:
                history = json.loads(h_resp.read().decode("utf-8"))
            if prompt_id in history:
                outputs = history[prompt_id].get("outputs", {})
                if "7" in outputs and "images" in outputs["7"] and len(outputs["7"]["images"]) > 0:
                    image_info = outputs["7"]["images"][0]
                    break
        except Exception:
            pass

    if not image_info:
        raise TimeoutError(f"Timeout generando imagen {scene['filename']}")

    filename = image_info.get("filename")
    subfolder = image_info.get("subfolder", "")
    img_type = image_info.get("type", "output")

    local_path = os.path.join(COMFYUI_OUTPUT_DIR, subfolder, filename) if COMFYUI_OUTPUT_DIR else None
    if local_path and os.path.exists(local_path):
        img_pil = Image.open(local_path)
    else:
        view_url = f"{COMFYUI_HOST}/view?filename={filename}&subfolder={subfolder}&type={img_type}"
        with urllib.request.urlopen(view_url, timeout=5.0) as v_resp:
            img_pil = Image.open(BytesIO(v_resp.read()))

    # Redimensionar a target_size con Lanczos
    img_pil = img_pil.convert("RGB")
    if img_pil.size != target_size:
        img_pil = img_pil.resize(target_size, Image.Resampling.LANCZOS)

    out_file = os.path.join(OUTPUT_DIR, scene["filename"])
    img_pil.save(out_file, "JPEG", quality=95)

    # Copiar también al directorio de artefactos para inspección
    if os.path.exists(ARTIFACT_DIR):
        artifact_out = os.path.join(ARTIFACT_DIR, scene["filename"])
        img_pil.save(artifact_out, "JPEG", quality=95)

    elapsed = round(time.time() - start_time, 2)
    return out_file, elapsed

def main():
    print("=== INICIANDO GENERACIÓN DE 3 MUESTRAS POKÉMON EN COMFYUI LOCAL ===")
    results = []
    for sc in SCENES:
        print(f"Renderizando [{sc['name']}] -> {sc['filename']}...")
        try:
            path, dur = generate_image(sc)
            print(f"  ✓ Completado en {dur}s: {path}")
            results.append({"name": sc["name"], "file": sc["filename"], "time": dur, "status": "success", "path": path})
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({"name": sc["name"], "file": sc["filename"], "error": str(e), "status": "error"})

    print("\n=== RESUMEN DE RENDERS ===")
    for r in results:
        if r["status"] == "success":
            print(f"• {r['file']} ({r['name']}): {r['time']} segundos [OK]")
        else:
            print(f"• {r['file']}: ERROR ({r.get('error')})")

if __name__ == "__main__":
    main()
