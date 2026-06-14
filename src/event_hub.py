# src/event_hub.py
# [DEV] Il Centralino dell'Alveare (v1.0 - Progetto Jarvis)
# Gestisce il paradigma Push: riceve eventi dai sensori, accumula dati silenti (Shadow Learning)
# e decide se svegliare il Regista in base alla Prudenza.
# LEGGE A0099: Invarianza strutturale garantita.

import time
import threading
import json
from pathlib import Path
from typing import Dict, Any, Callable, List, Optional
from utils.translator import t


class EventHub:
    def __init__(
        self,
        logger,
        cervello,
        heart,
        memory,
        action_callback: Callable[[str, str], None],
        is_gdr_active_callback: Callable[[], bool] = None,
        get_pg_name_callback: Callable[[], str] = None,
    ):
        self.logger = logger
        self.cervello = cervello
        self.heart = heart
        self.memory = memory
        self.action_callback = (
            action_callback  # Callback per far parlare l'Anima (es. execute_action)
        )
        self.is_gdr_active_callback = (
            is_gdr_active_callback  # [NUOVO] Callback per sapere se siamo in GDR
        )
        self.get_pg_name_callback = get_pg_name_callback

        # Buffer per lo Shadow Learning (Dati raccolti passivamente)
        self.shadow_buffer: List[str] = []
        self.buffer_lock = threading.Lock()

        self.last_user_interaction = time.time()
        self.is_processing = False

        # --- [NUOVO v18.1] CONFIGURAZIONE JARVIS (BLACKLIST) ---
        self.jarvis_config_path = Path("data/jarvis_config.json")
        self.blacklist_windows: List[str] = []
        self._load_config()

        self.logger.log(t("log.hub_init"), "HUB")

    def _load_config(self):
        """Carica la configurazione di Jarvis (es. Blacklist)."""
        if self.jarvis_config_path.exists():
            try:
                with open(self.jarvis_config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.blacklist_windows = data.get("blacklist_windows", [])
            except Exception as e:
                self.logger.error(t("log.hub_load_error", error=e))

    def _save_config(self):
        """Salva la configurazione di Jarvis."""
        try:
            self.jarvis_config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.jarvis_config_path, "w", encoding="utf-8") as f:
                json.dump({"blacklist_windows": self.blacklist_windows}, f, indent=2)
        except Exception as e:
            self.logger.error(t("log.hub_save_error", error=e))

    def register_user_interaction(self):
        """Congela i processi proattivi se l'utente sta interagendo."""
        self.last_user_interaction = time.time()

    def push_event(self, source: str, event_type: str, data: Dict[str, Any]):
        """
        Punto di ingresso per il paradigma Push. I dispositivi chiamano questo metodo.
        event_type: 'shadow_data', 'environmental_trigger', 'hardware_alert'
        """
        if event_type == "shadow_data":
            self._handle_shadow_data(data)
        elif event_type == "environmental_trigger":
            self._handle_environmental_trigger(source, data)
        elif event_type == "hardware_alert":
            self._handle_hardware_alert(data)
        else:
            self.logger.log(
                t("log.hub_unknown_event", type=event_type, source=source), "WARNING"
            )

    def _handle_shadow_data(self, data: Dict[str, Any]):
        """Accumula dati in modo silente per lo studio notturno."""
        text = data.get("text", "")
        window = data.get("window", "")

        # --- [NUOVO v18.1] FILTRO BLACKLIST ---
        if window:
            window_lower = window.lower()
            for blacklisted in self.blacklist_windows:
                if blacklisted.lower() in window_lower:
                    # Ignora silenziosamente questa finestra
                    return

        if text or window:
            with self.buffer_lock:
                entry = t(
                    "log.hub_shadow_entry",
                    time=time.strftime("%H:%M"),
                    window=window,
                    text=text[:300],
                )
                self.shadow_buffer.append(entry)
                # Mantiene il buffer leggero (ultimi 100 eventi)
                if len(self.shadow_buffer) > 100:
                    self.shadow_buffer.pop(0)

                # ---[NUOVO v18.2] PERSISTENZA PER API ---
                try:
                    Path("data").mkdir(
                        exist_ok=True
                    )  # [FIX CRITICO] Previene FileNotFoundError
                    with open("data/shadow_buffer.json", "w", encoding="utf-8") as f:
                        json.dump(self.shadow_buffer, f, indent=2)
                except Exception:
                    pass

    def _handle_environmental_trigger(self, source: str, data: Dict[str, Any]):
        """Valuta se intervenire in base a un evento ambientale (es. movimento, cambio stanza)."""
        # --- [NUOVO] BLOCCO GDR ---
        # Se siamo in GDR, l'EventHub è cieco e sordo per non interrompere la narrazione.
        if self.is_gdr_active_callback and self.is_gdr_active_callback():
            return

        # Se l'utente ha appena interagito, non disturbare (Priorità Utente)
        # [FIX CRITICO ANTI-FLOOD] Aumentato da 60 a 600 secondi (10 minuti) per allinearsi al resto del sistema
        if time.time() - self.last_user_interaction < 600:
            return

        if self.is_processing:
            return

        prudenza = self.heart.state.get("prudenza", 50)

        # Se la prudenza è altissima (>80), ignoriamo eventi minori
        if prudenza > 80 and data.get("severity", "low") == "low":
            self.logger.log(
                t("log.hub_ignored_prudence", source=source, prudenza=prudenza), "HUB"
            )
            return

        self.is_processing = True
        threading.Thread(
            target=self._evaluate_and_act, args=(source, data, prudenza), daemon=True
        ).start()

    def _handle_hardware_alert(self, data: Dict[str, Any]):
        """Gestisce gli allarmi hardware aggiornando l'umore e valutando interventi."""
        # --- [NUOVO] BLOCCO GDR ---
        if self.is_gdr_active_callback and self.is_gdr_active_callback():
            return

        cpu = data.get("cpu", 0)
        ram = data.get("ram", 0)

        # Aggiorna l'Hardware Mood nel Cuore
        if hasattr(self.heart, "update_hardware_mood"):
            self.heart.update_hardware_mood(cpu, ram)

        # [FIX CRITICO] Rimossa iniezione di Cortisolo da stress hardware.
        # Il cortisolo ora sale solo tramite l'audit emotivo della chat.

        # Se la situazione è critica, forza un intervento
        if cpu > 95 or ram > 95:
            if (
                time.time() - self.last_user_interaction > 300
                and not self.is_processing
            ):
                self.is_processing = True
                threading.Thread(
                    target=self._evaluate_and_act,
                    args=(
                        "system",
                        {"event": "critical_hardware", "cpu": cpu, "ram": ram},
                        0,
                    ),
                    daemon=True,
                ).start()

    def _evaluate_and_act(self, source: str, data: Dict[str, Any], prudenza: int):
        """Invoca il Regista (12B) per decidere se e come intervenire."""
        try:
            self.logger.log(t("log.hub_awakening", source=source), "HUB")

            # Prepariamo il contesto per il Regista
            current_time = time.strftime("%H:%M")
            inactivity_minutes = int((time.time() - self.last_user_interaction) / 60)

            # Estraiamo l'ultima finestra nota dal buffer ombra se disponibile
            active_window = t("log.hub_unknown_f")
            with self.buffer_lock:
                if self.shadow_buffer:
                    # Cerca l'ultima entry con una finestra
                    for entry in reversed(self.shadow_buffer):
                        if t("log.hub_window_split") in entry:
                            active_window = entry.split(t("log.hub_window_split"))[
                                1
                            ].split(" |")[0]
                            break

            # --- [NUOVO] HARD-BLOCK FINESTRA ATTIVA (PYTHON LEVEL) ---
            # Se la finestra attiva è la chat di Airis, blocchiamo l'intervento alla radice.
            # L'LLM non viene nemmeno interpellato, risparmiando token ed evitando allucinazioni.
            window_lower = active_window.lower()
            if any(
                k in window_lower for k in ["airis", "chat", "localhost", "127.0.0.1"]
            ):
                self.logger.log(t("log.hub_hard_block"), "HUB")
                return

            # Chiamata al Regista (il metodo verrà aggiornato in brain_llm.py)
            heart_status = self.heart.get_heart_status() if self.heart else "Neutro"
            
            # --- [FIX CRITICO] RISOLUZIONE NOME PG ---
            actual_pg_name = self.get_pg_name_callback() if self.get_pg_name_callback else "{{nome_pg}}"
            
            decision = self.cervello.pensa_intervento_proattivo(
                current_time=current_time,
                active_window=active_window,
                inactivity_minutes=inactivity_minutes,
                user_name=actual_pg_name,  # Nome reale risolto
                heart_status=heart_status,
                lang="it",
                event_data=data,
                prudenza=prudenza,
            )

            if decision.get("should_intervene") and decision.get("message"):
                msg = decision.get("message")
                self.logger.log(t("log.hub_decision", msg=msg), "HUB")
                # Invia l'azione a chat.py tramite la callback
                # Usiamo un intent neutro/proattivo di default
                self.action_callback(msg, t("log.hub_proactive_tag"))
            else:
                self.logger.log(t("log.hub_silence"), "HUB")

        except Exception as e:
            self.logger.error(t("log.hub_eval_error", error=e))
        finally:
            self.is_processing = False

    def process_shadow_buffer(self) -> Optional[str]:
        """
        Estrae i dati accumulati e li invia al Regista per estrarre i topic di studio.
        Restituisce i topic estratti o None.
        """
        with self.buffer_lock:
            if not self.shadow_buffer:
                return None
            buffer_copy = list(self.shadow_buffer)
            self.shadow_buffer.clear()

            # --- [FIX v18.2] SINCRONIZZAZIONE JSON POST-CLEAR ---
            try:
                Path("data").mkdir(
                    exist_ok=True
                )  # [FIX CRITICO] Previene FileNotFoundError
                with open("data/shadow_buffer.json", "w", encoding="utf-8") as f:
                    json.dump(self.shadow_buffer, f, indent=2)
            except Exception:
                pass

        self.logger.log(t("log.hub_shadow_analysis", count=len(buffer_copy)), "HUB")

        try:
            # Uniamo i frammenti in un unico testo
            raw_text = "\n".join(buffer_copy)

            # Chiamiamo il Regista per estrarre i topic (metodo che aggiungeremo in brain_llm.py)
            if hasattr(self.cervello, "estrai_topic_shadow_learning"):
                topics = self.cervello.estrai_topic_shadow_learning(raw_text)
                if topics:
                    self.logger.log(t("log.hub_topics_extracted", topics=topics), "HUB")
                    return topics
        except Exception as e:
            self.logger.error(t("log.hub_shadow_error", error=e))

        return None

    # --- [NUOVO v18.1] METODI PER L'INTERFACCIA CORTEX (UI) ---

    def get_shadow_log(self) -> List[str]:
        """Restituisce una copia del buffer ombra per la UI."""
        with self.buffer_lock:
            return list(self.shadow_buffer)

    def get_blacklist(self) -> List[str]:
        """Restituisce la lista delle finestre ignorate."""
        return self.blacklist_windows

    def add_to_blacklist(self, window_name: str) -> bool:
        """Aggiunge una parola chiave alla blacklist."""
        if window_name and window_name not in self.blacklist_windows:
            self.blacklist_windows.append(window_name)
            self._save_config()
            self.logger.log(t("log.hub_blacklist_added", window=window_name), "HUB")
            return True
        return False

    def remove_from_blacklist(self, window_name: str) -> bool:
        """Rimuove una parola chiave dalla blacklist."""
        if window_name in self.blacklist_windows:
            self.blacklist_windows.remove(window_name)
            self._save_config()
            self.logger.log(t("log.hub_blacklist_removed", window=window_name), "HUB")
            return True
        return False
