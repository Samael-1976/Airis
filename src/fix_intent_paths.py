# src/fix_intent_paths.py
# v1.2 - Strumento di Riparazione e Normalizzazione (Fase 17)
# Sincronizza intent.json con i file reali e uniforma i separatori in '/' (Unix standard).

import os
import sys
import json
from pathlib import Path

# --- [FIX CRITICO] INIEZIONE PATH (Deve precedere gli import locali) ---
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
# -----------------------------------------------------------------------

# Ora l'import è sicuro perché 'utils' è visibile nel sys.path
from utils.translator import t, set_language

# --- [FIX CRITICO] INIZIALIZZAZIONE LINGUA PRECOCE ---
_early_lang = "en"
try:
    _lang_cfg_path = Path(__file__).parent.parent / "lang.cfg"
    if _lang_cfg_path.exists():
        with open(_lang_cfg_path, "r", encoding="utf-8") as _f:
            _early_lang = _f.read().strip()
except:
    pass
set_language(_early_lang)

# --- [NUOVO] INIZIALIZZAZIONE MOTORE TRADUZIONE ---
def init_standalone_translator():
    try:
        user_config_dir = PROJECT_ROOT / "config" / "user"
        json_files = list(user_config_dir.glob("*.json"))
        lang = "it"  # Default
        if json_files:
            with open(json_files[0], "r", encoding="utf-8") as f:
                data = json.load(f)
                # Tenta di recuperare la lingua dal profilo utente (supporta entrambi i formati chiave)
                lingua_data = data.get("lingua", {})
                if isinstance(lingua_data, dict):
                    lang = lingua_data.get("preferredLanguage", "it")
                else:
                    lang = data.get("preferredLanguage", "it")
        set_language(lang)
    except Exception:
        set_language("it")


init_standalone_translator()
# -------------------------------------------------

# Definizione percorsi costanti
AVATARS_DIR = PROJECT_ROOT / "avatars"


def fix_avatar_intents(avatar_name):
    avatar_root = AVATARS_DIR / avatar_name
    intent_json_path = avatar_root / "intent" / "intent.json"
    videos_root = avatar_root / "videos" / "default"

    if not intent_json_path.exists():
        print(t("avatar_server.log.intent_not_found", avatar_name=avatar_name))
        return

    print(t("avatar_server.log.analysis_avatar", avatar_name=avatar_name))

    try:
        with open(intent_json_path, "r", encoding="utf-8") as f:
            intents = json.load(f)
    except Exception as e:
        print(t("avatar_server.log.json_read_error", error=str(e)))
        return

    updates_count = 0

    for item in intents:
        original_path = item.get("filepath", "")
        if not original_path:
            continue

        # --- FIX v1.1: Normalizzazione Separatori ---
        # Trasforma backslash in forward slash per uniformità
        normalized_path = original_path.replace("\\", "/")
        if normalized_path != original_path:
            item["filepath"] = normalized_path
            updates_count += 1

        # Costruisci percorso assoluto atteso per la verifica esistenza
        clean_rel_path = normalized_path.lstrip("./").lstrip("/")
        full_path = videos_root / clean_rel_path

        # Se il file esiste dopo la normalizzazione, procedi
        if full_path.exists():
            continue

        # SE IL FILE NON ESISTE: Cerca il file corretto
        print(t("avatar_server.log.missing_file", path=clean_rel_path))

        directory = full_path.parent
        filename = full_path.name

        if not directory.exists():
            print(t("avatar_server.log.folder_missing", directory=str(directory)))
            continue

        # Tentativo 1: Rimuovi o aggiungi 'state_'
        candidates = []
        if filename.startswith("state_"):
            candidates.append(filename.replace("state_", ""))
        else:
            candidates.append(f"state_{filename}")

        found_fix = None

        # Cerca candidati
        for cand in candidates:
            if (directory / cand).exists():
                found_fix = cand
                break

        # Tentativo 2: Cerca file con nome simile nella stessa cartella (case insensitive)
        if not found_fix:
            try:
                for f in directory.iterdir():
                    if f.is_file() and f.name.lower() == filename.lower():
                        found_fix = f.name
                        break
            except Exception:
                pass

        if found_fix:
            # Calcola nuovo percorso relativo (sempre con /)
            new_rel_path = f"{directory.name}/{found_fix}"
            print(t("avatar_server.log.fix_found", found_fix=found_fix))
            item["filepath"] = new_rel_path
            updates_count += 1
        else:
            print(t("avatar_server.log.fatal_missing", filename=filename))

    if updates_count > 0:
        # Salva backup prima di sovrascrivere
        backup_path = intent_json_path.with_suffix(".json.bak")
        try:
            import shutil

            shutil.copy2(intent_json_path, backup_path)
        except Exception:
            pass

        # Scrittura file normalizzato
        with open(intent_json_path, "w", encoding="utf-8") as f:
            json.dump(intents, f, indent=2, ensure_ascii=False)
        print(t("avatar_server.log.success_update", count=updates_count))
    else:
        print(t("avatar_server.log.ok_no_fix"))


if __name__ == "__main__":
    if not AVATARS_DIR.exists():
        print(t("avatar_server.log.avatars_dir_missing", path=str(AVATARS_DIR)))
        sys.exit(1)

    # Scansiona tutti gli avatar (escluso ai_souls)
    for d in AVATARS_DIR.iterdir():
        if d.is_dir() and d.name != "ai_souls":
            fix_avatar_intents(d.name)

    print(t("avatar_server.log.rite_completed"))
