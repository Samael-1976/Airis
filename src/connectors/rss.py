# src/connectors/rss.py
# Esecutore Autonomo per RSS Feeds (v2.0 - BaseConnector Refactor)
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
    import feedparser
    from src.guardian import Guardian
    from agent_base import ask_local_llm
except ImportError:
    print('{"status": "error", "message": "' + t("rss.lib_error") + '"}')
    sys.exit(1)

def read_feed(connector: BaseConnector, params: dict) -> str:
    if "url" not in params:
        raise ValueError("Parametro 'url' mancante.")

    url = params["url"]
    limit = params.get("limit", 5)

    connector.log_debug(f"Lettura feed: {url} (Limit: {limit})")

    try:
        feed = feedparser.parse(url)

        if feed.bozo:
            connector.log_debug(f"Avviso parsing (Bozo=1): {feed.bozo_exception}")
            if not feed.entries:
                raise Exception(f"Errore nel parsing del feed: {feed.bozo_exception}")

        feed_title = feed.feed.get("title", "Feed Senza Titolo")
        connector.log_debug(f"Titolo Feed: {feed_title}")

        entries = feed.entries[:limit]
        connector.log_debug(f"Notizie trovate: {len(entries)}")

        if not entries:
            return t("rss.no_entries", title=feed_title)

        raw_data_list =[]
        for entry in entries:
            title = entry.get("title", "Senza titolo")
            link = entry.get("link", "#")
            published = entry.get("published", entry.get("updated", "Data sconosciuta"))
            summary = entry.get("summary", entry.get("description", ""))

            raw_data_list.append(
                f"TITOLO: {title} | DATA: {published} | LINK: {link} | ESTRATTO: {summary[:500]}"
            )

        raw_string = "\n\n---\n\n".join(raw_data_list)
        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        connector.log_debug("Inoltro notizie all'agente locale per il Triage...")

        smart_summary = ask_local_llm(
            data_to_analyze=raw_string,
            context_description=t("rss.context_triage", title=feed_title),
            avatar_name=avatar_name,
        )

        return smart_summary

    except Exception as e:
        connector.log_debug(f"Eccezione durante il parsing: {e}")
        raise Exception(t("rss.parse_error", error=str(e)))

if __name__ == "__main__":
    connector = BaseConnector("Connettore per RSS Feeds.")
    connector.register_action("read_feed", lambda params: read_feed(connector, params))
    connector.run()