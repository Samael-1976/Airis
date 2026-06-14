# src/engine/repl_backend.py
# [DEV] Il Kernel dell'Anima (Smart Stateful REPL v2.0)
# Mantiene in memoria le variabili tra un'esecuzione e l'altra.
# Implementa AST Parsing per restituire automaticamente l'output delle espressioni.

import sys
import json
import traceback
import contextlib
import io
import ast

def main():
    # Dizionario persistente che funge da memoria RAM per le variabili Python
    global_env = {}
    
    # Forza l'encoding UTF-8 per evitare crash su Windows con caratteri speciali
    if sys.stdout.encoding != 'utf-8':
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')

    while True:
        try:
            # Legge una riga da stdin (bloccante finché l'Executor non invia dati)
            line = sys.stdin.readline()
            if not line:
                break  # EOF, il processo padre è morto o ha chiuso lo stream
                
            data = json.loads(line)
            code = data.get("code", "").strip()
            
            if not code:
                sys.stdout.write(json.dumps({"status": "success", "output": ""}) + "\n")
                sys.stdout.flush()
                continue
            
            # Cattura l'output standard e gli errori
            f = io.StringIO()
            status = "success"
            
            with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
                try:
                    # Parsing dell'Abstract Syntax Tree (AST)
                    tree = ast.parse(code)
                    
                    if not tree.body:
                        pass
                    elif isinstance(tree.body[-1], ast.Expr):
                        # L'ultima riga è un'espressione (es. `df.head()` o `2 + 2`)
                        last_expr = tree.body.pop()
                        
                        # Esegui tutto il codice precedente normalmente
                        if tree.body:
                            exec(compile(tree, filename="<ast>", mode="exec"), global_env)
                            
                        # Valuta l'ultima espressione e stampala per catturarla in stdout
                        result = eval(compile(ast.Expression(last_expr.value), filename="<ast>", mode="eval"), global_env)
                        if result is not None:
                            print(result)
                    else:
                        # Nessuna espressione finale (es. `x = 5`), esegui tutto normalmente
                        exec(code, global_env)
                        
                except Exception:
                    traceback.print_exc()
                    status = "error"
                    
            output = f.getvalue()
            
            # Invia la risposta all'Executor
            response = json.dumps({"status": status, "output": output})
            sys.stdout.write(response + "\n")
            sys.stdout.flush()
            
        except Exception as e:
            # Failsafe per evitare che il loop muoia per un JSON malformato
            err_response = json.dumps({"status": "error", "output": f"REPL Internal Error: {str(e)}"})
            sys.stdout.write(err_response + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()