# src/connectors/microsoft_todo.py
# Esecutore Autonomo per Microsoft To Do (v2.0 - BaseConnector Refactor)
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
    import msal
    import requests
    from src.guardian import Guardian
    from agent_base import ask_local_llm
except ImportError:
    print('{"status": "error", "message": "' + t("microsoft_todo.lib_error") + '"}')
    sys.exit(1)

GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"
SCOPES =["User.Read", "Tasks.ReadWrite"]

def authenticate(connector: BaseConnector):
    guardian = Guardian()
    creds_config = guardian.get_credentials("microsoft_api")
    if not creds_config:
        connector.log_debug("Configurazione 'microsoft_api' mancante.")
        raise ValueError(t("microsoft_excel.auth_error"))

    token_path = PROJECT_ROOT / creds_config.get("token_path", "config/microsoft_token.json")

    cache = msal.SerializableTokenCache()
    if token_path.exists():
        connector.log_debug("Cache token trovata, caricamento...")
        cache.deserialize(token_path.read_text())

    app = msal.PublicClientApplication(
        creds_config["client_id"],
        authority=creds_config["authority"],
        token_cache=cache,
    )

    accounts = app.get_accounts()
    result = None
    if accounts:
        connector.log_debug(f"Account trovato in cache: {accounts[0].get('username')}")
        result = app.acquire_token_silent(SCOPES, account=accounts[0])

    if not result:
        connector.log_debug("Nessun token valido in cache. Avvio Device Flow...")
        flow = app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            raise ValueError("Fallimento nell'ottenere il codice utente.", flow.get("error_description"))

        print(t("microsoft_excel.device_flow_msg", uri=flow["verification_uri"], code=flow["user_code"]))
        sys.stderr.write(f"ATTESA AUTENTICAZIONE UTENTE (Codice: {flow['user_code']})...\n")

        result = app.acquire_token_by_device_flow(flow)

    if "access_token" in result:
        if cache.has_state_changed:
            token_path.write_text(cache.serialize())
            connector.log_debug("Token salvato su disco.")
        return result["access_token"]
    else:
        err_desc = result.get("error_description", "Errore sconosciuto")
        connector.log_debug(f"Errore autenticazione: {err_desc}")
        raise Exception(err_desc)

def list_tasklists(connector: BaseConnector, access_token, params: dict):
    max_results = params.get("max_results", 10)
    connector.log_debug(f"Richiesta liste attività (Max: {max_results})...")

    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        response = requests.get(
            f"{GRAPH_API_ENDPOINT}/me/todo/lists",
            headers=headers,
            params={"$top": max_results},
        )

        if response.status_code != 200:
            connector.log_debug(f"Errore API: {response.text}")

        response.raise_for_status()
        items = response.json().get("value",[])
        connector.log_debug(f"Liste trovate: {len(items)}")

        if not items:
            return t("microsoft_todo.no_lists")

        raw_data_list =[]
        for item in items:
            raw_data_list.append(f"LISTA: {item['displayName']} | ID: {item['id']}")

        raw_string = "\n".join(raw_data_list)
        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        connector.log_debug("Inoltro liste all'agente locale per il Triage...")

        smart_summary = ask_local_llm(
            data_to_analyze=raw_string,
            context_description=t("microsoft_todo.context_lists"),
            avatar_name=avatar_name,
        )

        return smart_summary

    except Exception as e:
        connector.log_debug(f"Eccezione List Tasklists: {e}")
        raise e

def list_tasks(connector: BaseConnector, access_token, params: dict):
    if "tasklist_id" not in params:
        raise ValueError("Parametro 'tasklist_id' mancante per elencare le attività.")

    connector.log_debug(f"Richiesta task per lista ID: {params['tasklist_id']}")
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"{GRAPH_API_ENDPOINT}/me/todo/lists/{params['tasklist_id']}/tasks"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        items = response.json().get("value",[])
        connector.log_debug(f"Task trovati: {len(items)}")

        if not items:
            return t("microsoft_todo.empty_list")

        raw_data_list =[]
        for item in items:
            status = "COMPLETATA" if item.get("status") == "completed" else "DA FARE"
            raw_data_list.append(f"TASK: {item['title']} | STATO: {status} | ID: {item['id']}")

        raw_string = "\n".join(raw_data_list)
        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        connector.log_debug("Inoltro task all'agente locale per il Triage...")

        smart_summary = ask_local_llm(
            data_to_analyze=raw_string,
            context_description=t("microsoft_todo.context_tasks", id=params["tasklist_id"]),
            avatar_name=avatar_name,
        )

        return smart_summary

    except Exception as e:
        connector.log_debug(f"Eccezione List Tasks: {e}")
        raise e

def create_task(connector: BaseConnector, access_token, params: dict):
    required = ["tasklist_id", "title"]
    if not all(p in params for p in required):
        raise ValueError(f"Parametri mancanti. Richiesti: {', '.join(required)}")

    connector.log_debug(f"Creazione task '{params['title']}' in lista {params['tasklist_id']}")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    url = f"{GRAPH_API_ENDPOINT}/me/todo/lists/{params['tasklist_id']}/tasks"

    task_body = {"title": params["title"]}

    try:
        response = requests.post(url, headers=headers, json=task_body)

        if response.status_code != 201:
            connector.log_debug(f"Errore API: {response.text}")

        response.raise_for_status()
        created_task = response.json()

        connector.log_debug(f"Task creato. ID: {created_task.get('id')}")

        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        confirmation_data = t("microsoft_todo.create_confirm", title=params["title"])

        smart_confirmation = ask_local_llm(
            data_to_analyze=confirmation_data,
            context_description=t("microsoft_todo.context_create"),
            avatar_name=avatar_name,
        )

        return smart_confirmation

    except Exception as e:
        connector.log_debug(f"Eccezione Create Task: {e}")
        raise e

def action_wrapper(connector: BaseConnector, action_func, params: dict):
    access_token = authenticate(connector)
    return action_func(connector, access_token, params)

if __name__ == "__main__":
    connector = BaseConnector("Connettore per Microsoft To Do.")
    connector.register_action("list_lists", lambda params: action_wrapper(connector, list_tasklists, params))
    connector.register_action("list_tasks", lambda params: action_wrapper(connector, list_tasks, params))
    connector.register_action("create", lambda params: action_wrapper(connector, create_task, params))
    connector.run()