# src/connectors/trello.py
# Esecutore Autonomo per Trello (v2.0 - BaseConnector Refactor)
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
    from trello import TrelloClient
    from src.guardian import Guardian
    from agent_base import ask_local_llm
except ImportError:
    print('{"status": "error", "message": "' + t("connectors.trello.lib_error") + '"}')
    sys.exit(1)

def authenticate(connector: BaseConnector, creds: dict) -> TrelloClient:
    api_key = creds.get("api_key")
    api_secret = creds.get("api_secret")
    token = creds.get("token")

    if not all([api_key, api_secret, token]) or "IL_TUO" in api_key:
        connector.log_debug("Credenziali mancanti o placeholder.")
        raise ValueError(t("connectors.trello.auth_error"))

    connector.log_debug(f"Inizializzazione client Trello (Key: {api_key[:4]}...)")

    try:
        client = TrelloClient(api_key=api_key, api_secret=api_secret, token=token)
        return client
    except Exception as e:
        connector.log_debug(f"Errore inizializzazione client: {e}")
        raise e

def _find_board_by_name(connector: BaseConnector, client: TrelloClient, board_name: str):
    connector.log_debug(f"Ricerca bacheca: '{board_name}'")
    boards = client.list_boards()
    for board in boards:
        if board.name.lower() == board_name.lower():
            connector.log_debug(f"Bacheca trovata: {board.name} (ID: {board.id})")
            return board

    connector.log_debug(f"Bacheca '{board_name}' non trovata.")
    raise ValueError(t("connectors.trello.board_not_found", name=board_name))

def _find_list_by_name(connector: BaseConnector, board, list_name: str):
    connector.log_debug(f"Ricerca lista '{list_name}' nella bacheca '{board.name}'")
    lists = board.list_lists()
    for trello_list in lists:
        if trello_list.name.lower() == list_name.lower():
            connector.log_debug(f"Lista trovata: {trello_list.name} (ID: {trello_list.id})")
            return trello_list

    connector.log_debug(f"Lista '{list_name}' non trovata.")
    raise ValueError(t("connectors.trello.list_not_found", name=list_name))

def list_boards(connector: BaseConnector, client: TrelloClient, params: dict) -> str:
    connector.log_debug("Richiesta elenco bacheche...")
    try:
        boards = client.list_boards()
        connector.log_debug(f"Trovate {len(boards)} bacheche.")

        if not boards:
            return t("connectors.trello.no_boards")

        raw_data_list =[]
        for board in boards:
            raw_data_list.append(f"BACHECA: {board.name} | ID: {board.id} | CHIUSA: {board.closed}")

        raw_string = "\n".join(raw_data_list)
        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        connector.log_debug("Inoltro bacheche all'agente locale per il Triage...")

        smart_summary = ask_local_llm(
            data_to_analyze=raw_string,
            context_description=t("connectors.trello.context_list"),
            avatar_name=avatar_name,
        )

        return smart_summary
    except Exception as e:
        connector.log_debug(f"Errore listing bacheche: {e}")
        raise e

def create_card(connector: BaseConnector, client: TrelloClient, params: dict) -> str:
    required = ["board_name", "list_name", "name"]
    if not all(p in params for p in required):
        raise ValueError(f"Parametri mancanti. Richiesti: {', '.join(required)}")

    try:
        board = _find_board_by_name(connector, client, params["board_name"])
        trello_list = _find_list_by_name(connector, board, params["list_name"])

        connector.log_debug(f"Creazione card '{params['name']}'...")
        new_card = trello_list.add_card(name=params["name"], desc=params.get("desc", None))
        connector.log_debug(f"Card creata. ID: {new_card.id}")

        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        confirmation_data = t(
            "connectors.trello.create_confirm",
            name=params["name"],
            list=trello_list.name,
            board=board.name,
        )

        smart_confirmation = ask_local_llm(
            data_to_analyze=confirmation_data,
            context_description=t("connectors.trello.context_create"),
            avatar_name=avatar_name,
        )

        return smart_confirmation
    except Exception as e:
        connector.log_debug(f"Errore creazione card: {e}")
        raise e

def action_wrapper(connector: BaseConnector, action_func, params: dict):
    guardian = Guardian()
    creds_config = guardian.get_credentials("trello_api")
    if not creds_config:
        raise ValueError(t("avatar_server.heart.roster_error", error="trello_api"))
    client = authenticate(connector, creds_config)
    return action_func(connector, client, params)

if __name__ == "__main__":
    connector = BaseConnector("Connettore per Trello.")
    connector.register_action("list_boards", lambda params: action_wrapper(connector, list_boards, params))
    connector.register_action("create_card", lambda params: action_wrapper(connector, create_card, params))
    connector.run()