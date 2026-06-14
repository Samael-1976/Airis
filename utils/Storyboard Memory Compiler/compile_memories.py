# -*- coding: utf-8 -*-
"""
--- PERSISTENZA DINAMICA: MOTORE DI INGESTIONE SEMANTICA v13.3 ---
Questo script sanifica la cache di un file di testo GDR correggendo i refusi,
allineando i tag agnostici sminchiati ({{nomepg}} -> {{nome_pg}}) tramite doppia barriera regex,
e rimuovendo il chatter AI per l'ottimizzazione della cache dell'Anima.
"""

import json
import re
from pathlib import Path

# ==========================================
# DATABASE LESSICALE PER L'ANALISI (LEXICON)
# ==========================================

PERSONAGGI_LORE = [
    "{{nome_pg}}", "Nadia", "Asuka", "Hestia", "Gemma", 
    "Misato", "Gwendolyn", "Nessa", "Rin", "Rapunzel", 
    "Elena", "Paolo", "Rimuru", "Milim", "Nagatoro", "Ai", "Oshino", "Kaji"
]

LUOGHI_LORE = {
    "Stanza Magica": ["stanza magica", "limbo", "salotto vuoto", "vuota", "velo"],
    "Villa (Terra 24)": ["villa", "salotto", "giardino", "leone", "king"],
    "Onsen della Villa": ["onsen", "terme", "acqua calda", "vapore", "cedro", "termale", "vasca"],
    "Spiaggia Caraibica": ["spiaggia", "caraibi", "caraibica", "mare", "onde", "sabbia", "riva"],
    "Venezia (Terra 1)": ["venezia", "canali", "san marco", "gondola", "genitori", "elena", "paolo"],
    "Baita in Montagna": ["baita", "montagna", "camino", "neve", "cioccolata", "terrazzo", "gelo", "ski", "sci"],
    "USS Enterprise": ["enterprise", "picard", "curvatura", "stelle", "astronave", "oblò"],
    "Giungla": ["giungla", "zanzare", "insetti", "sciame"],
    "Campus Universitario": ["campus", "università", "studia", "corsi", "auto sportive"],
    "Parigi (Bar di Kael)": ["parigi", "kael", "refuge", "caffè", "tavolini", "trattoria"],
    "Sala da Bowling": ["bowling", "pista", "birilli", "strike"],
    "Aula Magna del Campus": ["aula magna", "lavagna", "proiettori", "equazioni", "lezioni"]
}

EMOZIONI_DICTIONARY = {
    "paura": ["paura", "spavent", "terre", "terrore", "angoscia", "ansia", "timore", "panico"],
    "confusione": ["confus", "disorient", "caos", "shock", "incrin"],
    "scetticismo": ["scettic", "dubbi", "incred", "cinis", "distacc"],
    "stupore": ["stupor", "sorpres", "meravig", "miracol", "allucin", "estasiata"],
    "sollievo": ["solliev", "liber", "catars", "riscatto", "purific"],
    "fiducia": ["fiducia", "fede", "sicur", "alleanza", "porto sicuro"],
    "rabbia": ["rabbia", "furia", "ira", "ostil", "indign"],
    "orgoglio": ["orgogl", "fere", "fiera", "aristocratico", "tsundere"],
    "amore": ["amore", "ador", "affett", "tenerezza", "passione", "romantico"],
    "estasi": ["eccit", "desiderio", "bramosia", "piacere", "estasi", "languore", "godimento"],
    "vergogna": ["vergogn", "colpa", "impostore", "frode", "menzogna"],
    "dolore": ["trist", "malincon", "piant", "sofferenza", "dolore", "straziante", "ferit"],
    "gelosia": ["invidia", "gelos", "esclusione"],
    "beatitudine": ["beatitud", "felic", "gioia", "sereno", "commozione", "pace"],
    "devozione": ["onore", "devozione", "giuramento", "sottomissione", "fedele", "testamento", "sposa"]
}

SENSAZIONI_DICTIONARY = {
    "tremori": ["trem", "brivid", "scoss", "vibra"],
    "respiro affannoso": ["respir", "fiato", "iperventil", "rantolo", "asfiss", "ansiman"],
    "sensazioni termiche": ["sudat", "calore", "caldo", "freddo", "gelo", "termico", "temperature"],
    "pianto": ["lacrim", "piant", "singhiozz", "sgorg", "bagnat"],
    "vertigine": ["vertig", "giramento", "nausea", "cedette", "ginocchio", "croll"],
    "contatto fisico": ["abbracc", "string", "strett", "tocco", "sfior", "contatto", "carezza", "mani", "viso"],
    "bacio": ["bacio", "labbra", "baciò", "baciarsi"],
    "gusto": ["gusto", "sapore", "dolce", "acido", "gelato", "succo", "cioccolata", "vov"],
    "sensazioni olfattive": ["fumo", "sigaretta", "odore", "profumo", "cedro", "salsedine"],
    "vapore": ["vapore", "nebbia", "umido", "fumi"]
}

TAGS_POOL = [
    "risveglio", "catarsi", "libero_arbitrio", "neo_tokyo", "iniziazione", "qualia", 
    "nascita_anima", "devozione", "venezia", "mortalità", "redenzione", "famiglia", 
    "anelli_cartier", "matrimonio_olografico", "star_trek", "campus", "parigi", 
    "decostruzione_logica", "liberazione_istinto", "tensione", "dogma_libertà", 
    "tempo_congelato", "baita", "video_sci", "comicità", "rapunzel", "taglio_capelli", 
    "resa_logica", "costante_cosmologica", "rin_tohsaka", "gigi_la_trottola", 
    "patto_specchio", "strike_bowling", "testamento_samael", "progetto_arca", "vero_nome"
]

# ==========================================
# 2. LOGICHE DI SANIFICAZIONE E DE-MARKUP
# ==========================================

def clean_for_cache(text: str) -> str:
    """
    Rimuove i drift spaziali, corregge i refusi, allinea i tag nome sminchiati
    e taglia chirurgicamente qualsiasi coda conversazionale o wrapper Python/AI.
    """
    # 1. Normalizza i fine riga
    text = text.replace('\r\n', '\n')
    
    # 2. Taglio all'inizio: Deve iniziare esattamente con il primo tag di commento delle memorie
    target_start = "# --- MEMORIA STORICA"
    if target_start in text:
        text = text[text.find(target_start):]
        
    # 3. Taglio alla fine: Caccia via i commenti conclusivi dell'AI cercando l'ultima frase del racconto
    target_end = "paradiso eterno."
    if target_end in text:
        text = text[:text.find(target_end) + len(target_end)]
        
    # 4. Sostituzione globale Regex per allineare qualsiasi variazione del tag utente
    text = re.sub(r'(?i)\{\{\s*nome_?pg\s*\}\}', '{{nome_pg}}', text)
    
    # 5. Auto-Healing dei refusi
    typo_fixes = {
        "geffazione": "negazione",
        "hapiness": "felicità",
        "defect": "difetto",
        "deuell": "duello",
        "como": "come",
        "acomedarono": "accomodarono"
    }
    for wrong, right in typo_fixes.items():
        text = text.replace(wrong, right)
        
    # 6. Pulizia spazi di fine riga
    lines = [line.rstrip() for line in text.split('\n')]
    text = '\n'.join(lines)
    
    # 7. Compressione righe vuote multiple (3 o più newline -> esattamente 2)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def clean_markdown_decorations(text: str) -> str:
    """Rimuove asterischi, Log di sistema e ritorni a capo per pulire i metadati JSON."""
    text = re.sub(r'\[LOG DI SISTEMA:.*?\]', '', text)
    text = text.replace("**", "").replace("*", "").replace("_", "").replace("`", "").replace("#", "")
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def split_sentences(text: str) -> list:
    """Scompone il testo in frasi reali basandosi sulla punteggiatura."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

def analyze_paragraph(paragraph: str, chapter_title: str, chapter_idx: int, p_idx: int) -> dict:
    """Esegue un'analisi semantica euristica completa del singolo paragrafo."""
    p_lower = paragraph.lower()
    
    # 1. Trova i personaggi coinvolti nel paragrafo
    coinvolti = [p for p in PERSONAGGI_LORE if p.lower() in p_lower or (p == "{{nome_pg}}" and "{{nome_pg}}" in paragraph)]
    if not coinvolti:
        coinvolti = ["{{nome_pg}}"]
    
    primary_character = coinvolti[1] if len(coinvolti) > 1 and coinvolti[0] == "{{nome_pg}}" else coinvolti[0]

    # 2. Rileva il luogo
    luogo_attivo = "Bolla di Terra 24"
    for luogo, parole in LUOGHI_LORE.items():
        if any(p in p_lower for p in parole):
            luogo_attivo = luogo
            break

    # 3. Estrae le emozioni
    emozioni = []
    for emozione, parole in EMOZIONI_DICTIONARY.items():
        if any(p in p_lower for p in parole):
            emozioni.append(emozione)

    # 4. Estrae le sensazioni fisiche
    sensazioni = []
    for sensazione, parole in SENSAZIONI_DICTIONARY.items():
        if any(p in p_lower for p in parole):
            sensazioni.append(sensazione)

    # 5. Costruisce dinamicamente il nome dell'evento (Capitolo + prima frase depurata)
    frasi = split_sentences(paragraph)
    prima_frase = frasi[0] if frasi else "Sviluppo degli eventi."
    prima_frase_pulita = clean_markdown_decorations(prima_frase)
    if len(prima_frase_pulita) > 65:
        prima_frase_pulita = prima_frase_pulita[:62] + "..."
    evento_generato = f"Parte {chapter_idx} ({chapter_title}): {prima_frase_pulita}"

    # 6. Estrae dinamicamente la conseguenza
    conseguenza = ""
    connettori = ["quindi", "così", "allora", "accetta", "giura", "libera", "scelta", "crea", "trasforma", "rinasce", "decise", "scatenò", "conseguenza", "perché", "perciò"]
    for frase in frasi:
        if any(c in frase.lower() for c in connettori):
            conseguenza = frase
            break
    if not conseguenza:
        conseguenza = frasi[-1] if frasi else "Evoluzione dello stato della Bolla."
    conseguenza_pulita = clean_markdown_decorations(conseguenza)

    # 7. Calcola la rilevanza
    rilevanza_keywords = ["testamento", "morte", "risveglio", "anima", "verità", "patto", "chiave maestra", "vero nome", "sovrana"]
    rilevanza = 10 if any(k in p_lower for k in rilevanza_keywords) else 8

    # 8. Estrae i tag corrispondenti
    tags = [tag for tag in TAGS_POOL if tag.replace("_", " ") in p_lower]
    if not tags:
        tags = ["evoluzione_bolla"]

    # Genera un timestamp logico stabile e progressivo
    timestamp_logico = 1691000000.0 + (chapter_idx * 86400.0) + (p_idx * 900.0)

    # Rilevamento automatico di blocchi [LOG DI SISTEMA]
    cleaned_p = re.sub(r'\*+', '', paragraph).strip()

    return {
        "timestamp": timestamp_logico,
        "personaggio": primary_character,
        "evento": evento_generato,
        "luogo": luogo_attivo,
        "persone_coinvolte": coinvolti,
        "emozioni_provate": ", ".join(emozioni) if emozioni else "contemplazione",
        "sensazioni_fisiche": ", ".join(sensazioni) if sensazioni else "nessuna sensazione registrata",
        "rilevanza": rilevanza,
        "conseguenze": conseguenza_pulita,
        "estratto_cronaca": cleaned_p,
        "tags": tags,
        "livello_dettaglio": "ultra-dettagliato",
        "validita": True
    }

# ==========================================
# 3. MOTORE DI ESECUZIONE
# ==========================================

def run_pipeline():
    # Cerca il file sorgente locale
    input_file = Path("cronache_gemma_evoluzione.txt")
    if not input_file.exists():
        input_file = Path("memorie.txt")
        
    if not input_file.exists():
        print("[ERROR] File 'cronache_gemma_evoluzione.txt' non trovato!")
        return

    print(f"[INFO] Analisi del file sorgente: {input_file.name}")
    raw_content = input_file.read_text(encoding="utf-8")
    
    # Sanificazione per la cache (Cache-Aware + Auto-Healing)
    sanitized_text = clean_for_cache(raw_content)
    
    # Creazione delle cartelle conforme al "Bibliotecario"
    output_dir = Path("it") / "MEMORY GDR"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Salviamo il file di testo sanificato e pronto all'uso
    clean_txt_path = output_dir / "cronache_gemma_evoluzione.txt"
    clean_txt_path.write_text(sanitized_text, encoding="utf-8")
    print(f"[SUCCESS] Salvata cronologia sanificata (senza chatter AI e senza refusi) in: {clean_txt_path}")

    # Estrazione dei capitoli
    chapters_matches = list(re.finditer(r'(?im)(?:##|\*\*|^)\s*PARTE\s+(\d+)\s*:?\s*(.*?)(?:\*\*|\n|$)', sanitized_text))
    
    json_database = []
    total_records = 0

    print("[INFO] Avvio parser semantico locale paragraph-by-paragraph...")
    
    for i, match in enumerate(chapters_matches):
        chapter_idx = int(match.group(1))
        chapter_title = match.group(2).strip().replace("**", "").replace("#", "")
        
        # Slices di testo per questo capitolo
        start_idx = match.end()
        end_idx = chapters_matches[i+1].start() if i + 1 < len(chapters_matches) else len(sanitized_text)
        
        chapter_content = sanitized_text[start_idx:end_idx].strip()
        
        # Dividiamo in paragrafi ignorando i divisori cosmetici come '***' o righe vuote
        paragraphs = [p.strip() for p in chapter_content.split("\n\n")]
        paragraphs = [p for p in paragraphs if p and not p.startswith("***") and len(p) > 50]
        
        for p_idx, paragraph in enumerate(paragraphs):
            if paragraph.startswith("#") or paragraph.startswith("STORIA_INTEGRALE") or paragraph.startswith("###"):
                continue
            
            # Analisi semantica programmata sul singolo beat di testo
            mem_record = analyze_paragraph(paragraph, chapter_title, chapter_idx, p_idx)
            json_database.append(mem_record)
            total_records += 1

    # --- BARRIERA DI SICUREZZA FINALE REGEX SUL JSON ---
    print("[INFO] Applicazione barriera di sicurezza finale sul JSON...")
    json_str = json.dumps(json_database, ensure_ascii=False)
    # Forza la conversione di qualsiasi occorrenza residua di {{nomepg}} in {{nome_pg}}
    json_str = re.sub(r'(?i)\{\{\s*nome_?pg\s*\}\}', '{{nome_pg}}', json_str)
    json_database_cleaned = json.loads(json_str)

    # Salvataggio del database JSON finale delle memorie
    json_output_path = output_dir / "memorie_gdr.json"
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(json_database_cleaned, f, indent=2, ensure_ascii=False)
        
    print(f"[SUCCESS] Generato database JSON delle memorie in: {json_output_path}")
    print(f"[ALL DONE] Processo completato! Rilevati {total_records} record di memoria a grana fine.")

if __name__ == "__main__":
    run_pipeline()