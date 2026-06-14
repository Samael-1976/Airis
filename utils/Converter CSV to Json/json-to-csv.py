import json
import csv
import os

# --- CONFIGURAZIONE ---
INPUT_JSON = 'intent.json'
OUTPUT_CSV = 'intent.csv'

def parse_json_to_csv():
    print(f"--- INIZIO CONVERSIONE: {INPUT_JSON} -> {OUTPUT_CSV} ---")

    if not os.path.exists(INPUT_JSON):
        print(f"[ERRORE] Il file '{INPUT_JSON}' non esiste.")
        return

    try:
        with open(INPUT_JSON, mode='r', encoding='utf-8') as infile:
            data = json.load(infile)
        
        print(f"[INFO] Letti {len(data)} intent dal file JSON.")

        # 'utf-8-sig' permette a Excel di aprire il file mostrando correttamente accenti e caratteri speciali
        with open(OUTPUT_CSV, mode='w', encoding='utf-8-sig', newline='') as outfile:
            writer = csv.writer(outfile, delimiter=';')

            # --- SCRITTURA INTESTAZIONE ---
            # Ordine colonne concordato:
            # 0: DESCRIPTION
            # 1: CATEGORY_FOLDER
            # 2: FILENAME
            # 3: DURATION
            # 4: EMOTION
            # 5: SHORT_DESCRIPTION
            # 6: IS_ALTERNATIVE
            headers = [
                "DESCRIPTION", 
                "CATEGORY_FOLDER", 
                "FILENAME", 
                "DURATION", 
                "EMOTION", 
                "SHORT_DESCRIPTION", 
                "IS_ALTERNATIVE"
            ]
            writer.writerow(headers)

            rows_written = 0

            for item in data:
                # 1. Recupero Dati
                description = item.get('description', '')
                filepath = item.get('filepath', '').replace('\\', '/') # Normalizza slash
                
                # 2. Estrazione Categoria e Filename dal Path Relativo
                # Il path nel JSON è tipo: "001_Foundational_States/state_idle.mp4"
                if '/' in filepath:
                    parts = filepath.split('/')
                    # Prende l'ultima parte come file, la penultima come categoria
                    filename = parts[-1]
                    category_folder = parts[-2] if len(parts) > 1 else ""
                else:
                    # Fallback se il path non ha cartelle
                    filename = filepath
                    category_folder = item.get('category', '') # Prova a prenderlo dal campo category se esiste

                # 3. Formattazione Durata (aggiunge '' per stile Excel se richiesto, o lascia numero)
                duration_val = item.get('duration_seconds', 0)
                duration_str = f"{duration_val}''" if duration_val else "0''"

                # 4. Formattazione Emozioni (Lista -> Stringa)
                emotions = item.get('emotion', [])
                if isinstance(emotions, list):
                    emotion_str = ", ".join(emotions)
                else:
                    emotion_str = str(emotions)

                # 5. Formattazione Alternative
                is_alt = item.get('is_alternative', False)
                alt_str = "**ALTERNATIVE VIDEO**" if is_alt else ""

                short_desc = item.get('short_description', '')

                # 6. Scrittura Riga
                row = [
                    description,
                    category_folder,
                    filename,
                    duration_str,
                    emotion_str,
                    short_desc,
                    alt_str
                ]
                writer.writerow(row)
                rows_written += 1

        print(f"\n--- CONVERSIONE COMPLETATA ---")
        print(f"File creato: {OUTPUT_CSV}")
        print(f"Righe scritte: {rows_written}")
        print("NOTA: Puoi aprire questo file direttamente con Excel.")

    except json.JSONDecodeError:
        print(f"[ERRORE] Il file JSON non è valido o è corrotto.")
    except Exception as e:
        print(f"[ERRORE CRITICO] {e}")

if __name__ == "__main__":
    parse_json_to_csv()