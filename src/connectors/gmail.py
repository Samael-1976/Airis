# src/connectors/gmail.py
# Esecutore Autonomo per Gmail (v2.0 - BaseConnector Refactor)
# LEGGE A0099: Invarianza strutturale garantita.

import sys
import os
from pathlib import Path
import base64
from email.mime.text import MIMEText

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
    print('{"status": "error", "message": "' + t("gmail.lib_error") + '"}')
    sys.exit(1)

SCOPES =[
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

def authenticate(connector: BaseConnector):
    creds = None
    guardian = Guardian()
    creds_config = guardian.get_credentials("google_api")
    if not creds_config:
        raise ValueError(t("gmail.auth_error"))

    token_path = PROJECT_ROOT / creds_config.get("token_path", "config/google_token.json")
    client_secrets_path = PROJECT_ROOT / creds_config.get("client_secrets_path", "config/google_client_secret.json")

    if not client_secrets_path.exists():
        raise FileNotFoundError(t("gmail.secret_error", path=client_secrets_path))

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            connector.log_debug(t("log.gmail_token_expired"))
            creds.refresh(Request())
        else:
            connector.log_debug(t("log.gmail_token_invalid"))
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_path), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)

def list_messages(connector: BaseConnector, service, max_results=5):
    connector.log_debug(t("log.gmail_scan_start", max=max_results))

    search_strategies =[
        {"name": t("gmail.strategy_unread_inbox"), "query": "is:unread in:inbox"},
        {"name": t("gmail.strategy_all_inbox"), "query": "in:inbox"},
        {"name": t("gmail.strategy_unread_all"), "query": "is:unread"},
        {"name": t("gmail.strategy_all"), "query": ""},
    ]

    found_messages =[]
    used_strategy = ""

    for strategy in search_strategies:
        query = strategy["query"]
        name = strategy["name"]
        connector.log_debug(t("log.gmail_strategy_try", name=name, query=query))

        try:
            results = service.users().messages().list(userId="me", q=query, maxResults=max_results, includeSpamTrash=False).execute()
            messages = results.get("items",[])
            if messages:
                found_messages = messages
                used_strategy = name
                break
        except Exception as e:
            connector.log_debug(t("log.gmail_strategy_error", name=name, error=e))

    if not found_messages:
        return t("gmail.no_messages")

    raw_data_for_agent =[]
    connector.log_debug(t("log.gmail_metadata_download", count=len(found_messages)))

    for msg in found_messages:
        try:
            msg_data = service.users().messages().get(userId="me", id=msg["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"]).execute()
            headers = msg_data["payload"]["headers"]

            subject = next((h["value"] for h in headers if h["name"] == "Subject"), t("avatar_server.gmail.no_subject"))
            sender = next((h["value"] for h in headers if h["name"] == "From"), t("avatar_server.gmail.unknown_sender"))
            date = next((h["value"] for h in headers if h["name"] == "Date"), "")

            raw_data_for_agent.append(t("avatar_server.gmail.msg_format", date=date, sender=sender, subject=subject))
        except Exception as e:
            connector.log_debug(t("log.gmail_read_error", id=msg["id"], error=e))

    raw_string = "\n".join(raw_data_for_agent)
    avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")

    connector.log_debug(t("log.gmail_triage_start"))
    smart_summary = ask_local_llm(
        data_to_analyze=raw_string,
        context_description=t("gmail.context_list", strategy=used_strategy),
        avatar_name=avatar_name,
    )

    return smart_summary

def send_message(connector: BaseConnector, service, params):
    required_params =["to", "subject", "body"]
    if not all(p in params for p in required_params):
        raise ValueError(t("avatar_server.gmail.missing_params", params=", ".join(required_params)))

    message = MIMEText(params["body"])
    message["to"] = params["to"]
    message["subject"] = params["subject"]

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {"raw": raw_message}

    sent_message = service.users().messages().send(userId="me", body=body).execute()
    return t("gmail.send_success", id=sent_message.get("id"))

def action_wrapper(connector: BaseConnector, action_func, params: dict):
    service = authenticate(connector)
    if action_func == list_messages:
        return action_func(connector, service, params.get("max_results", 5))
    return action_func(connector, service, params)

if __name__ == "__main__":
    connector = BaseConnector(t("avatar_server.gmail.cmd_desc"))
    connector.register_action("list", lambda params: action_wrapper(connector, list_messages, params))
    connector.register_action("send", lambda params: action_wrapper(connector, send_message, params))
    connector.run()