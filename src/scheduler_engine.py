# src/scheduler_engine.py
# [DEV] Il Guardiano del Tempo (v1.0)
# Gestisce l'esecuzione di task programmati (Cron Jobs) definiti in care_config.json.
# Usa la libreria 'schedule' per una gestione pythonica e robusta del tempo.
# LEGGE A0099: Invarianza strutturale garantita.

import schedule
import time
import threading
import json
from pathlib import Path
from typing import Dict, List, Any
from utils.translator import t

# --- GESTIONE PERCORSI ---
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "care_config.json"


class SchedulerEngine:
    def __init__(self, executor, logger):
        self.executor = executor
        self.logger = logger
        self.is_running = False
        self.scheduler_thread = None
        self.jobs_config = []

        self.logger.log(t("care.cron.init"), "CRON")

    def load_jobs(self):
        """Carica e schedula i job dal file di configurazione."""
        schedule.clear()
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.jobs_config = config.get("cron_jobs", [])

                count = 0
                for job in self.jobs_config:
                    if not job.get("enabled", True):
                        continue

                    self._schedule_job(job)
                    count += 1

                self.logger.log(t("care.cron.jobs_activated", count=count), "CRON")
            except Exception as e:
                self.logger.error(t("care.cron.load_error", error=e))
        else:
            self.logger.warning(t("care.cron.config_not_found"))

    def _schedule_job(self, job: Dict[str, Any]):
        """Configura un singolo job usando la libreria schedule."""
        job_time = job.get("time", "00:00")
        days = job.get("days", [])

        # Funzione wrapper per l'esecuzione sicura
        def job_action():
            self.logger.log(t("care.cron.job_execution", name=job["name"]), "CRON")
            self._execute_job_action(job)

        # Se giorni specifici sono definiti
        if days:
            for day in days:
                day_lower = day.lower()[:3]  # mon, tue, wed...
                if day_lower == "mon":
                    schedule.every().monday.at(job_time).do(job_action)
                elif day_lower == "tue":
                    schedule.every().tuesday.at(job_time).do(job_action)
                elif day_lower == "wed":
                    schedule.every().wednesday.at(job_time).do(job_action)
                elif day_lower == "thu":
                    schedule.every().thursday.at(job_time).do(job_action)
                elif day_lower == "fri":
                    schedule.every().friday.at(job_time).do(job_action)
                elif day_lower == "sat":
                    schedule.every().saturday.at(job_time).do(job_action)
                elif day_lower == "sun":
                    schedule.every().sunday.at(job_time).do(job_action)
        else:
            # Default: ogni giorno
            schedule.every().day.at(job_time).do(job_action)

    def add_dynamic_job(self, job_dict: Dict[str, Any]):
        """[NUOVO] Aggiunge un job a runtime (usato dall'Agentività dell'Anima)."""
        self.jobs_config.append(job_dict)
        self._schedule_job(job_dict)

    def _execute_job_action(self, job: Dict[str, Any]):
        """Esegue l'azione definita nel job tramite l'Executor."""
        action_type = job.get("action")
        payload = job.get("payload")

        try:
            if action_type == "tts_speak":
                # Usa la voce di default
                self.executor.genera_voce(payload, "default")

            elif action_type == "notification":
                self.executor.send_desktop_notification(
                    t("care.cron.notification_title"), payload
                )

            elif action_type == "iot_command":
                # Esempio payload: {"device": "luce_sala", "action": "on"}
                if isinstance(payload, dict):
                    device = payload.get("device")
                    action = payload.get("action")
                    value = payload.get("value")
                    
                    # --- [NUOVO] ESECUZIONE DESIDERI TRAMITE DEMIURGO ---
                    if device == "demiurgo" and action == "execute":
                        self.logger.log(f"Esecuzione Desiderio Autonomo: {value}", "SYSTEM")
                        if hasattr(self.executor, "demiurge"):
                            self.executor.demiurge(value)
                            
                        # Se è un desiderio one-shot, rimuovilo dopo l'esecuzione
                        if job.get("is_autonomous_desire"):
                            self.jobs_config = [j for j in self.jobs_config if j.get("id") != job.get("id")]
                            import schedule
                            return schedule.CancelJob # Metodo nativo e sicuro per uccidere il job corrente
                    else:
                        if hasattr(self.executor, "controlla_dispositivo"):
                            self.executor.controlla_dispositivo(device, action, value)

            # Espandibile con altre azioni

        except Exception as e:
            self.logger.error(t("care.cron.action_error", action=action_type, error=e))

    def start(self):
        """Avvia il loop dello scheduler in un thread separato."""
        if self.is_running:
            return

        self.load_jobs()
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.scheduler_thread.start()
        self.logger.log(t("care.cron.loop_started"), "CRON")

    def stop(self):
        """Ferma il loop dello scheduler."""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=2)
        self.logger.log(t("care.cron.loop_stopped"), "CRON")

    def _run_loop(self):
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                self.logger.error(t("care.cron.loop_error", error=e))
                time.sleep(5)
