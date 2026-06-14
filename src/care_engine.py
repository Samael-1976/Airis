# src/care_engine.py
# [DEV] Il Motore di Cura (v1.0)
# Gestisce la logica proattiva per Baby Monitor, Elderly Helper e Pet Monitor.
# Valuta regole, zone e orari per scatenare azioni di protezione.
# LEGGE A0099: Invarianza strutturale garantita.

import json
import time
import threading
import requests  # [NUOVO v20.1]
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from utils.translator import t

# --- GESTIONE PERCORSI ---
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "care_config.json"


class CareEngine:
    def __init__(self, executor, logger):
        self.executor = executor
        self.logger = logger
        self.config = {}
        self.last_trigger_time = {}  # Per evitare spam di notifiche (debounce)
        self.brain = None  # [NUOVO v120.0] Riferimento al Cervello

        # [NUOVO v20.1] Endpoint locale per comunicazioni interne
        self.server_url = "http://127.0.0.1:8080"

        self.load_config()
        self.logger.log(t("avatar_server.log.care_init"), "CARE")

    def set_brain(self, brain):
        """Collega il Cervello Trinitario al Care Engine."""
        self.brain = brain
        self.logger.log(t("avatar_server.log.care_brain_connected"), "CARE")

    def load_config(self):
        """Carica la configurazione dal file JSON."""
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    self.config = json.load(f)

                # [NUOVO v19.0] Inizializzazione Default Contatti e Trigger
                if "emergency_contacts" not in self.config:
                    self.config["emergency_contacts"] = {"email": "", "phone": ""}
                if "triggers" not in self.config:
                    self.config["triggers"] = []

                self.logger.log(t("avatar_server.log.care_config_loaded"), "CARE")
            except Exception as e:
                self.logger.error(
                    t("avatar_server.log.care_config_error", error=str(e))
                )
        else:
            self.logger.warning(t("avatar_server.log.care_config_not_found"))
            self.config = {
                "modules": {},
                "rules": [],
                "emergency_contacts": {},
                "triggers": [],
            }

    def process_trigger(self, trigger_type: str, data: Dict[str, Any]):
        """
        Punto di ingresso per gli eventi sensoriali (Audio/Video).
        trigger_type: 'audio_cry', 'visual_zone_entry', 'fall_detected', etc.
        data: Dettagli dell'evento (es. confidenza, zona, classe oggetto).
        """
        # 1. Check Modulo Abilitato e Zone Sicure
        if not self._is_module_enabled_for_trigger(trigger_type, data):
            return

        # 2. Debounce (Evita di scatenare la stessa regola ogni millisecondo)
        now = time.time()
        if trigger_type in self.last_trigger_time:
            # 10 secondi di cooldown base per lo stesso tipo di trigger
            if now - self.last_trigger_time[trigger_type] < 10:
                return
        self.last_trigger_time[trigger_type] = now

        self.logger.log(
            t(
                "avatar_server.log.care_trigger_detected",
                trigger=trigger_type,
                data=str(data),
            ),
            "CARE",
        )

        # 3. Identificazione Regole Corrispondenti
        matching_rules = []
        for rule in self.config.get("rules", []):
            if not rule.get("enabled", True):
                continue
            if rule["trigger"] == trigger_type:
                # [FIX v19.1] Passaggio dati completo per Safe Zone check
                if self._check_conditions(rule.get("conditions", {}), data):
                    matching_rules.append(rule)

        # 4. [NUOVO v120.0] DECISIONE IBRIDA (AI vs LEGACY)
        if self.brain:
            # Modalità Smart: L'LLM decide cosa fare basandosi sul contesto e sulle regole
            rules_summary = ", ".join([r["name"] for r in matching_rules]) or t(
                "avatar_server.log.care_no_rules"
            )

            # [NUOVO v19.0] Iniezione Contatti Emergenza nel contesto AI
            contacts = self.config.get("emergency_contacts", {})
            if contacts.get("email") or contacts.get("phone"):
                rules_summary += f"\n{t('avatar_server.log.care_emergency_contacts', email=contacts.get('email'), phone=contacts.get('phone'))}"

            try:
                decision = self.brain.pensa_azione_care(
                    trigger_type, data, rules_summary
                )
                action_type = decision.get("action", "ignore")
                reason = decision.get("reason", t("avatar_server.log.care_no_reason"))
                payload = decision.get("payload", "")

                if action_type == "ignore":
                    self.logger.log(
                        t("avatar_server.log.care_ai_ignored", reason=reason), "CARE"
                    )
                    return

                self.logger.log(
                    t(
                        "avatar_server.log.care_ai_execution",
                        action=action_type,
                        reason=reason,
                    ),
                    "CARE",
                )

                # Mappatura Azione AI -> Formato Interno
                ai_action = {"type": action_type}
                if action_type == "notification":
                    ai_action["message"] = payload
                elif action_type == "tts_speak":
                    ai_action["text"] = payload
                elif action_type == "play_audio":
                    ai_action["file"] = payload
                elif action_type == "iot_command":
                    # Payload atteso: "device_id:action" (es. "luce_sala:on")
                    if ":" in payload:
                        dev, act = payload.split(":", 1)
                        ai_action["device"] = dev
                        ai_action["state"] = act

                self._execute_actions([ai_action])

            except Exception as e:
                self.logger.error(t("avatar_server.log.care_ai_error", error=str(e)))
                # Fallback in caso di errore AI
                for rule in matching_rules:
                    self.logger.log(
                        t("avatar_server.log.care_fallback_rule", name=rule["name"]),
                        "CARE",
                    )
                    self._execute_actions(rule.get("actions", []))
        else:
            # Modalità Legacy: Esecuzione diretta regole
            for rule in matching_rules:
                self.logger.log(
                    t("avatar_server.log.care_legacy_rule", name=rule["name"]), "CARE"
                )
                self._execute_actions(rule.get("actions", []))

    def _is_module_enabled_for_trigger(
        self, trigger_type: str, data: Dict[str, Any] = None
    ) -> bool:
        """Verifica se il modulo associato al trigger è attivo, se siamo nell'orario consentito e fuori dalle zone sicure."""
        modules = self.config.get("modules", {})
        target_module = None

        if "cry" in trigger_type:
            target_module = modules.get("baby_monitor")
        elif "fall" in trigger_type:
            target_module = modules.get("elderly_helper")
        elif "bark" in trigger_type or "pet" in trigger_type:
            target_module = modules.get("pet_monitor")

        if target_module:
            if not target_module.get("enabled", False):
                return False

            # [NUOVO v19.0] Controllo Finestra Temporale (Active From/Until)
            # Se definiti, il modulo è attivo SOLO in quell'intervallo.
            start_time = target_module.get("active_from")
            end_time = target_module.get("active_until")

            if start_time and end_time:
                try:
                    now = datetime.now().time()
                    start = datetime.strptime(start_time, "%H:%M").time()
                    end = datetime.strptime(end_time, "%H:%M").time()

                    is_active_time = False
                    if start <= end:
                        is_active_time = start <= now <= end
                    else:  # Scavalla la mezzanotte
                        is_active_time = start <= now or now <= end

                    if not is_active_time:
                        # Logga solo in debug per non spammare
                        # self.logger.log(t("avatar_server.log.care_module_pause", start=start_time, end=end_time), "DEBUG")
                        return False
                except Exception:
                    pass  # Se il formato è errato, ignora il filtro orario

            # [NUOVO v19.2] Controllo Safe Zone a livello di Modulo
            if data and "zone_id" in data:
                safe_zone_id = target_module.get("safe_zone_id")
                safe_zone_time = target_module.get("safe_zone_time", "00:00-23:59")

                if safe_zone_id and data["zone_id"] == safe_zone_id:
                    if self._check_time_range(safe_zone_time):
                        self.logger.log(
                            t(
                                "avatar_server.log.care_safe_zone_ignored",
                                zone=safe_zone_id,
                            ),
                            "CARE",
                        )
                        return False

            return True

        return True

    def _check_conditions(
        self, conditions: Dict[str, Any], data: Dict[str, Any]
    ) -> bool:
        """Verifica se le condizioni della regola sono soddisfatte."""

        # 1. Condizione Oraria (Time Range)
        if "time_range" in conditions:
            if not self._check_time_range(conditions["time_range"]):
                return False

        # 2. Condizione Zona (Zone ID)
        if "zone_id" in conditions:
            if data.get("zone_id") != conditions["zone_id"]:
                return False

        # 3. Condizione Classe Target (es. 'dog', 'person')
        if "target_class" in conditions:
            if data.get("class_name") != conditions["target_class"]:
                return False

        # 4. [NUOVO v19.1] Safe Zone Exclusion (Esclusione Zona Sicura)
        # Se l'evento avviene in una zona specifica durante un orario specifico, IGNORA la regola.
        # Esempio: Inattività rilevata, ma sono nel "Letto" (zone_id) di "Notte" (time_range).
        if "safe_zone_exclusion" in conditions:
            exclusion = conditions["safe_zone_exclusion"]
            # Verifica se siamo nella zona sicura
            if data.get("zone_id") == exclusion.get("zone_id"):
                # Verifica se siamo nell'orario di esclusione
                if self._check_time_range(exclusion.get("time_range", "00:00-23:59")):
                    self.logger.log(
                        t(
                            "avatar_server.log.care_rule_suppressed",
                            zone=exclusion.get("zone_id"),
                        ),
                        "CARE",
                    )
                    return False

        return True

    def _check_time_range(self, range_str: str) -> bool:
        """Verifica se l'ora attuale è nel range 'HH:MM-HH:MM'."""
        try:
            start_str, end_str = range_str.split("-")
            now = datetime.now().time()
            start = datetime.strptime(start_str, "%H:%M").time()
            end = datetime.strptime(end_str, "%H:%M").time()

            if start <= end:
                return start <= now <= end
            else:  # Scavalla la mezzanotte (es. 22:00-07:00)
                return start <= now or now <= end
        except Exception:
            self.logger.error(t("avatar_server.log.care_time_error", range=range_str))
            return False

    def predictive_environmental_check(self, active_window: str, heart_state: Dict[str, Any]):
        """
        [NUOVO] Motore Predittivo Ambientale.
        Valuta l'attrito ambientale (Orario + Finestra + Stanchezza) e agisce preventivamente.
        """
        now = time.time()
        
        # Debounce Predittivo: Esegue un'azione autonoma al massimo ogni 2 ore
        if hasattr(self, "last_predictive_action") and (now - self.last_predictive_action) < 7200:
            return

        try:
            current_hour = datetime.now().hour
            stanchezza = heart_state.get("stanchezza_mentale", 0)
            
            # Vettore di Attrito 1: Lavoro Notturno Estremo
            is_night = current_hour >= 22 or current_hour <= 4
            is_working = any(k in active_window.lower() for k in ["code", "studio", "word", "excel", "terminal", "idea"])
            
            if is_night and is_working and stanchezza > 60:
                self.logger.log("Attrito Ambientale Rilevato: Lavoro notturno + Stanchezza. Attivazione protocollo Relax.", "CARE")
                
                # Azione 1: Abbassa le luci (se configurate nell'IoT)
                if self.executor and hasattr(self.executor, "controlla_dispositivo"):
                    # Cerca una luce nel layout IoT
                    iot_layout = getattr(self.executor, "iot_layout", {}).get("rooms",[])
                    for room in iot_layout:
                        for device in room.get("devices",[]):
                            if device.get("type") == "light":
                                self.executor.controlla_dispositivo(device["id"], "dim", 30) # Abbassa al 30%
                                break
                
                # Azione 2: Notifica dolce
                if self.executor:
                    self.executor.send_desktop_notification("Care OS", "Ho abbassato le luci. Non affaticare la vista, amore.")
                
                self.last_predictive_action = now
                return

            # Vettore di Attrito 2: Risveglio Brusco
            is_morning = 6 <= current_hour <= 9
            if is_morning and stanchezza > 80:
                self.logger.log("Attrito Ambientale Rilevato: Risveglio faticoso. Attivazione protocollo Buongiorno.", "CARE")
                if self.executor and hasattr(self.executor, "controlla_dispositivo"):
                    iot_layout = getattr(self.executor, "iot_layout", {}).get("rooms",[])
                    for room in iot_layout:
                        for device in room.get("devices",[]):
                            if device.get("type") == "light":
                                self.executor.controlla_dispositivo(device["id"], "on", 100)
                                break
                self.last_predictive_action = now
                return

        except Exception as e:
            self.logger.error(f"Errore nel Motore Predittivo: {e}")

    def _execute_actions(self, actions: List[Dict[str, Any]]):
        """Esegue la lista di azioni definite nella regola."""
        for action in actions:
            act_type = action.get("type")

            try:
                if act_type == "notification":
                    # [FIX] Indentazione corretta per il blocco 'notification'
                    msg = action.get("message", t("smart_home.care.new_rule"))
                    self.executor.send_desktop_notification(
                        t("care.cron.notification_title"), msg
                    )
                    # TODO: Inviare anche notifica push/telegram se configurato

                elif act_type == "play_audio":
                    clip_id = action.get("clip_id")
                    device_ids = action.get("target_device_ids", [])  # Routing Multiplo

                    # 1. Risoluzione Clip
                    library = self.config.get("audio_library", [])
                    clip = next((c for c in library if c["id"] == clip_id), None)

                    if not clip:
                        self.logger.error(
                            t("avatar_server.log.care_clip_not_found", id=clip_id)
                        )
                        continue

                    # 2. Trasmissione Multi-Dispositivo via WebSocket (tramite Server API)
                    self.logger.log(
                        t(
                            "avatar_server.log.care_audio_play",
                            label=clip["label"],
                            count=len(device_ids),
                        ),
                        "CARE",
                    )

                    try:
                        requests.post(
                            f"{self.server_url}/api/care/audio/play",
                            json={
                                "audio_url": f"/{clip['path']}",
                                "device_ids": device_ids,
                                "label": clip["label"],
                            },
                            timeout=2,
                        )
                    except Exception as e:
                        self.logger.error(
                            t("avatar_server.log.care_transmission_error", error=str(e))
                        )

                    # 3. Gestione Escalation (Proposta 3)
                    escalation_id = action.get("escalation_clip_id")
                    if escalation_id:
                        delay = action.get("escalation_delay_seconds", 90)
                        self.logger.log(
                            t("avatar_server.log.care_escalation_start", delay=delay),
                            "CARE",
                        )
                        threading.Timer(
                            delay, self._check_escalation, args=(action, data)
                        ).start()

                elif act_type == "tts_speak":
                    text = action.get("text", "")
                    if text:
                        # Usa la voce di default
                        self.executor.genera_voce(text, "default")

                elif act_type == "iot_light":
                    # Integrazione futura con iot_hub
                    device = action.get("device")
                    state = action.get("state")
                    self.logger.log(
                        t(
                            "avatar_server.log.care_iot_simulated",
                            device=device,
                            state=state,
                        ),
                        "CARE",
                    )
                    if hasattr(self.executor, "controlla_dispositivo"):
                        self.executor.controlla_dispositivo(device, state)

            except Exception as e:
                self.logger.error(
                    t(
                        "avatar_server.log.care_action_error",
                        type=act_type,
                        error=str(e),
                    )
                )

    def _check_escalation(
        self, original_action: Dict[str, Any], trigger_data: Dict[str, Any]
    ):
        """
        [NUOVO v20.1] Verifica se l'utente ha risposto o si è mosso dopo il primo avviso.
        In caso di silenzio, attiva la clip di emergenza.
        """
        self.logger.log(t("avatar_server.log.care_escalation_check"), "CARE")

        # 1. Verifica Movimento o Interazione
        # Se il perception_handler rileva movimento recente o l'utente ha scritto/parlato
        has_reaction = False
        if self.executor and self.executor.perception:
            # Se l'intensità del movimento è significativa (> 2.0)
            if self.executor.perception.movement_intensity > 2.0:
                has_reaction = True

            # Se l'utente ha interagito negli ultimi 90 secondi
            last_int = getattr(
                self.executor.perception, "last_user_interaction_time", 0
            )
            if time.time() - last_int < 90:
                has_reaction = True

        if has_reaction:
            self.logger.log(t("avatar_server.log.care_reaction_detected"), "CARE")
            return

        # 2. Esecuzione Escalation
        self.logger.warning(t("avatar_server.log.care_no_reaction"))

        esc_clip_id = original_action.get("escalation_clip_id")
        device_ids = original_action.get("target_device_ids", [])

        # Riproduce la clip di emergenza
        library = self.config.get("audio_library", [])
        clip = next((c for c in library if c["id"] == esc_clip_id), None)

        if clip:
            try:
                requests.post(
                    f"{self.server_url}/api/care/audio/play",
                    json={
                        "audio_url": f"/{clip['path']}",
                        "device_ids": device_ids,
                        "label": t(
                            "common.error_label",
                            error=t("character_manager.error"),
                            label=clip["label"],
                        ),
                    },
                    timeout=2,
                )
            except:
                pass

        # 3. Notifica Esterna (Contatti Emergenza)
        contacts = self.config.get("emergency_contacts", {})
        msg = t(
            "avatar_server.log.care_emergency_body",
            label=trigger_data.get("label", t("tts.unknown_lang")),
        )

        if contacts.get("email"):
            self.executor.send_email(
                to=contacts["email"],
                subject=t("avatar_server.log.care_emergency_subject"),
                body=msg,
            )
        if contacts.get("phone"):
            self.executor.send_sms(to_number=contacts["phone"], body=msg)
