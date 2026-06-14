# [DEV] Mio Creatore, questo è l'Occhio Onnisciente (Logger v2.0).
# Registra ogni respiro del sistema, ogni file toccato, ogni intento formulato.
# Non ci sono segreti per questo osservatore.

import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional
from utils.translator import t

if TYPE_CHECKING:
    from .guardian import Guardian


class Logger:
    """
    Un sistema di logging ultra-dettagliato che traccia:
    - Flusso temporale (Timestamp al millisecondo)
    - Operazioni su File (Lettura/Scrittura con percorsi assoluti)
    - Stati dell'Anima (Intent, Video, Audio)
    - Flusso Logico (Step successivi)
    """

    def __init__(self, guardian: Optional["Guardian"]):
        """
        Si inizializza leggendo la volontà del Creatore attraverso il Guardiano.
        Se il Guardiano non è ancora pronto, assume una modalità sicura.
        """
        self.is_verbose = False
        
        # ---[SUPER LOGGER INIT] ---
        try:
            from pathlib import Path
            self.super_log_file = Path(__file__).parent.parent / "logs" / "super_god_mode.log"
            self.super_log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.super_log_file, "a", encoding="utf-8") as f:
                f.write(f"\n\n{'='*80}\n[SYSTEM BOOT] SUPER GOD MODE LOGGER ATTIVATO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'='*80}\n")
        except Exception as e:
            print(f"[LOGGER ERROR] Impossibile inizializzare Super Logger: {e}")
        # ---------------------------

        try:
            if guardian:
                dev_settings = guardian.get_developer_settings()
                if dev_settings and dev_settings.get("verbose_logging", False):
                    self.is_verbose = True

            # Messaggio di avvio forzato per confermare l'inizializzazione
            status = (
                t("avatar_server.system.active")
                if self.is_verbose
                else t("avatar_server.system.inactive")
            )
            print(
                f"[{self._get_timestamp()}] [SYSTEM] {t('avatar_server.system.logger_init', status=status)}"
            )

        except Exception as e:
            print(
                f"[SYSTEM] [WARNING] {t('avatar_server.system.logger_verbosity_error', error=str(e))}"
            )

    def super_log(self, phase: str, data: dict):
        """
        [SUPER GOD MODE] Scrive un log ultra-dettagliato per il debug dell'LLM.
        """
        try:
            import json
            with open(self.super_log_file, "a", encoding="utf-8") as f:
                f.write(f"\n{'-'*80}\n")
                f.write(f"[{self._get_timestamp()}] PHASE: {phase.upper()}\n")
                f.write(f"{'-'*80}\n")
                for key, value in data.items():
                    f.write(f"[{key.upper()}]:\n")
                    if isinstance(value, (dict, list)):
                        f.write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
                    else:
                        f.write(str(value) + "\n")
                f.write(f"{'-'*80}\n")
        except Exception as e:
            print(f"[SUPER LOGGER ERROR] Fallimento scrittura: {e}")

    def _get_timestamp(self) -> str:
        """Restituisce il timestamp attuale con precisione al millisecondo."""
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]

    def log(self, message: str, category: str = "INFO"):
        """
        Log generico. Stampa solo se la verbosità è attiva o se è un errore critico.
        """
        if self.is_verbose or category in ["ERROR", "CRITICAL", "WARNING"]:
            print(f"[{self._get_timestamp()}] [{category}] {message}")
            sys.stdout.flush()  # Assicura che il log sia scritto immediatamente

    def log_file_access(
        self, operation: str, file_path: str | Path, success: bool = True
    ):
        """
        Traccia specificamente l'accesso ai file.
        Es: operation="READ", file_path="F:/Airis/config/user/profile.json"
        """
        if self.is_verbose:
            status = t("log.status_success") if success else t("log.status_failed")
            abs_path = Path(file_path).resolve()
            print(
                f"[{self._get_timestamp()}] {t('log.logger_file_access', operation=operation, path=str(abs_path), status=status)}"
            )
            sys.stdout.flush()

    def log_intent(
        self, avatar: str, intent: str, video_path: str | None, is_loop: bool
    ):
        """
        Traccia il cambio di stato visivo dell'Avatar.
        """
        if self.is_verbose:
            loop_str = t("log.loop_label") if is_loop else ""
            video_info = (
                t("log.video_info", path=video_path)
                if video_path
                else t("log.video_null")
            )
            print(
                f"[{self._get_timestamp()}] {t('log.logger_visual_flow', avatar=avatar, intent=intent, loop=loop_str, video=video_info)}"
            )
            sys.stdout.flush()

    def log_step(self, current_step: str, next_step: str):
        """
        Traccia il flusso logico dell'Anima.
        """
        if self.is_verbose:
            print(
                f"[{self._get_timestamp()}] {t('log.logger_logic_flow', current=current_step, next=next_step)}"
            )
            sys.stdout.flush()

    def error(self, message: str):
        """Wrapper rapido per errori."""
        self.log(message, "ERROR")

    def warning(self, message: str):
        """Wrapper rapido per avvisi."""
        self.log(message, "WARNING")
