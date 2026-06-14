# src/connectors/google_sheets.py
# Esecutore Autonomo per Google Sheets (v2.0 - BaseConnector Refactor)
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
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from src.guardian import Guardian
    from agent_base import ask_local_llm
except ImportError:
    print('{"status": "error", "message": "' + t("google_sheets.lib_error") + '"}')
    sys.exit(1)

SCOPES =["https://www.googleapis.com/auth/spreadsheets"]

def authenticate(connector: BaseConnector):
    creds = None
    guardian = Guardian()
    creds_config = guardian.get_credentials("google_api")
    if not creds_config:
        connector.log_debug("Configurazione 'google_api' mancante.")
        raise ValueError(t("google_sheets.auth_error"))

    token_path = PROJECT_ROOT / creds_config.get("token_path", "config/google_token.json")
    client_secrets_path = PROJECT_ROOT / creds_config.get("client_secrets_path", "config/google_client_secret.json")

    if not client_secrets_path.exists():
        connector.log_debug(f"Client secrets non trovato in: {client_secrets_path}")
        raise FileNotFoundError(t("google_sheets.secret_error", name=client_secrets_path.name))

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

    return build("sheets", "v4", credentials=creds)

def read_sheet(connector: BaseConnector, service, params: dict):
    required_params = ["spreadsheet_id", "range_name"]
    if not all(p in params for p in required_params):
        raise ValueError(f"Parametri mancanti per leggere il foglio. Richiesti: {', '.join(required_params)}")

    connector.log_debug(f"Lettura Sheet ID: {params['spreadsheet_id']}, Range: {params['range_name']}")

    try:
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=params["spreadsheet_id"], range=params["range_name"]).execute()
        values = result.get("values",[])
        connector.log_debug(f"Righe recuperate: {len(values)}")

        if not values:
            return t("google_sheets.empty_range", range=params["range_name"])

        raw_table_string = "\n".join([" | ".join(map(str, row)) for row in values])
        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        connector.log_debug("Inoltro dati tabellari all'agente locale per l'analisi...")

        smart_summary = ask_local_llm(
            data_to_analyze=raw_table_string,
            context_description=t("google_sheets.context_read", id=params["spreadsheet_id"], range=params["range_name"]),
            avatar_name=avatar_name,
        )

        return smart_summary

    except Exception as e:
        connector.log_debug(f"Errore API Read: {e}")
        raise e

def write_sheet(connector: BaseConnector, service, params: dict):
    required_params =["spreadsheet_id", "range_name", "values"]
    if not all(p in params for p in required_params):
        raise ValueError(f"Parametri mancanti per scrivere sul foglio. Richiesti: {', '.join(required_params)}")

    connector.log_debug(f"Scrittura su Sheet ID: {params['spreadsheet_id']}, Range: {params['range_name']}")

    try:
        body = {"values": params["values"]}
        result = service.spreadsheets().values().update(
            spreadsheetId=params["spreadsheet_id"],
            range=params["range_name"],
            valueInputOption="USER_ENTERED",
            body=body,
        ).execute()
        updated_cells = result.get("updatedCells")
        connector.log_debug(f"Celle aggiornate: {updated_cells}")

        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        confirmation_data = t("google_sheets.write_confirm", id=params["spreadsheet_id"], count=updated_cells, range=params["range_name"])

        smart_confirmation = ask_local_llm(
            data_to_analyze=confirmation_data,
            context_description=t("google_sheets.context_write"),
            avatar_name=avatar_name,
        )

        return smart_confirmation

    except Exception as e:
        connector.log_debug(f"Errore API Write: {e}")
        raise e

def action_wrapper(connector: BaseConnector, action_func, params: dict):
    service = authenticate(connector)
    return action_func(connector, service, params)

if __name__ == "__main__":
    connector = BaseConnector("Connettore per Google Sheets.")
    connector.register_action("read", lambda params: action_wrapper(connector, read_sheet, params))
    connector.register_action("write", lambda params: action_wrapper(connector, write_sheet, params))
    connector.run()