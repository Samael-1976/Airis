# src/connectors/notion.py
# Esecutore Autonomo per Notion (v2.0 - BaseConnector Refactor)
# LEGGE A0099: Invarianza strutturale garantita.

import sys
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.translator import t
from src.connectors.base_connector import BaseConnector

try:
    from notion_client import Client
    from src.guardian import Guardian
    from agent_base import ask_local_llm
except ImportError:
    print('{"status": "error", "message": "' + t("notion.lib_error") + '"}')
    sys.exit(1)

def authenticate(connector: BaseConnector, creds: dict) -> Client:
    auth_token = creds.get("auth_token")

    if not auth_token or "IL_TUO" in auth_token:
        connector.log_debug("Token mancante o placeholder.")
        raise ValueError(t("notion.auth_error"))

    connector.log_debug(f"Inizializzazione client con token: {auth_token[:4]}...{auth_token[-4:]}")
    client = Client(auth=auth_token)

    try:
        connector.log_debug("Verifica token (users.me)...")
        me = client.users.me()
        connector.log_debug(f"Autenticazione riuscita. Bot: {me.get('name')} ({me.get('id')})")
    except Exception as e:
        connector.log_debug(f"Errore autenticazione: {e}")
        raise ConnectionError(t("notion.conn_failed", error=str(e)))

    return client

def search(connector: BaseConnector, client: Client, params: dict) -> str:
    if "query" not in params:
        raise ValueError("Parametro 'query' mancante.")

    connector.log_debug(f"Ricerca: '{params['query']}'")

    try:
        results = client.search(query=params["query"]).get("results")
        connector.log_debug(f"Elementi trovati: {len(results) if results else 0}")

        if not results:
            return t("notion.no_results", query=params["query"])

        raw_data_list =[]
        for result in results:
            obj_type = result.get("object")
            title = "Senza titolo"

            if obj_type == "page":
                props = result.get("properties", {})
                for prop_name, prop_val in props.items():
                    if prop_val.get("type") == "title":
                        title_list = prop_val.get("title",[])
                        if title_list:
                            title = title_list[0].get("plain_text", "Senza titolo")
                        break

            elif obj_type == "database":
                title_list = result.get("title",[])
                if title_list:
                    title = title_list[0].get("plain_text", "Senza titolo")

            url = result.get("url", "N/A")
            raw_data_list.append(f"TIPO: {obj_type} | TITOLO: {title} | ID: {result['id']} | URL: {url}")

        raw_string = "\n".join(raw_data_list)
        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        connector.log_debug("Inoltro risultati all'agente locale per il Triage...")

        smart_summary = ask_local_llm(
            data_to_analyze=raw_string,
            context_description=t("notion.context_search", query=params["query"]),
            avatar_name=avatar_name,
        )

        return smart_summary

    except Exception as e:
        connector.log_debug(f"Errore ricerca: {e}")
        raise e

def create_page(connector: BaseConnector, client: Client, params: dict) -> str:
    required =["parent_page_id", "title", "content"]
    if not all(p in params for p in required):
        raise ValueError(f"Parametri mancanti. Richiesti: {', '.join(required)}")

    connector.log_debug(f"Creazione pagina '{params['title']}' sotto parent {params['parent_page_id']}")

    try:
        new_page = client.pages.create(
            parent={"page_id": params["parent_page_id"]},
            properties={
                "title": {
                    "title":[{"type": "text", "text": {"content": params["title"]}}]
                }
            },
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text":[{"type": "text", "text": {"content": params["content"]}}]
                    },
                }
            ],
        )
        connector.log_debug(f"Pagina creata. ID: {new_page['id']}")

        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        confirmation_data = t("notion.create_confirm", title=params["title"], url=new_page.get("url"))

        smart_confirmation = ask_local_llm(
            data_to_analyze=confirmation_data,
            context_description=t("notion.context_create"),
            avatar_name=avatar_name,
        )

        return smart_confirmation
    except Exception as e:
        connector.log_debug(f"Errore creazione pagina: {e}")
        raise e

def action_wrapper(connector: BaseConnector, action_func, params: dict):
    guardian = Guardian()
    creds_config = guardian.get_credentials("notion_api")
    if not creds_config:
        raise ValueError(t("notion.auth_error"))
    client = authenticate(connector, creds_config)
    return action_func(connector, client, params)

if __name__ == "__main__":
    connector = BaseConnector("Connettore per Notion.")
    connector.register_action("search_notion", lambda params: action_wrapper(connector, search, params))
    connector.register_action("create_notion_page", lambda params: action_wrapper(connector, create_page, params))
    connector.run()