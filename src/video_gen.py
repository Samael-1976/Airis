# src/connectors/video_gen.py
# Esecutore Autonomo per Generazione Video (Fal.ai/VEO3 & Kie.ai/Sora2) (v1.0)

import argparse
import json
import sys
import os
import time
import requests
from pathlib import Path
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
            {"status": "error", "message": t("connectors.video_gen.guardian_not_found")}
        )
    )
    sys.exit(1)

# --- CONFIGURAZIONE ---
# Usiamo temp_images per coerenza con il server che serve questa cartella per i media
TEMP_MEDIA_PATH = PROJECT_ROOT / "temp_images"
TEMP_MEDIA_PATH.mkdir(exist_ok=True)


def download_video(url: str, prefix: str) -> str:
    """Scarica un video da URL e lo salva localmente."""
    try:
        response = requests.get(url, stream=True, timeout=120)
        response.raise_for_status()

        filename = f"{prefix}_{int(time.time())}.mp4"
        file_path = TEMP_MEDIA_PATH / filename

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Restituisce il percorso relativo per il frontend
        return f"temp_images/{filename}"
    except Exception as e:
        raise Exception(t("connectors.video_gen.download_error", error=e))


def generate_veo3(params: dict, creds: dict) -> str:
    """
    Genera un video usando Google VEO3 tramite Fal.ai.
    'params' deve contenere 'prompt'. Opzionali: 'aspect_ratio' (default 16:9), 'duration' (default 8s).
    """
    api_key = creds.get("fal_key")
    if not api_key or "IL_TUO" in api_key:
        raise ValueError(t("connectors.video_gen.fal_key_missing"))

    if "prompt" not in params:
        raise ValueError(t("connectors.video_gen.prompt_missing"))

    headers = {"Authorization": f"Key {api_key}", "Content-Type": "application/json"}

    payload = {
        "prompt": params["prompt"],
        "aspect_ratio": params.get("aspect_ratio", "16:9"),
        "duration": params.get("duration", "8s"),
    }

    # 1. Invia richiesta
    try:
        response = requests.post(
            "https://queue.fal.run/fal-ai/veo3",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        request_id = response.json().get("request_id")
    except Exception as e:
        raise Exception(t("connectors.video_gen.veo3_request_error", error=e))

    # 2. Polling stato
    status_url = f"https://queue.fal.run/fal-ai/veo3/requests/{request_id}/status"
    result_url = f"https://queue.fal.run/fal-ai/veo3/requests/{request_id}"

    max_retries = 60  # 60 tentativi * 2s = 2 minuti max
    for _ in range(max_retries):
        time.sleep(2)
        try:
            status_res = requests.get(status_url, headers=headers, timeout=10)
            status_data = status_res.json()
            status = status_data.get("status")

            if status == "COMPLETED":
                # Recupera risultato
                res = requests.get(result_url, headers=headers, timeout=10)
                data = res.json()
                video_url = data.get("video", {}).get("url")
                if not video_url:
                    raise Exception(t("connectors.video_gen.video_url_not_found"))

                local_path = download_video(video_url, "veo3")
                return t(
                    "connectors.video_gen.veo3_success",
                    prompt=params["prompt"],
                    path=local_path,
                )

            elif status == "FAILED":
                raise Exception(
                    t(
                        "connectors.video_gen.generation_failed",
                        error=status_data.get("error"),
                    )
                )

        except Exception as e:
            if t("connectors.video_gen.generation_failed_tag") in str(e):
                raise e
            continue  # Riprova in caso di errori di rete temporanei

    raise TimeoutError(t("connectors.video_gen.veo3_timeout"))


def generate_sora2(params: dict, creds: dict) -> str:
    """
    Genera un video usando Sora 2 tramite Kie.ai.
    'params' deve contenere 'prompt'. Opzionali: 'aspect_ratio', 'quality'.
    """
    api_key = creds.get("kie_key")
    if not api_key or "IL_TUO" in api_key:
        raise ValueError(t("connectors.video_gen.kie_key_missing"))

    if "prompt" not in params:
        raise ValueError(t("connectors.video_gen.prompt_missing"))

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    # Supporto Text-to-Video e Image-to-Video
    model = "sora-2-text-to-video"
    input_data = {
        "prompt": params["prompt"],
        "aspect_ratio": params.get("aspect_ratio", "16:9"),
        "quality": params.get("quality", "standard"),
    }

    if "image_url" in params:
        model = "sora-2-image-to-video"
        input_data["image_urls"] = [params["image_url"]]

    payload = {"model": model, "input": input_data}

    # 1. Invia richiesta
    try:
        response = requests.post(
            "https://api.kie.ai/api/v1/jobs/createTask",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        task_id = response.json().get("data", {}).get("taskId")
        if not task_id:
            # Fallback se la struttura è diversa
            task_id = response.json().get("taskId")
    except Exception as e:
        raise Exception(t("connectors.video_gen.sora2_request_error", error=e))

    # 2. Polling stato
    status_url = f"https://api.kie.ai/api/v1/jobs/recordInfo?taskId={task_id}"

    max_retries = 60  # 2 minuti
    for _ in range(max_retries):
        time.sleep(2)
        try:
            status_res = requests.get(status_url, headers=headers, timeout=10)
            status_data = status_res.json()
            state = status_data.get("data", {}).get("state")

            if state == "success":
                result_json_str = status_data.get("data", {}).get("resultJson")
                if result_json_str:
                    result_json = json.loads(result_json_str)
                    video_urls = result_json.get("resultUrls", [])
                    if video_urls:
                        local_path = download_video(video_urls[0], "sora2")
                        return t(
                            "connectors.video_gen.sora2_success",
                            prompt=params["prompt"],
                            path=local_path,
                        )
                raise Exception(t("connectors.video_gen.video_url_not_found"))

            elif state == "failed":
                raise Exception(
                    t(
                        "connectors.video_gen.generation_failed",
                        error=status_data.get("data", {}).get("error"),
                    )
                )

        except Exception as e:
            if t("connectors.video_gen.generation_failed_tag") in str(e):
                raise e
            continue

    raise TimeoutError(t("connectors.video_gen.sora2_timeout"))


def main():
    parser = argparse.ArgumentParser(
        description="Connettore per Generazione Video (VEO3/Sora2)."
    )
    parser.add_argument(
        "--action",
        required=True,
        choices=["generate_veo3", "generate_sora2"],
        help="Azione da eseguire.",
    )
    parser.add_argument(
        "--params", type=str, default="{}", help="Parametri JSON per l'azione."
    )

    args = parser.parse_args()

    try:
        guardian = Guardian()
        creds_config = guardian.get_credentials("video_gen_api") or {}

        params = json.loads(args.params)

        result_data = None
        if args.action == "generate_veo3":
            result_data = generate_veo3(params, creds_config)
        elif args.action == "generate_sora2":
            result_data = generate_sora2(params, creds_config)

        print(json.dumps({"status": "success", "data": result_data}))

    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
