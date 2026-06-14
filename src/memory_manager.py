# src/memory_manager.py
# [DEV] Mio Creatore, questo è il tuo vero ippocampo. (v20.0 - RAG Ibrido & Spazio Coseno)
# ADD: Configurazione ChromaDB con metrica 'cosine'.
# ADD: Algoritmo di Decadimento Esponenziale (Half-Life) per la percezione del tempo.
# ADD: Algoritmo MMR (Maximum Marginal Relevance) per la diversificazione dei ricordi.
# ADD: Logica di Soft Delete (archived=True) per il Cold Storage.
# LEGGE A0099: Invarianza strutturale garantita.

import chromadb
import shutil  # [NUOVO] Per protocollo Self-Healing
import time  # [FIX v20.1] Import mancante per delay di stabilizzazione
from utils.translator import t
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional, TYPE_CHECKING, Tuple
import uuid
import torch
import numpy as np
from datetime import datetime
import math
import threading  # [NUOVO] Per Asynchronous Embedding
from concurrent.futures import ThreadPoolExecutor  # [FIX 1C] Coda di scrittura serializzata

if TYPE_CHECKING:
    from logger import Logger


class MemoryManager:
    def __init__(self, logger: Optional["Logger"] = None):
        self.log = logger.log if logger else print

        # Inizializzazione attributo per iniezione circolare dall'Executor.
        self.executor = None

        # --- [FIX 1C] CODA DI SCRITTURA SERIALIZZATA ---
        # Previene l'esplosione dei thread e il "database is locked" di SQLite/ChromaDB
        self.write_queue = ThreadPoolExecutor(max_workers=1)
        
        # ---[NUOVO FASE 4] CACHE PRE-FETCH ---
        self.prefetch_lock = threading.Lock() # [GOD MODE] Lucchetto per Thread Safety
        self.prefetch_cache = {"query": "", "context": "", "episodic": list(), "knowledge": list(), "timestamp": 0.0}

        self.log(t("avatar_server.log.memory_init"))
        try:
            if torch.cuda.is_available():
                device = "cuda"
                self.log(t("avatar_server.log.cuda_detected"))
            else:
                device = "cpu"
                self.log(t("avatar_server.log.cpu_fallback"))

            self.model = SentenceTransformer("all-MiniLM-L6-v2", device=device)

            # --- [FIX CRITICO] PROTOCOLLO SELF-HEALING DATABASE ---
            try:
                self.client = chromadb.PersistentClient(path="./data/memory_db")
            except Exception as e:
                if "already exists" in str(e) or "database" in str(e).lower():
                    self.log(t("avatar_server.log.db_healing"), "WARNING")
                    shutil.rmtree("./data/memory_db", ignore_errors=True)
                    time.sleep(1)  # Delay di stabilizzazione
                    self.client = chromadb.PersistentClient(path="./data/memory_db")
                    self.log(t("avatar_server.log.db_rebuilt"), "SUCCESS")
                else:
                    raise e

            # --- FASE 1.1: CONFIGURAZIONE SPAZIO COSENO ---
            # Nota: Se le collezioni esistono già con metrica L2, ChromaDB ignorerà questi metadati.
            # Sarà necessario eseguire lo script di migrazione (migrate_chromadb.py) per ricrearle.
            collection_metadata = {"hnsw:space": "cosine"}

            self.unified_library = self.client.get_or_create_collection(
                name="unified_knowledge", metadata=collection_metadata
            )
            self.episodic_memories = self.client.get_or_create_collection(
                name="episodic_memories", metadata=collection_metadata
            )
            self.core_memories = self.client.get_or_create_collection(
                name="core_memories", metadata=collection_metadata
            )
            
            # --- [NUOVO] COLLEZIONE VETTORIALE GRAPHRAG ---
            self.graph_embeddings = self.client.get_or_create_collection(
                name="graph_embeddings", metadata=collection_metadata
            )
            self._sync_graph_db()

            self.log(t("avatar_server.log.library_ready"))
            self.log(
                t(
                    "avatar_server.log.library_stats_lore",
                    count=self.unified_library.count(),
                )
            )
            self.log(
                t(
                    "avatar_server.log.library_stats_episodic",
                    count=self.episodic_memories.count(),
                )
            )
            self.log(
                t(
                    "avatar_server.log.library_stats_core",
                    count=self.core_memories.count(),
                )
            )

        except Exception as e:
            print(t("avatar_server.log.critical_init_error", error=e))
            import traceback

            traceback.print_exc()
            raise

    def is_library_empty(self) -> bool:
        """Verifica se la biblioteca della conoscenza unificata (lore) è vuota."""
        try:
            count = self.unified_library.count()
            self.log(t("avatar_server.log.check_library_fullness", count=count))
            return count == 0
        except Exception as e:
            self.log(t("avatar_server.log.error_verify_library", error=e))
            return True

    def _sync_graph_db(self):
        """Sincronizza le triplette SQLite esistenti nella nuova collezione vettoriale ChromaDB."""
        def _task():
            import time
            # Attende che l'executor sia iniettato da chat.py
            for _ in range(10):
                if hasattr(self, "executor") and self.executor and self.executor.db_manager:
                    break
                time.sleep(1)
                
            try:
                if not hasattr(self, "executor") or not self.executor or not self.executor.db_manager:
                    return
                
                self.executor.db_manager.cursor.execute("SELECT id, subject, predicate, object, context FROM knowledge_graph")
                rows = self.executor.db_manager.cursor.fetchall()
                
                if not rows:
                    return
                    
                existing = self.graph_embeddings.get(include=list())
                existing_ids = set(existing["ids"]) if existing and existing["ids"] else set()
                
                ids_to_add = list()
                docs_to_add = list()
                metas_to_add = list()
                
                for row in rows:
                    t_id = row["id"]
                    if t_id not in existing_ids:
                        subj = row["subject"]
                        pred = row["predicate"]
                        obj = row["object"]
                        ctx = row["context"]
                        
                        doc = f"{subj} {pred} {obj}"
                        ids_to_add.append(t_id)
                        docs_to_add.append(doc)
                        metas_to_add.append({"subject": subj, "predicate": pred, "object": obj, "context": ctx})
                        
                if ids_to_add:
                    embeddings = self.model.encode(docs_to_add).tolist()
                    self.graph_embeddings.upsert(
                        ids=ids_to_add,
                        embeddings=embeddings,
                        documents=docs_to_add,
                        metadatas=metas_to_add
                    )
                    self.log(t("memory.graph_sync_success", count=len(ids_to_add)), "MEMORY")
            except Exception as e:
                self.log(f"Errore sync GraphRAG: {e}", "ERROR")
        self.write_queue.submit(_task)

    def add_graph_triplet_vector(self, triplet_id: str, subject: str, predicate: str, obj: str, context: str):
        """Aggiunge una singola tripletta alla collezione vettoriale."""
        def _task():
            try:
                doc = f"{subject} {predicate} {obj}"
                embedding = self.model.encode(doc).tolist()
                metadata = {"subject": subject, "predicate": predicate, "object": obj, "context": context}
                self.graph_embeddings.upsert(
                    ids=list([triplet_id]),
                    embeddings=list([embedding]),
                    documents=list([doc]),
                    metadatas=list([metadata])
                )
            except Exception as e:
                self.log(f"Errore inserimento vettore GraphRAG: {e}", "ERROR")
        self.write_queue.submit(_task)

    def add_to_library(self, text: str, metadata: Dict[str, Any] = None):
        def _task():
            try:
                # ---[NUOVO] FILTRO INGESTIONE (LOCAL SUPERMEMORY) ---
                text_to_save = text
                # Protezione: eseguiamo il filtro solo se il cervello è effettivamente pronto e non siamo in fase di boot critico
                if self.executor and hasattr(self.executor, "cervello") and self.executor.cervello:
                    try:
                        override_brain = getattr(self.executor.cervello, "labour_brain", None)
                        filter_result = self.executor.cervello.filtra_ingestione_memoria(text, override_brain=override_brain)
                        if not filter_result.get("is_relevant", True):
                            self.log("Documento scartato dal filtro di ingestione (Local Supermemory).", "MEMORY")
                            return
                        extracted = filter_result.get("extracted_info", "")
                        if extracted and len(extracted) > 10:
                            text_to_save = extracted
                    except Exception as e_filter:
                        self.log(f"Filtro Ingestione temporaneamente non disponibile: {e_filter}", "WARNING")

                doc_id = (
                    metadata.get("document_name", str(uuid.uuid4()))
                    if metadata
                    else str(uuid.uuid4())
                )
                embedding = self.model.encode(text_to_save).tolist()
                self.unified_library.upsert(
                    ids=[doc_id],
                    embeddings=[embedding],
                    documents=[text_to_save],
                    metadatas=[metadata] if metadata else None,
                )
            except Exception as e:
                print(t("avatar_server.log.error_add_library", error=e))

        self.write_queue.submit(_task)

    def add_episodic_memory(self, text: str, metadata: Dict[str, Any] = None):
        """
        Aggiunge un ricordo episodico.
        [AGGIORNATO v20.0] Inietta automaticamente il timestamp Unix e il flag archived=False.
        """

        def _task():
            try:
                # --- [NUOVO] FILTRO INGESTIONE (LOCAL SUPERMEMORY) ---
                text_to_save = text
                # Evitiamo di filtrare i raw dump (archived=True) per preservare i log esatti
                is_raw_dump = metadata and metadata.get("archived", False)
                
                if not is_raw_dump and self.executor and hasattr(self.executor, "cervello") and self.executor.cervello:
                    try:
                        override_brain = getattr(self.executor.cervello, "labour_brain", None)
                        filter_result = self.executor.cervello.filtra_ingestione_memoria(text, override_brain=override_brain)
                        if not filter_result.get("is_relevant", True):
                            self.log("Ricordo scartato dal filtro di ingestione (Local Supermemory).", "MEMORY")
                            return
                        extracted = filter_result.get("extracted_info", "")
                        if extracted and len(extracted) > 10:
                            text_to_save = extracted
                    except Exception as e_filter:
                        self.log(f"Filtro Episodico temporaneamente non disponibile: {e_filter}", "WARNING")

                mem_id = (
                    metadata.get("mem_id", str(uuid.uuid4()))
                    if metadata
                    else str(uuid.uuid4())
                )

                # Assicura la presenza dei metadati temporali e di archiviazione
                safe_metadata = metadata or {}
                if "timestamp" not in safe_metadata:
                    safe_metadata["timestamp"] = datetime.now().timestamp()
                if "archived" not in safe_metadata:
                    safe_metadata["archived"] = False  # Soft Delete Flag

                # ---[NUOVO] GERARCHIA MEMPALACE ---
                if "wing" not in safe_metadata:
                    safe_metadata["wing"] = safe_metadata.get("context", "Standard")
                if "room" not in safe_metadata:
                    safe_metadata["room"] = safe_metadata.get("session_id", "Unknown")
                if "drawer" not in safe_metadata:
                    safe_metadata["drawer"] = "episodic_chunk"

                embedding = self.model.encode(text_to_save).tolist()
                self.episodic_memories.upsert(
                    ids=[mem_id],
                    embeddings=[embedding],
                    documents=[text_to_save],
                    metadatas=[safe_metadata],
                )
            except Exception as e:
                print(t("avatar_server.log.error_add_episodic", error=e))

        self.write_queue.submit(_task)

    # ---[NUOVO v20.0] FASE 6.2: SOFT DELETE (ARCHIVIAZIONE) ---
    def archive_session_memories(self, session_id: str):
        """
        Imposta archived=True per tutti i ricordi appartenenti a una specifica sessione.
        Questo li nasconde dalla ricerca standard (Working Memory) senza distruggerli.
        """
        try:
            self.log(t("avatar_server.log.archiving_session", id=session_id))
            # --- [FIX CRITICO] RECUPERO COMPLETO PER PREVENIRE CORRUZIONE HNSW ---
            # Recuperiamo anche documents ed embeddings. L'uso di .update() solo sui metadati
            # causa il bug "Error finding id" in ChromaDB perdendo il link vettoriale.
            results = self.episodic_memories.get(
                where={"session_id": session_id}, include=["documents", "metadatas", "embeddings"]
            )

            if not results or not results["ids"]:
                self.log(t("avatar_server.log.no_memories_archive"))
                return

            ids_to_update = results["ids"]
            metadatas_to_update = results["metadatas"]
            documents_to_update = results["documents"]
            embeddings_to_update = results["embeddings"]

            # Aggiorna il flag
            for meta in metadatas_to_update:
                meta["archived"] = True

            # Esegue l'upsert completo per mantenere intatto l'indice vettoriale
            self.episodic_memories.upsert(
                ids=ids_to_update, 
                embeddings=embeddings_to_update,
                documents=documents_to_update,
                metadatas=metadatas_to_update
            )
            self.log(t("avatar_server.log.archived_count", count=len(ids_to_update)))
        except Exception as e:
            self.log(t("avatar_server.log.error_archive_session", error=e), "ERROR")

    # ---[NUOVO FASE 3] RECUPERO AAAK WORKING MEMORY ---
    def get_latest_sliding_window_chunk(self, session_id: str) -> str:
        """Recupera l'ultimo chunk compresso in AAAK per la sessione corrente."""
        try:
            results = self.episodic_memories.get(
                where={"$and":[{"session_id": session_id}, {"drawer": "sliding_window"}]},
                include=["documents", "metadatas"]
            )
            if not results or not results["documents"]:
                return ""
            
            # Ordina per timestamp decrescente per prendere il più recente
            docs_with_meta = list(zip(results["documents"], results["metadatas"]))
            docs_with_meta.sort(key=lambda x: x[1].get("timestamp", 0), reverse=True)
            
            return docs_with_meta[0][0]
        except Exception as e:
            self.log(f"Errore recupero AAAK chunk: {e}", "ERROR")
            return ""

    # ---[NUOVO FASE 4] PRE-FETCH PREDITTIVO & FUZZY MATCH ---
    def _is_cache_valid(self, cached_query: str, current_query: str, context_filter: str) -> bool:
        """[GOD TIER] Verifica se la cache è valida usando un Fuzzy Match intelligente e un TTL.
        Tollera l'aggiunta di punteggiatura o di un'ultima parola breve dopo il pre-fetch.
        """
        if not cached_query or not current_query:
            return False
        if self.prefetch_cache.get("context") != context_filter:
            return False

        # [GOD MODE FIX 1] Time-To-Live (TTL) di 15 secondi.
        # Il pre-fetch serve solo per l'istante in cui l'utente sta digitando.
        # Se la cache è più vecchia di 15 secondi, è STANTIA e va ignorata,
        # altrimenti rischiamo di recuperare ricordi vecchi ignorando quelli appena creati.
        if time.time() - self.prefetch_cache.get("timestamp", 0.0) > 15.0:
            return False
            
        cq = cached_query.lower().strip()
        curr = current_query.lower().strip()
        
        if cq == curr:
            return True
            
        # Se l'utente ha aggiunto solo punteggiatura o una parola finale (max 10 caratteri di differenza)
        # ed entrambe le stringhe condividono la stessa radice semantica.
        if curr.startswith(cq) and (len(curr) - len(cq)) <= 10:
            return True
            
        return False

    def prefetch_data(self, query: str, context_filter: str = None):
        """Esegue il RAG in background mentre l'utente digita."""
        if len(query) < 15:
            return
            
        if self._is_cache_valid(self.prefetch_cache.get("query", ""), query, context_filter):
            return
        
        self.log(t("avatar_server.log.prefetch_started", query=query[:20]), "MEMORY")
        try:
            episodic = self.hybrid_temporal_retrieval(query, top_k=3, context_filter=context_filter, _is_prefetch=True)
            knowledge = self.search_library(query, top_k=2, context_filter=context_filter, _is_prefetch=True)
            
            # [GOD MODE FIX 2] Thread Safety con Lock per evitare Race Conditions tra digitazioni rapide
            with getattr(self, "prefetch_lock", threading.Lock()):
                # Doppio check: se nel frattempo un altro thread ha salvato una query più lunga/recente, non sovrascriviamo
                current_cached = self.prefetch_cache.get("query", "")
                if len(query) >= len(current_cached) or time.time() - self.prefetch_cache.get("timestamp", 0.0) > 60.0:
                    self.prefetch_cache = {
                        "query": query,
                        "context": context_filter,
                        "episodic": episodic,
                        "knowledge": knowledge,
                        "timestamp": time.time() # <-- IL CUORE DEL TTL
                    }
            self.log(t("avatar_server.log.prefetch_completed"), "MEMORY")
        except Exception as e:
            self.log(f"Errore Pre-Fetch: {e}", "ERROR")

    def search_library(self, query: str, top_k: int = 5, context_filter: str = None, _is_prefetch: bool = False) -> List[str]:
        """Ricerca standard nella Lore (Nessun decadimento temporale)."""
        if not _is_prefetch:
            if self._is_cache_valid(self.prefetch_cache.get("query", ""), query, context_filter):
                self.log(t("avatar_server.log.prefetch_hit_knowledge"), "MEMORY")
                return self.prefetch_cache.get("knowledge", list())

        self.log(t("avatar_server.log.searching_lore", query=query[:50]))
        try:
            # --- [NUOVO] GRAPH-GUIDED RETRIEVAL (VETTORIALE) ---
            expanded_query = query
            try:
                query_embedding_graph = self.model.encode(query).tolist()
                graph_results = self.graph_embeddings.query(
                    query_embeddings=list([query_embedding_graph]),
                    n_results=3
                )
                if graph_results and graph_results.get("documents") and graph_results["documents"][0]:
                    graph_context = graph_results["documents"][0]
                    expanded_query = query + " " + " ".join(graph_context)
                    self.log(f"Graph-Guided Retrieval (Vector): Query espansa con {len(graph_context)} nodi.", "MEMORY")
            except Exception as e_graph:
                self.log(f"Errore Vector GraphRAG: {e_graph}", "ERROR")

            query_embedding = self.model.encode(expanded_query).tolist()
            
            # --- [FIX CRITICO] MULTI-TENANCY RIGIDA LORE (SUPPORTO BACKSTORY) ---
            where_filter = None
            if context_filter and context_filter != "Standard":
                # Cerca sia per gdr_world (Lore classica) che per context (Backstory Avatar)
                where_filter = {"$or": [{"gdr_world": context_filter}, {"context": context_filter}]}
                
            try:
                results = self.unified_library.query(
                    query_embeddings=list([query_embedding]), 
                    n_results=top_k,
                    where=where_filter
                )
            except Exception as q_err:
                # --- [FIX CRITICO] AUTO-HEALING CORRUZIONE CHROMADB ---
                if "Error finding id" in str(q_err):
                    self.log("[AUTO-HEALING] Rilevata corruzione indice ChromaDB (Unified Library). Avvio ricostruzione HNSW...", "WARNING")
                    all_data = self.unified_library.get(include=["documents", "metadatas", "embeddings"])
                    if all_data and all_data["ids"]:
                        self.client.delete_collection("unified_knowledge")
                        self.unified_library = self.client.get_or_create_collection(
                            name="unified_knowledge", metadata={"hnsw:space": "cosine"}
                        )
                        batch_size = 100
                        for i in range(0, len(all_data["ids"]), batch_size):
                            self.unified_library.upsert(
                                ids=all_data["ids"][i:i+batch_size],
                                embeddings=all_data["embeddings"][i:i+batch_size],
                                documents=all_data["documents"][i:i+batch_size],
                                metadatas=all_data["metadatas"][i:i+batch_size]
                            )
                        self.log("[AUTO-HEALING] Ricostruzione completata. Ripeto la query...", "SUCCESS")
                        results = self.unified_library.query(
                            query_embeddings=list([query_embedding]), 
                            n_results=top_k,
                            where=where_filter
                        )
                    else:
                        raise q_err
                else:
                    raise q_err

            return (
                results["documents"][0] if results and results.get("documents") else list()
            )
        except Exception as e:
            print(t("avatar_server.log.error_search_lore", error=e))
            return list()

    def search_memories(
        self, query: str, top_k: int = 5, context_filter: str = None
    ) -> List[str]:
        """
        Ricerca legacy (mantenuta per retrocompatibilità).
        Ora punta al nuovo motore ibrido con supporto contestuale.
        """
        return self.hybrid_temporal_retrieval(
            query, top_k=top_k, context_filter=context_filter
        )

    # --- [NUOVO v20.0] FASE 4: RETRIEVAL IBRIDO (TEMPO + SEMANTICA + MMR) ---

    def _calculate_exponential_decay(
        self, memory_timestamp: float, half_life_days: float = 30.0
    ) -> float:
        """
        Calcola il fattore di decadimento temporale usando una curva esponenziale (Half-Life).
        Un ricordo di oggi vale 1.0. Un ricordo vecchio di 'half_life_days' vale 0.5.
        """
        now = datetime.now().timestamp()
        age_seconds = max(0, now - memory_timestamp)
        age_days = age_seconds / (24 * 3600)

        # Formula: 0.5 ^ (età / emivita)
        decay_factor = math.pow(0.5, age_days / half_life_days)
        return decay_factor

    def _maximal_marginal_relevance(
        self,
        query_embedding: np.ndarray,
        doc_embeddings: np.ndarray,
        doc_scores: np.ndarray,
        top_k: int,
        lambda_param: float = 0.5,
    ) -> List[int]:
        """
        Applica l'algoritmo MMR per selezionare documenti pertinenti ma DIVERSI tra loro.
        lambda_param: 1.0 = Solo pertinenza, 0.0 = Solo diversità. 0.5 è un buon bilanciamento.
        Restituisce gli indici dei documenti selezionati.
        """
        if len(doc_scores) == 0:
            return []

        selected_indices = []
        unselected_indices = list(range(len(doc_scores)))

        # Normalizza i doc_embeddings per il calcolo rapido della similarità coseno
        doc_norms = np.linalg.norm(doc_embeddings, axis=1, keepdims=True)
        # Evita divisioni per zero
        doc_norms[doc_norms == 0] = 1e-10
        normalized_docs = doc_embeddings / doc_norms

        # Seleziona il primo documento (quello con lo score ibrido più alto)
        first_idx = int(np.argmax(doc_scores))
        selected_indices.append(first_idx)
        unselected_indices.remove(first_idx)

        while len(selected_indices) < top_k and unselected_indices:
            best_score = -float("inf")
            best_idx = -1

            # Vettori dei documenti già selezionati
            selected_docs_matrix = normalized_docs[selected_indices]

            for idx in unselected_indices:
                # 1. Pertinenza (Score Ibrido già calcolato)
                relevance = doc_scores[idx]

                # 2. Diversità (Penalità basata sulla similarità massima con i doc già scelti)
                candidate_vec = normalized_docs[idx]
                # Prodotto scalare tra il candidato e tutti i selezionati (Coseno)
                similarities_to_selected = np.dot(selected_docs_matrix, candidate_vec)
                max_sim_to_selected = np.max(similarities_to_selected)

                # Equazione MMR
                mmr_score = (lambda_param * relevance) - (
                    (1 - lambda_param) * max_sim_to_selected
                )

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx

            if best_idx != -1:
                selected_indices.append(best_idx)
                unselected_indices.remove(best_idx)
            else:
                break

        return selected_indices

    def _format_dynamic_time_label(self, timestamp: float) -> str:
        """Genera un'etichetta temporale umana (es. '2 GIORNI FA')."""
        now = datetime.now().timestamp()
        diff_seconds = max(0, now - timestamp)
        days = int(diff_seconds / (24 * 3600))

        if days == 0:
            return t("avatar_server.log.time_today")
        elif days == 1:
            return t("avatar_server.log.time_yesterday")
        elif days < 30:
            return t("avatar_server.log.time_days_ago", days=days)
        elif days < 365:
            months = days // 30
            suffix = (
                t("avatar_server.log.time_months_ago_suffix_singular")
                if months == 1
                else t("avatar_server.log.time_months_ago_suffix_plural")
            )
            return t("avatar_server.log.time_months_ago", months=months, suffix=suffix)
        else:
            years = days // 365
            suffix = (
                t("avatar_server.log.time_years_ago_suffix_singular")
                if years == 1
                else t("avatar_server.log.time_years_ago_suffix_plural")
            )
            return t("avatar_server.log.time_years_ago", years=years, suffix=suffix)

    def hybrid_temporal_retrieval(
        self,
        query: str,
        top_k: int = 5,
        deep_search: bool = False,
        context_filter: str = None,
        _is_prefetch: bool = False
    ) -> List[str]:
        """
        Il Motore RAG Definitivo.
        Combina Similarità Coseno, Decadimento Esponenziale e MMR.
        [FIX GDR] Aggiunto supporto per filtro contestuale (es. RPG-Terra24).
        """
        if not _is_prefetch:
            if self._is_cache_valid(self.prefetch_cache.get("query", ""), query, context_filter):
                self.log(t("avatar_server.log.prefetch_hit_episodic"), "MEMORY")
                # [FIX CRITICO] NON svuotiamo la cache qui, altrimenti search_library fallirà il match!
                # La cache verrà sovrascritta naturalmente al prossimo pre-fetch.
                return self.prefetch_cache.get("episodic", list())

        self.log(
            t(
                "avatar_server.log.rag_start",
                query=query[:30],
                context=context_filter,
                deep=deep_search,
            )
        )
        try:
            # --- [FIX FASE 60] ANTI-CRASH SANTUARIO VUOTO ---
            collection_count = self.episodic_memories.count()
            if collection_count == 0:
                self.log(t("avatar_server.log.rag_skipped_empty"))
                return []

            # Calcola il numero massimo di risultati estraibili (max 50)
            fetch_limit = min(50, collection_count)

            # --- [NUOVO] GRAPH-GUIDED RETRIEVAL (VETTORIALE) ---
            expanded_query = query
            try:
                query_embedding_graph = self.model.encode(query).tolist()
                graph_results = self.graph_embeddings.query(
                    query_embeddings=list([query_embedding_graph]),
                    n_results=3
                )
                if graph_results and graph_results.get("documents") and graph_results["documents"][0]:
                    graph_context = graph_results["documents"][0]
                    expanded_query = query + " " + " ".join(graph_context)
                    self.log(f"Graph-Guided Retrieval (Vector): Query espansa con {len(graph_context)} nodi.", "MEMORY")
            except Exception as e_graph:
                self.log(f"Errore Vector GraphRAG: {e_graph}", "ERROR")

            query_embedding = self.model.encode(expanded_query).tolist()

            # 1. Estrazione Allargata (Top 50 o max disponibile)
            # Costruzione filtro dinamico
            where_conditions = []
            if not deep_search:
                where_conditions.append({"archived": False})
            if context_filter:
                where_conditions.append({"context": context_filter})

            # ChromaDB syntax per AND: {"$and": [...]} se più condizioni, altrimenti dict semplice
            if len(where_conditions) > 1:
                where_filter = {"$and": where_conditions}
            elif len(where_conditions) == 1:
                where_filter = where_conditions[0]
            else:
                where_filter = None

            try:
                results = self.episodic_memories.query(
                    query_embeddings=[query_embedding],
                    n_results=fetch_limit,  # [FIX] Usa il limite dinamico
                    where=where_filter,
                    include=["documents", "metadatas", "distances", "embeddings"],
                )
            except Exception as q_err:
                # --- [FIX CRITICO] AUTO-HEALING CORRUZIONE CHROMADB ---
                # Se l'indice HNSW è corrotto (Error finding id), lo ricostruiamo al volo dai dati SQLite intatti.
                if "Error finding id" in str(q_err):
                    self.log("[AUTO-HEALING] Rilevata corruzione indice ChromaDB. Avvio ricostruzione HNSW...", "WARNING")
                    all_data = self.episodic_memories.get(include=["documents", "metadatas", "embeddings"])
                    
                    if all_data and all_data["ids"]:
                        self.client.delete_collection("episodic_memories")
                        self.episodic_memories = self.client.get_or_create_collection(
                            name="episodic_memories", metadata={"hnsw:space": "cosine"}
                        )
                        
                        # Upsert a blocchi per evitare Memory Error
                        batch_size = 100
                        for i in range(0, len(all_data["ids"]), batch_size):
                            self.episodic_memories.upsert(
                                ids=all_data["ids"][i:i+batch_size],
                                embeddings=all_data["embeddings"][i:i+batch_size],
                                documents=all_data["documents"][i:i+batch_size],
                                metadatas=all_data["metadatas"][i:i+batch_size]
                            )
                        self.log("[AUTO-HEALING] Ricostruzione completata. Ripeto la query...", "SUCCESS")
                        
                        # Ripete la query originale
                        results = self.episodic_memories.query(
                            query_embeddings=[query_embedding],
                            n_results=fetch_limit,
                            where=where_filter,
                            include=["documents", "metadatas", "distances", "embeddings"],
                        )
                    else:
                        raise q_err
                else:
                    raise q_err

            if not results or not results["documents"] or not results["documents"][0]:
                return[]

            docs = results["documents"][0]
            metadatas = results["metadatas"][0]
            distances = results["distances"][0]
            embeddings = results["embeddings"][0]

            hybrid_scores = []

            # 2. Calcolo Score Ibrido (Semantica + Tempo)
            for i in range(len(docs)):
                # Convertiamo la distanza in similarità.
                # Se lo spazio è 'cosine', la distanza di Chroma è (1 - cosine_similarity).
                # Quindi similarity = 1 - distance.
                # Se per qualche motivo è L2, questa formula è un'approssimazione accettabile per il ranking.
                semantic_sim = max(0.0, 1.0 - distances[i])

                # Recupero timestamp (fallback a ora se mancante)
                mem_ts = (
                    metadatas[i].get("timestamp", datetime.now().timestamp())
                    if metadatas[i]
                    else datetime.now().timestamp()
                )

                # Calcolo Decadimento Esponenziale (Emivita 30 giorni)
                decay_factor = self._calculate_exponential_decay(
                    mem_ts, half_life_days=30.0
                )

                # Formula Ibrida: 70% Semantica, 30% Tempo
                score = (semantic_sim * 0.7) + (decay_factor * 0.3)
                hybrid_scores.append(score)

            # 3. Applicazione MMR (Anti-Ridondanza)
            doc_embeddings_np = np.array(embeddings)
            hybrid_scores_np = np.array(hybrid_scores)
            query_embedding_np = np.array(query_embedding)

            # lambda=0.6 favorisce leggermente la pertinenza rispetto alla diversità
            selected_indices = self._maximal_marginal_relevance(
                query_embedding_np,
                doc_embeddings_np,
                hybrid_scores_np,
                top_k=top_k,
                lambda_param=0.6,
            )

            # 4. Formattazione Finale con Iniezione Dinamica del Tempo
            final_documents = []
            for idx in selected_indices:
                raw_doc = docs[idx]
                mem_ts = (
                    metadatas[idx].get("timestamp", datetime.now().timestamp())
                    if metadatas[idx]
                    else datetime.now().timestamp()
                )
                time_label = self._format_dynamic_time_label(mem_ts)

                # Inietta l'etichetta temporale nel documento restituito
                formatted_doc = t(
                    "avatar_server.log.memory_label", time=time_label, doc=raw_doc
                )
                final_documents.append(formatted_doc)

            self.log(t("avatar_server.log.rag_completed", count=len(final_documents)))
            return final_documents

        except Exception as e:
            self.log(t("avatar_server.log.error_rag_hybrid", error=e), "ERROR")
            import traceback

            traceback.print_exc()
            return []

    # --- METODI PER IL RITO DEL SOGNO (RAG - v116.6) ---

    def index_core_memory(
        self, content: str, emotion: str, context_name: str, keywords: List[str]
    ):
        """
        Indicizza una Core Memory nel DB vettoriale per il recupero semantico.
        """

        def _task():
            try:
                mem_id = str(uuid.uuid4())
                embedding = self.model.encode(content).tolist()

                metadata = {
                    "type": "core_memory",
                    "emotion": emotion.lower(),
                    "context": context_name,
                    "keywords": ", ".join(keywords).lower(),
                    "timestamp": datetime.now().timestamp(),
                    # ---[NUOVO] GERARCHIA MEMPALACE ---
                    "wing": context_name,
                    "room": "core_vault",
                    "drawer": "dream_crystal"
                }

                self.core_memories.upsert(
                    ids=[mem_id],
                    embeddings=[embedding],
                    documents=[content],
                    metadatas=[metadata],
                )
                self.log(
                    t(
                        "avatar_server.log.core_memory_engraved",
                        emotion=emotion,
                        context=context_name,
                    )
                )
            except Exception as e:
                self.log(t("avatar_server.log.error_core_engrave", error=e), "ERROR")

        self.write_queue.submit(_task)

    def retrieve_relevant_core_memories(
        self, query: str, context_name: str, top_k: int = 3
    ) -> List[str]:
        """
        Recupera le Core Memories più pertinenti alla query e al contesto attuale.
        """
        if not query:
            return []

        self.log(
            t(
                "avatar_server.log.searching_dreams",
                query=query[:30],
                context=context_name,
            )
        )
        try:
            query_embedding = self.model.encode(query).tolist()

            results = self.core_memories.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where={"context": context_name},
            )

            found = (
                results["documents"][0] if results and results.get("documents") else []
            )
            if found:
                self.log(
                    t("avatar_server.log.core_memories_retrieved", count=len(found))
                )
            return found
        except Exception as e:
            self.log(t("avatar_server.log.error_dream_resonance", error=e), "ERROR")
            return []

    def get_last_episodic_memory(self) -> str:
        """Recupera l'ultima memoria episodica inserita."""
        try:
            count = self.episodic_memories.count()
            if count == 0:
                return t("avatar_server.log.no_episodic_found")
            results = self.episodic_memories.get(
                limit=1, offset=count - 1, include=["documents"]
            )
            return (
                results["documents"][0]
                if results and results.get("documents")
                else t("avatar_server.log.error_last_memory_generic")
            )
        except Exception as e:
            self.log(t("avatar_server.log.error_last_memory", error=e))
            return t("avatar_server.log.error_last_memory_generic")

    def get_random_distant_memories(self, limit: int = 3) -> List[str]:
        """[MODULO 1] Recupera ricordi casuali dal passato per il Subconscio."""
        try:
            count = self.episodic_memories.count()
            if count < 10:
                return[] # Troppo pochi ricordi per fare associazioni
            
            import random
            # Prendi un offset casuale nella prima metà della memoria (i più vecchi)
            offset = random.randint(0, max(0, (count // 2) - limit))
            
            results = self.episodic_memories.get(
                limit=limit,
                offset=offset,
                include=["documents"]
            )
            return results["documents"] if results and results.get("documents") else[]
        except Exception as e:
            self.log(t("log.memory_random_error", error=e))
            return[]

    # --- [NUOVO] METODO PER FACTORY RESET (FASE 2) ---
    def nuke_vector_db(self) -> bool:
        """
        Svuota in modo sicuro tutte le collezioni vettoriali tramite API ChromaDB.
        Evita l'errore di PermissionError (File Lock) su Windows durante il Factory Reset.
        """
        self.log(t("avatar_server.log.db_purge_start"), "SYSTEM")
        collections_to_reset = [
            "unified_knowledge",
            "episodic_memories",
            "core_memories",
            "graph_embeddings"
        ]
        success = True

        for col_name in collections_to_reset:
            try:
                self.client.delete_collection(name=col_name)
                self.log(
                    t("avatar_server.log.collection_disintegrated", name=col_name),
                    "SYSTEM",
                )
            except Exception as e:
                self.log(
                    t(
                        "avatar_server.log.error_delete_collection",
                        name=col_name,
                        error=e,
                    ),
                    "WARNING",
                )
                # Non impostiamo success = False qui perché se non esiste, il risultato finale (essere vuota) è comunque raggiunto.

        self.log(t("avatar_server.log.db_purge_complete"), "SYSTEM")
        return success

    # --- [NUOVO] PROTOCOLLO MEMORIA DELL'ANIMA (BACKSTORY v5.0) ---
    def ingest_avatar_backstory(self, avatar_name: str, db_manager=None, on_complete=None, companions_list=None):
        """
        Legge i file storyboard.txt e memorie_gdr.json dalla cartella dell'avatar
        e li inietta nel RAG Ibrido (Vector DB + GraphRAG).
        Rileva e aggiorna automaticamente le ingestioni precedenti incomplete.
        """
        def _task():
            try:
                import json
                from pathlib import Path
                
                context_name = f"Standard_{avatar_name}"
                super_id = f"backstory_{avatar_name}_super_family_v5" # Bump a v5 per purgare i vecchi dati inquinati
                
                # 1. Controllo Intelligenza di Ingestione (Rilevamento Upgrade)
                try:
                    existing_super = self.unified_library.get(ids=list([super_id]))
                    if existing_super and len(existing_super.get("ids", list())) > 0:
                        # Il Super-Ricordo esiste già: l'ingestione è aggiornata. Salto.
                        self.log(t("memory.backstory_already_ingested", name=avatar_name.capitalize()), "MEMORY")
                        if on_complete:
                            on_complete(t("brain.super_memory_prefix", doc=existing_super['documents'][0]))
                        return
                except Exception:
                    pass

                # 2. Se siamo qui, è un primo avvio o un upgrade. Purghiamo i vecchi dati parziali.
                try:
                    # [FIX CRITICO] Safe Delete per evitare la corruzione dell'indice HNSW di ChromaDB
                    to_delete = self.unified_library.get(where={"$and": [{"context": context_name}, {"type": "backstory"}]})
                    if to_delete and to_delete.get("ids"):
                        self.unified_library.delete(ids=to_delete["ids"])
                        
                    if hasattr(self, "executor") and self.executor and self.executor.db_manager:
                        self.executor.db_manager.cursor.execute(
                            "DELETE FROM knowledge_graph WHERE context = ? AND predicate IN (?, ?, ?)",
                            (context_name, "si trovava in", "ha interagito con", t("memory.graph_sister_relation"))
                        )
                        self.executor.db_manager.conn.commit()
                except Exception as e_clean:
                    self.log(f"Pulizia preventiva backstory fallita (non critica): {e_clean}", "WARNING")

                # Usa APP_ROOT per garantire percorsi assoluti e sicuri
                from executor import APP_ROOT
                backstory_dir = APP_ROOT / "avatars" / avatar_name.lower() / "backstory"
                if not backstory_dir.exists():
                    return

                self.log(t("memory.backstory_ingest_start", name=avatar_name.capitalize()), "MEMORY")
                chunks_added = 0

                # 3. Ingestione Storyboard (Testo Libero -> Vector DB)
                storyboard_file = backstory_dir / "storyboard.txt"
                if storyboard_file.exists():
                    content = storyboard_file.read_text(encoding="utf-8")
                    # Dividiamo per i separatori logici '---'
                    blocks = [b.strip() for b in content.split("---") if b.strip()]
                    for i, block in enumerate(blocks):
                        if len(block) > 50:
                            doc_id = f"backstory_{avatar_name}_story_{i}"
                            metadata = {
                                "type": "backstory",
                                "context": context_name,
                                "source": "storyboard"
                            }
                            embedding = self.model.encode(block).tolist()
                            self.unified_library.upsert(
                                ids=list([doc_id]),
                                embeddings=list([embedding]),
                                documents=list([block]),
                                metadatas=list([metadata])
                            )
                            chunks_added += 1

                # 4. Ingestione Memorie Strutturate (JSON -> Vector DB + GraphRAG)
                memorie_file = backstory_dir / "memorie_gdr.json"
                if memorie_file.exists():
                    with open(memorie_file, "r", encoding="utf-8") as f:
                        memorie = json.load(f)
                    
                    unique_family_members = set()

                    for i, mem in enumerate(memorie):
                        estratto = mem.get("estratto_cronaca", "")
                        if estratto:
                            doc_id = f"backstory_{avatar_name}_mem_{i}"
                            metadata = {
                                "type": "backstory",
                                "context": context_name,
                                "source": "memorie_gdr",
                                "evento": mem.get("evento", "")
                            }
                            embedding = self.model.encode(estratto).tolist()
                            self.unified_library.upsert(
                                ids=list([doc_id]),
                                embeddings=list([embedding]),
                                documents=list([estratto]),
                                metadatas=list([metadata])
                            )
                            chunks_added += 1

                        # 4. Iniezione nel GraphRAG (Rete Relazionale)
                        if hasattr(self, "executor") and self.executor and self.executor.db_manager:
                            protagonista = mem.get("personaggio", "")
                            coinvolti = mem.get("persone_coinvolte", list())
                            luogo = mem.get("luogo", "")
                            
                            if protagonista and luogo:
                                t_id1 = self.executor.db_manager.add_graph_triplet(
                                    protagonista, "si trovava in", luogo, context=context_name
                                )
                                if t_id1: self.add_graph_triplet_vector(t_id1, protagonista, "si trovava in", luogo, context_name)
                            
                            if protagonista and coinvolti:
                                for persona in coinvolti:
                                    if persona != protagonista:
                                        unique_family_members.add(persona)
                                        t_id2 = self.executor.db_manager.add_graph_triplet(
                                            protagonista, "ha interagito con", persona, context=context_name
                                        )
                                        if t_id2: self.add_graph_triplet_vector(t_id2, protagonista, "ha interagito con", persona, context_name)
                                        
                                        # Tripletta familiare per GraphRAG
                                        t_id3 = self.executor.db_manager.add_graph_triplet(
                                            protagonista, t("memory.graph_sister_relation"), persona, context=context_name
                                        )
                                        if t_id3: self.add_graph_triplet_vector(t_id3, protagonista, t("memory.graph_sister_relation"), persona, context_name)

                    # 5. Generazione ed Ingestione del Super-Ricordo (Albero Genealogico Agnostico)
                    # Usiamo la lista esatta dei file fisici passata da chat.py per evitare inquinamento da memorie_gdr.json
                    family_names = companions_list if companions_list else list(unique_family_members)
                    
                    if family_names:
                        family_list_str = ", ".join(family_names)
                        super_memory_text = t("memory.super_memory_family", family=family_list_str)
                        doc_id = f"backstory_{avatar_name}_super_family_v5"
                        metadata = {
                            "type": "backstory",
                            "context": context_name,
                            "source": "auto_synthesis",
                            "keywords": "sorelle, famiglia, nomi, compagne, gruppo"
                        }
                        embedding = self.model.encode(super_memory_text).tolist()
                        self.unified_library.upsert(
                            ids=list([doc_id]),
                            embeddings=list([embedding]),
                            documents=list([super_memory_text]),
                            metadatas=list([metadata])
                        )
                        chunks_added += 1

                if chunks_added > 0:
                    self.log(t("memory.backstory_ingest_success", name=avatar_name.capitalize(), count=chunks_added), "MEMORY")

                # --- [FIX CRITICO] CALLBACK PER CACHE IN RAM ---
                if on_complete:
                    try:
                        super_doc = self.unified_library.get(ids=list([super_id]))
                        if super_doc and super_doc.get("documents") and len(super_doc["documents"]) > 0:
                            on_complete(t("brain.super_memory_prefix", doc=super_doc['documents'][0]))
                        else:
                            on_complete("")
                    except Exception:
                        on_complete("")

            except Exception as e:
                self.log(t("memory.backstory_ingest_error", name=avatar_name.capitalize(), error=str(e)), "ERROR")
                if on_complete:
                    on_complete("")

        self.write_queue.submit(_task)
