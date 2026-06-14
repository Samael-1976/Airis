# src/connectors/image_gen.py
# Esecutore Autonomo per Generazione Immagini (Flux & DALL-E 3) (v1.0)

import argparse
import json
import sys
import os
import time
import requests
import base64
from pathlib import Path
from datetime import datetime
from utils.translator import t

# --- GESTIONE DEI PERCORSI PER L'AUTONOMIA ---
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from src.guardian import Guardian
except ImportError:
    print(
        json.dumps(
            {"status": "error", "message": t("image_gen.err_guardian_not_found")}
        )
    )
    sys.exit(1)

# --- CONFIGURAZIONE ---
TEMP_IMAGE_PATH = PROJECT_ROOT / "temp_images"
TEMP_IMAGE_PATH.mkdir(exist_ok=True)


def save_image_from_url(url: str, prefix: str) -> str:
    """Scarica un'immagine da URL e la salva in temp_images."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        filename = f"{prefix}_{int(time.time())}.png"
        file_path = TEMP_IMAGE_PATH / filename

        with open(file_path, "wb") as f:
            f.write(response.content)

        # Restituisce il percorso relativo per il frontend
        return f"temp_images/{filename}"
    except Exception as e:
        raise Exception(t("image_gen.err_save_failed", error=e))


def generate_flux(params: dict) -> str:
    """
    Genera un'immagine usando Flux (via Pollinations.ai - Gratuito/No Auth).
    'params' deve contenere 'prompt'. Opzionali: 'width', 'height', 'seed'.
    """
    if "prompt" not in params:
        raise ValueError(t("image_gen.err_missing_prompt_flux"))

    prompt = params["prompt"]
    width = params.get("width", 1080)
    height = params.get("height", 1920)
    seed = params.get("seed", 42)
    model = params.get("model", "flux")  # flux, turbo, etc.

    # Costruzione URL Pollinations (come da workflow n8n)
    # URL pattern: https://image.pollinations.ai/prompt/{prompt}?width={width}&height={height}&model={model}&seed={seed}&nologo=true
    encoded_prompt = requests.utils.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model={model}&seed={seed}&nologo=true"

    try:
        # Pollinations restituisce direttamente l'immagine
        local_path = save_image_from_url(url, "flux")
        return t("image_gen.flux_success", prompt=prompt, path=local_path)
    except Exception as e:
        raise Exception(t("image_gen.err_flux_failed", error=e))


def generate_dalle3(params: dict, creds: dict) -> str:
    """
    Genera un'immagine usando OpenAI DALL-E 3.
    'params' deve contenere 'prompt'.
    """
    api_key = creds.get("api_key")
    if not api_key or "IL_TUO" in api_key:
        raise ValueError(t("image_gen.err_no_api_key"))

    if "prompt" not in params:
        raise ValueError(t("image_gen.err_missing_prompt"))

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    data = {
        "model": "dall-e-3",
        "prompt": params["prompt"],
        "n": 1,
        "size": params.get("size", "1024x1024"),
        "quality": params.get("quality", "standard"),
        "style": params.get("style", "vivid"),
    }

    try:
        response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers=headers,
            json=data,
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()

        image_url = result["data"][0]["url"]
        revised_prompt = result["data"][0].get("revised_prompt", "N/A")

        local_path = save_image_from_url(image_url, "dalle3")

        return t(
            "image_gen.dalle_success", revised_prompt=revised_prompt, path=local_path
        )

    except Exception as e:
        raise Exception(t("image_gen.err_dalle_failed", error=e))


def main():
    parser = argparse.ArgumentParser(description=t("image_gen.help_desc"))
    parser.add_argument(
        "--action",
        required=True,
        choices=["generate_flux", "generate_dalle3"],
        help=t("image_gen.help_action"),
    )
    parser.add_argument(
        "--params", type=str, default="{}", help=t("image_gen.help_params")
    )

    args = parser.parse_args()

    try:
        guardian = Guardian()
        # Usiamo una chiave generica 'image_gen_api' per DALL-E, Flux non ne ha bisogno
        creds_config = guardian.get_credentials("image_gen_api") or {}

        params = json.loads(args.params)

        result_data = None
        if args.action == "generate_flux":
            result_data = generate_flux(params)
        elif args.action == "generate_dalle3":
            result_data = generate_dalle3(params, creds_config)

        print(json.dumps({"status": "success", "data": result_data}))

    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
