# src/connectors/base_connector.py
# [DEV] Classe Base per Connettori (v1.0 - DRY & Security Protocol)
# Centralizza la gestione dell'encoding, del buffer flush e della sicurezza dei percorsi.

import sys
import json
import argparse
from pathlib import Path
from typing import Callable, Dict, Any

# --- [FIX 1A] L'APOCALISSE DELL'ENCODING ---
# Forza l'encoding UTF-8 su stdout per evitare crash con emoji o caratteri speciali su Windows
if sys.stdout.encoding != 'utf-8':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

class BaseConnector:
    def __init__(self, description: str):
        self.description = description
        self.debug_buffer = []
        self.actions: Dict[str, Callable] = {}

    def register_action(self, action_name: str, func: Callable):
        """Registra una funzione associata a un'azione CLI."""
        self.actions[action_name] = func

    def log_debug(self, msg: str, prefix: str = "DEBUG"):
        """Scrive su stderr (console) e nel buffer interno."""
        sys.stderr.write(f"[{prefix}] {msg}\n")
        self.debug_buffer.append(f"[{prefix}] {msg}")

    def resolve_path(self, path_str: str, project_root: Path) -> Path:
        """
        --- [FIX 2A] PATH TRAVERSAL VULNERABILITY ---
        Risolve il percorso prevenendo l'uscita dalla directory del progetto.
        """
        clean_path = path_str.strip().strip('"').strip("'")
        path = Path(clean_path)
        
        if path.is_absolute():
            resolved = path.resolve()
        else:
            resolved = (project_root / path).resolve()
        
        # Verifica di sicurezza: il percorso risolto deve essere all'interno di project_root
        try:
            resolved.relative_to(project_root.resolve())
        except ValueError:
            raise PermissionError(f"Path Traversal bloccato. Accesso negato a: {resolved}")
            
        return resolved

    def run(self):
        """Esegue il parsing degli argomenti e lancia l'azione richiesta."""
        parser = argparse.ArgumentParser(description=self.description)
        parser.add_argument(
            "--action", 
            required=True, 
            choices=list(self.actions.keys()), 
            help="Azione da eseguire."
        )
        parser.add_argument(
            "--params", 
            type=str, 
            default="{}", 
            help="Parametri JSON per l'azione."
        )
        
        args = parser.parse_args()

        try:
            params = json.loads(args.params)
            action_func = self.actions[args.action]
            
            # Esecuzione della logica specifica del connettore
            result_data = action_func(params)
            
            output = json.dumps({"status": "success", "data": result_data})
            print(output)
            
        except Exception as e:
            debug_str = " | ".join(self.debug_buffer)
            error_output = json.dumps({"status": "error", "message": f"{str(e)} [LOG: {debug_str}]"})
            print(error_output)
            
        finally:
            # --- [FIX 2C] BUFFER FLUSH MANCANTE ---
            # Assicura che il JSON venga inviato a executor.py prima che il processo muoia
            sys.stdout.flush()