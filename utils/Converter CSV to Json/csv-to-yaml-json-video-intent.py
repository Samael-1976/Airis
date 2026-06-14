import csv
import json
import os

# --- CONFIGURAZIONE ---
INPUT_CSV = 'intent.csv'
OUTPUT_JSON = 'intent.json'

# --- MAPPA DELLE COLONNE (Allineata con il nuovo standard) ---
COL_DESCRIPTION = 0
COL_CATEGORY_FOLDER = 1
COL_FILENAME = 2
COL_DURATION = 3
COL_EMOTION = 4
COL_SHORT_DESCRIPTION = 5
COL_IS_ALTERNATIVE = 6

def main():
    print(f"Inizio la lettura del file CSV: {INPUT_CSV}")

    if not os.path.exists(INPUT_CSV):
        print(f"[ERRORE] Il file '{INPUT_CSV}' non è stato trovato.")
        return

    parsed_data = []
    rows_processed = 0

    try:
        # 'utf-8-sig' gestisce il carattere BOM di Excel
        with open(INPUT_CSV, mode='r', encoding='utf-8-sig') as infile:
            reader = csv.reader(infile, delimiter=';')
            
            for i, row in enumerate(reader):
                # Salta intestazione
                if i == 0 and row and "DESCRIPTION" in row[0].upper():
                    continue

                # Salta righe vuote o malformate (minimo 3 colonne necessarie: Desc, Cat, File)
                if not row or len(row) < 3:
                    print(f"Riga {i+1} saltata: dati insufficienti.")
                    continue

                try:
                    # 1. Dati Base
                    description = row[COL_DESCRIPTION].strip()
                    category = row[COL_CATEGORY_FOLDER].strip()
                    filename = row[COL_FILENAME].strip()

                    # 2. Costruzione Path Relativo (Agnostico)
                    # Il backend userà questo per cercare nelle cartelle Stagione/Orario
                    if category and filename:
                        filepath = f"{category}/{filename}"
                    else:
                        print(f"Riga {i+1}: Categoria o Filename mancanti. Salto.")
                        continue
                    
                    # 3. Durata
                    duration_seconds = 0
                    if len(row) > COL_DURATION:
                        try:
                            dur_str = row[COL_DURATION].strip().replace("''", "").replace(",", ".")
                            if dur_str:
                                duration_seconds = float(dur_str)
                        except ValueError:
                            print(f"Attenzione: durata non valida nella riga {i+1}. Impostata a 0.")

                    # 4. Emozioni (Lista)
                    emotion_list = []
                    if len(row) > COL_EMOTION:
                        raw_emotions = row[COL_EMOTION].strip()
                        if raw_emotions:
                            emotion_list = [e.strip() for e in raw_emotions.split(',') if e.strip()]

                    # 5. Alternative
                    is_alternative = False
                    if len(row) > COL_IS_ALTERNATIVE:
                        alt_marker = row[COL_IS_ALTERNATIVE].strip().upper()
                        if "ALTERNATIVE" in alt_marker or "YES" in alt_marker or "TRUE" in alt_marker:
                            is_alternative = True

                    # 6. Descrizione Breve
                    short_desc = row[COL_SHORT_DESCRIPTION].strip() if len(row) > COL_SHORT_DESCRIPTION else ""

                    # Creazione Oggetto
                    intent_object = {
                        'description': description,
                        'filepath': filepath,
                        'category': category,
                        'emotion': emotion_list,
                        'short_description': short_desc,
                        'is_alternative': is_alternative,
                        'duration_seconds': duration_seconds
                    }
                    
                    parsed_data.append(intent_object)
                    rows_processed += 1

                except IndexError:
                    print(f"Errore di indice nella riga {i+1}.")
                    continue

        print(f"Lettura completata. {rows_processed} righe processate.")

        # --- SCRITTURA JSON ---
        print(f"Scrittura del file JSON in corso: {OUTPUT_JSON}")
        with open(OUTPUT_JSON, mode='w', encoding='utf-8') as outfile_json:
            json.dump(parsed_data, outfile_json, indent=2, ensure_ascii=False)
        print("File JSON creato con successo.")

    except Exception as e:
        print(f"Si è verificato un errore inaspettato: {e}")

if __name__ == "__main__":
    main()