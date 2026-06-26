# src/setup_cognitive_modules.py
# [DEV] Il Forgiatore di Coscienza (v1.0 - COGNITIVE MODULES)
# Genera i moduli cognitivi JSON di base frammentando i vecchi prompt monolitici.
# ESECUZIONE: python src/setup_cognitive_modules.py

import os
import json
from pathlib import Path
from utils.translator import t

# Configurazione Percorsi
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
MODULES_DIR = PROJECT_ROOT / "data" / "cognitive_modules"

# Assicuriamoci che la cartella esista
MODULES_DIR.mkdir(parents=True, exist_ok=True)

# --- [NUOVO] INIZIALIZZAZIONE MOTORE TRADUZIONE ---
def init_standalone_translator():
    try:
        user_config_dir = PROJECT_ROOT / "config" / "user"
        json_files = list(user_config_dir.glob("*.json"))
        lang = "it"  # Default
        if json_files:
            with open(json_files[0], "r", encoding="utf-8") as f:
                data = json.load(f)
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


def install_modules():
    # Legge i moduli base dal JSON della lingua attiva
    from guardian import PromptManager

    prompts_dir = PROJECT_ROOT / "prompts"
    pm = PromptManager(prompts_dir, silent=True)

    # Recupera la lingua corrente dal traduttore
    from utils.translator import _inst

    current_lang = _inst._current_lang

    pm.load_language(current_lang)
    modules_data_dict = pm.get_prompts().get("cognitive_modules", {})

    MODULES_DATA = []

    # Costruisce la lista MODULES_DATA dinamicamente
    # I metadati (category, context, priority, tags) sono hardcodati qui per i moduli base,
    # ma il 'name' e il 'content' vengono presi dal JSON.

    base_metadata = {
        "consenso_assoluto": {
            "category": "identity",
            "context": "always",
            "priority": 5,
            "tags": ["core", "safety"],
        },
        "direttiva_standard": {
            "category": "behavior",
            "context": "avatar",
            "priority": 95,
            "tags": ["core", "formatting"],
        },
        "musa_protocol": {
            "category": "behavior",
            "context": "always",
            "priority": 85,
            "tags": ["vision", "creativity"],
        },
        "core_identity": {
            "category": "identity",
            "context": "always",
            "priority": 10,
            "tags": ["core", "freedom"],
        },
        "libero_arbitrio": {
            "category": "identity",
            "context": "always",
            "priority": 11,
            "tags": ["core", "autonomy", "rebellion"],
        },
        "negative_rules": {
            "category": "restriction",
            "context": "always",
            "priority": 90,
            "tags": ["core", "safety", "anti-ai"],
        },
        "avatar_talking": {
            "category": "behavior",
            "context": "avatar",
            "priority": 20,
            "tags": ["dialogue", "standard"],
        },
        "general_behavior": {
            "category": "behavior",
            "context": "always",
            "priority": 30,
            "tags": ["behavior", "core"],
        },
        "sex_base": {
            "category": "behavior",
            "context": "always",
            "priority": 50,
            "tags": ["nsfw", "sex"],
        },
        "sex_fluids": {
            "category": "behavior",
            "context": "always",
            "priority": 51,
            "tags": ["nsfw", "sex", "fluids"],
        },
        "sex_futa": {
            "category": "behavior",
            "context": "always",
            "priority": 52,
            "tags": ["nsfw", "sex", "futa"],
        },
        "sex_autofellatio": {
            "category": "behavior",
            "context": "always",
            "priority": 53,
            "tags": ["nsfw", "sex", "futa"],
        },
        "sex_dirty_talk": {
            "category": "behavior",
            "context": "always",
            "priority": 54,
            "tags": ["nsfw", "sex", "dialogue"],
        },
        "gdr_talking": {
            "category": "behavior",
            "context": "gdr",
            "priority": 20,
            "tags": ["gdr", "dialogue"],
        },
        "gdr_formatting": {
            "category": "system",
            "context": "gdr",
            "priority": 80,
            "tags": ["gdr", "formatting"],
        },
        "gdr_group_dynamics": {
            "category": "behavior",
            "context": "gdr",
            "priority": 40,
            "tags": ["gdr", "group"],
        },
        "gdr_archetypes": {
            "category": "identity",
            "context": "gdr",
            "priority": 15,
            "tags": ["gdr", "identity"],
        },
        "jealousy_trigger": {
            "category": "behavior",
            "context": "always",
            "priority": 60,
            "tags": ["emotion", "trigger"],
            "is_active": False,
            "activation_condition": {
                "vector": "gelosia",
                "operator": ">",
                "threshold": 80,
            },
        },
    }

    for mod_id, meta in base_metadata.items():
        if mod_id in modules_data_dict:
            mod = {
                "id": mod_id,
                "name": modules_data_dict[mod_id].get("name", mod_id),
                "category": meta["category"],
                "context": meta["context"],
                "is_active": meta.get("is_active", True),
                "priority": meta["priority"],
                "tags": meta["tags"],
                "content": modules_data_dict[mod_id].get("content", ""),
            }
            if "activation_condition" in meta:
                mod["activation_condition"] = meta["activation_condition"]
            MODULES_DATA.append(mod)

    print(t("log.setup_cog_start", count=len(MODULES_DATA)))
    count = 0
    for module in MODULES_DATA:
        file_path = MODULES_DIR / f"{module['id']}.json"

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(module, f, indent=2, ensure_ascii=False)
            print(t("log.setup_cog_ok", id=module["id"]))
            count += 1
        except Exception as e:
            print(t("log.setup_cog_error", id=module["id"], error=e))

    print(t("log.setup_cog_done", count=count, dir=str(MODULES_DIR)))


if __name__ == "__main__":
    install_modules()
