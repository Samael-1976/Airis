# src/connectors/wordpress.py
# Esecutore Autonomo per WordPress (v2.0 - BaseConnector Refactor)
# LEGGE A0099: Invarianza strutturale garantita.

import sys
import os
import base64
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
    print('{"status": "error", "message": "' + t("wordpress.lib_error") + '"}')
    sys.exit(1)

def get_auth_header(connector: BaseConnector, username: str, app_password: str) -> dict:
    connector.log_debug(f"Generazione header auth per utente: {username}")
    credentials = f"{username}:{app_password}"
    token = base64.b64encode(credentials.encode())
    return {"Authorization": f'Basic {token.decode("utf-8")}'}

def get_posts(connector: BaseConnector, params: dict, creds: dict) -> str:
    base_url = creds.get("url")
    username = creds.get("username")
    app_password = creds.get("application_password")

    if not all([base_url, username, app_password]) or "IL_TUO" in base_url:
        connector.log_debug("Credenziali mancanti o placeholder.")
        raise ValueError(t("wordpress.auth_error"))

    base_url = base_url.rstrip("/")
    endpoint = f"{base_url}/wp-json/wp/v2/posts"

    per_page = params.get("per_page", 5)
    status = params.get("status", "publish")

    connector.log_debug(f"Richiesta post da: {endpoint} (Limit: {per_page}, Status: {status})")

    try:
        response = requests.get(
            endpoint,
            headers=get_auth_header(connector, username, app_password),
            params={"per_page": per_page, "status": status, "context": "view"},
            timeout=10,
        )

        response.raise_for_status()
        posts = response.json()
        connector.log_debug(f"Post trovati: {len(posts)}")

        if not posts:
            return t("wordpress.no_posts")

        raw_data_list =[]
        for post in posts:
            title = post["title"]["rendered"]
            date = post["date"]
            link = post["link"]
            excerpt = post.get("excerpt", {}).get("rendered", "")
            raw_data_list.append(f"TITOLO: {title} | DATA: {date} | LINK: {link} | ESTRATTO: {excerpt[:300]}")

        raw_string = "\n---\n".join(raw_data_list)
        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        connector.log_debug("Inoltro post all'agente locale per il Triage...")

        smart_summary = ask_local_llm(
            data_to_analyze=raw_string,
            context_description=t("wordpress.context_list", url=base_url),
            avatar_name=avatar_name,
        )

        return smart_summary

    except requests.exceptions.RequestException as e:
        connector.log_debug(f"Errore API: {e}")
        raise Exception(t("wordpress.api_error", error=str(e)))

def create_post(connector: BaseConnector, params: dict, creds: dict) -> str:
    base_url = creds.get("url")
    username = creds.get("username")
    app_password = creds.get("application_password")

    if not all([base_url, username, app_password]) or "IL_TUO" in base_url:
        raise ValueError("Credenziali WordPress non configurate correttamente.")

    if "title" not in params or "content" not in params:
        raise ValueError("Parametri 'title' e 'content' mancanti.")

    base_url = base_url.rstrip("/")
    endpoint = f"{base_url}/wp-json/wp/v2/posts"

    post_data = {
        "title": params["title"],
        "content": params["content"],
        "status": params.get("status", "draft"),
    }

    connector.log_debug(f"Creazione post '{params['title']}' su {endpoint}")

    try:
        response = requests.post(
            endpoint,
            headers=get_auth_header(connector, username, app_password),
            json=post_data,
            timeout=10,
        )

        response.raise_for_status()
        new_post = response.json()
        connector.log_debug(f"Post creato. ID: {new_post['id']}")

        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        confirmation_data = t(
            "wordpress.create_confirm",
            title=params["title"],
            id=new_post["id"],
            link=new_post["link"],
            status=new_post["status"],
        )

        smart_confirmation = ask_local_llm(
            data_to_analyze=confirmation_data,
            context_description=t("wordpress.context_create"),
            avatar_name=avatar_name,
        )

        return smart_confirmation

    except requests.exceptions.RequestException as e:
        connector.log_debug(f"Errore creazione post: {e}")
        raise Exception(f"Errore creazione post WordPress: {e}")

def action_wrapper(connector: BaseConnector, action_func, params: dict):
    guardian = Guardian()
    creds_config = guardian.get_credentials("wordpress_api")
    if not creds_config:
        raise ValueError("Configurazione 'wordpress_api' non trovata in credentials.yaml.")
    return action_func(connector, params, creds_config)

if __name__ == "__main__":
    connector = BaseConnector("Connettore per WordPress.")
    connector.register_action("get_posts", lambda params: action_wrapper(connector, get_posts, params))
    connector.register_action("create_post", lambda params: action_wrapper(connector, create_post, params))
    connector.run()