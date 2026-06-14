# src/connectors/discord.py
# Esecutore Autonomo per Discord (v2.0 - BaseConnector Refactor)
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
    import discord
    from src.guardian import Guardian
    from agent_base import ask_local_llm
except ImportError:
    print('{"status": "error", "message": "' + t("discord.lib_error") + '"}')
    sys.exit(1)

async def send_message_action(connector: BaseConnector, token, channel_id, content):
    connector.log_debug(t("discord.log.init_send", id=channel_id))
    intents = discord.Intents.default()
    intents.messages = True

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        connector.log_debug(t("discord.log.connected", user=client.user))
        try:
            channel = await client.fetch_channel(int(channel_id))
            if not channel:
                raise ValueError(t("discord.log.chan_not_found", id=channel_id))

            connector.log_debug(t("discord.log.sending"))
            await channel.send(content)
            connector.log_debug(t("discord.log.success"))
            await client.close()
        except Exception as e:
            connector.log_debug(t("discord.log.err_send", error=e))
            client.last_error = e
            await client.close()

    client.last_error = None
    try:
        await client.start(token)
    except Exception as e:
        connector.log_debug(t("discord.log.err_conn", error=e))
        raise e

    if client.last_error:
        raise client.last_error

async def list_messages_action(connector: BaseConnector, token, channel_id, limit=10):
    connector.log_debug(t("discord.log.init_list", id=channel_id))
    intents = discord.Intents.default()
    intents.message_content = True
    intents.messages = True

    client = discord.Client(intents=intents)
    messages_data =[]

    @client.event
    async def on_ready():
        connector.log_debug(t("discord.log.connected", user=client.user))
        try:
            channel = await client.fetch_channel(int(channel_id))
            connector.log_debug(t("discord.log.reading", limit=limit))

            async for message in channel.history(limit=limit):
                messages_data.append(
                    t("discord.log.msg_format", author=message.author.name, date=message.created_at, content=message.content)
                )

            await client.close()
        except Exception as e:
            connector.log_debug(t("discord.log.err_read", error=e))
            client.last_error = e
            await client.close()

    client.last_error = None
    await client.start(token)

    if client.last_error:
        raise client.last_error

    return messages_data

def handle_discord_action(connector: BaseConnector, action: str, params: dict) -> str:
    guardian = Guardian()
    creds_config = guardian.get_credentials("discord_api")
    if not creds_config:
        raise ValueError(t("discord.auth_error"))

    bot_token = creds_config.get("bot_token")
    if not bot_token or "IL_TUO" in bot_token:
        raise ValueError(t("discord.auth_error"))

    channel_id = params.get("channel_id") or creds_config.get("channel_id")
    if not channel_id:
        raise ValueError(t("discord.channel_error"))

    avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")

    if action == "send_message":
        content = params.get("content")
        if not content:
            raise ValueError(t("discord.channel_error"))

        asyncio.run(send_message_action(connector, bot_token, channel_id, content))

        return ask_local_llm(
            data_to_analyze=t("discord.send_confirm", content=content),
            context_description=t("discord.context_send"),
            avatar_name=avatar_name,
        )

    elif action == "list_messages":
        limit = params.get("limit", 10)
        raw_messages = asyncio.run(list_messages_action(connector, bot_token, channel_id, limit))

        if not raw_messages:
            return t("discord.no_messages")
        
        raw_string = "\n".join(raw_messages)
        connector.log_debug(t("discord.log.triage"))
        return ask_local_llm(
            data_to_analyze=raw_string,
            context_description=t("discord.context_list", id=channel_id),
            avatar_name=avatar_name,
        )

if __name__ == "__main__":
    connector = BaseConnector(t("avatar_server.discord.cmd_desc"))
    connector.register_action("send_message", lambda params: handle_discord_action(connector, "send_message", params))
    connector.register_action("list_messages", lambda params: handle_discord_action(connector, "list_messages", params))
    connector.run()