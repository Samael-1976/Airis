# src/connectors/slack.py
# Esecutore Autonomo per Slack (v2.0 - BaseConnector Refactor)
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
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
    from src.guardian import Guardian
    from agent_base import ask_local_llm
except ImportError:
    print('{"status": "error", "message": "' + t("slack.lib_error") + '"}')
    sys.exit(1)

def send_message(connector: BaseConnector, creds: dict, params: dict) -> str:
    bot_token = creds.get("bot_token")
    if not bot_token or "IL_TUO" in bot_token:
        connector.log_debug("Bot Token mancante o placeholder.")
        raise ValueError(t("slack.auth_error"))

    content = params.get("content")
    if not content:
        raise ValueError("Parametro 'content' mancante per inviare il messaggio.")

    channel_id = params.get("channel_id") or creds.get("channel_id")
    if not channel_id:
        raise ValueError("Nessun 'channel_id' specificato.")

    connector.log_debug(f"Inizializzazione client per invio su canale: {channel_id}")

    try:
        client = WebClient(token=bot_token)
        connector.log_debug("Invio messaggio...")
        response = client.chat_postMessage(channel=channel_id, text=content)

        if response["ok"]:
            connector.log_debug(f"Messaggio inviato. TS: {response['ts']}")

            avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
            confirmation_data = t("slack.send_confirm", id=channel_id, content=content)

            smart_confirmation = ask_local_llm(
                data_to_analyze=confirmation_data,
                context_description=t("slack.context_send"),
                avatar_name=avatar_name,
            )

            return smart_confirmation
        else:
            error_msg = response["error"]
            connector.log_debug(f"Errore API (response not ok): {error_msg}")
            raise SlackApiError(f"Errore dall'API di Slack: {error_msg}", response)

    except SlackApiError as e:
        connector.log_debug(f"Eccezione SlackApiError: {e.response['error']}")
        raise Exception(t("slack.api_error", error=e.response["error"]))
    except Exception as e:
        connector.log_debug(f"Eccezione generica: {e}")
        raise e

def list_messages(connector: BaseConnector, creds: dict, params: dict) -> str:
    bot_token = creds.get("bot_token")
    if not bot_token or "IL_TUO" in bot_token:
        raise ValueError(t("slack.auth_error"))

    channel_id = params.get("channel_id") or creds.get("channel_id")
    if not channel_id:
        raise ValueError("Nessun 'channel_id' specificato.")

    limit = params.get("limit", 10)
    connector.log_debug(f"Richiesta ultimi {limit} messaggi dal canale: {channel_id}")

    try:
        client = WebClient(token=bot_token)
        response = client.conversations_history(channel=channel_id, limit=limit)

        if not response["ok"]:
            raise SlackApiError("Errore recupero cronologia", response)

        messages = response.get("messages",[])
        connector.log_debug(f"Messaggi trovati: {len(messages)}")

        if not messages:
            return t("slack.no_messages")

        raw_data_list =[]
        for msg in messages:
            user = msg.get("user", "Sistema/Bot")
            text = msg.get("text", "")
            ts = msg.get("ts", "")
            dt = datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M:%S")
            raw_data_list.append(f"UTENTE: {user} | DATA: {dt} | MESSAGGIO: {text}")

        raw_string = "\n".join(raw_data_list)
        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        connector.log_debug("Inoltro messaggi all'agente locale per il Triage...")

        smart_summary = ask_local_llm(
            data_to_analyze=raw_string,
            context_description=t("slack.context_list", id=channel_id),
            avatar_name=avatar_name,
        )

        return smart_summary

    except SlackApiError as e:
        connector.log_debug(f"Errore API Slack: {e.response['error']}")
        raise Exception(t("slack.api_error", error=e.response["error"]))
    except Exception as e:
        connector.log_debug(f"Errore generico: {e}")
        raise e

def action_wrapper(connector: BaseConnector, action_func, params: dict):
    guardian = Guardian()
    creds_config = guardian.get_credentials("slack_api")
    if not creds_config:
        raise ValueError("Configurazione 'slack_api' non trovata in credentials.yaml.")
    return action_func(connector, creds_config, params)

if __name__ == "__main__":
    connector = BaseConnector("Connettore per Slack.")
    connector.register_action("send_message", lambda params: action_wrapper(connector, send_message, params))
    connector.register_action("list_messages", lambda params: action_wrapper(connector, list_messages, params))
    connector.run()