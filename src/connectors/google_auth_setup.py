# src/connectors/google_auth_setup.py
# Utility per generare il token Google OAuth2 (v2.0 - BaseConnector Refactor)
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
    from google_auth_oauthlib.flow import InstalledAppFlow
    from src.guardian import Guardian
except ImportError:
    print('{"status": "error", "message": "' + t("google_auth.lib_error") + '"}')
    sys.exit(1)

SCOPES =[
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/photoslibrary.readonly",
    "https://www.googleapis.com/auth/contacts.readonly",
]

def setup_auth(connector: BaseConnector, params: dict):
    connector.log_debug(t("log.google_auth_start"))

    guardian = Guardian()
    creds_config = guardian.get_credentials("google_api")

    if not creds_config:
        connector.log_debug(t("log.google_auth_no_config"))
        token_path = PROJECT_ROOT / "config" / "google_token.json"
        client_secrets_path = PROJECT_ROOT / "config" / "google_client_secret.json"
    else:
        token_path = PROJECT_ROOT / creds_config.get("token_path", "config/google_token.json")
        client_secrets_path = PROJECT_ROOT / creds_config.get("client_secrets_path", "config/google_client_secret.json")

    connector.log_debug(t("log.google_auth_path_secret", path=client_secrets_path))
    connector.log_debug(t("log.google_auth_path_token", path=token_path))

    if not client_secrets_path.exists():
        raise FileNotFoundError(t("google_auth.secret_not_found", path=str(client_secrets_path)))

    try:
        connector.log_debug(t("log.google_auth_flow"))
        flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_path), SCOPES)

        connector.log_debug(t("log.google_auth_browser"))
        creds = flow.run_local_server(port=0)

        connector.log_debug(t("log.google_auth_consent"))

        token_path.parent.mkdir(parents=True, exist_ok=True)

        with open(token_path, "w") as token:
            token.write(creds.to_json())

        connector.log_debug(t("log.google_auth_saved", path=token_path))
        return t("google_auth.success", filename=token_path.name)

    except Exception as e:
        connector.log_debug(t("log.google_auth_error", error=e))
        raise e

if __name__ == "__main__":
    connector = BaseConnector(t("google_auth.cmd_desc"))
    connector.register_action("setup", lambda params: setup_auth(connector, params))
    connector.run()