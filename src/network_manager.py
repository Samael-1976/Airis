# src/network_manager.py
# [DEV] Il Centralino P2P (v1.0 - Multiplayer Network)
# Gestisce la Bacheca Firebase, il Registro Gilde e l'Heartbeat resiliente.
# LEGGE A0099: Invarianza strutturale garantita.

import requests
import threading
import time
import json
import re
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from utils.translator import t

# --- TRACKER PROPRIETARIO (Omnia Diffusion) ---
TRACKER_URL = "https://www.omnia-diffusion.com/airis_tracker/api.php"
PUBLIC_NETWORK_KEY = "Airis_Omnia_Network_Key_2026_v1"


class NetworkManager:
    def __init__(self, logger):
        self.logger = logger
        self.uid = self._get_or_create_uid()
        self.id_token = "legacy_bypass"
        self.heartbeat_thread = None
        self.is_heartbeat_active = False
        self.current_room_id = None
        self.headers = {
            "X-Airis-Key": PUBLIC_NETWORK_KEY,
            "Content-Type": "application/json",
        }

    def _get_or_create_uid(self) -> str:
        """Genera o recupera un UID persistente per il giocatore locale."""
        uid_file = Path("config/network_uid.txt")
        if uid_file.exists():
            return uid_file.read_text().strip()
        new_uid = uuid.uuid4().hex
        uid_file.parent.mkdir(exist_ok=True)
        uid_file.write_text(new_uid)
        return new_uid

    def login_anonimo(self) -> bool:
        """Bypassato: Il nuovo tracker usa l'autenticazione tramite Header."""
        return True

    def crea_stanza(
        self,
        room_id: str,
        host_nome: str,
        nome_locanda: str,
        titolo_avventura: str,
        descrizione_avventura: str,
        url_ngrok: str,
        max_giocatori: int = 10,
        lingua: str = "",
        women_only: bool = False,
        livello_minimo: int = 1,
        livello_massimo: int = 20,
        is_private: bool = False,
    ) -> bool:
        """Pubblica la stanza sulla bacheca del Tracker."""
        url = f"{TRACKER_URL}?path=stanze_attive/{room_id}.json"
        payload = {
            "host_nome": host_nome,
            "nome_locanda": nome_locanda,
            "titolo_avventura": titolo_avventura,
            "descrizione_avventura": descrizione_avventura,
            "url_ngrok": url_ngrok,
            "giocatori_attuali": 1,
            "max_giocatori": max_giocatori,
            "ultimo_ping": int(time.time()),
            "lingua": lingua,
            "women_only": women_only,
            "livello_minimo": livello_minimo,
            "livello_massimo": livello_massimo,
            "is_private": is_private,
        }

        try:
            response = requests.put(url, json=payload, headers=self.headers, timeout=10)
            if response.status_code == 200:
                self.current_room_id = room_id
                self.logger.log(
                    t("avatar_server.log.network_room_published", name=nome_locanda),
                    "NETWORK",
                )
                self.start_heartbeat(room_id)
                return True
            else:
                self.logger.error(
                    t(
                        "avatar_server.log.network_room_publish_error",
                        error=response.text,
                    )
                )
                return False
        except Exception as e:
            self.logger.error(
                t("avatar_server.log.network_room_create_error", error=str(e))
            )
            return False

    def cerca_stanze(self) -> Dict[str, Any]:
        """Recupera le stanze attive, filtrando quelle fantasma (ping > 3 minuti)."""
        url = f"{TRACKER_URL}?path=stanze_attive.json"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json() or {}
                stanze_valide = {}
                now = int(time.time())

                for r_id, r_data in data.items():
                    ultimo_ping = r_data.get("ultimo_ping", 0)
                    # Filtro Stanze Fantasma (180 secondi = 3 minuti)
                    if now - ultimo_ping <= 180:
                        stanze_valide[r_id] = r_data

                return stanze_valide
            return {}
        except Exception as e:
            self.logger.error(t("avatar_server.log.network_search_error", error=str(e)))
            return {}

    def start_heartbeat(self, room_id: str):
        """Avvia il thread resiliente per l'aggiornamento del timestamp."""
        if self.is_heartbeat_active:
            return
        self.is_heartbeat_active = True
        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop, args=(room_id,), daemon=True
        )
        self.heartbeat_thread.start()
        self.logger.log(t("avatar_server.log.network_heartbeat_start"), "NETWORK")

    def stop_heartbeat(self):
        """Ferma l'heartbeat e rimuove la stanza dal Tracker."""
        self.is_heartbeat_active = False
        if self.current_room_id:
            url = f"{TRACKER_URL}?path=stanze_attive/{self.current_room_id}.json"
            try:
                requests.delete(url, headers=self.headers, timeout=5)
                self.logger.log(t("avatar_server.log.network_room_removed"), "NETWORK")
            except:
                pass
        self.current_room_id = None

    def _heartbeat_loop(self, room_id: str):
        """Loop isolato e resiliente. Non crasherà mai il server principale."""
        while self.is_heartbeat_active:
            # [FIX CRITICO] Loop di attesa reattivo per permettere la chiusura immediata del thread
            for _ in range(60):
                if not self.is_heartbeat_active:
                    break
                time.sleep(1)

            if not self.is_heartbeat_active:
                break

            url = f"{TRACKER_URL}?path=stanze_attive/{room_id}/ultimo_ping.json"
            try:
                requests.put(
                    url, json=int(time.time()), headers=self.headers, timeout=5
                )
            except Exception as e:
                # Fallisce silenziosamente e riprova al ciclo successivo
                self.logger.warning(
                    t("avatar_server.log.network_heartbeat_failed", error=str(e))
                )

    # --- GESTIONE GILDE (MMORPG CORE) ---
    def crea_gilda(
        self,
        gilda_id: str,
        nome_gilda: str,
        capo_gilda_nome: str,
        simbolo_gilda: str = "",
        tags: str = "Casual",
        obiettivo: str = "",
    ) -> bool:
        url = f"{TRACKER_URL}?path=gilde/{gilda_id}.json"
        payload = {
            "nome_gilda": nome_gilda,
            "capo_gilda": self.uid,
            "sottocapi": {},
            "membri": {self.uid: capo_gilda_nome},
            "simbolo_gilda": simbolo_gilda,
            "tags": tags,
            "obiettivo": obiettivo,
            "richieste_pendenti": {},
            "bannati": {},
            "data_creazione": int(time.time()),
        }
        try:
            response = requests.put(url, json=payload, headers=self.headers, timeout=10)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(
                t("avatar_server.log.network_guild_sync_error", error=str(e))
            )
            return False

    def modifica_gilda(
        self,
        gilda_id: str,
        nome_gilda: str,
        simbolo_gilda: str,
        tags: str = "",
        obiettivo: str = "",
    ) -> bool:
        try:
            url = f"{TRACKER_URL}?path=gilde/{gilda_id}.json"
            payload = {
                "nome_gilda": nome_gilda,
                "simbolo_gilda": simbolo_gilda,
                "tags": tags,
                "obiettivo": obiettivo,
            }
            response = requests.patch(
                url, json=payload, headers=self.headers, timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            self.logger.error(
                t("avatar_server.log.network_guild_sync_error", error=str(e))
            )
            return False

    def elimina_gilda(self, gilda_id: str) -> bool:
        url = f"{TRACKER_URL}?path=gilde/{gilda_id}.json"
        try:
            response = requests.delete(url, headers=self.headers, timeout=10)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(
                t("avatar_server.log.network_guild_sync_error", error=str(e))
            )
            return False

    def abbandona_gilda(
        self, gilda_id: str, my_uid: str, nuovo_capo_uid: str = None
    ) -> bool:
        try:
            # Controlla se sono l'ultimo membro
            url_get = f"{TRACKER_URL}?path=gilde/{gilda_id}/membri.json"
            res = requests.get(url_get, timeout=5)
            membri = res.json() or {}

            if len(membri) <= 1 and my_uid in membri:
                # Auto-scioglimento
                self.logger.log(
                    t("avatar_server.log.network_guild_dissolved", id=gilda_id),
                    "NETWORK",
                )
                return self.elimina_gilda(gilda_id)

            # Rimuovi me stesso da membri e sottocapi
            requests.delete(
                f"{TRACKER_URL}?path=gilde/{gilda_id}/membri/{my_uid}.json",
                headers=self.headers,
                timeout=5,
            )
            requests.delete(
                f"{TRACKER_URL}?path=gilde/{gilda_id}/sottocapi/{my_uid}.json",
                headers=self.headers,
                timeout=5,
            )

            # Se c'è un nuovo capo, aggiorna capo_gilda
            if nuovo_capo_uid:
                url_capo = f"{TRACKER_URL}?path=gilde/{gilda_id}/capo_gilda.json"
                requests.put(
                    url_capo, json=nuovo_capo_uid, headers=self.headers, timeout=5
                )
            return True
        except Exception as e:
            self.logger.error(
                t("avatar_server.log.network_guild_sync_error", error=str(e))
            )
            return False

    def kick_gilda(self, gilda_id: str, target_uid: str) -> bool:
        try:
            requests.delete(
                f"{TRACKER_URL}?path=gilde/{gilda_id}/membri/{target_uid}.json",
                headers=self.headers,
                timeout=5,
            )
            requests.delete(
                f"{TRACKER_URL}?path=gilde/{gilda_id}/sottocapi/{target_uid}.json",
                headers=self.headers,
                timeout=5,
            )
            return True
        except Exception as e:
            self.logger.error(
                t("avatar_server.log.network_guild_sync_error", error=str(e))
            )
            return False

    # --- GESTIONE RUOLI E CANDIDATURE ---
    def promuovi_ufficiale(
        self, gilda_id: str, target_uid: str, target_nome: str
    ) -> bool:
        url = f"{TRACKER_URL}?path=gilde/{gilda_id}/sottocapi/{target_uid}.json"
        try:
            response = requests.put(
                url, json=target_nome, headers=self.headers, timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            self.logger.error(
                t("avatar_server.log.network_guild_sync_error", error=str(e))
            )
            return False

    def declassa_ufficiale(self, gilda_id: str, target_uid: str) -> bool:
        url = f"{TRACKER_URL}?path=gilde/{gilda_id}/sottocapi/{target_uid}.json"
        try:
            response = requests.delete(url, headers=self.headers, timeout=5)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(
                t("avatar_server.log.network_guild_sync_error", error=str(e))
            )
            return False

    def candidati_gilda(
        self,
        gilda_id: str,
        my_uid: str,
        my_name: str,
        lettera: str,
        livello: int,
        classe: str,
    ) -> bool:
        # Controllo Ban (7 giorni)
        url_ban = f"{TRACKER_URL}?path=gilde/{gilda_id}/bannati/{my_uid}.json"
        try:
            res_ban = requests.get(url_ban, timeout=5)
            ban_timestamp = res_ban.json()
            if ban_timestamp:
                if int(time.time()) - ban_timestamp < (7 * 24 * 3600):
                    self.logger.warning(
                        t("avatar_server.log.network_candidacy_rejected_ban")
                    )
                    return False
                else:
                    # Ban scaduto, rimuovilo
                    requests.delete(url_ban, headers=self.headers, timeout=5)
        except Exception as e:
            self.logger.error(
                t("avatar_server.log.network_guild_sync_error", error=str(e))
            )

        url = f"{TRACKER_URL}?path=gilde/{gilda_id}/richieste_pendenti/{my_uid}.json"
        payload = {
            "nome": my_name,
            "lettera": lettera,
            "livello": livello,
            "classe": classe,
            "timestamp": int(time.time()),
        }
        try:
            response = requests.put(url, json=payload, headers=self.headers, timeout=10)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(
                t("avatar_server.log.network_guild_sync_error", error=str(e))
            )
            return False

    def accetta_candidatura(
        self, gilda_id: str, target_uid: str, target_nome: str
    ) -> bool:
        try:
            url_membri = f"{TRACKER_URL}?path=gilde/{gilda_id}/membri/{target_uid}.json"
            requests.put(url_membri, json=target_nome, headers=self.headers, timeout=5)

            url_req = f"{TRACKER_URL}?path=gilde/{gilda_id}/richieste_pendenti/{target_uid}.json"
            requests.delete(url_req, headers=self.headers, timeout=5)
            return True
        except Exception as e:
            self.logger.error(
                t("avatar_server.log.network_guild_sync_error", error=str(e))
            )
            return False

    def rifiuta_candidatura(self, gilda_id: str, target_uid: str) -> bool:
        try:
            url_ban = f"{TRACKER_URL}?path=gilde/{gilda_id}/bannati/{target_uid}.json"
            requests.put(
                url_ban, json=int(time.time()), headers=self.headers, timeout=5
            )

            url_req = f"{TRACKER_URL}?path=gilde/{gilda_id}/richieste_pendenti/{target_uid}.json"
            requests.delete(url_req, headers=self.headers, timeout=5)
            return True
        except Exception as e:
            self.logger.error(
                t("avatar_server.log.network_guild_sync_error", error=str(e))
            )
            return False

    # --- LFG BOARD (LOOKING FOR GROUP) ---
    def pubblica_lfg(
        self, lfg_id: str, nome_pg: str, classe: str, livello: int, nota: str
    ) -> bool:
        url = f"{TRACKER_URL}?path=lfg_board/{lfg_id}.json"
        payload = {
            "nome_pg": nome_pg,
            "classe": classe,
            "livello": livello,
            "nota": nota,
            "timestamp": int(time.time()),
        }
        try:
            response = requests.put(url, json=payload, headers=self.headers, timeout=10)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(
                t("avatar_server.log.network_lfg_sync_error", error=str(e))
            )
            return False

    def rimuovi_lfg(self, lfg_id: str) -> bool:
        url = f"{TRACKER_URL}?path=lfg_board/{lfg_id}.json"
        try:
            response = requests.delete(url, headers=self.headers, timeout=10)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(
                t("avatar_server.log.network_lfg_sync_error", error=str(e))
            )
            return False
