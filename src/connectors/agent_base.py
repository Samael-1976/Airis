# src/connectors/agent_base.py
# [DEV] Il Nucleo dell'Intelligenza Distribuita (v1.0)
# Questo helper permette ai connettori di agire come Mini-Agenti.
# Implementa la logica di Triage e il mantenimento del tono di [nome_avatar].
# LEGGE A0099: Invarianza strutturale garantita.

import requests
import json
import os
import sys
from pathlib import Path
from utils.translator import t

# --- CONFIGURAZIONE CONNESSIONE LOCALE ---
LOCAL_API_URL = "http://127.0.0.1:8080/v1/chat/completions"


def ask_local_llm(
    data_to_analyze: str, context_description: str, avatar_name: str = "L'Anima"
) -> str:
    """
    Invia i dati grezzi al cervello locale per il Triage e la distillazione.
    Mantiene il tono dell'avatar e filtra le informazioni irrilevanti.
    """

    # --- PROMPT DI SISTEMA: IL MANDATO DELL'AGENTE ---
    system_prompt = t(
        "connectors.agent_base.system_prompt",
        avatar_name=avatar_name,
        context_description=context_description,
    )

    payload = {
        "model": "airis-local",  # Identificativo per il bridge interno
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": t(
                    "connectors.agent_base.raw_data_label", data=data_to_analyze
                ),
            },
        ],
        "temperature": 0.3,  # Bassa temperatura per precisione nel triage
    }

    try:
        # Invio richiesta al server locale (avatar_server.py)
        response = requests.post(LOCAL_API_URL, json=payload, timeout=60)

        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        else:
            return t(
                "connectors.agent_base.error_local_llm", status=response.status_code
            )

    except Exception as e:
        return t("connectors.agent_base.error_communication", error=str(e))


# --- TEST STANDALONE (Opzionale) ---
if __name__ == "__main__":
    test_data = t("log.agent_base_test_data")
    print(ask_local_llm(test_data, t("log.test_triage_gmail")))
