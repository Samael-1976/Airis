# src/connectors/webhook.py
# Esecutore Autonomo per Webhooks (v2.0 - BaseConnector Refactor)
# LEGGE A0099: Invarianza strutturale garantita.

import sys
import os
import json
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
    print('{"status": "error", "message": "' + t("webhook.lib_error") + '"}')
    sys.exit(1)

def trigger_webhook(connector: BaseConnector, params: dict, creds: dict) -> str:
    url = params.get("url") or creds.get("default_url")
    if not url:
        raise ValueError(t("webhook.url_error"))

    method = params.get("method", "POST").upper()
    payload = params.get("payload", {})
    headers = params.get("headers", {"Content-Type": "application/json"})

    if "auth_header" in creds and "auth_token" in creds:
        headers[creds["auth_header"]] = creds["auth_token"]
        connector.log_debug(f"Aggiunto header auth: {creds['auth_header']}")

    connector.log_debug(f"Richiesta: {method} {url}")
    connector.log_debug(f"Payload: {json.dumps(payload)}")

    try:
        response = requests.request(method, url, json=payload, headers=headers, timeout=10)
        connector.log_debug(f"Response Status: {response.status_code}")

        raw_response_text = ""
        try:
            response_data = response.json()
            raw_response_text = json.dumps(response_data, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            raw_response_text = response.text

        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        connector.log_debug("Inoltro risposta all'agente locale per il Triage...")

        agent_input = f"METODO: {method}\nURL: {url}\nSTATUS CODE: {response.status_code}\nRISPOSTA CORPO:\n{raw_response_text[:5000]}"

        smart_summary = ask_local_llm(
            data_to_analyze=agent_input,
            context_description=t("webhook.context_trigger", url=url),
            avatar_name=avatar_name,
        )

        return smart_summary

    except requests.exceptions.RequestException as e:
        connector.log_debug(f"Errore richiesta: {e}")
        if e.response is not None:
            connector.log_debug(f"Errore Body: {e.response.text}")
        raise Exception(t("webhook.request_error", error=str(e)))

def action_wrapper(connector: BaseConnector, action_func, params: dict):
    guardian = Guardian()
    creds_config = guardian.get_credentials("webhook_api") or {}
    return action_func(connector, params, creds_config)

if __name__ == "__main__":
    connector = BaseConnector("Connettore per Webhooks.")
    connector.register_action("trigger", lambda params: action_wrapper(connector, trigger_webhook, params))
    connector.run()