import json
import re
import time
import os
import sys
from deep_translator import GoogleTranslator

# ==========================================
# CONFIGURAZIONE UTENTE
# ==========================================

FILE_ORIGINALE = "it.json" 

# Mappatura dei codici: "Codice_Airis" (Nome File Output): "Codice_Google_Translate"
LINGUE_TARGET = {
    "ar": "ar",       # Arabo
    "br": "pt",       # Portoghese / Brasiliano (br in Airis)
    "cn": "zh-CN",    # Cinese Semplificato (cn in Airis)
    "de": "de",       # Tedesco
    "en": "en",       # Inglese
    "es": "es",       # Spagnolo
    "fr": "fr",       # Francese
    "hi": "hi",       # Indiano / Hindi (hi in Airis)
    "jp": "ja",       # Giapponese (jp in Airis)
    "kr": "ko",       # Coreano (kr in Airis)
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
    """Conta il numero totale di stringhe nel JSON per calcolare la percentuale."""
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

    if not testo or not testo.strip():
        aggiorna_progresso()
        return testo

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

    # 3. TRADUZIONE CON ANTI-FREEZE (MAX 3 TENTATIVI)
    traduttore = GoogleTranslator(source='auto', target=codice_lingua)
    testo_tradotto_completo = ""
    MAX_RETRIES = 3

    for i, chunk in enumerate(chunks):
        chunk_tradotto = None
        for tentativo in range(MAX_RETRIES):
            try:
                chunk_tradotto = traduttore.translate(chunk)
                break # Uscita dal loop se ha successo
            except Exception:
                time.sleep(2) # Pausa prima di riprovare
        
        # Se dopo 3 tentativi fallisce, mantiene l'originale per non bloccarsi
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
        # Il \r riporta il cursore all'inizio della riga, sovrascrivendo il testo precedente
        sys.stdout.write(f"\r    [⏳] Progresso: {stringhe_completate}/{totale_stringhe} ({percentuale:.1f}%)")
        sys.stdout.flush()

def processa_struttura_json(dati, codice_lingua, chiave_corrente=None):
    if isinstance(dati, dict):
        return {k: processa_struttura_json(v, codice_lingua, k) for k, v in dati.items()}
    elif isinstance(dati, list):
        return [processa_struttura_json(item, codice_lingua, chiave_corrente) for item in dati]
    elif isinstance(dati, str):
        # Se il testo o la sua chiave appartiene alle barriere di protezione, bypassa la traduzione
        if (chiave_corrente and chiave_corrente.lower() in PROTECTED_KEYS) or dati.strip().lower() in PROTECTED_WORDS or dati.strip() in PROTECTED_WORDS:
            aggiorna_progresso()
            return dati
        return traduci_testo_protetto(dati, codice_lingua)
    else:
        return dati

# ==========================================
# ESECUZIONE PRINCIPALE
# ==========================================
def main():
    global totale_stringhe, stringhe_completate

    print("==================================================")
    print("  AVVIO MOTORE DI TRADUZIONE MULTILINGUA AIRIS")
    print("==================================================")

    if not os.path.exists(FILE_ORIGINALE):
        print(f"[ERRORE CRITICO] Il file '{FILE_ORIGINALE}' non è stato trovato.")
        return

    print(f"[*] Lettura del file sorgente: {FILE_ORIGINALE}...")
    with open(FILE_ORIGINALE, 'r', encoding='utf-8') as f:
        try:
            dati_originali = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[ERRORE CRITICO] Il file {FILE_ORIGINALE} non è un JSON valido. Errore: {e}")
            return

    # Calcola il totale delle stringhe da tradurre
    totale_stringhe = conta_stringhe(dati_originali)
    print(f"[*] Trovate {totale_stringhe} stringhe di testo da tradurre per ogni lingua.")

    for codice_airis, codice_google in LINGUE_TARGET.items():
        stringhe_completate = 0 # Resetta il contatore per la nuova lingua
        print(f"\n[>] Inizio traduzione in: {codice_airis.upper()} (Google target: {codice_google})...")
        
        dati_tradotti = processa_struttura_json(dati_originali, codice_google)
        
        # Stampa una riga vuota per non sovrascrivere l'ultimo aggiornamento del progresso
        print() 
        
        with open(f"{codice_airis}.json", 'w', encoding='utf-8') as f:
            json.dump(dati_tradotti, f, indent=2, ensure_ascii=False)
            
        print(f"[V] File salvato con successo: {codice_airis}.json")

    print("\n==================================================")
    print("  TRADUZIONE GLOBALE COMPLETATA CON SUCCESSO.")
    print("==================================================")

if __name__ == "__main__":
    main()