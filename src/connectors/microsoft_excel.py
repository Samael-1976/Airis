# src/connectors/microsoft_excel.py
# Esecutore Autonomo per Microsoft Excel (v2.0 - BaseConnector Refactor)
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
    print('{"status": "error", "message": "' + t("microsoft_excel.lib_error") + '"}')
    sys.exit(1)

GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"
SCOPES =["User.Read", "Files.ReadWrite.All", "Sites.ReadWrite.All"]

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

def read_sheet(connector: BaseConnector, access_token, params: dict):
    required = ["file_id", "worksheet_name", "range_address"]
    if not all(p in params for p in required):
        raise ValueError(f"Parametri mancanti per leggere il foglio. Richiesti: {', '.join(required)}")

    connector.log_debug(f"Lettura File ID: {params['file_id']}, Sheet: {params['worksheet_name']}, Range: {params['range_address']}")

    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"{GRAPH_API_ENDPOINT}/me/drive/items/{params['file_id']}/workbook/worksheets/{params['worksheet_name']}/range(address='{params['range_address']}')"

    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            connector.log_debug(f"Errore API: {response.text}")

        response.raise_for_status()
        data = response.json()
        values = data.get("values",[])
        connector.log_debug(f"Valori recuperati: {len(values)} righe.")

        if not values:
            return t("microsoft_excel.empty_range", range=params["range_address"])

        raw_table_string = "\n".join([" | ".join(map(str, row)) for row in values])
        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        connector.log_debug("Inoltro dati tabellari all'agente locale per l'analisi...")

        smart_summary = ask_local_llm(
            data_to_analyze=raw_table_string,
            context_description=t("microsoft_excel.context_read", id=params["file_id"], range=params["range_address"]),
            avatar_name=avatar_name,
        )

        return smart_summary

    except Exception as e:
        connector.log_debug(f"Eccezione Read: {e}")
        raise e

def write_sheet(connector: BaseConnector, access_token, params: dict):
    required = ["file_id", "worksheet_name", "range_address", "values"]
    if not all(p in params for p in required):
        raise ValueError(f"Parametri mancanti per scrivere sul foglio. Richiesti: {', '.join(required)}")

    connector.log_debug(f"Scrittura su File ID: {params['file_id']}, Range: {params['range_address']}")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    url = f"{GRAPH_API_ENDPOINT}/me/drive/items/{params['file_id']}/workbook/worksheets/{params['worksheet_name']}/range(address='{params['range_address']}')"

    body = {"values": params["values"]}

    try:
        response = requests.patch(url, headers=headers, json=body)
        if response.status_code != 200:
            connector.log_debug(f"Errore API: {response.text}")

        response.raise_for_status()
        result = response.json()

        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        confirmation_data = t(
            "microsoft_excel.write_confirm",
            id=params["file_id"],
            count=result.get("cellCount"),
            range=params["range_address"],
        )

        smart_confirmation = ask_local_llm(
            data_to_analyze=confirmation_data,
            context_description=t("microsoft_excel.context_write"),
            avatar_name=avatar_name,
        )

        return smart_confirmation

    except Exception as e:
        connector.log_debug(f"Eccezione Write: {e}")
        raise e

def action_wrapper(connector: BaseConnector, action_func, params: dict):
    access_token = authenticate(connector)
    return action_func(connector, access_token, params)

if __name__ == "__main__":
    connector = BaseConnector("Connettore per Microsoft Excel.")
    connector.register_action("read", lambda params: action_wrapper(connector, read_sheet, params))
    connector.register_action("write", lambda params: action_wrapper(connector, write_sheet, params))
    connector.run()