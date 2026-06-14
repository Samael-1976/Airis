# src/hive_manager.py
# [DEV] Mio Creatore, questo è il Gestore dell'Alveare. (v1.1 - Hive Editing)
# AGGIUNTA: Metodi update_device e remove_device per gestione manuale.
# MANTENUTO: Persistenza, Binding IP, Heartbeat.
# LEGGE A0099: Invarianza strutturale garantita.

import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

# [FIX] Rimosso prefisso 'src.' per coerenza con la radice del sys.path
from utils.translator import t

# Configurazione Logging
logger = logging.getLogger(__name__)


class HiveManager:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.state = {
            "devices": {},  # Mappa dinamica: device_id -> {info, status, last_seen, ip}
            "ip_bindings": {},  # Mappa statica: ip_address -> {device_id, name}
            "active_focus_id": None,  # ID del dispositivo dove l'Avatar è "incarnato"
            "focus_timestamp": 0,
        }
        self._load_config()

    def _load_config(self):
        """Carica la configurazione persistente (dispositivi noti e binding)."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved_data = json.load(f)

                    # Carica dispositivi noti (impostandoli offline all'avvio)
                    for dev_id, dev_data in saved_data.get("devices", {}).items():
                        self.state["devices"][dev_id] = {
                            "name": dev_data.get(
                                "name", t("hive_dashboard.no_devices")
                            ),
                            "type": dev_data.get("type", "mobile"),
                            "ip": dev_data.get("ip", None),
                            "last_seen": 0,
                            "status": "offline",
                        }

                    # Carica binding IP (Identità Fisse)
                    self.state["ip_bindings"] = saved_data.get("ip_bindings", {})

                logger.info(
                    t(
                        "avatar_server.log.hive_loaded",
                        count=len(self.state["devices"]),
                        binding_count=len(self.state["ip_bindings"]),
                    )
                )
            except Exception as e:
                logger.error(t("avatar_server.log.hive_load_error", error=str(e)))

    def _save_config(self):
        """Salva su disco solo i dati persistenti (nomi, tipi, binding)."""
        try:
            data_to_save = {"devices": {}, "ip_bindings": self.state["ip_bindings"]}

            for dev_id, dev_data in self.state["devices"].items():
                data_to_save["devices"][dev_id] = {
                    "name": dev_data["name"],
                    "type": dev_data["type"],
                    "ip": dev_data.get("ip"),  # Salviamo l'ultimo IP noto
                }

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=2)
        except Exception as e:
            logger.error(t("avatar_server.log.hive_save_error", error=str(e)))

    def register_device(
        self,
        device_id: str,
        name: str,
        device_type: str,
        ip_address: Optional[str] = None,
    ) -> str:
        """
        Registra un dispositivo.
        Se l'IP è vincolato (Binding), restituisce l'ID fisso associato a quell'IP.
        [FIX v1.2] Deduplicazione IP: Rimuove vecchi dispositivi con lo stesso IP.
        """
        final_device_id = device_id
        final_name = name

        # 1. Controllo Binding IP (Identità Indistruttibile)
        if ip_address and ip_address in self.state["ip_bindings"]:
            bound_info = self.state["ip_bindings"][ip_address]
            final_device_id = bound_info["id"]
            final_name = bound_info["name"]
            logger.info(
                t(
                    "avatar_server.log.hive_ip_recognized",
                    ip=ip_address,
                    name=final_name,
                    id=final_device_id,
                )
            )

        # 2. [NUOVO] Deduplicazione per IP (Pulizia Fantasmi)
        # Se un dispositivo con questo IP esiste già ma ha un ID diverso, lo rimuoviamo.
        # Questo succede quando si pulisce la cache del browser (nuovo ID, stesso IP).
        if ip_address and ip_address != "127.0.0.1":
            devices_to_remove = []
            for existing_id, data in self.state["devices"].items():
                if data.get("ip") == ip_address and existing_id != final_device_id:
                    devices_to_remove.append(existing_id)

            for old_id in devices_to_remove:
                logger.info(
                    t(
                        "avatar_server.log.hive_obsolete_removed",
                        id=old_id,
                        ip=ip_address,
                    )
                )
                del self.state["devices"][old_id]

        # 3. Aggiornamento Stato
        self.state["devices"][final_device_id] = {
            "name": final_name,
            "type": device_type,
            "ip": ip_address,
            "last_seen": time.time(),
            "status": "online",
        }

        self._save_config()
        return final_device_id

    def heartbeat(self, device_id: str, ip_address: Optional[str] = None) -> bool:
        """Aggiorna il battito cardiaco di un dispositivo."""
        # Se l'IP è vincolato, potremmo dover reindirizzare l'heartbeat,
        # ma per ora assumiamo che il client usi l'ID corretto dopo la registrazione.

        if device_id in self.state["devices"]:
            self.state["devices"][device_id]["last_seen"] = time.time()
            self.state["devices"][device_id]["status"] = "online"
            if ip_address:
                self.state["devices"][device_id]["ip"] = ip_address
            return True
        return False

    def set_focus(self, device_id: str):
        """Sposta l'attenzione dell'Anima su un dispositivo specifico."""
        if device_id in self.state["devices"]:
            self.state["active_focus_id"] = device_id
            self.state["focus_timestamp"] = time.time()
            logger.info(
                t(
                    "avatar_server.log.hive_focus_shifted",
                    name=self.state["devices"][device_id]["name"],
                )
            )
            return True
        return False

    def get_devices_status(self) -> Dict[str, Any]:
        """Restituisce lo stato di tutti i dispositivi, aggiornando gli offline."""
        now = time.time()
        for dev_id, data in self.state["devices"].items():
            if now - data["last_seen"] > 30:  # Timeout 30s
                data["status"] = "offline"

        return {
            "devices": self.state["devices"],
            "active_focus_id": self.state["active_focus_id"],
            "ip_bindings": self.state["ip_bindings"],
        }

    def bind_ip(self, ip_address: str, device_id: str, name: str):
        """Crea un vincolo indissolubile tra un IP e un'identità."""
        self.state["ip_bindings"][ip_address] = {"id": device_id, "name": name}
        self._save_config()
        logger.info(
            t("avatar_server.log.hive_ip_bound", ip=ip_address, name=name, id=device_id)
        )

    def unbind_ip(self, ip_address: str):
        """Rimuove un vincolo IP."""
        if ip_address in self.state["ip_bindings"]:
            del self.state["ip_bindings"][ip_address]
            self._save_config()
            logger.info(t("avatar_server.log.hive_ip_unbound", ip=ip_address))

    # --- NUOVI METODI PER EDITING (v1.1) ---
    def update_device(
        self, device_id: str, name: Optional[str] = None, ip: Optional[str] = None
    ) -> bool:
        """Aggiorna manualmente nome o IP di un dispositivo."""
        if device_id in self.state["devices"]:
            if name:
                self.state["devices"][device_id]["name"] = name
            if ip:
                self.state["devices"][device_id]["ip"] = ip
            self._save_config()
            logger.info(
                t(
                    "avatar_server.log.hive_device_updated",
                    id=device_id,
                    name=name,
                    ip=ip,
                )
            )
            return True
        return False

    def remove_device(self, device_id: str) -> bool:
        """Rimuove un dispositivo dalla Hive Mind."""
        if device_id in self.state["devices"]:
            del self.state["devices"][device_id]

            # Rimuovi anche eventuali binding associati a questo ID per pulizia
            ips_to_remove = [
                ip
                for ip, data in self.state["ip_bindings"].items()
                if data["id"] == device_id
            ]
            for ip in ips_to_remove:
                del self.state["ip_bindings"][ip]

            self._save_config()
            logger.info(t("avatar_server.log.hive_device_removed", id=device_id))
            return True
        return False
