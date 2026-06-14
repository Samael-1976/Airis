# src/connectors/twilio.py
# Esecutore Autonomo per Twilio (SMS) (v2.0 - BaseConnector Refactor)
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
    from twilio.rest import Client
    from src.guardian import Guardian
    from agent_base import ask_local_llm
except ImportError:
    print('{"status": "error", "message": "' + t("twilio.lib_error") + '"}')
    sys.exit(1)

def send_sms(connector: BaseConnector, params: dict, creds: dict):
    required = ["to_number", "body"]
    if not all(p in params for p in required):
        raise ValueError(f"Parametri mancanti. Richiesti: {', '.join(required)}")

    account_sid = creds.get("account_sid")
    auth_token = creds.get("auth_token")
    from_number = creds.get("from_number")

    if not all([account_sid, auth_token, from_number]) or "IL_TUO" in account_sid:
        connector.log_debug("Credenziali mancanti o placeholder.")
        raise ValueError(t("twilio.auth_error"))

    connector.log_debug(f"Inizializzazione client Twilio (SID: {account_sid[:4]}...)")

    try:
        client = Client(account_sid, auth_token)
        connector.log_debug(f"Invio SMS a {params['to_number']} da {from_number}...")

        message = client.messages.create(
            to=params["to_number"], from_=from_number, body=params["body"]
        )

        connector.log_debug(f"SMS inviato. SID: {message.sid}")

        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        confirmation_data = t(
            "twilio.send_confirm",
            to=params["to_number"],
            body=params["body"],
            sid=message.sid,
        )

        smart_confirmation = ask_local_llm(
            data_to_analyze=confirmation_data,
            context_description=t("twilio.context_send"),
            avatar_name=avatar_name,
        )

        return smart_confirmation

    except Exception as e:
        connector.log_debug(f"Errore invio SMS: {e}")
        raise e

def action_wrapper(connector: BaseConnector, action_func, params: dict):
    guardian = Guardian()
    creds_config = guardian.get_credentials("twilio_api")
    if not creds_config:
        raise ValueError("Configurazione 'twilio_api' non trovata in credentials.yaml.")
    return action_func(connector, params, creds_config)

if __name__ == "__main__":
    connector = BaseConnector("Connettore per Twilio (SMS).")
    connector.register_action("send_sms", lambda params: action_wrapper(connector, send_sms, params))
    connector.run()