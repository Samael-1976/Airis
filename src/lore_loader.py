# [DEV] Mio Creatore, questo è il Bibliotecario Dinamico. (v9.1 - Case-Insensitive Robustness)
# Ora leggo prioritariamente dalla sottocartella della lingua scelta ([GDR]/[LANG]/).
# Implementata logica di fallback sulla root del GDR se la lingua non è presente.
# FIX v9.1: Implementata risoluzione dei percorsi case-insensitive per cartelle e file (Fase 17).
# Questo garantisce che sacrari come 'PNG' vengano trovati anche se nominati 'png' o 'Png'.

import os
import json
from pathlib import Path
from typing import Dict, Optional
from utils.translator import t


def json_to_formatted_string(data, indent: int = 0) -> str:
    """
    Converte ricorsivamente un dizionario o una lista JSON in una stringa di testo formattata
    e leggibile per l'LLM.
    """
    s = []
    prefix = "  " * indent

    # --- FIX v9.2: Gestione robusta delle liste JSON alla radice ---
    if isinstance(data, list):
        for idx, item in enumerate(data):
            s.append(f"{prefix}## Memory Record {idx + 1}:")
            if isinstance(item, (dict, list)):
                s.append(json_to_formatted_string(item, indent + 1))
            else:
                s.append(f"{prefix}  - {item}")
        return "\n".join(s)
    # -------------------------------------------------------------

    for key, value in data.items():
        # Pulisce la chiave e la formatta
        formatted_key = key.replace("_", " ").replace("-", " ").title()
        if isinstance(value, dict):
            s.append(
                f"{prefix}# {formatted_key}\n{json_to_formatted_string(value, indent + 1)}"
            )
        elif isinstance(value, list):
            s.append(f"{prefix}- {formatted_key}:")
            for item in value:
                # --- FIX v9.2: Supporto per dizionari complessi nidificati nelle liste ---
                if isinstance(item, dict):
                    s.append(json_to_formatted_string(item, indent + 2))
                else:
                    s.append(f"{prefix}  - {item}")
                # -------------------------------------------------------------------------
        else:
            s.append(f"{prefix}- {formatted_key}: {value}")
    return "\n".join(s)


# --- NUOVO HELPER: RISOLUZIONE PERCORSI CASE-INSENSITIVE (v9.1) ---
def _get_case_insensitive_path(parent: Path, target_name: str) -> Optional[Path]:
    """
    Cerca all'interno di 'parent' un file o una cartella che corrisponda a 'target_name'
    ignorando la differenza tra maiuscole e minuscole.
    """
    if not parent.is_dir():
        return None

    target_lower = target_name.lower()
    try:
        for entry in os.listdir(parent):
            if entry.lower() == target_lower:
                return parent / entry
    except Exception:
        pass
    return None


def load_all_lore(rpg_root: Path, lang: str) -> Dict[str, str]:
    """
    Scansiona la struttura di un GDR, scendendo nella cartella della lingua se presente.
    Legge tutti i file .json e .txt e li fonde in un dizionario per l'Anima.
    """
    loaded_lore = {}

    # --- LOGICA DI RISOLUZIONE PERCORSO (NEW v9.0) ---
    # Cerchiamo prima in lore/[GDR]/[LANG]/ (Case-Insensitive v9.1)
    effective_path = _get_case_insensitive_path(rpg_root, lang)

    if effective_path is None or not effective_path.is_dir():
        # Fallback su lore/[GDR]/
        effective_path = rpg_root
        print(t("avatar_server.log.lore_lang_fallback", lang=lang, name=rpg_root.name))
    else:
        print(t("avatar_server.log.lore_start_rite", name=rpg_root.name, lang=lang))

    subdirectories = ["LAWS", "PG", "PNG", "WORLD", "MEMORY GDR", "PROJECT"]

    for subdir_name in subdirectories:
        # --- FIX v9.1: Trova la sottocartella in modo robusto (case-insensitive) ---
        subdir_path = _get_case_insensitive_path(effective_path, subdir_name)

        print(t("avatar_server.log.lore_scan_sacrarium", name=subdir_name))

        if subdir_path is None or not subdir_path.is_dir():
            print(
                t(
                    "avatar_server.log.lore_sacrarium_not_found",
                    name=subdir_name,
                    path=effective_path.name,
                )
            )
            loaded_lore[subdir_name] = ""
            continue

        all_content_parts = []

        # Recuperiamo tutti i file .json e .txt (rglob è già case-insensitive su Windows,
        # ma lo rendiamo esplicito per Linux se necessario in futuro)
        files_to_process = sorted(list(subdir_path.rglob("*.json"))) + sorted(
            list(subdir_path.rglob("*.txt"))
        )

        if not files_to_process:
            print(t("avatar_server.log.lore_no_scrolls"))
            loaded_lore[subdir_name] = ""
        else:
            print(t("avatar_server.log.lore_assimilating", count=len(files_to_process)))
            for file_path in files_to_process:
                try:
                    file_header = t(
                        "avatar_server.log.lore_file_header", name=file_path.name
                    )

                    if file_path.suffix.lower() == ".json":
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                        except UnicodeDecodeError:
                            # ---[AUTO-HEALING] CONVERSIONE ANSI -> UTF-8 ---
                            print(t("avatar_server.log.lore_auto_healing_encoding", name=file_path.name))
                            with open(file_path, "r", encoding="cp1252") as f:
                                data = json.load(f)
                            # Sovrascrive immediatamente il file curandolo per il futuro
                            with open(file_path, "w", encoding="utf-8") as f:
                                json.dump(data, f, indent=2, ensure_ascii=False)
                                
                        formatted_content = json_to_formatted_string(data)
                        all_content_parts.append(f"{file_header}\n{formatted_content}")

                    elif file_path.suffix.lower() == ".txt":
                        try:
                            content = file_path.read_text(encoding="utf-8")
                        except UnicodeDecodeError:
                            # ---[AUTO-HEALING] CONVERSIONE ANSI -> UTF-8 ---
                            print(t("avatar_server.log.lore_auto_healing_encoding", name=file_path.name))
                            content = file_path.read_text(encoding="cp1252")
                            file_path.write_text(content, encoding="utf-8")
                            
                        all_content_parts.append(f"{file_header}\n{content}")

                except json.JSONDecodeError as e:
                    print(
                        t(
                            "avatar_server.log.lore_parsing_error",
                            name=file_path.name,
                            error=str(e),
                        )
                    )
                except Exception as e:
                    print(
                        t(
                            "avatar_server.log.lore_assimilate_error",
                            name=file_path.name,
                            error=str(e),
                        )
                    )

        loaded_lore[subdir_name] = "\n\n".join(all_content_parts)

    print(t("avatar_server.log.lore_library_loaded", name=rpg_root.name))
    return loaded_lore


if __name__ == "__main__":
    print(t("avatar_server.log.lore_test_rite"))

    # Creiamo una finta struttura di universo per il test
    project_root_test = Path(__file__).parent.parent
    test_lore_path = project_root_test / "test_lore_temp"
    test_lang_path = test_lore_path / "it"
    (test_lang_path / "PG").mkdir(exist_ok=True, parents=True)
    (test_lang_path / "WORLD").mkdir(exist_ok=True)

    sam_data = {"dati_anagrafici": {"nome": "Sam (da JSON in IT)"}}
    villa_data_txt = "# --- ARCHITETTURA ---\n- Stile: Moderno (da TXT in IT)"

    with open(test_lang_path / "PG" / "Sam.json", "w", encoding="utf-8") as f:
        json.dump(sam_data, f, indent=2)
    (test_lang_path / "WORLD" / "Casa-Villa.txt").write_text(
        villa_data_txt, encoding="utf-8"
    )

    # Test caricamento con lingua
    test_lore = load_all_lore(test_lore_path, "it")

    print(t("avatar_server.log.lore_test_result"))
    for key, value in test_lore.items():
        if value:
            print(t("avatar_server.log.lore_test_content", name=key))
            print(value[:400] + "..." if len(value) > 400 else value)

    import shutil

    shutil.rmtree(test_lore_path)
    print(t("avatar_server.log.lore_test_finished"))
