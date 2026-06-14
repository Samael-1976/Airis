import csv
import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox

# --- MAPPA DELLE COLONNE (Basata su intent-empty.csv) ---
# 0: DESCRIPTION
# 1: FILEPATH
# 2: CATEGORY
# 3: EMOTIONS
# 4: SHORT DESCRIPTION
# 5: ALTERNATIVE VIDEO
# 6: DURATION
COL_DESCRIPTION = 0
COL_FILEPATH = 1
COL_CATEGORY = 2
COL_EMOTIONS = 3
COL_SHORT_DESCRIPTION = 4
COL_IS_ALTERNATIVE = 5
COL_DURATION = 6

def select_file_gui():
    """Apre una finestra di dialogo per scegliere il file CSV."""
    # Crea una finestra root nascosta (per non mostrare la finestra vuota di tk)
    root = tk.Tk()
    root.withdraw()

    file_path = filedialog.askopenfilename(
        title="Seleziona il file CSV da convertire",
        filetypes=[("File CSV", "*.csv"), ("Tutti i file", "*.*")]
    )
    
    # Distrugge la root dopo la selezione
    root.destroy()
    return file_path

def show_message(title, message, is_error=False):
    """Mostra un popup di messaggio."""
    # Ricrea una root temporanea per il messagebox se necessario
    root = tk.Tk()
    root.withdraw()
    if is_error:
        messagebox.showerror(title, message)
    else:
        messagebox.showinfo(title, message)
    root.destroy()

def parse_csv_to_json():
    # 1. Selezione File tramite GUI
    input_csv = select_file_gui()
    
    # Se l'utente preme "Annulla" o chiude la finestra
    if not input_csv:
        print("Nessun file selezionato. Uscita.")
        return

    output_json = os.path.splitext(input_csv)[0] + '.json'
    
    print(f"--- ELABORAZIONE: {input_csv} ---")

    parsed_data = []
    rows_processed = 0
    rows_skipped = 0

    try:
        # 'utf-8-sig' è fondamentale per CSV da Excel
        with open(input_csv, mode='r', encoding='utf-8-sig') as infile:
            reader = csv.reader(infile, delimiter=';')
            
            for i, row in enumerate(reader):
                # --- Controllo Intestazione ---
                if i == 0 and row and "DESCRIPTION" in row[0].upper():
                    continue

                # --- Controllo Validità Riga ---
                if not row or all(field.strip() == "" for field in row):
                    rows_skipped += 1
                    continue

                try:
                    # Riempiamo le colonne mancanti se la riga è corta
                    while len(row) <= COL_DURATION:
                        row.append("")

                    # 1. Estrazione Dati
                    description = row[COL_DESCRIPTION].strip()
                    filepath = row[COL_FILEPATH].strip()
                    category = row[COL_CATEGORY].strip()
                    short_description = row[COL_SHORT_DESCRIPTION].strip()

                    # 2. Emozioni
                    emotion_list = []
                    raw_emotions = row[COL_EMOTIONS].strip()
                    if raw_emotions:
                        emotion_list = [e.strip() for e in raw_emotions.split(',') if e.strip()]

                    # 3. Alternative (Booleano)
                    is_alternative = False
                    alt_marker = row[COL_IS_ALTERNATIVE].strip().upper()
                    # Logica: se c'è scritto qualcosa di significativo, è True
                    if alt_marker and (len(alt_marker) > 1 or "YES" in alt_marker or "TRUE" in alt_marker):
                        is_alternative = True

                    # 4. Durata (Float)
                    duration_seconds = 0.0
                    dur_str = row[COL_DURATION].strip().replace("''", "").replace(",", ".")
                    if dur_str:
                        try:
                            duration_seconds = float(dur_str)
                        except ValueError:
                            pass

                    # 5. Oggetto JSON
                    intent_object = {
                        'description': description,
                        'filepath': filepath,
                        'category': category,
                        'emotion': emotion_list,
                        'short_description': short_description,
                        'is_alternative': is_alternative,
                        'duration_seconds': duration_seconds
                    }
                    
                    parsed_data.append(intent_object)
                    rows_processed += 1

                except Exception as e:
                    print(f"Errore riga {i+1}: {e}")
                    rows_skipped += 1

        # --- SCRITTURA JSON ---
        with open(output_json, mode='w', encoding='utf-8') as outfile:
            json.dump(parsed_data, outfile, indent=2, ensure_ascii=False)

        msg = (f"Conversione completata!\n\n"
               f"File JSON creato: {os.path.basename(output_json)}\n"
               f"Righe processate: {rows_processed}\n"
               f"Righe saltate: {rows_skipped}")
        
        print(msg)
        show_message("Successo", msg)

    except Exception as e:
        err_msg = f"Errore durante la conversione:\n{str(e)}"
        print(err_msg)
        show_message("Errore Critico", err_msg, is_error=True)

if __name__ == "__main__":
    parse_csv_to_json()