# src/connectors/image_gen.py
# Esecutore Autonomo per Generazione Immagini (v2.0 - BaseConnector Refactor)
# LEGGE A0099: Invarianza strutturale garantita.

import sys
import os
import time
import requests
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.translator import t
from src.connectors.base_connector import BaseConnector

try:
    from src.guardian import Guardian
    from agent_base import ask_local_llm
except ImportError:
    print('{"status": "error", "message": "' + t("image_gen.lib_error") + '"}')
    sys.exit(1)

TEMP_IMAGE_PATH = PROJECT_ROOT / "temp_images"
TEMP_IMAGE_PATH.mkdir(exist_ok=True)

def save_image_from_url(connector: BaseConnector, url: str, prefix: str) -> str:
    connector.log_debug(f"Download immagine da: {url[:50]}...")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        filename = f"{prefix}_{int(time.time())}.png"
        file_path = TEMP_IMAGE_PATH / filename

        with open(file_path, "wb") as f:
            f.write(response.content)

        connector.log_debug(f"Immagine salvata in: {file_path}")
        return f"temp_images/{filename}"
    except Exception as e:
        connector.log_debug(f"Errore download/salvataggio: {e}")
        raise Exception(t("image_gen.save_error", error=e))

def generate_flux(connector: BaseConnector, params: dict) -> str:
    if "prompt" not in params:
        raise ValueError("Parametro 'prompt' mancante.")

    prompt = params["prompt"]
    width = params.get("width", 1080)
    height = params.get("height", 1920)
    seed = params.get("seed", 42)
    model = params.get("model", "flux")

    connector.log_debug(f"Generazione Flux. Prompt: '{prompt}', Size: {width}x{height}, Seed: {seed}")

    encoded_prompt = requests.utils.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model={model}&seed={seed}&nologo=true"

    connector.log_debug(f"URL Pollinations: {url}")

    try:
        local_path = save_image_from_url(connector, url, "flux")

        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", t("tts.unknown_lang"))
        confirmation_data = t("image_gen.flux_confirm", prompt=prompt, path=local_path)

        smart_confirmation = ask_local_llm(
            data_to_analyze=confirmation_data,
            context_description=t("image_gen.context_flux"),
            avatar_name=avatar_name,
        )

        return f"{smart_confirmation}\nPercorso: {local_path}"

    except Exception as e:
        connector.log_debug(f"Errore Flux: {e}")
        raise Exception(f"Errore generazione Flux: {e}")

def generate_dalle3(connector: BaseConnector, params: dict) -> str:
    guardian = Guardian()
    creds = guardian.get_credentials("image_gen_api") or {}
    api_key = creds.get("api_key")
    
    if not api_key or "IL_TUO" in api_key:
        connector.log_debug("API Key OpenAI mancante.")
        raise ValueError(t("image_gen.auth_error"))

    if "prompt" not in params:
        raise ValueError("Parametro 'prompt' mancante.")

    connector.log_debug(f"Generazione DALL-E 3. Prompt: '{params['prompt']}'")

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
        connector.log_debug("Invio richiesta a OpenAI API...")
        response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers=headers,
            json=data,
            timeout=60,
        )

        if response.status_code != 200:
            connector.log_debug(f"Errore API OpenAI: {response.text}")

        response.raise_for_status()
        result = response.json()

        image_url = result["data"][0]["url"]
        revised_prompt = result["data"][0].get("revised_prompt", "N/A")

        connector.log_debug(f"Immagine generata. URL: {image_url[:50]}...")

        local_path = save_image_from_url(connector, image_url, "dalle3")

        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", t("tts.unknown_lang"))
        confirmation_data = t(
            "image_gen.dalle_confirm",
            prompt=params["prompt"],
            revised=revised_prompt,
            path=local_path,
        )

        smart_confirmation = ask_local_llm(
            data_to_analyze=confirmation_data,
            context_description=t("image_gen.context_dalle"),
            avatar_name=avatar_name,
        )

        return f"{smart_confirmation}\nPercorso: {local_path}"

    except Exception as e:
        connector.log_debug(f"Eccezione DALL-E: {e}")
        raise Exception(f"Errore API OpenAI: {e}")

if __name__ == "__main__":
    connector = BaseConnector("Connettore per Generazione Immagini (Flux/DALL-E).")
    connector.register_action("generate_flux", lambda params: generate_flux(connector, params))
    connector.register_action("generate_dalle3", lambda params: generate_dalle3(connector, params))
    connector.run()