# src/connectors/telegram.py
# Esecutore Autonomo per Telegram (v2.0 - BaseConnector Refactor)
# LEGGE A0099: Invarianza strutturale garantita.

import sys
import os
from pathlib import Path
import asyncio

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.translator import t
from src.connectors.base_connector import BaseConnector

try:
    import telegram
    from src.guardian import Guardian
    from agent_base import ask_local_llm
except ImportError:
    print('{"status": "error", "message": "' + t("telegram.lib_error") + '"}')
    sys.exit(1)

async def send_message_action(connector: BaseConnector, token, chat_id, content):
    connector.log_debug(f"Inizializzazione Bot per invio su Chat ID: {chat_id}")
    try:
        bot = telegram.Bot(token=token)
        connector.log_debug("Invio messaggio...")
        message = await bot.send_message(chat_id=chat_id, text=content)
        connector.log_debug(f"Messaggio inviato. Message ID: {message.message_id}")
        return message
    except Exception as e:
        connector.log_debug(f"Errore generico Telegram: {e}")
        raise e

async def list_messages_action(connector: BaseConnector, token, limit=5):
    connector.log_debug("Richiesta ultimi aggiornamenti dal bot...")
    try:
        bot = telegram.Bot(token=token)
        updates = await bot.get_updates(limit=limit, allowed_updates=["message"])

        messages_data =[]
        for u in updates:
            if u.message:
                sender = u.message.from_user.username or u.message.from_user.first_name
                date = u.message.date
                text = u.message.text or "[Contenuto non testuale]"
                messages_data.append(f"MITTENTE: {sender} | DATA: {date} | TESTO: {text}")

        return messages_data
    except Exception as e:
        connector.log_debug(f"Errore recupero aggiornamenti: {e}")
        raise e

def handle_telegram_action(connector: BaseConnector, action: str, params: dict) -> str:
    guardian = Guardian()
    creds_config = guardian.get_credentials("telegram_api")
    if not creds_config:
        raise ValueError(t("telegram.auth_error"))

    bot_token = creds_config.get("bot_token")
    if not bot_token or "IL_TUO" in bot_token:
        connector.log_debug("Bot Token mancante o placeholder.")
        raise ValueError(t("telegram.auth_error"))

    avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")

    if action == "send_message":
        content = params.get("content")
        if not content:
            raise ValueError("Parametro 'content' mancante.")

        chat_id = params.get("chat_id") or creds_config.get("chat_id")
        if not chat_id:
            raise ValueError("Nessun 'chat_id' specificato.")

        asyncio.run(send_message_action(connector, bot_token, chat_id, content))

        confirmation_data = t("telegram.send_confirm", id=chat_id, content=content)
        return ask_local_llm(
            data_to_analyze=confirmation_data,
            context_description=t("telegram.context_send"),
            avatar_name=avatar_name,
        )

    elif action == "list_messages":
        limit = params.get("limit", 5)
        raw_messages = asyncio.run(list_messages_action(connector, bot_token, limit))

        if not raw_messages:
            return t("telegram.no_messages")
        
        raw_string = "\n".join(raw_messages)
        connector.log_debug("Inoltro messaggi all'agente locale per il Triage...")
        return ask_local_llm(
            data_to_analyze=raw_string,
            context_description=t("telegram.context_list"),
            avatar_name=avatar_name,
        )

if __name__ == "__main__":
    connector = BaseConnector("Connettore per Telegram.")
    connector.register_action("send_message", lambda params: handle_telegram_action(connector, "send_message", params))
    connector.register_action("list_messages", lambda params: handle_telegram_action(connector, "list_messages", params))
    connector.run()