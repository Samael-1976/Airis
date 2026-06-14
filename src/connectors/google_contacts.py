# src/connectors/google_contacts.py
# Esecutore Autonomo per Google Contacts (v2.0 - BaseConnector Refactor)
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
    print('{"status": "error", "message": "' + t("avatar_server.google_contacts.lib_error") + '"}')
    sys.exit(1)

SCOPES =["https://www.googleapis.com/auth/contacts.readonly"]

def authenticate(connector: BaseConnector):
    creds = None
    guardian = Guardian()
    creds_config = guardian.get_credentials("google_api")
    if not creds_config:
        connector.log_debug(t("log.gcontacts_config_missing"))
        raise ValueError(t("google_contacts.auth_error"))

    token_path = PROJECT_ROOT / creds_config.get("token_path", "config/google_token.json")
    client_secrets_path = PROJECT_ROOT / creds_config.get("client_secrets_path", "config/google_client_secret.json")

    if not client_secrets_path.exists():
        connector.log_debug(t("log.gcontacts_secret_not_found", path=client_secrets_path))
        raise FileNotFoundError(t("avatar_server.google_calendar.secret_error", name=client_secrets_path.name))

    if token_path.exists():
        connector.log_debug(t("log.gcontacts_token_found"))
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            connector.log_debug(t("log.gcontacts_token_expired"))
            creds.refresh(Request())
        else:
            connector.log_debug(t("log.gcontacts_token_invalid"))
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_path), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as token:
            token.write(creds.to_json())
            connector.log_debug(t("log.gcontacts_token_saved"))

    return build("people", "v1", credentials=creds, static_discovery=False)

def search_contacts(connector: BaseConnector, service, params: dict):
    if "query" not in params:
        raise ValueError(t("avatar_server.google_contacts.missing_param"))

    max_results = params.get("max_results", 5)
    connector.log_debug(t("log.gcontacts_search_start", query=params["query"], max=max_results))

    try:
        results = service.people().searchContacts(
            query=params["query"], pageSize=max_results, readMask="names,emailAddresses,phoneNumbers"
        ).execute()

        people = results.get("results",[])
        connector.log_debug(t("log.gcontacts_found", count=len(people)))

        if not people:
            return t("avatar_server.google_contacts.no_results", query=params["query"])

        raw_data_list =[]
        for person_result in people:
            person = person_result.get("person", {})
            name = person.get("names", [{}])[0].get("displayName", t("avatar_server.google_contacts.no_name"))

            emails_str = ", ".join(emails) if (emails :=[e.get("value") for e in person.get("emailAddresses", []) if e.get("value")]) else "N/A"
            phones_str = ", ".join(phones) if (phones :=[p.get("value") for p in person.get("phoneNumbers", []) if p.get("value")]) else "N/A"

            raw_data_list.append(t("avatar_server.google_contacts.contact_format", name=name, emails=emails_str, phones=phones_str))

        raw_string = "\n".join(raw_data_list)
        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        connector.log_debug(t("log.gcontacts_triage"))

        smart_summary = ask_local_llm(
            data_to_analyze=raw_string,
            context_description=t("google_contacts.context_search", query=params["query"]),
            avatar_name=avatar_name,
        )

        return smart_summary

    except Exception as e:
        connector.log_debug(t("log.gcontacts_api_error", error=e))
        raise e

def action_wrapper(connector: BaseConnector, action_func, params: dict):
    service = authenticate(connector)
    return action_func(connector, service, params)

if __name__ == "__main__":
    connector = BaseConnector(t("avatar_server.google_contacts.cmd_desc"))
    connector.register_action("search", lambda params: action_wrapper(connector, search_contacts, params))
    connector.run()