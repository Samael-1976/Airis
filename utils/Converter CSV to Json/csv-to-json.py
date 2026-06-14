import csv
import json
import os

# --- CONFIGURAZIONE ---
# Nome del file CSV di input (esportato da Excel)
INPUT_CSV = 'intent_gemma.csv'
# Nome del file JSON di output
OUTPUT_JSON = 'intent_gemma.json'

# --- MAPPA DELLE COLONNE (Modificare se si cambia l'ordine in Excel) ---
COL_DESCRIPTION = 0
COL_FILENAME = 1
COL_CATEGORY_FOLDER = 2
COL_EMOTION = 3
COL_SHORT_DESCRIPTION = 4
COL_IS_ALTERNATIVE = 6
COL_DURATION = 7


def parse_csv_to_json():
    print(f"--- INIZIO CONVERSIONE: {INPUT_CSV} -> {OUTPUT_JSON} ---")
    
    if not os.path.exists(INPUT_CSV):
        print(f"[ERRORE] Il file '{INPUT_CSV}' non esiste. Assicurati di averlo creato.")
        return

    parsed_data = []
    rows_processed = 0
    rows_skipped = 0

    try:
        # 'utf-8-sig' è fondamentale per leggere CSV creati da Excel (rimuove il BOM)
        with open(INPUT_CSV, mode='r', encoding='utf-8-sig') as infile:
            reader = csv.reader(infile, delimiter=';')
            
            for i, row in enumerate(reader):
                # Salta l'intestazione se presente (euristica: controlla se la prima colonna è "DESCRIPTION")
                if i == 0 and row and "DESCRIPTION" in row[0].upper():
                    print("[INFO] Intestazione rilevata e saltata.")
                    continue

                # Controllo validità riga (almeno le colonne fondamentali devono esserci)
                if not row or len(row) < 3:
                    print(f"[WARN] Riga {i+1} saltata: dati insufficienti o vuota.")
                    rows_skipped += 1
                    continue

                try:
                    # 1. Estrazione Dati Base
                    description = row[COL_DESCRIPTION].strip()
                    category_folder = row[COL_CATEGORY_FOLDER].strip()
                    filename = row[COL_FILENAME].strip()
                    
                    # 2. Costruzione del Filepath Relativo (Agnostico)
                    # Questo path sarà usato dal backend come base per costruire i path stagionali
                    # Es: "001_Foundational_States/state_idle.mp4"
                    # Nota: Usiamo forward slash '/' per compatibilità JSON/Web
                    if category_folder and filename:
                        filepath = f"{category_folder}/{filename}"
                    else:
                        print(f"[WARN] Riga {i+1}: Categoria o Filename mancanti. Salto.")
                        rows_skipped += 1
                        continue

                    # 3. Gestione Durata
                    duration_seconds = 0.0
                    try:
                        if len(row) > COL_DURATION:
                            dur_str = row[COL_DURATION].strip().replace("''", "").replace(",", ".")
                            if dur_str:
                                duration_seconds = float(dur_str)
                    except ValueError:
                        print(f"[WARN] Riga {i+1}: Durata non valida ('{row[COL_DURATION]}'). Impostata a 0.")

                    # 4. Gestione Emozioni (Lista)
                    emotion_list = []
                    if len(row) > COL_EMOTION:
                        raw_emotions = row[COL_EMOTION].strip()
                        if raw_emotions:
                            # Divide per virgola e pulisce gli spazi
                            emotion_list = [e.strip() for e in raw_emotions.split(',') if e.strip()]

                    # 5. Altri Campi
                    short_description = row[COL_SHORT_DESCRIPTION].strip() if len(row) > COL_SHORT_DESCRIPTION else ""
                    
                    is_alternative = False
                    if len(row) > COL_IS_ALTERNATIVE:
                        alt_marker = row[COL_IS_ALTERNATIVE].strip().upper()
                        # Rileva vari modi di dire "Sì"
                        if "ALTERNATIVE" in alt_marker or "YES" in alt_marker or "TRUE" in alt_marker or "SI" in alt_marker:
                            is_alternative = True

                    # 6. Creazione Oggetto JSON
                    intent_object = {
                        'description': description,
                        'filepath': filepath, # Path relativo: Categoria/File
                        'category': category_folder, # Utile per raggruppamenti
                        'emotion': emotion_list,
                        'short_description': short_description,
                        'is_alternative': is_alternative,
                        'duration_seconds': duration_seconds
                    }
                    
                    parsed_data.append(intent_object)
                    rows_processed += 1

                except IndexError as e:
                    print(f"[ERRORE] Riga {i+1}: Indice colonna fuori range. Controlla il CSV. {e}")
                    rows_skipped += 1

        # --- SCRITTURA JSON ---
        with open(OUTPUT_JSON, mode='w', encoding='utf-8') as outfile:
            json.dump(parsed_data, outfile, indent=2, ensure_ascii=False)

        print(f"\n--- CONVERSIONE COMPLETATA ---")
        print(f"Righe processate: {rows_processed}")
        print(f"Righe saltate/errate: {rows_skipped}")
        print(f"File creato: {OUTPUT_JSON}")
        print("NOTA: Il campo 'filepath' nel JSON è ora relativo (Categoria/File).")
        print("      Il backend userà questo path per cercare nelle cartelle Stagione/Orario.")

    except Exception as e:
        print(f"\n[ERRORE CRITICO] {e}")

if __name__ == "__main__":
    parse_csv_to_json()