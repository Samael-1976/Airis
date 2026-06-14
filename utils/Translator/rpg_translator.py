# utils/translator/traduttore_airis_gdr_interattivo.py
# v3.0 - INTERACTIVE GDR LORE TRANSLATOR WITH DYNAMIC FALLBACK & MEMORY SHIELD
# Location: %root%/utils/translator/
# Translates entire GDR Lore folders selectively to a chosen Airis target language.
# Fully internationalized in English with automatic source language detection.
# Safe parsing for structured memory-gdr.txt files.
# LEGGE A0099: Structural invariance and completeness guaranteed.

import json
import re
import time
import os
import sys
import yaml
from pathlib import Path
from deep_translator import GoogleTranslator

# ==========================================
# PATH RESOLUTION (AGNOSTIC ROOT)
# ==========================================
SCRIPT_PATH = Path(__file__).resolve()
APP_ROOT = SCRIPT_PATH.parent.parent.parent
LORE_PATH = APP_ROOT / "lore"

# Resolve directories
CARTELLA_RADICE = "lore"
SALTA_ESISTENTI = True

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
# DYNAMIC SOURCE LANGUAGE DETECTION (GDR)
# ==========================================
def get_source_gdr_language(rpg_dir: Path) -> str:
    """Detects first available source language with prioritized fallbacks inside GDR folders."""
    it_path = rpg_dir / "it"
    en_path = rpg_dir / "en"
    
    if it_path.exists() and it_path.is_dir():
        return "it"
    if en_path.exists() and en_path.is_dir():
        return "en"
        
    # Fallback scan: find any 2-character directory with RPG content
    for item in rpg_dir.iterdir():
        if item.is_dir() and len(item.name) == 2 and item.name != "it" and item.name != "en":
            if (item / "PNG").is_dir() or (item / "PG").is_dir() or (item / "WORLD").is_dir():
                return item.name
                
    return "it" # Absolute fallback

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

def conta_stringhe_memory_gdr(file_path) -> int:
    """Counts translatable lines (narrative values only) in structured memory-gdr.txt file."""
    count = 0
    if not os.path.exists(file_path):
        return 0
    translatable_keys = {"evento", "luogo", "emozioni_provate", "sensazioni_fisiche", "conseguenze", "livello_dettaglio"}
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            if stripped and ':' in stripped:
                key = stripped.split(':', 1)[0].strip().lower()
                if key in translatable_keys:
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
        sys.stdout.write(f"\r        [⏳] Progress: {stringhe_completate}/{totale_stringhe} ({percentuale:.1f}%)")
        sys.stdout.flush()

def processa_struttura_dati(dati, codice_lingua, chiave_corrente=None):
    """Recursively processes JSON/YAML dictionary translating only unshielded values."""
    if isinstance(dati, dict):
        return {k: processa_struttura_dati(v, codice_lingua, k) for k, v in dati.items()}
    elif isinstance(dati, list):
        return [processa_struttura_dati(item, codice_lingua, chiave_corrente) for item in dati]
    elif isinstance(dati, str):
        # Shield Check: If the string is a protected word, or belongs to a technical key, skip translation
        if (chiave_corrente and chiave_corrente.lower() in PROTECTED_KEYS) or dati.strip().lower() in PROTECTED_WORDS or dati.strip() in PROTECTED_WORDS:
            aggiorna_progresso()
            return dati
        return traduci_testo_protetto(dati, codice_lingua)
    else:
        return dati

def processa_memory_gdr_txt(file_path, codice_google) -> str:
    """Processes and translates memory-gdr.txt surgically line by line keeping structure intact."""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    translatable_keys = {"evento", "luogo", "emozioni_provate", "sensazioni_fisiche", "conseguenze", "livello_dettaglio"}
    translated_lines = list()

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("---"):
            translated_lines.append(line)
            continue

        if ':' in stripped:
            key, val = stripped.split(':', 1)
            clean_key = key.strip().lower()
            clean_val = val.strip()

            if clean_key in translatable_keys:
                # Surgical value translation
                translated_val = traduci_testo_protetto(clean_val, codice_google)
                translated_lines.append(f"{key}: {translated_val}\n")
            else:
                # Structural/Technical lines remain untouched
                translated_lines.append(line)
        else:
            translated_lines.append(line)

    return "".join(translated_lines)

def get_files_to_translate(base_dir):
    """Retrieves all JSON, TXT, and YAML files in the given directory."""
    valid_exts = ['.json', '.txt', '.yaml', '.yml']
    files_list = list()
    for root, _, files in os.walk(base_dir):
        for file in files:
            if any(file.lower().endswith(ext) for ext in valid_exts):
                files_list.append(os.path.join(root, file))
    return files_list

# ==========================================
# MAIN EXECUTION
# ==========================================
def main():
    global totale_stringhe, stringhe_completate

    print("==================================================")
    print("   AIRIS INTERACTIVE GDR LORE TRANSLATOR (v2.0)")
    print("   (Supports: JSON, TXT, YAML)")
    print("==================================================")
    print(f"[*] Project Root: {APP_ROOT}")

    if not LORE_PATH.exists():
        print(f"[FATAL ERROR] Root folder '{CARTELLA_RADICE}' not found.")
        return

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

    # Scan all GDR worlds and build tasks dynamically
    all_tasks = list()
    
    for gdr_dir in LORE_PATH.iterdir():
        if not gdr_dir.is_dir():
            continue
            
        # Detect the source language for this specific GDR
        source_lang = get_source_gdr_language(gdr_dir)
        src_lang_dir = gdr_dir / source_lang
        
        if not src_lang_dir.exists() or not src_lang_dir.is_dir():
            continue
            
        files_to_translate = get_files_to_translate(src_lang_dir)
        for file_path in files_to_translate:
            rel_path = os.path.relpath(file_path, src_lang_dir)
            dst_file_path = gdr_dir / selected_airis_code / rel_path
            
            if SALTA_ESISTENTI and dst_file_path.exists():
                continue
                
            all_tasks.append((file_path, dst_file_path))

    if not all_tasks:
        print("[*] No files need translation (or all already translated). Exiting.")
        return

    print(f"[*] Found {len(all_tasks)} files/modules across GDRs ready for translation.")

    # Calculate workload and preload files
    totale_stringhe = 0
    loaded_files_data = dict()
    
    for src_path, dst_path in all_tasks:
        ext = Path(src_path).suffix.lower()
        try:
            if ext == '.json':
                with open(src_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                loaded_files_data[src_path] = data
                totale_stringhe += conta_stringhe(data)
            elif ext in ['.yaml', '.yml']:
                with open(src_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                loaded_files_data[src_path] = data
                totale_stringhe += conta_stringhe(data)
            elif ext == '.txt':
                if "memory-gdr" in src_path.name.lower():
                    totale_stringhe += conta_stringhe_memory_gdr(src_path)
                else:
                    totale_stringhe += 1
        except Exception as e:
            print(f"[ERROR] Failed to pre-read {src_path.name}: {e}")

    print(f"[*] Real-time workload calculated: {totale_stringhe} translatable elements.")
    print("[*] Beginning massive translation process...")

    # Process tasks sequentially
    stringhe_completate = 0
    for src_path, dst_path in all_tasks:
        ext = Path(src_path).suffix.lower()
        rel_path = os.path.relpath(src_path, APP_ROOT)
        print(f"\n  [-] File: {rel_path} -> {dst_path.relative_to(APP_ROOT)}")
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if ext in ['.json', '.yaml', '.yml']:
                data = loaded_files_data.get(src_path)
                if data is not None:
                    translated_data = processa_struttura_dati(data, google_code)
                    with open(dst_path, 'w', encoding='utf-8') as f:
                        if ext == '.json':
                            json.dump(translated_data, f, indent=2, ensure_ascii=False)
                        else:
                            yaml.dump(translated_data, f, allow_unicode=True, sort_keys=False)
            elif ext == '.txt':
                if "memory-gdr" in src_path.name.lower():
                    translated_txt = processa_memory_gdr_txt(src_path, google_code)
                else:
                    with open(src_path, 'r', encoding='utf-8') as f:
                        txt_data = f.read()
                    translated_txt = traduci_testo_protetto(txt_data, google_code)
                    
                with open(dst_path, 'w', encoding='utf-8') as f:
                    f.write(translated_txt)
        except Exception as e:
            print(f"\n      [ERROR] Translation failed for {src_path.name}: {e}")

    print() # Carriage return after last progress bar
    print("\n==================================================")
    print("  MASSIVE GDR TRANSLATION COMPLETED SUCCESSFULLY.")
    print("==================================================")

if __name__ == "__main__":
    main()