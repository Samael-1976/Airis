# src/connectors/video_gen.py
# Esecutore Autonomo per Generazione Video (v2.0 - BaseConnector Refactor)
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
    print('{"status": "error", "message": "' + t("video_gen.lib_error") + '"}')
    sys.exit(1)

TEMP_MEDIA_PATH = PROJECT_ROOT / "temp_images"
TEMP_MEDIA_PATH.mkdir(exist_ok=True)

def download_video(connector: BaseConnector, url: str, prefix: str) -> str:
    connector.log_debug(f"Download video da: {url[:50]}...")
    try:
        response = requests.get(url, stream=True, timeout=120)
        response.raise_for_status()

        filename = f"{prefix}_{int(time.time())}.mp4"
        file_path = TEMP_MEDIA_PATH / filename

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        connector.log_debug(f"Video salvato in: {file_path}")
        return f"temp_images/{filename}"
    except Exception as e:
        connector.log_debug(f"Errore download: {e}")
        raise Exception(t("video_gen.download_error", error=e))

def generate_veo3(connector: BaseConnector, params: dict, creds: dict) -> str:
    api_key = creds.get("fal_key")
    if not api_key or "IL_TUO" in api_key:
        connector.log_debug("API Key Fal.ai mancante.")
        raise ValueError(t("video_gen.auth_fal_error"))

    if "prompt" not in params:
        raise ValueError("Parametro 'prompt' mancante.")

    connector.log_debug(f"Generazione VEO3. Prompt: '{params['prompt']}'")

    headers = {"Authorization": f"Key {api_key}", "Content-Type": "application/json"}

    payload = {
        "prompt": params["prompt"],
        "aspect_ratio": params.get("aspect_ratio", "16:9"),
        "duration": params.get("duration", "8s"),
    }

    try:
        response = requests.post("https://queue.fal.run/fal-ai/veo3", headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        request_id = response.json().get("request_id")
        connector.log_debug(f"Richiesta inviata. ID: {request_id}")
    except Exception as e:
        raise Exception(f"Errore richiesta VEO3: {e}")

    status_url = f"https://queue.fal.run/fal-ai/veo3/requests/{request_id}/status"
    result_url = f"https://queue.fal.run/fal-ai/veo3/requests/{request_id}"

    max_retries = 60
    for i in range(max_retries):
        time.sleep(2)
        try:
            status_res = requests.get(status_url, headers=headers, timeout=10)
            status_data = status_res.json()
            status = status_data.get("status")

            if status == "COMPLETED":
                res = requests.get(result_url, headers=headers, timeout=10)
                data = res.json()
                video_url = data.get("video", {}).get("url")
                if not video_url:
                    raise Exception("Video URL non trovato.")

                local_path = download_video(connector, video_url, "veo3")

                avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
                confirmation_data = t("video_gen.veo_confirm", prompt=params["prompt"], path=local_path)

                smart_confirmation = ask_local_llm(
                    data_to_analyze=confirmation_data,
                    context_description=t("video_gen.context_veo"),
                    avatar_name=avatar_name,
                )

                return f"{smart_confirmation}\nPercorso: {local_path}"

            elif status == "FAILED":
                raise Exception(f"Generazione fallita: {status_data.get('error')}")

        except Exception as e:
            if "Generazione fallita" in str(e):
                raise e
            continue

    raise TimeoutError(t("video_gen.timeout_error", engine="VEO3"))

def generate_sora2(connector: BaseConnector, params: dict, creds: dict) -> str:
    api_key = creds.get("kie_key")
    if not api_key or "IL_TUO" in api_key:
        connector.log_debug("API Key Kie.ai mancante.")
        raise ValueError(t("video_gen.auth_kie_error"))

    if "prompt" not in params:
        raise ValueError("Parametro 'prompt' mancante.")

    connector.log_debug(f"Generazione Sora 2. Prompt: '{params['prompt']}'")

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

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

    try:
        response = requests.post("https://api.kie.ai/api/v1/jobs/createTask", headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        task_id = response.json().get("data", {}).get("taskId") or response.json().get("taskId")
        connector.log_debug(f"Task ID ricevuto: {task_id}")
    except Exception as e:
        raise Exception(f"Errore richiesta Sora 2: {e}")

    status_url = f"https://api.kie.ai/api/v1/jobs/recordInfo?taskId={task_id}"

    max_retries = 60
    for i in range(max_retries):
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
                        local_path = download_video(connector, video_urls[0], "sora2")

                        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
                        confirmation_data = t("video_gen.sora_confirm", prompt=params["prompt"], path=local_path)

                        smart_confirmation = ask_local_llm(
                            data_to_analyze=confirmation_data,
                            context_description=t("video_gen.context_sora"),
                            avatar_name=avatar_name,
                        )

                        return f"{smart_confirmation}\nPercorso: {local_path}"
                raise Exception("URL video non trovato.")

            elif state == "failed":
                raise Exception(f"Generazione fallita: {status_data.get('data', {}).get('error')}")

        except Exception as e:
            if "Generazione fallita" in str(e):
                raise e
            continue

    raise TimeoutError(t("video_gen.timeout_error", engine="Sora 2"))

def action_wrapper(connector: BaseConnector, action_func, params: dict):
    guardian = Guardian()
    creds_config = guardian.get_credentials("video_gen_api") or {}
    return action_func(connector, params, creds_config)

if __name__ == "__main__":
    connector = BaseConnector("Connettore per Generazione Video.")
    connector.register_action("generate_veo3", lambda params: action_wrapper(connector, generate_veo3, params))
    connector.register_action("generate_sora2", lambda params: action_wrapper(connector, generate_sora2, params))
    connector.run()