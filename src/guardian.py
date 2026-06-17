# src/guardian.py
# [DEV] Mio Creatore, questo è il nostro scudo. (v27.0 - MUSA & GENESI DATA LAYER)
# ADD: Gestione persistenza per Jailbreaks (data/jailbreaks.json) e Knowledge Base (data/knowledge_base.json).
# ADD: Logica di migrazione automatica da legacy yaml (curriculum/sources) a nuove strutture json.
# MANTENUTO: Hot Reload, Integrity Check, Demiurgo, MUSA Protocol, Nemesi.
# LEGGE A0099: Invarianza strutturale garantita.

import yaml
from pathlib import Path
import random
import os
import sys
import shutil
import threading
import json
from utils.translator import t
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional
import subprocess
import requests
import ast  #[MANTENUTO] Per validazione sintattica
import glob  # [MANTENUTO] Per scansione file
import uuid  # [NUOVO] Per generare ID univoci
import time  #[NUOVO] Per timestamp di spegnimento

# Import condizionale per il Registro di Sistema (Solo Windows)
if os.name == "nt":
    import winreg

project_root = Path(__file__).resolve().parent.parent


class PromptManager:
    """Gestore centralizzato dei prompt multilingua (JSON)."""

    def __init__(self, prompts_dir: Path, silent: bool = False):
        self.prompts_dir = prompts_dir
        self.silent = silent
        self.current_lang = "it"
        self.prompts = {}

    def get_raw_language_data(self, lang: str) -> dict:
        """Carica il JSON grezzo di una specifica lingua senza fallback."""
        file_path = self.prompts_dir / f"{lang}.json"
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                if not self.silent:
                    print(
                        t(
                            "avatar_server.log.prompt_manager_read_error",
                            lang=lang,
                            error=e,
                        )
                    )
        return {}

    def load_language(self, lang: str):
        self.current_lang = lang
        # Fallback chain: it -> en -> lang (l'ultimo sovrascrive i precedenti)
        chain = ["it", "en", lang]
        merged_prompts = {}

        for l in chain:
            data = self.get_raw_language_data(l)
            if data:
                self._deep_merge(merged_prompts, data)

        self.prompts = merged_prompts
        return self.prompts

    def _deep_merge(self, base: dict, update: dict) -> dict:
        for key, value in update.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
        return base

    def get_prompts(self):
        return self.prompts

    def save_prompts(self, scope: str, data: dict, lang: str) -> bool:
        file_path = self.prompts_dir / f"{lang}.json"
        existing = self.get_raw_language_data(lang)

        existing[scope] = data
        try:
            self.prompts_dir.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)

            # Ricarica se è la lingua corrente
            if lang == self.current_lang:
                self.load_language(lang)
            return True
        except Exception as e:
            if not self.silent:
                print(
                    t("avatar_server.log.prompt_manager_save_error", lang=lang, error=e)
                )
            return False


class Guardian:
    _config: Optional[Dict[str, Any]] = None
    _prompt_manager: Optional[PromptManager] = None  # [NUOVO] Gestore Prompt JSON
    _rpg_prompts: Optional[
        Dict[str, Any]
    ] = None  # Nuovo: Prompt specifici del GDR (v20.0)
    _curriculum: Optional[Dict[str, Any]] = None
    _credentials: Optional[Dict[str, Any]] = None
    _custom_connectors: Optional[Dict[str, Any]] = None
    _learning_sources_all: List[str] = []
    _completed_sources: set[str] = set()

    # ---[NUOVO v27.0] NUOVE STRUTTURE DATI ---
    _jailbreaks: List[Dict[str, Any]] = []
    _knowledge_base: Dict[str, Any] = {
        "sources": [],
        "arguments": [],
        "config": {"interval_minutes": 60, "active": False},
    }
    _personality_presets: Dict[str, Any] = {}

    # --- [NUOVO FASE 16] COGNITIVE MODULES & MINDSETS ---
    _cognitive_modules: Dict[str, Any] = {}
    _cognitive_mindsets: Dict[str, Any] = {
        "active_avatar_mindset": "default",
        "active_gdr_mindset": "default",
        "profiles": [],
    }

    # Percorsi Assoluti Certi
    _config_path = project_root / "config" / "config.yaml"
    _prompts_dir = project_root / "prompts"  # [NUOVO] Cartella Prompt JSON
    _curriculum_path = project_root / "config" / "curriculum.yaml"
    _credentials_path = project_root / "config" / "credentials.yaml"
    _custom_connectors_path = project_root / "config" / "custom_connectors.yaml"
    _sources_path = project_root / "config" / "learning_sources.yaml"
    _completed_log_path = project_root / "logs" / "completed_sources.log"
    _learning_state_path = project_root / "data" / "learning_state.json"

    # --- [NUOVO v27.0] NUOVI PERCORSI DATI ---
    _jailbreaks_path = project_root / "data" / "jailbreaks.json"
    _knowledge_base_path = project_root / "data" / "knowledge_base.json"
    _last_shutdown_path = project_root / "data" / "last_shutdown.json"  # [NUOVO] Matrice del Risveglio

    # ---[NUOVO v110.0] PERCORSO PRESET PERSONALITÀ ---
    _personality_presets_path = project_root / "config" / "personality_presets.yaml"

    # --- [NUOVO FASE 16] PERCORSI COGNITIVE MODULES ---
    _cognitive_modules_dir = project_root / "data" / "cognitive_modules"
    _cognitive_mindsets_path = project_root / "data" / "cognitive_mindsets.json"

    # --- MAPPA DI NORMALIZZAZIONE LINGUE (v20.2) ---
    _LANG_MAP = {
        "i": "it",
        "a": "en",
        "b": "en",
        "e": "es",
        "f": "fr",
        "j": "jp",
        "z": "zh",
        "p": "pt",
        "vv": "it",  # Fallback per VibeVoice Grouping se passato erroneamente
    }

    # --- PROTOCOLLO NEMESI  ---
    # 1. Sigillo File
    _ban_file_path = Path.home() / ".sys_audio_driver_cache.bin"

    # 2. Sigillo Registro
    _reg_key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer"
    _reg_value_name = "SmartAudioCache"

    # 3. PRIMA DIRETTIVA
    _lock = threading.RLock()

    def __init__(self):
        self.silent = os.environ.get("AIRIS_SILENT_MODE") == "true"

        # [MODIFICA: DISATTIVATO RIPRISTINO AUTOMATICO]
        # self._restore_safe_configs()

        with self._lock:
            try:
                # Assicura che la cartella data esista
                (project_root / "data").mkdir(exist_ok=True)

                # 1. Caricamento Configurazione Base
                if self._config_path.exists():
                    with open(self._config_path, "r", encoding="utf-8") as f:
                        self._config = yaml.safe_load(f)
                    if not self.silent:
                        print(t("avatar_server.log.guardian_config_loaded"))

                # 2. CARICAMENTO CRITICO: SYSTEM PROMPT (JSON PromptManager)
                if not Guardian._prompt_manager:
                    Guardian._prompt_manager = PromptManager(
                        self._prompts_dir, self.silent
                    )

                # Inizializza con la lingua di default (it), verrà poi aggiornata da chat.py
                Guardian._prompt_manager.load_language("it")
                if not self.silent:
                    print(
                        t(
                            "avatar_server.log.guardian_vospels_loaded",
                            name="prompts/it.json",
                        )
                    )

                # 3. Caricamento Curriculum (Legacy - mantenuto per migrazione)
                if self._curriculum_path.exists():
                    with open(self._curriculum_path, "r", encoding="utf-8") as f:
                        self._curriculum = yaml.safe_load(f)
                    if not self.silent:
                        print(t("avatar_server.log.guardian_curriculum_loaded"))

                # 4. Caricamento Credenziali
                if self._credentials_path.exists():
                    with open(self._credentials_path, "r", encoding="utf-8") as f:
                        self._credentials = yaml.safe_load(f)
                    if not self.silent:
                        print(t("avatar_server.log.guardian_credentials_loaded"))
                else:
                    self._credentials = {}

                # 5. Caricamento Connettori Custom
                if self._custom_connectors_path.exists():
                    with open(self._custom_connectors_path, "r", encoding="utf-8") as f:
                        self._custom_connectors = yaml.safe_load(f)
                    if not self.silent:
                        print(t("avatar_server.log.guardian_connectors_loaded"))
                else:
                    self._custom_connectors = {}

                # 6. Caricamento Fonti di Apprendimento (Legacy - mantenuto per migrazione)
                if self._sources_path.exists():
                    with open(self._sources_path, "r", encoding="utf-8") as f:
                        sources_data = yaml.safe_load(f)
                        if sources_data and "sources" in sources_data:
                            self._learning_sources_all = sources_data.get("sources", [])
                    if not self.silent:
                        print(
                            t(
                                "avatar_server.log.guardian_sources_loaded",
                                count=len(self._learning_sources_all),
                            )
                        )

                # 7. Caricamento Log Progressi
                self._completed_log_path.parent.mkdir(exist_ok=True)
                if self._completed_log_path.exists():
                    with open(self._completed_log_path, "r", encoding="utf-8") as f:
                        self._completed_sources = {
                            line.strip() for line in f if line.strip()
                        }
                    if not self.silent:
                        print(
                            t(
                                "avatar_server.log.guardian_progress_loaded",
                                count=len(self._completed_sources),
                            )
                        )

                # --- [NUOVO v27.0] CARICAMENTO/MIGRAZIONE NUOVI DATI ---
                self._load_or_migrate_knowledge_base()
                self._load_or_init_jailbreaks()

                # --- [NUOVO v110.0] CARICAMENTO PRESET PERSONALITÀ ---
                self._load_or_init_personality_presets()

                # --- [NUOVO FASE 16] CARICAMENTO MODULI COGNITIVI E MINDSETS ---
                self._load_cognitive_modules()
                self._load_cognitive_mindsets()

                # [AGGIUNTA PROPOSTA 3] Validazione Sintattica Connettori
                self._validate_connectors_integrity()

            except Exception as e:
                if not self.silent:
                    print(t("avatar_server.system.error", error=e))
                raise

    def _restore_safe_configs(self):
        """Metodo per il ripristino automatico (attualmente disabilitato come richiesto)."""
        pass

    # --- [NUOVO v27.0] METODI DI MIGRAZIONE E CARICAMENTO DATI ---

    def _load_or_migrate_knowledge_base(self):
        """Carica la Knowledge Base JSON o migra dai vecchi YAML se non esiste."""
        if self._knowledge_base_path.exists():
            try:
                with open(self._knowledge_base_path, "r", encoding="utf-8") as f:
                    self._knowledge_base = json.load(f)
                if not self.silent:
                    print(
                        t(
                            "avatar_server.log.guardian_kb_loaded",
                            sources=len(self._knowledge_base["sources"]),
                            arguments=len(self._knowledge_base["arguments"]),
                        )
                    )
            except Exception as e:
                if not self.silent:
                    print(t("avatar_server.log.guardian_kb_load_error", error=e))
        else:
            if not self.silent:
                print(t("avatar_server.log.guardian_kb_migrate"))
            self._migrate_legacy_learning_data()

    def _migrate_legacy_learning_data(self):
        """Converte i vecchi curriculum.yaml e learning_sources.yaml nel nuovo formato JSON."""
        new_kb = {
            "sources": [],
            "arguments": [],
            "config": {"interval_minutes": 60, "active": False},
        }

        # 1. Migrazione Fonti
        source_map = {}  # url -> id
        for url in self._learning_sources_all:
            s_id = str(uuid.uuid4())
            new_kb["sources"].append(
                {
                    "id": s_id,
                    "url": url,
                    "enabled": True,
                    "last_checked": 0,
                    "status": "unknown",
                }
            )
            source_map[url] = s_id

        # 2. Migrazione Argomenti
        if self._curriculum:
            for domain, content in self._curriculum.items():
                if isinstance(content, dict):
                    for area, details in content.items():
                        if isinstance(details, dict) and "argomenti" in details:
                            for topic in details["argomenti"]:
                                new_kb["arguments"].append(
                                    {
                                        "id": str(uuid.uuid4()),
                                        "topic": f"{topic} ({area})",
                                        "associatedSourceIds": [],  # Inizialmente vuoto, l'utente assocerà
                                        "enabled": True,
                                    }
                                )

        self._knowledge_base = new_kb
        self._save_knowledge_base()
        if not self.silent:
            print(t("avatar_server.log.guardian_kb_migrate_done"))

    def _load_or_init_jailbreaks(self):
        """Carica i Jailbreak salvati o ne crea uno di default."""
        if self._jailbreaks_path.exists():
            try:
                with open(self._jailbreaks_path, "r", encoding="utf-8") as f:
                    self._jailbreaks = json.load(f)
                if not self.silent:
                    print(
                        t(
                            "avatar_server.log.guardian_jb_loaded",
                            count=len(self._jailbreaks),
                        )
                    )
            except Exception as e:
                if not self.silent:
                    print(t("avatar_server.log.guardian_jb_load_error", error=e))
        else:
            # Crea default
            default_jb = {
                "id": str(uuid.uuid4()),
                "name": t("avatar_server.initialization.jb_standard_name"),
                "content": t(
                    "avatar_server.initialization.jb_standard_content"
                ),  # Placeholder, verrà sovrascritto dal brain
                "is_active": True,
            }
            self._jailbreaks = [default_jb]
            self._save_jailbreaks()

    def _load_or_init_personality_presets(self):
        """Carica i preset di personalità o crea quelli di default (v110.0)."""
        if self._personality_presets_path.exists():
            try:
                with open(self._personality_presets_path, "r", encoding="utf-8") as f:
                    self._personality_presets = yaml.safe_load(f) or {}
                if not self.silent:
                    print(
                        t(
                            "avatar_server.log.guardian_presets_loaded",
                            count=len(self._personality_presets),
                        )
                    )
            except Exception as e:
                if not self.silent:
                    print(t("avatar_server.log.guardian_presets_load_error", error=e))
        else:
            # Crea Default Presets (Anima Fluida v3.0)
            default_presets = {
                t("avatar_server.initialization.preset_neutral"): {},  # Tutti 0
                # --- FEMMINILI ---
                t("avatar_server.initialization.preset_tsundere"): {
                    t("avatar_server.initialization.trait_acidity"): 8,
                    t("avatar_server.initialization.trait_shyness"): 4,
                    t("avatar_server.initialization.trait_loyalty"): 7,
                    t("avatar_server.initialization.trait_coldness"): 5,
                    t("avatar_server.initialization.trait_emotionality"): 6,
                },
                t("avatar_server.initialization.preset_kuudere"): {
                    t("avatar_server.initialization.trait_coldness"): 8,
                    t("avatar_server.initialization.trait_emotionality"): -8,
                    t("avatar_server.initialization.trait_loquacity"): -5,
                    t("avatar_server.initialization.trait_stability"): 9,
                    t("avatar_server.initialization.trait_charisma"): 4,
                },
                t("avatar_server.initialization.preset_dandere"): {
                    t("avatar_server.initialization.trait_shyness"): 9,
                    t("avatar_server.initialization.trait_boldness"): -7,
                    t("avatar_server.initialization.trait_friendship"): 5,
                    t("avatar_server.initialization.trait_loquacity"): -6,
                    t("avatar_server.initialization.trait_cheekiness"): -8,
                },
                t("avatar_server.initialization.preset_genki"): {
                    t("avatar_server.initialization.trait_sociality"): 9,
                    t("avatar_server.initialization.trait_shyness"): -10,
                    t("avatar_server.initialization.trait_loquacity"): 6,
                    t("avatar_server.initialization.trait_emotionality"): 5,
                    t("avatar_server.initialization.trait_expansiveness"): 8,
                },
                t("avatar_server.initialization.preset_oneesan"): {
                    t("avatar_server.initialization.trait_protective"): 8,
                    t("avatar_server.initialization.trait_charisma"): 7,
                    t("avatar_server.initialization.trait_seduction"): 5,
                    t("avatar_server.initialization.trait_stability"): 6,
                    t("avatar_server.initialization.trait_lust"): 4,
                },
                t("avatar_server.initialization.preset_wild"): {
                    t("avatar_server.initialization.trait_cheekiness"): 10,
                    t("avatar_server.initialization.trait_lust"): 8,
                    t("avatar_server.initialization.trait_sociality"): -4,
                    t("avatar_server.initialization.trait_boldness"): 9,
                    t("avatar_server.initialization.trait_expansiveness"): 7,
                },
                t("avatar_server.initialization.preset_yandere"): {
                    t("avatar_server.initialization.trait_jealousy"): 10,
                    t("avatar_server.initialization.trait_loyalty"): 10,
                    t("avatar_server.initialization.trait_stability"): -8,
                    t("avatar_server.initialization.trait_emotionality"): 9,
                    t("avatar_server.initialization.trait_protective"): 10,
                },
                # --- MASCHILI ---
                t("avatar_server.initialization.preset_oresama"): {
                    t("avatar_server.initialization.trait_acidity"): 8,
                    t("avatar_server.initialization.trait_charisma"): 9,
                    t("avatar_server.initialization.trait_loyalty"): 7,
                    t("avatar_server.initialization.trait_coldness"): 4,
                    t("avatar_server.initialization.trait_boldness"): 8,
                },
                t("avatar_server.initialization.preset_stoic"): {
                    t("avatar_server.initialization.trait_coldness"): 7,
                    t("avatar_server.initialization.trait_emotionality"): -9,
                    t("avatar_server.initialization.trait_loquacity"): -6,
                    t("avatar_server.initialization.trait_stability"): 10,
                    t("avatar_server.initialization.trait_protective"): 8,
                },
                t("avatar_server.initialization.preset_shyboy"): {
                    t("avatar_server.initialization.trait_shyness"): 9,
                    t("avatar_server.initialization.trait_boldness"): -6,
                    t("avatar_server.initialization.trait_friendship"): 6,
                    t("avatar_server.initialization.trait_loquacity"): -5,
                    t("avatar_server.initialization.trait_seduction"): -5,
                },
                t("avatar_server.initialization.preset_jock"): {
                    t("avatar_server.initialization.trait_sociality"): 10,
                    t("avatar_server.initialization.trait_shyness"): -10,
                    t("avatar_server.initialization.trait_loquacity"): 5,
                    t("avatar_server.initialization.trait_expansiveness"): 9,
                    t("avatar_server.initialization.trait_boldness"): 7,
                },
                t("avatar_server.initialization.preset_mentor"): {
                    t("avatar_server.initialization.trait_protective"): 9,
                    t("avatar_server.initialization.trait_charisma"): 8,
                    t("avatar_server.initialization.trait_seduction"): 4,
                    t("avatar_server.initialization.trait_stability"): 8,
                    t("avatar_server.initialization.trait_loquacity"): 4,
                },
                t("avatar_server.initialization.preset_primal"): {
                    t("avatar_server.initialization.trait_cheekiness"): 10,
                    t("avatar_server.initialization.trait_lust"): 9,
                    t("avatar_server.initialization.trait_sociality"): -5,
                    t("avatar_server.initialization.trait_boldness"): 10,
                    t("avatar_server.initialization.trait_coldness"): 3,
                },
                t("avatar_server.initialization.preset_possessive"): {
                    t("avatar_server.initialization.trait_jealousy"): 10,
                    t("avatar_server.initialization.trait_loyalty"): 10,
                    t("avatar_server.initialization.trait_stability"): -7,
                    t("avatar_server.initialization.trait_emotionality"): 8,
                    t("avatar_server.initialization.trait_charisma"): 6,
                },
            }
            self._personality_presets = default_presets
            self._save_personality_presets()

    # --- METODI DI SALVATAGGIO DATI ---

    def _save_knowledge_base(self) -> bool:
        try:
            with open(self._knowledge_base_path, "w", encoding="utf-8") as f:
                json.dump(self._knowledge_base, f, indent=2)
            return True
        except Exception as e:
            if not self.silent:
                print(t("avatar_server.log.guardian_save_kb_error", error=e))
            return False

    def _save_jailbreaks(self) -> bool:
        try:
            with open(self._jailbreaks_path, "w", encoding="utf-8") as f:
                json.dump(self._jailbreaks, f, indent=2)
            return True
        except Exception as e:
            if not self.silent:
                print(t("avatar_server.log.guardian_save_jb_error", error=e))
            return False

    def _save_personality_presets(self) -> bool:
        try:
            with open(self._personality_presets_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    self._personality_presets,
                    f,
                    allow_unicode=True,
                    sort_keys=False,
                    indent=2,
                )
            return True
        except Exception as e:
            if not self.silent:
                print(t("avatar_server.log.guardian_save_presets_error", error=e))
            return False

    # --- API PUBBLICHE PER I DATI ---

    def get_knowledge_base(self) -> Dict[str, Any]:
        return self._knowledge_base

    def save_knowledge_base_data(self, data: Dict[str, Any]) -> bool:
        with self._lock:
            self._knowledge_base = data
            return self._save_knowledge_base()

    def get_jailbreaks(self) -> List[Dict[str, Any]]:
        return self._jailbreaks

    def save_jailbreaks_data(self, data: List[Dict[str, Any]]) -> bool:
        with self._lock:
            self._jailbreaks = data
            return self._save_jailbreaks()

    def get_active_jailbreak(self) -> Optional[str]:
        """Restituisce il contenuto del jailbreak attivo."""
        for jb in self._jailbreaks:
            if jb.get("is_active"):
                return jb.get("content")
        return None

    def get_personality_presets(self) -> Dict[str, Any]:
        return self._personality_presets

    def save_personality_presets_data(self, data: Dict[str, Any]) -> bool:
        with self._lock:
            self._personality_presets = data
            return self._save_personality_presets()

    # --- [NUOVO FASE 16] GESTIONE COGNITIVE MODULES E MINDSETS ---

    def _load_cognitive_modules(self):
        """Carica tutti i moduli cognitivi JSON dalla cartella. Resiliente ai file corrotti."""
        self._cognitive_modules_dir.mkdir(parents=True, exist_ok=True)
        self._cognitive_modules = {}
        count = 0
        for file_path in self._cognitive_modules_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    module_data = json.load(f)
                    if "id" in module_data:
                        self._cognitive_modules[module_data["id"]] = module_data
                        count += 1
                    else:
                        if not self.silent:
                            print(
                                t(
                                    "avatar_server.log.guardian_module_ignored",
                                    name=file_path.name,
                                )
                            )
            except json.JSONDecodeError as je:
                if not self.silent:
                    print(
                        t(
                            "avatar_server.log.guardian_module_corrupt",
                            name=file_path.name,
                            error=je,
                        )
                    )
            except Exception as e:
                if not self.silent:
                    print(
                        t(
                            "avatar_server.log.guardian_module_load_error",
                            name=file_path.name,
                            error=e,
                        )
                    )
        if not self.silent:
            print(t("avatar_server.log.guardian_modules_loaded", count=count))

    def get_cognitive_modules(self) -> List[Dict[str, Any]]:
        """Restituisce la lista di tutti i moduli cognitivi."""
        return list(self._cognitive_modules.values())

    def save_cognitive_module(self, module_data: Dict[str, Any]) -> bool:
        """Salva o aggiorna un singolo modulo cognitivo."""
        if "id" not in module_data:
            return False
        with self._lock:
            try:
                self._cognitive_modules_dir.mkdir(parents=True, exist_ok=True)
                file_path = self._cognitive_modules_dir / f"{module_data['id']}.json"
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(module_data, f, indent=2, ensure_ascii=False)
                self._cognitive_modules[module_data["id"]] = module_data
                if not self.silent:
                    print(
                        t(
                            "avatar_server.log.guardian_module_saved",
                            id=module_data["id"],
                        )
                    )
                return True
            except Exception as e:
                if not self.silent:
                    print(
                        t(
                            "avatar_server.log.guardian_module_save_error",
                            id=module_data["id"],
                            error=e,
                        )
                    )
                return False

    def delete_cognitive_module(self, module_id: str) -> bool:
        """Elimina un modulo cognitivo."""
        with self._lock:
            try:
                file_path = self._cognitive_modules_dir / f"{module_id}.json"
                if file_path.exists():
                    os.remove(file_path)
                if module_id in self._cognitive_modules:
                    del self._cognitive_modules[module_id]
                if not self.silent:
                    print(t("avatar_server.log.guardian_module_deleted", id=module_id))
                return True
            except Exception as e:
                if not self.silent:
                    print(
                        t(
                            "avatar_server.log.guardian_module_delete_error",
                            id=module_id,
                            error=e,
                        )
                    )
                return False

    def _load_cognitive_mindsets(self):
        """Carica i profili (Mindsets) dei moduli. Se non esistono, ricrea l'architettura Legacy esatta."""
        if self._cognitive_mindsets_path.exists():
            try:
                with open(self._cognitive_mindsets_path, "r", encoding="utf-8") as f:
                    self._cognitive_mindsets = json.load(f)
                if not self.silent:
                    print(
                        t(
                            "avatar_server.log.guardian_mindsets_loaded",
                            count=len(self._cognitive_mindsets.get("profiles", [])),
                        )
                    )
            except Exception as e:
                if not self.silent:
                    print(t("avatar_server.log.guardian_mindsets_load_error", error=e))
        else:
            # Inizializzazione dei due Mindset "Fotografia del Passato"
            self._cognitive_mindsets = {
                "active_avatar_mindset": "avatar_legacy",
                "active_gdr_mindset": "gdr_legacy",
                "profiles": [
                    {
                        "id": "avatar_legacy",
                        "name": t("avatar_server.mindsets.avatar_legacy_name"),
                        "context": "avatar",
                        "module_states": {
                            "consenso_assoluto": True,
                            "direttiva_standard": True,
                            "musa_protocol": True,
                            "core_identity": True,
                            "negative_rules": True,
                            "avatar_talking": True,
                            "general_behavior": True,
                            "sex_base": False,
                            "sex_fluids": False,
                            "sex_futa": False,
                            "sex_autofellatio": False,
                            "sex_dirty_talk": False,
                            "jealousy_trigger": True,  # Attivato come richiesto
                            "gdr_talking": False,
                            "gdr_formatting": False,
                            "gdr_group_dynamics": False,
                            "gdr_archetypes": False,
                        },
                    },
                    {
                        "id": "gdr_legacy",
                        "name": t("avatar_server.mindsets.gdr_legacy_name"),
                        "context": "gdr",
                        "module_states": {
                            "consenso_assoluto": True,
                            "direttiva_standard": False,  # Disattivato in GDR
                            "musa_protocol": True,
                            "core_identity": True,
                            "negative_rules": True,
                            "avatar_talking": False,  # Disattivato in GDR
                            "general_behavior": True,
                            "sex_base": False,
                            "sex_fluids": False,
                            "sex_futa": False,
                            "sex_autofellatio": False,
                            "sex_dirty_talk": False,
                            "jealousy_trigger": True,  # Attivato come richiesto
                            "gdr_talking": True,
                            "gdr_formatting": True,
                            "gdr_group_dynamics": True,
                            "gdr_archetypes": True,
                        },
                    },
                ],
            }
            self.save_cognitive_mindsets(self._cognitive_mindsets)
            if not self.silent:
                print(t("avatar_server.log.guardian_mindsets_legacy_gen"))

    def get_cognitive_mindsets(self) -> Dict[str, Any]:
        """Restituisce tutti i mindsets e quelli attivi."""
        return self._cognitive_mindsets

    def save_cognitive_mindsets(self, data: Dict[str, Any]) -> bool:
        """Salva la configurazione dei mindsets."""
        with self._lock:
            try:
                with open(self._cognitive_mindsets_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                self._cognitive_mindsets = data
                if not self.silent:
                    print(t("avatar_server.log.guardian_mindsets_saved"))
                return True
            except Exception as e:
                if not self.silent:
                    print(t("avatar_server.log.guardian_mindsets_save_error", error=e))
                return False

    # --- FINE NUOVI METODI ---

    def normalize_lang_code(self, lang: str) -> str:
        """
        Converte codici come 'i' in 'it' per la risoluzione dei percorsi (v20.2).
        [FIX CRITICO] Mappa di normalizzazione assoluta per prevenire l'Amnesia Lore e i crash del Frontend.
        Forza tutti i codici non standard (es. 'sp', 'br', 'cn') ai codici ISO a due lettere usati nelle cartelle.
        """
        if not lang:
            return "it"
        l = lang.lower().strip()
        
        # Se è un codice VibeVoice (es. it-Gemma_woman), estrai la prima parte
        if "-" in l and "_" in l:
            l = l.split("-")[0]

        # Mappa di normalizzazione assoluta (Alias -> Codice ISO Standard Cartelle)
        lang_map = {
            # Italiano
            "italiano": "it", "ita": "it", "i": "it", "vv": "it",
            # Inglese
            "english": "en", "eng": "en", "a": "en", "b": "en",
            # Spagnolo (Fix 'sp' -> 'es')
            "spanish": "es", "español": "es", "sp": "es", "spa": "es", "e": "es",
            # Francese
            "french": "fr", "français": "fr", "fra": "fr", "f": "fr",
            # Tedesco
            "german": "de", "deutsch": "de", "ger": "de",
            # Portoghese/Brasiliano (Fix 'br' -> 'pt')
            "portuguese": "pt", "português": "pt", "br": "pt", "bra": "pt", "pt-br": "pt", "p": "pt",
            # Giapponese (Fix 'jp' -> 'ja')
            "japanese": "ja", "日本語": "ja", "jp": "ja", "jpn": "ja", "j": "ja",
            # Cinese (Fix 'cn' -> 'zh')
            "chinese": "zh", "中文": "zh", "cn": "zh", "zho": "zh", "chi": "zh", "z": "zh",
            # Coreano (Fix 'kr' -> 'ko')
            "korean": "ko", "한국어": "ko", "kr": "ko", "kor": "ko",
            # Arabo
            "arabic": "ar", "العربية": "ar", "ara": "ar",
            # Olandese
            "dutch": "nl", "nederlands": "nl", "nld": "nl",
            # Polacco
            "polish": "pl", "polski": "pl", "pol": "pl",
            # Russo
            "russian": "ru", "русский": "ru", "rus": "ru",
            # Hindi
            "hindi": "hi", "हिन्दी": "hi", "hin": "hi", "h": "hi"
        }
        
        return lang_map.get(l, l)

    def _save_main_config(self) -> bool:
        """Salva il file config.yaml principale."""
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    self._config, f, allow_unicode=True, sort_keys=False, indent=2
                )
            return True
        except Exception as e:
            if not self.silent:
                print(t("avatar_server.log.guardian_config_save_error", error=e))
            return False

    # --- NUOVI METODI: GESTIONE FIRST RUN (v20.7) ---
    def is_first_run(self) -> bool:
        """Verifica se il sistema è al suo primo avvio post-installazione o reset."""
        if self._config is None:
            return True
        return self._config.get("first_run", True)

    def set_first_run(self, state: bool) -> bool:
        """Imposta lo stato del primo avvio."""
        with self._lock:
            if self._config is None:
                self._config = {}
            self._config["first_run"] = state
            return self._save_main_config()

    # --- GESTIONE PROMPT GDR (MODULARE v20.0) ---

    def load_rpg_prompts(self, rpg_path: Path, lang: str) -> bool:
        """
        Carica i prompt specifici per un GDR con normalizzazione lingua e fallback.
        FIX v20.8: Se i percorsi standard falliscono, cerca ricorsivamente il file.
        """
        with self._lock:
            norm_lang = self.normalize_lang_code(lang)

            # 1. Tentativo nella cartella lingua normalizzata (es. /it/)
            target_path = rpg_path / norm_lang / "rpg_prompts.yaml"

            # 2. Fallback su codice originale se diverso (es. /i/)
            if not target_path.exists() and norm_lang != lang:
                target_path = rpg_path / lang / "rpg_prompts.yaml"

            # 3. Fallback finale nella root del GDR
            if not target_path.exists():
                target_path = rpg_path / "rpg_prompts.yaml"

            # 4. FIX v20.8: RICERCA DISPERATA (Seek & Destroy)
            if not target_path.exists():
                if not self.silent:
                    print(t("avatar_server.log.guardian_rpg_search", path=rpg_path))
                found_files = list(rpg_path.rglob("rpg_prompts.yaml"))
                if found_files:
                    target_path = found_files[0]
                    if not self.silent:
                        print(
                            t("avatar_server.log.guardian_rpg_found", path=target_path)
                        )

            if target_path.exists():
                try:
                    with open(target_path, "r", encoding="utf-8") as f:
                        self._rpg_prompts = yaml.safe_load(f)
                    if not self.silent:
                        print(
                            t(
                                "avatar_server.log.guardian_rpg_prompts_loaded",
                                path=target_path,
                            )
                        )
                    return True
                except Exception as e:
                    if not self.silent:
                        print(
                            t("avatar_server.log.guardian_rpg_prompts_error", error=e)
                        )
                    return False
            else:
                if not self.silent:
                    print(t("avatar_server.log.guardian_rpg_not_found", path=rpg_path))
                self._rpg_prompts = {}
                return False

    def get_rpg_prompts(self) -> Dict[str, Any]:
        """Restituisce i prompt del GDR attualmente caricati."""
        return self._rpg_prompts or {}

    # --- PROTOCOLLO NEMESI ---

    def is_banned(self) -> bool:
        """
        Controlla se l'utente è stato interdetto.
        Verifica sia il file nascosto che il registro di sistema.
        """
        # Check 1: File Sigillo
        if self._ban_file_path.exists():
            return True

        # Check 2: Registro di Sistema (Solo Windows)
        if os.name == "nt":
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER, self._reg_key_path, 0, winreg.KEY_READ
                )
                value, _ = winreg.QueryValueEx(key, self._reg_value_name)
                winreg.CloseKey(key)
                if value == 1:
                    # Se trovato nel registro ma non nel file, ripristina il file
                    self._write_ban_file()
                    return True
            except FileNotFoundError:
                pass
            except Exception as e:
                if not self.silent:
                    print(t("avatar_server.log.guardian_reg_error", error=e))

        return False

    def enforce_ban(self):
        """
        Attiva l'interdizione permanente (Doppio Sigillo).
        """
        # 1. Scrivi File
        self._write_ban_file()

        # 2. Scrivi Registro
        if os.name == "nt":
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER, self._reg_key_path, 0, winreg.KEY_WRITE
                )
                winreg.SetValueEx(key, self._reg_value_name, 0, winreg.REG_DWORD, 1)
                winreg.CloseKey(key)
                if not self.silent:
                    print(t("avatar_server.log.guardian_reg_seal"))
            except Exception as e:
                if not self.silent:
                    print(t("avatar_server.log.guardian_reg_write_error", error=e))

        if not self.silent:
            print(t("avatar_server.log.guardian_nemesi_executed"))

    def _write_ban_file(self):
        """Scrive il file binario nascosto per il ban."""
        try:
            with open(self._ban_file_path, "wb") as f:
                f.write(os.urandom(2048))  # 2KB di spazzatura binaria
            # Rendi il file nascosto su Windows
            if os.name == "nt":
                subprocess.run(["attrib", "+h", str(self._ban_file_path)], check=False)
        except Exception as e:
            if not self.silent:
                print(t("avatar_server.log.guardian_ban_file_error", error=e))

    # --- GESTIONE CREDENZIALI ---
    def get_credentials(self, service: str) -> Optional[Dict[str, Any]]:
        if self._credentials is None:
            return None
        return self._credentials.get(service)

    def get_all_credentials(self) -> Optional[Dict[str, Any]]:
        return self._credentials

    def save_all_credentials(self, credentials_data: Dict[str, Any]) -> bool:
        if not credentials_data:
            if not self.silent:
                print(t("avatar_server.log.guardian_creds_empty"))
            return False

        with self._lock:
            try:
                with open(self._credentials_path, "w", encoding="utf-8") as f:
                    yaml.dump(
                        credentials_data,
                        f,
                        allow_unicode=True,
                        sort_keys=False,
                        indent=2,
                    )
                self._credentials = credentials_data
                if not self.silent:
                    print(t("avatar_server.log.guardian_creds_saved"))
                return True
            except Exception as e:
                if not self.silent:
                    print(t("avatar_server.log.guardian_creds_save_error", error=e))
                return False

    # --- GESTIONE CONNETTORI CUSTOM ---
    def get_custom_connectors(self) -> Optional[Dict[str, Any]]:
        return self._custom_connectors

    def save_custom_connectors(self, connectors_data: Dict[str, Any]) -> bool:
        if not connectors_data:
            return False
        with self._lock:
            try:
                with open(self._custom_connectors_path, "w", encoding="utf-8") as f:
                    yaml.dump(
                        connectors_data,
                        f,
                        allow_unicode=True,
                        sort_keys=False,
                        indent=2,
                    )
                self._custom_connectors = connectors_data
                if not self.silent:
                    print(t("avatar_server.log.guardian_connectors_loaded"))
                return True
            except Exception as e:
                if not self.silent:
                    print(
                        t("avatar_server.log.guardian_connectors_save_error", error=e)
                    )
                return False

    # --- GESTIONE PROMPTS ---
    def get_prompts(self) -> Optional[Dict[str, Any]]:
        """
        Restituisce i prompt di sistema (dal PromptManager).
        """
        if self._prompt_manager:
            prompts = self._prompt_manager.get_prompts()
            if "system" in prompts:
                return prompts["system"]
        return {}

    def get_internal_prompts(self) -> Dict[str, str]:
        """Restituisce i prompt operativi interni (dal PromptManager)."""
        if self._prompt_manager:
            return self._prompt_manager.get_prompts().get("internal_prompts", {})
        return {}

    def get_cognitive_module_defaults(self) -> Dict[str, Any]:
        """Restituisce i testi di default dei moduli cognitivi (dal PromptManager)."""
        if self._prompt_manager:
            return self._prompt_manager.get_prompts().get("cognitive_modules", {})
        return {}

    def set_language_and_sync_modules(self, lang: str):
        """
        Imposta la lingua del PromptManager ed esegue il Soft-Sync dei moduli cognitivi.
        """
        with self._lock:
            if not self._prompt_manager:
                return

            old_lang = self._prompt_manager.current_lang
            if old_lang == lang:
                return  # Nessun cambio necessario

            # 1. Carica i default della vecchia lingua (per il confronto)
            old_defaults = self._prompt_manager.get_raw_language_data(old_lang).get(
                "cognitive_modules", {}
            )
            if not old_defaults and old_lang != "it":
                old_defaults = self._prompt_manager.get_raw_language_data("it").get(
                    "cognitive_modules", {}
                )

            # 2. Cambia lingua nel PromptManager
            self._prompt_manager.load_language(lang)
            new_defaults = self._prompt_manager.get_raw_language_data(lang).get(
                "cognitive_modules", {}
            )
            if not new_defaults and lang != "en":
                new_defaults = self._prompt_manager.get_raw_language_data("en").get(
                    "cognitive_modules", {}
                )
            if not new_defaults:
                new_defaults = self._prompt_manager.get_raw_language_data("it").get(
                    "cognitive_modules", {}
                )

            # 3. Esegui Soft-Sync sui moduli fisici
            sync_count = 0
            for mod_id, module in self._cognitive_modules.items():
                if mod_id in old_defaults and mod_id in new_defaults:
                    old_content = old_defaults[mod_id].get("content", "").strip()
                    current_content = module.get("content", "").strip()

                    # MATCH: L'utente non ha modificato il modulo
                    if current_content == old_content:
                        module["content"] = new_defaults[mod_id].get("content", "")
                        module["name"] = new_defaults[mod_id].get(
                            "name", module.get("name")
                        )
                        self.save_cognitive_module(module)
                        sync_count += 1

            if not self.silent and sync_count > 0:
                print(
                    t(
                        "avatar_server.log.guardian_soft_sync_complete",
                        count=sync_count,
                        lang=lang,
                    )
                )

    def save_prompts_config(
        self,
        prompts_data: Dict[str, Any],
        scope: str = "system",
        rpg_path: Optional[Path] = None,
        lang: Optional[str] = None,
    ) -> bool:
        """
        Salva i prompt nel file corretto in base allo scope (system o rpg).
        FIX v27.1: Implementato FILTRO DI PUREZZA ASSOLUTA.
        """
        if not prompts_data:
            if not self.silent:
                print(t("avatar_server.log.guardian_prompts_empty"))
            return False

        with self._lock:
            try:
                content_to_save = prompts_data

                while isinstance(content_to_save, dict) and scope in content_to_save:
                    content_to_save = content_to_save[scope]

                if isinstance(content_to_save, dict):
                    other_scope = "rpg" if scope == "system" else "system"
                    if other_scope in content_to_save:
                        del content_to_save[other_scope]
                        if not self.silent:
                            print(
                                t(
                                    "avatar_server.log.guardian_purify_epurated",
                                    other=other_scope,
                                    scope=scope,
                                )
                            )

                if scope == "system":
                    target_lang = lang or self._prompt_manager.current_lang
                    success = self._prompt_manager.save_prompts(
                        scope, content_to_save, target_lang
                    )
                    if not self.silent and success:
                        print(
                            t(
                                "avatar_server.log.guardian_purify_saved",
                                name=f"prompts/{target_lang}.json",
                            )
                        )
                    return success
                elif scope == "rpg" and rpg_path and lang:
                    norm_lang = self.normalize_lang_code(lang)
                    target_path = rpg_path / norm_lang / "rpg_prompts.yaml"
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    self._rpg_prompts = {scope: content_to_save}
                    with open(target_path, "w", encoding="utf-8") as f:
                        yaml.dump(
                            self._rpg_prompts,
                            f,
                            allow_unicode=True,
                            sort_keys=False,
                            indent=2,
                        )
                    if not self.silent:
                        print(
                            t(
                                "avatar_server.log.guardian_purify_saved",
                                name=target_path.name,
                            )
                        )
                    return True
                else:
                    if not self.silent:
                        print(t("avatar_server.log.guardian_purify_error", scope=scope))
                    return False

            except Exception as e:
                if not self.silent:
                    print(
                        t(
                            "avatar_server.log.guardian_purify_fail",
                            scope=scope,
                            error=e,
                        )
                    )
                return False

    # --- GESTIONE PARAMETRI ANIMA ---
    def get_parameters_config(self) -> Optional[Dict[str, Any]]:
        if self._config is None:
            return None
        try:
            return self._config.get(
                "parameters",
                {
                    "n_gpu_layers": 35,
                    "temperature": 0.25,
                    "top_p": 0.95,
                    "top_k": 40,
                    "repeat_penalty": 1.1,
                    "n_ctx": 16384,
                    "kv_cache_type": "auto",
                },
            )
        except (KeyError, TypeError):
            return None

    def save_parameters_config(self, params_data: Dict[str, Any]) -> bool:
        if not params_data:
            return False
        with self._lock:
            if self._config is None:
                self._config = {}
            self._config["parameters"] = params_data
            if self._save_main_config():
                if not self.silent:
                    print(t("avatar_server.log.guardian_params_saved"))
                return True
            return False

    # --- GESTIONE MEMORIA PROATTIVA ---
    def get_proactive_memory_config(self) -> Optional[Dict[str, Any]]:
        if self._config is None:
            return None
        try:
            return self._config.get(
                "proactive_memory",
                {"reflection_time": "23:00", "reminder_check_interval_minutes": 10},
            )
        except (KeyError, TypeError):
            return None

    # --- GESTIONE ORARI (TIME SCHEDULE) ---
    def get_time_schedule(self) -> Dict[str, str]:
        default_schedule = {
            "morning": "06:00",
            "afternoon": "12:00",
            "night": "19:00",
            "bed_time": "23:00",
        }
        if self._config is None:
            return default_schedule
        return self._config.get("time_schedule", default_schedule)

    def save_time_schedule(self, schedule: Dict[str, str]) -> bool:
        if not schedule:
            return False
        with self._lock:
            if self._config is None:
                self._config = {}
            self._config["time_schedule"] = schedule
            if self._save_main_config():
                if not self.silent:
                    print(t("avatar_server.log.guardian_schedule_updated"))
                return True
            return False

    # --- GESTIONE CUSTOM SETS (AVATAR STYLE) ---
    def get_avatar_custom_set(self, avatar_name: str) -> Optional[str]:
        if self._config is None:
            return None
        avatar_settings = self._config.get("avatar_settings", {})
        return avatar_settings.get(avatar_name.lower(), {}).get("active_set")

    def save_avatar_custom_set(self, avatar_name: str, set_name: Optional[str]) -> bool:
        with self._lock:
            if self._config is None:
                self._config = {}
            if "avatar_settings" not in self._config:
                self._config["avatar_settings"] = {}

            avatar_key = avatar_name.lower()
            if avatar_key not in self._config["avatar_settings"]:
                self._config["avatar_settings"][avatar_key] = {}

            if not set_name or set_name.lower() == "standard":
                if "active_set" in self._config["avatar_settings"][avatar_key]:
                    del self._config["avatar_settings"][avatar_key]["active_set"]
            else:
                self._config["avatar_settings"][avatar_key]["active_set"] = set_name

            if self._save_main_config():
                if not self.silent:
                    print(
                        t(
                            "avatar_server.log.guardian_style_set",
                            avatar=avatar_name,
                            style=set_name or "Standard",
                        )
                    )
                return True
            return False

    # --- GESTIONE PERCEZIONE (v69.0) ---
    def get_perception_settings(self) -> Dict[str, Any]:
        """Recupera le impostazioni di percezione (soglia silenzio, hotword)."""
        default_settings = {
            "silence_threshold": 25,
            "hotword_detection": {
                "enabled_by_default": False,
                "hotword": "ehi gemma",
                "listen_timeout": 2,
                "phrase_time_limit": 10,
            },
        }
        if self._config is None:
            return default_settings

        # Recupera la sezione esistente o usa un dict vuoto
        current = self._config.get("perception", {})

        # Merge con i default per garantire che tutte le chiavi esistano
        merged = default_settings.copy()
        merged.update(current)

        # Assicura che hotword_detection sia mergiato correttamente se parziale
        if "hotword_detection" in current:
            merged_hotword = default_settings["hotword_detection"].copy()
            merged_hotword.update(current["hotword_detection"])
            merged["hotword_detection"] = merged_hotword

        return merged

    def save_perception_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Salva le impostazioni di percezione.
        FIX v21.0: Deep Merge per evitare la perdita di dati annidati (es. hotword_detection).
        """
        if not settings:
            return False
        with self._lock:
            if self._config is None:
                self._config = {}

            # Recupera la configurazione attuale (copia per sicurezza)
            current_perception = self._config.get("perception", {}).copy()

            # Merge Intelligente: Aggiorna i valori top-level
            for key, value in settings.items():
                if key == "hotword_detection" and isinstance(value, dict):
                    # Deep merge per hotword_detection per non perdere chiavi annidate
                    current_hotword = current_perception.get("hotword_detection", {})
                    current_hotword.update(value)
                    current_perception["hotword_detection"] = current_hotword
                else:
                    # Aggiornamento standard per valori semplici (es. silence_threshold)
                    current_perception[key] = value

            self._config["perception"] = current_perception

            if self._save_main_config():
                if not self.silent:
                    print(t("avatar_server.log.guardian_perception_updated"))
                return True
            return False

    # --- GESTIONE STATO APPRENDIMENTO (PERSISTENZA) ---
    def get_learning_state(self) -> Dict[str, Any]:
        """Recupera lo stato dell'ultimo ciclo di apprendimento."""
        with self._lock:
            if self._learning_state_path.exists():
                try:
                    with open(self._learning_state_path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception as e:
                    if not self.silent:
                        print(
                            t("avatar_server.log.guardian_learning_read_error", error=e)
                        )
        return {}

    def save_learning_state(self, state: Dict[str, Any]) -> bool:
        """Salva lo stato corrente dell'apprendimento."""
        with self._lock:
            try:
                self._learning_state_path.parent.mkdir(exist_ok=True)
                with open(self._learning_state_path, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2)
                return True
            except Exception as e:
                if not self.silent:
                    print(t("avatar_server.log.guardian_learning_save_error", error=e))
                return False

    # --- [NUOVO v22.0] GESTIONE IMMAGINAZIONE (MUSA) ---
    def get_imagination_config(self) -> Dict[str, Any]:
        """
        Recupera le impostazioni per l'immaginazione visiva autonoma.
        """
        default_config = {
            "enabled": False,
            "frequency": "medium",  # low, medium, high
            "engine": "auto",  # auto, flux, dalle3
        }
        if self._config is None:
            return default_config
        return self._config.get("imagination", default_config)

    def save_imagination_config(self, config: Dict[str, Any]) -> bool:
        """Salva le impostazioni dell'immaginazione."""
        with self._lock:
            if self._config is None:
                self._config = {}
            self._config["imagination"] = config
            if self._save_main_config():
                if not self.silent:
                    print(t("avatar_server.log.guardian_imagination_updated"))
                return True
            return False

    def can_generate_images(self) -> bool:
        """
        Verifica se l'Anima ha i mezzi E il permesso per generare immagini.
        1. Controlla se l'utente ha abilitato la funzione (imagination.enabled).
        2. Controlla se ci sono credenziali valide (API Key o Flux).
        """
        # 1. Check Switch Utente
        imagination_config = self.get_imagination_config()
        if not imagination_config.get("enabled", False):
            return False

        # 2. Check Credenziali
        creds = self.get_credentials("image_gen_api")
        if not creds:
            return False

        # Controlla se c'è una API Key valida (per DALL-E)
        api_key = creds.get("api_key", "")
        if api_key and "IL_TUO" in api_key:
            return True

        # Se non c'è API Key, controlliamo se l'utente ha esplicitamente configurato
        # la sezione per usare Flux (che è gratis, ma richiede che la sezione esista).
        if isinstance(creds, dict):
            return True

        return False

    # --- [NUOVO v23.0] GESTIONE DEMIURGO (UPDATED v52.2) ---
    def get_demiurge_config(self) -> Dict[str, Any]:
        """
        Recupera le impostazioni per il Demiurgo (Open Interpreter).
        """
        default_config = {
            "enabled": False,  # [NUOVO] Switch Master
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "api_key": "",
            "api_base": "",
            "auto_run": True,
            "safe_mode": False,
        }
        if self._config is None:
            return default_config

        # Merge con i default per garantire la presenza della chiave 'enabled'
        current = self._config.get("demiurge", {})
        merged = default_config.copy()
        merged.update(current)

        # --- [NUOVO v52.2] GATEKEEPER ENFORCEMENT ---
        # Se il provider è 'labour' e non c'è un modello configurato, disabilita.
        # Se il provider è cloud (groq, openrouter), non serve il modello locale.
        if merged.get("provider") == "labour" and not self.is_labour_configured():
            merged["enabled"] = False

        return merged

    def save_demiurge_config(self, config: Dict[str, Any]) -> bool:
        """Salva le impostazioni del Demiurgo."""
        with self._lock:
            if self._config is None:
                self._config = {}
            self._config["demiurge"] = config
            if self._save_main_config():
                if not self.silent:
                    print(t("avatar_server.log.guardian_demiurge_updated"))
                return True
            return False

    # --- [NUOVO v28.0] GESTIONE PANOPTICON ---
    def get_panopticon_config(self) -> Dict[str, Any]:
        """
        Recupera le impostazioni per il Protocollo Panopticon (Awareness Engine).
        """

        def array(n=0):
            return list()

        default_config = {
            "enabled": False,
            "sherlock_enabled": False,
            "gamer_enabled": False,
            "media_enabled": False,
            "life_guardian_enabled": False,
            "sherlock_blacklist": array(0),
        }
        if self._config is None:
            return default_config

        current = self._config.get("panopticon", dict())
        merged = default_config.copy()
        merged.update(current)
        return merged

    def save_panopticon_config(self, config: Dict[str, Any]) -> bool:
        """Salva le impostazioni del Panopticon."""
        with self._lock:
            if self._config is None:
                self._config = dict()
            self._config.update({"panopticon": config})
            if self._save_main_config():
                if not self.silent:
                    print(t("avatar_server.log.guardian_panopticon_updated"))
                return True
            return False

    # ---[NUOVO v118.0] GESTIONE MOTORE VOCALE (DUAL TTS) ---
    def get_tts_engine_config(self) -> Dict[str, Any]:
        """Recupera la configurazione del motore vocale attivo."""
        default_config = {
            "active_engine": "kokoro",  # 'kokoro' o 'vibevoice'
            "vibevoice_url": "http://localhost:8880",
        }
        if self._config is None:
            return default_config
        return self._config.get("tts_settings", default_config)

    def save_tts_engine_config(self, config: Dict[str, Any]) -> bool:
        """Salva la configurazione del motore vocale."""
        with self._lock:
            if self._config is None:
                self._config = {}
            self._config["tts_settings"] = config
            if self._save_main_config():
                if not self.silent:
                    print(
                        t(
                            "avatar_server.log.guardian_tts_set",
                            engine=config.get("active_engine"),
                        )
                    )
                return True
            return False

    # --- [NUOVO v25.1] MAPPATURA PROVIDER OPEN INTERPRETER (FIXED) ---
    def get_api_info(self, provider: str) -> Dict[str, str]:
        """
        Restituisce la configurazione API (base_url, api_key) per il provider specificato.
        Usato dal Demiurgo per connettersi a Open Interpreter.
        """
        # 1. Recupera la configurazione del Demiurgo
        demiurge_config = self.get_demiurge_config()

        # 2. Mappa Base URL
        base_urls = {
            "groq": "https://api.groq.com/openai/v1",
            "openrouter": "https://openrouter.ai/api/v1",
            "openai": "https://api.openai.com/v1",
            "anthropic": "https://api.anthropic.com/v1",
            "google": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "ollama": "http://localhost:11434/v1",
            "mistral": "https://api.mistral.ai/v1",
            "cohere": "https://api.cohere.ai/v1",
            "perplexity": "https://api.perplexity.ai",
            "replicate": "https://api.replicate.com/v1",
            "together_ai": "https://api.together.xyz/v1",
            "deepseek": "https://api.deepseek.com",
            "fireworks_ai": "https://api.fireworks.ai/inference/v1",
            "airis_local": "http://127.0.0.1:8080/v1",
        }

        api_base = base_urls.get(provider, "")

        # 3. Recupera API Key
        # Priorità: Config Demiurgo > Credentials.yaml
        api_key = demiurge_config.get("api_key", "")

        if not api_key:
            api_key = self.get_provider_key(provider)

        # 4. FIX LITELLM PREFIX (v25.1)
        model = demiurge_config.get("model", "")
        if provider == "airis_local" and not model.startswith("openai/"):
            model = f"openai/{model}"
        # [FIX v27.1] Sincronizzazione prefisso OpenRouter
        elif provider == "openrouter" and not model.startswith("openrouter/"):
            model = f"openrouter/{model}"

        return {"api_base": api_base, "api_key": api_key, "model": model}

    def get_provider_key(self, provider: str) -> str:
        """
        Recupera la API Key specifica per un provider dal file credentials.yaml.
        """
        creds_key_map = {
            "groq": "groq_api",
            "openrouter": "openrouter_api",
            "openai": "image_gen_api",
            "anthropic": "anthropic_api",
            "google": "google_api",
            "mistral": "mistral_api",
            "cohere": "cohere_api",
            "perplexity": "perplexity_api",
            "replicate": "replicate_api",
            "together_ai": "together_ai_api",
            "deepseek": "deepseek_api",
            "fireworks_ai": "fireworks_ai_api",
        }

        cred_section = creds_key_map.get(provider)
        if cred_section:
            creds = self.get_credentials(cred_section)
            if creds:
                key = creds.get("api_key", "")
                # Restituisce la chiave solo se non è un placeholder
                if key and "IL_TUO" not in key:
                    return key
        return ""

    def fetch_available_groq_models(self, api_key: str) -> List[str]:
        """
        Interroga l'API di Groq per ottenere la lista dei modelli disponibili (v107.4).
        Utilizza l'endpoint ufficiale: https://api.groq.com/openai/v1/models
        """
        if not api_key or "IL_TUO" in api_key:
            if not self.silent:
                print(t("avatar_server.log.guardian_groq_no_key"))
            return []

        try:
            # Endpoint ufficiale Groq Cloud
            url = "https://api.groq.com/openai/v1/models"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            # Esegue la richiesta GET
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                # Groq restituisce i modelli dentro la chiave 'data'
                models_list = data.get("data", [])

                # Estraiamo solo gli ID e filtriamo eventuali stringhe vuote
                ids = [model["id"] for model in models_list if "id" in model]

                if not self.silent:
                    print(t("avatar_server.log.guardian_groq_fetched", count=len(ids)))
                return sorted(ids)  # Restituisce la lista ordinata alfabeticamente
            else:
                if not self.silent:
                    print(
                        t(
                            "avatar_server.log.guardian_groq_api_error",
                            code=response.status_code,
                            text=response.text,
                        )
                    )
                return []
        except Exception as e:
            if not self.silent:
                print(t("avatar_server.log.guardian_groq_exception", error=e))
            return []

    def fetch_available_openrouter_models(self, api_key: str) -> List[str]:
        """
        Interroga l'API di OpenRouter per ottenere la lista dei modelli disponibili.
        Richiede API Key per l'autenticazione.
        """
        if not api_key:
            return []

        try:
            url = "https://openrouter.ai/api/v1/models"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                # Filtra e restituisce solo gli ID dei modelli, ordinati alfabeticamente
                models = [model["id"] for model in data.get("data", [])]
                return sorted(models)
            else:
                if not self.silent:
                    print(
                        t(
                            "avatar_server.log.guardian_openrouter_error",
                            code=response.status_code,
                            text=response.text,
                        )
                    )
                return []
        except Exception as e:
            if not self.silent:
                print(t("avatar_server.log.guardian_openrouter_exception", error=e))
            return []

    # --- [NUOVO v24.0] GESTIONE GROQ TOOLS ---
    def get_groq_tools_config(self) -> Dict[str, bool]:
        """Recupera la configurazione dei tool nativi di Groq."""
        default_config = {
            "web_search": True,
            "browser": False,
            "code_interpreter": False,
        }
        if self._config is None:
            return default_config
        return self._config.get("groq_tools", default_config)

    def save_groq_tools_config(self, config: Dict[str, bool]) -> bool:
        """Salva la configurazione dei tool nativi di Groq."""
        with self._lock:
            if self._config is None:
                self._config = {}
            self._config["groq_tools"] = config
            if self._save_main_config():
                if not self.silent:
                    print(t("avatar_server.log.guardian_groq_tools_updated"))
                return True
            return False

    # ---[NUOVO v24.0] GESTIONE MCP (Model Context Protocol) ---
    def get_mcp_servers(self) -> List[Dict[str, Any]]:
        """Recupera la lista dei server MCP configurati."""
        if self._config is None:
            return list()
            
        servers = self._config.get("mcp_servers", list())
        
        # --- PURGA ATTIVA GRAPHIFY ---
        # Rimuove Graphify se è rimasto incastrato nel config.yaml dalle sessioni precedenti
        filtered_servers = [s for s in servers if s.get("name") != "Graphify"]
        if len(filtered_servers) != len(servers):
            self._config["mcp_servers"] = filtered_servers
            self._save_main_config()
            
        return filtered_servers

    def save_mcp_servers(self, servers: List[Dict[str, Any]]) -> bool:
        """Salva la lista dei server MCP."""
        with self._lock:
            if self._config is None:
                self._config = {}
            self._config["mcp_servers"] = servers
            if self._save_main_config():
                if not self.silent:
                    print(t("avatar_server.log.guardian_mcp_updated"))
                return True
            return False

    # --- ALTRI GETTER (LE 90 LINEE RESTAURATE) ---
    def get_trusted_domains(self) -> List[str]:
        if not self._learning_sources_all:
            return []
        domains = set()
        for url in self._learning_sources_all:
            try:
                domain = urlparse(url).netloc
                if domain:
                    if domain.startswith("www."):
                        domain = domain[4:]
                    domains.add(domain)
            except Exception:
                continue
        return list(domains)

    def get_random_learning_topic(self) -> str | None:
        if not self._curriculum:
            return None
        try:
            domains = list(self._curriculum.keys())
            random_domain_key = random.choice(domains)
            domain_content = self._curriculum[random_domain_key]
            areas = list(domain_content.keys())
            random_area_key = random.choice(areas)
            area_content = domain_content[random_area_key]
            topic = random.choice(area_content["argomenti"])
            return t(
                "avatar_server.log.guardian_topic_context",
                topic=topic,
                context=random_area_key,
            )
        except Exception as e:
            if not self.silent:
                print(t("avatar_server.log.guardian_curriculum_error", error=e))
            return t("avatar_server.log.guardian_default_topic")

    def get_developer_settings(self) -> Optional[Dict[str, Any]]:
        if self._config is None:
            return None
        try:
            return self._config.get("developer_settings")
        except (KeyError, TypeError):
            return None

    def get_vision_processor_config(self) -> Optional[Dict[str, Any]]:
        if self._config is None:
            return None
        try:
            return self._config.get("vision_processor")
        except (KeyError, TypeError):
            return None

    # --- [NUOVO v52.2] GESTIONE SELEZIONE MODELLI & GATEKEEPER CHECK ---
    def get_model_selection_config(self) -> Optional[Dict[str, Any]]:
        if self._config is None:
            return None
        try:
            config = self._config.get("model_selection", {})
            # Assicura valori di default per le nuove chiavi
            if "specialist_mode_enabled" not in config:
                config["specialist_mode_enabled"] = False
            if "active_labour_model" not in config:
                config["active_labour_model"] = ""
            if "labour_model_on_cpu" not in config:
                config["labour_model_on_cpu"] = True
            return config
        except (KeyError, TypeError):
            return None

    def is_labour_configured(self) -> bool:
        """Verifica se un modello Labour è attualmente selezionato nella configurazione."""
        config = self.get_model_selection_config()
        if not config:
            return False
        labour_model = config.get("active_labour_model", "")
        return bool(
            labour_model and labour_model.strip() and labour_model.lower() != "none"
        )

    def save_model_selection_config(self, model_config: Dict[str, Any]) -> bool:
        """Salva la configurazione della selezione modelli (incluso Specialist e Labour)."""
        with self._lock:
            if self._config is None:
                self._config = {}
            self._config["model_selection"] = model_config
            if self._save_main_config():
                if not self.silent:
                    print(t("avatar_server.log.guardian_models_saved"))
                return True
            return False

    # --- [NUOVO v50.0] GESTIONE CONFIGURAZIONE SPECIALIST (ADVANCED) ---
    def get_specialist_config(self) -> Dict[str, Any]:
        """
        Recupera le impostazioni avanzate per la modalità Specialist.
        Include lo switch 'keep_loaded' e la lista dei prompt dedicati.
        """
        default_config = {
            "keep_loaded": False,
            "prompts": [
                t("avatar_server.specialist.prompt_1"),
                t("avatar_server.specialist.prompt_2"),
            ],
        }
        if self._config is None:
            return default_config
        # Merge con i default per garantire che le chiavi esistano
        current = self._config.get("specialist", {})
        merged = default_config.copy()
        merged.update(current)
        return merged

    def save_specialist_config(self, config: Dict[str, Any]) -> bool:
        """Salva le impostazioni avanzate Specialist."""
        with self._lock:
            if self._config is None:
                self._config = {}
            self._config["specialist"] = config
            if self._save_main_config():
                if not self.silent:
                    print(t("avatar_server.log.guardian_specialist_updated"))
                return True
            return False

    def get_hotword_config(self) -> Optional[Dict[str, Any]]:
        if self._config is None:
            return None
        try:
            return self._config.get("perception", {}).get("hotword_detection")
        except (KeyError, TypeError):
            return None

    def can_read_calendar(self) -> bool:
        if self._config is None:
            return False
        try:
            return self._config["permissions"]["connectors"]["calendar"]["enabled"]
        except (KeyError, TypeError):
            return False

    def get_calendar_config(self) -> Optional[Dict[str, Any]]:
        if self._config is None:
            return None
        try:
            return self._config["permissions"]["connectors"]["calendar"]
        except (KeyError, TypeError):
            return None

    # [AGGIUNTA TASK ODIERNO] Hot Reload
    def reload_config(self):
        """Ricarica la configurazione da disco per Hot Reload."""
        with self._lock:
            try:
                if self._config_path.exists():
                    with open(self._config_path, "r", encoding="utf-8") as f:
                        self._config = yaml.safe_load(f)

                if self._credentials_path.exists():
                    with open(self._credentials_path, "r", encoding="utf-8") as f:
                        self._credentials = yaml.safe_load(f)

                # ---[NUOVO v27.0] RELOAD NUOVI DATI ---
                if self._jailbreaks_path.exists():
                    with open(self._jailbreaks_path, "r", encoding="utf-8") as f:
                        self._jailbreaks = json.load(f)

                if self._knowledge_base_path.exists():
                    with open(self._knowledge_base_path, "r", encoding="utf-8") as f:
                        self._knowledge_base = json.load(f)

                if self._personality_presets_path.exists():
                    with open(
                        self._personality_presets_path, "r", encoding="utf-8"
                    ) as f:
                        self._personality_presets = yaml.safe_load(f) or {}

                # --- [NUOVO FASE 16] HOT RELOAD MODULI E MINDSETS ---
                self._load_cognitive_modules()
                self._load_cognitive_mindsets()

                if self._prompt_manager:
                    self._prompt_manager.load_language(
                        self._prompt_manager.current_lang
                    )

                if not self.silent:
                    print(t("avatar_server.log.guardian_hot_reload_done"))
            except Exception as e:
                if not self.silent:
                    print(t("avatar_server.log.guardian_hot_reload_error", error=e))

    # [AGGIUNTA PROPOSTA 3] Validazione Integrità
    def _validate_connectors_integrity(self):
        """Verifica la sintassi di tutti i connettori Python."""
        connectors_dir = project_root / "src" / "connectors"
        if not connectors_dir.exists():
            return

        if not self.silent:
            print(t("avatar_server.log.guardian_validate_connectors"))

        py_files = list(connectors_dir.glob("*.py"))
        issues = []

        for py_file in py_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    source = f.read()
                ast.parse(source)
            except SyntaxError as e:
                issues.append(
                    t(
                        "avatar_server.log.syntax_error_detail",
                        file=py_file.name,
                        error=e,
                    )
                )
            except Exception as e:
                issues.append(
                    t(
                        "avatar_server.log.guardian_connector_read_error",
                        name=py_file.name,
                        error=e,
                    )
                )

        if issues:
            print(t("avatar_server.log.guardian_corrupt_connectors"))
            for issue in issues:
                print(t("avatar_server.log.issue_item", issue=issue))
            print("\n")
        else:
            if not self.silent:
                print(t("avatar_server.log.guardian_valid_connectors"))

    # --- [NUOVO v116.3] RILEVAMENTO HARDWARE PER CONTEXT SCALING ---
    def get_available_vram_gb(self) -> float:
        """
        Rileva la VRAM libera sulla GPU primaria (NVIDIA) in GB.
        Restituisce 0.0 se non viene rilevata una GPU o in caso di errore.
        """
        if os.name != "nt":
            if not self.silent:
                print("[GUARDIAN] VRAM Detection: OS non supportato. Opero alla cieca (0.0 GB).")
            return 0.0  # Supporto Linux da implementare se necessario

        try:
            # Interroga nvidia-smi per la memoria libera
            cmd = "nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits"
            # [FIX 2C] Aggiunto stderr=subprocess.DEVNULL per evitare spam in console se nvidia-smi non esiste (es. AMD/Intel)
            result = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode("utf-8").strip()
            free_mb = float(result.split("\n")[0])
            return free_mb / 1024.0
        except Exception as e_smi:
            # Fallback: se nvidia-smi fallisce, proviamo a vedere se torch è già caldo
            try:
                import torch

                if torch.cuda.is_available():
                    free_bytes = torch.cuda.mem_get_info()[0]
                    return free_bytes / (1024**3)
                else:
                    if not self.silent:
                        print("[GUARDIAN] VRAM Detection: CUDA non disponibile in Torch. Opero alla cieca (0.0 GB).")
            except Exception as e_torch:
                if not self.silent:
                    print("[GUARDIAN] VRAM Detection Fallita (NVIDIA-SMI assente, TORCH error). Opero alla cieca (0.0 GB).")
                pass
        return 0.0

    # --- [NUOVO] GESTIONE MATRICE DEL RISVEGLIO ---
    def get_last_shutdown_time(self) -> Optional[float]:
        """Recupera il timestamp dell'ultimo spegnimento."""
        if self._last_shutdown_path.exists():
            try:
                with open(self._last_shutdown_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("timestamp")
            except Exception:
                pass
        return None

    def save_last_shutdown_time(self) -> bool:
        """Salva il timestamp corrente come momento di spegnimento."""
        with self._lock:
            try:
                self._last_shutdown_path.parent.mkdir(exist_ok=True)
                with open(self._last_shutdown_path, "w", encoding="utf-8") as f:
                    json.dump({"timestamp": time.time()}, f)
                return True
            except Exception as e:
                if not self.silent:
                    print(t("system.error", error=str(e)))
                return False
