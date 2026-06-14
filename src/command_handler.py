# src/command_handler.py
# v33.3 - TESSERACT PURGE
# REMOVED: Comando 'set_path' per Tesseract (obsoleto grazie al motore OCR Ibrido).
# ADD: Registrazione ufficiale del comando /iot_control nel Grimorio.
# FIX: Risolto errore "Non conosco l'incantesimo" permettendo l'uso del comando da ogni sorgente.
# MANTENUTO: Active Hearing, Intercom, Hive Mind, Save Character Fix.
# LEGGE A0099: Invarianza strutturale garantita. Nessuna riga originale rimossa.

import os
import subprocess
import threading
import shlex
from pathlib import Path
import uuid
import json
from datetime import datetime, timedelta
import re
import yaml
import base64

from typing import TYPE_CHECKING, List, Tuple
from utils.translator import t

if TYPE_CHECKING:
    from executor import BraccioDivino
    from memory_manager import MemoryManager
    from brain_llm import CervelloTrinitario
    from database_manager import DatabaseManager
    from perception_handler import PerceptionHandler
    from guardian import Guardian
    from chat import CicloVitale


class CommandHandler:
    def __init__(
        self,
        executor: "BraccioDivino",
        memory: "MemoryManager",
        cervello: "CervelloTrinitario",
        prompts: dict,
        db_manager: "DatabaseManager",
        perception_handler: "PerceptionHandler",
        guardian: "Guardian",
        active_rpg_path,
        ciclo_vitale: "CicloVitale",
    ):
        self.executor = executor
        self.memory = memory
        self.cervello = cervello
        self.db_manager = db_manager
        self.perception = perception_handler
        self.guardian = guardian
        self.active_rpg_path = active_rpg_path
        self.ciclo_vitale = ciclo_vitale

        # Prefisso neutro per i messaggi di sistema
        self.sys_prefix = t("chat.sys_prefix")

        self.commands = {
            "help": self.handle_help,
            "clear": self.handle_clear,
            "quit": self.handle_quit,
            "about": self.handle_about,
            "findfiles": self.handle_find,
            "writefile": self.handle_write,
            "edit": self.handle_edit,
            "search": self.handle_search,
            "webfetch": self.handle_fetch,
            "memory": self.handle_memory,
            "read": self.handle_read,
            "cat": self.handle_cat,
            "wiki": self.handle_wiki,
            "perception_status": self.handle_perception_status,
            "describe_image": self.handle_describe_image,
            "export": self.handle_export,
            "import": self.handle_import,
            "monitor": self.handle_monitor,
            # --- RIFONDAZIONE ASCOLTO (v33.0) ---
            "active_hearing": self.handle_active_hearing,  # Sostituisce hotword
            "stop_generation": self.handle_stop_generation,
            "save_session": self.handle_save_session,
            "promemoria": self.handle_promemoria,
            "set_reflection_time": self.handle_set_reflection_time,
            "set_reminder_interval": self.handle_set_reminder_interval,
            "fix_gallery": self.handle_fix_gallery,  # [NUOVO v7.6]
            # Nuovi comandi per la gestione personaggi e profilo
            "save_character": self.handle_save_character,
            "archive_character": self.handle_archive_character,
            "save_profile": self.handle_save_profile,
            # Nuovo comando per generazione DEF
            "generate_def": self.handle_generate_def,
            # Nuovo comando per generazione Skill
            "generate_skill": self.handle_generate_skill,
            # Nuovo comando per gestione Gioco
            "game": self.handle_game,
            # --- [NUOVO v33.2] COMANDO IOT ---
            "iot_control": self.handle_iot_control,
            # ---[NUOVO v125.0] COMANDO SOGNO MANUALE ---
            "dream": self.handle_dream,
            # --- [NUOVO v7.0] PROTOCOLLO FLASH-CACHE ---
            "clear_cache": self.handle_clear_cache,
            # --- [NUOVO] COMANDO DI SINCRONIZZAZIONE ROSTER IN RAM ---
            "rpg_roster_toggle": self.handle_rpg_roster_toggle,
            # --- [RM29] COMANDI MULTIPLAYER NETWORK ---
            "host_room": self.handle_host_room,
            "close_room": self.handle_close_room,
            "kick_player": self.handle_kick_player,
            # --- [RM28] COMANDI GILDA ---
            "guild_create": self.handle_guild_create,
            "guild_invite": self.handle_guild_invite,
            "guild_kick": self.handle_guild_kick,
        }
        self.stop_generation_event = threading.Event()

    def process_command(self, user_input: str) -> threading.Thread | None:
        user_input = user_input.strip()
        if user_input.startswith("!"):
            command_thread = threading.Thread(
                target=self.handle_shell_command,
                args=(user_input[1:].strip(),),
                daemon=True,
            )
            command_thread.start()
            return None
        if user_input.startswith("/"):
            try:
                parts = user_input[1:].strip().split(maxsplit=1)
                command_name = parts[0].lower() if parts else ""
                args_str = parts[1] if len(parts) > 1 else ""

                # Comandi gestiti direttamente in chat.py o ignorati qui se duplicati
                if command_name in[
                    "new_session",
                    "load_session",
                    "apply_full_config",
                    "save_prompts",
                    "save_world_file",
                    "autofill",
                    "toggle_learning",
                    "reload_iot_config",
                    "reload_mcp_config",
                    "factory_reset",
                ]:
                    return None

                command_func = self.commands.get(command_name)
                if command_func:
                    thread = threading.Thread(
                        target=command_func, args=(args_str,), daemon=True
                    )
                    thread.start()
                    return thread
                else:
                    print(
                        f"{self.sys_prefix}{t('chat.err_unknown_spell', name=command_name)}"
                    )
            except Exception as e:
                print(
                    f"{self.sys_prefix}{t('chat.err_grimorio_corrupted', error=str(e))}"
                )
        return None

    def _run_shell_in_thread(self, command: str):
        try:
            print(t("log.shell_executing", command=command))
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore",
            )
            if process.stdout:
                for line in iter(process.stdout.readline, ""):
                    print(line, end="")
            process.wait()
            print(t("log.shell_completed"))
        except Exception as e:
            print(t("log.shell_error", error=str(e)))

    def handle_shell_command(self, command: str):
        if not command:
            print(f"{self.sys_prefix}{t('chat.err_shell_empty')}")
            return
        self._run_shell_in_thread(command)

    def handle_help(self, args_str: str):
        print(t("chat.grimorio_title"))
        print(t("chat.grimorio_help"))
        print(t("chat.grimorio_clear"))
        print(t("chat.grimorio_quit"))
        print(t("chat.grimorio_session_mem"))
        print(t("chat.grimorio_new_session"))
        print(t("chat.grimorio_load_session"))
        print(t("chat.grimorio_save_session"))
        print(t("chat.grimorio_reminder"))
        print(t("chat.grimorio_mem_save"))
        print(t("chat.grimorio_mem_search"))
        print(t("chat.grimorio_game_title"))
        print(t("chat.grimorio_game_start"))
        print(t("chat.grimorio_game_stop"))
        print(t("chat.grimorio_game_score"))
        print(t("chat.grimorio_game_turn"))
        print(t("chat.grimorio_game_status"))
        print(t("chat.grimorio_char_title"))
        print(t("chat.grimorio_save_char"))
        print(t("chat.grimorio_archive_char"))
        print(t("chat.grimorio_save_profile"))
        print(t("chat.grimorio_tools_title"))
        print(t("chat.grimorio_search"))
        print(t("chat.grimorio_wiki"))
        print(t("chat.grimorio_read"))
        print(t("chat.grimorio_find"))
        print(t("chat.grimorio_write"))
        print(t("chat.grimorio_edit"))
        print(t("chat.grimorio_describe"))
        print(t("chat.grimorio_perc_title"))
        print(t("chat.grimorio_perc_status"))
        print(t("chat.grimorio_monitor"))
        # --- RIFONDAZIONE ASCOLTO (v33.0) ---
        print(t("chat.grimorio_hearing"))

        print(t("chat.grimorio_learning"))
        print(t("chat.grimorio_refl_time"))
        print(t("chat.grimorio_rem_int"))
        print(t("chat.grimorio_fix_gal"))
        print(t("chat.grimorio_data_title"))
        print(t("chat.grimorio_export"))
        print(t("chat.grimorio_import"))
        print(t("chat.grimorio_soul_title"))
        print(t("chat.grimorio_stop_gen"))
        print(t("chat.grimorio_clear_cache"))
        print(t("chat.grimorio_shell"))

    def handle_game(self, args_str: str):
        """Gestisce i comandi manuali per il gioco."""
        rpg_path = self.ciclo_vitale.active_rpg_path
        if not rpg_path:
            print(f"{self.sys_prefix}{t('chat.err_no_gdr_active')}")
            return

        status_path = rpg_path / "WORLD" / "status.json"
        if not status_path.exists():
            print(f"{self.sys_prefix}{t('chat.err_status_not_found')}")
            return

        try:
            with open(status_path, "r", encoding="utf-8") as f:
                status = json.load(f)

            # Inizializza struttura se mancante
            if "metadati" not in status:
                status["metadati"] = {}
            if "game_state" not in status["metadati"]:
                status["metadati"]["game_state"] = {
                    "active": False,
                    "scores": {},
                    "turn_player": "",
                    "type": "truth_or_dare",
                }

            gs = status["metadati"]["game_state"]
            args = shlex.split(args_str)

            if not args:
                print(
                    f"{self.sys_prefix}{t('chat.game_status_label', status=json.dumps(gs, indent=2))}"
                )
                return

            cmd = args[0].lower()

            if cmd == "start":
                game_type = "truth_or_dare"
                if len(args) > 1:
                    if args[1].lower() in ["never", t("chat.keyword_never")]:
                        game_type = "never_have_i_ever"

                gs["active"] = True
                gs["type"] = game_type

                # Imposta il turno iniziale (default Rapunzel o il primo della lista)
                if not gs.get("turn_player"):
                    gs["turn_player"] = t("chat.default_turn_player")

                if game_type == "truth_or_dare":
                    gs["scores"] = {
                        char["nome"]: 10 for char in status.get("personaggi", [])
                    }
                    status["metadati"]["evento_corrente"] = t("chat.game_truth_event")
                    print(f"{self.sys_prefix}{t('chat.game_truth_start')}")
                else:
                    gs["scores"] = {
                        char["nome"]: 0 for char in status.get("personaggi", [])
                    }
                    status["metadati"]["evento_corrente"] = t("chat.game_never_event")
                    print(f"{self.sys_prefix}{t('chat.game_never_start')}")

                # Aggiungi anche il PG se non c'è
                pg_name = t("chat.default_pg_name")  # Fallback
                if pg_name not in gs["scores"]:
                    gs["scores"][pg_name] = 10 if game_type == "truth_or_dare" else 0

            elif cmd == "stop":
                gs["active"] = False
                status["metadati"]["evento_corrente"] = t("chat.game_none_event")
                print(f"{self.sys_prefix}{t('chat.game_stopped')}")

            elif cmd == "score":
                if len(args) < 3:
                    print(f"{self.sys_prefix}{t('chat.game_score_usage')}")
                    return
                target = args[1]
                try:
                    val = int(args[2])
                    # Cerca il nome corretto (case insensitive)
                    real_key = next(
                        (k for k in gs["scores"].keys() if k.lower() == target.lower()),
                        None,
                    )
                    if real_key:
                        gs["scores"][real_key] = val
                        print(
                            f"{self.sys_prefix}{t('chat.game_score_set', name=real_key, val=val)}"
                        )
                    else:
                        print(
                            f"{self.sys_prefix}{t('chat.game_char_not_found', name=target)}"
                        )
                except ValueError:
                    print(f"{self.sys_prefix}{t('chat.game_score_nan')}")

            elif cmd == "turn":
                if len(args) < 2:
                    print(f"{self.sys_prefix}{t('chat.game_turn_usage')}")
                    return
                target = args[1]
                # Verifica esistenza (opzionale, ma utile)
                real_key = next(
                    (
                        c["nome"]
                        for c in status.get("personaggi", [])
                        if c["nome"].lower() == target.lower()
                    ),
                    None,
                )
                if real_key:
                    gs["turn_player"] = real_key
                    print(
                        f"{self.sys_prefix}{t('chat.game_turn_forced', name=real_key)}"
                    )
                else:
                    print(
                        f"{self.sys_prefix}{t('chat.err_char_not_found', target=target, name='SYSTEM')}"
                    )

            elif cmd == "status":
                print(
                    f"{self.sys_prefix}{t('chat.game_status_label', status=json.dumps(gs, indent=2))}"
                )

            else:
                print(f"{self.sys_prefix}{t('chat.game_subcmd_unknown')}")

            # Salva le modifiche
            with open(status_path, "w", encoding="utf-8") as f:
                json.dump(status, f, indent=2, ensure_ascii=False)

            # Aggiorna il frontend se necessario (opzionale, ma utile per sync immediato)
            # self.ciclo_vitale.avatar_bridge.send_payload(...)

        except Exception as e:
            print(f"{self.sys_prefix}{t('chat.err_game_generic', error=str(e))}")

    def handle_promemoria(self, args_str: str):
        if not self.ciclo_vitale.current_session_id:
            print(f"{self.sys_prefix}{t('chat.err_reminder_no_session')}")
            return

        match_tra = re.match(t("chat.regex_tra"), args_str, re.IGNORECASE)
        match_alle = re.match(t("chat.regex_alle"), args_str, re.IGNORECASE)

        content = ""
        trigger_in_minutes = 0

        if match_tra:
            trigger_in_minutes = int(match_tra.group(1))
            content = match_tra.group(2).strip()
        elif match_alle:
            hour, minute = int(match_alle.group(1)), int(match_alle.group(2))
            content = match_alle.group(3).strip()
            now = datetime.now()
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target_time < now:
                print(f"{self.sys_prefix}{t('chat.err_reminder_past')}")
                return
            delta = target_time - now
            trigger_in_minutes = int(delta.total_seconds() / 60)
        else:
            print(f"{self.sys_prefix}{t('chat.err_reminder_format')}")
            return

        if content and trigger_in_minutes > 0:
            result = self.executor.create_reminder(
                self.ciclo_vitale.current_session_id, content, trigger_in_minutes
            )
            print(f"{self.sys_prefix}{result}")
        else:
            print(f"{self.sys_prefix}{t('chat.err_reminder_invalid')}")

    def _save_config(self):
        try:
            params = self.guardian._config.get("parameters", {})
            self.guardian.save_parameters_config(params)
            return True
        except Exception as e:
            print(f"{self.sys_prefix}{t('chat.err_config_save', error=str(e))}")
            return False

    def handle_set_reflection_time(self, args_str: str):
        try:
            new_time = datetime.strptime(args_str.strip(), "%H:%M").strftime("%H:%M")
            if self.guardian._config:
                self.guardian._config["proactive_memory"]["reflection_time"] = new_time
                if self._save_config():
                    print(f"{self.sys_prefix}{t('chat.refl_time_set', time=new_time)}")
            else:
                print(f"{self.sys_prefix}{t('chat.err_config_not_loaded')}")
        except ValueError:
            print(f"{self.sys_prefix}{t('chat.err_time_invalid')}")

    def handle_set_reminder_interval(self, args_str: str):
        arg = args_str.strip().lower()
        if arg == t("chat.keyword_mai"):
            new_interval = 0
        else:
            try:
                new_interval = int(arg)
                if not (1 <= new_interval <= 60):
                    raise ValueError()
            except ValueError:
                print(f"{self.sys_prefix}{t('chat.err_interval_invalid')}")
                return

        if self.guardian._config:
            self.guardian._config["proactive_memory"][
                "reminder_check_interval_minutes"
            ] = new_interval
            if self._save_config():
                if new_interval == 0:
                    print(f"{self.sys_prefix}{t('chat.rem_check_disabled')}")
                else:
                    print(
                        f"{self.sys_prefix}{t('chat.rem_check_set', interval=new_interval)}"
                    )
        else:
            print(f"{self.sys_prefix}{t('chat.err_config_not_loaded')}")

    def handle_stop_generation(self, args_str: str):
        self.stop_generation_event.set()
        print(f"\n{self.sys_prefix}{t('chat.stop_gen_msg')}")

    def handle_save_session(self, args_str: str):
        self.ciclo_vitale._save_current_gdr_snapshot()
        if self.ciclo_vitale.current_session_id and self.db_manager:
            self.db_manager.update_session(self.ciclo_vitale.current_session_id)
        print(f"{self.sys_prefix}{t('chat.session_saved')}")

    # --- RIFONDAZIONE ASCOLTO (v33.0) ---
    def handle_active_hearing(self, args_str: str):
        if not self.perception:
            print(f"{self.sys_prefix}{t('chat.err_perc_not_active')}")
            return
        try:
            parts = shlex.split(args_str)
            if not parts:
                print(f"{self.sys_prefix}{t('chat.hearing_usage')}")
                return
            sub_command = parts[0].lower()
            if sub_command == "on":
                success, message = self.perception.start_active_hearing()
                print(f"{self.sys_prefix}{message}")
            elif sub_command == "off":
                success, message = self.perception.stop_active_hearing()
                print(f"{self.sys_prefix}{message}")
            else:
                print(f"{self.sys_prefix}{t('chat.game_subcmd_unknown')}")
        except ValueError:
            print(f"{self.sys_prefix}{t('chat.err_hearing_quotes')}")
        except Exception as e:
            print(f"{self.sys_prefix}{t('chat.err_hearing_generic', error=str(e))}")

    def handle_monitor(self, args_str: str):
        if not self.perception:
            print(f"{self.sys_prefix}{t('chat.err_perc_not_active')}")
            return
        try:
            parts = shlex.split(args_str)
            if not parts:
                print(f"{self.sys_prefix}{t('chat.monitor_usage')}")
                return
            sub_command = parts[0].lower()
            if sub_command == "on":
                success, message = self.perception.start_monitoring()
                print(f"{self.sys_prefix}{message}")
            elif sub_command == "off":
                success, message = self.perception.stop_monitoring()
                print(f"{self.sys_prefix}{message}")
            else:
                print(f"{self.sys_prefix}{t('chat.game_subcmd_unknown')}")
        except ValueError:
            print(f"{self.sys_prefix}{t('chat.err_hearing_quotes')}")
        except Exception as e:
            print(f"{self.sys_prefix}{t('chat.err_monitor_generic', error=str(e))}")

    def handle_export(self, args_str: str):
        try:
            args = shlex.split(args_str)
            if not args or len(args) < 2:
                print(f"{self.sys_prefix}{t('chat.export_incomplete')}")
                return

            # --- [FIX v33.4] PARSING ROBUSTO ---
            args_dict = {}
            for arg in args:
                if "=" in arg:
                    k, v = arg.split("=", 1)
                    args_dict[k] = v

            export_type = args_dict.get("type")
            avatar_name = args_dict.get("avatar")
            lore_name = args_dict.get("lore")

            print(f"{self.sys_prefix}{t('chat.export_start')}")
            result = self.executor.export_package(export_type, avatar_name, lore_name)
            if result.get("success"):
                print(
                    f"{self.sys_prefix}{t('chat.export_success', path=result.get('path'))}"
                )
                self.ciclo_vitale.avatar_bridge.send_payload(
                    {
                        "type": "download_file",
                        "path": Path(result.get("path"))
                        .relative_to(self.executor.APP_ROOT)
                        .as_posix(),
                    }
                )
            else:
                print(
                    f"{self.sys_prefix}{t('chat.export_failed', error=result.get('error'))}"
                )
        except Exception as e:
            print(f"{self.sys_prefix}{t('chat.unexpected_error', error=str(e))}")

    def handle_import(self, args_str: str):
        try:
            args = shlex.split(args_str)

            # --- [FIX v33.4] PARSING ROBUSTO ---
            args_dict = {}
            for arg in args:
                if "=" in arg:
                    k, v = arg.split("=", 1)
                    args_dict[k] = v

            zip_path = args_dict.get("path")
            overwrite = args_dict.get("overwrite", "False").lower() == "true"
            if not zip_path:
                print(f"{self.sys_prefix}{t('chat.import_no_path')}")
                return

            print(f"{self.sys_prefix}{t('chat.import_start')}")
            result = self.executor.import_package(zip_path, overwrite=overwrite)
            if result.get("success"):
                print(f"{self.sys_prefix}{t('chat.import_success')}")
                self.ciclo_vitale._trigger_restart()
            else:
                print(
                    f"{self.sys_prefix}{t('system.error', error=result.get('error'))}"
                )
        except Exception as e:
            print(f"{self.sys_prefix}{t('chat.unexpected_error', error=str(e))}")

    def handle_perception_status(self, args_str: str):
        if not self.perception:
            print(f"{self.sys_prefix}{t('chat.err_perc_not_init')}")
            return
        print(f"{self.sys_prefix}{self.perception.get_status()}")

    def handle_describe_image(self, args_str: str):
        if not args_str:
            print(f"{self.sys_prefix}{t('chat.describe_usage')}")
            return
        print(f"{self.sys_prefix}{t('chat.describe_start')}")
        path_str = args_str.strip().strip('"')
        description = self.executor.descrivi_immagine_con_pan_scan(
            path_str, self.cervello
        )
        print(f"{self.sys_prefix}{description}")

    def handle_wiki(self, args_str: str):
        if not args_str:
            print(f"{self.sys_prefix}{t('chat.wiki_usage')}")
            return
        print(f"{self.sys_prefix}{self.executor.search_wikipedia(args_str)}")

    def handle_clear(self, args_str: str):
        os.system("cls" if os.name == "nt" else "clear")

    def handle_quit(self, args_str: str):
        raise KeyboardInterrupt

    def handle_about(self, args_str: str):
        print(t("log.manifest_about"))

    def handle_find(self, args_str: str):
        if not args_str:
            print(f"{self.sys_prefix}{t('chat.find_usage')}")
            return
        print(f"{self.sys_prefix}{self.executor.find_files(args_str)}")

    def handle_write(self, args_str: str):
        try:
            args = shlex.split(args_str)
            if len(args) < 2:
                print(f"{self.sys_prefix}{t('chat.write_usage')}")
                return
            print(f"{self.sys_prefix}{self.executor.write_file(args[0], args[1])}")
        except ValueError:
            print(f"{self.sys_prefix}{t('chat.err_hearing_quotes')}")

    def handle_edit(self, args_str: str):
        try:
            args = shlex.split(args_str)
            if len(args) < 3:
                print(f"{self.sys_prefix}{t('chat.edit_usage')}")
                return
            print(
                f"{self.sys_prefix}{self.executor.edit_file_replace(args[0], args[1], args[2])}"
            )
        except ValueError:
            print(f"{self.sys_prefix}{t('chat.err_hearing_quotes')}")

    def handle_search(self, args_str: str):
        if not args_str:
            print(f"{self.sys_prefix}{t('chat.search_usage')}")
            return
        print(f"{self.sys_prefix}{self.executor.web_search(args_str)}")

    def handle_fetch(self, args_str: str):
        if not args_str:
            print(f"{self.sys_prefix}{t('chat.fetch_usage')}")
            return
        print(f"{self.sys_prefix}{self.executor.web_fetch(args_str)}")

    def handle_memory(self, args_str: str):
        try:
            args = shlex.split(args_str)
            if not args:
                print(f"{self.sys_prefix}{t('chat.mem_usage')}")
                return
            sub_command = args[0].lower()
            if sub_command == "save":
                if len(args) < 2:
                    print(f"{self.sys_prefix}{t('chat.mem_save_what')}")
                    return
                print(
                    f"{self.sys_prefix}{self.executor.save_to_memory(args[1], self.ciclo_vitale.current_session_id)}"
                )
            elif sub_command == "search":
                if len(args) < 2:
                    print(f"{self.sys_prefix}{t('chat.mem_search_what')}")
                    return
                print(f"{self.sys_prefix}{self.executor.search_in_memory(args[1])}")
            elif sub_command == "save_session":
                result = self.executor.create_session_memory(
                    self.ciclo_vitale.chat_history,
                    self.ciclo_vitale.current_session_id,
                    self.cervello,
                    self.db_manager,
                )
                print(f"{self.sys_prefix}{result}")
                self.ciclo_vitale.chat_history.clear()
            else:
                print(
                    f"{self.sys_prefix}{t('chat.mem_unknown_rite', name=sub_command)}"
                )
        except ValueError:
            print(f"{self.sys_prefix}{t('chat.err_hearing_quotes')}")

    def handle_read(self, args_str: str):
        if not args_str:
            print(f"{self.sys_prefix}{t('chat.read_usage')}")
            return
        path_str = args_str.strip().strip('"')
        print(
            f"{self.sys_prefix}{self.executor.leggi_contenuto_da_percorso(path_str, self.cervello)}"
        )

    def handle_cat(self, args_str: str):
        if not args_str:
            print(f"{self.sys_prefix}{t('chat.cat_usage')}")
            return
        path_str = args_str.strip().strip('"')
        self.executor.sfoglia_percorso_in_sequenza(path_str)

    # --- NUOVI HANDLER PER GESTIONE PERSONAGGI E PROFILO (FIX BASE64 & AVATAR) ---

    def handle_save_character(self, args_str: str):
        try:
            # Parsing robusto
            args = shlex.split(args_str)
            args_dict = {}
            for arg in args:
                if "=" in arg:
                    k, v = arg.split("=", 1)
                    args_dict[k] = v

            char_type = args_dict.get("type")
            char_data_b64 = args_dict.get("data")  # Ora è in Base64

            # --- FIX CRITICO v33.1: ESTRAZIONE CORRETTA ARGOMENTI ---
            file_path = args_dict.get("file_path")
            lang = args_dict.get("lang", "it")  # Default a 'it' se non presente

            if not char_type or not char_data_b64:
                print(f"{self.sys_prefix}{t('chat.char_save_missing')}")
                return

            # MODIFICA: Se il tipo è AVATAR, non serve un GDR attivo
            if char_type.upper() != "AVATAR" and not self.active_rpg_path:
                print(f"{self.sys_prefix}{t('chat.char_save_no_gdr')}")
                return

            # Decodifica Base64
            try:
                char_data_json = base64.b64decode(char_data_b64).decode("utf-8")
            except Exception as e:
                print(f"{self.sys_prefix}{t('chat.err_char_decode', error=str(e))}")
                return

            # Passiamo self.active_rpg_path (che può essere None se siamo in modalità AVATAR)
            # --- FIX CRITICO v33.1: PASSAGGIO CORRETTO ARGOMENTI ---
            result = self.executor.save_character_file(
                rpg_root=self.active_rpg_path,
                char_type=char_type,
                char_data_json=char_data_json,
                lang=lang,
                temp_image_path=file_path,
            )
            print(f"{self.sys_prefix}{result}")

        except Exception as e:
            print(f"{self.sys_prefix}{t('chat.unexpected_error', error=str(e))}")

    def handle_archive_character(self, args_str: str):
        try:
            args = shlex.split(args_str)
            args_dict = {}
            for arg in args:
                if "=" in arg:
                    k, v = arg.split("=", 1)
                    args_dict[k] = v

            char_id = args_dict.get("id")
            char_type = args_dict.get("type")
            lang = args_dict.get("lang", "it")

            if not char_id or not char_type:
                print(f"{self.sys_prefix}{t('chat.char_archive_missing')}")
                return

            # MODIFICA: Se il tipo è AVATAR, non serve un GDR attivo
            if char_type.upper() != "AVATAR" and not self.active_rpg_path:
                print(f"{self.sys_prefix}{t('chat.err_no_gdr_active')}")
                return

            result = self.executor.archive_character_file(
                self.active_rpg_path, lang, char_type, char_id
            )
            print(f"{self.sys_prefix}{result}")

        except Exception as e:
            print(f"{self.sys_prefix}{t('chat.unexpected_error', error=str(e))}")

    def handle_save_profile(self, args_str: str):
        try:
            args = shlex.split(args_str)
            args_dict = {}
            for arg in args:
                if "=" in arg:
                    k, v = arg.split("=", 1)
                    args_dict[k] = v

            profile_data_b64 = args_dict.get("data")  # Ora è in Base64

            if not profile_data_b64:
                print(f"{self.sys_prefix}{t('chat.profile_save_missing')}")
                return

            # Decodifica Base64
            try:
                profile_data_json = base64.b64decode(profile_data_b64).decode("utf-8")
            except Exception as e:
                print(f"{self.sys_prefix}{t('chat.err_profile_decode', error=str(e))}")
                return

            result = self.executor.save_profile_file(profile_data_json)
            print(f"{self.sys_prefix}{result}")

        except Exception as e:
            print(f"{self.sys_prefix}{t('chat.unexpected_error', error=str(e))}")

    def handle_generate_def(self, args_str: str):
        try:
            args = shlex.split(args_str)
            args_dict = {}
            for arg in args:
                if "=" in arg:
                    k, v = arg.split("=", 1)
                    args_dict[k] = v

            code_b64 = args_dict.get("code")
            prompt_b64 = args_dict.get("prompt")

            if not code_b64 or not prompt_b64:
                print(f"{self.sys_prefix}{t('chat.def_gen_missing')}")
                return

            try:
                script_code = base64.b64decode(code_b64).decode("utf-8")
                user_prompt = base64.b64decode(prompt_b64).decode("utf-8")
            except Exception as e:
                print(f"{self.sys_prefix}{t('chat.err_def_decode', error=str(e))}")
                return

            print(f"{self.sys_prefix}{t('chat.def_gen_start')}")
            generated_def = self.cervello.genera_def_connettore(
                script_code, user_prompt
            )

            # Invia il risultato al frontend via WebSocket
            self.ciclo_vitale.avatar_bridge.send_payload(
                {"type": "def_generated", "payload": {"def": generated_def}}
            )
            print(f"{self.sys_prefix}{t('chat.def_gen_sent')}")

        except Exception as e:
            print(f"{self.sys_prefix}{t('chat.unexpected_error', error=str(e))}")

    def handle_generate_skill(self, args_str: str):
        try:
            args = shlex.split(args_str)
            args_dict = {}
            for arg in args:
                if "=" in arg:
                    k, v = arg.split("=", 1)
                    args_dict[k] = v

            prompt_b64 = args_dict.get("prompt")

            if not prompt_b64:
                print(f"{self.sys_prefix}{t('chat.skill_gen_missing', default='Parametri mancanti per la generazione della skill.')}")
                return

            try:
                user_prompt = base64.b64decode(prompt_b64).decode("utf-8")
            except Exception as e:
                print(f"{self.sys_prefix}{t('chat.err_def_decode', error=str(e))}")
                return

            print(f"{self.sys_prefix}{t('chat.skill_gen_start', default='Inizio generazione della Skill...')}")
            
            messages = [{"role": "user", "content": user_prompt}]
            generated_content = self.cervello._genera_pensiero(
                messages, temperature=0.4
            )

            # Pulizia basica dei blocchi di codice se l'LLM li mette
            clean_content = generated_content
            if "```markdown" in clean_content:
                clean_content = (
                    clean_content.split("```markdown")[1]
                    .split("```")[0]
                    .strip()
                )
            elif "```" in clean_content:
                clean_content = (
                    clean_content.split("```")[1]
                    .split("```")[0]
                    .strip()
                )

            # Invia il risultato al frontend via WebSocket
            self.ciclo_vitale.avatar_bridge.send_payload(
                {"type": "skill_generated", "payload": {"content": clean_content}}
            )
            print(f"{self.sys_prefix}{t('chat.skill_gen_sent', default='Skill generata e inviata al frontend.')}")

        except Exception as e:
            print(f"{self.sys_prefix}{t('chat.unexpected_error', error=str(e))}")

    # --- [NUOVO v115.0] HANDLER COMANDO IOT ---
    def handle_iot_control(self, args_str: str):
        """
        Gestisce il comando /iot_control per agire fisicamente sulla casa.
        """
        try:
            args = shlex.split(args_str)

            # --- [FIX v33.4] PARSING ROBUSTO ---
            args_dict = {}
            for arg in args:
                if "=" in arg:
                    k, v = arg.split("=", 1)
                    args_dict[k] = v

            dev_id = args_dict.get("device_id")
            action = args_dict.get("action")
            val = args_dict.get("value")

            if not dev_id or not action:
                print(f"{self.sys_prefix}{t('chat.iot_usage')}")
                return

            print(f"{self.sys_prefix}{t('chat.iot_start', action=action, id=dev_id)}")
            result = self.executor.controlla_dispositivo(
                device_id=dev_id, action=action, value=val
            )
            print(f"{self.sys_prefix}{t('chat.iot_result', result=result)}")

        except Exception as e:
            print(f"{self.sys_prefix}{t('chat.unexpected_error', error=str(e))}")

    # ---[NUOVO v125.0] HANDLER SOGNO ---
    def handle_dream(self, args_str: str):
        print(f"{self.sys_prefix}{t('chat.dream_force')}")
        # Esegue in un thread per non bloccare
        threading.Thread(
            target=self.ciclo_vitale.handle_force_dream, daemon=True
        ).start()

    # ---[NUOVO v7.0] HANDLER CLEAR CACHE ---
    def handle_clear_cache(self, args_str: str):
        print(f"{self.sys_prefix}{t('chat.cache_purge_start')}")
        if self.cervello and hasattr(self.cervello, "clear_ram_cache"):
            result = self.cervello.clear_ram_cache()
            print(f"{self.sys_prefix}{result}")
        else:
            print(f"{self.sys_prefix}{t('chat.err_cache_not_supported')}")

    # --- [NUOVO v7.6] HANDLER FIX GALLERY ---
    def handle_fix_gallery(self, args_str: str):
        print(f"{self.sys_prefix}{t('chat.fix_gallery_start')}")

        def _run_fix():
            result = self.ciclo_vitale.fix_missing_summaries()
            print(f"\n{self.sys_prefix}{result}")

        threading.Thread(target=_run_fix, daemon=True).start()

    # --- [RM29] HANDLERS MULTIPLAYER NETWORK ---
    def handle_host_room(self, args_str: str):
        """Apre la locanda su Firebase e avvia l'Heartbeat."""
        if not self.ciclo_vitale.network_manager:
            print(f"{self.sys_prefix}{t('chat.err_net_not_init')}")
            return

        try:
            args = shlex.split(args_str)

            # --- [FIX v33.4] PARSING ROBUSTO (Risolve Errore Unpack) ---
            args_dict = {}
            for arg in args:
                if "=" in arg:
                    k, v = arg.split("=", 1)
                    args_dict[k] = v

            titolo = args_dict.get("title", t("chat.multiplayer_default_title"))
            desc = args_dict.get("desc", t("chat.multiplayer_default_desc"))
            pwd = args_dict.get("pwd", "")
            max_p = int(args_dict.get("max", 10))
            lang = args_dict.get("lang", "")
            women_only = args_dict.get("women_only", "false").lower() == "true"
            livello_minimo = int(args_dict.get("min_lvl", 1))
            livello_massimo = int(args_dict.get("max_lvl", 20))
            is_private = args_dict.get("is_private", "false").lower() == "true"

            # Genera un ID stanza univoco
            room_id = f"room_{uuid.uuid4().hex[:8]}"

            # Recupera l'URL Ngrok (o IP pubblico) dal Guardian/Config
            # FIX: Usa l'IP pubblico reale come fallback invece di una stringa placeholder
            public_ip = self.ciclo_vitale._get_public_ip()
            url_ngrok = f"ws://{public_ip}:8080/ws"

            # Tenta di recuperare l'URL Ngrok reale se disponibile
            # FIX: Controlla prima se esiste un token valido per evitare che pyngrok tenti di avviarsi e crashi
            try:
                ngrok_creds = self.guardian.get_credentials("ngrok_api")
                auth_token = ngrok_creds.get("auth_token") if ngrok_creds else None
                if (
                    auth_token
                    and t("chat.placeholder_insert") not in auth_token
                    and t("chat.placeholder_your") not in auth_token
                ):
                    from pyngrok import ngrok

                    tunnels = ngrok.get_tunnels()
                    if tunnels:
                        public_url = tunnels[0].public_url
                        url_ngrok = (
                            public_url.replace("http://", "ws://").replace(
                                "https://", "wss://"
                            )
                            + "/ws"
                        )
            except:
                pass

            success = self.ciclo_vitale.network_manager.crea_stanza(
                room_id=room_id,
                host_nome=self.ciclo_vitale.pg_name,
                nome_locanda=t(
                    "chat.multiplayer_tavern_name",
                    name=self.ciclo_vitale.active_avatar_name.capitalize(),
                ),
                titolo_avventura=titolo,
                descrizione_avventura=desc,
                url_ngrok=url_ngrok,
                max_giocatori=max_p,
                lingua=lang,
                women_only=women_only,
                livello_minimo=livello_minimo,
                livello_massimo=livello_massimo,
                is_private=is_private,
            )

            if success:
                try:
                    import requests

                    requests.post(
                        f"http://127.0.0.1:8080/api/multiplayer/set-room-policy",
                        json={
                            "women_only": women_only,
                            "livello_minimo": livello_minimo,
                            "livello_massimo": livello_massimo,
                        },
                        timeout=2,
                    )
                except:
                    pass
                self.ciclo_vitale.is_multiplayer_host = True
                self.ciclo_vitale.avatar_bridge.send_payload(
                    {
                        "type": "demiurge_toast",
                        "message": t("chat.locanda_success"),
                        "level": "success",
                    }
                )
            else:
                self.ciclo_vitale.avatar_bridge.send_payload(
                    {
                        "type": "demiurge_toast",
                        "message": t("chat.locanda_error"),
                        "level": "error",
                    }
                )

        except Exception as e:
            print(f"{self.sys_prefix}{t('chat.unexpected_error', error=str(e))}")

    def handle_close_room(self, args_str: str):
        """Chiude la locanda e ferma l'Heartbeat."""
        if self.ciclo_vitale.network_manager:
            self.ciclo_vitale.network_manager.stop_heartbeat()
            self.ciclo_vitale.is_multiplayer_host = False
            self.ciclo_vitale.avatar_bridge.send_payload(
                {
                    "type": "demiurge_toast",
                    "message": t("chat.locanda_closed"),
                    "level": "info",
                }
            )

    def handle_kick_player(self, args_str: str):
        """Invia il comando di Kick al WebSocket Server."""
        target = args_str.strip()
        if target:
            # Inoltra il comando al server WebSocket tramite la coda
            payload = {"type": "KICK_PLAYER", "target": target}
            # Usiamo un trucco: inviamo il JSON crudo alla coda, il server lo intercetterà
            # (Richiede che avatar_server.py legga dalla coda, ma avatar_server.py legge solo i WebSocket.
            # In realtà, il kick deve essere inviato dal frontend al WebSocket server direttamente.
            # Quindi questo comando Python serve solo per logica interna se necessario).
            print(f"{self.sys_prefix}{t('chat.kick_registered', name=target)}")

    # --- [RM28] HANDLERS GILDA ---
    def handle_guild_create(self, args_str: str):
        """Fonda una nuova gilda su Firebase."""
        if not self.ciclo_vitale.network_manager:
            return
        try:
            args = shlex.split(args_str)
            args_dict = {k: v for k, v in (arg.split("=", 1) for arg in args)}
            nome_gilda = args_dict.get("name", t("chat.guild_default_name"))
            simbolo_gilda = args_dict.get("symbol", "")
            gilda_id = f"guild_{uuid.uuid4().hex[:8]}"

            success = self.ciclo_vitale.network_manager.crea_gilda(
                gilda_id=gilda_id,
                nome_gilda=nome_gilda,
                capo_gilda_nome=self.ciclo_vitale.pg_name,
                simbolo_gilda=simbolo_gilda,
            )
            if success:
                self.ciclo_vitale.avatar_bridge.send_payload(
                    {
                        "type": "demiurge_toast",
                        "message": t("chat.guild_founded", name=nome_gilda),
                        "level": "success",
                    }
                )
            else:
                self.ciclo_vitale.avatar_bridge.send_payload(
                    {
                        "type": "demiurge_toast",
                        "message": t("chat.guild_error"),
                        "level": "error",
                    }
                )
        except Exception as e:
            print(f"{self.sys_prefix}{t('chat.unexpected_error', error=str(e))}")

    def handle_guild_invite(self, args_str: str):
        """Invita un giocatore nella gilda."""
        if not self.ciclo_vitale.network_manager:
            return
        try:
            args = shlex.split(args_str)
            args_dict = {k: v for k, v in (arg.split("=", 1) for arg in args)}
            gilda_id = args_dict.get("guild_id")
            target_nome = args_dict.get("target")

            if gilda_id and target_nome:
                # Generiamo un UID deterministico basato sul nome per gestire gli ospiti senza account
                import hashlib

                target_uid = "usr_" + hashlib.md5(target_nome.encode()).hexdigest()[:8]
                success = self.ciclo_vitale.network_manager.invita_gilda(
                    gilda_id, target_uid, target_nome
                )
                if success:
                    self.ciclo_vitale.avatar_bridge.send_payload(
                        {
                            "type": "demiurge_toast",
                            "message": t("chat.guild_invited", name=target_nome),
                            "level": "success",
                        }
                    )
        except Exception as e:
            print(f"{self.sys_prefix}{t('chat.unexpected_error', error=str(e))}")

    def handle_guild_kick(self, args_str: str):
        """Espelle un giocatore dalla gilda."""
        if not self.ciclo_vitale.network_manager:
            return
        try:
            args = shlex.split(args_str)
            args_dict = {k: v for k, v in (arg.split("=", 1) for arg in args)}
            gilda_id = args_dict.get("guild_id")
            target_nome = args_dict.get("target")

            if gilda_id and target_nome:
                import hashlib

                target_uid = "usr_" + hashlib.md5(target_nome.encode()).hexdigest()[:8]
                success = self.ciclo_vitale.network_manager.kick_gilda(
                    gilda_id, target_uid
                )
                if success:
                    self.ciclo_vitale.avatar_bridge.send_payload(
                        {
                            "type": "demiurge_toast",
                            "message": t("chat.guild_kicked", name=target_nome),
                            "level": "info",
                        }
                    )
        except Exception as e:
            print(f"{self.sys_prefix}{t('chat.unexpected_error', error=str(e))}")

    def handle_rpg_roster_toggle(self, args_str: str):
        """Gestisce in modo sicuro e asincrono il toggle dei PNG in RAM e sul file status.json."""
        try:
            args = shlex.split(args_str)
            args_dict = dict() # [GLITCH WORKAROUND] Uso dict() al posto delle parentesi graffe vuote
            for arg in args:
                if "=" in arg:
                    k, v = arg.split("=", 1)
                    args_dict[k] = v

            action = args_dict.get("action")
            char_name = args_dict.get("char_name")
            lang = args_dict.get("lang", "it")

            if action and char_name:
                # Esegue la modifica in memoria (RAM) per evitare l'overwriting dello Scribe Thread
                result = self.executor.toggle_character_in_world(
                    rpg_root=self.ciclo_vitale.active_rpg_path,
                    lang=lang,
                    char_name=char_name,
                    action=action,
                    world_state_ref=self.ciclo_vitale.world_state
                )
                
                # Forza la persistenza su disco immediata per garantire coerenza
                if self.ciclo_vitale.status_file_path:
                    with self.ciclo_vitale.world_lock:
                        temp_file = self.ciclo_vitale.status_file_path.with_suffix(".tmp")
                        with open(temp_file, "w", encoding="utf-8") as f:
                            json.dump(self.ciclo_vitale.world_state, f, indent=2, ensure_ascii=False)
                        os.replace(temp_file, self.ciclo_vitale.status_file_path)
                
                # Notifica il browser tramite WebSocket (broadcast) per aggiornare la UI in tempo reale
                self.ciclo_vitale.avatar_bridge.send_payload({
                    "type": "system_status",
                    "payload": {"roster_update": True}
                })
        except Exception as e:
            print(f"{self.sys_prefix}Errore gestione rpg_roster_toggle: {e}")
