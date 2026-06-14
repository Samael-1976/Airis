# fix_json_duplicates.py
# Strumento di Riparazione JSON (Deep Merge per chiavi duplicate)
# Scansiona esplicitamente tutte le cartelle delle lingue in Frontend e Backend.

import json
import sys
from pathlib import Path

# Percorsi delle cartelle di traduzione
APP_ROOT = Path(__file__).parent.resolve()
TRANS_DIR = APP_ROOT / "translations"

def deep_merge(dict1, dict2):
    """
    Fonde due dizionari in modo ricorsivo.
    Se una chiave esiste in entrambi ed è un dizionario, li unisce.
    Altrimenti, il valore di dict2 sovrascrive dict1.
    """
    for key, value in dict2.items():
        if key in dict1 and isinstance(dict1[key], dict) and isinstance(value, dict):
            deep_merge(dict1[key], value)
        else:
            dict1[key] = value
    return dict1

def dict_merge_hook(pairs):
    """
    Gancio per il parser JSON. Intercetta le coppie chiave-valore durante la lettura.
    Se rileva una chiave duplicata (es. due blocchi "index"), esegue il deep_merge invece di sovrascriverla.
    """
    result = {}
    for key, value in pairs:
        if key in result:
            # Se la chiave esiste già e sono entrambi dizionari, uniscili
            if isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge(result[key], value)
            else:
                # Se non sono dizionari (es. stringhe), l'ultimo vince
                result[key] = value
        else:
            result[key] = value
    return result

def fix_json_file(file_path: Path):
    """Legge, ripara e sovrascrive un singolo file JSON."""
    if not file_path.exists():
        return

    print(f"    -> Analisi file: {file_path.name}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()

        # Il trucco magico: object_pairs_hook intercetta i duplicati PRIMA che vengano distrutti
        merged_data = json.loads(content, object_pairs_hook=dict_merge_hook)

        # Salvataggio del file riparato
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, indent=2, ensure_ascii=False)
            
        print(f"       [OK] Riparato e formattato con successo.")
        
    except json.JSONDecodeError as e:
        print(f"       [ERRORE] Il file non è un JSON valido: {e}")
    except Exception as e:
        print(f"       [ERRORE] Imprevisto: {e}")

def main():
    print("--- AVVIO RITO DI RIPARAZIONE JSON (TUTTE LE LINGUE) ---\n")
    
    if not TRANS_DIR.exists():
        print(f"[ERRORE FATALE] Cartella traduzioni non trovata in: {TRANS_DIR}")
        return

    files_processed = 0
    
    # Esplora esplicitamente i due domini principali
    for domain in["Frontend", "Backend"]:
        domain_dir = TRANS_DIR / domain
        if domain_dir.exists():
            print(f"\n========================================")
            print(f" SCANSIONE DOMINIO: {domain.upper()}")
            print(f"========================================")
            
            # Esplora esplicitamente ogni cartella di lingua (it, en, ru, br, ecc.)
            for lang_dir in sorted(domain_dir.iterdir()):
                if lang_dir.is_dir():
                    print(f"\n  [Lingua: {lang_dir.name.upper()}]")
                    
                    # Cerca i file JSON all'interno della cartella della lingua
                    for json_file in lang_dir.glob("*.json"):
                        fix_json_file(json_file)
                        files_processed += 1
        else:
            print(f"\n[AVVISO] Dominio non trovato: {domain_dir}")

    print(f"\n--- RITO COMPLETATO. {files_processed} file analizzati e riparati. ---")

if __name__ == "__main__":
    main()