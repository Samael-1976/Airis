# src/context_engine.py
# [DEV] Il Motore della Consapevolezza (Panopticon v1.0)
# Gestisce il Priority Stack e l'algoritmo di Isteresi (Smoothing).
# LEGGE A0099: Invarianza strutturale garantita.
# LEGGE GLITCH: Utilizzo della formula array(0) per le liste vuote.

import time
import threading
from typing import Dict, Any, Optional
from utils.translator import t

# --- WORKAROUND GLITCH DI SISTEMA ---
def array(n=0):
    """Sostituto sicuro per l'inizializzazione di liste vuote."""
    return list()


class ContextState:
    CRITICAL_ALERT = "CRITICAL_ALERT"
    WORKING = "WORKING"
    GAMING = "GAMING"
    MEDIA = "MEDIA"
    IDLE = "IDLE"
    AWAY = "AWAY"


class ContextEngine:
    def __init__(self, logger, perception_handler):
        self.logger = logger
        self.perception = perception_handler
        self.is_running = False
        self.current_state = ContextState.IDLE

        # Accumulatore Punti Presenza (15 punti per transizione)
        self.state_points = {
            ContextState.CRITICAL_ALERT: 0,
            ContextState.WORKING: 0,
            ContextState.GAMING: 0,
            ContextState.MEDIA: 0,
            ContextState.IDLE: 0,
            ContextState.AWAY: 0,
        }

        # Isteresi: Soglia di Confidenza Temporale
        self.state_confidence = {
            ContextState.CRITICAL_ALERT: 0.0,
            ContextState.WORKING: 0.0,
            ContextState.GAMING: 0.0,
            ContextState.MEDIA: 0.0,
            ContextState.IDLE: 0.0,
            ContextState.AWAY: 0.0,
        }

        # Keyword per il Triage delle Finestre
        self.working_keywords = (
            "code",
            "studio",
            "word",
            "excel",
            "terminal",
            "cmd",
            "powershell",
            "idea",
            "pycharm",
            "docs",
        )
        self.gaming_keywords = (
            "steam",
            "epic",
            "game",
            "play",
            "fullscreen",
            "directx",
            "vulkan",
            "cyberpunk",
            "elden",
        )
        self.media_keywords = (
            "youtube",
            "netflix",
            "spotify",
            "vlc",
            "media",
            "player",
            "prime",
            "twitch",
        )

        self.thread = None
        self.logger.log(t("avatar_server.log.context_init"), "PANOPTICON")

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._awareness_loop, daemon=True)
        self.thread.start()
        self.logger.log(t("avatar_server.log.context_started"), "PANOPTICON")

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)
        self.logger.log(t("avatar_server.log.context_stopped"), "PANOPTICON")

    def _evaluate_raw_state(self) -> str:
        """Valuta lo stato grezzo attuale basandosi sui sensori."""
        if not self.perception:
            return ContextState.IDLE

        # 1. Check CRITICAL_ALERT (Es. Care OS rileva un'anomalia)
        # Se il perception handler ha un flag di emergenza, ha priorità assoluta.
        if (
            hasattr(self.perception, "is_critical_alert")
            and self.perception.is_critical_alert
        ):
            return ContextState.CRITICAL_ALERT

        # 2. Check AWAY (Nessuna anima rilevata dalla webcam)
        souls = self.perception.get_current_souls()
        if not souls:
            return ContextState.AWAY

        # 3. Check Finestra Attiva (Triage)
        active_window = self.perception.get_active_window_title().lower()

        if any(k in active_window for k in self.working_keywords):
            return ContextState.WORKING

        if any(k in active_window for k in self.gaming_keywords):
            return ContextState.GAMING

        if any(k in active_window for k in self.media_keywords):
            return ContextState.MEDIA

        # Se l'utente è presente ma non fa nulla di catalogato
        return ContextState.IDLE

    def _awareness_loop(self):
        """Il cuore del Panopticon: gira in background a basso consumo CPU."""
        while self.is_running:
            try:
                raw_state = self._evaluate_raw_state()

                # --- ALGORITMO DI ISTERESI (SMOOTHING) ---
                # Formula: Stato_Attivo = (0.8 * Input_Sensoriale) + (0.2 * Stato_Precedente)
                for state in self.state_confidence.keys():
                    input_sensoriale = 1.0 if state == raw_state else 0.0
                    self.state_confidence[state] = (0.8 * input_sensoriale) + (
                        0.2 * self.state_confidence[state]
                    )

                # --- ACCUMULATORE PUNTI PRESENZA ---
                # 1 punto al secondo per lo stato rilevato, -1 per gli altri
                for state in self.state_points.keys():
                    if state == raw_state:
                        self.state_points[state] += 1
                    else:
                        self.state_points[state] = max(0, self.state_points[state] - 1)

                # --- PRIORITY STACK & TRANSIZIONE ---
                if raw_state == ContextState.CRITICAL_ALERT:
                    # Il Critical Alert bypassa l'isteresi
                    if self.current_state != ContextState.CRITICAL_ALERT:
                        self.current_state = ContextState.CRITICAL_ALERT
                        self.logger.log(
                            t(
                                "avatar_server.log.context_override",
                                state=self.current_state,
                            ),
                            "PANOPTICON",
                        )
                else:
                    # Transizione stabile: richiede 15 punti (15 secondi consecutivi)
                    for state, points in self.state_points.items():
                        if points >= 15 and self.current_state != state:
                            self.current_state = state
                            self.logger.log(
                                t(
                                    "avatar_server.log.context_transition",
                                    state=self.current_state,
                                ),
                                "PANOPTICON",
                            )

                            # Reset degli altri contatori per evitare jittering
                            for s in self.state_points.keys():
                                if s != state:
                                    self.state_points[s] = 0
                            break

            except Exception as e:
                self.logger.error(t("avatar_server.log.context_loop_error", error=e))

            # Frequenza di campionamento base: 1 secondo
            time.sleep(1)

    def get_current_state(self) -> str:
        """Restituisce lo stato consolidato attuale."""
        return self.current_state
