# src/connectors/google_tasks.py
# Esecutore Autonomo per Google Tasks (v2.0 - BaseConnector Refactor)
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
    print('{"status": "error", "message": "' + t("google_tasks.lib_error") + '"}')
    sys.exit(1)

SCOPES =["https://www.googleapis.com/auth/tasks"]

def authenticate(connector: BaseConnector):
    creds = None
    guardian = Guardian()
    creds_config = guardian.get_credentials("google_api")
    if not creds_config:
        connector.log_debug("Configurazione 'google_api' mancante.")
        raise ValueError(t("google_tasks.auth_error"))

    token_path = PROJECT_ROOT / creds_config.get("token_path", "config/google_token.json")
    client_secrets_path = PROJECT_ROOT / creds_config.get("client_secrets_path", "config/google_client_secret.json")

    if not client_secrets_path.exists():
        connector.log_debug(f"Client secrets non trovato in: {client_secrets_path}")
        raise FileNotFoundError(t("google_tasks.secret_error", name=client_secrets_path.name))

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

    return build("tasks", "v1", credentials=creds)

def list_tasklists(connector: BaseConnector, service, params: dict):
    connector.log_debug("Richiesta liste attività...")
    try:
        results = service.tasklists().list(maxResults=10).execute()
        items = results.get("items",[])
        connector.log_debug(f"Liste trovate: {len(items)}")

        if not items:
            return t("google_tasks.no_lists")

        raw_data_list =[]
        for item in items:
            raw_data_list.append(f"LISTA: {item['title']} | ID: {item['id']}")

        raw_string = "\n".join(raw_data_list)
        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        connector.log_debug("Inoltro liste all'agente locale per il Triage...")

        smart_summary = ask_local_llm(
            data_to_analyze=raw_string,
            context_description=t("google_tasks.context_lists"),
            avatar_name=avatar_name,
        )

        return smart_summary
    except Exception as e:
        connector.log_debug(f"Errore API List Tasklists: {e}")
        raise e

def list_tasks(connector: BaseConnector, service, params: dict):
    if "tasklist_id" not in params:
        raise ValueError("Parametro 'tasklist_id' mancante per elencare le attività.")

    connector.log_debug(f"Richiesta task per lista ID: {params['tasklist_id']}")

    try:
        results = service.tasks().list(tasklist=params["tasklist_id"]).execute()
        items = results.get("items",[])
        connector.log_debug(f"Task trovati: {len(items)}")

        if not items:
            return t("google_tasks.empty_list")

        raw_data_list =[]
        for item in items:
            status = "COMPLETATA" if item.get("status") == "completed" else "DA FARE"
            due = item.get("due", "Nessuna scadenza")
            raw_data_list.append(f"TASK: {item['title']} | STATO: {status} | SCADENZA: {due} | NOTE: {item.get('notes', 'N/A')}")

        raw_string = "\n".join(raw_data_list)
        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        connector.log_debug("Inoltro task all'agente locale per il Triage...")

        smart_summary = ask_local_llm(
            data_to_analyze=raw_string,
            context_description=t("google_tasks.context_tasks", id=params["tasklist_id"]),
            avatar_name=avatar_name,
        )

        return smart_summary
    except Exception as e:
        connector.log_debug(f"Errore API List Tasks: {e}")
        raise e

def create_task(connector: BaseConnector, service, params: dict):
    required_params = ["tasklist_id", "title"]
    if not all(p in params for p in required_params):
        raise ValueError(f"Parametri mancanti per creare l'attività. Richiesti: {', '.join(required_params)}")

    connector.log_debug(f"Creazione task '{params['title']}' in lista {params['tasklist_id']}")

    task = {
        "title": params["title"],
        "notes": params.get("notes", ""),
    }
    if "due" in params:
        task["due"] = params["due"]

    try:
        created_task = service.tasks().insert(tasklist=params["tasklist_id"], body=task).execute()
        connector.log_debug(f"Task creato. ID: {created_task.get('id')}")

        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        confirmation_data = t("google_tasks.create_confirm", title=params["title"], notes=params.get("notes", "Nessuna"))

        smart_confirmation = ask_local_llm(
            data_to_analyze=confirmation_data,
            context_description=t("google_tasks.context_create"),
            avatar_name=avatar_name,
        )

        return smart_confirmation
    except Exception as e:
        connector.log_debug(f"Errore API Create Task: {e}")
        raise e

def action_wrapper(connector: BaseConnector, action_func, params: dict):
    service = authenticate(connector)
    return action_func(connector, service, params)

if __name__ == "__main__":
    connector = BaseConnector("Connettore per Google Tasks.")
    connector.register_action("list_lists", lambda params: action_wrapper(connector, list_tasklists, params))
    connector.register_action("list_tasks", lambda params: action_wrapper(connector, list_tasks, params))
    connector.register_action("create", lambda params: action_wrapper(connector, create_task, params))
    connector.run()