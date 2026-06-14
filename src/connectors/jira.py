# src/connectors/jira.py
# Esecutore Autonomo per Jira (v2.0 - BaseConnector Refactor)
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
    from jira import JIRA
    from src.guardian import Guardian
    from agent_base import ask_local_llm
except ImportError:
    print('{"status": "error", "message": "' + t("jira.lib_error") + '"}')
    sys.exit(1)

def authenticate(connector: BaseConnector, creds: dict) -> JIRA:
    server_url = creds.get("server_url")
    username = creds.get("username")
    api_token = creds.get("api_token")

    if not all([server_url, username, api_token]) or "IL_TUO" in server_url:
        connector.log_debug("Credenziali mancanti o placeholder rilevati.")
        raise ValueError(t("jira.auth_error"))

    connector.log_debug(f"Tentativo connessione a: {server_url} come {username}")
    options = {"server": server_url}

    try:
        jira_client = JIRA(options, basic_auth=(username, api_token))
        myself = jira_client.myself()
        connector.log_debug(f"Autenticazione riuscita. Account: {myself.get('displayName')}")
        return jira_client
    except Exception as e:
        connector.log_debug(f"Errore autenticazione: {e}")
        raise ConnectionError(t("jira.conn_error", error=str(e)))

def search_issues(connector: BaseConnector, client: JIRA, params: dict) -> str:
    if "jql_query" not in params:
        raise ValueError("Parametro 'jql_query' mancante.")

    max_results = params.get("max_results", 5)
    connector.log_debug(f"Esecuzione JQL: '{params['jql_query']}' (Max: {max_results})")

    try:
        issues = client.search_issues(params["jql_query"], max_results=max_results)
        connector.log_debug(f"Issue trovate: {len(issues)}")

        if not issues:
            return t("jira.no_issues", query=params["jql_query"])

        raw_data_list =[]
        for issue in issues:
            raw_data_list.append(
                f"KEY: {issue.key} | SOMMARIO: {issue.fields.summary} | STATO: {issue.fields.status.name} | PRIORITÀ: {issue.fields.priority.name if hasattr(issue.fields, 'priority') else 'N/A'}"
            )

        raw_string = "\n".join(raw_data_list)
        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        connector.log_debug("Inoltro issue all'agente locale per il Triage...")

        smart_summary = ask_local_llm(
            data_to_analyze=raw_string,
            context_description=t("jira.context_search", query=params["jql_query"]),
            avatar_name=avatar_name,
        )

        return smart_summary
    except Exception as e:
        connector.log_debug(f"Errore ricerca JQL: {e}")
        raise e

def create_issue(connector: BaseConnector, client: JIRA, params: dict) -> str:
    required =["project_key", "summary", "description", "issuetype_name"]
    if not all(p in params for p in required):
        raise ValueError(f"Parametri mancanti. Richiesti: {', '.join(required)}")

    connector.log_debug(f"Creazione issue in progetto: {params['project_key']}")

    issue_dict = {
        "project": {"key": params["project_key"]},
        "summary": params["summary"],
        "description": params["description"],
        "issuetype": {"name": params["issuetype_name"]},
    }

    try:
        new_issue = client.create_issue(fields=issue_dict)
        connector.log_debug(f"Issue creata con successo: {new_issue.key}")

        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        confirmation_data = t(
            "jira.create_confirm",
            key=new_issue.key,
            project=params["project_key"],
            title=params["summary"],
            type=params["issuetype_name"],
        )

        smart_confirmation = ask_local_llm(
            data_to_analyze=confirmation_data,
            context_description=t("jira.context_create"),
            avatar_name=avatar_name,
        )

        return smart_confirmation
    except Exception as e:
        connector.log_debug(f"Errore creazione issue: {e}")
        raise e

def action_wrapper(connector: BaseConnector, action_func, params: dict):
    guardian = Guardian()
    creds_config = guardian.get_credentials("jira_api")
    if not creds_config:
        raise ValueError("Configurazione 'jira_api' non trovata in credentials.yaml.")
    client = authenticate(connector, creds_config)
    return action_func(connector, client, params)

if __name__ == "__main__":
    connector = BaseConnector("Connettore per Jira.")
    connector.register_action("search_issues", lambda params: action_wrapper(connector, search_issues, params))
    connector.register_action("create_issue", lambda params: action_wrapper(connector, create_issue, params))
    connector.run()