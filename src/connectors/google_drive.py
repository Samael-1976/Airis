# src/connectors/google_drive.py
# Esecutore Autonomo per Google Drive (v2.0 - BaseConnector Refactor)
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
    print('{"status": "error", "message": "' + t("google_drive.lib_error") + '"}')
    sys.exit(1)

SCOPES =["https://www.googleapis.com/auth/drive.readonly"]

def authenticate(connector: BaseConnector):
    creds = None
    guardian = Guardian()
    creds_config = guardian.get_credentials("google_api")
    if not creds_config:
        connector.log_debug("Configurazione 'google_api' mancante.")
        raise ValueError(t("google_drive.auth_error"))

    token_path = PROJECT_ROOT / creds_config.get("token_path", "config/google_token.json")
    client_secrets_path = PROJECT_ROOT / creds_config.get("client_secrets_path", "config/google_client_secret.json")

    if not client_secrets_path.exists():
        connector.log_debug(f"Client secrets non trovato in: {client_secrets_path}")
        raise FileNotFoundError(t("google_calendar.secret_error", name=client_secrets_path.name))

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

    return build("drive", "v3", credentials=creds)

def list_files(connector: BaseConnector, service, params: dict):
    max_results = params.get("max_results", 10)
    connector.log_debug(f"Richiesta lista file (Max: {max_results})...")
    try:
        results = service.files().list(
            pageSize=max_results,
            fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
        ).execute()
        items = results.get("files",[])
        connector.log_debug(f"File trovati: {len(items)}")

        if not items:
            return t("google_drive.no_files")

        raw_data_list =[]
        for item in items:
            modified_time = datetime.fromisoformat(item["modifiedTime"].replace("Z", "+00:00")).strftime("%d/%m/%Y %H:%M")
            file_type = item.get("mimeType", "Sconosciuto").split("/")[-1]
            raw_data_list.append(f"FILE: {item['name']} | TIPO: {file_type} | MODIFICATO: {modified_time}")

        raw_string = "\n".join(raw_data_list)
        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        connector.log_debug("Inoltro file all'agente locale per il Triage...")

        smart_summary = ask_local_llm(
            data_to_analyze=raw_string,
            context_description=t("google_drive.context_list"),
            avatar_name=avatar_name,
        )

        return smart_summary

    except Exception as e:
        connector.log_debug(f"Errore API List: {e}")
        raise e

def action_wrapper(connector: BaseConnector, action_func, params: dict):
    service = authenticate(connector)
    return action_func(connector, service, params)

if __name__ == "__main__":
    connector = BaseConnector("Connettore per Google Drive.")
    connector.register_action("list", lambda params: action_wrapper(connector, list_files, params))
    connector.run()