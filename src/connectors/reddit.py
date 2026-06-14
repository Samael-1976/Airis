# src/connectors/reddit.py
# Esecutore Autonomo per Reddit (v2.0 - BaseConnector Refactor)
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
    import praw
    from src.guardian import Guardian
    from agent_base import ask_local_llm
except ImportError:
    print('{"status": "error", "message": "' + t("reddit.lib_error") + '"}')
    sys.exit(1)

def authenticate(connector: BaseConnector, creds: dict) -> praw.Reddit:
    client_id = creds.get("client_id")
    client_secret = creds.get("client_secret")
    user_agent = creds.get("user_agent")
    username = creds.get("username")
    password = creds.get("password")

    if not all([client_id, client_secret, user_agent, username, password]) or "IL_TUO" in client_id:
        connector.log_debug("Credenziali mancanti o placeholder.")
        raise ValueError(t("reddit.auth_error"))

    connector.log_debug(f"Inizializzazione PRAW per utente: {username}")

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
        username=username,
        password=password,
    )

    try:
        me = reddit.user.me()
        connector.log_debug(f"Autenticazione riuscita. Account: {me.name}")
    except Exception as e:
        connector.log_debug(f"Errore autenticazione: {e}")
        raise ConnectionError(t("reddit.conn_failed"))

    return reddit

def submit_post(connector: BaseConnector, reddit: praw.Reddit, params: dict) -> str:
    required = ["subreddit", "title"]
    if not all(p in params for p in required):
        raise ValueError(f"Parametri mancanti. Richiesti: {', '.join(required)}")
    if "selftext" not in params and "url" not in params:
        raise ValueError("Parametro mancante. Richiesto 'selftext' o 'url'.")

    connector.log_debug(f"Pubblicazione su r/{params['subreddit']}: '{params['title']}'")

    try:
        subreddit = reddit.subreddit(params["subreddit"])

        submission = subreddit.submit(
            title=params["title"],
            selftext=params.get("selftext"),
            url=params.get("url"),
        )

        connector.log_debug(f"Post pubblicato. ID: {submission.id}")

        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        confirmation_data = t(
            "reddit.submit_confirm",
            title=params["title"],
            subreddit=params["subreddit"],
            url=submission.shortlink,
        )

        smart_confirmation = ask_local_llm(
            data_to_analyze=confirmation_data,
            context_description=t("reddit.context_submit"),
            avatar_name=avatar_name,
        )

        return smart_confirmation
    except Exception as e:
        connector.log_debug(f"Errore pubblicazione: {e}")
        raise e

def get_hot_posts(connector: BaseConnector, reddit: praw.Reddit, params: dict) -> str:
    if "subreddit" not in params:
        raise ValueError("Parametro 'subreddit' mancante.")

    limit = params.get("limit", 5)
    connector.log_debug(f"Recupero Hot Posts da r/{params['subreddit']} (Limit: {limit})")

    try:
        subreddit = reddit.subreddit(params["subreddit"])

        hot_posts = list(subreddit.hot(limit=limit))
        connector.log_debug(f"Post trovati: {len(hot_posts)}")

        if not hot_posts:
            return t("reddit.no_hot_posts", subreddit=params["subreddit"])

        raw_data_list =[]
        for post in hot_posts:
            raw_data_list.append(
                f"TITOLO: {post.title} | SCORE: {post.score} | URL: {post.shortlink} | TESTO: {post.selftext[:300] if post.selftext else 'Link Post'}"
            )

        raw_string = "\n".join(raw_data_list)
        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        connector.log_debug("Inoltro post all'agente locale per il Triage...")

        smart_summary = ask_local_llm(
            data_to_analyze=raw_string,
            context_description=t("reddit.context_hot", subreddit=params["subreddit"]),
            avatar_name=avatar_name,
        )

        return smart_summary
    except Exception as e:
        connector.log_debug(f"Errore recupero post: {e}")
        raise e

def action_wrapper(connector: BaseConnector, action_func, params: dict):
    guardian = Guardian()
    creds_config = guardian.get_credentials("reddit_api")
    if not creds_config:
        raise ValueError(t("reddit.auth_error"))
    reddit = authenticate(connector, creds_config)
    return action_func(connector, reddit, params)

if __name__ == "__main__":
    connector = BaseConnector("Connettore per Reddit.")
    connector.register_action("submit_post", lambda params: action_wrapper(connector, submit_post, params))
    connector.register_action("get_hot_posts", lambda params: action_wrapper(connector, get_hot_posts, params))
    connector.run()