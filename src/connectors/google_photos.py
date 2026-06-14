# src/connectors/google_photos.py
# Esecutore Autonomo per Google Photos (v2.0 - BaseConnector Refactor)
# LEGGE A0099: Invarianza strutturale garantita.

import sys
import os
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.translator import t
from src.connectors.base_connector import BaseConnector

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from src.guardian import Guardian
    from agent_base import ask_local_llm
except ImportError:
    print('{"status": "error", "message": "' + t("google_photos.lib_error") + '"}')
    sys.exit(1)

SCOPES =["https://www.googleapis.com/auth/photoslibrary.readonly"]

def authenticate(connector: BaseConnector):
    creds = None
    guardian = Guardian()
    creds_config = guardian.get_credentials("google_api")
    if not creds_config:
        connector.log_debug("Configurazione 'google_api' mancante.")
        raise ValueError("Configurazione 'google_api' non trovata in credentials.yaml.")

    token_path = PROJECT_ROOT / creds_config.get("token_path", "config/google_token.json")
    client_secrets_path = PROJECT_ROOT / creds_config.get("client_secrets_path", "config/google_client_secret.json")

    if not client_secrets_path.exists():
        connector.log_debug(f"Client secrets non trovato: {client_secrets_path}")
        raise FileNotFoundError(t("google_photos.auth_error"))

    if token_path.exists():
        connector.log_debug("Token trovato, caricamento...")
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            connector.log_debug("Token scaduto, refresh in corso...")
            creds.refresh(Request())
        else:
            connector.log_debug("Token non valido o assente, avvio flusso di login...")
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_path), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as token:
            token.write(creds.to_json())
            connector.log_debug("Nuovo token salvato.")

    return build("photoslibrary", "v1", credentials=creds, static_discovery=False)

def list_albums(connector: BaseConnector, service, params: dict):
    page_size = params.get("max_results", 20)
    connector.log_debug(f"Richiesta lista album (Max: {page_size})...")

    try:
        results = service.albums().list(pageSize=page_size).execute()
        items = results.get("albums",[])
        connector.log_debug(f"Album trovati: {len(items)}")

        if not items:
            return t("google_photos.no_albums")

        raw_data_list =[]
        for item in items:
            raw_data_list.append(f"ALBUM: {item['title']} | MEDIA: {item.get('mediaItemsCount', 0)} | ID: {item['id']}")

        raw_string = "\n".join(raw_data_list)
        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        connector.log_debug("Inoltro album all'agente locale per il Triage...")

        smart_summary = ask_local_llm(
            data_to_analyze=raw_string,
            context_description=t("google_photos.context_albums"),
            avatar_name=avatar_name,
        )

        return smart_summary

    except Exception as e:
        connector.log_debug(f"Errore API List Albums: {e}")
        raise e

def search_media(connector: BaseConnector, service, params: dict):
    if "query" not in params:
        raise ValueError("Parametro 'query' mancante per la ricerca.")

    page_size = params.get("max_results", 10)
    connector.log_debug(f"Ricerca media: '{params['query']}' (Max: {page_size})")

    try:
        body = {"pageSize": page_size}
        if "favoriti" in params["query"].lower() or "favorites" in params["query"].lower():
            body["filters"] = {"featureFilter": {"includedFeatures": ["FAVORITES"]}}

        results = service.mediaItems().search(body=body).execute()
        items = results.get("mediaItems",[])
        connector.log_debug(f"Media trovati: {len(items)}")

        if not items:
            return t("google_photos.no_media", query=params["query"])

        raw_data_list =[]
        for item in items:
            creation_time = datetime.fromisoformat(item["mediaMetadata"]["creationTime"].replace("Z", "+00:00")).strftime("%d/%m/%Y")
            raw_data_list.append(f"FILE: {item['filename']} | CREATO: {creation_time} | TIPO: {item.get('mimeType')} | LINK: {item['productUrl']}")

        raw_string = "\n".join(raw_data_list)
        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        connector.log_debug("Inoltro media all'agente locale per il Triage...")

        smart_summary = ask_local_llm(
            data_to_analyze=raw_string,
            context_description=t("google_photos.context_search", query=params["query"]),
            avatar_name=avatar_name,
        )

        return smart_summary

    except Exception as e:
        connector.log_debug(f"Errore API Search Media: {e}")
        raise e

def action_wrapper(connector: BaseConnector, action_func, params: dict):
    service = authenticate(connector)
    return action_func(connector, service, params)

if __name__ == "__main__":
    connector = BaseConnector("Connettore per Google Photos.")
    connector.register_action("list_albums", lambda params: action_wrapper(connector, list_albums, params))
    connector.register_action("search", lambda params: action_wrapper(connector, search_media, params))
    connector.run()