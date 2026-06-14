# src/connectors/forms.py
# Esecutore Autonomo per Typeform (v1.2 - Smart Agent Triage)
# ADD: Integrazione con agent_base per distillazione e triage dei moduli e delle risposte.
# MANTENUTO: Logica API Typeform, list_forms, get_responses.
# LEGGE A0099: Invarianza strutturale garantita.

import argparse
import json
import sys
import os
from pathlib import Path
import requests

# --- GESTIONE DEI PERCORSI PER L'AUTONOMIA ---
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from src.guardian import Guardian

    # --- [NUOVO v1.2] IMPORT AGENTE LOCALE ---
    from agent_base import ask_local_llm
    from utils.translator import t
except ImportError:
    from utils.translator import t

    print(json.dumps({"status": "error", "message": t("forms.lib_error")}))
    sys.exit(1)

# --- CONFIGURAZIONE ---
TYPEFORM_API_URL = "https://api.typeform.com"

# Buffer per i log di debug
debug_buffer = []


def log_debug(msg):
    """Scrive su stderr (console) e nel buffer."""
    sys.stderr.write(t("log.forms_debug_prefix", msg=msg))
    debug_buffer.append(f"[DEBUG] {msg}")


def get_headers(token: str):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def list_forms(params: dict, creds: dict) -> str:
    """
    Elenca i form disponibili e li distilla tramite l'agente locale.
    """
    token = creds.get("personal_access_token")
    if not token or "IL_TUO" in token:
        log_debug(t("avatar_server.forms.auth_error"))
        raise ValueError(t("avatar_server.forms.auth_error"))

    page_size = params.get("page_size", 10)
    log_debug(t("log.forms_request_list", size=page_size))

    try:
        url = f"{TYPEFORM_API_URL}/forms"
        response = requests.get(
            url, headers=get_headers(token), params={"page_size": page_size}, timeout=10
        )

        response.raise_for_status()
        data = response.json()

        items = data.get("items", [])
        log_debug(t("log.forms_found", count=len(items)))

        if not items:
            return t("avatar_server.forms.no_forms")

        raw_data_list = []
        for item in items:
            raw_data_list.append(
                t(
                    "avatar_server.forms.form_item_format",
                    title=item["title"],
                    id=item["id"],
                    date=item["last_updated_at"],
                )
            )

        raw_string = "\n".join(raw_data_list)

        # --- [NUOVO v1.2] FASE DI TRIAGE INTELLIGENTE ---
        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        log_debug(t("log.forms_triage_list"))

        smart_summary = ask_local_llm(
            data_to_analyze=raw_string,
            context_description=t("forms.context_list"),
            avatar_name=avatar_name,
        )

        return smart_summary

    except requests.exceptions.RequestException as e:
        log_debug(t("log.forms_api_error", error=str(e)))
        raise Exception(t("avatar_server.forms.api_error", error=str(e)))


def get_responses(params: dict, creds: dict) -> str:
    """
    Recupera le risposte per un form specifico e le distilla tramite l'agente locale.
    """
    token = creds.get("personal_access_token")
    if not token or "IL_TUO" in token:
        raise ValueError(t("avatar_server.forms.auth_error"))

    if "form_id" not in params:
        raise ValueError(t("avatar_server.forms.missing_param"))

    page_size = params.get("page_size", 5)
    form_id = params["form_id"]

    log_debug(t("log.forms_request_responses", id=form_id, size=page_size))

    try:
        url = f"{TYPEFORM_API_URL}/forms/{form_id}/responses"
        response = requests.get(
            url, headers=get_headers(token), params={"page_size": page_size}, timeout=10
        )

        response.raise_for_status()
        data = response.json()

        items = data.get("items", [])
        log_debug(t("log.forms_responses_found", count=len(items)))

        if not items:
            return t("avatar_server.forms.no_responses", id=form_id)

        raw_responses = []
        for item in items:
            submitted_at = item.get(
                "submitted_at", t("avatar_server.forms.unknown_date")
            )
            answers = item.get("answers", [])

            ans_summary = t("avatar_server.forms.response_header", date=submitted_at)
            for answer in answers:
                ans_type = answer.get("type")
                value = "N/A"
                if ans_type == "text":
                    value = answer.get("text")
                elif ans_type == "choice":
                    value = answer.get("choice", {}).get("label")
                elif ans_type == "email":
                    value = answer.get("email")
                elif ans_type == "number":
                    value = str(answer.get("number"))
                elif ans_type == "boolean":
                    value = str(answer.get("boolean"))

                ans_summary += f"- {ans_type}: {value}\n"
            raw_responses.append(ans_summary)

        raw_string = "\n---\n".join(raw_responses)

        # --- [NUOVO v1.2] FASE DI TRIAGE INTELLIGENTE ---
        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        log_debug(t("log.forms_triage_responses"))

        smart_summary = ask_local_llm(
            data_to_analyze=raw_string,
            context_description=t("forms.context_responses", id=form_id),
            avatar_name=avatar_name,
        )

        return smart_summary

    except requests.exceptions.RequestException as e:
        log_debug(t("log.forms_api_error", error=str(e)))
        raise Exception(t("avatar_server.forms.api_error", error=str(e)))


def main():
    parser = argparse.ArgumentParser(description=t("avatar_server.forms.cmd_desc"))
    parser.add_argument(
        "--action",
        required=True,
        choices=["list_forms", "get_responses"],
        help=t("avatar_server.forms.help_action"),
    )
    parser.add_argument(
        "--params", type=str, default="{}", help=t("avatar_server.forms.help_params")
    )

    args = parser.parse_args()
    debug_buffer.clear()

    try:
        guardian = Guardian()
        creds_config = guardian.get_credentials("forms_api")
        if not creds_config:
            raise ValueError(t("avatar_server.forms.creds_not_found"))

        params = json.loads(args.params)

        result_data = None
        if args.action == "list_forms":
            result_data = list_forms(params, creds_config)
        elif args.action == "get_responses":
            result_data = get_responses(params, creds_config)

        print(json.dumps({"status": "success", "data": result_data}))

    except Exception as e:
        debug_str = " | ".join(debug_buffer)
        print(
            json.dumps({"status": "error", "message": f"{str(e)} [LOG: {debug_str}]"})
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
