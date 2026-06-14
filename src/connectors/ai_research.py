# src/connectors/ai_research.py
# Esecutore Autonomo per AI Research & Deep Search (v2.0 - BaseConnector Refactor)
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
    import arxiv
    from ddgs import DDGS
    from src.guardian import Guardian
    from agent_base import ask_local_llm
except ImportError:
    print('{"status": "error", "message": "' + t("connectors.ai_research.lib_error") + '"}')
    sys.exit(1)

def search_arxiv(connector: BaseConnector, params: dict) -> str:
    if "query" not in params:
        raise ValueError(t("avatar_server.ai_research.query_missing"))

    max_results = params.get("max_results", 5)
    connector.log_debug(t("log.ai_research_arxiv_start", query=params["query"], max=max_results))

    try:
        client = arxiv.Client()
        search = arxiv.Search(
            query=params["query"],
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )

        results =[]
        count = 0
        for r in client.results(search):
            count += 1
            authors = ", ".join([a.name for a in r.authors[:3]])
            summary = r.summary.replace("\n", " ")[:500]
            results.append(
                t("avatar_server.ai_research.arxiv_format", title=r.title, authors=authors, summary=summary, url=r.pdf_url)
            )

        connector.log_debug(t("log.ai_research_arxiv_count", count=count))

        if not results:
            return t("ai_research.arxiv_no_results", query=params["query"])

        raw_string = "\n\n---\n\n".join(results)
        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")

        connector.log_debug(t("log.ai_research_arxiv_triage"))
        smart_summary = ask_local_llm(
            data_to_analyze=raw_string,
            context_description=t("ai_research.context_arxiv", query=params["query"]),
            avatar_name=avatar_name,
        )

        return smart_summary

    except Exception as e:
        connector.log_debug(t("log.ai_research_arxiv_exception", error=str(e)))
        raise Exception(t("ai_research.arxiv_error", error=str(e)))

def deep_web_search(connector: BaseConnector, params: dict) -> str:
    if "query" not in params:
        raise ValueError(t("avatar_server.ai_research.query_missing"))

    max_results = params.get("max_results", 5)
    connector.log_debug(t("log.ai_research_web_start", query=params["query"], max=max_results))

    try:
        results =[]
        with DDGS() as ddgs:
            ddgs_gen = ddgs.text(
                params["query"],
                region="wt-wt",
                safesearch="off",
                timelimit="y",
                max_results=max_results,
            )
            for r in ddgs_gen:
                results.append(
                    t("avatar_server.ai_research.web_format", title=r["title"], snippet=r["body"], url=r["href"])
                )

        connector.log_debug(t("log.ai_research_web_count", count=len(results)))

        if not results:
            return t("ai_research.web_no_results", query=params["query"])

        raw_string = "\n\n---\n\n".join(results)
        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")

        connector.log_debug(t("log.ai_research_web_triage"))
        smart_summary = ask_local_llm(
            data_to_analyze=raw_string,
            context_description=t("ai_research.context_web", query=params["query"]),
            avatar_name=avatar_name,
        )

        return smart_summary

    except Exception as e:
        connector.log_debug(t("log.ai_research_web_exception", error=str(e)))
        raise Exception(t("ai_research.web_error", error=str(e)))

if __name__ == "__main__":
    connector = BaseConnector(t("avatar_server.ai_research.cmd_desc"))
    connector.register_action("search_arxiv", lambda params: search_arxiv(connector, params))
    connector.register_action("deep_web_search", lambda params: deep_web_search(connector, params))
    connector.run()