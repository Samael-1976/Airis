# src/connectors/gitlab.py
# Esecutore Autonomo per GitLab (v2.0 - BaseConnector Refactor)
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
    import gitlab
    from src.guardian import Guardian
    from agent_base import ask_local_llm
except ImportError:
    print('{"status": "error", "message": "' + t("connectors.gitlab.lib_error") + '"}')
    sys.exit(1)

def authenticate(connector: BaseConnector, creds: dict) -> gitlab.Gitlab:
    url = creds.get("url", "https://gitlab.com")
    private_token = creds.get("private_token")

    if not private_token or "IL_TUO" in private_token:
        connector.log_debug(t("connectors.gitlab.auth_error"))
        raise ValueError(t("connectors.gitlab.auth_error"))

    connector.log_debug(t("log.gitlab_attempt_conn", url=url, start=private_token[:4], end=private_token[-4:]))
    gl = gitlab.Gitlab(url=url, private_token=private_token)

    try:
        gl.auth()
        connector.log_debug(t("log.gitlab_auth_success", user=gl.user.username))
    except Exception as e:
        connector.log_debug(t("log.gitlab_auth_error", error=str(e)))
        raise ConnectionError(t("connectors.gitlab.conn_failed", error=str(e)))

    return gl

def list_projects(connector: BaseConnector, gl: gitlab.Gitlab, params: dict) -> str:
    connector.log_debug(t("log.gitlab_request_projects"))
    projects = gl.projects.list(owned=True, order_by="updated_at", sort="desc", per_page=10)

    connector.log_debug(t("log.gitlab_projects_found", count=len(projects)))

    if not projects:
        return t("connectors.gitlab.no_projects")

    raw_data_list =[]
    for p in projects:
        raw_data_list.append(
            t("avatar_server.gitlab.project_format", name=p.name_with_namespace, id=p.id, desc=p.description, date=p.last_activity_at)
        )

    raw_string = "\n".join(raw_data_list)
    avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
    connector.log_debug(t("log.gitlab_triage_projects"))

    smart_summary = ask_local_llm(
        data_to_analyze=raw_string,
        context_description=t("connectors.gitlab.context_list"),
        avatar_name=avatar_name,
    )

    return smart_summary

def create_issue(connector: BaseConnector, gl: gitlab.Gitlab, params: dict) -> str:
    required = ["project_id", "title"]
    if not all(p in params for p in required):
        raise ValueError(t("avatar_server.gitlab.missing_params", params=", ".join(required)))

    project_id = params["project_id"]
    connector.log_debug(t("log.gitlab_attempt_issue", id=project_id))

    try:
        project = gl.projects.get(project_id)
        issue = project.issues.create({"title": params["title"], "description": params.get("description", "")})
        connector.log_debug(t("log.gitlab_issue_created", id=issue.iid))

        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        confirmation_data = t("connectors.gitlab.issue_confirm", number=issue.iid, project=project.name, title=params["title"], url=issue.web_url)

        smart_confirmation = ask_local_llm(
            data_to_analyze=confirmation_data,
            context_description=t("connectors.gitlab.context_issue"),
            avatar_name=avatar_name,
        )

        return smart_confirmation

    except Exception as e:
        connector.log_debug(t("log.gitlab_issue_error", error=str(e)))
        raise Exception(t("connectors.gitlab.issue_error", error=str(e)))

def action_wrapper(connector: BaseConnector, action_func, params: dict):
    guardian = Guardian()
    creds_config = guardian.get_credentials("gitlab_api")
    if not creds_config:
        raise ValueError(t("avatar_server.gitlab.creds_not_found"))
    gl = authenticate(connector, creds_config)
    return action_func(connector, gl, params)

if __name__ == "__main__":
    connector = BaseConnector(t("avatar_server.gitlab.cmd_desc"))
    connector.register_action("list_projects", lambda params: action_wrapper(connector, list_projects, params))
    connector.register_action("create_issue", lambda params: action_wrapper(connector, create_issue, params))
    connector.run()