# src/engine/mcp_client.py
# [DEV] MCP Client Manager (v1.0 - Universal Tool Assimilation)
# Gestisce le connessioni ai server MCP esterni (stdio/sse) e l'assimilazione dei tool.
# LEGGE A0099: Invarianza strutturale garantita.

import asyncio
import threading
import os
import sys
import json
import time
import logging
import subprocess
import socket
from pathlib import Path
from typing import List, Dict, Any
from contextlib import AsyncExitStack
from utils.translator import t

# --- [FIX CRITICO] SILENZIAMENTO SPAM PYDANTIC MCP ---
# Impedisce alla libreria MCP di spammare "Received exception from stream" 
# quando un server esterno (es. Graphify) invia dati sporchi o si disconnette.
logging.getLogger("mcp").setLevel(logging.CRITICAL)

try:
    # [FIX GOD MODE 3.2] Import espliciti per evitare conflitti di namespace nelle varie versioni dell'SDK
    from mcp.client.session import ClientSession
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp.client.sse import sse_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

class McpManager:
    def __init__(self, guardian, logger, send_toast_callback=None):
        self.guardian = guardian
        self.logger = logger
        self.send_toast = send_toast_callback
        self.servers: Dict[str, ClientSession] = {}
        self._exit_stack = AsyncExitStack()
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._ready_event = threading.Event()
        self.tools_cache: List[Dict[str, Any]] =[]
        self.is_running = False
        
        # --- [NUOVO FASE 3.2] WATCHDOG MCP ---
        self.manifests_dir = Path("config/mcp_manifests")
        self.manifests_dir.mkdir(parents=True, exist_ok=True)
        self.known_manifests = set(os.listdir(self.manifests_dir)) if self.manifests_dir.exists() else set()
        self.watchdog_active = True
        self._watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self._watchdog_thread.start()

    def _watchdog_loop(self):
        """Monitora la cartella mcp_manifests per auto-discovery di nuovi server."""
        while self.watchdog_active:
            try:
                if not self.manifests_dir.exists():
                    time.sleep(5)
                    continue
                    
                current_files = set(f for f in os.listdir(self.manifests_dir) if f.endswith('.json'))
                new_files = current_files - self.known_manifests
                
                if new_files:
                    for file in new_files:
                        file_path = self.manifests_dir / file
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                manifest_data = json.load(f)
                            
                            # Valida e aggiungi
                            if "name" in manifest_data and "transport" in manifest_data:
                                servers = self.guardian.get_mcp_servers()
                                # Evita duplicati
                                if not any(s.get("name") == manifest_data["name"] for s in servers):
                                    manifest_data["id"] = f"mcp_{int(time.time())}"
                                    manifest_data["enabled"] = True
                                    servers.append(manifest_data)
                                    self.guardian.save_mcp_servers(servers)
                                    
                                    self.logger.log(t("mcp.new_server_detected", name=manifest_data["name"]), "SYSTEM")
                                    if self.send_toast:
                                        self.send_toast(t("mcp.new_power_acquired", name=manifest_data["name"]), "success")
                                    
                                    # Ricarica a caldo in modo thread-safe
                                    self._loop.call_soon_threadsafe(self.reload)
                        except Exception as e:
                            self.logger.error(f"Errore lettura manifest MCP {file}: {e}")
                            
                    self.known_manifests = current_files
            except Exception:
                pass
            time.sleep(5)

    def _run_loop(self):
        """Esegue l'event loop asincrono nel thread dedicato."""
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._async_setup())
        self._ready_event.set()
        if self.is_running:
            self._loop.run_forever()

    async def _connect_server(self, config: Dict[str, Any]):
        """Stabilisce la connessione STDIO o SSE con un singolo server."""
        name = config["name"]
        transport = config.get("transport", "stdio")
        
        if transport == "stdio":
            # Parsing sicuro degli argomenti
            args = config.get("args",[])
            if isinstance(args, str):
                import shlex
                args = shlex.split(args)
                
            server_params = StdioServerParameters(
                command=config["command"],
                args=args,
                env=None
            )
            stdio_transport = await self._exit_stack.enter_async_context(stdio_client(server_params))
            read, write = stdio_transport
        else:
            url = config.get("url")
            if not url:
                raise ValueError("URL missing for SSE transport")
            
            # --- [FIX CRITICO] RETRY LOOP PER SERVER SSE (es. Graphify) ---
            # I server esterni avviati in background potrebbero impiegare secondi ad aprire la porta.
            max_retries = 15
            sse_transport = None
            for attempt in range(max_retries):
                try:
                    sse_transport = await self._exit_stack.enter_async_context(sse_client(url))
                    break
                except BaseException as e: # Cattura ExceptionGroup di anyio
                    if attempt == max_retries - 1:
                        raise e
                    err_msg = str(e)
                    if hasattr(e, 'exceptions'):
                        err_msg = " | ".join([type(sub).__name__ for sub in e.exceptions])
                    self.logger.log(t("mcp.server_waiting", name=name, attempt=attempt+1, max=max_retries) + f" [{err_msg}]", "SYSTEM")
                    await asyncio.sleep(2)
                    
            read, write = sse_transport

        session = await self._exit_stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        self.servers[name] = session
        self.logger.log(t("mcp.server_connected", name=name), "SYSTEM")

    async def _refresh_tools_cache(self):
        """Interroga i server connessi per assimilare i loro tool."""
        self.tools_cache =[]
        for name, session in self.servers.items():
            try:
                tools_response = await session.list_tools()
                for tool in tools_response.tools:
                    # Converte il tool MCP nel formato JSON Schema di Airis
                    safe_name = f"mcp_{name.lower().replace(' ', '_')}_{tool.name}"
                    self.tools_cache.append({
                        "name": safe_name,
                        "description": tool.description or f"MCP Tool from {name}",
                        "parameters": tool.inputSchema,
                        "category": "mcp_tool",
                        "_mcp_server": name,
                        "_mcp_tool": tool.name
                    })
                self.logger.log(t("mcp.tools_assimilated", name=name, count=len(tools_response.tools)), "SYSTEM")
            except Exception as e:
                self.logger.error(t("mcp.tool_fetch_error", name=name, error=str(e)))

    async def _async_setup(self):
        """Inizializza le connessioni a tutti i server MCP configurati."""
        if not MCP_AVAILABLE:
            self.logger.warning(t("mcp.lib_missing"))
            return

        configs = self.guardian.get_mcp_servers()
        for config in configs:
            if not config.get("enabled", True):
                continue
            try:
                await self._connect_server(config)
            except BaseException as e: # [FIX CRITICO] Cattura ExceptionGroup di anyio
                err_msg = str(e)
                if hasattr(e, 'exceptions'):
                    err_msg = " | ".join([f"{type(sub).__name__}: {str(sub)}" for sub in e.exceptions])
                self.logger.error(t("mcp.conn_error", name=config.get('name', 'Unknown'), error=err_msg))
        
        await self._refresh_tools_cache()

    def start(self):
        """Avvia il manager e attende che le connessioni siano stabilite."""
        if not MCP_AVAILABLE:
            return
        self.is_running = True
        self._thread.start()
        self._ready_event.wait(timeout=15)

    def stop(self):
        """Chiude tutte le connessioni e ferma il loop."""
        if not self.is_running:
            return
        self.is_running = False
            
        if self._loop.is_running():
            try:
                # [FIX CRITICO] Attendiamo che la chiusura delle connessioni (aclose) 
                # sia completata prima di fermare brutalmente il loop.
                # Questo previene l'errore "Task was destroyed but it is pending".
                future = asyncio.run_coroutine_threadsafe(self._exit_stack.aclose(), self._loop)
                future.result(timeout=5.0)
            except Exception as e:
                self.logger.error(f"Errore durante la chiusura delle connessioni MCP: {e}")
            finally:
                self._loop.call_soon_threadsafe(self._loop.stop)
                
        if self._thread.is_alive():
            self._thread.join(timeout=5)
            
        if self._loop.is_running():
            try:
                # [FIX CRITICO] Attendiamo che la chiusura delle connessioni (aclose) 
                # sia completata prima di fermare brutalmente il loop.
                # Questo previene l'errore "Task was destroyed but it is pending".
                future = asyncio.run_coroutine_threadsafe(self._exit_stack.aclose(), self._loop)
                future.result(timeout=5.0)
            except Exception as e:
                self.logger.error(f"Errore durante la chiusura delle connessioni MCP: {e}")
            finally:
                self._loop.call_soon_threadsafe(self._loop.stop)
                
        if self._thread.is_alive():
            self._thread.join(timeout=5)

    def reload(self):
        """Riavvia il manager per applicare nuove configurazioni (Hot-Reload)."""
        self.logger.log(t("mcp.reloading"), "SYSTEM")
        self.stop()
        self.servers.clear()
        self.tools_cache.clear()
        self._exit_stack = AsyncExitStack()
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._ready_event = threading.Event()
        self.start()

    def get_tools(self) -> List[Dict[str, Any]]:
        """Restituisce la lista dei tool assimilati per l'Executor."""
        return self.tools_cache

    def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> str:
        """Esegue un tool MCP in modo sincrono (bloccante per il Demiurgo)."""
        if not MCP_AVAILABLE:
            return "ERROR: MCP library not installed."
        
        future = asyncio.run_coroutine_threadsafe(
            self._async_call_tool(server_name, tool_name, arguments), 
            self._loop
        )
        try:
            return future.result(timeout=600) # I tool MCP possono essere lenti (es. query DB)
        except Exception as e:
            return f"ERROR: MCP Tool execution timeout or failure: {e}"

    async def _async_call_tool(self, server_name: str, tool_name: str, arguments: dict) -> str:
        """Esecuzione asincrona effettiva del tool."""
        if server_name not in self.servers:
            return f"ERROR: MCP Server '{server_name}' not connected."
        
        session = self.servers[server_name]
        try:
            # Assicuriamoci che arguments sia un dict pulito per evitare JSONRPCError
            safe_args = arguments if isinstance(arguments, dict) else {}
            result = await session.call_tool(tool_name, arguments=safe_args)
            
            output =[]
            for content in result.content:
                if content.type == "text":
                    output.append(content.text)
                else:
                    output.append(f"[{content.type} content]")
                    
            final_output = "\n".join(output)
            
            # --- [FIX GOD MODE 4.A] TRUNCATION SHIELD ---
            # Previene l'esplosione della Context Window (n_ctx) se il server MCP restituisce dump enormi
            if len(final_output) > 4000:
                final_output = final_output[:4000] + "\n...[TRONCATO DAL SERVER MCP PER SUPERAMENTO LIMITE CONTESTO]"
                
            if result.isError:
                return f"ERRORE MCP: {final_output}"
            return final_output
        except BaseException as e: # [FIX CRITICO] Cattura ExceptionGroup di anyio
            err_msg = str(e)
            if hasattr(e, 'exceptions'):
                err_msg = " | ".join([f"{type(sub).__name__}: {str(sub)}" for sub in e.exceptions])
            return f"ERRORE MCP: {err_msg}"