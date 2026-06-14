# src/connectors/asana.py
# Esecutore Autonomo per Asana (v2.0 - BaseConnector Refactor)
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
    import asana
    from src.guardian import Guardian
    from agent_base import ask_local_llm
except ImportError:
    print('{"status": "error", "message": "' + t("asana.lib_error") + '"}')
    sys.exit(1)

def authenticate(connector: BaseConnector, creds: dict) -> asana.Client:
    token = creds.get("personal_access_token")

    if not token or "IL_TUO" in token:
        connector.log_debug(t("log.asana_token_missing"))
        raise ValueError(t("asana.auth_error"))

    connector.log_debug(t("log.asana_auth_attempt", prefix=token[:5], suffix=token[-3:]))
    client = asana.Client.access_token(token)

    try:
        me = client.users.me()
        connector.log_debug(t("log.asana_auth_success", name=me.get("name"), gid=me.get("gid")))
    except asana.error.NoAuthorizationError:
        connector.log_debug(t("log.asana_auth_error_401"))
        raise ConnectionError(t("asana.auth_failed"))
    except Exception as e:
        connector.log_debug(t("log.asana_conn_error", error=e))
        raise ConnectionError(t("asana.conn_error", error=e))

    return client

def list_workspaces(connector: BaseConnector, client: asana.Client, params: dict) -> str:
    connector.log_debug(t("log.asana_list_workspaces"))
    workspaces = list(client.workspaces.get_workspaces())
    connector.log_debug(t("log.asana_workspaces_found", count=len(workspaces)))

    if not workspaces:
        return t("asana.no_workspaces")

    raw_data = "\n".join([f"NOME: {ws['name']} | GID: {ws['gid']}" for ws in workspaces])

    avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
    connector.log_debug(t("log.asana_triage_workspaces"))

    smart_summary = ask_local_llm(
        data_to_analyze=raw_data,
        context_description=t("asana.context_workspaces"),
        avatar_name=avatar_name,
    )

    return smart_summary

def list_projects(connector: BaseConnector, client: asana.Client, params: dict) -> str:
    if "workspace_gid" not in params:
        raise ValueError(t("avatar_server.asana.workspace_missing"))

    connector.log_debug(t("log.asana_list_projects", gid=params["workspace_gid"]))
    projects = list(client.projects.get_projects(workspace=params["workspace_gid"]))
    connector.log_debug(t("log.asana_projects_found", count=len(projects)))

    if not projects:
        return t("asana.no_projects")

    raw_data = "\n".join([f"PROGETTO: {p['name']} | GID: {p['gid']}" for p in projects])

    avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
    connector.log_debug(t("log.asana_triage_projects"))

    smart_summary = ask_local_llm(
        data_to_analyze=raw_data,
        context_description=t("asana.context_projects", gid=params["workspace_gid"]),
        avatar_name=avatar_name,
    )

    return smart_summary

def create_task(connector: BaseConnector, client: asana.Client, params: dict) -> str:
    required =["workspace_gid", "project_gid", "name"]
    if not all(p in params for p in required):
        raise ValueError(t("avatar_server.asana.params_missing", params=", ".join(required)))

    connector.log_debug(t("log.asana_create_task_start", name=params["name"], gid=params["project_gid"]))

    task_data = {
        "name": params["name"],
        "notes": params.get("notes", ""),
        "projects": [params["project_gid"]],
        "workspace": params["workspace_gid"],
    }

    try:
        new_task = client.tasks.create_task(task_data)
        connector.log_debug(t("log.asana_create_task_success", gid=new_task["gid"]))
        return t("asana.task_created", name=new_task["name"], gid=new_task["gid"])
    except Exception as e:
        connector.log_debug(t("log.asana_create_task_error", error=e))
        raise e

def action_wrapper(connector: BaseConnector, action_func, params: dict):
    guardian = Guardian()
    creds_config = guardian.get_credentials("asana_api")
    if not creds_config:
        raise ValueError(t("asana.auth_error"))
    client = authenticate(connector, creds_config)
    return action_func(connector, client, params)

if __name__ == "__main__":
    connector = BaseConnector(t("avatar_server.asana.cmd_desc"))
    connector.register_action("list_workspaces", lambda params: action_wrapper(connector, list_workspaces, params))
    connector.register_action("list_projects", lambda params: action_wrapper(connector, list_projects, params))
    connector.register_action("create_task", lambda params: action_wrapper(connector, create_task, params))
    connector.run()