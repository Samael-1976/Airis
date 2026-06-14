# src/connectors/github.py
# Esecutore Autonomo per GitHub (v2.0 - BaseConnector Refactor)
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
    from github import Github, GithubException
    from src.guardian import Guardian
    from agent_base import ask_local_llm
except ImportError:
    print('{"status": "error", "message": "' + t("github.lib_error") + '"}')
    sys.exit(1)

def authenticate(connector: BaseConnector, creds: dict) -> Github:
    auth_token = creds.get("auth_token")

    if not auth_token or "IL_TUO" in auth_token:
        connector.log_debug(t("log.github_token_missing"))
        raise ValueError(t("github.auth_error"))

    connector.log_debug(t("log.github_conn_attempt", prefix=auth_token[:4], suffix=auth_token[-4:]))
    g = Github(auth_token)

    try:
        user = g.get_user()
        login = user.login
        connector.log_debug(t("log.github_auth_success", login=login))
    except GithubException as e:
        connector.log_debug(t("log.github_auth_error", error=e))
        raise ConnectionError(t("github.conn_failed", error=e))
    except Exception as e:
        connector.log_debug(t("log.github_conn_error", error=e))
        raise ConnectionError(t("github.conn_error", error=e))

    return g

def list_repos(connector: BaseConnector, client: Github, params: dict) -> str:
    connector.log_debug(t("log.github_list_repos"))
    try:
        repos = client.get_user().get_repos(sort="updated", direction="desc")

        raw_data_list =[]
        count = 0
        for repo in repos:
            if count >= 15:
                break
            raw_data_list.append(
                t("avatar_server.github.repo_format", name=repo.full_name, desc=repo.description, lang=repo.language, date=repo.updated_at)
            )
            count += 1

        connector.log_debug(t("log.github_repos_found", count=count))

        if not raw_data_list:
            return t("github.no_repos")

        raw_string = "\n".join(raw_data_list)
        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        connector.log_debug(t("log.github_triage_repos"))

        smart_summary = ask_local_llm(
            data_to_analyze=raw_string,
            context_description=t("github.context_list"),
            avatar_name=avatar_name,
        )

        return smart_summary

    except Exception as e:
        connector.log_debug(t("log.github_list_repos_error", error=e))
        raise e

def create_issue(connector: BaseConnector, client: Github, params: dict) -> str:
    required =["repo_full_name", "title", "body"]
    if not all(p in params for p in required):
        raise ValueError(t("avatar_server.github.missing_params", required=", ".join(required)))

    repo_name = params["repo_full_name"]
    connector.log_debug(t("log.github_issue_attempt", name=repo_name))

    try:
        repo = client.get_repo(repo_name)
        issue = repo.create_issue(title=params["title"], body=params.get("body", ""))
        connector.log_debug(t("log.github_issue_success", number=issue.number))

        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        confirmation_data = t("github.issue_confirm", number=issue.number, repo=repo_name, title=params["title"], url=issue.html_url)

        smart_confirmation = ask_local_llm(
            data_to_analyze=confirmation_data,
            context_description=t("github.context_issue"),
            avatar_name=avatar_name,
        )

        return smart_confirmation

    except GithubException as e:
        connector.log_debug(t("log.github_api_error_log", error=e.data))
        msg = e.data.get("message", t("avatar_server.github.unspecified_error"))
        raise Exception(t("github.api_error", message=msg))
    except Exception as e:
        connector.log_debug(t("log.github_issue_error", error=e))
        raise e

def action_wrapper(connector: BaseConnector, action_func, params: dict):
    guardian = Guardian()
    creds_config = guardian.get_credentials("github_api")
    if not creds_config:
        raise ValueError(t("avatar_server.github.creds_not_found"))
    client = authenticate(connector, creds_config)
    return action_func(connector, client, params)

if __name__ == "__main__":
    connector = BaseConnector(t("avatar_server.github.cmd_desc"))
    connector.register_action("list_repos", lambda params: action_wrapper(connector, list_repos, params))
    connector.register_action("create_issue", lambda params: action_wrapper(connector, create_issue, params))
    connector.run()