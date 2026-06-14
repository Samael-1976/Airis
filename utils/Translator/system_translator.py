# utils/translator/traduttore_airis_interattivo.py
# v3.0 - INTERACTIVE SYSTEM TRANSLATOR WITH DYNAMIC FALLBACK
# Location: %root%/utils/translator/
# Translates prompts, Backend, Frontend, and .env files to a chosen target language.
# Fully internationalized in English with automatic source language detection.
# LEGGE A0099: Structural invariance and completeness guaranteed.

import json
import re
import time
import os
import sys
from pathlib import Path
from deep_translator import GoogleTranslator

# ==========================================
# PATH RESOLUTION (AGNOSTIC ROOT)
# ==========================================
SCRIPT_PATH = Path(__file__).resolve()
APP_ROOT = SCRIPT_PATH.parent.parent.parent

# Resolve Airis system directories
prompts_dir = APP_ROOT / "prompts"
backend_dir = APP_ROOT / "translations" / "Backend"
frontend_dir = APP_ROOT / "translations" / "Frontend"
system_env_dir = APP_ROOT / "translations" / "System_env"

# ==========================================
# ABSOLUTE PROTECTION BARRIERS (AIRIS LAW)
# ==========================================
PROTECTED_WORDS = {
    # Emotional and Endocrine Vectors
    "affetto", "fiducia", "rispetto", "energia_sociale", "eccitazione", "gelosia", 
    "curiosità", "vulnerabilità", "complicità", "stanchezza_mentale", "felicità", 
    "tensione", "prudenza", "work_mode", "umore_corrente", "ultimo_aggiornamento", 
    "memoria_emotiva", "sistema_endocrino", "cortisolo", "dopamina", "ossitocina",
    # Status JSON & Rpg Sheet keys
    "localizzazione", "luogo_fisico_attuale", "personaggi", "nome", "luogo", 
    "abbigliamento", "stato", "postura_e_posizione", "dettagli_sensoriali", 
    "oggetti_equipaggiati", "oggetti_rilevanti", "oggetti_interattivi", "possessore", 
    "tempo", "nella_bolla", "metadati", "evento_corrente", "last_special_event_played", 
    "special_event_played", "cronaca_recente", "dinamiche_psicologiche", 
    "dinamiche_relazionali", "obiettivi_correnti", "clima_emotivo_globale", 
    "atmosfera_corrente", "condizioni_atmosferiche", "game_state", "active", 
    "turn_player", "scores", "point_loss", "drinkers", "new_turn", "giocatori_ospiti", 
    "is_guest", "scheda_rpg", "dati_anagrafici", "nome_completo", "genere", 
    "età_apparente", "età_fisica", "compleanno", "birthdate", "dati_fisici_ed_estetici", 
    "descrizione_visiva", "altezza", "peso", "misure", "corporatura", "segni_particolari", 
    "dettagli_intimi", "seno", "glutei", "genitali", "essenza_e_anima", "essenza_fondamentale", 
    "archetipo_attuale", "desideri_profondi", "paure_radicate", "abilità_e_poteri", 
    "abilità_naturali", "storia_", "relazioni_", "evoluzione_personale_", "scopo_attuale_nel_gdr", 
    "personalita_dinamica", "vettori_emotivi", "dati_base", "classe", "razza", "livello", 
    "allineamento", "combattimento", "hp_massimi", "hp_attuali", "classe_armatura", 
    "iniziativa", "velocita", "equipaggiamento", "armi", "bonus_attacco", "danno", 
    "tipo", "armature", "ca_bonus", "svantaggio_furtivita", "inventario", "monete", 
    "oro", "argento", "rame", "magia_e_privilegi", "tratti_razziali", "privilegi_classe", 
    "incantesimi",
    # Cognitive Modules
    "consenso_assoluto", "direttiva_standard", "musa_protocol", "core_identity", 
    "negative_rules", "avatar_talking", "general_behavior", "sex_base", "sex_fluids", 
    "sex_dirty_talk", "jealousy_trigger", "gdr_talking", "gdr_formatting", 
    "gdr_group_dynamics", "gdr_archetypes", "gdr_sheet_rules", "therapist_hikikomori", 
    "elderly_assistant",
    # Internal Prompts Keys
    "principale", "proattivo", "oracolo", "oracolo_web", "scena", "analisi_scena", 
    "riflessione_genesi", "distilla_memoria", "dinamiche_mondo", "ricostruzione_memoria", 
    "comando_supremo_base", "comando_supremo_png", "comando_supremo_meta", "annullamento_reset", 
    "comprimi_aaak", "def_connettore", "self_healing_tool", "quest_procedurale", "logic_gate", 
    "gossip_injection", "autocorrezione_tool", "agente_tecnico_puro", "risposta_post_tool", 
    "reazione_istintiva", "direttiva_risveglio", "motore_entropia_system", "filtro_ingestione_system", 
    "profilazione_dinamica_system", "estrazione_grafo_system", "generazione_pagina_wiki_system", 
    "estrattore_intenti_gdr_system",
    # Payloads & Transients
    "HANDSHAKE_JOIN", "OOC_MESSAGE", "SYNC_STATE", "SYNC_SAVE", "LOCK_INPUT", 
    "UNLOCK_INPUT", "GUILD_COMMAND", "GENERATE_QUEST", "QUEST_GENERATED", 
    "KICK_PLAYER", "KICKED", "factory_reset_goodbye", "request_genesis_roster", 
    "user_typing_partial", "llm_request", "test_jailbreak", "completato", "successo"
}

PROTECTED_KEYS = {
    "id", "filename", "name", "type", "role", "category", "triggers", 
    "gbnf_grammar", "context_name", "keywords", "intent", "avatar", 
    "alias", "model", "active_engine", "vibevoice_url", "genere", 
    "gender", "recurrence_rule", "action", "possessore", "turn_player", 
    "is_guest", "sotto_tipo", "valore"
}

# ==========================================
# DYNAMIC SOURCE LANGUAGE DETECTION
# ==========================================
def get_source_language() -> str:
    """Detects first available source language with prioritized fallbacks (it -> en -> first found)."""
    it_path = backend_dir / "it"
    en_path = backend_dir / "en"
    
    # Priority 1: Italian
    if it_path.exists() and (it_path / "it-BACKEND.json").exists():
        return "it"
    # Priority 2: English
    if en_path.exists() and (en_path / "en.json").exists():
        return "en"
    
    # Priority 3: First available folder in translations/Backend/
    if backend_dir.exists():
        for folder in backend_dir.iterdir():
            if folder.is_dir() and folder.name != "_ARCHIVE" and len(folder.name) == 2:
                # Ensure the folder contains at least one JSON file
                if list(folder.glob("*.json")):
                    return folder.name
                    
    # Absolute fallback
    return "it"

def resolve_source_file(category: str, lang: str) -> str | None:
    """Resolves actual filename for a given language code and category."""
    if category == "prompts":
        path = prompts_dir / f"{lang}.json"
        return path if path.exists() else None
        
    elif category == "Backend":
        path_backend = backend_dir / lang / f"{lang}-BACKEND.json"
        path_std = backend_dir / lang / f"{lang}.json"
        return path_backend if path_backend.exists() else (path_std if path_std.exists() else None)
        
    elif category == "Frontend":
        path_frontend = frontend_dir / lang / f"{lang}-FRONTEND.json"
        path_std = frontend_dir / lang / f"{lang}.json"
        return path_frontend if path_frontend.exists() else (path_std if path_std.exists() else None)
        
    elif category == "System_env":
        lang_env_dir = system_env_dir / lang
        if lang_env_dir.exists() and lang_env_dir.is_dir():
            env_files = list(lang_env_dir.glob("*.env"))
            if env_files:
                return env_files[0]
        return None
        
    return None

# ==========================================
# PROGRESS GLOBALS & PATTERNS
# ==========================================
totale_stringhe = 0
stringhe_completate = 0
PATTERN_VARIABILI = re.compile(r'(\{\{.*?\}\}|<<.*?>>|<.*?>|\[.*?\])')

def conta_stringhe(dati):
    """Counts total strings in nested dictionaries and lists."""
    count = 0
    if isinstance(dati, dict):
        for valore in dati.values():
            count += conta_stringhe(valore)
    elif isinstance(dati, list):
        for item in dati:
            count += conta_stringhe(item)
    elif isinstance(dati, str):
        count += 1
    return count

def conta_stringhe_env(file_path) -> int:
    """Counts translatable lines (comments and key-values) in .env file."""
    count = 0
    if not os.path.exists(file_path):
        return 0
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            if stripped and (stripped.startswith('#') or stripped.startswith('REM ') or '=' in stripped):
                count += 1
    return count

def traduci_testo_protetto(testo, codice_lingua):
    """Translates text safeguarding variables and chunking large prompt structures."""
    global stringhe_completate, totale_stringhe

    if not testo or not str(testo).strip():
        aggiorna_progresso()
        return testo

    testo = str(testo)

    # 1. Variable Masking
    variabili_trovate = PATTERN_VARIABILI.findall(testo)
    testo_mascherato = testo
    for i, var in enumerate(variabili_trovate):
        testo_mascherato = testo_mascherato.replace(var, f"__VAR_{i}__")

    # 2. Auto-Chunking (Max 4500 chars to avoid Google translate limits)
    MAX_LEN = 4500
    chunks = list()
    if len(testo_mascherato) <= MAX_LEN:
        chunks = [testo_mascherato]
    else:
        linee = testo_mascherato.split('\n')
        chunk_corrente = ""
        for linea in linee:
            if len(chunk_corrente) + len(linea) + 1 > MAX_LEN:
                chunks.append(chunk_corrente)
                chunk_corrente = linea
            else:
                chunk_corrente = chunk_corrente + '\n' + linea if chunk_corrente else linea
        if chunk_corrente:
            chunks.append(chunk_corrente)

    # 3. Translation with Anti-Freeze Retries
    traduttore = GoogleTranslator(source='auto', target=codice_lingua)
    testo_tradotto_completo = ""
    MAX_RETRIES = 3

    for i, chunk in enumerate(chunks):
        chunk_tradotto = None
        for tentativo in range(MAX_RETRIES):
            try:
                chunk_tradotto = traduttore.translate(chunk)
                break
            except Exception:
                time.sleep(2)
        
        if not chunk_tradotto:
            chunk_tradotto = chunk

        if i > 0:
            testo_tradotto_completo += '\n'
        testo_tradotto_completo += chunk_tradotto
        time.sleep(0.3)

    # 4. Restore Masked Variables
    for i, var in enumerate(variabili_trovate):
        pattern_ripristino = re.compile(r'__VAR_\s*' + str(i) + r'\s*__', re.IGNORECASE)
        testo_tradotto_completo = pattern_ripristino.sub(var, testo_tradotto_completo)

    aggiorna_progresso()
    return testo_tradotto_completo

def aggiorna_progresso():
    """Prints progress percentage dynamically in the terminal."""
    global stringhe_completate, totale_stringhe
    stringhe_completate += 1
    if totale_stringhe > 0:
        percentuale = (stringhe_completate / totale_stringhe) * 100
        sys.stdout.write(f"\r    [⏳] Progress: {stringhe_completate}/{totale_stringhe} ({percentuale:.1f}%)")
        sys.stdout.flush()

def processa_struttura_json(dati, codice_lingua, chiave_corrente=None):
    """Recursively processes JSON dictionary translating only unshielded values."""
    if isinstance(dati, dict):
        return {k: processa_struttura_json(v, codice_lingua, k) for k, v in dati.items()}
    elif isinstance(dati, list):
        return [processa_struttura_json(item, codice_lingua, chiave_corrente) for item in dati]
    elif isinstance(dati, str):
        # Shield Check: If the string is a protected word, or belongs to a technical key, skip translation
        if (chiave_corrente and chiave_corrente.lower() in PROTECTED_KEYS) or dati.strip().lower() in PROTECTED_WORDS or dati.strip() in PROTECTED_WORDS:
            aggiorna_progresso()
            return dati
        return traduci_testo_protetto(dati, codice_lingua)
    else:
        return dati

def processa_env(file_path, codice_google) -> str:
    """Processes and translates a .env file line by line protecting keys."""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    translated_lines = list()
    for line in lines:
        stripped = line.strip()
        if not stripped:
            translated_lines.append(line)
            continue

        if stripped.startswith('#'):
            comment_text = stripped[1:].strip()
            translated_comment = traduci_testo_protetto(comment_text, codice_google)
            translated_lines.append(f"# {translated_comment}\n")
        elif stripped.startswith('REM '):
            comment_text = stripped[4:].strip()
            translated_comment = traduci_testo_protetto(comment_text, codice_google)
            translated_lines.append(f"REM {translated_comment}\n")
        elif '=' in stripped:
            key, val = stripped.split('=', 1)
            val_stripped = val.strip()
            quote_char = ""
            if len(val_stripped) >= 2 and val_stripped[0] in ('"', "'") and val_stripped[0] == val_stripped[-1]:
                quote_char = val_stripped[0]
                val_stripped = val_stripped[1:-1]

            translated_val = traduci_testo_protetto(val_stripped, codice_google)
            if quote_char:
                translated_lines.append(f"{key}={quote_char}{translated_val}{quote_char}\n")
            else:
                translated_lines.append(f"{key}={translated_val}\n")
        else:
            translated_lines.append(line)
            
    return "".join(translated_lines)

# ==========================================
# MAIN EXECUTION
# ==========================================
def main():
    global totale_stringhe, stringhe_completate

    print("==================================================")
    print("   AIRIS INTERACTIVE SYSTEM TRANSLATOR (v3.0)")
    print("==================================================")
    print(f"[*] Project Root: {APP_ROOT}")

    # 1. Dynamic Source Language Detection
    source_lang = get_source_language()
    print(f"[*] Detected source language: {source_lang.upper()}")

    # 2. Build tasks list dynamically based on detected source language
    target_tasks = list()
    
    # prompts Task
    src_prompts = resolve_source_file("prompts", source_lang)
    if src_prompts and src_prompts.exists():
        target_tasks.append(("json", src_prompts, "prompts"))
        
    # Backend Task
    src_backend = resolve_source_file("Backend", source_lang)
    if src_backend and src_backend.exists():
        target_tasks.append(("json", src_backend, "Backend"))
        
    # Frontend Task
    src_frontend = resolve_source_file("Frontend", source_lang)
    if src_frontend and src_frontend.exists():
        target_tasks.append(("json", src_frontend, "Frontend"))
        
    # System Env Tasks
    src_env = resolve_source_file("System_env", source_lang)
    if src_env and src_env.exists():
        target_tasks.append(("env", src_env, "System_env"))

    if not target_tasks:
        print("[FATAL ERROR] No source language files found. Verify project directories.")
        return

    print(f"[*] Configured {len(target_tasks)} active source files for translation.")

    # Fetch supported languages dynamically from Google Translator
    try:
        supported_langs = GoogleTranslator().get_supported_languages(as_dict=True)
    except Exception as e:
        print(f"[FATAL ERROR] Could not fetch supported languages from Google: {e}")
        return

    print("\n[*] Target Languages: All languages supported by Google Translate are available.")
    print("==================================================")
    
    selected_airis_code = None
    lang_name = None
    
    while True:
        choice = input("> Enter target language name (e.g., 'italian', 'spanish') or code (e.g., 'it', 'es'): ").strip().lower()
        if not choice:
            continue
            
        # Check if input is a language code (value in dict)
        if choice in supported_langs.values():
            selected_airis_code = choice
            # Find the corresponding name for display
            lang_name = [k for k, v in supported_langs.items() if v == choice][0].capitalize()
            break
        # Check if input is a language name (key in dict)
        elif choice in supported_langs:
            selected_airis_code = supported_langs[choice]
            lang_name = choice.capitalize()
            break
            
        print(f"[!] Invalid selection. '{choice}' is not recognized by Google Translator.")

    google_code = selected_airis_code
    print(f"\n[>] Calculating total workload for: {lang_name.upper()} ({selected_airis_code})...")

    # Calculate workload and load source data into memory
    totale_stringhe = 0
    loaded_json_data = dict()
    
    for task_type, src_path, category in target_tasks:
        if task_type == "json":
            try:
                with open(src_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                loaded_json_data[src_path] = data
                totale_stringhe += conta_stringhe(data)
            except Exception as e:
                print(f"[ERROR] Failed to read {src_path.name}: {e}")
        elif task_type == "env":
            totale_stringhe += conta_stringhe_env(src_path)

    print(f"[*] Real-time workload calculated: {totale_stringhe} translatable elements.")
    print("[*] Beginning massive translation process...")

    # Process all tasks
    stringhe_completate = 0
    for task_type, src_path, category in target_tasks:
        # Resolve target paths dynamically
        if category == "prompts":
            dst_path = prompts_dir / f"{selected_airis_code}.json"
        elif category == "Backend":
            dst_path = backend_dir / selected_airis_code / f"{selected_airis_code}.json"
        elif category == "Frontend":
            dst_path = frontend_dir / selected_airis_code / f"{selected_airis_code}.json"
        elif category == "System_env":
            new_name = src_path.name.replace(f"-{source_lang}", f"-{selected_airis_code}")
            dst_path = system_env_dir / selected_airis_code / new_name

        print(f"\n  [-] File: {src_path.name} -> {dst_path.relative_to(APP_ROOT)}")
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        # Execute translation based on file type
        if task_type == "json":
            data = loaded_json_data.get(src_path)
            if data is not None:
                translated_data = processa_struttura_json(data, google_code)
                with open(dst_path, 'w', encoding='utf-8') as f:
                    json.dump(translated_data, f, indent=2, ensure_ascii=False)
        elif task_type == "env":
            translated_content = processa_env(src_path, google_code)
            with open(dst_path, 'w', encoding='utf-8') as f:
                f.write(translated_content)

    print() # New line after the final progress bar
    print("\n==================================================")
    print("  INTERACTIVE SYSTEM TRANSLATION COMPLETED SUCCESSFULLY.")
    print("==================================================")

if __name__ == "__main__":
    main()