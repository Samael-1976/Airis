# src/migrate_chromadb.py
# [DEV] Script di Purga e Rinascita per ChromaDB (Spazio Coseno)
# Distrugge le vecchie collezioni L2 e le ricrea con metrica Cosine.
# Recupera automaticamente la Lore e lo storico da SQLite.

import chromadb
import sqlite3
import json
from pathlib import Path
import sys

# Aggiungi src al path per le importazioni
sys.path.insert(0, str(Path(__file__).parent))
from ingest import ingest_all_lore
from memory_manager import MemoryManager
from logger import Logger
from utils.translator import t


def migrate():
    print(t("avatar_server.log.migration_start"))

    # 1. Inizializza client ChromaDB
    client = chromadb.PersistentClient(path="./data/memory_db")

    # 2. Elimina vecchie collezioni (che usavano la metrica L2 di default)
    collections_to_reset = ["unified_knowledge", "episodic_memories", "core_memories"]
    for col_name in collections_to_reset:
        try:
            client.delete_collection(name=col_name)
            print(t("avatar_server.log.migration_col_deleted", col_name=col_name))
        except Exception as e:
            print(t("avatar_server.log.migration_col_not_found", col_name=col_name))

    # 3. Inizializza MemoryManager (che creerà le nuove collezioni con spazio Coseno)
    print(t("avatar_server.log.migration_init_vector"))
    logger = Logger(None)
    memory = MemoryManager(logger)

    # 4. Re-ingestione Lore Base
    print(t("avatar_server.log.migration_ingest_lore"))
    ingest_all_lore(memory, logger)

    # 5. Recupero Storico da SQLite
    print(t("avatar_server.log.migration_sqlite_recovery"))
    db_path = Path("./data/memory_db/chronicle.db")
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Recupera i buffer narrativi delle sessioni
            cursor.execute(
                "SELECT id, creation_date, narrative_buffer, state_json FROM chat_sessions WHERE narrative_buffer != ''"
            )
            sessions = cursor.fetchall()

            count = 0
            for row in sessions:
                session_id = row["id"]
                timestamp = row["creation_date"]
                buffer = row["narrative_buffer"]

                metadata = {
                    "session_id": session_id,
                    "timestamp": timestamp,
                    "archived": False,
                    "source": "migration",
                }

                # Inserisci in episodic_memories
                memory.add_episodic_memory(buffer, metadata=metadata)
                count += 1

            print(t("avatar_server.log.migration_narrative_recovered", count=count))

            # Recupera anche i sogni (core_memories) se esistono
            cursor.execute(
                "SELECT id, timestamp, content, emotion, context_name, keywords FROM dream_memories"
            )
            dreams = cursor.fetchall()
            dream_count = 0
            for row in dreams:
                keywords_list = json.loads(row["keywords"]) if row["keywords"] else []
                memory.index_core_memory(
                    content=row["content"],
                    emotion=row["emotion"],
                    context_name=row["context_name"],
                    keywords=keywords_list,
                )
                dream_count += 1
            print(t("avatar_server.log.migration_dreams_recovered", count=dream_count))

        except Exception as e:
            print(t("avatar_server.log.migration_sqlite_error", error=str(e)))
        finally:
            conn.close()
    else:
        print(t("avatar_server.log.migration_sqlite_skip"))

    print(t("avatar_server.log.migration_complete"))
    print(t("avatar_server.log.migration_cosine_info"))
    print(t("avatar_server.log.migration_ready"))


if __name__ == "__main__":
    migrate()
