# src/connectors/google_calendar.py
# Esecutore Autonomo per Google Calendar (v2.0 - BaseConnector Refactor)
# LEGGE A0099: Invarianza strutturale garantita.

import sys
import os
from pathlib import Path
from datetime import datetime, timezone

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
    print('{"status": "error", "message": "' + t("google_calendar.lib_error") + '"}')
    sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def authenticate(connector: BaseConnector):
    creds = None
    guardian = Guardian()
    creds_config = guardian.get_credentials("google_api")
    if not creds_config:
        connector.log_debug(t("log.gcal_config_missing"))
        raise ValueError(t("google_calendar.auth_error"))

    token_path = PROJECT_ROOT / creds_config.get("token_path", "config/google_token.json")
    client_secrets_path = PROJECT_ROOT / creds_config.get("client_secrets_path", "config/google_client_secret.json")

    if not client_secrets_path.exists():
        connector.log_debug(t("log.gcal_secret_not_found", path=client_secrets_path))
        raise FileNotFoundError(t("google_calendar.secret_error", name=client_secrets_path.name))

    if token_path.exists():
        connector.log_debug(t("log.gcal_token_found"))
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            connector.log_debug(t("log.gcal_token_expired"))
            creds.refresh(Request())
        else:
            connector.log_debug(t("log.gcal_token_invalid"))
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_path), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as token:
            token.write(creds.to_json())
            connector.log_debug(t("log.gcal_token_saved"))

    return build("calendar", "v3", credentials=creds)

def list_upcoming_events(connector: BaseConnector, service, params: dict):
    max_results = params.get("max_results", 10)
    now = datetime.now(timezone.utc).isoformat()
    connector.log_debug(t("log.gcal_request_events", now=now, max=max_results))

    try:
        events_result = service.events().list(
            calendarId="primary", timeMin=now, maxResults=max_results, singleEvents=True, orderBy="startTime"
        ).execute()
        events = events_result.get("items",[])
        connector.log_debug(t("log.gcal_events_found", count=len(events)))

        if not events:
            return t("google_calendar.no_events")

        raw_data_list = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            summary = event.get("summary", t("google_calendar.no_title"))
            location = event.get("location", "N/A")
            description = event.get("description", "N/A")
            raw_data_list.append(
                t("google_calendar.event_format", summary=summary, start=start, location=location, description=description)
            )

        raw_string = "\n".join(raw_data_list)
        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        connector.log_debug(t("log.gcal_triage_list"))

        smart_summary = ask_local_llm(
            data_to_analyze=raw_string,
            context_description=t("google_calendar.context_list"),
            avatar_name=avatar_name,
        )

        return smart_summary

    except Exception as e:
        connector.log_debug(t("log.gcal_api_error", action="List", error=e))
        raise e

def create_event(connector: BaseConnector, service, params: dict):
    required_params = ["summary", "start_time", "end_time"]
    if not all(p in params for p in required_params):
        raise ValueError(t("google_calendar.missing_params", params=", ".join(required_params)))

    connector.log_debug(t("log.gcal_create_start", summary=params["summary"]))

    event = {
        "summary": params["summary"],
        "location": params.get("location", ""),
        "description": params.get("description", ""),
        "start": {"dateTime": params["start_time"], "timeZone": "Europe/Rome"},
        "end": {"dateTime": params["end_time"], "timeZone": "Europe/Rome"},
    }

    try:
        created_event = service.events().insert(calendarId="primary", body=event).execute()
        connector.log_debug(t("log.gcal_create_success", id=created_event.get("id")))

        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        confirmation_data = t(
            "google_calendar.create_confirm", summary=params["summary"], start=params["start_time"], end=params["end_time"]
        )

        smart_confirmation = ask_local_llm(
            data_to_analyze=confirmation_data,
            context_description=t("google_calendar.context_create"),
            avatar_name=avatar_name,
        )

        return smart_confirmation
    except Exception as e:
        connector.log_debug(t("log.gcal_api_error", action="Create", error=e))
        raise e

def action_wrapper(connector: BaseConnector, action_func, params: dict):
    service = authenticate(connector)
    return action_func(connector, service, params)

if __name__ == "__main__":
    connector = BaseConnector(t("google_calendar.cmd_desc"))
    connector.register_action("list", lambda params: action_wrapper(connector, list_upcoming_events, params))
    connector.register_action("create", lambda params: action_wrapper(connector, create_event, params))
    connector.run()