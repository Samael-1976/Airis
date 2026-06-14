import json
import re
import time
import os
import sys
import yaml
from deep_translator import GoogleTranslator

# ==========================================
# CONFIGURAZIONE UTENTE
# ==========================================

CARTELLA_RADICE = "lore"
CARTELLA_SORGENTE = "it"
SALTA_ESISTENTI = True

# Mappatura dei codici: "Codice_Airis" (Nome Cartella Lore): "Codice_Google_Translate"
LINGUE_TARGET = {
    "ar": "ar",       # Arabo
    "br": "pt",       # Portoghese / Brasiliano
    "cn": "zh-CN",    # Cinese Semplificato
    "de": "de",       # Tedesco
    "en": "en",       # Inglese
    "es": "es",       # Spagnolo
    "fr": "fr",       # Francese
    "hi": "hi",       # Indiano / Hindi
    "jp": "ja",       # Giapponese
    "kr": "ko",       # Coreano
    "nl": "nl",       # Olandese
    "pl": "pl",       # Polacco
    "ru": "ru"        # Russo
}

# ==========================================
# VARIABILI GLOBALI PER IL PROGRESSO
# ==========================================
totale_stringhe = 0
stringhe_completate = 0
PATTERN_VARIABILI = re.compile(r'(\{\{.*?\}\}|<<.*?>>|<.*?>|\[.*?\])')

# --- [BARRIERA DI PROTEZIONE ASSOLUTA AIRIS] ---
# Queste parole non devono MAI essere tradotte per non corrompere la logica del backend
PROTECTED_WORDS = {
    # Emotivi e Endocrini
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
    # Moduli Cognitivi
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
    # Payloads
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

def conta_stringhe(dati):
    """Conta il numero totale di stringhe in dizionari/liste (JSON/YAML)."""
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

def traduci_testo_protetto(testo, codice_lingua):
    """Traduce proteggendo le variabili, gestendo i chunk e aggiornando il progresso."""
    global stringhe_completate, totale_stringhe

    if not testo or not str(testo).strip():
        aggiorna_progresso()
        return testo

    # Assicuriamoci che sia una stringa
    testo = str(testo)

    # 1. MASCHERAMENTO
    variabili_trovate = PATTERN_VARIABILI.findall(testo)
    testo_mascherato = testo
    for i, var in enumerate(variabili_trovate):
        testo_mascherato = testo_mascherato.replace(var, f"__VAR_{i}__")

    # 2. AUTO-CHUNKER
    MAX_LEN = 4500
    chunks = []
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

    # 3. TRADUZIONE CON ANTI-FREEZE
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

    # 4. RIPRISTINO VARIABILI
    for i, var in enumerate(variabili_trovate):
        pattern_ripristino = re.compile(r'__VAR_\s*' + str(i) + r'\s*__', re.IGNORECASE)
        testo_tradotto_completo = pattern_ripristino.sub(var, testo_tradotto_completo)

    # 5. AGGIORNAMENTO PROGRESSO VISIVO
    aggiorna_progresso()
    return testo_tradotto_completo

def aggiorna_progresso():
    """Stampa la percentuale sulla stessa riga del CMD."""
    global stringhe_completate, totale_stringhe
    stringhe_completate += 1
    if totale_stringhe > 0:
        percentuale = (stringhe_completate / totale_stringhe) * 100
        sys.stdout.write(f"\r        [⏳] Progresso: {stringhe_completate}/{totale_stringhe} ({percentuale:.1f}%)")
        sys.stdout.flush()

def processa_struttura_dati(dati, codice_lingua, chiave_corrente=None):
    """Naviga JSON o YAML traducendo solo i valori non protetti."""
    if isinstance(dati, dict):
        return {k: processa_struttura_dati(v, codice_lingua, k) for k, v in dati.items()}
    elif isinstance(dati, list):
        return [processa_struttura_dati(item, codice_lingua, chiave_corrente) for item in dati]
    elif isinstance(dati, str):
        # Se il testo o la sua chiave appartiene alle barriere di protezione, bypassa la traduzione
        if (chiave_corrente and chiave_corrente.lower() in PROTECTED_KEYS) or dati.strip().lower() in PROTECTED_WORDS or dati.strip() in PROTECTED_WORDS:
            aggiorna_progresso()
            return dati
        return traduci_testo_protetto(dati, codice_lingua)
    else:
        return dati

def get_files_to_translate(base_dir):
    """Recupera tutti i file JSON, TXT e YAML."""
    valid_exts = ['.json', '.txt', '.yaml', '.yml']
    files_list = []
    for root, _, files in os.walk(base_dir):
        for file in files:
            if any(file.lower().endswith(ext) for ext in valid_exts):
                files_list.append(os.path.join(root, file))
    return files_list

# ==========================================
# ESECUZIONE PRINCIPALE
# ==========================================
def main():
    global totale_stringhe, stringhe_completate

    print("==================================================")
    print("  AVVIO MOTORE DI TRADUZIONE MASSIVA AIRIS")
    print("  (Supporto: JSON, TXT, YAML)")
    print("==================================================")

    if not os.path.exists(CARTELLA_RADICE):
        print(f"[ERRORE] La cartella radice '{CARTELLA_RADICE}' non esiste.")
        return

    cartelle_sorgente_trovate = []
    for root, dirs, files in os.walk(CARTELLA_RADICE):
        if CARTELLA_SORGENTE in dirs:
            cartelle_sorgente_trovate.append(os.path.join(root, CARTELLA_SORGENTE))

    if not cartelle_sorgente_trovate:
        print(f"[!] Nessuna cartella '{CARTELLA_SORGENTE}' trovata all'interno di '{CARTELLA_RADICE}'.")
        return

    print(f"[*] Trovate {len(cartelle_sorgente_trovate)} cartelle sorgente '{CARTELLA_SORGENTE}'.\n")

    for cartella_it in cartelle_sorgente_trovate:
        print(f"[📁] Analisi cartella: {cartella_it}")
        cartella_genitore = os.path.dirname(cartella_it)
        file_da_tradurre = get_files_to_translate(cartella_it)
        
        for file_path in file_da_tradurre:
            percorso_relativo = os.path.relpath(file_path, cartella_it)
            estensione = os.path.splitext(file_path)[1].lower()
            print(f"\n  [-] File: {percorso_relativo} ({estensione.upper()})")

            # 1. CARICAMENTO DEL FILE IN BASE ALL'ESTENSIONE
            dati_originali = None
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    if estensione == '.json':
                        dati_originali = json.load(f)
                        totale_stringhe = conta_stringhe(dati_originali)
                    elif estensione in ['.yaml', '.yml']:
                        dati_originali = yaml.safe_load(f)
                        totale_stringhe = conta_stringhe(dati_originali)
                    elif estensione == '.txt':
                        dati_originali = f.read()
                        totale_stringhe = 1 # Il TXT è considerato come un'unica grande stringa
            except Exception as e:
                print(f"      [ERRORE] Impossibile leggere il file. Salto. Errore: {e}")
                continue

            # 2. TRADUZIONE PER OGNI LINGUA
            for cartella_lingua, codice_iso in LINGUE_TARGET.items():
                cartella_destinazione_base = os.path.join(cartella_genitore, cartella_lingua)
                percorso_file_destinazione = os.path.join(cartella_destinazione_base, percorso_relativo)

                if SALTA_ESISTENTI and os.path.exists(percorso_file_destinazione):
                    print(f"      [>] {cartella_lingua.upper()}: Già tradotto (Saltato)")
                    continue

                print(f"      [>] {cartella_lingua.upper()}: In traduzione...", end="")
                os.makedirs(os.path.dirname(percorso_file_destinazione), exist_ok=True)
                stringhe_completate = 0

                # Traduzione in base al tipo di dato
                if estensione in ['.json', '.yaml', '.yml']:
                    dati_tradotti = processa_struttura_dati(dati_originali, codice_iso)
                elif estensione == '.txt':
                    dati_tradotti = traduci_testo_protetto(dati_originali, codice_iso)

                # 3. SALVATAGGIO DEL FILE IN BASE ALL'ESTENSIONE
                with open(percorso_file_destinazione, 'w', encoding='utf-8') as f:
                    if estensione == '.json':
                        json.dump(dati_tradotti, f, indent=2, ensure_ascii=False)
                    elif estensione in ['.yaml', '.yml']:
                        yaml.dump(dati_tradotti, f, allow_unicode=True, sort_keys=False)
                    elif estensione == '.txt':
                        f.write(dati_tradotti)
                
                print() # A capo dopo la barra di progresso

    print("\n==================================================")
    print("  TRADUZIONE MASSIVA COMPLETATA CON SUCCESSO.")
    print("==================================================")

if __name__ == "__main__":
    main()