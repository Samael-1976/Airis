# src/convert_safetensors.py
# Script interattivo per la conversione di modelli HuggingFace (Safetensors) in GGUF.
# Scarica automaticamente le dipendenze e lo script ufficiale di llama.cpp.

import os
import sys
import subprocess
import urllib.request
from pathlib import Path

# --- CONFIGURAZIONE PERCORSI ---
SCRIPT_DIR = Path(__file__).parent.resolve()
APP_ROOT = SCRIPT_DIR.parent
SAFETENSORS_DIR = APP_ROOT / "models" / "safetensors"
CONVERTER_SCRIPT = SCRIPT_DIR / "convert_hf_to_gguf.py"
CONVERTER_URL = "https://raw.githubusercontent.com/ggml-org/llama.cpp/master/convert_hf_to_gguf.py"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    clear_screen()
    print("============================================================")
    print("      FORGIA DEI MODELLI (Safetensors -> GGUF)")
    print("============================================================\n")

def check_dependencies():
    """Verifica e installa le librerie necessarie per la conversione."""
    print("[SISTEMA] Verifica dipendenze in corso...")
    try:
        import gguf
        import transformers
        import torch
        import sentencepiece
    except ImportError:
        print("[SISTEMA] Librerie mancanti. Installazione in corso (potrebbe richiedere un minuto)...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "gguf", "transformers", "torch", "sentencepiece", "safetensors"])
        print("[SISTEMA] Dipendenze installate con successo.\n")

def ensure_converter_script():
    """Scarica lo script ufficiale di llama.cpp se non esiste."""
    if not CONVERTER_SCRIPT.exists():
        print("[SISTEMA] Script 'convert_hf_to_gguf.py' non trovato. Download dal repository ufficiale...")
        try:
            urllib.request.urlretrieve(CONVERTER_URL, CONVERTER_SCRIPT)
            print("[SISTEMA] Script scaricato con successo.\n")
        except Exception as e:
            print(f"[ERRORE CRITICO] Impossibile scaricare lo script di conversione: {e}")
            sys.exit(1)

def get_model_folders() -> list:
    """Restituisce la lista delle cartelle dentro models/safetensors."""
    if not SAFETENSORS_DIR.exists():
        SAFETENSORS_DIR.mkdir(parents=True, exist_ok=True)
        return []
    return [d for d in SAFETENSORS_DIR.iterdir() if d.is_dir()]

def main():
    print_header()
    check_dependencies()
    ensure_converter_script()

    folders = get_model_folders()
    if not folders:
        print(f"[ERRORE] Nessuna cartella trovata in {SAFETENSORS_DIR}.")
        print("Scarica i file .safetensors e .json da HuggingFace, mettili in una cartella qui dentro e riprova.")
        input("\nPremi Invio per uscire...")
        return

    # 1. SCELTA DEL MODELLO
    print("Modelli Safetensors disponibili per la conversione:\n")
    for i, folder in enumerate(folders):
        print(f"  [{i + 1}] - {folder.name}")
    print(f"  [0] - Esci")

    while True:
        try:
            choice = int(input("\n> Scegli il modello da convertire: "))
            if choice == 0:
                return
            if 1 <= choice <= len(folders):
                selected_folder = folders[choice - 1]
                break
        except ValueError:
            pass
        print("Scelta non valida.")

    # 2. SCELTA DELLA PRECISIONE (OUTTYPE)
    print_header()
    print(f"Modello selezionato: {selected_folder.name}\n")
    print("Scegli la precisione di output (Quantizzazione base):")
    print("  [1] - f16  (Consigliato. Qualità massima, file grande. Potrai quantizzarlo dopo)")
    print("  [2] - q8_0 (Veloce. File più piccolo, ottima qualità per modelli < 14B)")
    print("  [3] - f32  (Sconsigliato. File enorme, solo per debug)")
    
    outtype_map = {1: "f16", 2: "q8_0", 3: "f32"}
    while True:
        try:
            type_choice = int(input("\n> Scegli la precisione [Default: 1]: ") or "1")
            if type_choice in outtype_map:
                selected_outtype = outtype_map[type_choice]
                break
        except ValueError:
            pass
        print("Scelta non valida.")

    # 3. SCELTA DELLA DESTINAZIONE
    print_header()
    print("Scegli la cartella di destinazione in Airis:")
    print("  [1] - models/gguf       (Modelli Principali / Cuore)")
    print("  [2] - models/labour     (Gatekeeper / Semantic Routing)")
    print("  [3] - models/specialist (Sussurratore / Draft Models)")
    
    dest_map = {
        1: APP_ROOT / "models" / "gguf",
        2: APP_ROOT / "models" / "labour",
        3: APP_ROOT / "models" / "specialist"
    }
    while True:
        try:
            dest_choice = int(input("\n> Scegli la destinazione [Default: 1]: ") or "1")
            if dest_choice in dest_map:
                dest_dir = dest_map[dest_choice]
                dest_dir.mkdir(parents=True, exist_ok=True)
                break
        except ValueError:
            pass
        print("Scelta non valida.")

    # 4. ESECUZIONE CONVERSIONE
    output_filename = f"{selected_folder.name}-{selected_outtype}.gguf"
    output_path = dest_dir / output_filename

    print_header()
    print(f"Inizio conversione di: {selected_folder.name}")
    print(f"Destinazione: {output_path}")
    print(f"Precisione: {selected_outtype}")
    print("\nATTENZIONE: Questo processo richiede molta RAM e può durare diversi minuti.")
    print("Non chiudere la finestra...\n")
    print("-" * 60)

    cmd = [
        sys.executable,
        str(CONVERTER_SCRIPT),
        str(selected_folder),
        "--outfile", str(output_path),
        "--outtype", selected_outtype
    ]

    try:
        # Eseguiamo il comando lasciando che l'output vada direttamente a schermo
        subprocess.run(cmd, check=True)
        print("-" * 60)
        print(f"\n[SUCCESSO] Modello convertito e salvato in:\n{output_path}")
    except subprocess.CalledProcessError as e:
        print("-" * 60)
        print(f"\n[ERRORE CRITICO] La conversione è fallita. Codice errore: {e.returncode}")
    except KeyboardInterrupt:
        print("\n[ANNULLATO] Conversione interrotta dall'utente.")

    input("\nPremi Invio per tornare al menu o chiudere...")

if __name__ == "__main__":
    main()