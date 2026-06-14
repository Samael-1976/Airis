# src/connectors/twitter.py
# Esecutore Autonomo per Twitter/X (v2.0 - BaseConnector Refactor)
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
    import tweepy
    from src.guardian import Guardian
    from agent_base import ask_local_llm
except ImportError:
    print('{"status": "error", "message": "' + t("twitter.lib_error") + '"}')
    sys.exit(1)

def authenticate(connector: BaseConnector, creds: dict) -> tweepy.Client:
    consumer_key = creds.get("consumer_key")
    consumer_secret = creds.get("consumer_secret")
    access_token = creds.get("access_token")
    access_token_secret = creds.get("access_token_secret")
    bearer_token = creds.get("bearer_token")

    if not all([consumer_key, consumer_secret, access_token, access_token_secret, bearer_token]) or "IL_TUO" in consumer_key:
        connector.log_debug("Credenziali mancanti o placeholder.")
        raise ValueError(t("twitter.auth_error"))

    connector.log_debug("Inizializzazione client Tweepy v2...")
    client = tweepy.Client(
        bearer_token=bearer_token,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )
    return client

def post_tweet(connector: BaseConnector, client: tweepy.Client, params: dict) -> str:
    if "text" not in params:
        raise ValueError("Parametro 'text' mancante per pubblicare il tweet.")

    text_to_post = params["text"]
    connector.log_debug(f"Tentativo pubblicazione tweet: '{text_to_post[:30]}...'")

    try:
        response = client.create_tweet(text=text_to_post)

        tweet_data = response.data
        if tweet_data and "id" in tweet_data:
            tweet_id = tweet_data["id"]
            connector.log_debug(f"Tweet pubblicato. ID: {tweet_id}")

            avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
            confirmation_data = t("twitter.post_confirm", text=text_to_post, id=tweet_id)

            smart_confirmation = ask_local_llm(
                data_to_analyze=confirmation_data,
                context_description=t("twitter.context_post"),
                avatar_name=avatar_name,
            )

            return smart_confirmation
        else:
            raise Exception(f"L'API di Twitter non ha restituito un ID valido. Risposta: {response}")

    except Exception as e:
        connector.log_debug(f"Errore API Twitter: {e}")
        raise e

def action_wrapper(connector: BaseConnector, action_func, params: dict):
    guardian = Guardian()
    creds_config = guardian.get_credentials("twitter_api")
    if not creds_config:
        raise ValueError(t("twitter.auth_error"))
    client = authenticate(connector, creds_config)
    return action_func(connector, client, params)

if __name__ == "__main__":
    connector = BaseConnector("Connettore per Twitter/X.")
    connector.register_action("post_tweet", lambda params: action_wrapper(connector, post_tweet, params))
    connector.run()