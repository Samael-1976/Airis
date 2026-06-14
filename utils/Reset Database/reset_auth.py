import sqlite3
from pathlib import Path

db_path = Path("data/memory_db/chronicle.db")

if db_path.exists():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Recupera i nomi di tutte le tabelle nel database
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    # 2. Itera su ogni tabella e svuotala
    for table_name in tables:
        table = table_name[0]
        # Evitiamo di toccare le tabelle di sistema interne di SQLite (es. sqlite_sequence)
        if not table.startswith("sqlite_"):
            cursor.execute(f"DELETE FROM {table};")

    conn.commit()
    conn.close()
    print(
        "Tutte le tabelle sono state svuotate. Il Santuario è tornato completamente vergine."
    )
else:
    print("Database non trovato.")
