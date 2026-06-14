# src/connectors/iot_hub.py
# [DEV] Il Ponte Universale Deus Ex Machina (v2.0 - BaseConnector Refactor)
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

IOT_LAYOUT_PATH = PROJECT_ROOT / "config" / "iot_layout.json"
CREDENTIALS_PATH = PROJECT_ROOT / "config" / "credentials.yaml"

def load_layout(connector: BaseConnector) -> dict:
    if not IOT_LAYOUT_PATH.exists():
        return {"rooms":[], "automations":[]}
    try:
        with open(IOT_LAYOUT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        connector.log_debug(f"Errore lettura layout: {e}")
        return {"rooms": [], "automations":[]}

def get_ha_creds(connector: BaseConnector) -> dict:
    try:
        import yaml
        if CREDENTIALS_PATH.exists():
            with open(CREDENTIALS_PATH, "r", encoding="utf-8") as f:
                creds = yaml.safe_load(f)
                return creds.get("home_assistant", {})
    except Exception as e:
        connector.log_debug(f"Errore lettura credenziali HA: {e}")
    return {}

def execute_command(connector: BaseConnector, params: dict) -> dict:
    device_id = params.get("device_id")
    action = params.get("action")
    value = params.get("value")

    if not device_id or not action:
        raise ValueError(t("iot_hub.params_error"))

    layout = load_layout(connector)
    device = None

    for room in layout.get("rooms", []):
        for dev in room.get("devices",[]):
            if dev["id"] == device_id:
                device = dev
                break
        if device:
            break

    if not device:
        raise ValueError(t("iot_hub.device_not_found", id=device_id))

    protocol = device.get("protocol", "http_get")
    ip = device.get("ip", "")
    commands = device.get("commands", {})

    if action not in commands:
        raise ValueError(t("iot_hub.action_not_defined", action=action, name=device["name"]))

    cmd_path = commands[action]
    if value is not None:
        cmd_path = cmd_path.replace("{val}", str(value))

    url = f"http://{ip}{cmd_path}" if not cmd_path.startswith("http") else cmd_path

    try:
        if protocol == "http_get":
            connector.log_debug(f"Esecuzione HTTP GET: {url}")
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            return {"status": "success", "data": resp.text}

        elif protocol == "http_post":
            connector.log_debug(f"Esecuzione HTTP POST: {url}")
            payload = {"value": value} if value is not None else {}
            resp = requests.post(url, json=payload, timeout=5)
            resp.raise_for_status()
            return {
                "status": "success",
                "data": resp.json() if "json" in resp.headers.get("Content-Type", "") else resp.text,
            }

        elif protocol == "ha":
            ha_creds = get_ha_creds(connector)
            token = ha_creds.get("token")
            ha_url = ha_creds.get("url", "").rstrip("/")

            if not token or not ha_url:
                raise ValueError(t("iot_hub.ha_creds_missing"))

            full_ha_url = f"{ha_url}{cmd_path}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            payload = {"entity_id": ip}
            if value is not None:
                payload["brightness_pct"] = value

            connector.log_debug(f"Esecuzione HA API: {full_ha_url}")
            resp = requests.post(full_ha_url, headers=headers, json=payload, timeout=5)
            resp.raise_for_status()
            return {"status": "success", "data": resp.json()}

        elif protocol == "mqtt":
            connector.log_debug("MQTT non ancora implementato nativamente. Usa HTTP bridge o HA.")
            raise ValueError(t("iot_hub.mqtt_not_implemented"))

        else:
            raise ValueError(t("iot_hub.protocol_not_supported", protocol=protocol))

    except Exception as e:
        connector.log_debug(f"Errore esecuzione: {e}")
        raise e

if __name__ == "__main__":
    connector = BaseConnector("Connettore IOT Hub per Smart Home.")
    connector.register_action("execute", lambda params: execute_command(connector, params))
    connector.register_action("test", lambda params: execute_command(connector, params))
    connector.run()