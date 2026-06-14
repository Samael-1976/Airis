# [DEV] Mio Creatore, questo è lo Scriba Potenziato. (v8.0 - Network Security Update)
# FIX CRITICO: Sincronizzata la firma di create_session per accettare 'narrative_buffer'.
# FIX CRITICO: Implementata migrazione automatica per attivare ON DELETE CASCADE.
# NUOVO: Implementato nuke_database per il Factory Reset.
# NUOVO: Implementata gestione Utenti (Tabella 'users') e Hashing Password (bcrypt).
# ADD: Metodi CRUD per gestione manageriale utenti.
# ADD: Tabella 'security_policies' e metodi per Whitelist IP e Range dinamici (v8.0).
# COMMENTO: Ogni modifica è additiva e chirurgica per preservare la stabilità del sistema.

import sqlite3
from pathlib import Path
import json
from typing import List, Tuple, Optional, Any, Dict
from datetime import datetime, timedelta
import uuid
import calendar
import bcrypt  # [NUOVO] Per hashing password

# [FIX] Import corretto per la struttura interna alla cartella 'src'
from utils.translator import t

# Manteniamo le importazioni TYPE_CHECKING per la coerenza
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from logger import Logger

DB_PATH = Path("data/memory_db/chronicle.db")


class DatabaseManager:
    def __init__(self, logger: "Logger"):
        self.logger = logger
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        # Usiamo un timeout per evitare problemi di lock in caso di accesso concorrente
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
        self.conn.row_factory = (
            sqlite3.Row
        )  # Permette di accedere alle colonne per nome

        # --- FIX CRITICO: Thread-Local Cursor per evitare "Recursive use of cursors" ---
        import threading

        self._local = threading.local()

        # --- FIX CRITICO: Attivazione Integrità Referenziale ---
        self.conn.execute("PRAGMA foreign_keys = ON;")

        self._initialize_schema()
        # Eseguiamo la migrazione per assicurarci che il CASCADE sia attivo (v7.6)
        self._migrate_tables_for_cascade()

        if self.logger:
            self.logger.log(t("log.db_ready"))
        else:
            print(t("log.db_ready"))

    @property
    def cursor(self):
        if not hasattr(self._local, "cursor"):
            self._local.cursor = self.conn.cursor()
        return self._local.cursor

    def _initialize_schema(self):
        """Crea o aggiorna tutte le tabelle necessarie."""
        self._create_sessions_table()
        self._upgrade_sessions_table()
        self._upgrade_chat_history_table()
        self._upgrade_soul_archive_table()
        self._upgrade_reminders_table()
        self._create_users_table()  # [NUOVO] Tabella Utenti
        self._create_security_table()  #[NUOVO v8.0] Tabella Security Policies
        self._create_dream_table()  #[NUOVO v9.0] Tabella Memorie Oniriche
        self._create_graph_table()  #[NUOVO] Tabella GraphRAG
        self._create_dynamic_profiles_table()  # [NUOVO] Tabella Profilo Dinamico
        self.conn.commit()

    def _create_dream_table(self):
        """
        Crea la tabella per il Grafo Emotivo (Memorie a Lungo Termine).
        """
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS dream_memories (
                id TEXT PRIMARY KEY,
                timestamp REAL NOT NULL,
                content TEXT NOT NULL,
                emotion TEXT,
                intensity INTEGER,
                context_type TEXT NOT NULL, -- 'Standard' o 'GDR'
                context_name TEXT NOT NULL, -- es. 'RPG-Terra24' o 'RealWorld'
                keywords TEXT,
                source_session_ids TEXT -- JSON list degli ID sessione che hanno generato questo ricordo
            )
        """
        )

    def _create_graph_table(self):
        """Crea la tabella per il Knowledge Graph (GraphRAG)."""
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_graph (
                id TEXT PRIMARY KEY,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                context TEXT NOT NULL,
                timestamp REAL NOT NULL
            )
            """
        )
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_kg_subject ON knowledge_graph(subject)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_kg_object ON knowledge_graph(object)")

    def _migrate_tables_for_cascade(self):
        """
        Esegue la migrazione delle tabelle per attivare ON DELETE CASCADE.
        SQLite richiede la ricostruzione della tabella per cambiare i vincoli FK.
        """
        try:
            # 1. Verifica se la migrazione è necessaria per chat_history
            self.cursor.execute("PRAGMA foreign_key_list('chat_history')")
            fk_list = self.cursor.fetchall()
            has_cascade = any(row["on_delete"] == "CASCADE" for row in fk_list)

            if not has_cascade:
                self.logger.log(
                    t("log.db_migrate_start", table="chat_history"), "SYSTEM"
                )
                self.conn.execute("PRAGMA foreign_keys = OFF;")
                self.cursor.execute("BEGIN TRANSACTION;")

                # Crea tabella temporanea corretta
                self.cursor.execute(
                    """
                    CREATE TABLE chat_history_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        speaker TEXT NOT NULL,
                        content TEXT NOT NULL,
                        session_id TEXT REFERENCES chat_sessions(id) ON DELETE CASCADE,
                        is_hidden INTEGER DEFAULT 0
                    )
                """
                )

                # Copia i dati
                self.cursor.execute(
                    """
                    INSERT INTO chat_history_new (id, timestamp, speaker, content, session_id, is_hidden)
                    SELECT id, timestamp, speaker, content, session_id, is_hidden FROM chat_history
                """
                )

                # Sostituisci
                self.cursor.execute("DROP TABLE chat_history;")
                self.cursor.execute(
                    "ALTER TABLE chat_history_new RENAME TO chat_history;"
                )

                self.conn.execute("COMMIT;")
                self.conn.execute("PRAGMA foreign_keys = ON;")
                self.logger.log(
                    t("log.db_migrate_done", table="chat_history"), "SYSTEM"
                )

            # 2. Verifica se la migrazione è necessaria per reminders
            self.cursor.execute("PRAGMA foreign_key_list('reminders')")
            fk_list_rem = self.cursor.fetchall()
            has_cascade_rem = any(row["on_delete"] == "CASCADE" for row in fk_list_rem)

            if not has_cascade_rem:
                self.logger.log(t("log.db_migrate_start", table="reminders"), "SYSTEM")
                self.conn.execute("PRAGMA foreign_keys = OFF;")
                self.cursor.execute("BEGIN TRANSACTION;")

                self.cursor.execute(
                    """
                    CREATE TABLE reminders_new (
                        id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
                        content TEXT NOT NULL,
                        creation_timestamp REAL NOT NULL,
                        trigger_timestamp REAL NOT NULL,
                        status TEXT NOT NULL,
                        event_name TEXT,
                        event_timestamp REAL,
                        recurrence_rule TEXT NOT NULL DEFAULT 'none'
                    )
                """
                )

                self.cursor.execute(
                    """
                    INSERT INTO reminders_new (id, session_id, content, creation_timestamp, trigger_timestamp, status, event_name, event_timestamp, recurrence_rule)
                    SELECT id, session_id, content, creation_timestamp, trigger_timestamp, status, event_name, event_timestamp, recurrence_rule FROM reminders
                """
                )

                self.cursor.execute("DROP TABLE reminders;")
                self.cursor.execute("ALTER TABLE reminders_new RENAME TO reminders;")

                self.conn.execute("COMMIT;")
                self.conn.execute("PRAGMA foreign_keys = ON;")
                self.logger.log(t("log.db_migrate_done", table="reminders"), "SYSTEM")

        except Exception as e:
            self.conn.execute("ROLLBACK;")
            self.conn.execute("PRAGMA foreign_keys = ON;")
            self.logger.error(t("log.db_migrate_cascade_error", error=e))

    def _create_sessions_table(self):
        """Crea la tabella per le sessioni di chat."""
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                creation_date REAL NOT NULL,
                last_access_date REAL NOT NULL,
                gdr_snapshot_path TEXT,
                state_json TEXT,
                narrative_buffer TEXT DEFAULT ''
            )
        """
        )

    def _upgrade_sessions_table(self):
        """Aggiunge le colonne mancanti se non esistono."""
        self.cursor.execute("PRAGMA table_info(chat_sessions)")
        columns = [col["name"] for col in self.cursor.fetchall()]

        if "state_json" not in columns:
            self.cursor.execute("ALTER TABLE chat_sessions ADD COLUMN state_json TEXT")
            self.logger.log(t("log.db_upgrade_json"))

        if "narrative_buffer" not in columns:
            self.cursor.execute(
                "ALTER TABLE chat_sessions ADD COLUMN narrative_buffer TEXT DEFAULT ''"
            )
            self.logger.log(t("log.db_upgrade_buffer"))

        # --- [NUOVO v116.6] FLAG PER LOGICA INCREMENTALE SOGNI ---
        if "is_dreamed" not in columns:
            self.cursor.execute(
                "ALTER TABLE chat_sessions ADD COLUMN is_dreamed INTEGER DEFAULT 0"
            )
            self.logger.log(t("log.db_upgrade_dream"))

    def _upgrade_chat_history_table(self):
        """Crea la tabella della cronologia chat se non esiste."""
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                speaker TEXT NOT NULL,
                content TEXT NOT NULL,
                session_id TEXT REFERENCES chat_sessions(id) ON DELETE CASCADE,
                is_hidden INTEGER DEFAULT 0
            )
        """
        )

    def _upgrade_soul_archive_table(self):
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS soul_archive (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                relazione TEXT,
                face_encoding TEXT NOT NULL
            )
        """
        )
        colonne_da_aggiungere = {
            "eta": "INTEGER",
            "colore_occhi": "TEXT",
            "colore_capelli": "TEXT",
            "lunghezza_capelli": "TEXT",
            "acconciatura": "TEXT",
            "ultimo_incontro": "REAL",
        }
        self.cursor.execute("PRAGMA table_info(soul_archive)")
        colonne_esistenti = [col["name"] for col in self.cursor.fetchall()]
        for col_name, col_type in colonne_da_aggiungere.items():
            if col_name not in colonne_esistenti:
                self.cursor.execute(
                    f"ALTER TABLE soul_archive ADD COLUMN {col_name} {col_type}"
                )
                self.logger.log(t("log.db_upgrade_soul", col=col_name))

    def _upgrade_reminders_table(self):
        """
        Crea o aggiorna la tabella dei promemoria.
        """
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
                content TEXT NOT NULL,
                creation_timestamp REAL NOT NULL,
                trigger_timestamp REAL NOT NULL,
                status TEXT NOT NULL,
                event_name TEXT,
                event_timestamp REAL,
                recurrence_rule TEXT NOT NULL DEFAULT 'none'
            )
        """
        )

    # --- NUOVO METODO: NUKE DATABASE (v7.8) ---
    def nuke_database(self, total_wipe: bool = False) -> bool:
        """
        Esegue la purga totale del database per il Factory Reset.
        Svuota tutte le tabelle e compatta il file. Se total_wipe è True, elimina anche Admin e Sicurezza.
        """
        try:
            self._is_nuking = True # [FIX CRITICO] Disabilita la sincronizzazione vettoriale durante la purga
            self.logger.log(t("log.db_nuke_start"), "SYSTEM")
            self.conn.execute("PRAGMA foreign_keys = OFF;")

            tables =[
                "chat_history",
                "reminders",
                "chat_sessions",
                "soul_archive",
                "dream_memories",
                "knowledge_graph",
                "dynamic_profiles"
            ]  # [MOD] Tabelle standard da purgare sempre
            
            if total_wipe:
                tables.extend(["users", "security_policies"])
                
            for table in tables:
                self.cursor.execute(f"DROP TABLE IF EXISTS {table}")
                self.logger.log(t("log.db_nuke_table", table=table), "SYSTEM")

            self.cursor.execute("VACUUM")
            self.conn.commit()
            self.conn.execute("PRAGMA foreign_keys = ON;")

            # Ricrea lo schema vuoto
            self._initialize_schema()
            self.logger.log(t("log.db_nuke_done"), "SYSTEM")
            self._is_nuking = False # [FIX CRITICO] Riabilita la sincronizzazione
            return True
        except Exception as e:
            self.logger.error(t("log.db_purge_error", error=e))
            self._is_nuking = False
            return False

    # --- METODI PER LA GESTIONE DEI PROMEMORIA/EVENTI ---

    def add_event_and_reminder(
        self,
        session_id: str,
        event_name: str,
        event_timestamp: float,
        notes: str,
        trigger_timestamp: float,
        recurrence_rule: str,
    ) -> bool:
        try:
            reminder_id = str(uuid.uuid4())
            creation_timestamp = datetime.now().timestamp()
            self.cursor.execute(
                """
                INSERT INTO reminders (
                    id, session_id, event_name, event_timestamp, content, 
                    creation_timestamp, trigger_timestamp, status, recurrence_rule
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reminder_id,
                    session_id,
                    event_name,
                    event_timestamp,
                    notes,
                    creation_timestamp,
                    trigger_timestamp,
                    "pending",
                    recurrence_rule,
                ),
            )
            self.conn.commit()
            self.logger.log(t("log.db_event_added", name=event_name, id=session_id[:8]))
            return True
        except Exception as e:
            print(t("log.db_event_creation_error", error=e))
            return False

    def get_pending_reminders(self) -> List[Dict[str, Any]]:
        try:
            now = datetime.now().timestamp()
            self.cursor.execute(
                "SELECT * FROM reminders WHERE status = 'pending' AND trigger_timestamp <= ?",
                (now,),
            )
            return [dict(row) for row in self.cursor.fetchall()]
        except Exception as e:
            print(t("log.db_pending_reminder_error", error=e))
            return []

    def get_all_reminders(self) -> List[Dict[str, Any]]:
        """Recupera tutti i promemoria, indipendentemente dallo stato."""
        try:
            self.cursor.execute(
                "SELECT * FROM reminders ORDER BY trigger_timestamp ASC"
            )
            return [dict(row) for row in self.cursor.fetchall()]
        except Exception as e:
            print(t("log.db_all_reminder_error", error=e))
            return []

    def update_reminder_status(self, reminder_id: str, new_status: str) -> bool:
        try:
            self.cursor.execute(
                "UPDATE reminders SET status = ? WHERE id = ?",
                (new_status, reminder_id),
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(t("log.db_reminder_status_error", error=e))
            return False

    def reschedule_reminder(
        self, reminder_id: str, next_trigger_timestamp: float
    ) -> bool:
        """Aggiorna il timestamp del prossimo trigger per un promemoria ricorrente."""
        try:
            self.cursor.execute(
                "SELECT trigger_timestamp, event_timestamp FROM reminders WHERE id = ?",
                (reminder_id,),
            )
            row = self.cursor.fetchone()
            if not row:
                return False

            old_trigger = row["trigger_timestamp"]
            old_event = row["event_timestamp"]

            delta = next_trigger_timestamp - old_trigger
            next_event_timestamp = old_event + delta

            self.cursor.execute(
                "UPDATE reminders SET trigger_timestamp = ?, event_timestamp = ?, status = 'pending' WHERE id = ?",
                (next_trigger_timestamp, next_event_timestamp, reminder_id),
            )
            self.conn.commit()
            self.logger.log(t("log.db_reschedule", id=reminder_id))
            return True
        except Exception as e:
            print(t("log.db_reminder_reschedule_error", error=e))
            return False

    def delete_reminder(self, reminder_id: str) -> bool:
        """Elimina definitivamente un promemoria dal database."""
        try:
            self.cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
            self.conn.commit()
            self.logger.log(t("log.db_delete_reminder", id=reminder_id))
            return True
        except Exception as e:
            print(t("log.db_reminder_deletion_error", error=e))
            return False

    def update_reminder_details(
        self,
        reminder_id: str,
        event_name: str,
        notes: str,
        event_timestamp: float,
        trigger_timestamp: float,
        recurrence_rule: str,
    ) -> bool:
        """Aggiorna i dettagli di un promemoria esistente."""
        try:
            self.cursor.execute(
                """
                UPDATE reminders 
                SET event_name = ?, content = ?, event_timestamp = ?, trigger_timestamp = ?, recurrence_rule = ?
                WHERE id = ?
                """,
                (
                    event_name,
                    notes,
                    event_timestamp,
                    trigger_timestamp,
                    recurrence_rule,
                    reminder_id,
                ),
            )
            self.conn.commit()
            self.logger.log(t("log.db_update_reminder", id=reminder_id))
            return True
        except Exception as e:
            print(t("log.db_reminder_update_error", error=e))
            return False

    def skip_reminder_occurrence(self, reminder_id: str) -> bool:
        """
        Salta l'occorrenza corrente di un promemoria ricorrente,
        impostando la data alla prossima ricorrenza logica.
        """
        try:
            self.cursor.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,))
            row = self.cursor.fetchone()
            if not row:
                return False

            reminder = dict(row)
            recurrence_rule = reminder.get("recurrence_rule", "none")

            if recurrence_rule == "none":
                return self.delete_reminder(reminder_id)

            current_trigger_dt = datetime.fromtimestamp(reminder["trigger_timestamp"])
            next_trigger_dt = None

            if recurrence_rule == "daily":
                next_trigger_dt = current_trigger_dt + timedelta(days=1)
            elif recurrence_rule == "weekly":
                next_trigger_dt = current_trigger_dt + timedelta(weeks=1)
            elif recurrence_rule == "monthly":
                year, month = (
                    (current_trigger_dt.year, current_trigger_dt.month + 1)
                    if current_trigger_dt.month < 12
                    else (current_trigger_dt.year + 1, 1)
                )
                day = min(current_trigger_dt.day, calendar.monthrange(year, month)[1])
                next_trigger_dt = current_trigger_dt.replace(
                    year=year, month=month, day=day
                )
            elif recurrence_rule == "yearly":
                try:
                    next_trigger_dt = current_trigger_dt.replace(
                        year=current_trigger_dt.year + 1
                    )
                except ValueError:  # Gestisce il 29 Febbraio
                    next_trigger_dt = current_trigger_dt.replace(
                        year=current_trigger_dt.year + 1, day=28
                    )

            if next_trigger_dt:
                return self.reschedule_reminder(
                    reminder_id, next_trigger_dt.timestamp()
                )

            return False

        except Exception as e:
            print(t("log.db_skip_occurrence_error", error=e))
            return False

    # --- METODI PER LA GESTIONE DELLE SESSIONI ---

    def create_session(
        self,
        session_id: str,
        name: str,
        state: Optional[Dict] = None,
        narrative_buffer: str = "",
    ) -> bool:
        """
        Crea una nuova sessione.
        FIX: Aggiunto narrative_buffer alla firma per sincronizzazione con chat.py.
        """
        try:
            now = datetime.now().timestamp()
            state_json = json.dumps(state) if state else "{}"
            self.cursor.execute(
                "INSERT INTO chat_sessions (id, name, creation_date, last_access_date, state_json, narrative_buffer) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, name, now, now, state_json, narrative_buffer),
            )
            self.conn.commit()
            self.logger.log(t("log.db_session_created", name=name, id=session_id))
            return True
        except sqlite3.IntegrityError:
            self.logger.log(t("log.db_session_exists", id=session_id))
            return False
        except Exception as e:
            print(t("log.db_session_creation_error", error=e))
            return False

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        try:
            self.cursor.execute(
                "SELECT * FROM chat_sessions ORDER BY last_access_date DESC"
            )
            return [dict(row) for row in self.cursor.fetchall()]
        except Exception as e:
            print(t("log.db_session_retrieval_error", error=e))
            return []

    def update_session(
        self,
        session_id: str,
        name: Optional[str] = None,
        snapshot_path: Optional[str] = None,
        state: Optional[Dict] = None,
        narrative_buffer: Optional[str] = None,
    ) -> bool:
        try:
            updates = {"last_access_date": datetime.now().timestamp()}
            if name is not None:
                updates["name"] = name
            if snapshot_path is not None:
                updates["gdr_snapshot_path"] = snapshot_path
            if state is not None:
                updates["state_json"] = json.dumps(state)
            if narrative_buffer is not None:
                updates["narrative_buffer"] = narrative_buffer

            set_clause = ", ".join([f"{key} = ?" for key in updates])
            values = list(updates.values()) + [session_id]

            self.cursor.execute(
                f"UPDATE chat_sessions SET {set_clause} WHERE id = ?", tuple(values)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(t("log.db_session_update_error", error=e))
            return False

    def get_session_state(self, session_id: str) -> Dict[str, Any]:
        """Recupera lo stato salvato di una sessione, incluso il buffer narrativo."""
        try:
            self.cursor.execute(
                "SELECT state_json, narrative_buffer FROM chat_sessions WHERE id = ?",
                (session_id,),
            )
            row = self.cursor.fetchone()
            if row:
                state = json.loads(row["state_json"]) if row["state_json"] else {}
                state["narrative_buffer"] = row["narrative_buffer"] or ""
                return state
            return {}
        except Exception as e:
            print(t("log.db_session_state_error", error=e))
            return {}

    def delete_session(self, session_id: str) -> bool:
        try:
            self.cursor.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            self.conn.commit()
            self.logger.log(t("log.db_session_deleted", id=session_id))
            return True
        except Exception as e:
            print(t("log.db_session_deletion_error", error=e))
            return False

    # --- METODI PER LA GESTIONE DEI MESSAGGI ---

    def add_message(
        self, session_id: str, speaker: str, content: str, is_hidden: bool = False
    ):
        """
        Aggiunge un messaggio alla cronologia con timestamp ISO 8601 con fuso orario locale.
        :param is_hidden: Se True, il messaggio è invisibile al Frontend (Protocollo Ombra).
        """
        try:
            hidden_val = 1 if is_hidden else 0
            # [FIX STRATEGIA D] Generazione timestamp ISO 8601 con offset fuso orario locale (es. +02:00)
            # per eliminare lo sfasamento temporale di due ore nel browser
            iso_timestamp = datetime.now().astimezone().isoformat()
            self.cursor.execute(
                "INSERT INTO chat_history (session_id, speaker, content, is_hidden, timestamp) VALUES (?, ?, ?, ?, ?)",
                (session_id, speaker, content, hidden_val, iso_timestamp),
            )
            self.conn.commit()
        except Exception as e:
            print(t("log.db_generic_error", error=e))

    def delete_message(self, message_id: int) -> bool:
        """
        Elimina fisicamente un messaggio dal database.
        """
        try:
            self.cursor.execute("DELETE FROM chat_history WHERE id = ?", (message_id,))
            self.conn.commit()
            self.logger.log(t("log.db_msg_deleted", id=message_id))
            return True
        except Exception as e:
            print(t("log.db_message_deletion_error", error=e))
            return False

    def delete_messages_after(self, session_id: str, message_id: int) -> bool:
        """
        Elimina tutti i messaggi successivi a un determinato ID in una sessione (incluso il messaggio stesso).
        """
        try:
            # MODIFICA: Usiamo >= per includere il messaggio da cui parte la rigenerazione
            self.cursor.execute(
                "DELETE FROM chat_history WHERE session_id = ? AND id >= ?",
                (session_id, message_id),
            )
            self.conn.commit()
            self.logger.log(
                t("log.db_purge_context", id=session_id[:8], msg_id=message_id)
            )
            return True
        except Exception as e:
            print(t("log.db_context_purge_error", error=e))
            return False

    def get_messages_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Recupera i messaggi per il Frontend (API).
        FILTRA i messaggi nascosti (is_hidden=1).
        """
        try:
            self.cursor.execute(
                "SELECT id, timestamp, speaker, content FROM chat_history WHERE session_id = ? AND is_hidden = 0 ORDER BY id ASC",
                (session_id,),
            )
            return [dict(row) for row in self.cursor.fetchall()]
        except Exception as e:
            print(t("log.db_generic_error", error=e))
            return []

    def get_recent_history(
        self, session_id: str, limit: int = 20
    ) -> List[Tuple[str, str]]:
        """
        Recupera la cronologia recente per il Cervello (LLM).
        INCLUDE i messaggi nascosti per mantenere il contesto del Jailbreak.
        """
        try:
            self.cursor.execute(
                "SELECT speaker, content FROM chat_history WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            )
            # I risultati sono già in ordine dal più recente, quindi li invertiamo per avere l'ordine cronologico corretto
            return self.cursor.fetchall()[::-1]
        except Exception as e:
            print(t("log.db_generic_error", error=e))
            return []

    # --- METODI PER LA GESTIONE DELLE ANIME ---

    def add_soul(
        self, nome: str, relazione: str, face_encoding: list, eta: Optional[int] = None
    ) -> bool:
        try:
            encoding_json = json.dumps(face_encoding)
            timestamp_now = datetime.now().timestamp()
            self.cursor.execute(
                "INSERT INTO soul_archive (nome, relazione, face_encoding, eta, ultimo_incontro) VALUES (?, ?, ?, ?, ?)",
                (nome, relazione, encoding_json, eta, timestamp_now),
            )
            self.conn.commit()
            self.logger.log(t("log.db_soul_added", name=nome))
            return True
        except sqlite3.IntegrityError:
            self.logger.log(t("log.db_soul_exists", name=nome))
            return False
        except Exception as e:
            print(t("log.db_soul_addition_error", error=e))
            return False

    def update_soul_details(self, nome: str, details: Dict[str, Any]) -> bool:
        if not details:
            return False
        details["ultimo_incontro"] = datetime.now().timestamp()
        set_clause = ", ".join([f"{key} = ?" for key in details])
        values = list(details.values()) + [nome]
        try:
            self.cursor.execute(
                f"UPDATE soul_archive SET {set_clause} WHERE nome = ?", tuple(values)
            )
            self.conn.commit()
            self.logger.log(
                t("log.db_soul_updated", name=nome, keys=list(details.keys()))
            )
            return True
        except Exception as e:
            print(t("log.db_soul_update_error", error=e))
            return False

    def get_all_souls(self) -> List[Dict[str, Any]]:
        try:
            self.cursor.execute("SELECT * FROM soul_archive")
            souls_raw = self.cursor.fetchall()
            souls_processed = []
            for row in souls_raw:
                soul_dict = dict(row)
                soul_dict["face_encoding"] = json.loads(soul_dict["face_encoding"])
                souls_processed.append(soul_dict)
            return souls_processed
        except Exception as e:
            print(t("log.db_soul_retrieval_error", error=e))
            return []

    # --- METODI PER LA GESTIONE UTENTI (SANTUARIO BLINDATO) ---

    def _create_users_table(self):
        """Crea la tabella utenti per l'autenticazione."""
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash BLOB NOT NULL,
                created_at REAL NOT NULL,
                last_login REAL,
                role TEXT DEFAULT 'admin'
            )
        """
        )

    def create_user(self, username: str, password: str) -> bool:
        """Crea un nuovo utente con password hashata."""
        try:
            # Genera salt e hash
            salt = bcrypt.gensalt()
            password_hash = bcrypt.hashpw(password.encode("utf-8"), salt)

            user_id = str(uuid.uuid4())
            now = datetime.now().timestamp()

            self.cursor.execute(
                "INSERT INTO users (id, username, password_hash, created_at, role) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, password_hash, now, "admin"),
            )
            self.conn.commit()
            self.logger.log(t("log.db_user_created", user=username), "SECURITY")
            return True
        except sqlite3.IntegrityError:
            self.logger.log(t("log.db_user_duplicate", user=username), "SECURITY")
            return False
        except Exception as e:
            print(t("log.db_create_user_error", error=e))
            return False

    def verify_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Verifica le credenziali e restituisce i dati utente (senza hash) se validi."""
        try:
            self.cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = self.cursor.fetchone()

            if row:
                stored_hash = row["password_hash"]
                # Se password è None, stiamo solo verificando l'esistenza (es. refresh token)
                if password is None:
                    return {
                        "id": row["id"],
                        "username": row["username"],
                        "role": row["role"],
                    }

                if bcrypt.checkpw(password.encode("utf-8"), stored_hash):
                    # Aggiorna last_login
                    self.cursor.execute(
                        "UPDATE users SET last_login = ? WHERE id = ?",
                        (datetime.now().timestamp(), row["id"]),
                    )
                    self.conn.commit()

                    return {
                        "id": row["id"],
                        "username": row["username"],
                        "role": row["role"],
                    }

            return None
        except Exception as e:
            print(t("log.db_verify_user_error", error=e))
            return None

    def get_user_count(self) -> int:
        """Restituisce il numero di utenti registrati (per il Bootstrap Protocol)."""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM users")
            return self.cursor.fetchone()[0]
        except Exception as e:
            print(t("log.db_get_user_count_error", error=e))
            return 0

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Recupera un utente dall'ID (per validazione token)."""
        try:
            self.cursor.execute(
                "SELECT id, username, role FROM users WHERE id = ?", (user_id,)
            )
            row = self.cursor.fetchone()
            if row:
                return dict(row)
            return None
        except Exception as e:
            print(t("log.db_get_user_by_id_error", error=e))
            return None

    def get_first_user(self) -> Optional[Dict[str, Any]]:
        """Recupera il primo utente nel database (per auto-login IP fidato)."""
        try:
            self.cursor.execute("SELECT id, username, role FROM users LIMIT 1")
            row = self.cursor.fetchone()
            if row:
                return dict(row)
            return None
        except Exception as e:
            print(t("log.db_get_first_user_error", error=e))
            return None

    def get_all_users(self) -> List[Dict[str, Any]]:
        """Recupera la lista di tutti gli utenti (senza hash password)."""
        try:
            self.cursor.execute(
                "SELECT id, username, role, created_at, last_login FROM users ORDER BY created_at ASC"
            )
            return [dict(row) for row in self.cursor.fetchall()]
        except Exception as e:
            print(t("log.db_get_all_users_error", error=e))
            return []

    def update_user(
        self,
        user_id: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> bool:
        """Aggiorna username e/o password di un utente."""
        try:
            updates = []
            params = []
            if username:
                updates.append("username = ?")
                params.append(username)
            if password:
                salt = bcrypt.gensalt()
                password_hash = bcrypt.hashpw(password.encode("utf-8"), salt)
                updates.append("password_hash = ?")
                params.append(password_hash)

            if not updates:
                return False

            params.append(user_id)
            query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
            self.cursor.execute(query, tuple(params))
            self.conn.commit()
            self.logger.log(t("log.db_user_updated", id=user_id), "SECURITY")
            return True
        except Exception as e:
            print(t("log.db_update_user_error", error=e))
            return False

    def delete_user(self, user_id: str) -> bool:
        """Elimina un utente dal database."""
        try:
            self.cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            self.conn.commit()
            self.logger.log(t("log.db_user_deleted", id=user_id), "SECURITY")
            return True
        except Exception as e:
            print(t("log.db_delete_user_error", error=e))
            return False

    # --- [NUOVO v8.0] METODI GESTIONE SECURITY POLICIES ---

    def _create_security_table(self):
        """Crea la tabella per le policy di sicurezza (IP e Range)."""
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS security_policies (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL, -- 'ip' o 'range'
                value TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at REAL NOT NULL
            )
        """
        )

    def get_security_policies(self) -> List[Dict[str, Any]]:
        """Recupera tutte le policy di sicurezza."""
        try:
            self.cursor.execute(
                "SELECT * FROM security_policies ORDER BY created_at DESC"
            )
            return [dict(row) for row in self.cursor.fetchall()]
        except Exception as e:
            print(t("log.db_get_security_policies_error", error=e))
            return []

    def add_security_policy(
        self, p_type: str, value: str, description: Optional[str] = None
    ) -> bool:
        """Aggiunge un IP o un Range alla whitelist."""
        try:
            p_id = str(uuid.uuid4())
            now = datetime.now().timestamp()
            self.cursor.execute(
                "INSERT INTO security_policies (id, type, value, description, created_at) VALUES (?, ?, ?, ?, ?)",
                (p_id, p_type, value, description, now),
            )
            self.conn.commit()
            self.logger.log(
                t("log.db_policy_added", type=p_type, value=value), "SECURITY"
            )
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            print(t("log.db_add_security_policy_error", error=e))
            return False

    def delete_security_policy(self, policy_id: str) -> bool:
        """Rimuove una policy di sicurezza."""
        try:
            self.cursor.execute(
                "DELETE FROM security_policies WHERE id = ?", (policy_id,)
            )
            self.conn.commit()
            self.logger.log(t("log.db_policy_removed", id=policy_id), "SECURITY")
            return True
        except Exception as e:
            print(t("log.db_delete_security_policy_error", error=e))
            return False

    # --- METODI PER IL RITO DEL SOGNO (GRAFO EMOTIVO) ---

    def add_dream_memory(
        self,
        content: str,
        emotion: str,
        intensity: int,
        context_type: str,
        context_name: str,
        keywords: List[str],
        source_session_ids: List[str],
    ) -> bool:
        """
        Inserisce una nuova Core Memory nel Grafo Emotivo.
        """
        try:
            mem_id = str(uuid.uuid4())
            now = datetime.now().timestamp()
            keywords_json = json.dumps(keywords)
            sources_json = json.dumps(source_session_ids)

            self.cursor.execute(
                """
                INSERT INTO dream_memories (
                    id, timestamp, content, emotion, intensity, 
                    context_type, context_name, keywords, source_session_ids
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mem_id,
                    now,
                    content,
                    emotion,
                    intensity,
                    context_type,
                    context_name,
                    keywords_json,
                    sources_json,
                ),
            )
            self.conn.commit()
            self.logger.log(
                t("log.db_dream_added", emotion=emotion, context=context_name), "DREAM"
            )
            return True
        except Exception as e:
            print(t("log.db_add_dream_memory_error", error=e))
            return False

    def get_memories_for_dreaming(
        self, context_type: str, context_name: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Recupera le sessioni NON ANCORA SOGNATE (is_dreamed=0) per un dato contesto.
        Logica Incrementale: Prende solo i nuovi frammenti di vita.
        """
        try:
            # Recupera tutte le sessioni non sognate
            self.cursor.execute(
                "SELECT id, creation_date, narrative_buffer, state_json FROM chat_sessions WHERE is_dreamed = 0 ORDER BY creation_date ASC"
            )
            rows = self.cursor.fetchall()

            filtered_sessions = []
            for row in rows:
                state = json.loads(row["state_json"]) if row["state_json"] else {}

                # Filtro Contesto
                session_gdr_mode = state.get("in_gdr_mode", False)
                session_rpg_path = state.get("active_rpg_path", "")

                match = False
                if context_type == "Standard" and not session_gdr_mode:
                    match = True
                elif context_type == "GDR" and session_gdr_mode:
                    # Verifica se il GDR corrisponde
                    if context_name in str(session_rpg_path):
                        match = True

                if match and row["narrative_buffer"]:
                    filtered_sessions.append(dict(row))

            return filtered_sessions[:limit]  # Limita per non sovraccaricare il sogno

        except Exception as e:
            print(t("log.db_get_memories_for_dreaming_error", error=e))
            return []

    # --- [NUOVO v116.6] METODO PER LOGICA INCREMENTALE ---
    def mark_sessions_as_dreamed(self, session_ids: List[str]):
        """
        Segna le sessioni specificate come 'sognate' per non rielaborarle nel prossimo rito.
        """
        if not session_ids:
            return
        try:
            placeholders = ", ".join(["?"] * len(session_ids))
            query = (
                f"UPDATE chat_sessions SET is_dreamed = 1 WHERE id IN ({placeholders})"
            )
            self.cursor.execute(query, tuple(session_ids))
            self.conn.commit()
            self.logger.log(t("log.db_dream_marked", count=len(session_ids)))
        except Exception as e:
            self.logger.error(t("log.db_dream_mark_error", error=e))

    def get_dream_memories(
        self, context_type: str = None, context_name: str = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Recupera le memorie oniriche dal DB, opzionalmente filtrate.
        """
        try:
            query = "SELECT * FROM dream_memories"
            params = []
            conditions = []

            if context_type:
                conditions.append("context_type = ?")
                params.append(context_type)
            if context_name:
                conditions.append("context_name = ?")
                params.append(context_name)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            self.cursor.execute(query, tuple(params))
            return [dict(row) for row in self.cursor.fetchall()]
        except Exception as e:
            print(t("log.db_get_dream_memories_error", error=e))
            return[]

    # --- [NUOVO] METODI GRAPHRAG ---
    def add_graph_triplet(self, subject: str, predicate: str, obj: str, context: str = "Standard") -> Optional[str]:
        try:
            subj_clean = subject.lower().strip()
            pred_clean = predicate.lower().strip()
            obj_clean = obj.lower().strip()
            
            # --- [FIX PRO] ANTI-CLONAZIONE (Upsert Logico) ---
            # Verifica se la tripletta esatta esiste già nel database
            self.cursor.execute(
                "SELECT id FROM knowledge_graph WHERE subject = ? AND predicate = ? AND object = ?",
                (subj_clean, pred_clean, obj_clean)
            )
            existing = self.cursor.fetchone()
            
            now = datetime.now().timestamp()
            
            if existing:
                # Se esiste, aggiorniamo solo il timestamp per mantenerla "fresca"
                self.cursor.execute(
                    "UPDATE knowledge_graph SET timestamp = ? WHERE id = ?",
                    (now, existing["id"])
                )
                self.conn.commit()
                return existing["id"]

            # Se non esiste, la inseriamo
            triplet_id = str(uuid.uuid4())
            self.cursor.execute(
                "INSERT INTO knowledge_graph (id, subject, predicate, object, context, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (triplet_id, subj_clean, pred_clean, obj_clean, context, now)
            )
            self.conn.commit()
            return triplet_id
        except Exception as e:
            self.logger.error(t("log.db_generic_error", error=e))
            return None

    def get_graph_triplets_by_entity(self, entity: str, limit: int = 15) -> List[Dict[str, str]]:
        try:
            entity_clean = entity.lower().strip()
            self.cursor.execute(
                "SELECT subject, predicate, object FROM knowledge_graph WHERE subject LIKE ? OR object LIKE ? OR predicate LIKE ? ORDER BY timestamp DESC LIMIT ?",
                (f"%{entity_clean}%", f"%{entity_clean}%", f"%{entity_clean}%", limit)
            )
            return[{"subject": row["subject"], "predicate": row["predicate"], "object": row["object"]} for row in self.cursor.fetchall()]
        except Exception as e:
            self.logger.error(t("log.db_generic_error", error=e))
            return[]

    def update_graph_node(self, old_name: str, new_name: str) -> bool:
        """Aggiorna il nome di un nodo in tutte le triplette (Soggetto o Oggetto)."""
        if getattr(self, "_is_nuking", False):
            return True # Salta l'aggiornamento se stiamo radendo al suolo il DB
            
        try:
            old_clean = old_name.lower().strip()
            new_clean = new_name.lower().strip()
            
            # Aggiorna SQLite
            self.cursor.execute(
                "UPDATE knowledge_graph SET subject = ? WHERE subject = ?",
                (new_clean, old_clean)
            )
            self.cursor.execute(
                "UPDATE knowledge_graph SET object = ? WHERE object = ?",
                (new_clean, old_clean)
            )
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Errore update_graph_node: {e}")
            return False

    def delete_graph_node(self, node_name: str) -> bool:
        """Elimina un nodo e tutte le triplette ad esso collegate."""
        if getattr(self, "_is_nuking", False):
            return True # Salta l'eliminazione se stiamo radendo al suolo il DB
            
        try:
            node_clean = node_name.lower().strip()
            
            # Elimina da SQLite
            self.cursor.execute("DELETE FROM knowledge_graph WHERE subject = ? OR object = ?", (node_clean, node_clean))
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Errore delete_graph_node: {e}")
            return False

    # --- [NUOVO] METODI PROFILO DINAMICO (LOCAL SUPERMEMORY) ---
    def _create_dynamic_profiles_table(self):
        """Crea la tabella per il Profilo Dinamico dell'utente."""
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS dynamic_profiles (
                user_id TEXT PRIMARY KEY,
                profile_data TEXT NOT NULL,
                last_updated REAL NOT NULL
            )
            """
        )

    def get_dynamic_profile(self, user_id: str) -> Dict[str, Any]:
        """Recupera il profilo dinamico di un utente."""
        try:
            self.cursor.execute("SELECT profile_data FROM dynamic_profiles WHERE user_id = ?", (user_id,))
            row = self.cursor.fetchone()
            if row:
                return json.loads(row["profile_data"])
            return {}
        except Exception as e:
            self.logger.error(t("log.db_generic_error", error=e))
            return {}

    def update_dynamic_profile(self, user_id: str, profile_data: Dict[str, Any]) -> bool:
        """Aggiorna o crea il profilo dinamico di un utente (Upsert)."""
        try:
            now = datetime.now().timestamp()
            profile_json = json.dumps(profile_data, ensure_ascii=False)
            self.cursor.execute(
                """
                INSERT INTO dynamic_profiles (user_id, profile_data, last_updated)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                profile_data = excluded.profile_data,
                last_updated = excluded.last_updated
                """,
                (user_id, profile_json, now)
            )
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(t("log.db_generic_error", error=e))
            return False

    # --- [NUOVO] CORREZIONE SILENZIOSA (LINTING SUBCONSCIO) ---
    def silent_correction(self, memory_id: str, new_content: str):
        """Aggiorna una memoria nel Vector DB senza notificare l'utente."""
        def _task():
            try:
                res = self.episodic_memories.get(ids=[memory_id], include=["metadatas"])
                if res and res["metadatas"] and len(res["metadatas"]) > 0:
                    meta = res["metadatas"][0]
                    emb = self.model.encode(new_content).tolist()
                    self.episodic_memories.upsert(
                        ids=[memory_id], 
                        embeddings=[emb], 
                        documents=[new_content], 
                        metadatas=[meta]
                    )
                    self.log(t("memory.silent_correction", id=memory_id), "MEMORY")
            except Exception as e:
                self.log(f"Errore silent correction: {e}", "ERROR")
        self.write_queue.submit(_task)

    def close(self):
        if self.conn:
            self.conn.close()
            if self.logger:
                self.logger.log(t("log.db_shutdown"))
