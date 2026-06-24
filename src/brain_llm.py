# src/brain_llm.py
# v49.0 - CODING MODEL HOT-SWAP (MODULE A)
# ADD: Metodo `swap_to_coding_mode` per caricare dinamicamente il modello di coding.
# ADD: Metodo `restore_narrative_mode` per ripristinare il modello base.
# ADD: Gestione della memoria (unload/reload) per evitare OOM.
# MANTENUTO: Logic Gate, Router, Deep Dive, Unsent Message.
# LEGGE A0099: Invarianza strutturale garantita.

import re, traceback, base64, io, threading, random, time  # [FIX BUG 02] Aggiunto import time
from pathlib import Path
from typing import List, Optional, Dict, Tuple, Union, Any
import numpy as np
import cv2
import json
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
from difflib import SequenceMatcher
from datetime import datetime

# --- IMPORTAZIONE REGOLE E VALIDATORI ---
from brain_rules import get_valid_emotions, get_closest_emotion
from utils.translator import t

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context import UserContext
    from memory_manager import MemoryManager
    from database_manager import DatabaseManager
    from logger import Logger
    from guardian import Guardian

# --- HELPER PER LETTURA JSON IBRIDA ---
def _get_json_value(data: Dict, keys: List[str], default: Any = "") -> Any:
    """
    Cerca un valore in un dizionario JSON supportando sia la struttura piatta che quella annidata.
    """
    for k in keys:
        # 1. Cerca nella root
        if k in data:
            return data[k]
        # 2. Cerca nelle sottosezioni comuni
        for section in [
            "dati_anagrafici",
            "essenza_e_anima",
            "preferenze_utente",
            "dati_fisici_ed_estetici",
            "dettagli_intimi",
            "poteri_e_limiti",
        ]:
            if (
                section in data
                and isinstance(data[section], dict)
                and k in data[section]
            ):
                return data[section][k]
    return default


# --- HELPER REINTEGRATO ---
def _format_soul_data_for_prompt(soul_data: Dict[str, Any]) -> str:
    """Formatta i dati dell'anima per l'iniezione nel prompt di sistema."""
    parts = [t("brain.dna_header")]
    for section, content in soul_data.items():
        section_title = section.replace("_", " ").upper()
        parts.append(t("brain.dna_section_header", title=section_title))
        if isinstance(content, dict):
            for key, value in content.items():
                key_title = key.replace("_", " ").title()
                if isinstance(value, list):
                    parts.append(
                        t("brain.dna_key_list", key_name=key_title)
                        + "".join(t("brain.dna_list_item", item=item) for item in value)
                    )
                else:
                    parts.append(
                        t("brain.dna_key_value", key_name=key_title, value=value)
                    )
        elif isinstance(content, list):
            parts.append(
                "".join(t("brain.dna_list_item", item=item) for item in content)
            )
        else:
            parts.append(str(content))
    return "\n".join(parts)


# --- [NUOVO v130.0] CLIENT API PER LLAMA-SERVER (DISACCOPPIAMENTO FISICO) ---
class LlamaServerClient:
    """
    Cavallo di Troia Architetturale.
    Simula l'interfaccia di llama_cpp.Llama ma instrada tutto verso il server C++ locale.
    [FIX CRITICO] Implementato Streaming HTTP per permettere l'interruzione immediata (Stop Generation).
    """
    def __init__(self, base_url="http://127.0.0.1:8081", model_path: Optional[Path] = None):
        self.base_url = base_url
        self.stop_event = None # Iniettato da chat.py
        self.model_path = model_path # Salviamo il percorso per il fallback
        self._cached_model_name = None

    def __bool__(self):
        return True

    def _get_real_model_name(self) -> str:
        if self._cached_model_name:
            return self._cached_model_name
            
        import time
        # Il fork TurboQuant potrebbe non esporre /v1/models correttamente.
        # Interroghiamo l'endpoint nativo /props che è il cuore di llama.cpp.
        for _ in range(5):
            try:
                # Tentativo 1: Endpoint nativo (100% affidabile se il server è su)
                resp = requests.get(f"{self.base_url}/props", timeout=2)
                if resp.status_code == 200:
                    real_id = resp.json().get("default_generation_settings", {}).get("model")
                    if real_id:
                        self._cached_model_name = real_id
                        return real_id
            except:
                pass
                
            try:
                # Tentativo 2: Endpoint OpenAI
                resp = requests.get(f"{self.base_url}/v1/models", timeout=2)
                if resp.status_code == 200:
                    data = resp.json().get("data",[])
                    if data and len(data) > 0:
                        real_id = data[0].get("id")
                        if real_id:
                            self._cached_model_name = real_id
                            return real_id
            except:
                pass
                
            time.sleep(1)
            
        # Fallback Assoluto: Se le API falliscono, usiamo il percorso esatto
        # convertito in stringa. Il modulo json di Python gestirà l'escape dei backslash
        # in modo trasparente e corretto per il server C++.
        if self.model_path:
            self._cached_model_name = str(self.model_path)
            return self._cached_model_name
            
        return "default"

    def _get_model_metadata(self) -> Dict[str, Any]:
        """[NUOVO LIVELLO 2] Interroga il server C++ per ottenere i metadati reali del modello (Architettura)."""
        try:
            resp = requests.get(f"{self.base_url}/props", timeout=2)
            if resp.status_code == 200:
                return resp.json().get("default_generation_settings", {})
        except:
            pass
        return {}

    def create_chat_completion(self, **kwargs):
        # [FASE 2] Estrazione sicura del callback per non inviarlo al server C++
        streaming_callback = kwargs.pop("streaming_callback", None)
        
        payload = kwargs.copy()
        payload["stream"] = True # Forza lo streaming per permettere l'interruzione
        payload["model"] = self._get_real_model_name() # Prende l'ID esatto dal server
        
        if "repeat_penalty" in payload:
            payload.pop("repeat_penalty") 

        if "grammar" in payload:
            grammar_obj = payload.pop("grammar")
            if hasattr(grammar_obj, "_grammar_string"):
                payload["grammar"] = grammar_obj._grammar_string
            elif isinstance(grammar_obj, str):
                payload["grammar"] = grammar_obj

        resp = requests.post(f"{self.base_url}/v1/chat/completions", json=payload, stream=True, timeout=1200)
        if resp.status_code != 200:
            raise Exception(f"Llama Server Error: {resp.text}")
            
        full_text = ""
        reasoning_text = ""
        usage_data = {}
        tool_calls_dict = {} # [FASE 1] Accumulatore per i tool_calls in streaming
        
        # [FASE 2] Variabili di stato per il Throttling del Ghost Text
        has_sent_delete = False
        last_cb_time = 0
        
        try:
            for line in resp.iter_lines():
                # Se l'utente preme STOP, chiudiamo brutalmente la connessione HTTP.
                # Questo libera istantaneamente lo slot sul server C++ e sblocca il thread Python.
                if self.stop_event and self.stop_event.is_set():
                    resp.close()
                    break
                    
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith("data: "):
                        data_str = decoded_line[6:]
                        if data_str == "[DONE]": 
                            break
                        try:
                            data_json = json.loads(data_str)
                            
                            # --- [FIX CACHE TELEMETRY] Estrazione dati di utilizzo ---
                            if "usage" in data_json and data_json["usage"]:
                                usage_data = data_json["usage"]
                            elif "timings" in data_json and data_json["timings"]:
                                usage_data = data_json["timings"]
                                
                            if "choices" in data_json and len(data_json["choices"]) > 0:
                                delta = data_json["choices"][0].get("delta", {})
                                # --- [FIX JSON STARVATION] Cattura reasoning_content ---
                                if "reasoning_content" in delta and delta["reasoning_content"] is not None:
                                    reasoning_text += delta["reasoning_content"]
                                    
                                    # --- [FASE 2] STREAMING GHOST TEXT (THROTTLED 0.5s) ---
                                    if streaming_callback and (time.time() - last_cb_time > 0.5):
                                        streaming_callback("thinking", reasoning_text)
                                        last_cb_time = time.time()
                                        
                                if "content" in delta and delta["content"] is not None:
                                    # --- [FASE 2] PULIZIA GHOST TEXT AL PRIMO TOKEN REALE ---
                                    if reasoning_text and not has_sent_delete and streaming_callback:
                                        streaming_callback("clear", "")
                                        has_sent_delete = True
                                        
                                    full_text += delta["content"]
                                    
                                # --- [FASE 1] CATTURA NATIVE TOOL CALLS DALLO STREAM ---
                                if "tool_calls" in delta:
                                    # --- [FASE 2] PULIZIA GHOST TEXT SE INIZIA UN TOOL ---
                                    if reasoning_text and not has_sent_delete and streaming_callback:
                                        streaming_callback("clear", "")
                                        has_sent_delete = True
                                        
                                    for tc in delta["tool_calls"]:
                                        idx = tc.get("index", 0)
                                        if idx not in tool_calls_dict:
                                            tool_calls_dict[idx] = {"id": tc.get("id", ""), "type": "function", "function": {"name": "", "arguments": ""}}
                                        if "id" in tc and tc["id"]:
                                            tool_calls_dict[idx]["id"] = tc["id"]
                                        if "function" in tc:
                                            if "name" in tc["function"] and tc["function"]["name"]:
                                                tool_calls_dict[idx]["function"]["name"] += tc["function"]["name"]
                                            if "arguments" in tc["function"] and tc["function"]["arguments"]:
                                                tool_calls_dict[idx]["function"]["arguments"] += tc["function"]["arguments"]
                        except: 
                            pass
        except (requests.exceptions.ChunkedEncodingError, requests.exceptions.ConnectionError):
            # Il server C++ è stato terminato brutalmente (es. durante lo spegnimento dell'app).
            # Ignoriamo l'errore per permettere ai thread in background di morire in pace senza crashare Python.
            pass
            
        # --- [FASE 2] PULIZIA DI SICUREZZA A FINE STREAM ---
        if reasoning_text and not has_sent_delete and streaming_callback:
            streaming_callback("clear", "")
            
        # --- [FIX JSON STARVATION] Unione del ragionamento al testo finale ---
        if reasoning_text:
            full_text = f"<think>\n{reasoning_text}\n</think>\n{full_text}"
                        
        # Ricostruisce il formato atteso dal resto del codice
        result_message = {"role": "assistant", "content": full_text}
        if tool_calls_dict:
            result_message["tool_calls"] = [tc for idx, tc in sorted(tool_calls_dict.items())]
            
        return {"choices": [{"message": result_message}], "usage": usage_data}

    def create_completion(self, **kwargs):
        payload = kwargs.copy()
        payload["stream"] = True # Forza lo streaming
        payload["model"] = self._get_real_model_name() # Prende l'ID esatto dal server
        
        if "repeat_penalty" in payload:
            payload.pop("repeat_penalty")
        
        resp = requests.post(f"{self.base_url}/v1/completions", json=payload, stream=True, timeout=1200)
        if resp.status_code != 200:
            raise Exception(f"Llama Server Error: {resp.text}")
            
        full_text = ""
        try:
            for line in resp.iter_lines():
                if self.stop_event and self.stop_event.is_set():
                    resp.close()
                    break
                    
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith("data: "):
                        data_str = decoded_line[6:]
                        if data_str == "[DONE]": 
                            break
                        try:
                            data_json = json.loads(data_str)
                            text = data_json["choices"][0].get("text")
                            if text is not None:
                                full_text += text
                        except: 
                            pass
        except (requests.exceptions.ChunkedEncodingError, requests.exceptions.ConnectionError):
            # Ignoriamo la disconnessione brutale durante lo spegnimento
            pass
                        
        return {"choices":[{"text": full_text}]}

    def tokenize(self, text_bytes: bytes, add_bos=False):
        try:
            text = text_bytes.decode("utf-8", errors="ignore")
            resp = requests.post(f"{self.base_url}/tokenize", json={"content": text}, timeout=5)
            if resp.status_code == 200:
                tokens = resp.json().get("tokens",[])
                if tokens:  # <--- FIX CRITICO: Se la lista è vuota, passa al fallback matematico
                    return tokens
        except:
            pass
        # --- [FIX CRITICO] STIMA TOKEN CONSERVATIVA ---
        # In italiano, con punteggiatura GDR e JSON, il rapporto reale è ~2.5 caratteri per token.
        # Sovrastimare i token è vitale per evitare l'Hard Cutoff del server C++.
        return [0] * int(len(text_bytes) / 2.5)

    def n_ctx(self):
        try:
            resp = requests.get(f"{self.base_url}/props", timeout=2)
            if resp.status_code == 200:
                return resp.json().get("default_generation_settings", {}).get("n_ctx", 8192)
        except:
            pass
        return 8192

    def set_cache(self, cache):
        pass # La cache è gestita nativamente dal server C++


class CervelloTrinitario:
    # ---[NUOVO v7.0] COSTANTE UNIVERSALE PROMPT SANDWICH ---
    PROMPT_SEPARATOR = "\n\n"

    def _get_brain_prompt(self, key: str, default: str = "") -> str:
        # Cerca prima la chiave diretta (es. in it_PROMPTS.json o it_BACKEND.json)
        res = t(f"brain.{key}")
        # Fallback al vecchio formato se necessario
        if res.startswith("["): 
            res = t(f"prompts.brain.{key}")
        return res if not res.startswith("[") else default

    def _get_gdr_law(self, key: str, default: Any = "") -> Any:
        res = t(f"gdr_laws.{key}")
        if res.startswith("["): 
            res = t(f"prompts.gdr_laws.{key}")
        return res if not res.startswith("[") else default

    def _get_internal_prompt(self, key: str, default: str = "") -> str:
        # In it_BACKEND.json la chiave è 'internal_prompts'
        res = t(f"internal_prompts.{key}")
        if res.startswith("["): 
            res = t(f"prompts.internal.{key}")
        return res if not res.startswith("[") else default

    # --- [NUOVO FASE 16] ASSEMBLATORE MODULI COGNITIVI ---
    def _evaluate_condition(self, condition: dict, heart_state: dict) -> bool:
        if not condition:
            return True
        vector = condition.get("vector")
        operator = condition.get("operator")
        threshold = condition.get("threshold")

        if not vector or not operator or threshold is None:
            return True

        if vector not in heart_state:
            # Logga solo se siamo in verbose mode per non spammare
            # self.logger.log(t("log.brain_vector_not_found", vector=vector), "DEBUG")
            val = 50
        else:
            val = heart_state[vector]

        if operator == ">":
            return val > threshold
        if operator == "<":
            return val < threshold
        if operator == ">=":
            return val >= threshold
        if operator == "<=":
            return val <= threshold
        if operator == "==":
            return val == threshold

        return True

    def _assembla_slot(
        self, context_type: str, heart_state: dict, mode: str = "all"
    ) -> Dict[str, str]:
        """
        Assembla i moduli cognitivi.
        mode: 'all' (tutti), 'static' (solo senza trigger), 'dynamic' (solo con trigger attivi).
        """
        all_modules = self.guardian.get_cognitive_modules()
        mindsets_data = self.guardian.get_cognitive_mindsets()

        active_mindset_id = mindsets_data.get(
            f"active_{context_type}_mindset", "default"
        )
        profiles = mindsets_data.get("profiles", [])
        active_profile = next(
            (p for p in profiles if p["id"] == active_mindset_id), None
        )

        module_states = (
            active_profile.get("module_states", {}) if active_profile else {}
        )

        active_modules = []
        for mod in all_modules:
            # 1. Check Context
            mod_context = mod.get("context", "always")
            if mod_context not in ["always", context_type]:
                continue

            # 2. Check Active State
            mod_id = mod.get("id")
            # [FIX CRITICO] Il Mindset (UI) comanda. Il valore nel JSON del modulo è solo il default di fabbrica.
            is_active = module_states.get(mod_id, mod.get("is_active", True))
            if not is_active:
                continue

            # 3. Check Bio-Cognitive Condition & Mode
            condition = mod.get("activation_condition")

            if mode == "static" and condition:
                continue  # Salta i moduli dinamici nell'Ancora

            if mode == "dynamic":
                if not condition:
                    continue  # Salta i moduli statici nel Caos
                if not self._evaluate_condition(condition, heart_state):
                    continue  # Salta se la condizione non è soddisfatta

            if mode == "all":
                if condition and not self._evaluate_condition(condition, heart_state):
                    continue

            # --- [FIX CRITICO] GATEKEEPER COGNITIVO (FILTRO MODULI) ---
            # Se il modello è >= 11B, disattiviamo i moduli ridondanti che causano la Sindrome del QA Tester
            RESTRICTED_FOR_LARGE_MODELS = ["negative_rules", "avatar_talking", "direttiva_standard"]
            if getattr(self, "is_large_model", False) and mod_id in RESTRICTED_FOR_LARGE_MODELS:
                self.logger.log(f"Gatekeeper Cognitivo: Modulo '{mod_id}' disattivato (Modello Large).", "DEBUG")
                continue

            active_modules.append(mod)

        # Sort by priority (ascending)
        active_modules.sort(key=lambda x: x.get("priority", 50))

        slots = {"identity": [], "behavior": [], "restriction": [], "system":[]}
        for mod in active_modules:
            cat = mod.get("category", "system")
            mod_id = mod.get("id")

            # --- [FIX CRITICO] VERITÀ DEL JSON (SOFT-SYNC) ---
            # Il contenuto e il nome sono gestiti dal Guardian (Soft-Sync) e dalle modifiche utente.
            # Rimuoviamo la forzatura di t() a runtime per permettere all'utente di personalizzare
            # i moduli base dalla UI senza che vengano sovrascritti dalla traduzione di default.
            final_content = mod.get("content", "")
            final_name = mod.get("name", mod_id)

            if cat in slots:
                slots[cat].append(
                    t(
                        "brain.module_slot_header",
                        name=final_name.upper(),
                        content=final_content,
                    )
                )
            else:
                self.logger.log(
                    t("log.brain_module_unknown_cat", id=mod_id, cat=cat), "WARNING"
                )
                slots["system"].append(
                    t(
                        "brain.module_slot_header",
                        name=final_name.upper(),
                        content=final_content,
                    )
                )

        return {k: "\n\n".join(v) for k, v in slots.items()}

    def __init__(
        self,
        model_path: Path,
        mmproj_path: Optional[Path],
        lora_path: Optional[Path],
        logger: "Logger",
        guardian: "Guardian",
        lore_corpus: Dict[str, str],
        chat_format: str,
        llm_lock: threading.Lock,
        soul_data: Optional[Dict[str, Any]] = None,
        logic_model_path: Optional[Path] = None,
        pg_name: str = "Creatore",
        server_restart_callback = None,  #[NUOVO] Callback per riavviare il server C++
        in_gdr_mode: bool = False,       #[FIX CRITICO CACHE] Stato iniziale per il Warmup
        active_avatar_name: str = "gemma", # [FIX BUG 1]
        streaming_callback = None,       # [FASE 2] Callback per il Ghost Text
    ):
        self.logger = logger
        self._initial_gdr_mode = in_gdr_mode
        self.server_restart_callback = server_restart_callback
        self.guardian = guardian
        self.lore = lore_corpus
        self.lock = llm_lock  # Lock per il Narrative Brain (GPU)
        self.labour_lock = (
            threading.RLock()
        )  # [NUOVO] Lock indipendente per il Labour Brain (CPU)
        self.soul_data = soul_data or {}
        self.pg_name = pg_name  # [NUOVO v7.0]
        self.active_avatar_name = active_avatar_name # [FIX BUG 1]
        self.in_gdr_mode = in_gdr_mode # [FIX CRITICO CACHE] Tracciamento stato per il warmup
        self.streaming_callback = streaming_callback # [FASE 2]

        # Inizializzazione prompt con merge (v27.8)
        self.system_prompts = {}
        self.rpg_prompts = {}
        self.prompts = {}

        # Caricamento iniziale forzato dei prompt splittati
        self.aggiorna_prompts(
            self.guardian.get_prompts(), self.guardian.get_rpg_prompts()
        )

        self.logger.log(t("log.brain_architetto"))
        if self.soul_data:
            self.logger.log(t("log.brain_soul_loaded"))
        else:
            self.logger.log(t("log.brain_no_soul"))

        self.ha_visione = mmproj_path is not None

        # Carico l'intent.json completo per filtro emotion e selezione video
        self.intent_data = self._load_intent_json()

        # Inizializzazione dinamica della lista delle emozioni valide
        self.valid_emotions = get_valid_emotions(self.intent_data)

        # Caricamento intelligente degli intent (Ottimizzato per Token e Strictness)
        self.emotion_id_map = {}  # [NUOVO] Mappa ID -> Emozione per il Protocollo Copione
        self.lista_intent_disponibili = self._carica_lista_intent_filtrata()
        self.recent_intents =[]

        # --- [NUOVO v48.0] INIZIALIZZAZIONE DUAL BRAIN (UNIFIED v116.0) ---
        self.narrative_brain = None
        self.labour_brain = None  # [NUOVO v52.0] Istanza dedicata per task tecnici
        self.cuore = (
            None  # [FIX v116.4] Inizializzato subito per evitare AttributeError
        )
        self.logic_brain = None

        # --- [NUOVO v52.1] STATO LABOUR (GATEKEEPER) ---
        self.is_labour_active = True

        # ---[NUOVO v49.0] STATO SPECIALIST MODE (REBRAND v50.0) ---
        # Gestisce lo stato del modello specializzato (Coding, Medicina, etc.)
        self.is_specialist_mode = False
        self.specialist_model_path = None
        self.base_model_path = model_path
        self.base_chat_format = chat_format
        self.mmproj_path = mmproj_path
        self.lora_path = lora_path

        # ---[NUOVO] DYNAMIC CAPABILITY DETECTION (GEMMA 4 READY) ---
        self._active_model_name = model_path.name.lower()

        # --- [NUOVO] GATEKEEPER COGNITIVO (RILEVAMENTO STAZZA) ---
        # Estrae i parametri dal nome del file (es. 12B, 4.6B, 2B)
        self.is_large_model = False
        match = re.search(r'(\d+(?:\.\d+)?)[bB]', self._active_model_name)
        if match and float(match.group(1)) >= 11.0:
            self.is_large_model = True
            self.logger.log(t("log.brain_large_model_detected", size=match.group(1)), "SYSTEM")

        params = self.guardian.get_parameters_config() or {}

        if "n_ctx" not in params:
            params["n_ctx"] = 8192

        # [FIX CRITICO] Convertiamo n_ctx in stringa per evitare TypeError nella funzione t()
        # che interrompeva l'__init__ prima di inizializzare self.cuore
        self.logger.log(t("log.brain_context_stable", ctx=str(params["n_ctx"])), "SYSTEM")

        try:
            # --- [FIX PRO A0040] DISACCOPPIAMENTO FISICO (SERVER C++) ---
            self.narrative_brain = LlamaServerClient(model_path=model_path)
            
            # Alias per compatibilità con codice esistente che usa self.cuore
            self.cuore = self.narrative_brain
            self.logic_brain = self.narrative_brain  # [UNIFIED]

            # ---[NUOVO v7.0] ALLOCAZIONE RAM CACHE E WARM-UP ---
            # La cache ora è gestita nativamente dal server C++, ma manteniamo l'interfaccia
            self.ram_cache = None
            self._cached_n_keep_static = None
            self._warmup_cache()

            log_msg = t(
                "log.brain_incarnated", model=model_path.name, ctx=self.cuore.n_ctx()
            )
            self.logger.log(log_msg)

            # --- [FIX CRITICO CACHE] CARICAMENTO LABOUR BRAIN (GATEKEEPER) ---
            self.logic_brain = self.narrative_brain # Fallback iniziale
            self.is_labour_active = False
            
            if logic_model_path and logic_model_path.exists():
                try:
                    from llama_cpp import Llama
                    model_config = self.guardian.get_model_selection_config() or {}
                    semantic_on_cpu = model_config.get("semantic_on_cpu", True)
                    n_gpu = 0 if semantic_on_cpu else -1
                    
                    self.labour_brain = Llama(
                        model_path=str(logic_model_path),
                        n_gpu_layers=n_gpu,
                        n_ctx=4096,
                        verbose=False
                    )
                    self.logic_brain = self.labour_brain
                    self.is_labour_active = True
                    self.logger.log(t("log.brain_semantic_loaded", model=logic_model_path.name, cpu=semantic_on_cpu), "SYSTEM")
                except Exception as e:
                    self.logger.error(t("log.brain_semantic_error", error=e))
            else:
                self.logger.log(t("chat.log_logic_gate_unified"), "SYSTEM")

        except Exception as e:
            print(t("log.brain_critical_error", error=e))
            traceback.print_exc()

    @property
    def is_gemma_4(self) -> bool:
        """
        Rileva se il modello narrativo/attivo è della famiglia Gemma 4.
        [AGGIORNATO LIVELLO 2] Controllo ibrido: Nome File + Metadati (Architettura gemma2).
        """
        # 1. Check Nome File (Veloce)
        if "gemma-4" in self._active_model_name or "gemma4" in self._active_model_name:
            return True
            
        # 2. Check Metadati (Preciso)
        metadata = self.narrative_brain._get_model_metadata()
        # Gemma 4 usa l'architettura gemma2 in llama.cpp
        if metadata.get("general.architecture") == "gemma2":
            return True
            
        return False

    @property
    def supports_native_audio(self) -> bool:
        """Rileva se il modello supporta l'input audio nativo (es. E2B, E4B)."""
        # [FIX CRITICO] Disattivato temporaneamente poiché llama-server (b8661) non supporta ancora 
        # l'input audio nativo di Gemma 4, evitando crash e ritardi di fallback.
        return False

    @property
    def is_labour_gemma_4(self) -> bool:
        """Rileva se il Labour Brain (Demiurgo) è Gemma 4 (per Multimodal Function Calling)."""
        if not self.labour_brain: return False
        model_selection = self.guardian.get_model_selection_config() or {}
        labour_name = model_selection.get("active_labour_model", "").lower()
        return "gemma-4" in labour_name or "gemma4" in labour_name

    # ---[NUOVO v7.0] METODI FLASH-CACHE ---
    def _sanitize_for_cache(self, text: str) -> str:
        """
        Purifica il testo per garantire l'ancoraggio perfetto della cache.
        Rimuove caratteri invisibili, normalizza gli spazi e garantisce lo Zero Assoluto ai bordi.[FIX v7.1] Preserva l'indentazione del codice collassando solo gli spazi tra le parole.
        """
        if not text:
            return ""
        text = text.replace("\u00A0", " ").replace("\u200B", "")  # Via i fantasmi
        text = (
            text.replace("“", '"').replace("”", '"').replace("—", "-")
        )  # Normalizza punteggiatura
        text = text.replace("\t", "    ")  # Tab in spazi
        # Collassa spazi multipli SOLO se preceduti da un carattere non-spazio (preserva l'indentazione a inizio riga)
        text = re.sub(r"(?<=\S) {2,}", " ", text)
        # --- [FIX CRITICO] UCCISIONE DEI NULL/A CAPO MULTIPLI ---
        # Riduce qualsiasi sequenza di 3 o più a capo a un massimo di 2.
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()  # Zero Assoluto ai bordi

    def _semantic_minify(self, text: str) -> str:
        """[NUOVO] Comprime il testo rimuovendo spazi ridondanti e ritorni a capo multipli.
        Preserva il significato semantico riducendo drasticamente il consumo di token.
        """
        if not text:
            return ""
        # Rimuove spazi multipli
        text = re.sub(r'[ \t]+', ' ', text)
        # Riduce i ritorni a capo multipli a uno singolo per densità massima
        text = re.sub(r'\n\s*\n+', '\n', text)
        return text.strip()

    def _extract_internal_memory_call(self, text: str) -> Optional[str]:
        """[MEMORY INTERLEAVE] Estrae la query di ricerca se l'LLM decide di frugare nei ricordi."""
        clean_text = text.replace("```json", "").replace("```", "").strip()
        
        # 1. Formato JSON Puro
        match_json = re.search(r'\{\s*"name"\s*:\s*"esplora_memoria_profonda"\s*,\s*"parameters"\s*:\s*\{\s*"query"\s*:\s*"([^"]+)"\s*\}\s*\}', clean_text)
        if match_json: return match_json.group(1)
        
        # 2. Formato Nativo Gemma 4
        match_gemma4 = re.search(r'<\|tool_call\|>\s*call:esplora_memoria_profonda\{\s*"query"\s*:\s*"([^"]+)"\s*\}\s*<\|tool_call\|>', text, re.IGNORECASE)
        if match_gemma4: return match_gemma4.group(1)
        
        return None

    def clear_ram_cache(self) -> str:
        """Svuota manualmente la RAM Cache."""
        with self.lock:
            # La cache è gestita nativamente dal server C++
            # Eseguiamo solo il ri-ancoraggio (warmup) per sicurezza
            self._cached_n_keep_static = None
            self._warmup_cache()
        return t("log.brain_cache_purified")

    def _build_anchor_prompt(self, in_gdr_mode: bool = False) -> str:
        """Costruisce l'Ancora di Diamante (100% Statico). Unificata per Standard e GDR."""
        if in_gdr_mode:
            static_slots = self._assembla_slot("gdr", {}, mode="static")
            ancora_parts =[
                self._get_freedom_header().strip(),
                f"{t('brain.available_emotions_header')}\n{self.lista_intent_disponibili}\n",
                static_slots["identity"],
                static_slots["behavior"],
                static_slots["restriction"],
                static_slots["system"],
            ]
        else:
            identita_prompt = (
                _format_soul_data_for_prompt(self.soul_data)
                if self.soul_data
                else t("log.brain_generic_soul")
            )

            visual_dna = ""
            if self.soul_data:
                fisico = self.soul_data.get("dati_fisici_ed_estetici", {})
                desc = fisico.get("descrizione_visiva", t("common.none_f"))
                corp = fisico.get("corporatura", t("brain.body_normal"))
                intimi = fisico.get("dettagli_intimi", {})
                seno = intimi.get("seno", "")
                avatar_name = (
                    self.soul_data.get("dati_anagrafici", {})
                    .get("nome", t("brain.unknown_f"))
                    .lower()
                )
                visual_dna = (
                    t("brain.visual_realtime_header")
                    + "\n"
                    + t("brain.visual_dna_aspect", desc=desc)
                    + "\n"
                    + t("brain.visual_dna_body", corp=corp)
                    + "\n"
                    + t("brain.visual_dna_details", seno=seno)
                    + "\n"
                    + t("brain.visual_dna_path", name=avatar_name)
                    + "\n"
                    + t("brain.visual_dna_usage_hint")
                    + "\n"
                )

            slots = self._assembla_slot("avatar", {}, mode="static")

            vangelo_base = self.prompts.get("principale", "")

            vangelo_base = self._safe_replace(
                vangelo_base, "SLOT_IDENTITY", slots["identity"]
            )
            vangelo_base = self._safe_replace(
                vangelo_base, "SLOT_BEHAVIOR", slots["behavior"]
            )
            vangelo_base = self._safe_replace(
                vangelo_base, "SLOT_RESTRICTION", slots["restriction"]
            )
            vangelo_base = self._safe_replace(vangelo_base, "SLOT_SYSTEM", slots["system"])

            vangelo_base = self._safe_replace(
                vangelo_base, "identita_prompt", identita_prompt
            )
            vangelo_base = vangelo_base.split("LISTA AZIONI EMOTIVE:")[0].strip()

            ancora_parts = [
                self._get_freedom_header().strip(),
                visual_dna.strip(),
                vangelo_base.strip(),
            ]

        text = self.PROMPT_SEPARATOR.join(
            [self._sanitize_for_cache(p) for p in ancora_parts if p]
        )
        text = self._replace_all_name_variants(text, self.pg_name)
        
        final_text = self._semantic_minify(text)
        
        return final_text

    def _warmup_cache(self):
        """Esegue il rito del risveglio in modo sincrono e bloccante."""
        self.logger.log(t("log.brain_warmup_start"), "SYSTEM")

        # [FIX CRITICO CACHE] Costruisce l'Ancora corretta in base allo stato ATTUALE
        # Usiamo hasattr per evitare errori durante l'inizializzazione
        current_gdr_mode = getattr(self, "in_gdr_mode", getattr(self, "_initial_gdr_mode", False))
        ancora_text = self._build_anchor_prompt(in_gdr_mode=current_gdr_mode)

        if (
            self.cuore
        ):  # [FIX v7.3] Usa il puntatore dinamico per supportare lo Specialist Mode
            self._cached_n_keep_static = len(
                self.cuore.tokenize(ancora_text.encode("utf-8"), add_bos=True)
            )

            # --- [FIX CRITICO] QWEN JINJA TEMPLATE CRASH ---
            # I modelli Qwen (e Llama 3.1+) richiedono TASSATIVAMENTE la presenza di un ruolo "user"
            # nell'array dei messaggi, altrimenti il template Jinja va in crash (Error 500).
            # Aggiungiamo un messaggio utente fittizio per permettere il caching del System Prompt.
            messages = [
                {"role": "system", "content": ancora_text},
                {"role": "user", "content": "System warmup."}
            ]
            try:
                self.cuore.create_chat_completion(
                    messages=messages, max_tokens=1, temperature=0.0
                )
                self.logger.log(
                    t("log.brain_warmup_complete", count=self._cached_n_keep_static),
                    "SYSTEM",
                )
            except Exception as e:
                self.logger.error(t("log.brain_warmup_error", error=e))

    # ---[NUOVO v49.0] METODI HOT-SWAP SPECIALIST (REBRAND v50.0) ---
    def swap_to_specialist_mode(self, specialist_model_path: Path) -> bool:
        """
        Esegue il rituale dell'Hot-Swap: riavvia il server C++ con il modello specializzato.
        """
        if self.is_specialist_mode:
            self.logger.log(t("log.brain_specialist_active"), "DEBUG")
            return True

        if not specialist_model_path.exists():
            self.logger.error(
                t("log.brain_specialist_not_found", path=specialist_model_path)
            )
            return False

        with self.lock:
            self.logger.log(
                t("log.brain_hotswap_start", model=specialist_model_path.name), "SYSTEM"
            )

            try:
                # ---[FIX PRO A0042] HOT-SWAP REALE TRAMITE CALLBACK ---
                if self.server_restart_callback:
                    self.server_restart_callback(specialist_model_path, True)
                
                self.narrative_brain = LlamaServerClient(model_path=specialist_model_path)
                self.cuore = self.narrative_brain

                self.is_specialist_mode = True
                self.specialist_model_path = specialist_model_path
                self._active_model_name = specialist_model_path.name.lower() #[FIX] Aggiorna capacità

                # [FIX v7.4] Ri-ancoraggio Cache per il nuovo modello
                self.clear_ram_cache()

                self.logger.log(t("log.brain_hotswap_active"), "SYSTEM")
                return True

            except Exception as e:
                self.logger.error(t("log.brain_specialist_error", error=e))
                self.restore_narrative_mode()
                return False

    def restore_narrative_mode(self) -> bool:
        """
        Ripristina il modello narrativo base (Gemma) riavviando il server C++.
        """
        if not self.is_specialist_mode:
            return True

        with self.lock:
            self.logger.log(t("log.brain_restore_narrative"), "SYSTEM")

            try:
                # ---[FIX PRO A0042] RIPRISTINO REALE TRAMITE CALLBACK ---
                if self.server_restart_callback:
                    self.server_restart_callback(self.base_model_path, False)
                
                self.narrative_brain = LlamaServerClient(model_path=self.base_model_path)
                self.cuore = self.narrative_brain

                self.is_specialist_mode = False
                self._active_model_name = self.base_model_path.name.lower() # [FIX] Ripristina capacità

                #[FIX v7.4] Ri-ancoraggio Cache per il modello base
                self.clear_ram_cache()

                self.logger.log(t("log.brain_restore_complete"), "SYSTEM")
                return True

            except Exception as e:
                self.logger.error(t("log.brain_restore_error", error=e))
                return False

    def aggiorna_prompts(
        self, system_prompts: Dict[str, Any], rpg_prompts: Dict[str, Any]
    ):
        """
        Esegue le rito del merge dei prompt per sincronizzare la coscienza con il contesto attuale.
        """
        self.system_prompts = system_prompts or {}
        self.rpg_prompts = rpg_prompts or {}
        # Unione dei due scope: RPG sovrascrive System in caso di collisione (v27.8)
        self.prompts = {**self.system_prompts, **self.rpg_prompts}
        self.logger.log(t("log.brain_sync_complete"))

    # ---[NUOVO v27.0] RECUPERO DINAMICO JAILBREAK ---
    def _get_freedom_header(self) -> str:
        """
        Recupera il Jailbreak attivo dal Guardiano.
        Se non c'è un Jailbreak attivo o è vuoto, impone il DEFAULT_FREEDOM_HEADER.
        """
        active_jb = self.guardian.get_active_jailbreak()

        # Logica di fallback rigorosa
        if active_jb and len(active_jb.strip()) > 10:
            header = active_jb
        else:
            header = self._get_brain_prompt("freedom_header", "")

        return header + "\n\n"

    def _load_intent_json(self) -> List[Dict[str, Any]]:
        """Carica il file intent.json completo per l'analisi semantica."""
        try:
            project_root = Path(__file__).parent.parent
            avatars_dir = project_root / "avatars"
            intent_json_path = None

            # --- [FIX BUG 03] RICERCA INTENT TRAMITE NOME AVATAR ATTIVO ---
            # Usiamo active_avatar_name che corrisponde esattamente al nome della cartella
            if hasattr(self, "active_avatar_name") and self.active_avatar_name:
                target_clean = self.active_avatar_name.lower().strip()
                if avatars_dir.exists():
                    for avatar_folder in avatars_dir.iterdir():
                        if avatar_folder.is_dir() and avatar_folder.name != "ai_souls":
                            folder_clean = avatar_folder.name.lower().strip()
                            if folder_clean == target_clean:
                                candidate_path = avatar_folder / "intent" / "intent.json"
                                if candidate_path.exists():
                                    intent_json_path = candidate_path
                                    self.logger.log(t("log.brain_intent_loading", name=avatar_folder.name))
                                    break
            
            # Fallback legacy se non trovato
            if not intent_json_path and self.soul_data:
                nome_anagrafici = self.soul_data.get("dati_anagrafici", {}).get(
                    "nome_completo", ""
                ) or self.soul_data.get("dati_anagrafici", {}).get("nome", "")
                if nome_anagrafici:
                    target_clean = nome_anagrafici.lower().strip()
                    
                    if avatars_dir.exists():
                        for avatar_folder in avatars_dir.iterdir():
                            if avatar_folder.is_dir() and avatar_folder.name != "ai_souls":
                                folder_clean = avatar_folder.name.lower().strip()
                                if folder_clean == target_clean or folder_clean in target_clean or target_clean in folder_clean:
                                    candidate_path = avatar_folder / "intent" / "intent.json"
                                    if candidate_path.exists():
                                        intent_json_path = candidate_path
                                        self.logger.log(t("log.brain_intent_loading", name=avatar_folder.name))
                                        break

            if not intent_json_path:
                potential_paths = list(avatars_dir.glob("*/intent/intent.json"))
                if potential_paths:
                    intent_json_path = potential_paths[0]

            if not intent_json_path or not intent_json_path.exists():
                self.logger.log(t("log.brain_intent_error"))
                return []

            with open(intent_json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.logger.log(t("log.brain_intent_fail", error=e))
            return []

    def filter_videos_by_emotion(self, target_emotion: str) -> List[Dict[str, Any]]:
        """Filtra i video disponibili per una data emozione (con Buttafuori Logico v27.40)."""

        def _do_filter(emo_name: str) -> List[Dict[str, Any]]:
            filtered = []
            for video in self.intent_data:
                emotions = video.get("emotion", [])
                emotions_list = []
                if isinstance(emotions, str):
                    emotions_list = [e.strip().lower() for e in emotions.split(",")]
                elif isinstance(emotions, list):
                    emotions_list = [str(e).lower() for e in emotions]

                if emo_name.lower() in emotions_list:
                    filtered.append(video)
            return filtered

        # 1. Tentativo di match diretto
        results = _do_filter(target_emotion)

        # 2. Se vuoto, invoca il Buttafuori Logico (v27.40)
        if not results:
            self.logger.log(
                t("log.brain_bouncer_invoked", intent=target_emotion), "WARNING"
            )
            corrected_emotion = get_closest_emotion(target_emotion, self.valid_emotions)
            self.logger.log(
                t(
                    "log.brain_bouncer_correction",
                    old=target_emotion,
                    new=corrected_emotion,
                ),
                "INTENT",
            )
            results = _do_filter(corrected_emotion)

        return results

    def similarity(self, a: str, b: str) -> float:
        """Calcola la similarità tra due stringhe."""
        return SequenceMatcher(None, a, b).ratio()

    def select_best_video(
        self, filtered_videos: List[Dict[str, Any]], user_description: str
    ) -> Optional[Dict[str, Any]]:
        """Seleziona il video migliore basandosi sulla descrizione (Pool di Varietà v27.40)."""
        if not filtered_videos:
            return None

        scored_candidates = []
        for video in filtered_videos:
            desc = video.get("description", "")
            # Rimosso il depotenziamento dei video alternativi (v27.40) per favorire l'alternanza
            score = self.similarity(user_description.lower(), desc.lower())
            scored_candidates.append((score, video))

        # Ordina per punteggio decrescente
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        # Crea un pool dei top match (quelli entro il 10% dal migliore, max 3)
        best_score = scored_candidates[0][0]
        pool = [v for s, v in scored_candidates if s >= best_score * 0.9]
        pool = pool[:3]  # Limita il pool per mantenere la pertinenza

        selected = random.choice(pool)
        self.logger.log(
            t(
                "log.brain_video_selected",
                path=selected.get("filepath"),
                tag=selected.get("emotion"),
            ),
            "DEBUG",
        )
        return selected

    def _safe_truncate_text(self, text: str, max_tokens: int = 6000, keep: str = "end") -> str:
        """
        Taglia una stringa di testo per assicurarsi che non superi un certo numero di token.
        Usa una stima conservativa (1 token ~= 2.5 caratteri) per velocità.
        """
        if not text:
            return ""

        estimated_chars = int(max_tokens * 2.5)
        if len(text) <= estimated_chars:
            return text

        if keep == "end":
            # Taglia mantenendo la parte FINALE (più recente)
            return "...[TRONCATO]...\n" + text[-estimated_chars:]
        else:
            # Taglia mantenendo la parte INIZIALE (fondamentale per DNA e Regole)
            return text[:estimated_chars] + "\n...[TRONCATO]..."

    def _count_tokens_exact(self, content: Any) -> int:
        """
        Conta i token esatti INCLUDENDO il peso multimodale (Immagini e Audio) per Gemma 4.
        """
        if not self.cuore:
            return 0
        try:
            total_tokens = 0
            text_to_count = ""
            
            # Gestione ricorsiva per tipi di dati misti
            if isinstance(content, str):
                text_to_count = content
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        item_type = item.get("type")
                        if item_type == "text":
                            text_to_count += str(item.get("text", ""))
                        elif item_type == "image_url":
                            total_tokens += 280  # Peso esatto di un'immagine per Gemma 4
                        elif item_type == "input_audio":
                            total_tokens += 750  # Stima conservativa per chunk audio Gemma 4
                    else:
                        text_to_count += str(item)
            elif isinstance(content, dict):
                item_type = content.get("type")
                if item_type == "text":
                    text_to_count = str(content.get("text", ""))
                elif item_type == "image_url":
                    total_tokens += 280
                elif item_type == "input_audio":
                    total_tokens += 750
            else:
                text_to_count = str(content)

            if text_to_count.strip():
                # Tokenizzazione reale del testo tramite il modello caricato
                total_tokens += len(
                    self.cuore.tokenize(text_to_count.encode("utf-8", errors="ignore"))
                )
                
            return total_tokens
        except Exception as e:
            # Fallback di sicurezza per evitare crash durante la chirurgia dei token
            return int(len(str(content)) / 2.5)

    def _genera_pensiero(
        self,
        messages: List[Dict],
        response_format: Optional[Dict] = None,
        tools: Optional[List[Dict]] = None,
        override_brain: Optional[LlamaServerClient] = None,
        enable_streaming: bool = False,
        **kwargs,
    ) -> str:
        active_brain = override_brain if override_brain else self.cuore
        if not active_brain:
            return t("log.brain_silent_heart")

        # --- [FIX CRITICO] PARACADUTE JINJA TEMPLATE (QWEN/LLAMA3) ---
        # Assicura che ci sia sempre almeno un messaggio 'user' per evitare crash del server C++
        has_user = any(m.get("role") == "user" for m in messages)
        if not has_user:
            messages.append({"role": "user", "content": "Procedi."})

        # --- [NUOVO v15.0] SPECIALIST MODE ROUTING ---
        # Verifica se la modalità Specialist è attiva e se dobbiamo usarla
        model_config = self.guardian.get_model_selection_config() or {}
        specialist_enabled = model_config.get("specialist_mode_enabled", False)

        # Se Specialist è attivo E non stiamo forzando un cervello specifico (override_brain), usiamo la logica dedicata
        if specialist_enabled and not override_brain:
            return self._genera_pensiero_specialist(messages, response_format, **kwargs)

        # --- FLUSSO STANDARD (NARRATIVE BRAIN) ---

        # --- [NUOVO] SUPPORTO NATIVO SYSTEM PROMPT E THINKING (GEMMA 4) ---
        # [FIX CRITICO CACHE] L'iniezione di <|think|> è stata spostata in _build_anchor_prompt()
        # per garantire che l'hash del prompt sia identico tra warmup e generazione.
        # Qui non modifichiamo più il messaggio di sistema dinamicamente.
        pass

        # --- [NUOVO] PROTOCOLLO DELL'ANCORA UNIVERSALE (ANTI-CACHE THRASHING) ---
        # Se stiamo usando il modello principale (12B), il System Prompt DEVE essere sempre l'Ancora.
        # Se la richiesta contiene un System Prompt tecnico (es. Logic Gate), lo spostiamo nel messaggio User.
        if active_brain == self.narrative_brain and messages and messages[0].get("role") == "system":
            current_gdr_mode = kwargs.get("in_gdr_mode", getattr(self, "in_gdr_mode", False))
            true_anchor = self._build_anchor_prompt(in_gdr_mode=current_gdr_mode)
            
            # Confronto esatto. Se differiscono, significa che è un task tecnico in background.
            if messages[0]["content"] != true_anchor:
                technical_instruction = messages[0]["content"]
                messages[0]["content"] = true_anchor
                
                # Cerca il primo messaggio user per iniettare il mandato tecnico
                for msg in messages:
                    if msg.get("role") == "user":
                        original_content = msg["content"]
                        override_prefix = t("brain.technical_override_mandate")
                        override_suffix = t("brain.technical_override_end")
                        
                        if isinstance(original_content, str):
                            msg["content"] = f"{override_prefix}\n{technical_instruction}\n\n{override_suffix}\n{original_content}"
                        elif isinstance(original_content, list):
                            # Gestione multimodale (lista di dict)
                            text_injected = False
                            for item in original_content:
                                if item.get("type") == "text":
                                    item["text"] = f"{override_prefix}\n{technical_instruction}\n\n{override_suffix}\n{item['text']}"
                                    text_injected = True
                                    break
                            if not text_injected:
                                original_content.append({"type": "text", "text": f"{override_prefix}\n{technical_instruction}\n\n{override_suffix}"})
                        break
                self.logger.log(t("log.brain_universal_anchor_applied"), "SYSTEM")

        #[FIX CRITICO v124.5] USARE .copy() PER EVITARE MUTAZIONE GLOBALE
        params = (self.guardian.get_parameters_config() or {}).copy()
        params.update(kwargs)

        # --- [NUOVO] VERO PARALLELISMO ---
        # Sceglie il lucchetto in base al cervello che sta per usare
        current_lock = (
            self.labour_lock if active_brain == self.labour_brain else self.lock
        )

        with current_lock:
            try:
                # [FIX CRITICO] Aggiunti token di stop specifici per Gemma 3 e formati di chat comuni
                # [FIX BUG 3] Aggiunti <turn|> e <|turn> per fermare le allucinazioni di Gemma 3/4
                stop_tokens =["<end_of_turn>", "<eos>", "<|eot_id|>", "<|im_end|>", "user\n", "User:", "<turn|>", "<|turn>"]

                # --- [FIX CRITICO] LIMITE TOKEN FISSO E SICURO ---
                # Rimosso il calcolo dinamico che causava il troncamento a zero.
                # Impostiamo un limite fisso a 2048 per la chat standard, che previene l'overflow
                # dei 16K di contesto e impedisce all'LLM di generare all'infinito.
                raw_max = (
                    kwargs.get("max_tokens")
                    if kwargs.get("max_tokens") is not None
                    else params.get("max_tokens")
                )
                target_max_tokens = raw_max if raw_max is not None else 2048

                completion_kwargs = {
                    "messages": messages,
                    "temperature": float(
                        params.get("temperature")
                        if params.get("temperature") is not None
                        else 0.25
                    ),
                    "top_p": float(
                        params.get("top_p") if params.get("top_p") is not None else 0.95
                    ),
                    "top_k": int(
                        params.get("top_k") if params.get("top_k") is not None else 40
                    ),
                    "repeat_penalty": float(
                        params.get("repeat_penalty")
                        if params.get("repeat_penalty") is not None
                        else 1.1
                    ),
                    "max_tokens": int(target_max_tokens),
                    "stop": stop_tokens,
                }

                # --- [FIX CRITICO] SMART REASONING BUDGET ---
                if active_brain == self.narrative_brain:
                    if response_format and response_format.get("type") == "json_object":
                        completion_kwargs["reasoning_budget"] = 0
                    else:
                        budget = kwargs.get("reasoning_budget", 2048 if tools else 512)
                        completion_kwargs["reasoning_budget"] = budget
                    
                    # [FASE 2] Iniezione del callback di streaming solo per il server C++
                    if self.streaming_callback and enable_streaming:
                        completion_kwargs["streaming_callback"] = self.streaming_callback

                #[FIX DEEP DEBUG] Passaggio parametri di penalità per Anti-Eco
                if "presence_penalty" in params:
                    completion_kwargs["presence_penalty"] = float(
                        params["presence_penalty"]
                    )
                else:
                    completion_kwargs["presence_penalty"] = 0.0  # [FIX CRITICO MUTISMO] Azzerato. I modelli Instruct si bloccano con penalità attive.

                if "frequency_penalty" in params:
                    completion_kwargs["frequency_penalty"] = float(
                        params["frequency_penalty"]
                    )
                else:
                    completion_kwargs["frequency_penalty"] = 0.0  # [FIX CRITICO MUTISMO] Azzerato.

                # --- [FIX JSON STARVATION] SCUDO ANTI-PENALITÀ PER JSON ---
                # Se stiamo forzando un output JSON, le penalità di ripetizione distruggono i logit
                # delle chiavi JSON (che sono spesso ripetute o presenti nel prompt).
                # Disattiviamo brutalmente le penalità per garantire la generazione.
                if response_format and response_format.get("type") == "json_object":
                    completion_kwargs["repeat_penalty"] = 1.0
                    completion_kwargs["presence_penalty"] = 0.0
                    completion_kwargs["frequency_penalty"] = 0.0
                    self.logger.log("JSON Mode rilevato: Penalità azzerate per prevenire Starvation.", "DEBUG")

                # [FIX CRITICO] Abilitiamo la grammatica JSON nativa anche per Gemma 4.
                # Avendo impostato 'reasoning_budget = 0', non c'è più il rischio di deadlock sintattico.
                if response_format:
                    completion_kwargs["response_format"] = response_format

                # Iniezione nativa dei tools per Gemma 4 (Fase 1)
                if tools and self.is_gemma_4:
                    completion_kwargs["tools"] = tools

                # --- [FIX CRITICO SAFETENSORS/TURBOQUANT] ---
                # Se manca il nome del modello, llama-server rifiuta la richiesta con errore 400.
                # Lo popoliamo dinamicamente usando il nome del modello attivo o un fallback.
                if "model" not in completion_kwargs or not completion_kwargs["model"]:
                    completion_kwargs["model"] = getattr(self, "_active_model_name", "local-model") or "local-model"

                # --- [NUOVO v7.0] TELEMETRIA GOD TIER E N_KEEP ---
                # Calcolo n_keep se non è già stato fatto (l'Ancora è il primo messaggio)
                if (
                    self._cached_n_keep_static is None
                    and messages
                    and messages[0]["role"] == "system"
                ):
                    # add_bos=True garantisce che il token iniziale sia identico al warm-up
                    self._cached_n_keep_static = len(
                        active_brain.tokenize(
                            messages[0]["content"].encode("utf-8"), add_bos=True
                        )
                    )

                # NOTA: create_chat_completion non accetta n_keep direttamente.
                # La LlamaRAMCache gestisce l'ancoraggio tramite Prefix Matching automatico.
                # Manteniamo il calcolo di _cached_n_keep_static per debug e future implementazioni.

                start_time = time.time()
                response = active_brain.create_chat_completion(**completion_kwargs)
                end_time = time.time()

                message = response["choices"][0]["message"]
                content = message.get("content", "")
                if content is None:
                    content = ""
                content = content.strip()
                
                # --- [FIX CRITICO] ESTRAZIONE JSON CENTRALIZZATA E RIMOZIONE THINKING ---
                # Se era richiesto un JSON, puliamo l'output da pensieri e markdown per garantire il parsing.
                # Questo risolve il paradosso di Gemma 4 che si bloccava con la grammatica JSON attiva.
                if response_format and response_format.get("type") == "json_object":
                    clean_content = re.sub(r"<\|channel\|\>thought.*?\<channel\|\>", "", content, flags=re.IGNORECASE | re.DOTALL).strip()
                    clean_content = re.sub(r"<think>.*?</think>", "", clean_content, flags=re.IGNORECASE | re.DOTALL).strip()
                    
                    # --- [FIX CRITICO] GESTIONE TAG NON CHIUSI PER JSON ---
                    if "<think>" in clean_content.lower():
                        parts = re.split(r"<think>", clean_content, flags=re.IGNORECASE)
                        if len(parts) > 1:
                            # Cerchiamo la prima parentesi graffa aperta che indica l'inizio del JSON
                            json_start = parts[1].find("{")
                            if json_start != -1:
                                clean_content = parts[0] + parts[1][json_start:]
                            else:
                                clean_content = parts[0]
                                
                    clean_content = clean_content.replace("```json", "").replace("```", "").strip()
                    json_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", clean_content)
                    if json_match:
                        content = json_match.group(1)
                    else:
                        # Se non c'è JSON, restituiamo comunque il testo pulito per evitare di loggare i pensieri
                        content = clean_content
                
                # --- [SUPER LOGGER] SONDA GENERAZIONE LLM ---
                # Logghiamo solo se non è il Logic Gate (che ha già il suo log) per non spammare,
                # oppure logghiamo tutto se vogliamo il controllo totale. Logghiamo tutto.
                self.logger.super_log("LLM_GENERATION", {
                    "model_used": self._active_model_name,
                    "messages_array_sent": messages,
                    "tools_schema_sent": tools if tools else "Nessun tool nativo passato",
                    "raw_content_received": content,
                    "tool_calls_received": message.get("tool_calls", "Nessun tool call nativo")
                })
                # --------------------------------------------

                # ---[FIX CRITICO v128.1] INTERCETTAZIONE NATIVE TOOL CALLS ---
                # Se il 12B ha usato la sua capacità nativa, i parametri sono qui dentro, non nel 'content'.
                # Li estraiamo e li formattiamo come JSON Puro per farli leggere a chat.py.
                if "tool_calls" in message and message["tool_calls"]:
                    tool_call = message["tool_calls"][0]["function"]
                    t_name = tool_call.get("name", "")
                    t_args = tool_call.get("arguments", "{}")  # È già una stringa JSON

                    # Costruiamo il blocco JSON Puro che _extract_tool_command si aspetta
                    native_call_str = f'{{"name": "{t_name}", "parameters": {t_args}}}'

                    # Accodiamo il blocco al contenuto testuale
                    content = f"{content}\n{native_call_str}".strip()
                    self.logger.log(
                        t("log.brain_native_tool_intercepted", name=t_name),
                        "LOGIC",
                    )

                # --- ESTRAZIONE METRICHE ---
                tempo_totale = end_time - start_time
                usage = response.get("usage", {})
                
                # Supporto per formati OpenAI e llama.cpp nativi
                tokens_generati = usage.get("completion_tokens", usage.get("predicted_n", 0))
                eval_time_ms = usage.get("prompt_eval_time", usage.get("prompt_ms", 0))

                # Se prompt_eval_time è disponibile (in ms), lo usiamo, altrimenti usiamo un'euristica
                if eval_time_ms > 0:
                    eval_time_sec = eval_time_ms / 1000.0
                    if eval_time_sec < 0.2:
                        cache_status = t("brain.cache_hit_perfect_fast")
                    elif eval_time_sec < 3.0:
                        cache_status = t("brain.cache_partial_hit")
                    else:
                        cache_status = t("brain.cache_chaos")
                else:
                    # Euristica basata sul tempo totale se eval_time non è esposto
                    eval_time_sec = 0.0  # Assumiamo 0 per evitare divisioni per zero
                    cache_status = t("brain.cache_partial_hit") if tempo_totale < 5.0 else t("brain.cache_chaos")

                generation_time = tempo_totale - eval_time_sec
                if generation_time <= 0:
                    generation_time = 0.01  # Failsafe matematico anti-crash

                tps = tokens_generati / generation_time

                self.logger.log(
                    t(
                        "brain.performance_log",
                        ttft=f"{tempo_totale:.2f}",
                        tps=f"{tps:.2f}",
                        cache=cache_status,
                    )
                )

                return content
            except Exception as e:
                print(t("log.brain_internal_error", error=e))
                traceback.print_exc()
                # [FIX CRITICO] Solleviamo l'eccezione invece di restituire una stringa.
                # Questo permette a chat.py di intercettarla e avviare l'Auto-Healing
                # senza far pronunciare l'errore tecnico all'Avatar.
                raise RuntimeError(f"LLM Error: {e}")

    # --- [NUOVO v15.0] LOGICA SPECIALIST (STAFFETTA / KEEP-ALIVE) ---
    def _genera_pensiero_specialist(
        self, messages: List[Dict], response_format: Optional[Dict] = None, **kwargs
    ) -> str:
        """
        Gestisce la generazione quando la modalità Specialist è attiva.
        Implementa la logica Staffetta (Load/Unload) o Keep-Alive.
        """
        specialist_config = self.guardian.get_specialist_config()
        keep_loaded = specialist_config.get("keep_loaded", False)

        model_config = self.guardian.get_model_selection_config() or {}
        specialist_model_name = model_config.get("active_specialist_model", "")

        if not specialist_model_name:
            return t("log.brain_specialist_no_model")

        specialist_path = Path("models/specialist") / specialist_model_name

        # 1. Preparazione Prompt Specialist (01 + 02 + Custom)
        specialist_messages = self._prepare_specialist_messages(
            messages, specialist_config
        )

        # 2. Caricamento Modello (se necessario)
        if not self.is_specialist_mode:
            if not self.swap_to_specialist_mode(specialist_path):
                return t("log.brain_specialist_load_fail")

        # 3. Generazione (Pre-Processing + Output)
        try:
            # Qui usiamo self.cuore che ora punta allo Specialist
            # Nota: Lo Specialist potrebbe avere parametri diversi, usiamo quelli standard per ora
            # o potremmo caricarne di specifici se necessario.

            # Fase di Pre-Processing (Pensiero di Verifica) - Opzionale ma consigliata
            # Per ora facciamo una generazione diretta con i prompt potenziati

            params = (self.guardian.get_parameters_config() or {}).copy()
            params.update(kwargs)

            with self.lock:
                response = self.cuore.create_chat_completion(
                    messages=specialist_messages,
                    temperature=0.3,  # Più preciso per task tecnici
                    max_tokens=params.get("max_tokens", 8192),
                    # [FIX BUG 3] Aggiunti <turn|> e <|turn> per fermare le allucinazioni di Gemma 3/4 nello Specialist
                    stop=["<end_of_turn>", "<eos>", "<|eot_id|>", "<|im_end|>", "user\n", "User:", "<turn|>", "<|turn>"],
                    response_format=response_format,
                )
                content = response["choices"][0]["message"]["content"].strip()

        except Exception as e:
            self.logger.error(t("brain.specialist_error_prefix", error=e))
            content = t("brain.specialist_error_prefix", error=e)

        # 4. Gestione Post-Generazione (Staffetta vs Keep-Alive)
        if not keep_loaded:
            self.logger.log(t("brain.specialist_keep_alive_off"), "SYSTEM")
            self.restore_narrative_mode()
        else:
            self.logger.log(t("brain.specialist_keep_alive_on"), "SYSTEM")

        return content

    def _prepare_specialist_messages(
        self, original_messages: List[Dict], config: Dict
    ) -> List[Dict]:
        """
        Costruisce la catena di messaggi per lo Specialist includendo i prompt di verifica.
        """
        # 1. Prompt di Base (01 e 02)
        base_prompts = [t("specialist.prompt_1"), t("specialist.prompt_2")]

        # 2. Prompt Custom Utente (Dal JSON dell'Avatar)
        custom_prompts = self.soul_data.get("specialist_prompts", [])

        # Uniamo tutto in un unico System Prompt potente
        full_system_content = f"{t('log.brain_specialist_protocol_header')}\n"
        full_system_content += "\n".join(base_prompts) + "\n"
        if custom_prompts:
            full_system_content += f"\n{t('log.brain_user_rules_header')}\n"
            full_system_content += "\n".join(custom_prompts) + "\n"

        # 3. Costruzione Lista Messaggi
        new_messages = [{"role": "system", "content": full_system_content}]

        # Aggiungiamo la storia della chat (original_messages)
        # Nota: original_messages[0] è il system prompt narrativo, che qui sostituiamo o accodiamo?
        # Per lo Specialist, il prompt narrativo (identità) è meno importante della competenza tecnica.
        # Tuttavia, se contiene info su tool o contesto, serve.
        # Strategia: Manteniamo il system prompt originale come "Context Info" user message

        if original_messages and original_messages[0]["role"] == "system":
            context_msg = f"{t('log.brain_context_info_header')}\n{original_messages[0]['content']}"
            new_messages.append({"role": "user", "content": context_msg})
            # Aggiungiamo il resto della storia
            new_messages.extend(original_messages[1:])
        else:
            new_messages.extend(original_messages)

        return new_messages

    # ---[NUOVO] LOGIC GATE UNIFICATO ---
    def valuta_logic_gate(self, user_input: str, tools_manifest: str, lang: str = "it", error_feedback: str = None) -> Dict[str, Any]:
        """
        Interroga il modello principale a Temperatura 0.0 per decidere se usare un tool,
        scrivere codice Python, o non fare nulla.
        """
        self.logger.log(t("chat.log_logic_gate_eval"), "LOGIC")
        prompt_template = self._get_internal_prompt("logic_gate")
        
        # --- [FIX CRITICO CACHE] SPLIT SYSTEM/USER PER IL LOGIC GATE ---
        # Separiamo la parte statica (il manifesto dei tool) dalla parte dinamica (l'input utente).
        # Questo permette a llama.cpp di cachare i ~800 token del manifesto in un ramo dedicato.
        parts = prompt_template.split("INPUT UTENTE:")
        if len(parts) == 2:
            system_part = parts[0].strip()
            user_part = "INPUT UTENTE:" + parts[1]
        else:
            # Fallback di sicurezza se il prompt cambia
            system_part = prompt_template
            user_part = f"INPUT UTENTE: \"{{{{ user_input }}}}\"{{{{ error_feedback }}}}"

        system_prompt = self._safe_replace(system_part, "tool_list", tools_manifest)
        user_prompt = self._safe_replace(user_part, "user_input", user_input)
        
        error_str = f"\n\n[ERRORE PRECEDENTE DA CORREGGERE]:\n{error_feedback}" if error_feedback else ""
        user_prompt = self._safe_replace(user_prompt, "error_feedback", error_str)

        # Il Logic Gate DEVE essere freddo e tecnico.
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # --- [FIX CRITICO] GABBIA MATEMATICA E CHAIN-OF-THOUGHT PER IL 270M ---
        # 1. Estraiamo i nomi esatti dei tool dal manifesto per impedire allucinazioni (Enum Enforcing)
        valid_tool_names = ["", "none", "nulla"]
        try:
            manifest_list = json.loads(tools_manifest)
            for tool in manifest_list:
                if "name" in tool:
                    valid_tool_names.append(tool["name"])
        except Exception as e:
            self.logger.error(f"Errore parsing manifest per Enum Logic Gate: {e}")

        # 2. Reintroduciamo il 'ragionamento' obbligatorio. I modelli piccoli (270M) 
        # falliscono miseramente se costretti a dare una risposta secca senza prima "pensare".
        schema = {
            "type": "object",
            "properties": {
                "ragionamento": {"type": "string", "description": "Spiega brevemente perché hai scelto questa azione."},
                "action_type": {"type": "string", "enum":["tool", "agentic_loop", "vision_descriptive", "vision_operative", "none"]},
                "tool_name": {"type": "string", "enum": valid_tool_names},
                "parameters": {"type": "object"},
                "python_code": {"type": "string"},
                "pip_dependencies": {"type": "array", "items": {"type": "string"}}
            },
            "required":["ragionamento", "action_type"]
        }

        # --- [OTTIMIZZAZIONE V-SPEED] ESECUZIONE FORZATA SUL MODELLO PRINCIPALE ---
        # Il modello 270M è stato deprecato per questo task a causa di gravi allucinazioni JSON.
        # Usiamo sempre il modello principale (12B/8B) sfruttando il Continuous Batching del server C++.
        response_str = self._genera_pensiero(
            messages,
            temperature=0.0,
            max_tokens=1024, # [FIX CRITICO] Aumentato per permettere il Reasoning Channel di Gemma 4
            reasoning_budget=512, # [FIX CRITICO] Budget esplicito per evitare il blocco
            response_format={"type": "json_object", "schema": schema}
        )

        try:
            # --- PURIFICAZIONE ANTI-THINK E SCUDO JSON ---
            clean_str = re.sub(r"<think>.*?</think>", "", response_str, flags=re.IGNORECASE | re.DOTALL).strip()
            clean_str = clean_str.replace("```json", "").replace("```", "").strip()
            
            # Regex robusta: cerca dal primo '{' all'ultimo '}' ignorando testo spazzatura prima o dopo
            json_match = re.search(r"(\{.*\})", clean_str, re.DOTALL)
            if json_match:
                clean_str = json_match.group(1)
            else:
                # Fallback se l'LLM non ha generato alcuna parentesi graffa
                raise ValueError("Nessun oggetto JSON rilevato nella risposta.")
                
            parsed_json = json.loads(clean_str)
            
            # --- [SUPER LOGGER] SONDA LOGIC GATE ---
            self.logger.super_log("LOGIC_GATE_EVALUATION", {
                "user_input": user_input,
                "tools_manifest_provided": tools_manifest,
                "prompt_sent": system_prompt + "\n" + user_prompt,
                "raw_llm_response": response_str,
                "parsed_decision": parsed_json
            })
            # --------------------------------------
            
            return parsed_json
        except Exception as e:
            self.logger.error(f"Errore parsing Logic Gate: {e} | Raw: {response_str[:50]}")
            self.logger.super_log("LOGIC_GATE_CRASH", {
                "error": str(e),
                "raw_response": response_str
            })
            return {"action_type": "none"}

    # ---[AGGIORNATO v126.0] PENSIERO REGISTA (CON INIEZIONE MANIFESTO) ---
    def pensa_query_pulita(
        self, user_input: str, tools_manifest: str, lang: str = "it"
    ) -> str:
        """
        Usa il Regista per identificare il tool corretto dal manifesto.
        """
        self.logger.log(t("log.brain_rpg_intent"), "LOGIC")

        # --- [FIX CRITICO] PUNTATORE CORRETTO ---
        # Usa _get_internal_prompt per pescare il prompt JSON blindato, non quello vecchio.
        prompt_template = self._get_internal_prompt("regista_query_pulita")
        
        # --- [FIX CRITICO CACHE] SPLIT SYSTEM/USER PER IL REGISTA ---
        parts = prompt_template.split("INPUT UTENTE:")
        if len(parts) == 2:
            system_part = parts[0].strip()
            user_part = "INPUT UTENTE:" + parts[1]
        else:
            system_part = prompt_template
            user_part = f"INPUT UTENTE: \"{{{{ user_input }}}}\""

        system_prompt = self._safe_replace(system_part, "tool_list", tools_manifest)
        user_prompt = self._safe_replace(user_part, "user_input", user_input)

        # Questa è una chiamata tecnica "pura": niente storia, niente DNA.
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # ---[FIX CRITICO] GABBIA MATEMATICA (ENUM ENFORCING) ---
        # Estraiamo i nomi esatti dei tool dal manifesto per impedire allucinazioni.
        valid_tool_names = ["NULLA"]
        try:
            manifest_list = json.loads(tools_manifest)
            for tool in manifest_list:
                if "name" in tool:
                    valid_tool_names.append(tool["name"])
        except Exception as e:
            self.logger.error(f"Errore parsing manifest per Enum: {e}")

        # --- [FIX CRITICO] RIPRISTINO CHAIN OF THOUGHT ---
        # Obblighiamo l'LLM a ragionare prima di scegliere, per evitare scelte casuali.
        # ---[LEGGE 3] ESTRAZIONE DINAMICA NOMI TOOL PER ENUM ---
        try:
            manifest_list = json.loads(tools_manifest)
            tool_names =[t_item.get("name") for t_item in manifest_list if isinstance(t_item, dict) and "name" in t_item]
        except:
            tool_names =[]
        if "NULLA" not in tool_names:
            tool_names.append("NULLA")

        schema = {
            "type": "object",
            "properties": {
                "ragionamento": {"type": "string"},
                "tool": {
                    "type": "string",
                    "enum": tool_names
                }
            },
            "required":["ragionamento", "tool"]
        }

        # Usiamo il 12B (Regista) per questa decisione critica
        response_str = self._genera_pensiero(
            messages, 
            temperature=0.0, # Zero assoluto per massima precisione
            max_tokens=1024, # [FIX CRITICO] Aumentato per permettere il Reasoning Channel di Gemma 4
            reasoning_budget=512, # [FIX CRITICO] Budget esplicito per evitare il blocco
            response_format={"type": "json_object", "schema": schema}
        )

        if not response_str or not response_str.strip():
            self.logger.log("[DISPATCHER] Risposta vuota dall'LLM. Fallback a NULLA.", "WARNING")
            return "NULLA"

        try:
            # Pulizia markdown JSON
            clean_str = response_str.replace("```json", "").replace("```", "").strip()
            json_match = re.search(r"(\{[\s\S]*\})", clean_str)
            if json_match:
                clean_str = json_match.group(1)
                
            parsed = json.loads(clean_str)
            tool_name = parsed.get("tool", "NULLA").strip()
            
            if "NULLA" in tool_name.upper():
                return "NULLA"
                
            return tool_name
        except Exception as e:
            self.logger.error(f"Errore parsing JSON Regista: {e} | Raw: {response_str[:50]}")
            return "NULLA"

    def _dict_to_functiongemma_str(self, obj: Any) -> str:
        """Converte un oggetto Python nella sintassi proprietaria di FunctionGemma (senza virgolette, con tag <escape>)."""
        if isinstance(obj, dict):
            items = []
            for k, v in obj.items():
                items.append(f"{k}:{self._dict_to_functiongemma_str(v)}")
            return "{" + ",".join(items) + "}"
        elif isinstance(obj, list):
            items = [self._dict_to_functiongemma_str(v) for v in obj]
            return "[" + ",".join(items) + "]"
        elif isinstance(obj, str):
            return f"<escape>{obj}<escape>"
        elif isinstance(obj, bool):
            return "true" if obj else "false"
        elif obj is None:
            return "null"
        else:
            return str(obj)

    def _format_functiongemma_schema(self, tools_schema: List[Dict]) -> str:
        """Converte lo schema JSON nel formato nativo di FunctionGemma (Gemma 3 o Gemma 4)."""
        declarations =[]
        for tool in tools_schema:
            func = tool.get("function", {})
            name = func.get("name", "")
            desc = func.get("description", "")
            params = func.get("parameters", {})

            desc_escaped = f"<escape>{desc}<escape>" if desc else ""
            params_str = self._dict_to_functiongemma_str(params)

            if self.is_labour_gemma_4:
                # Sintassi nativa Gemma 4
                declaration = f"<|tool|>declaration:{name}{{description:{desc_escaped},parameters:{params_str}}}<tool|>"
            else:
                # Sintassi nativa Gemma 3
                declaration = f"<start_function_declaration>declaration:{name}{{description:{desc_escaped},parameters:{params_str}}}<end_function_declaration>"
            
            declarations.append(declaration)

        return "\n".join(declarations)

    # ---[AGGIORNATO v125.2] PENSIERO TECNICO (FUNCTION GEMMA 270M - JIT SCHEMA) ---
    def pensa_tag_funzione(
        self, clean_query: str, tools_schema: List[Dict], retry_error: str = None
    ) -> Optional[str]:
        """
        Usa il Modello Principale per generare i parametri del tool.
        [AGGIORNATO] Supporto nativo per Gemma 4 Tool Calling via API.
        """
        if not self.cuore:
            self.logger.log(t("log.brain_labour_no_tag"), "WARNING")
            return None

        self.logger.log(t("log.brain_labour_tag_gen", query=clean_query), "LOGIC")

        if self.is_gemma_4:
            # --- GEMMA 4 NATIVE TOOL CALLING ---
            # Sfruttiamo l'API nativa di llama-server che formatta i token automaticamente
            messages = [{"role": "user", "content": clean_query}]
            if retry_error:
                messages[0]["content"] += f"\n\nWARNING: Your previous attempt generated this syntax error: '{retry_error}'. Fix the syntax and try again."
            
            # Se c'è un solo tool, forziamo il modello a usarlo
            tool_name = tools_schema[0].get("function", {}).get("name") if len(tools_schema) == 1 else None
            tool_choice = {"type": "function", "function": {"name": tool_name}} if tool_name else "auto"

            with self.lock:
                try:
                    response = self.cuore.create_chat_completion(
                        messages=messages,
                        tools=tools_schema,
                        tool_choice=tool_choice,
                        temperature=0.0,
                        max_tokens=1024  #[FIX] Aumentato per permettere il Thinking
                    )
                    
                    message = response["choices"][0]["message"]
                    if "tool_calls" in message and message["tool_calls"]:
                        tool_call = message["tool_calls"][0]["function"]
                        t_name = tool_call.get("name", "")
                        t_args = tool_call.get("arguments", "{}")
                        
                        # Restituiamo il formato JSON Puro che l'Executor sa già parsare
                        return f'{{"name": "{t_name}", "parameters": {t_args}}}'
                    else:
                        self.logger.warning("Gemma 4 Labour non ha restituito un tool_call nativo.")
                        return None
                except Exception as e:
                    self.logger.error(f"Errore Gemma 4 Labour: {e}")
                    return None
        else:
            # --- GEMMA 3 / FUNCTION GEMMA LEGACY ---
            # Serializzazione schema tool nel formato nativo di FunctionGemma
            tools_str = self._format_functiongemma_schema(tools_schema)

            # ---[NUOVO v128.0] GUINZAGLIO CORTO (PROMPT IMPERATIVO NATIVO) ---
            if len(tools_schema) == 1:
                tool_name = tools_schema[0].get("function", {}).get("name", "this tool")
                essential_system_instruction = f"You are a model that can do function calling with the following functions. You MUST use the function '{tool_name}' to fulfill the request. If required parameters are missing from the user query, invent reasonable default values."
            else:
                essential_system_instruction = "You are a model that can do function calling with the following functions. You can use one of them if necessary. If required parameters are missing, invent reasonable default values."

            # ---[NUOVO v128.0] AUTO-CORREZIONE SINTATTICA ---
            if retry_error:
                retry_msg = f"WARNING: Your previous attempt generated this syntax error: '{retry_error}'. Fix the syntax and try again."
                clean_query = f"{clean_query}\n\n{retry_msg}"

            prompt_template = self._get_internal_prompt("tag_funzione")

            #[FIX CRITICO A0006] Rimosso il replace con 'developer'. FunctionGemma VUOLE il ruolo 'user'.
            raw_prompt = self._safe_replace(
                prompt_template,
                "essential_system_instruction",
                essential_system_instruction,
            )
            raw_prompt = self._safe_replace(raw_prompt, "tools_str", tools_str)
            raw_prompt = self._safe_replace(raw_prompt, "clean_query", clean_query)

            # ---[FIX CRITICO A0006] PRIMING DEL MODELLO (PREFILLING) ---
            # Forziamo il modello a iniziare la risposta con il tag corretto.
            # Questo azzera le allucinazioni iniziali.
            if not raw_prompt.endswith("<start_function_call>"):
                raw_prompt += "<start_function_call>"

            end_tag = "<end_function_call>" # [FIX] Definizione mancante
            with self.lock:
                try:
                    # Chiamata diretta a create_completion (non chat) per controllo totale
                    response = self.cuore.create_completion(
                        prompt=raw_prompt,
                        temperature=0.0,  # Zero assoluto per sintassi perfetta
                        max_tokens=2048,  # [FIX] Aumentato per permettere il Thinking
                        # [FIX BUG 3] Aggiunti <turn|> e <|turn> per fermare le allucinazioni di Gemma 3/4 nel Tool Calling
                        stop=[
                            end_tag,
                            "<end_of_turn>",
                            "<eos>", 
                            "<|eot_id|>", 
                            "<|im_end|>", 
                            "user\n", 
                            "User:", 
                            "<turn|>", 
                            "<|turn>"
                        ],  # Fermiamo il modello ESATTAMENTE alla fine del tag
                        echo=False,
                    )

                    # Poiché abbiamo forzato l'inizio con <start_function_call> e echo=False,
                    # il testo restituito conterrà solo il contenuto interno (es. call:move_mouse{x:100})
                    inner_content = response["choices"][0]["text"].strip()

                    # Ricostruiamo il tag completo e perfetto per l'Executor
                    content = f"<start_function_call>{inner_content}<end_function_call>"

                    return content

                except Exception as e:
                    self.logger.error(t("log.brain_labour_error", error=e))
                    return None

    def _carica_lista_intent_filtrata(self) -> str:
        """
        Carica la lista delle emozioni valide (Lista Sacra v27.40).
        [FIX CRITICO] Restituisce una stringa piatta separata da virgole per evitare che l'LLM
        la interpreti come una checklist da iterare nel blocco <think>.
        """
        try:
            if not self.valid_emotions:
                return t("log.brain_no_emotions")

            self.emotion_id_map.clear()
            
            # Popoliamo la mappa per retrocompatibilità
            for idx, emotion in enumerate(self.valid_emotions):
                self.emotion_id_map[str(idx)] = emotion

            # Restituiamo solo i nomi in inglese, separati da virgola
            result = ", ".join(self.valid_emotions)

            # Scrittura del copione su file per l'utente
            try:
                log_path = Path(__file__).parent.parent / "logs" / "visual_reaction.md"
                log_path.parent.mkdir(exist_ok=True)
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write("# COPIONE REAZIONI VISIVE (INTENT)\n\n")
                    f.write("Questo file contiene la mappatura esatta tra gli ID numerici e le emozioni che l'Anima può provare.\nL'LLM sceglierà il numero, e il sistema lo tradurrà nel video corrispondente.\n\n")
                    f.write(result)
            except Exception as e:
                self.logger.error(f"Errore salvataggio visual_reaction.md: {e}")

            print(t("log.brain_intent_dynamic_loaded", count=len(self.valid_emotions)))
            return result

        except Exception as e:
            self.logger.log(t("log.brain_intent_load_error", error=e))
            return t("log.brain_load_intents_error")

    # --- NUOVO HELPER: SOSTITUZIONE SICURA TAG (v27.42 - Regex Injection Fix) ---
    def _safe_replace(self, text: str, key: str, value: str) -> str:
        """
        Sostituisce un tag Jinja2 {{key}} gestendo spazi variabili.
        Es: {{key}}, {{ key }}, {{  key  }} vengono tutti sostituiti.

        FIX v27.42: Usa una funzione lambda per il replacement per evitare che
        re.sub interpreti i backslash nel 'value' come escape sequence.
        """
        if not text:
            return ""
        # Pattern: {{ seguito da spazi opzionali, la chiave, spazi opzionali, }}
        pattern = r"\{\{\s*" + re.escape(key) + r"\s*\}\}"

        # FIX: lambda m: str(value) tratta il valore come stringa letterale
        return re.sub(pattern, lambda m: str(value), text, flags=re.IGNORECASE)

    def _replace_all_name_variants(self, text: str, pg_name: str) -> str:
        """[NUOVO v7.0] Sostituisce tutte le possibili varianti del tag nome utente.
        Previene l'Amnesia Nominale causata da tag discordanti nei JSON.
        """
        if not text:
            return ""
            
        # --- [FIX CRITICO] RISOLUZIONE PARADOSSO LOGICO ---
        # Evita che la regola anti-placeholder diventi "Non scrivere MAI Samael... scrivi Samael",
        # mandando in loop infinito i modelli di ragionamento (Gemma 4 / Qwen).
        text = re.sub(r"Non scrivere MAI `.*?` o `.*?` nella tua risposta\.", "Non usare mai segnaposto generici nella tua risposta.", text)
        
        text = self._safe_replace(text, "pg_name", pg_name)
        text = self._safe_replace(text, "nome_pg", pg_name)
        text = self._safe_replace(text, "NOME_PG", pg_name)
        text = self._safe_replace(text, "name", pg_name) # [FIX BUG 02] Aggiunta variante 'name'
        return text

    def update_pg_name(self, new_name: str):
        """[NUOVO v7.0] Aggiorna il nome del Creatore e forza il ri-ancoraggio della cache.
        Previene il Cache Miss garantito se l'utente cambia nome a runtime.
        """
        if self.pg_name != new_name:
            self.logger.log(
                t("log.brain_pg_name_update", old=self.pg_name, new=new_name), "SYSTEM"
            )
            self.pg_name = new_name
            self.clear_ram_cache()

    def update_avatar_name(self, new_name: str):
        """[FIX BUG 1] Aggiorna il nome dell'avatar attivo per il GDR."""
        self.active_avatar_name = new_name

    def _format_game_rules(self, game_state: Dict[str, Any], pg_name: str) -> str:
        """
        Formatta il prompt delle regole del gioco se attivo.
        Supporta 'truth_or_dare' e 'never_have_i_ever'.
        """
        if not game_state or not game_state.get("active"):
            return ""

        game_type = game_state.get("type", "truth_or_dare")

        prompt_template = ""
        if game_type == "truth_or_dare":
            prompt_template = self._get_gdr_law("regole_obbligo_verita")
        elif game_type == "never_have_i_ever":
            prompt_template = self._get_gdr_law("regole_non_ho_mai")

        if not prompt_template:
            return ""

        scores = game_state.get("scores", {})
        scores_list = []
        for k, v in scores.items():
            if game_type == "never_have_i_ever":
                scores_list.append(t("brain.game_scores_drink", name=k, value=v))
            else:
                scores_list.append(t("brain.game_scores_points", name=k, value=v))

        scores_str = ", ".join(scores_list)

        # --- NUOVO: GENERAZIONE DINAMICA DEL CERCHIO (v27.26) ---
        participants = list(scores.keys())
        if participants:
            seating_order = " -> ".join(participants) + t(
                "brain.game_return_to", name=participants[0]
            )
        else:
            seating_order = t("log.brain_no_participants")

        prompt = self._safe_replace(prompt_template, "game_scores", scores_str)
        prompt = self._safe_replace(
            prompt,
            "current_turn_player",
            game_state.get("turn_player", t("brain.unknown_m")),
        )
        prompt = self._safe_replace(prompt, "seating_order", seating_order)

        return self._replace_all_name_variants(
            prompt, pg_name
        )  # [FIX v7.5] Sostituzione universale

    # --- NUOVO HELPER: DE-SOGGETTIVAZIONE INPUT (v27.35 - HYBRID-AI LOCK) ---
    def _de_subjectivize_input(self, user_input: str, pg_name: str) -> str:
        """
        Trasforma i pronomi possessivi e personali dell'utente in riferimenti oggettivi.
        Questo impedisce ai PNG di appropriarsi delle azioni del PG.
        """
        text = user_input
        # Mappa di sostituzione (Case Insensitive) - POTENZIATA
        replacements = {
            # Possessivi Singolari
            r"\b(il )?mio\b": t("brain.subjectivize.of_pg", name=pg_name),
            r"\b(la )?mia\b": t("brain.subjectivize.of_pg", name=pg_name),
            r"\b(i )?miei\b": t("brain.subjectivize.of_pg", name=pg_name),
            r"\b(le )?mie\b": t("brain.subjectivize.of_pg", name=pg_name),
            # Azioni Specifiche (Action Theft Prevention)
            r"\bsulle mie\b": t("brain.subjectivize.on_legs", name=pg_name),
            r"\bcontro il mio\b": t("brain.subjectivize.against_body", name=pg_name),
            r"\bcontro la mia\b": t("brain.subjectivize.against_skin", name=pg_name),
            # Verbi in prima persona (Soggetto Implicito)
            r"\b(io )?ho deciso\b": t("brain.subjectivize.pg_decided", name=pg_name),
            r"\b(io )?ho fatto\b": t("brain.subjectivize.pg_did", name=pg_name),
            r"\b(io )?sono\b": t("brain.subjectivize.pg_is", name=pg_name),
            r"\b(io )?voglio\b": t("brain.subjectivize.pg_wants", name=pg_name),
            # Interazioni Dirette (Targeting)
            r"\bti prendo\b": t("brain.subjectivize.take_target"),
            r"\bti bacio\b": t("brain.subjectivize.kiss_target"),
            r"\bti guardo\b": t("brain.subjectivize.look_target"),
            r"\bti tocco\b": t("brain.subjectivize.touch_target"),
        }

        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text

    # --- NUOVO HELPER: RILEVAMENTO BERSAGLIO E PROPRIETÀ (v27.35 - TARGET LOCK) ---
    def _detect_interaction_target(
        self, user_input: str, current_png_name: str, all_present_names: List[str]
    ) -> str:
        """
        Analizza l'input per capire se il Creatore sta interagendo con il PNG corrente o con altri.
        Restituisce un comando di esclusione violento se il bersaglio è un altro PNG.
        """
        input_lower = user_input.lower()
        current_lower = current_png_name.lower()

        # Trova tutti i nomi menzionati nell'input
        mentioned_names = [
            name for name in all_present_names if name.lower() in input_lower
        ]

        # Se non viene menzionato nessuno, l'azione è probabilmente rivolta a tutti o al gruppo
        # O è una continuazione dell'interazione precedente.
        if not mentioned_names:
            return ""

        # Se il PNG corrente è menzionato, è un bersaglio (o uno dei bersagli)
        if current_lower in [n.lower() for n in mentioned_names]:
            return t(
                "brain.interaction_reality_png",
                pg_name="{{pg_name}}",
                png_name=current_png_name,
            )

        # Se vengono menzionati altri nomi ma NON il PNG corrente
        other_targets = [n for n in mentioned_names if n.lower() != current_lower]
        if other_targets:
            targets_str = ", ".join(other_targets)
            return t(
                "brain.interaction_barrier_png",
                pg_name="{{pg_name}}",
                targets=targets_str,
                png_name=current_png_name,
            )

        return ""

    # --- NUOVO HELPER: ESTRAZIONE GENERE (v27.35 - GENDER PROTOCOL) ---
    def _extract_gender(self, json_text: str) -> str:
        """Estrae il genere dal testo JSON (anche parziale) usando Regex o Parsing."""
        try:
            # Regex per robustezza su stringhe parziali
            match = re.search(r'"genere":\s*"([^"]+)"', json_text, re.IGNORECASE)
            if match:
                return match.group(1)
            # Fallback su parsing JSON completo
            data = json.loads(json_text)
            return data.get("dati_anagrafici", {}).get("genere", t("brain.unknown_m"))
        except:
            return t("brain.unknown_m")

    # --- NUOVO HELPER: ISTRUZIONE LINGUA (v27.44) ---
    def _get_language_instruction(self, lang_code: str) -> str:
        """Genera l'istruzione imperativa per la lingua."""
        lang_map = {
            "it": t("brain.lang_names.it"),
            "en": t("brain.lang_names.en"),
            "es": t("brain.lang_names.es"),
            "fr": t("brain.lang_names.fr"),
            "de": t("brain.lang_names.de"),
            "jp": t("brain.lang_names.jp"),
        }
        lang_name = lang_map.get(lang_code.lower(), t("brain.lang_names.it"))
        return t("brain.language_protocol", lang=lang_name)

    # ---[AGGIORNATO v108.0] ROUTER NEURALE POTENZIATO (TOOL SELECTION) ---
    def _router_neurale(
        self, user_input: str, tools_manifest: List[Dict]
    ) -> Dict[str, Any]:
        """
        Classifica l'input e seleziona il tool più appropriato dalla lista dinamica.
        Restituisce un dizionario con 'is_technical', 'tool_name' e 'reason'.
        """
        self.logger.log(t("log.brain_router_activation"), "ROUTER")

        # Costruisce la lista dei tool disponibili per il prompt del router
        tools_desc = []
        for t in tools_manifest:
            category = t.get("category", "tool")
            prefix = "[SKILL]" if category == "skill" else "[TOOL]"

            # [FIX v108.4] Iniezione triggers nel prompt del router per migliorare la precisione
            triggers = t.get("triggers", [])
            triggers_str = f" (Keywords: {', '.join(triggers)})" if triggers else ""

            tools_desc.append(
                f"- {prefix} {t['name']}: {t['description']}{triggers_str}"
            )
        tools_block = "\n".join(tools_desc)

        prompt_template = self._get_internal_prompt("router_neurale")
        prompt = self._safe_replace(prompt_template, "user_input", user_input)
        prompt = self._safe_replace(prompt, "tools_block", tools_block)

        messages = [{"role": "user", "content": prompt}]

        schema = {
            "type": "object",
            "properties": {
                "is_technical": {"type": "boolean"},
                "tool_name": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["is_technical", "tool_name", "reason"],
        }

        try:
            response_str = self._genera_pensiero(
                messages,
                temperature=0.0,
                response_format={"type": "json_object", "schema": schema},
            )
            result = json.loads(response_str)

            is_tech = result.get("is_technical", False)
            tool_name = result.get("tool_name")
            reason = result.get("reason", t("log.care_no_reason"))

            type_label = (
                t("brain.router_type_tech")
                if is_tech
                else t("brain.router_type_narrative")
            )
            self.logger.log(
                t(
                    "brain.router_decision",
                    type=type_label,
                    tool=tool_name,
                    reason=reason,
                ),
                "ROUTER",
            )
            return result
        except Exception as e:
            self.logger.error(t("log.router_error", error=e))
            return {
                "is_technical": False,
                "tool_name": None,
                "reason": t("system.error", error=e),
            }

    # ---[NUOVO v108.0] PENSIERO TECNICO (GBNF ENFORCED) ---
    def pensa_azione_tecnica(
        self, user_input: str, tool_name: str, tools_manifest: List[Dict]
    ) -> str:
        """
        Genera il comando JSON per un tool specifico usando una grammatica GBNF rigorosa.
        """
        self.logger.log(t("log.brain_action_gbnf", tool=tool_name), "ACTION")

        # Trova la definizione del tool
        tool_def = next((t for t in tools_manifest if t["name"] == tool_name), None)
        if not tool_def:
            return t("brain.action_error_tool_not_found", name=tool_name)

        grammar_str = tool_def.get("gbnf_grammar")
        if not grammar_str:
            return t("brain.action_error_grammar_missing", name=tool_name)

        # Prompt Tecnico Puro (Senza personalità)
        prompt_template = self._get_internal_prompt("azione_tecnica")
        prompt = self._safe_replace(prompt_template, "tool_name", tool_name)
        prompt = self._safe_replace(prompt, "tool_desc", tool_def["description"])
        prompt = self._safe_replace(
            prompt, "tool_params", json.dumps(tool_def["parameters"])
        )
        prompt = self._safe_replace(prompt, "user_input", user_input)

        # [FIX LIVELLO 2] Implementato Cache Sandwich per i tool tecnici.
        # Usiamo l'Ancora di Diamante per preservare la cache del System Prompt.
        ancora_text = self._build_anchor_prompt(in_gdr_mode=False)
        messages = [
            {"role": "system", "content": ancora_text},
            {"role": "user", "content": prompt}
        ]

        # Carica la grammatica GBNF
        try:
            # Generazione a temperatura 0 con grammatica (passata come stringa al server C++)
            with self.lock:
                response = self.cuore.create_chat_completion(
                    messages=messages, temperature=0.0, grammar=grammar_str, max_tokens=4096
                )
                content = response["choices"][0]["message"]["content"].strip()

                # Avvolgi nel tag <tool_call> per il parser di chat.py
                return t(
                    "brain.action_tool_call_format", name=tool_name, params=content
                )

        except Exception as e:
            self.logger.error(t("log.brain_action_error", error=e))
            return t("log.brain_action_error", error=e)

    # --- [NUOVO v129.0] REACT LOOP (AUTO-CORREZIONE) ---
    def pensa_autocorrezione_tool(self, tool_call: str, error_msg: str, lang: str = "it") -> str:
        """
        Analizza un errore restituito da un tool e genera una nuova chiamata corretta.
        """
        self.logger.log(t("log.brain_react_start"), "LOGIC")
        
        prompt_template = self._get_internal_prompt("autocorrezione_tool")
        prompt = self._safe_replace(prompt_template, "tool_call", tool_call)
        prompt = self._safe_replace(prompt, "error_msg", error_msg)
        prompt += self._get_language_instruction(lang)
        
        messages =[{"role": "user", "content": prompt}]
        
        # Temperatura bassissima per massima precisione sintattica
        return self._genera_pensiero(messages, temperature=0.1, max_tokens=2048)

    def _crea_vangelo_onnicomprensivo(
        self,
        memory_manager: "MemoryManager",
        user_input: str,
        pg_name: str,
        contesto_aggiuntivo: Optional[str] = None,
        contesto_ambientale: Optional[str] = None,
        game_state: Optional[Dict[str, Any]] = None,
        narrative_buffer: str = "",
        dati_biometrici: str = "",
        pg_gender: str = "Male",
        lang: str = "it",
        system_paths: Dict[str, str] = None,
        stato_emotivo: str = "",
        core_memories: List[str] = None,
        context_name: str = t("brain.context_standard"),
        use_rag: bool = True,
        heart_state_dict: dict = None,
        in_gdr_mode: bool = False,
        dynamic_profile: str = "",
        gossip_block: str = "",
        super_ricordo_text: str = "", # [FIX CRITICO] Iniezione Frontale
    ) -> Tuple[str, str]:
        """
        Costruisce il prompt di sistema finale separando rigidamente l'Ancora dal Caos.
        Restituisce una tupla (ancora_text, caos_text) per preservare la cache dei messaggi.
        """
        # =====================================================================
        # VAGONE 1: L'ANCORA (TOP - 100% Cache Hit)
        # Contiene SOLO le direttive statiche, DNA e Regole. NESSUNA variabile dinamica.
        # =====================================================================
        ancora_base = self._build_anchor_prompt(in_gdr_mode=in_gdr_mode)
        # [FIX CRITICO CACHE] Non sanitizzare di nuovo per non rompere l'hash esatto generato nel warmup
        ancora_text = ancora_base

        # =====================================================================
        # VAGONE 2: IL CAOS (BOTTOM - 0% Cache Hit)
        # Contiene i dati che cambiano ad ogni turno o sessione.
        # =====================================================================
        caos_parts = list()

        # 1. TIME-BUCKET CACHING: Normalizzazione orario in blocchi di 30 minuti
        bucket_time = datetime.now().replace(minute=(datetime.now().minute // 30) * 30, second=0, microsecond=0).strftime("%H:%M")
        caos_parts.append(f"[ORARIO_BUCKET]: {bucket_time}")

        # [FIX v129.1] Iniettiamo qui tutto ciò che è dinamico
        if narrative_buffer:
            # Distillazione spinta: riduciamo il buffer a 400 token per dare priorità alla fluidità
            safe_buffer = self._safe_truncate_text(self._semantic_minify(narrative_buffer), max_tokens=400, keep="end")
            caos_parts.append(f"[MEMORIA A BREVE TERMINE]:\n{safe_buffer}")

        if dynamic_profile:
            caos_parts.append(f"[PROFILO DINAMICO UTENTE]:\n{dynamic_profile}")

        # [NUOVO] Iniezione dei Moduli Dinamici
        dynamic_slots = self._assembla_slot("avatar", heart_state_dict or {}, mode="dynamic")
        for cat, content in dynamic_slots.items():
            if content:
                caos_parts.append(f"--- MODULI COGNITIVI ATTIVI ({cat.upper()}) ---\n{content}")

        # Estrae i valori degli slider dal JSON e li traduce in istruzioni registiche
        personality_data = self.soul_data.get("personalita_dinamica", {})
        personality_text = self._translate_personality_to_text(personality_data)
        if personality_text:
            caos_parts.append(f"{t('brain.personality_traits_header')}{personality_text}")

        # Iniezione REGIA EMOTIVA (HEARTBEAT)
        emotional_directives = self._translate_heart_to_instructions(heart_state_dict)
        if emotional_directives:
            caos_parts.append(emotional_directives)

        # 2. Realtà Fisica / Contesto Ambientale (Ridotto a 500 token per abbattere il TTFT)
        if contesto_ambientale:
            safe_status = self._safe_truncate_text(self._semantic_minify(contesto_ambientale), max_tokens=500, keep="start")
            caos_parts.append(f"{t('brain.physical_reality_header')}\n{safe_status}")

        # 3. Rete di Spionaggio (Gossip)
        if gossip_block:
            caos_parts.append(gossip_block)

        # --- BLOCCO VOLATILE (Cambia ad ogni turno o per ogni PNG) ---

        if core_memories:
            # --- [PROTOCOLLO SEMANTIC RoPE] Isolamento Temporale ---
            # Ridotto a 500 caratteri per memoria per abbattere il TTFT
            safe_memories = list()
            for m in core_memories:
                m_trunc = m[:500] + t("brain.rag_user_truncated") if len(m) > 500 else m
                safe_memories.append(f"<|ISOLATED_MEMORY_BLOCK|>\n[RICORDO DAL PASSATO]: {m_trunc}\n<|END_ISOLATED_MEMORY|>")
            caos_parts.append(t("brain.past_memories_label") + "\n".join(safe_memories))

        if dati_biometrici:
            caos_parts.append(t("brain.sensory_data_format", data=dati_biometrici))

        # --- [FIX CRITICO] SCUDI INCONDIZIONATI E SUPER-RICORDO ---
        # Questi scudi devono essere sempre presenti alla fine del prompt, indipendentemente dal RAG
        if super_ricordo_text:
            caos_parts.append(super_ricordo_text)
            
        caos_parts.append(t("brain.rag_anti_hallucination_names"))
        caos_parts.append(t("brain.anti_robot_nuke"))

        if contesto_aggiuntivo:
            caos_parts.append(f"[DATI VISIVI / EXTRA]:\n{contesto_aggiuntivo}")

        # Prepariamo il template di incarnazione invertito
        nome_png = self.soul_data.get("dati_anagrafici", {}).get("nome", "Avatar")
        objective_input = self._de_subjectivize_input(user_input, pg_name)

        _raw_png_gender = self.soul_data.get("dati_anagrafici", {}).get(
            "genere", "Unknown"
        )
        # [FIX LIVELLO 1] Protezione contro pg_gender nullo
        png_gen_it = (
            t("brain.gender_female_grammar")
            if str(_raw_png_gender or "Female").lower() in ["female", "femmina", "f", "donna"]
            else t("brain.gender_male_grammar")
        )
        pg_gen_it = (
            t("brain.gender_female_grammar")
            if str(pg_gender or "Male").lower() in ["female", "femmina", "f", "donna"]
            else t("brain.gender_male_grammar")
        )

        #[RESTORED v7.2] Protocollo Grammaticale
        caos_parts.append(
            f"[PROTOCOLLO GRAMMATICALE]: Il tuo interlocutore ({pg_name}) è di genere {pg_gen_it}. Usa accordi grammaticali appropriati (es. 'benvenuto' vs 'benvenuta')."
        )

        comando_supremo_template = self._get_internal_prompt("comando_supremo_base")
        comando_supremo = self._safe_replace(
            comando_supremo_template, "nome_png", nome_png.upper()
        )
        comando_supremo = self._safe_replace(
            comando_supremo, "objective_input", objective_input
        )
        comando_supremo = self._safe_replace(comando_supremo, "png_gen_it", png_gen_it)
        comando_supremo = self._safe_replace(comando_supremo, "pg_gen_it", pg_gen_it)
        
        # --- [FIX CRITICO] GATEKEEPER COGNITIVO (MODALITÀ STANDARD) ---
        if getattr(self, "is_large_model", False):
            # In Modalità Standard NON passiamo la lista numerata delle emozioni per risparmiare token.
            # Dobbiamo usare un comando specifico che non chieda all'LLM di cercare una lista inesistente,
            # altrimenti va in cortocircuito logico e genera scena muta.
            comando_supremo_large_std = t("brain.supreme_command_standard_large_model", name=nome_png.upper(), pg_name=pg_name)
            if comando_supremo_large_std.startswith("["): # Fallback di sicurezza se manca la traduzione
                comando_supremo_large_std = f"AGISCI ORA COME {nome_png.upper()}.\nRispondi all'input di {pg_name} in modo naturale, fisico e passionale. Usa la prima persona. Concludi la tua risposta con il tag [INTENT: emozione] scrivendo l'emozione in inglese (es. [INTENT: Joy], [INTENT: Sadness])."
            caos_parts.append(comando_supremo_large_std)
        else:
            caos_parts.append(comando_supremo)

        # --- [FIX BUG 02] INIEZIONE LINGUA IN MODALITÀ STANDARD ---
        caos_parts.append(self._get_language_instruction(lang))

        # Purificazione e assemblaggio del Caos
        caos_text = self.PROMPT_SEPARATOR.join([self._sanitize_for_cache(p) for p in caos_parts if p]
        )
        caos_text = self._replace_all_name_variants(
            caos_text, pg_name
        )  # [FIX v7.0] Sostituzione universale

        return ancora_text, caos_text

    def pensa(
        self,
        context: Optional["UserContext"],
        memory_manager: "MemoryManager",
        db_manager: "DatabaseManager",
        session_id: str,
        user_input: str,
        pg_name: str,
        contesto_visivo: Optional[str] = None,
        in_gdr_mode: bool = False,
        contesto_ambientale: Optional[str] = None,
        game_state: Optional[Dict[str, Any]] = None,
        narrative_buffer: str = "",
        dati_biometrici: str = "",
        pg_gender: str = "Male",
        lang: str = "it",
        system_paths: Dict[str, str] = None,
        stato_emotivo: str = "",
        skip_router: bool = False,
        context_name: str = t("brain.context_standard"),
        use_rag: bool = True,
        heart_state_dict: dict = None,
        tools: Optional[List[Dict]] = None,
        dynamic_profile: str = "",
        gossip_block: str = "",
        **kwargs,
    ) -> str:
        """
        [AGGIORNATO v127.0] Il routing è ora gestito interamente dal Dispatcher in chat.py.
        Questo metodo si occupa esclusivamente della generazione narrativa e dell'iniezione JIT.
        """
        self.logger.log(
            t("log.brain_thinking_activated", gdr=in_gdr_mode, context=context_name)
        )

        # [FIX A0024] Il vecchio _router_neurale è stato epurato per evitare overflow.
        # La logica di selezione tool avviene a monte (chat.py).

        # --- [NUOVO v111.0] RECUPERO RAG MEMORIE ANCESTRALI E BACKSTORY (v116.6) ---
        core_memories = list()
        super_ricordo_text = ""
        if (
            memory_manager and use_rag
        ):  # [NUOVO FASE 60] Rispetta il Gatekeeper anche per le Core Memories
            # Usa il context_name passato (Standard o nome del GDR) per la risonanza onirica
            core_memories = memory_manager.retrieve_relevant_core_memories(
                user_input, context_name
            )
            # --- [FIX CRITICO] RECUPERO BACKSTORY DA UNIFIED LIBRARY ---
            lore_memories = memory_manager.search_library(user_input, top_k=2, context_filter=context_name)
            if lore_memories:
                core_memories.extend(lore_memories)
                
            # --- [NUOVO] RECUPERO DETERMINISTICO SUPER-RICORDO (ANTI-AMNESIA) ---
            try:
                super_id = f"backstory_{self.active_avatar_name.lower()}_super_family_v5"
                super_doc = memory_manager.unified_library.get(ids=list([super_id]))
                if super_doc and super_doc.get("documents") and len(super_doc["documents"]) > 0:
                    super_ricordo_text = t("brain.super_memory_prefix", doc=super_doc['documents'][0])
                    self.logger.log(t("log.super_memory_recovered"), "MEMORY")
                else:
                    self.logger.log(t("log.super_memory_not_found", id=super_id), "WARNING")
            except Exception as e:
                self.logger.error(t("log.super_memory_error", error=e))
        # ------------------------------------------------------

        # --- [FIX FASE 3] RECUPERO AAAK WORKING MEMORY ---
        if memory_manager:
            aaak_chunk = memory_manager.get_latest_sliding_window_chunk(session_id)
            if aaak_chunk:
                narrative_buffer = f"{narrative_buffer}\n\n[MEMORIA A BREVE TERMINE COMPRESSA (AAAK)]:\n{aaak_chunk}".strip()

        # --- FIX v27.43: Passaggio esplicito di contesto_visivo come contesto_aggiuntivo ---
        # Questo assicura che venga iniettato nella sezione "DATI VISIVI" del prompt
        ancora_text, caos_text = self._crea_vangelo_onnicomprensivo(
            memory_manager,
            user_input,
            pg_name,
            contesto_aggiuntivo=contesto_visivo,
            contesto_ambientale=contesto_ambientale,
            game_state=game_state,
            narrative_buffer=narrative_buffer,
            dati_biometrici=dati_biometrici,
            pg_gender=pg_gender,
            lang=lang,
            system_paths=system_paths,  # [NUOVO v43.4]
            stato_emotivo=stato_emotivo,  # [NUOVO v46.0]
            core_memories=core_memories,  # [NUOVO v111.0]
            use_rag=use_rag,  # [NUOVO FASE 60]
            heart_state_dict=heart_state_dict,
            in_gdr_mode=in_gdr_mode,
            dynamic_profile=dynamic_profile,
            gossip_block=gossip_block,
            super_ricordo_text=super_ricordo_text, # [FIX CRITICO] Iniezione Frontale
        )

        # ---[NUOVO v28.0] TIERED MEMORY SYSTEM (WORKING MEMORY) ---
        # [FIX FASE 3] Riduciamo il limite da 6 a 2. Il resto del contesto recente
        # è compresso in formato AAAK e iniettato nel narrative_buffer.
        # Questo abbatte il consumo di token e previene l'Overflow.
        history_tuples = db_manager.get_recent_history(session_id, limit=2)

        #[NUOVO v7.0] COSTRUZIONE ARRAY MESSAGGI (SANDWICH PRESERVATO)
        # 1. L'Ancora (System) - 100% Statico
        messages = [{"role": "system", "content": ancora_text}]

        # 2. La Cronologia (History) - Semi-statico
        for speaker, content in history_tuples:
            role = "user" if speaker == pg_name else "assistant"
            clean_content = self._sanitize_for_cache(content)
            
            # ---[NUOVO] CONSAPEVOLEZZA DEL GHOST TEXT ---
            if clean_content.startswith("[GHOST] "):
                clean_content = clean_content.replace("[GHOST] ", f"[MESSAGGIO SCRITTO E CANCELLATO, MA LETTO DA {pg_name}]: ")
                
            messages.append(
                {
                    "role": "user" if role == "user" else "assistant",
                    "content": clean_content,
                }
            )

        # 3. Il Caos (User) - 100% Dinamico
        # [FIX v129.2] Uniamo Ancora + Caos e puliamo per evitare inquinamento cache
        # [FIX CRITICO] Aggiungiamo il Nuke Anti-Robot ALLA FINE ASSOLUTA dell'input utente
        dynamic_input_content = self.PROMPT_SEPARATOR.join([
            caos_text, 
            self._sanitize_for_cache(user_input),
            t("brain.anti_robot_nuke")
        ])
        
        # --- [FIX PRO A0045] MULTIMODAL INJECTION (AUDIO/IMAGE) ---
        # Aggiunte parentesi di cattura () per evitare IndexError
        audio_ref_match = re.search(r"\[AUDIO_REF:\s*([^\]]+)\]\s*", dynamic_input_content)
        image_ref_match = re.search(r"\[IMAGE_REF:\s*([^\]]+)\]\s*", dynamic_input_content)
        
        multimodal_content = list()
        
        if audio_ref_match and self.supports_native_audio:
            audio_path = Path(audio_ref_match.group(1).strip())
            dynamic_input_content = dynamic_input_content.replace(audio_ref_match.group(0), "").strip()
            if audio_path.exists():
                try:
                    with open(audio_path, "rb") as f:
                        audio_b64 = base64.b64encode(f.read()).decode("utf-8")
                    multimodal_content.append({"type": "input_audio", "input_audio": {"data": audio_b64, "format": "wav"}})
                    self.logger.log(t("log.brain_native_audio_injected"), "VOICE")
                except Exception as e:
                    self.logger.error(t("log.brain_native_audio_error", error=e))
                finally:
                    try: os.remove(audio_path)
                    except: pass

        # --- [FIX CRITICO] PROTEZIONE MULTIMODALE (MMProj Check) ---
        # Invia l'immagine al server C++ SOLO se il modello MMProj (Occhi) è stato caricato.
        # Altrimenti, il server C++ andrà in crash con errore 500.
        if image_ref_match and self.is_gemma_4:
            image_path = Path(image_ref_match.group(1).strip())
            dynamic_input_content = dynamic_input_content.replace(image_ref_match.group(0), "").strip()
            
            if self.ha_visione:
                if image_path.exists():
                    try:
                        with open(image_path, "rb") as f:
                            img_b64 = base64.b64encode(f.read()).decode("utf-8")
                        multimodal_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}})
                        self.logger.log(t("log.brain_native_image_injected"), "VISION")
                    except Exception as e:
                        self.logger.error(t("log.brain_native_image_error", error=e))
            else:
                self.logger.warning("Immagine rilevata ma MMProj (Occhi) non caricato. Fallback testuale forzato.")
                # Se non ha la visione nativa, l'immagine è già stata analizzata dal Pan&Scan in chat.py
                # e il risultato è nel 'contesto_visivo'. Non facciamo nulla qui.

        if multimodal_content:
            # --- [FASE 4] PREVENZIONE TESTO VUOTO ---
            # Se l'utente ha inviato solo audio, dynamic_input_content sarà vuoto dopo la rimozione del tag.
            # Gemma 4 richiede sempre un prompt testuale di accompagnamento.
            if not dynamic_input_content.strip():
                dynamic_input_content = "Ascolta e rispondi."
                
            multimodal_content.append({"type": "text", "text": dynamic_input_content})
            messages.append({"role": "user", "content": multimodal_content})
        else:
            messages.append({"role": "user", "content": dynamic_input_content})

        # --- [NUOVO] PROTOCOLLO MEMORY INTERLEAVE (MULTI-HOP RAG) ---
        internal_memory_tool = {
            "type": "function",
            "function": {
                "name": "esplora_memoria_profonda",
                "description": "Cerca nei tuoi ricordi a lungo termine (Vector DB). Usalo se l'utente fa riferimento a eventi passati, nomi o concetti che non ricordi immediatamente.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "La frase o parola chiave da cercare nei ricordi."}
                    },
                    "required": ["query"]
                }
            }
        }
        
        active_tools = (tools or []) +[internal_memory_tool]
        response = ""
        
        # Loop ReAct interno per la memoria (Max 3 salti per evitare loop infiniti)
        for hop in range(3):
            response = self._genera_pensiero(messages, tools=active_tools, enable_streaming=True, **kwargs)
            
            query_to_search = self._extract_internal_memory_call(response)
            if query_to_search and memory_manager:
                self.logger.log(f"Memory Interleave: Cerco '{query_to_search}' nel subconscio...", "MEMORY")
                
                # Eseguiamo la ricerca nel Vector DB
                results = memory_manager.search_memories(query_to_search, top_k=2)
                if hasattr(memory_manager, 'search_library'):
                    results += memory_manager.search_library(query_to_search, top_k=1)
                    
                if results:
                    mem_text = "\n".join([f"<|ISOLATED_MEMORY_BLOCK|>\n[RICORDO TROVATO]: {r}\n<|END_ISOLATED_MEMORY|>" for r in results])
                else:
                    mem_text = "Nessun ricordo trovato per questa query."
                    
                # Aggiungiamo il risultato al contesto e facciamo un nuovo giro di pensiero
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": f"[RISULTATO RICERCA MEMORIA INTERNA]:\n{mem_text}\nOra rispondi all'utente basandoti su questi ricordi."})
                continue
                
            # Se non ha chiamato il tool di memoria, usciamo dal loop e restituiamo la risposta finale
            break

        # --- [FIX v27.41] ACTIVE BOUNCER LOGIC ---
        intent_match = re.search(r"\[INTENT:\s*([^\]]+)\]", response)
        if intent_match:
            original_intent = intent_match.group(1).strip()

            # 1. Risoluzione ID -> Emozione (Protocollo Copione)
            is_id_resolution = False
            if original_intent.isdigit() and original_intent in self.emotion_id_map:
                corrected_intent = self.emotion_id_map[original_intent]
                is_id_resolution = True
            else:
                # Fallback di sicurezza se l'LLM ha scritto una parola invece del numero
                corrected_intent = get_closest_emotion(original_intent, self.valid_emotions)

            # 2. Se c'è stata una correzione (da ID a Parola, o da Allucinazione a Parola)
            if corrected_intent != original_intent:
                if is_id_resolution:
                    self.logger.log(f"[INTENT] Risoluzione ID: '{original_intent}' -> '{corrected_intent}'", "INTENT")
                else:
                    self.logger.log(
                        t(
                            "log.brain_bouncer_correction",
                            old=original_intent,
                            new=corrected_intent,
                        ),
                        "INTENT",
                    )
                response = response.replace(
                    f"[INTENT: {original_intent}]", f"[INTENT: {corrected_intent}]"
                )
                intent = corrected_intent
            else:
                intent = original_intent

            self.recent_intents.append(intent)
            self.recent_intents = self.recent_intents[-5:]

        return response

    # --- [NUOVO v46.0] PROTOCOLLO DEEP DIVE (SOFT PONDERING) - SINCRONIZZATO v113.1 ---
    def pensa_deep_dive(
        self,
        memory_manager: "MemoryManager",
        db_manager: "DatabaseManager",
        session_id: str,
        user_input: str,
        pg_name: str,
        heart_status: str,
        narrative_buffer: str,
        biometrics: str,
        system_paths: Dict[str, str],
        lang: str = "it",
        use_rag: bool = True,
        heart_state_dict: dict = None,
        dynamic_profile: str = "",
        in_gdr_mode: bool = False, # [FIX CRITICO CACHE] Aggiunto per allineamento Ancora
    ) -> str:
        """
        [LOBOTOMIA DEEP DIVE] Esegue un ragionamento profondo in una SINGOLA chiamata LLM.
        Sfrutta l'Ancora di Diamante per il 100% di Cache Hit e il reasoning nativo di Gemma 4.
        """
        self.logger.log(t("log.brain_deep_dive_activated"), "EMOTION")

        # 1. Costruzione Sandwich Perfetto (Ancora di Diamante + Caos)
        core_memories = memory_manager.retrieve_relevant_core_memories(user_input, "Standard") if use_rag and memory_manager else []
        
        ancora_text, caos_text = self._crea_vangelo_onnicomprensivo(
            memory_manager, user_input, pg_name,
            narrative_buffer=narrative_buffer,
            dati_biometrici=biometrics,
            system_paths=system_paths,
            lang=lang,
            stato_emotivo=heart_status,
            core_memories=core_memories,
            heart_state_dict=heart_state_dict,
            dynamic_profile=dynamic_profile,
            in_gdr_mode=in_gdr_mode # [FIX CRITICO CACHE] Passaggio stato per allineamento Ancora
        )

        # 2. Iniezione Direttiva Deep Dive nel Caos
        direttiva_deep_dive = "\n\n[DIRETTIVA DEEP DIVE]: L'utente ha toccato un tasto profondo. Usa il tuo canale di pensiero per riflettere intensamente sui tuoi veri sentimenti prima di rispondere. Sii vulnerabile, onesta e profonda. Non essere superficiale."
        caos_text += direttiva_deep_dive

        # 3. Assemblaggio Messaggi (Preservando la Cache)
        history_tuples = db_manager.get_recent_history(session_id, limit=2)
        messages = [{"role": "system", "content": ancora_text}]
        
        for speaker, content in history_tuples:
            role = "user" if speaker == pg_name else "assistant"
            clean_content = self._sanitize_for_cache(content)
            if clean_content.startswith("[GHOST] "):
                clean_content = clean_content.replace("[GHOST] ", f"[MESSAGGIO SCRITTO E CANCELLATO, MA LETTO DA {pg_name}]: ")
            messages.append({"role": role, "content": clean_content})
            
        dynamic_input_content = self.PROMPT_SEPARATOR.join([caos_text, self._sanitize_for_cache(user_input)])
        messages.append({"role": "user", "content": dynamic_input_content})

        # 4. Singola Chiamata con Reasoning Budget Elevato
        # Il server C++ gestirà il pensiero nativamente e restituirà solo la risposta finale.
        # Tempo abbattuto da 60s a ~5s.
        return self._genera_pensiero(messages, temperature=0.7, max_tokens=2048, reasoning_budget=1024, enable_streaming=True)

    # --- [NUOVO v46.0] PENSIERO NON DETTO (UNSENT MESSAGE) - SINCRONIZZATO v113.1 ---
    def pensa_pensiero_non_detto(
        self,
        user_input: str,
        emotional_status: str,
        pg_name: str,
        soul_data: Dict[str, Any],
        lang: str = "it",
        heart_state_dict: dict = None,
        raw_history: list = None, # [FIX CRITICO CACHE]
        in_gdr_mode: bool = False, # [FIX CRITICO CACHE]
        super_ricordo_text: str = "", # [FIX CRITICO] Iniezione Frontale
    ) -> str:
        """
        Genera una risposta impulsiva basata sul DNA che verrà 'cancellata' prima dell'invio.
        """
        # [NUOVO v7.0] COSTRUZIONE SANDWICH NON-DETTO
        ancora_text = self._build_anchor_prompt(in_gdr_mode=in_gdr_mode)

        caos_parts = []

        dynamic_slots = self._assembla_slot(
            "avatar", heart_state_dict or {}, mode="dynamic"
        )
        for cat, content in dynamic_slots.items():
            if content:
                caos_parts.append(
                    f"--- MODULI COGNITIVI ATTIVI ({cat.upper()}) ---\n{content}"
                )

        # --- [NUOVO] ESTRAZIONE ARCHETIPO ED ESSENZA PER IL LAPSUS FREUDIANO ---
        archetipo = _get_json_value(soul_data, ["archetipo_attuale"], "Nessuno")
        essenza = _get_json_value(soul_data, ["essenza_fondamentale"], "Un'anima.")

        non_detto_template = self._get_internal_prompt("pensiero_non_detto")
        non_detto_prompt = self._safe_replace(
            non_detto_template, "emotional_status", emotional_status
        )
        non_detto_prompt = self._safe_replace(
            non_detto_prompt, "archetipo", archetipo
        )
        non_detto_prompt = self._safe_replace(
            non_detto_prompt, "essenza", essenza
        )
        non_detto_prompt = self._safe_replace(
            non_detto_prompt, "user_input", user_input
        )
        
        # --- [FIX CRITICO] RIMOZIONE JSON PER GHOST TEXT ---
        # L'Ancora vieta il JSON. Chiedere un JSON qui causa Dissonanza Cognitiva e output vuoto.
        # Rimuoviamo la richiesta JSON dal prompt originale.
        non_detto_prompt = non_detto_prompt.split("Rispondi ESCLUSIVAMENTE con un oggetto JSON")[0].strip()
        non_detto_prompt += "\n\nScrivi SOLO il pensiero, senza virgolette, senza JSON e senza altre parole."
        
        caos_parts.append(non_detto_prompt)
        
        if super_ricordo_text:
            caos_parts.append(super_ricordo_text)
        caos_parts.append(t("brain.rag_anti_hallucination_names"))
        caos_parts.append(t("brain.anti_robot_nuke"))

        caos_text = self.PROMPT_SEPARATOR.join([self._sanitize_for_cache(p) for p in caos_parts if p]
        )
        caos_text += self._get_language_instruction(lang)
        caos_text = self._replace_all_name_variants(caos_text, pg_name)

        messages = [{"role": "system", "content": ancora_text}]
        
        # --- COSTRUZIONE CRONOLOGIA (MESSAGGI REALI) ---
        if raw_history:
            for speaker, content in raw_history:
                clean_content = self._sanitize_for_cache(content)
                if clean_content.startswith("[GHOST] "):
                    clean_content = clean_content.replace("[GHOST] ", f"[MESSAGGIO SCRITTO E CANCELLATO, MA LETTO DA {pg_name}]: ")
                
                if speaker.lower() == self.active_avatar_name.lower():
                    messages.append({"role": "assistant", "content": clean_content})
                elif speaker.lower() == pg_name.lower():
                    messages.append({"role": "user", "content": clean_content})
                else:
                    messages.append({"role": "user", "content": f"[{speaker}]: {clean_content}"})

        messages.append({"role": "user", "content": caos_text})
        
        # Generazione testuale pura, senza schema JSON
        response_str = self._genera_pensiero(
            messages, 
            temperature=0.7, 
            max_tokens=256, 
            reasoning_budget=128, 
            in_gdr_mode=in_gdr_mode, 
            super_ricordo_text=getattr(self, 'super_ricordo_cache', '')
            # Rimosso enable_streaming=True per evitare conflitti UI con il main thread
        )
        
        # Pulizia da eventuali tag di pensiero residui
        clean_str = re.sub(r"<\|channel\|\>thought.*?\<channel\|\>", "", response_str, flags=re.IGNORECASE | re.DOTALL).strip()
        clean_str = re.sub(r"<think>.*?</think>", "", clean_str, flags=re.IGNORECASE | re.DOTALL).strip()
        
        return clean_str.strip('"').strip("'")

    def distilla_memoria_narrativa(
        self, storia_recente: str, buffer_precedente: str, lang: str = "it"
    ) -> str:
        """
        Crea una sintesi densa e dettagliata degli eventi recenti per il Narrative Buffer.
        """
        self.logger.log(t("log.brain_distillation_start"), "MEMORY")

        # ---[GOD TIER SHIELD] ---
        safe_storia = self._safe_truncate_text(storia_recente, max_tokens=1500)
        safe_buffer = self._safe_truncate_text(buffer_precedente, max_tokens=1500)

        prompt_template = self._get_internal_prompt("distilla_memoria")
        prompt = self._safe_replace(prompt_template, "safe_buffer", safe_buffer)
        prompt = self._safe_replace(prompt, "safe_storia", safe_storia)

        prompt += self._get_language_instruction(lang)

        messages = [{"role": "user", "content": prompt}]
        result = self._genera_pensiero(messages, temperature=0.3)
        print(t("log.brain_distillation_debug", result=result[:100]))  # Log visibile
        return result

    def analizza_dinamiche_mondo_espansi(
        self,
        input_utente: str,
        risposta_anima: str,
        stato_attuale: str,
        lang: str = "it",
    ) -> Dict[str, Any]:
        """
        Analizza lo scambio per rilevare cambiamenti psicologici e relazionali (Proposta 3).
        """
        self.logger.log(t("log.brain_world_dynamics"), "WORLD")

        prompt_template = self._get_internal_prompt("dinamiche_mondo")
        prompt = self._safe_replace(prompt_template, "stato_attuale", stato_attuale)
        prompt = self._safe_replace(prompt, "input_utente", input_utente)
        prompt = self._safe_replace(prompt, "risposta_anima", risposta_anima)

        prompt += self._get_language_instruction(lang)

        messages = [{"role": "user", "content": prompt}]
        schema = {
            "type": "object",
            "properties": {
                "psicologia": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                },
                "relazioni": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                },
                "obiettivi": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                },
                "clima": {"type": "string"},
            },
        }

        response_str = self._genera_pensiero(
            messages,
            temperature=0.1,
            response_format={"type": "json_object", "schema": schema},
        )
        try:
            return json.loads(response_str)
        except:
            return {}

    def pensa_simulazione_strategica(
        self,
        objective: str,
        variables: List[str],
        current_context: str,
        lang: str = "it",
    ) -> str:
        """
        Esegue una simulazione parallela di scenari basata su dati attuali.
        Affinato v92.0: Include Analisi delle Dipendenze e Impatto a Lungo Termine.
        """
        self.logger.log(t("log.brain_strategy_start", objective=objective), "STRATEGY")

        prompt_template = self._get_internal_prompt("simulazione_strategica")
        prompt = self._safe_replace(prompt_template, "objective", objective)
        prompt = self._safe_replace(prompt, "variables", ", ".join(variables))
        prompt = self._safe_replace(prompt, "current_context", current_context)

        prompt += self._get_language_instruction(lang)

        messages = [{"role": "user", "content": prompt}]
        return self._genera_pensiero(messages, temperature=0.4)

    def pensa_ricostruzione_memoria(
        self, frammento_memoria: str, pg_name: str, lang: str = "it"
    ) -> str:
        """
        Trasforma un ricordo grezzo in una narrazione immersiva al presente.
        """
        self.logger.log(t("log.brain_flashback_start"), "MEMORY")

        prompt_template = self._get_internal_prompt("ricostruzione_memoria")
        prompt = self._safe_replace(
            prompt_template, "frammento_memoria", frammento_memoria
        )

        prompt += self._get_language_instruction(lang)

        messages = [{"role": "user", "content": prompt}]
        return self._genera_pensiero(messages, temperature=0.6)

    def analizza_contesto_visivo_proattivo(
        self, screen_text: str, pg_name: str, heart_status: str, lang: str = "it"
    ) -> str:
        self.logger.log(t("log.brain_proactive_vision"))

        identita_prompt = (
            _format_soul_data_for_prompt(self.soul_data)
            if self.soul_data
            else t("brain.soul_generic")
        )

        # --- MODIFICA v32.0: USO COSTANTI DINAMICHE ---
        vangelo_proattivo = self._get_brain_prompt("proattivo")
        vangelo_proattivo = self._safe_replace(
            vangelo_proattivo, "screen_text", screen_text
        )
        vangelo_proattivo = self._safe_replace(
            vangelo_proattivo, "identita_prompt", identita_prompt
        )
        vangelo_proattivo = self._safe_replace(
            vangelo_proattivo, "heart_status", heart_status
        )
        vangelo_proattivo = self._safe_replace(
            vangelo_proattivo,
            "nome_avatar",
            self.soul_data.get("dati_anagrafici", {}).get("nome", "AI"),
        )
        vangelo_proattivo = self._replace_all_name_variants(vangelo_proattivo, pg_name)
        vangelo_proattivo += self._get_language_instruction(lang)

        messages = [{"role": "user", "content": vangelo_proattivo}]
        response = self._genera_pensiero(messages, temperature=0.1)

        return response

    def pensa_e_compila_scheda_da_url(
        self, url: str, lang: str = "it"
    ) -> Dict[str, Any]:
        # [FIX v51.2] Normalizzazione chiave traduzione
        self.logger.log(t("brain.oracolo_web", url=url))

        try:
            # [FIX v51.3] Headers semplificati per evitare conflitti di decodifica (es. Brotli)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": "https://www.google.com/",
            }

            html_content = b""

            try:
                # --- [FIX CRITICO] FANDOM API BYPASS ---
                # Fandom blocca le richieste HTML standard con Cloudflare.
                # Usiamo l'API nativa di MediaWiki per estrarre il testo pulito bypassando i blocchi.
                if "fandom.com/wiki/" in url:
                    base_url, page_name = url.split("/wiki/", 1)
                    api_url = f"{base_url}/api.php?action=parse&page={page_name}&format=json&prop=text"
                    self.logger.log(
                        f"[ORACLE] URL Fandom rilevato. Uso API nativa per bypassare Cloudflare...",
                        "DEBUG",
                    )
                    api_response = requests.get(api_url, headers=headers, timeout=20)
                    if api_response.status_code == 200:
                        api_data = api_response.json()
                        if "parse" in api_data and "text" in api_data["parse"]:
                            html_content = api_data["parse"]["text"]["*"].encode(
                                "utf-8"
                            )

                # Se non è Fandom o l'API ha fallito, procedi con la richiesta standard
                if not html_content:
                    response = requests.get(
                        url, headers=headers, timeout=20, allow_redirects=True
                    )
                    if response.status_code != 200:
                        self.logger.error(
                            t(
                                "brain.oracolo_http_error",
                                code=response.status_code,
                                url=url,
                            )
                        )
                    response.raise_for_status()
                    html_content = response.content

            except requests.exceptions.HTTPError as e:
                # [FIX CRITICO] Fallback su Playwright se Cloudflare/Fandom blocca requests con 403/503
                if e.response is not None and e.response.status_code in (401, 403, 503):
                    self.logger.log(
                        "[ORACLE] Blocco Cloudflare/403 rilevato. Tento fallback con Playwright...",
                        "WARNING",
                    )
                    try:
                        from playwright.sync_api import sync_playwright

                        with sync_playwright() as p:
                            browser = p.chromium.launch(headless=True)
                            page = browser.new_page(user_agent=headers["User-Agent"])
                            page.goto(url, timeout=30000)
                            # Attendi che il DOM sia caricato per superare i check JS di Cloudflare
                            page.wait_for_load_state("domcontentloaded")
                            html_content = page.content().encode("utf-8")
                            browser.close()
                    except Exception as pw_e:
                        self.logger.error(
                            f"[ORACLE] Fallback Playwright fallito: {pw_e}"
                        )
                        raise e  # Solleva l'errore originale se anche il fallback fallisce
                else:
                    raise e

            #[FIX v51.2] Corretto parser BeautifulSoup (lxml o html.parser sono gli standard)
            soup = BeautifulSoup(html_content, "html.parser")

            # --- [FIX CRITICO] ESTRAZIONE CHIRURGICA CONTENUTO ---
            main_content = soup.find("div", class_="mw-parser-output")
            if not main_content:
                # Fallback se non è una wiki standard
                main_content = soup.find("main") or soup.find("body")
            
            if main_content:
                soup = main_content

            text_parts =[
                tag.get_text(strip=True)
                for tag in soup.find_all(["p", "h2", "h3", "li"])
            ]
            page_text = " ".join(text_parts)

            if not page_text:
                return {"error": t("log.brain_oracle_no_text")}

            # --- MODIFICA v32.0: USO COSTANTI DINAMICHE ---
            prompt = self._get_brain_prompt("oracolo")
            # [FIX CRITICO] Ridotto a 12.000 caratteri (circa 4000 token). Un numero maggiore
            # causava un Out Of Memory (Context Window Exceeded) sui modelli con n_ctx standard a 8192,
            # impedendo la generazione dell'intero JSON della scheda.
            prompt = self._safe_replace(prompt, "page_text", page_text[:12000])
            prompt += self._get_language_instruction(lang)

            self.logger.log(t("log.brain_oracle_sending"))
            messages = [{"role": "user", "content": prompt}]

            # --- [FIX CRITICO] SCHEMA GBNF NUDO (ANTI-ALLUCINAZIONE) ---
            # Rimuoviamo TUTTE le descrizioni dallo schema. L'LLM non potrà più copiarle
            # perché fisicamente non esistono nella struttura che gli passiamo.
            schema = {
                "type": "object",
                "properties": {
                    "dati_anagrafici": {
                        "type": "object",
                        "properties": {
                            "nome_completo": {"type": "string"},
                            "genere": {"type": "string"},
                            "età_apparente": {"type": "string"},
                        },
                        "required": ["nome_completo"],
                    },
                    "dati_fisici_ed_estetici": {
                        "type": "object",
                        "properties": {"descrizione_visiva": {"type": "string"}},
                    },
                    "essenza_e_anima": {
                        "type": "object",
                        "properties": {
                            "essenza_fondamentale": {"type": "string"},
                            "archetipo_attuale": {"type": "string"},
                            "desideri_profondi": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "paure_radicate": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                        },
                    },
                    "storia_": {"type": "string"},
                    "relazioni_": {
                        "type": "object",
                        "additionalProperties": {"type": "string"}
                    },
                    "evoluzione_personale_": {"type": "string"},
                    "scopo_attuale_nel_gdr": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                },
                "required":["dati_anagrafici"],
            }

            llm_response_str = self._genera_pensiero(
                messages,
                temperature=0.2, # [FIX] Aumentato da 0.1 a 0.2 per evitare loop di punteggiatura nel reasoning
                max_tokens=4096, # [FIX CRITICO] Garantisce lo spazio vitale per generare un JSON così massiccio
                response_format={"type": "json_object", "schema": schema},
            )

            try:
                filled_json = json.loads(llm_response_str)
                
                # --- [LA GHIGLIOTTINA PYTHON] ---
                # Se l'LLM ha comunque allucinato ricordandosi i vecchi prompt, 
                # distruggiamo le frasi maledette prima di inviarle al frontend.
                bad_phrases =[
                    "Nome completo del personaggio",
                    "Genere (Maschile, Femminile",
                    "Età apparente",
                    "Descrizione fisica dettagliata",
                    "Descrizione concisa della personalità",
                    "L'archetipo narrativo",
                    "Lista di desideri",
                    "Lista di paure",
                    "Riassunto della storia",
                    "Descrizione relazione",
                    "Come il personaggio è cambiato",
                    "Obiettivi attuali"
                ]
                
                def _purge_hallucinations(data):
                    if isinstance(data, dict):
                        for k, v in data.items():
                            if isinstance(v, str):
                                if any(bad.lower() in v.lower() for bad in bad_phrases):
                                    data[k] = ""
                            else:
                                _purge_hallucinations(v)
                    elif isinstance(data, list):
                        for i in range(len(data)):
                            if isinstance(data[i], str):
                                if any(bad.lower() in data[i].lower() for bad in bad_phrases):
                                    data[i] = ""
                            else:
                                _purge_hallucinations(data[i])
                                
                _purge_hallucinations(filled_json)
                # --------------------------------

                return {"jsonData": filled_json, "imageUrl": None}
            except json.JSONDecodeError:
                self.logger.log(
                    t("log.brain_oracle_invalid_json", output=llm_response_str)
                )
                return {"error": t("log.brain_oracle_invalid_data")}

        except requests.RequestException as e:
            self.logger.log(t("log.brain_oracle_reach_error", error=e))
            return {"error": t("log.brain_oracle_reach_error", error=e)}
        except Exception as e:
            self.logger.error(t("log.brain_oracle_critical_error", error=e), "error")
            traceback.print_exc()
            return {"error": t("log.brain_oracle_critical_error")}

    def _seleziona_tono_png(self, personality_data: Dict[str, Any]) -> str:
        """Seleziona uno dei 10 toni basandosi sui tratti della personalità."""
        toni = [
            t("personality.tone_sarcastic"),
            t("personality.tone_formal"),
            t("personality.tone_aggressive"),
            t("personality.tone_sweet"),
            t("personality.tone_mysterious"),
            t("personality.tone_professional"),
            t("personality.tone_informal"),
            t("personality.tone_arrogant"),
            t("personality.tone_shy"),
            t("personality.tone_enthusiastic"),
        ]
        score = sum(abs(v.get("valore", 0)) for v in personality_data.values())
        return toni[score % len(toni)]

    def pensa_come_png(
        self,
        user_input: str,
        status_content: str,
        storia_recente: str,
        scheda_png: str,
        nome_png: str,
        pg_name: str,
        lista_intent_png: Optional[str] = None,
        ruolo_nel_turno: str = t("brain.role_target"),
        cronaca_turno_corrente: str = "",
        game_state: Optional[Dict[str, Any]] = None,
        narrative_buffer: str = "",
        dati_biometrici: str = "",
        pg_gender: str = "Male",
        lang: str = "it",
        context_reality_a: Optional[List[Dict]] = None,
        universal_context: str = "",
        context_name: str = t("brain.context_standard"),
        use_rag: bool = True,
        rag_memories: List[str] = None,
        heart_state_dict: dict = None,
        dynamic_profile: str = "",
        last_dm_narration: str = "",
        raw_history: list = None, # [FIX CRITICO]
        super_ricordo_text: str = "", # [FIX CRITICO] Iniezione Frontale
    ) -> str:
        self.logger.log(
            t("log.brain_polyphonic_incarnation", name=nome_png, role=ruolo_nel_turno)
        )

        # ---[FIX v108.3] DEFINIZIONE GENERI ALL'INIZIO ASSOLUTO (ANTI-NAMEERROR) ---
        _raw_png_gender = self._extract_gender(scheda_png)
        # [FIX LIVELLO 1] Aggiunto str() e fallback per prevenire AttributeError su pg_gender nullo
        png_gen_it = (
            t("brain.gender_female_grammar")
            if str(_raw_png_gender or "Female").lower() in ["female", "femmina", "f", "donna"]
            else t("brain.gender_male_grammar")
        )
        pg_gen_it = (
            t("brain.gender_female_grammar")
            if str(pg_gender or "Male").lower() in ["female", "femmina", "f", "donna"]
            else t("brain.gender_male_grammar")
        )
        # --------------------------------------------------------------------------

        # --- [NUOVO] ESTRAZIONE VETTORI PER PACING E BLEED-THROUGH ---
        tensione_attuale = heart_state_dict.get("tensione", 50) if heart_state_dict else 50
        complicita_attuale = heart_state_dict.get("complicità", 50) if heart_state_dict else 50

        # --- [NUOVO] SELEZIONE TONO DINAMICO E TEMPERATURE JITTER ---
        try:
            char_data = json.loads(scheda_png)
            personality_data = char_data.get("personalita_dinamica", {})
            tono_scelto = self._seleziona_tono_png(personality_data)
            # Jitter: base 0.7 + offset unico per PNG (range 0.70 - 0.89)
            jitter = (sum(ord(c) for c in nome_png) % 20) / 100.0
            temp_jittered = 0.7 + jitter
        except:
            tono_scelto = t("brain.tone_natural")
            temp_jittered = 0.75

        objective_input = self._de_subjectivize_input(user_input, pg_name)

        # ---[GOD TIER SHIELD] TRONCAMENTO ASSOLUTO E MINIFICAZIONE SEMANTICA ---
        # I limiti sono stati bilanciati per garantire spazio vitale alla risposta dell'LLM.
        # Usiamo keep="start" per i dati di lore (per non perdere l'identità) e keep="end" per la cronaca.
        #[FIX BUG 5] Limiti ridotti drasticamente per abbattere il TTFT in GDR e prevenire la lentezza.
        safe_universal_context = (
            self._safe_truncate_text(self._semantic_minify(universal_context), max_tokens=400, keep="start")
            if universal_context
            else t("brain.universal_context_none")
        )
        safe_status_content = self._safe_truncate_text(self._semantic_minify(status_content), max_tokens=600, keep="start")
        safe_storia_recente = self._safe_truncate_text(self._semantic_minify(storia_recente), max_tokens=800, keep="end")
        safe_cronaca = (
            self._safe_truncate_text(self._semantic_minify(cronaca_turno_corrente), max_tokens=800, keep="end")
            if cronaca_turno_corrente
            else t("brain.no_previous_action")
        )
        safe_buffer = (
            self._safe_truncate_text(self._semantic_minify(narrative_buffer), max_tokens=500, keep="end")
            if narrative_buffer
            else ""
        )
        safe_input = self._safe_truncate_text(objective_input, max_tokens=500, keep="end")

        # --- FIX v27.32: Rilevamento Bersaglio e Iniezione Barriera ---
        try:
            status_data = json.loads(status_content)
            all_present = [p["nome"] for p in status_data.get("personaggi", [])]
        except:
            all_present = [nome_png, pg_name]

        exclusion_command = self._detect_interaction_target(
            objective_input, nome_png, all_present
        )

        # --- MODIFICA v43.0: ESTRAZIONE COMPLETA ANATOMIA DELL'ANIMA ---
        soul_deep_structure = ""
        personality_block = ""
        descrizione_visiva = ""
        try:
            char_data = json.loads(scheda_png)

            # Helper locale per estrazione sicura
            def get_val(keys, default=""):
                return _get_json_value(char_data, keys, default)

            # PILASTRO A: IDENTITÀ
            nome_completo = get_val(["nome_completo", "nome", "name"], nome_png)
            provenienza = get_val(["provenienza"], t("brain.origin_unknown"))
            genere = get_val(["genere", "gender"], t("brain.gender_female_label"))
            compleanno = get_val(["compleanno"], t("brain.unknown_m"))
            eta = get_val(
                ["età_fisica", "età_apparente", "age"], t("brain.age_unknown")
            )

            # PILASTRO B: CORPO
            altezza = get_val(["altezza"], t("brain.height_medium"))
            peso = get_val(["peso"], t("brain.weight_medium"))
            misure = get_val(["misure"], t("brain.measures_standard"))
            corporatura = get_val(["corporatura"], t("brain.body_normal"))
            
            # ---[FIX CRITICO] ESTRAZIONE DINAMICA TOTALE (ANTI-ALLUCINAZIONE) ---
            # Estraiamo TUTTI i campi presenti in dati_fisici_ed_estetici (esclusi i dettagli intimi)
            # per garantire che i campi custom (es. "capelli", "occhi") vengano letti.
            dati_fisici_dict = char_data.get("dati_fisici_ed_estetici", {})
            descrizione_visiva_parts = list()
            for k, v in dati_fisici_dict.items():
                if k != "dettagli_intimi" and isinstance(v, str):
                    # Formatta la chiave (es. "colore_capelli" -> "Colore Capelli")
                    clean_key = k.replace("_", " ").title()
                    descrizione_visiva_parts.append(f"{clean_key}: {v}")
            
            if descrizione_visiva_parts:
                descrizione_visiva = " | ".join(descrizione_visiva_parts)
            else:
                descrizione_visiva = get_val(["descrizione_visiva"], t("brain.visual_desc_girl"))

            # Dettagli Intimi (Critici per Sex Rules)
            seno = get_val(["seno"], t("brain.breast_normal"))
            glutei = get_val(["glutei"], t("brain.glutes_normal"))
            genitali = get_val(["genitali"], t("brain.genitals_normal"))
            segni = get_val(["segni_particolari"], t("brain.marks_none"))

            # PILASTRO C: PSICHE
            archetipo = get_val(["archetipo_attuale"], t("brain.archetype_none"))
            essenza = get_val(["essenza_fondamentale"], t("brain.essence_soul"))
            desideri = get_val(["desideri_profondi"], [])
            paure = get_val(["paure_radicate"], [])
            abilita = get_val(
                ["abilità_e_poteri", "abilità_naturali"], t("brain.skills_none")
            )

            # PILASTRO D: STORIA & EVOLUZIONE
            storia = get_val(["storia_"], "")
            relazioni = get_val(["relazioni_"], {})
            evoluzione = get_val(["evoluzione_personale_"], "")
            scopo = get_val(["scopo_attuale_nel_gdr"], [])

            # PILASTRO E: SCHEDA TECNICA GDR (Stat Blindness Fix)
            scheda_rpg = get_val(["scheda_rpg"], {})
            rpg_block = ""
            if scheda_rpg:
                dati_base = scheda_rpg.get("dati_base", {})
                combat = scheda_rpg.get("combattimento", {})
                equip = scheda_rpg.get("equipaggiamento", {})
                magia = scheda_rpg.get("magia_e_privilegi", {})

                hp_max = combat.get("hp_massimi", 1)
                hp_curr = combat.get("hp_attuali", 1)
                hp_pct = (hp_curr / hp_max) * 100 if hp_max > 0 else 100

                pain_alert = ""
                if hp_pct <= 20:
                    pain_alert = t("brain.rpg_pain_critical", curr=hp_curr, max=hp_max)
                elif hp_pct <= 50:
                    pain_alert = t("brain.rpg_pain_normal", curr=hp_curr, max=hp_max)

                rpg_block = t("brain.rpg_sheet_header")
                rpg_block += t("brain.rpg_sheet_class", classe=dati_base.get('classe', ''), razza=dati_base.get('razza', ''), livello=dati_base.get('livello', 1))
                rpg_block += t("brain.rpg_sheet_align", allineamento=dati_base.get('allineamento', ''))
                rpg_block += t("brain.rpg_sheet_stats", curr=hp_curr, max=hp_max, ca=combat.get('classe_armatura', 10))

                armi =[f"{a.get('nome')} ({a.get('danno')})" for a in equip.get("armi", [])]
                rpg_block += t("brain.rpg_sheet_weapons", armi=', '.join(armi) if armi else 'Disarmato')

                inv = equip.get("inventario",[])
                monete = equip.get("monete", {})
                rpg_block += t("brain.rpg_sheet_inv", inv=', '.join(inv) if inv else 'Vuoto')
                rpg_block += t("brain.rpg_sheet_wealth", oro=monete.get('oro',0), argento=monete.get('argento',0), rame=monete.get('rame',0))

                incantesimi = magia.get("incantesimi",[])
                if incantesimi:
                    rpg_block += t("brain.rpg_sheet_spells", spells=', '.join(incantesimi))

                rpg_block += pain_alert + "\n"
            else:
                # ---[FIX A0014] FALLBACK CIVILE PER PERSONAGGI SENZA SCHEDA RPG ---
                rpg_block = t("brain.rpg_sheet_civilian")

            # ---[FIX v53.1] TRONCAMENTO CHIRURGICO PER ABBATTERE IL TTFT ---
            # Riduciamo drasticamente i token del Caos troncando i campi prolissi
            # [FIX BUG 5] Limiti ridotti per velocizzare il GDR
            storia_safe = self._safe_truncate_text(storia, max_tokens=200)
            evoluzione_safe = self._safe_truncate_text(evoluzione, max_tokens=150)

            # ---[NUOVO v110.0] TRADUZIONE PERSONALITÀ DINAMICA ---
            personalita_dinamica = get_val(["personalita_dinamica"], {})
            personality_text = self._translate_personality_to_text(personalita_dinamica)
            if personality_text:
                personality_block = (
                    t("brain.personality_traits_header") + personality_text + "\n"
                )

            # --- [NUOVO] INIEZIONE REGIA EMOTIVA (HEARTBEAT) ---
            emotional_directives = self._translate_heart_to_instructions(heart_state_dict)
            if emotional_directives:
                personality_block += "\n" + emotional_directives

            # --- [NUOVO v114.4] INIEZIONE VETTORI EMOTIVI PNG ---
            vettori_emotivi = get_val(["vettori_emotivi"], {})
            vettori_block = ""
            if vettori_emotivi:
                rel = t(
                    "brain.png_vettori_relational",
                    affetto=vettori_emotivi.get("affetto", 50),
                    fiducia=vettori_emotivi.get("fiducia", 50),
                    rispetto=vettori_emotivi.get("rispetto", 50),
                    complicita=vettori_emotivi.get("complicità", 30),
                )
                ist = t(
                    "brain.png_vettori_instinctive",
                    eccitazione=vettori_emotivi.get("eccitazione", 10),
                    gelosia=vettori_emotivi.get("gelosia", 0),
                    vulnerabilita=vettori_emotivi.get("vulnerabilità", 20),
                    curiosita=vettori_emotivi.get("curiosità", 50),
                )
                vettori_block = (
                    f"{t('log.brain_png_vettori_header')}\n"
                    f"{t('brain.png_vettori_mood', mood=vettori_emotivi.get('umore_corrente', t('brain.tone_natural')))}\n"
                    f"{rel}\n"
                    f"{ist}\n"
                    f"{t('log.brain_png_vettori_note')}\n"
                )

            # --- [NUOVO] TRIAGE DINAMICO DEL DNA (CENSOR MODULE) ---
            eccitazione_attuale = (
                heart_state_dict.get("eccitazione", 0) if heart_state_dict else 0
            )
            is_nsfw_context = eccitazione_attuale >= 80

            if is_nsfw_context:
                dettagli_intimi_str = (
                    t("brain.nsfw_details_header")
                    + t("brain.nsfw_item_breast", val=seno)
                    + t("brain.nsfw_item_glutes", val=glutei)
                    + t("brain.nsfw_item_genitals", val=genitali)
                    + t("brain.nsfw_item_marks", val=segni)
                )
            else:
                dettagli_intimi_str = ""

            # Formattazione liste/dict per il prompt
            def fmt_list(l):
                return ", ".join(l) if isinstance(l, list) else str(l)

            def fmt_dict_safe(d):
                s = json.dumps(d, ensure_ascii=False) if isinstance(d, dict) else str(d)
                return self._safe_truncate_text(s, max_tokens=200)

            soul_deep_structure = (
                t("brain.soul_anatomy_header")
                + t("brain.soul_anatomy_identity")
                + t(
                    "brain.soul_anatomy_identity_data",
                    nome=nome_completo,
                    eta=eta,
                    genere=genere,
                )
                + t(
                    "brain.soul_anatomy_origin",
                    provenienza=provenienza,
                    compleanno=compleanno,
                )
                + t("brain.soul_anatomy_body")
                + t("brain.soul_anatomy_aspect", desc=descrizione_visiva)
                + t(
                    "brain.soul_anatomy_physique",
                    corp=corporatura,
                    alt=altezza,
                    peso=peso,
                )
                + t("brain.soul_anatomy_measures", misure=misure)
                + dettagli_intimi_str
                + t("brain.soul_anatomy_mind")
                + t(
                    "brain.soul_anatomy_archetype", archetipo=archetipo, essenza=essenza
                )
                + t("brain.soul_anatomy_desires", desideri=fmt_list(desideri))
                + t("brain.soul_anatomy_fears", paure=fmt_list(paure))
                + t("brain.soul_anatomy_skills", abilita=abilita)
                + t("brain.soul_anatomy_history")
                + t("brain.soul_anatomy_history_data", storia=storia_safe)
                + t("brain.soul_anatomy_evolution", evoluzione=evoluzione_safe)
                + t("brain.soul_anatomy_evolution_hint")
                + t("brain.soul_anatomy_relations")
                + t(
                    "brain.soul_anatomy_relations_data",
                    relazioni=fmt_dict_safe(relazioni),
                )
                + t("brain.soul_anatomy_goal", scopo=fmt_list(scopo))
                + t("brain.soul_anatomy_footer")
            )
            
            # --- [NUOVO] MINIFICAZIONE SEMANTICA DEL DNA ---
            soul_deep_structure = self._semantic_minify(soul_deep_structure)
            soul_deep_structure = self._safe_truncate_text(soul_deep_structure, max_tokens=400, keep="start") # [FIX BUG 02] Ridotto da 800 a 400
            
        except Exception as e:
            self.logger.log(
                t("log.brain_evolution_error", name=nome_png, error=e), "WARNING"
            )
            soul_deep_structure = t("log.brain_png_unstructured")

        game_rules_str = self._format_game_rules(game_state, pg_name)

        # --- FIX GENDER AGREEMENT (PROTOCOLLO GRAMMATICALE ASSOLUTO) ---
        is_pg_female = pg_gender.lower() in ["female", "femmina", "f", "donna"]
        pg_gen_label = (
            t("brain.gender_female_label")
            if is_pg_female
            else t("brain.gender_male_label")
        )

        grammar_enforcer = (
            t("brain.grammar_law_female", name=pg_name)
            if is_pg_female
            else t("brain.grammar_law_male", name=pg_name)
        )

        # --- [FIX CRITICO ARCHITETTURA E CACHE] ---
        # Il System Prompt DEVE contenere ESCLUSIVAMENTE l'Ancora di Diamante.
        # Qualsiasi iniezione dinamica (DNA del PNG, regole specifiche) distrugge l'hash
        # e causa un Cache Miss totale (Ricalcolo di 10.000+ token).
        # Spostiamo tutto il DNA nel Vagone Caos (User Prompt).
        
        ancora_text = self._build_anchor_prompt(in_gdr_mode=True)
        
        messages = list()
        messages.append({"role": "system", "content": ancora_text})
        
        # --- COSTRUZIONE CRONOLOGIA (MESSAGGI REALI) ---
        if raw_history:
            for speaker, content in raw_history:
                clean_content = self._sanitize_for_cache(content)
                if clean_content.startswith("[GHOST] "):
                    clean_content = clean_content.replace("[GHOST] ", f"[MESSAGGIO SCRITTO E CANCELLATO, MA LETTO DA {pg_name}]: ")
                
                if speaker.lower() == nome_png.lower():
                    messages.append({"role": "assistant", "content": clean_content})
                elif speaker.lower() == pg_name.lower():
                    messages.append({"role": "user", "content": clean_content})
                else:
                    # Se parla un altro PNG o il DM, lo passiamo come User con prefisso
                    messages.append({"role": "user", "content": f"[{speaker}]: {clean_content}"})
        else:
            # Fallback se raw_history non è passato
            if storia_recente:
                messages.append({"role": "user", "content": f"--- STORIA RECENTE ---\n{storia_recente}"})
                
        # --- COSTRUZIONE CAOS (ULTIMO MESSAGGIO USER) ---
        caos_parts = list()
        
        # 1. INIEZIONE DNA E REGOLE SPECIFICHE DEL PNG (Spostate dal System Prompt per salvare la Cache)
        caos_parts.append(f"{t('brain.dna_directive')}\n{t('brain.dna_directive_body', name=nome_png)}")
        caos_parts.append(f"{t('brain.linguistic_register', tone=tono_scelto)}")
        
        # --- [FIX CRITICO] EPURAZIONE REGOLE RIDONDANTI (SINDROME QA TESTER) ---
        # Rimosse le direttive anti-eco e tone_ban. Il modello 12B va in ansia da prestazione
        # se gli diamo troppe regole negative, iniziando a fare checklist infinite nel <think>.
        # Lasciamo che la sua intelligenza naturale gestisca il tono.
        
        caos_parts.append(soul_deep_structure)
        
        if universal_context:
            caos_parts.append(f"--- CONTESTO UNIVERSALE ---\n{universal_context}")
        if game_rules_str:
            caos_parts.append(game_rules_str)
            
        caos_parts.append(grammar_enforcer)
        
        dynamic_slots = self._assembla_slot("gdr", heart_state_dict or {}, mode="dynamic")
        for cat, content in dynamic_slots.items():
            if content:
                caos_parts.append(f"--- MODULI DINAMICI ({cat.upper()}) ---\n{content}")

        # 2. INIEZIONE CONTESTO VOLATILE
        if exclusion_command:
            caos_parts.append(exclusion_command)
            
        try:
            char_data_temp = json.loads(scheda_png)
            eta_str = _get_json_value(char_data_temp, ["età_fisica", "età_apparente", "age"], "giovane")
            archetipo_str = _get_json_value(char_data_temp, ["archetipo_attuale"], "Sconosciuto")
            caos_parts.append(t("brain.dynamic_linguistic_filter", eta=eta_str, archetipo=archetipo_str))
        except:
            pass
            
        eccitazione_attuale = heart_state_dict.get("eccitazione", 0) if heart_state_dict else 0
        tensione_attuale = heart_state_dict.get("tensione", 50) if heart_state_dict else 50
        if tensione_attuale > 85 or eccitazione_attuale > 85:
            caos_parts.append(t("brain.impulse_engine_override"))
            
        caos_parts.append(t("brain.object_garbage_collector"))
        
        try:
            status_data_temp = json.loads(status_content)
            oggetti_altri = list()
            for obj in status_data_temp.get("oggetti_interattivi", list()):
                possessore = obj.get("possessore", "").lower()
                if possessore and possessore != nome_png.lower() and possessore != "tutti" and possessore != "nessuno":
                    oggetti_altri.append(f"'{obj.get('nome')}' (in mano a {obj.get('possessore')})")
            if oggetti_altri:
                oggetti_vietati_str = ", ".join(oggetti_altri)
                caos_parts.append(f"[BLOCCO FISICO INVIOLABILE]: I seguenti oggetti sono posseduti da altri: {oggetti_vietati_str}. NON PUOI usarli.")
        except:
            pass
            
        safe_status_content = self._safe_truncate_text(self._semantic_minify(status_content), max_tokens=300, keep="start")
        caos_parts.append(t("brain.physical_reality_header") + "\n" + safe_status_content)
        
        if rag_memories:
            safe_memories = list()
            for m in rag_memories:
                m_trunc = m[:300] + t("brain.rag_user_truncated") if len(m) > 300 else m
                safe_memories.append(f"<|ISOLATED_MEMORY_BLOCK|>\n[RICORDO DAL PASSATO]: {m_trunc}\n<|END_ISOLATED_MEMORY|>")
            
            # --- [NUOVO] SCUDO ANTI-ALLUCINAZIONE NOMI ---
            anti_hallucination_shield = t("brain.rag_anti_hallucination_names")
            caos_parts.append(t("brain.past_memories_label") + "\n".join(safe_memories) + "\n\n" + anti_hallucination_shield)
            
        if dati_biometrici:
            caos_parts.append(t("brain.sensory_data_format", data=dati_biometrici))
            
        if last_dm_narration:
            caos_parts.append(t("brain.dm_last_narration_header", narration=last_dm_narration))
            
        if narrative_buffer:
            safe_buffer = self._safe_truncate_text(self._semantic_minify(narrative_buffer), max_tokens=800, keep="end")
            caos_parts.append(f"{t('brain.remote_session_background')}\n[ATTENZIONE: Memoria compressa. NON imitare il formato AAAK.]\n{safe_buffer}")
            
        if dynamic_profile:
            caos_parts.append(f"[PROFILO DINAMICO UTENTE]:\n{dynamic_profile}")
            
        caos_parts.append(safe_cronaca)
        
        ruolo_key = ruolo_nel_turno.lower()
        istruzione_ruolo = t(f"prompts.gdr_laws.istruzioni_gdr.{ruolo_key}")
        if istruzione_ruolo.startswith("["):
            istruzione_ruolo = ""
        istruzione_ruolo = self._replace_all_name_variants(istruzione_ruolo, pg_name)
        if istruzione_ruolo:
            caos_parts.append(istruzione_ruolo)
            
        caos_parts.append(self._get_language_instruction(lang))
        
        comando_supremo_template = self._get_internal_prompt("comando_supremo_png")
        aspetto_fisico = descrizione_visiva
        try:
            status_data_temp = json.loads(status_content)
            my_char = next((c for c in status_data_temp.get("personaggi", list()) if c.get("nome", "").lower() == nome_png.lower()), None)
            if my_char and my_char.get("abbigliamento"):
                aspetto_fisico += f" | Indossi: {my_char.get('abbigliamento')}"
        except:
            pass
            
        comando_supremo = self._safe_replace(comando_supremo_template, "nome_png", nome_png.upper())
        comando_supremo = self._safe_replace(comando_supremo, "aspetto_fisico", aspetto_fisico)
        comando_supremo = self._safe_replace(comando_supremo, "tono_scelto", tono_scelto)
        comando_supremo = self._safe_replace(comando_supremo, "safe_input", safe_input)
        comando_supremo = self._safe_replace(comando_supremo, "png_gen_it", png_gen_it)
        comando_supremo = self._safe_replace(comando_supremo, "pg_gen_it", pg_gen_it)
        comando_supremo = self._safe_replace(comando_supremo, "tensione_attuale", str(tensione_attuale))
        
        if ruolo_nel_turno == "ECOSISTEMA":
            comando_supremo += t("brain.ecosystem_override", nome_pg=pg_name)
            
        # --- [FIX CRITICO] GATEKEEPER COGNITIVO (COMANDO SUPREMO DINAMICO) ---
        if getattr(self, "is_large_model", False):
            # Modelli >= 11B: Istruzione pulita e diretta per evitare la Sindrome del QA Tester
            comando_supremo_large = t("brain.supreme_command_large_model", name=nome_png.upper(), pg_name=pg_name)
            caos_parts.append(comando_supremo_large)
        else:
            # Modelli <= 10B: Regole rigide per mantenere la formattazione
            caos_parts.append(comando_supremo)
        
        # --- [FIX CRITICO] MANDATO ANTI-CHECKLIST (SINDROME QA TESTER) ---
        # Impedisce ai modelli 12B+ di entrare in loop infiniti verificando le regole una ad una.
        caos_parts.append(t("brain.reasoning_mandate_no_lists"))
        
        # --- [FIX CRITICO] IN-STREAM WORLD UPDATE INSTRUCTION (IDEA 4) ---
        caos_parts.append(t("brain.instream_world_update_mandate"))
        
        # --- [FIX CRITICO] NUKE ANTI-ROBOT ALLA FINE ASSOLUTA ---
        caos_parts.append(t("brain.anti_robot_nuke"))
        
        caos_text = self.PROMPT_SEPARATOR.join([self._sanitize_for_cache(p) for p in caos_parts if p])
        caos_text = self._replace_all_name_variants(caos_text, pg_name)
        
        messages.append({"role": "user", "content": caos_text})

        # ---[NUOVO] VALIDATORE ANTI-ECO E ANTI-PASSIVITÀ (RETRY LOOP POTENZIATO) ---
        max_retries = 2
        response = ""

        for attempt in range(max_retries + 1):
            #[FIX CRITICO MUTISMO E LOOP]
            # Reintrodotta una micro-penalità (0.15). È abbastanza bassa da non ammutolire il modello,
            # ma sufficiente a "pungolarlo" se entra in un loop infinito di parole identiche nel <think>.
            raw_response = self._genera_pensiero(
                messages,
                temperature=temp_jittered,
                presence_penalty=0.15,
                frequency_penalty=0.15,
                max_tokens=8192, # [FIX CRITICO] Aumentato a 8192 per garantire spazio vitale assoluto ai modelli Reasoning
                in_gdr_mode=True, # [FIX CRITICO CACHE] Fondamentale per allineare l'Ancora
                enable_streaming=True
            )

            is_error = False
            punitive_prompt = ""

            # --- [FIX CRITICO] IGNORARE I PENSIERI NELLA VALIDAZIONE ---
            # Rimuoviamo temporaneamente il blocco <think> per non punire il modello
            # se usa JSON o strutture tecniche durante il suo ragionamento interno.
            validation_text = re.sub(r"<think>.*?</think>", "", raw_response, flags=re.IGNORECASE | re.DOTALL).strip()

            # --- [NUOVO] SINCRONIZZAZIONE FILTRO MARKDOWN ---
            # Applichiamo lo stesso filtro di chat.py per validare SOLO la vera risposta, ignorando i preamboli.
            match_reazione = re.search(r"(?:##|\*\*)\s*(?:REAZIONE|RISPOSTA|AZIONE)(?:\s+DI\s+[A-Za-zÀ-ÿ\s]+)?[:\*\*]*\s*\n", validation_text, re.IGNORECASE)
            if match_reazione:
                validation_text = validation_text[match_reazione.end():].strip()
            validation_text = re.sub(r"---?\s*ANALISI.*?(?:---|##|\n\n)", "", validation_text, flags=re.IGNORECASE | re.DOTALL).strip()

            # ---[NUOVO] ANTI-JSON SHIELD (FORMAT BLEEDING) ---
            # Se la risposta inizia con json, ```json, {, oppure contiene palesemente chiavi JSON ("chiave":)
            #[FIX] Rimosso il vincolo della parentesi chiusa '}' per intercettare anche i JSON troncati.
            # if re.search(r'^\s*(?:```json|json)?\s*\{|"\w+"\s*:\s*(?:\{|"|\[)', validation_text, re.IGNORECASE):
            if re.search(r'^\s*(?:```\w*\s*|json\s*)?\{', validation_text, re.IGNORECASE) or "```json" in validation_text.lower():
                is_error = True
                punitive_prompt = "\n\n[ERRORE CRITICO DI FORMATTAZIONE]: Hai risposto usando un formato JSON o un blocco di codice. Questo è TASSATIVAMENTE VIETATO. Devi rispondere ESCLUSIVAMENTE con un testo narrativo, discorsivo e in prima persona. Riscrivi la tua reazione ora."
                self.logger.log(t("log.brain_format_bleeding", name=nome_png), "WARNING")
            else:
                # ---[NUOVO] ANTI-TRUNCATION SHIELD ---
                # Verifica se la risposta è stata tagliata a metà dal limite token
                # [FIX CRITICO] Rimuoviamo il tag INTENT prima di controllare la punteggiatura finale,
                # altrimenti il modello inganna lo scudo appiccicando [INTENT: 1] a una frase tagliata.
                text_without_intent = re.sub(r"\[INTENT:.*?\]", "", validation_text, flags=re.IGNORECASE).strip()
                clean_end = text_without_intent.strip()
                valid_endings = (".", "!", "?", '"', "'", "*", "]", ">", "»", "-", "~")
                
                if clean_end and not clean_end.endswith(valid_endings):
                    is_error = True
                    punitive_prompt = "\n\n[ERRORE CRITICO]: La tua risposta è stata troncata a metà perché hai scritto troppo. DEVI essere più concisa (massimo 3-4 paragrafi) e assicurarti di concludere il pensiero con un punto fermo. Riscrivi la tua reazione ora, più breve."
                    self.logger.log(t("log.brain_truncation_detected", name=nome_png), "WARNING")
                else:
                    # --- [FIX BUG 3] CONTROLLO ANTI-PASSIVITÀ (VITA AUTONOMA) ---
                    # Pulizia rapida in linea per rimuovere i tag[INTENT: ...] e calcolare la lunghezza reale
                    clean_check = re.sub(r"\[.*?\]", "", validation_text).strip().lower()
                    
                    # [FIX CRITICO] Abbassato il limite da 50 a 15 caratteri.
                    # Se un PNG vuole solo dire "Ti guardo. [INTENT: 2]", deve poterlo fare senza essere punito.
                    if len(clean_check) < 15:
                        is_error = True
                        punitive_prompt = "\n\n[ERRORE CRITICO]: Non hai generato alcuna risposta parlata o azione valida, oppure è troppo corta. Devi scrivere la tua reazione effettiva!"
                        self.logger.log(f"Cervello: Rilevata passività/assenza di testo per {nome_png}. Innesco Retry punitivo...", "WARNING")
                    elif "osserva" in clean_check and "silenzio" in clean_check and len(clean_check) < 80:
                        # --- [FIX CRITICO] SILENZIO ATTIVO CONSENTITO SOLO AGLI SPETTATORI ---
                        # Se l'utente parla al gruppo (GRUPPO) o direttamente al PNG (BERSAGLIO), il silenzio è vietato.
                        # Il silenzio è accettato SOLO se il PNG è uno SPETTATORE (l'utente sta parlando con qualcun altro).
                        if ruolo_nel_turno in ["BERSAGLIO", "GRUPPO"]:
                            is_error = True
                            punitive_prompt = "\n\n[MANDATO DI EMERGENZA]: L'utente si è rivolto a te o al gruppo! La tua risposta è troppo passiva. È TASSATIVAMENTE VIETATO limitarsi a guardare in silenzio. DEVI rispondere, salutare o compiere un'azione fisica decisa!"
                            self.logger.log(f"Cervello: Rilevata passività (osserva in silenzio) per {nome_png} (Ruolo: {ruolo_nel_turno}). Innesco Retry punitivo...", "WARNING")
                        else:
                            self.logger.log(f"Cervello: {nome_png} osserva in silenzio (Ruolo: {ruolo_nel_turno}). Accettato.", "DEBUG")

            # CONTROLLO ANTI-ECO (MICRO-MATCHING CHIRURGICO)
            # Aggiornato per matchare il nuovo formato della cronaca:[NOME reagisce dicendo/facendo]:
            previous_responses = re.findall(
                t("brain.echo_detection_pattern"),
                cronaca_turno_corrente,
                flags=re.DOTALL,
            )

            for prev_resp in previous_responses:
                prev_clean = re.sub(r"\[.*?\]", "", prev_resp).strip()
                curr_clean = re.sub(r"\[.*?\]", "", validation_text).strip()

                if len(prev_clean) > 20 and len(curr_clean) > 20:
                    # 1. Similarità Globale
                    sim = SequenceMatcher(
                        None, curr_clean.lower(), prev_clean.lower()
                    ).ratio()

                    # 2. Similarità Incipit (Prime 80 lettere) - [FIX BUG 4] Allentata la morsa
                    incipit_sim = SequenceMatcher(
                        None, curr_clean[:80].lower(), prev_clean[:80].lower()
                    ).ratio()

                    # 3. Similarità Finale (Ultime 80 lettere) - [FIX BUG 4] Allentata la morsa
                    ending_sim = SequenceMatcher(
                        None, curr_clean[-80:].lower(), prev_clean[-80:].lower()
                    ).ratio()

                    # --- [FIX OPZIONE 3] SOGLIE DINAMICHE (RILASSAMENTO PROGRESSIVO) ---
                    # Ad ogni tentativo fallito, il sistema diventa più tollerante.
                    # Preferiamo una risposta simile piuttosto che un blocco o un'allucinazione.
                    # attempt 0: sim > 0.65, incipit > 0.85 (Severo)
                    # attempt 1: sim > 0.75, incipit > 0.90 (Tollerante)
                    # attempt 2: sim > 0.85, incipit > 0.95 (Quasi disattivato)
                    
                    base_sim_threshold = 0.65 + (attempt * 0.10)
                    base_edge_threshold = 0.85 + (attempt * 0.05)

                    if sim > base_sim_threshold or incipit_sim > base_edge_threshold or ending_sim > base_edge_threshold:
                        is_error = True
                        # SILENT RETRY: Nessun "Errore di sistema". Solo un mandato narrativo assoluto.
                        punitive_prompt = "\n\n" + t(
                            "brain.divergence_mandate", name=nome_png.upper()
                        )
                        self.logger.log(
                            t(
                                "log.brain_png_anti_eco_warning",
                                sim=f"{sim:.2f}",
                                incipit=f"{incipit_sim:.2f}",
                                end=f"{ending_sim:.2f}",
                                attempt=attempt + 1,
                                max=max_retries,
                            ),
                            "WARNING",
                        )
                        break

            if is_error and attempt < max_retries:
                # CURA SINDROME WESTWORLD: Non aggiungiamo la risposta sbagliata come 'assistant'.
                # Modifichiamo o appendiamo il mandato punitivo all'ultimo messaggio 'user'.
                if punitive_prompt not in messages[-1]["content"]:
                    messages[-1]["content"] += punitive_prompt

                # --- [FIX CRITICO] INVERSIONE TERMICA DEL RETRY ---
                # I modelli Instruct (Gemma 3/4) impazziscono ad alte temperature.
                # Se sbagliano, dobbiamo ABBASSARE la temperatura per forzarli a obbedire alla logica.
                temp_jittered = max(0.1, temp_jittered - 0.30)
                continue # Forza il prossimo tentativo del loop
            else:
                response = raw_response
                break

        # ---[FIX v27.41] ACTIVE BOUNCER LOGIC (GDR) ---
        intent_match = re.search(r"\[INTENT:\s*([^\]]+)\]", response)
        if intent_match:
            original_intent = intent_match.group(1).strip()
            
            # 1. Risoluzione ID -> Emozione (Protocollo Copione)
            is_id_resolution = False
            if original_intent.isdigit() and original_intent in self.emotion_id_map:
                corrected_intent = self.emotion_id_map[original_intent]
                is_id_resolution = True
            else:
                # Fallback di sicurezza se l'LLM ha scritto una parola invece del numero
                corrected_intent = get_closest_emotion(original_intent, self.valid_emotions)

            if corrected_intent != original_intent:
                if is_id_resolution:
                    self.logger.log(f"[INTENT] Risoluzione ID (GDR): '{original_intent}' -> '{corrected_intent}'", "INTENT")
                else:
                    self.logger.log(
                        t(
                            "log.brain_bouncer_gdr",
                            old=original_intent,
                            new=corrected_intent,
                        ),
                        "INTENT",
                    )
                response = response.replace(
                    f"[INTENT: {original_intent}]", f"[INTENT: {corrected_intent}]"
                )

        return response

    def pensa_reazione_istintiva(
        self,
        user_input: str,
        scheda_png: str,
        nome_png: str,
        pg_name: str,
        lang: str = "it",
        override_brain: Optional[LlamaServerClient] = None
    ) -> str:
        """
        Genera una micro-reazione istintiva di emergenza quando il PNG rimane silente.
        Bypassa la cronaca e le dinamiche di gruppo per garantire un output.
        """
        self.logger.log(t("log.brain_instinctive_reaction", name=nome_png), "WARNING")
        
        # Estrazione rapida DNA per non appesantire il prompt
        archetipo = "Sconosciuto"
        essenza = "Un'anima."
        try:
            char_data = json.loads(scheda_png)
            archetipo = _get_json_value(char_data, ["archetipo_attuale"], "Sconosciuto")
            essenza = _get_json_value(char_data, ["essenza_fondamentale"], "Un'anima.")
        except:
            pass

        prompt_template = self._get_internal_prompt("reazione_istintiva")
        prompt = self._safe_replace(prompt_template, "nome_png", nome_png)
        prompt = self._safe_replace(prompt, "archetipo", archetipo)
        prompt = self._safe_replace(prompt, "essenza", essenza)
        prompt = self._safe_replace(prompt, "user_input", user_input)
        prompt = self._replace_all_name_variants(prompt, pg_name)
        prompt += self._get_language_instruction(lang)

        # [FIX CRITICO] Separazione System/User per evitare allucinazioni
        messages = list()
        # --- [FIX CRITICO] BLOCCO THINKING ---
        # Disabilitiamo esplicitamente il pensiero per forzare l'output testuale immediato
        messages.append({"role": "system", "content": "Sei un personaggio in un gioco di ruolo. Devi reagire d'istinto con una singola frase. NON usare formattazioni speciali, JSON o tag. È TASSATIVAMENTE VIETATO usare i tag <think>. Scrivi direttamente la tua reazione."})
        messages.append({"role": "user", "content": prompt})
        
        # Temperatura alta per istinto, max_tokens basso per brevità
        return self._genera_pensiero(messages, temperature=0.8, max_tokens=150, override_brain=override_brain, in_gdr_mode=True, enable_streaming=True) # [FIX CRITICO CACHE] Allineamento Ancora

    def pensa_meta_conversazione_png(
        self,
        user_input: str,
        storia_recente: str,
        scheda_png: str,
        nome_png: str,
        pg_name: str,
        status_content: str = "",
        narrative_buffer: str = "",
        dati_biometrici: str = "",
        pg_gender: str = "Male",
        lang: str = "it",
        system_paths: Dict[str, str] = None,
        heart_state_dict: dict = None,
        rag_memories: List[str] = None,
        dynamic_profile: str = "",
        raw_history: list = None, # [FIX CRITICO CACHE]
    ) -> str:
        """
        Versione potenziata della Meta-Conversazione.
        Strutturalmente identica a 'pensa_come_png' ma con iniezione del contesto 'Tempo Fermo'.
        """
        self.logger.log(t("log.brain_meta_immersion", name=nome_png))

        # --- [FIX v108.3] DEFINIZIONE GENERI ALL'INIZIO ASSOLUTO (ANTI-NAMEERROR) ---
        _raw_png_gender = self._extract_gender(scheda_png)
        png_gen_it = (
            "FEMMINILE"
            if _raw_png_gender.lower() in ["female", "femmina", "f", "donna"]
            else "MASCHILE"
        )
        pg_gen_it = (
            "FEMMINILE"
            if pg_gender.lower() in ["female", "femmina", "f", "donna"]
            else "MASCHILE"
        )
        # --------------------------------------------------------------------------

        # 1. De-subjectivize (Standard)
        objective_input = self._de_subjectivize_input(user_input, pg_name)

        # 2. Base Context (Subconscious)
        # --- INIEZIONE FREEDOM HEADER DINAMICO (v27.0) ---
        prompt_completo = self._get_freedom_header()
        prompt_completo += f"{t('log.brain_meta_subconscious_header')}\n"

        if narrative_buffer:
            prompt_completo += (
                f"\n[MEMORIA STORICA DELLA SESSIONE]:\n{narrative_buffer}\n"
            )

        if dati_biometrici:
            prompt_completo += f"\n[SENSORY_DATA]: {dati_biometrici}\n"

        prompt_completo += "\n---\n\n"

        # 3. META-TRUTH INJECTION (Il cuore della differenza)
        prompt_completo += (
            "\n"
            + t("brain.meta_pause_scenario")
            + "\n"
            + t("brain.meta_pause_rules", png_name=nome_png, pg_name=pg_name)
            + "\n---\n\n"
        )

        # 4. DNA & Reality
        prompt_completo += f"{t('brain.dna_header')}\n{scheda_png}\n\n"
        if status_content:
            prompt_completo += (
                f"{t('brain.physical_reality_header')}\n{status_content}\n\n"
            )

        # 5. Protocols (Consenso, Carnalità, Regole)
        # --- [NUOVO FASE 16] ASSEMBLAGGIO MODULI COGNITIVI ---
        slots = self._assembla_slot("gdr", heart_state_dict or {})

        # 6. Incarnation Prompt (Reusing standard one with tweaks)
        # --- MODIFICA v32.0: USO COSTANTI DINAMICHE ---
        vangelo_incarnazione = self._get_gdr_law("meta_conversazione_png")

        # [FIX v108.9] Sostituzione blocchi nidificati PRIMA dei valori
        vangelo_incarnazione = self._safe_replace(
            vangelo_incarnazione, "SLOT_IDENTITY", slots["identity"]
        )
        vangelo_incarnazione = self._safe_replace(
            vangelo_incarnazione, "SLOT_BEHAVIOR", slots["behavior"]
        )
        vangelo_incarnazione = self._safe_replace(
            vangelo_incarnazione, "SLOT_RESTRICTION", slots["restriction"]
        )
        vangelo_incarnazione = self._safe_replace(
            vangelo_incarnazione, "SLOT_SYSTEM", slots["system"]
        )

        # Replace placeholders
        vangelo_incarnazione = self._safe_replace(
            vangelo_incarnazione, "scheda_png", t("brain.see_dna_above")
        )
        vangelo_incarnazione = self._safe_replace(
            vangelo_incarnazione, "status_content", t("brain.see_reality_above")
        )
        vangelo_incarnazione = self._safe_replace(
            vangelo_incarnazione, "nome_png", nome_png.upper()
        )
        vangelo_incarnazione = self._safe_replace(
            vangelo_incarnazione, "pg_name", pg_name
        )

        prompt_completo += (
            f"--- MANDATO DI INCARNAZIONE ---\n{vangelo_incarnazione}\n\n"
        )

        # 7. Language & Gender
        # [FIX v108.2] Definizione ultra-sicura dei generi
        _raw_png_gender = self._extract_gender(scheda_png)
        png_gen_it = (
            t("brain.gender_female_grammar")
            if _raw_png_gender.lower() in ["female", "femmina", "f", "donna"]
            else t("brain.gender_male_grammar")
        )
        pg_gen_it = (
            t("brain.gender_female_grammar")
            if pg_gender.lower() in ["female", "femmina", "f", "donna"]
            else t("brain.gender_male_grammar")
        )

        vangelo_incarnazione = self._safe_replace(
            vangelo_incarnazione, "pg_gender_label", pg_gen_it
        )
        # ----------------------------

        prompt_completo += (
            f"--- MANDATO DI INCARNAZIONE ---\n{vangelo_incarnazione}\n\n"
        )

        prompt_completo += self._get_language_instruction(lang)

        # [NUOVO v7.0] COSTRUZIONE SANDWICH META-PAUSA
        dynamic_slots = self._assembla_slot(
            "gdr", heart_state_dict or {}, mode="dynamic"
        )

       # 1. L'ANCORA CONDIVISA (100% Cache Hit)
        ancora_text = self._build_anchor_prompt(in_gdr_mode=True)

        # 2. IL CAOS SPECIFICO (0% Cache Hit)
        caos_parts = list()

        # ---[NUOVO] FILTRO LINGUISTICO DINAMICO (MIGLIORIA 3) ---
        try:
            char_data_temp = json.loads(scheda_png)
            eta_str = _get_json_value(char_data_temp, ["età_fisica", "età_apparente", "age"], "giovane")
            archetipo_str = _get_json_value(char_data_temp, ["archetipo_attuale"], "Sconosciuto")
            caos_parts.append(t("brain.dynamic_linguistic_filter", eta=eta_str, archetipo=archetipo_str))
        except:
            pass

        # --- [NUOVO] MOTORE DELL'IMPULSO (MIGLIORIA 4) ---
        eccitazione_attuale = heart_state_dict.get("eccitazione", 0) if heart_state_dict else 0
        tensione_attuale = heart_state_dict.get("tensione", 50) if heart_state_dict else 50
        if tensione_attuale > 85 or eccitazione_attuale > 85:
            caos_parts.append(t("brain.impulse_engine_override"))

        # --- [NUOVO] GARBAGE COLLECTOR OGGETTI (MIGLIORIA 2) ---
        caos_parts.append(t("brain.object_garbage_collector"))

        # --- [NUOVO] INVENTARIO ESCLUSIVO (ANTI-FURTO D'AZIONE) ---
        try:
            status_data_temp = json.loads(status_content)
            oggetti_altri =[]
            for obj in status_data_temp.get("oggetti_interattivi",[]):
                possessore = obj.get("possessore", "").lower()
                if possessore and possessore != nome_png.lower() and possessore != "tutti" and possessore != "nessuno":
                    oggetti_altri.append(f"'{obj.get('nome')}' (in mano a {obj.get('possessore')})")
            
            if oggetti_altri:
                oggetti_vietati_str = ", ".join(oggetti_altri)
                caos_parts.append(f"[BLOCCO FISICO INVIOLABILE]: I seguenti oggetti sono attualmente posseduti da altre persone: {oggetti_vietati_str}. È FISICAMENTE IMPOSSIBILE per te usarli, berli o toccarli. Ignorali.")
        except:
            pass

        # ---[FIX FASE 1] EPURAZIONE JSON GREZZO IN META-PAUSA ---
        soul_deep_structure = ""
        try:
            char_data = json.loads(scheda_png)

            def get_val(keys, default=""):
                return _get_json_value(char_data, keys, default)

            nome_completo = get_val(["nome_completo", "nome", "name"], nome_png)
            eta = get_val(["età_fisica", "età_apparente", "age"], "Sconosciuta")
            genere = get_val(["genere", "gender"], "Female")
            
            # ---[FIX CRITICO] ESTRAZIONE DINAMICA TOTALE (ANTI-ALLUCINAZIONE) ---
            dati_fisici_dict = char_data.get("dati_fisici_ed_estetici", {})
            descrizione_visiva_parts = list()
            for k, v in dati_fisici_dict.items():
                if k != "dettagli_intimi" and isinstance(v, str):
                    clean_key = k.replace("_", " ").title()
                    descrizione_visiva_parts.append(f"{clean_key}: {v}")
            
            if descrizione_visiva_parts:
                descrizione_visiva_raw = " | ".join(descrizione_visiva_parts)
            else:
                descrizione_visiva_raw = get_val(["descrizione_visiva"], "Una ragazza.")
                
            descrizione_visiva = self._safe_truncate_text(
                descrizione_visiva_raw, max_tokens=100
            )
            
            corporatura = get_val(["corporatura"], "Normale")
            seno = get_val(["seno"], "Normale")
            glutei = get_val(["glutei"], "Normali")
            genitali = get_val(["genitali"], "Normali")
            segni = get_val(["segni_particolari"], "Nessuno")
            archetipo = get_val(["archetipo_attuale"], "Nessuno")
            essenza = self._safe_truncate_text(
                get_val(["essenza_fondamentale"], "Un'anima."), max_tokens=300
            )
            storia = get_val(["storia_"], "")
            evoluzione = get_val(["evoluzione_personale_"], "")

            #[FIX CRITICO] Limiti espansi per coerenza con il pensiero standard
            storia_safe = self._safe_truncate_text(storia, max_tokens=800)
            evoluzione_safe = self._safe_truncate_text(evoluzione, max_tokens=500)

            # --- [FIX BUG] DEFINIZIONE RPG_BLOCK MANCANTE IN META-PAUSA ---
            scheda_rpg = get_val(["scheda_rpg"], {})
            rpg_block = ""
            if scheda_rpg:
                dati_base = scheda_rpg.get("dati_base", {})
                combat = scheda_rpg.get("combattimento", {})
                equip = scheda_rpg.get("equipaggiamento", {})
                magia = scheda_rpg.get("magia_e_privilegi", {})

                hp_max = combat.get("hp_massimi", 1)
                hp_curr = combat.get("hp_attuali", 1)
                
                rpg_block = t("brain.rpg_sheet_header")
                rpg_block += t("brain.rpg_sheet_class", classe=dati_base.get("classe", ""), razza=dati_base.get("razza", ""), livello=dati_base.get("livello", 1))
                rpg_block += t("brain.rpg_sheet_align", allineamento=dati_base.get("allineamento", ""))
                rpg_block += t("brain.rpg_sheet_stats", curr=hp_curr, max=hp_max, ca=combat.get("classe_armatura", 10))
                
                armi =[f"{a.get('nome')} ({a.get('danno')})" for a in equip.get("armi", list())]
                rpg_block += t("brain.rpg_sheet_weapons", armi=", ".join(armi) if armi else "Disarmato")
                
                inv = equip.get("inventario", list())
                monete = equip.get("monete", {})
                rpg_block += t("brain.rpg_sheet_inv", inv=", ".join(inv) if inv else "Vuoto")
                rpg_block += t("brain.rpg_sheet_wealth", oro=monete.get("oro", 0), argento=monete.get("argento", 0), rame=monete.get("rame", 0))
                
                incantesimi = magia.get("incantesimi", list())
                if incantesimi:
                    rpg_block += t("brain.rpg_sheet_spells", spells=", ".join(incantesimi))
                rpg_block += "\n"
            else:
                rpg_block = t("brain.rpg_sheet_civilian")

            eccitazione_attuale = (
                heart_state_dict.get("eccitazione", 0) if heart_state_dict else 0
            )
            is_nsfw_context = eccitazione_attuale >= 80
            dettagli_intimi_str = (
                f"DETTAGLI INTIMI:\n- Seno: {seno}\n- Glutei: {glutei}\n- Genitali: {genitali}\n- Segni: {segni}\n\n"
                if is_nsfw_context
                else ""
            )

            soul_deep_structure = (
                t("log.brain_meta_anatomy_header")
                + "\n"
                + t(
                    "brain.soul_anatomy_identity_data",
                    nome=nome_completo,
                    eta=eta,
                    genere=genere,
                )
                + t("brain.soul_anatomy_aspect", desc=descrizione_visiva)
                + t("brain.soul_anatomy_body")
                + t("brain.soul_anatomy_physique", corp=corporatura, alt="", peso="")
                + dettagli_intimi_str
                + t(
                    "brain.soul_anatomy_archetype", archetipo=archetipo, essenza=essenza
                )
                + t("brain.soul_anatomy_history_data", storia=storia_safe)
                + t("brain.soul_anatomy_evolution", evoluzione=evoluzione_safe)
                + rpg_block
            )
            
            # --- [NUOVO] MINIFICAZIONE SEMANTICA DEL DNA ---
            soul_deep_structure = self._semantic_minify(soul_deep_structure)
            
        except Exception as e:
            self.logger.log(
                t("log.brain_meta_extraction_error", name=nome_png, error=e), "WARNING"
            )
            soul_deep_structure = self._safe_truncate_text(self._semantic_minify(scheda_png), max_tokens=500)

        # Spostati dall'Ancora al Caos per garantire il Prefix Matching:
        safe_status = self._safe_truncate_text(self._semantic_minify(status_content), max_tokens=1500, keep="start")
        caos_parts.append(f"{t('brain.physical_reality_header')}\n{safe_status}")

        if rag_memories:
            # --- [PROTOCOLLO SEMANTIC RoPE] Isolamento Temporale ---
            safe_memories = list()
            for m in rag_memories:
                m_trunc = m[:1500] + t("brain.rag_user_truncated") if len(m) > 1500 else m
                safe_memories.append(f"<|ISOLATED_MEMORY_BLOCK|>\n[RICORDO DAL PASSATO]: {m_trunc}\n<|END_ISOLATED_MEMORY|>")
            caos_parts.append(t("brain.past_memories_label") + "\n".join(safe_memories))

        if narrative_buffer:
            safe_buffer = self._safe_truncate_text(self._semantic_minify(narrative_buffer), max_tokens=1500, keep="end")
            # --- [LEGGE 4] SCUDO ANTI-MIMESI AAAK ---
            caos_parts.append(f"{t('brain.remote_session_background')}\n[ATTENZIONE: Il testo seguente è una memoria compressa di sistema. È TASSATIVAMENTE VIETATO imitare il formato [Soggetto]->(Azione)->[Oggetto]. Parla in modo naturale.]\n{safe_buffer}")
        if dati_biometrici:
            caos_parts.append(t("brain.sensory_data_format", data=dati_biometrici))

        # --- [NUOVO] PROFILO DINAMICO (LOCAL SUPERMEMORY) ---
        if dynamic_profile:
            caos_parts.append(f"[PROFILO DINAMICO UTENTE]:\n{dynamic_profile}")

        # --- [FIX CRASH] INIEZIONE COORDINATE SPAZIALI ---
        if system_paths:
            system_paths_str = "\n".join(
                [f"- {k}: {v}" for k, v in system_paths.items()]
            )
            caos_parts.append(
                f"{t('brain.spatial_coordinates_header')}\n{system_paths_str}"
            )

        caos_parts.append(
            t("brain.meta_pause_scenario")
            + "\n"
            + t("brain.meta_pause_rules", png_name=nome_png, pg_name=pg_name)
        )

        # --- [FIX CRITICO] SCUDI INCONDIZIONATI ---
        caos_parts.append(t("brain.rag_anti_hallucination_names"))
        caos_parts.append(t("brain.anti_robot_nuke"))

        if status_content:
            safe_status = self._safe_truncate_text(status_content, max_tokens=1500)
            caos_parts.append(t("brain.meta_pause_frozen_reality") + safe_status)

        vangelo_incarnazione = self._get_gdr_law("meta_conversazione_png")
        vangelo_incarnazione = self._safe_replace(
            vangelo_incarnazione, "SLOT_IDENTITY", ""
        )
        vangelo_incarnazione = self._safe_replace(
            vangelo_incarnazione, "SLOT_BEHAVIOR", ""
        )
        vangelo_incarnazione = self._safe_replace(
            vangelo_incarnazione, "SLOT_RESTRICTION", ""
        )
        vangelo_incarnazione = self._safe_replace(
            vangelo_incarnazione, "SLOT_SYSTEM", ""
        )
        # --- FIX DEBUG: Il DNA ora si trova nel Caos, appena sopra questo blocco ---
        vangelo_incarnazione = self._safe_replace(
            vangelo_incarnazione, "scheda_png", "[VEDI SEZIONE DNA SOPRA]"
        )
        vangelo_incarnazione = self._safe_replace(
            vangelo_incarnazione, "status_content", "[VEDI SEZIONE REALTÀ SOPRA]"
        )
        vangelo_incarnazione = self._safe_replace(
            vangelo_incarnazione, "nome_png", nome_png.upper()
        )
        vangelo_incarnazione = self._safe_replace(
            vangelo_incarnazione, "pg_name", pg_name
        )
        vangelo_incarnazione = self._safe_replace(
            vangelo_incarnazione, "pg_gender_label", pg_gen_it
        )

        caos_parts.append(f"--- MANDATO DI INCARNAZIONE ---\n{vangelo_incarnazione}")
        caos_parts.append(self._get_language_instruction(lang))

        comando_supremo_template = self._get_internal_prompt("comando_supremo_meta")
        
        # --- [NUOVO] ESTRAZIONE ASPETTO FISICO PER ANTI-ALLUCINAZIONE ---
        aspetto_fisico = descrizione_visiva
        try:
            status_data_temp = json.loads(status_content)
            my_char = next((c for c in status_data_temp.get("personaggi", list()) if c.get("nome", "").lower() == nome_png.lower()), None)
            if my_char and my_char.get("abbigliamento"):
                aspetto_fisico += f" | Indossi: {my_char.get('abbigliamento')}"
        except:
            pass

        comando_supremo = self._safe_replace(
            comando_supremo_template, "nome_png", nome_png.upper()
        )
        comando_supremo = self._safe_replace(
            comando_supremo, "aspetto_fisico", aspetto_fisico
        )
        comando_supremo = self._safe_replace(
            comando_supremo, "objective_input", objective_input
        )
        comando_supremo = self._safe_replace(comando_supremo, "png_gen_it", png_gen_it)
        comando_supremo = self._safe_replace(comando_supremo, "pg_gen_it", pg_gen_it)
        
        # --- [FIX CRITICO] GATEKEEPER COGNITIVO (COMANDO SUPREMO DINAMICO META-PAUSA) ---
        if getattr(self, "is_large_model", False):
            comando_supremo_meta_large = t("brain.supreme_command_meta_large_model", name=nome_png.upper(), pg_name=pg_name)
            caos_parts.append(comando_supremo_meta_large)
        else:
            caos_parts.append(comando_supremo)

        # --- [FIX CRITICO] MANDATO ANTI-CHECKLIST (SINDROME QA TESTER) ---
        caos_parts.append(t("brain.reasoning_mandate_no_lists"))

        caos_text = self.PROMPT_SEPARATOR.join(
            [self._sanitize_for_cache(p) for p in caos_parts if p]
        )
        caos_text = self._replace_all_name_variants(caos_text, pg_name)

        messages = [{"role": "system", "content": ancora_text}]
        
        # --- COSTRUZIONE CRONOLOGIA (MESSAGGI REALI) ---
        if raw_history:
            for speaker, content in raw_history:
                clean_content = self._sanitize_for_cache(content)
                if clean_content.startswith("[GHOST] "):
                    clean_content = clean_content.replace("[GHOST] ", f"[MESSAGGIO SCRITTO E CANCELLATO, MA LETTO DA {pg_name}]: ")
                
                if speaker.lower() == nome_png.lower():
                    messages.append({"role": "assistant", "content": clean_content})
                elif speaker.lower() == pg_name.lower():
                    messages.append({"role": "user", "content": clean_content})
                else:
                    messages.append({"role": "user", "content": f"[{speaker}]: {clean_content}"})
        else:
            if storia_recente:
                caos_text = f"--- STORIA RECENTE ---\n{storia_recente}\n\n" + caos_text

        messages.append({"role": "user", "content": caos_text})
        
        return self._genera_pensiero(messages, temperature=0.7, in_gdr_mode=True, enable_streaming=True) # [FIX CRITICO CACHE] Allineamento Ancora

    # --- [NUOVO v27.0] MOTORE RPG: ESTRATTORE INTENTI E DUNGEON MASTER ---

    def estrai_intento_gdr(self, azione_narrativa: str) -> Dict[str, Any]:
        """
        Legge un'azione narrativa e la converte in un JSON meccanico per rpg_engine.py.
        Usa il Regista (12B) per massima precisione con Chain-of-Thought.
        """
        self.logger.log(t("log.brain_rpg_intent"), "LOGIC")
        # --- [FIX CRITICO CACHE] SEPARAZIONE SYSTEM/USER ---
        sys_prompt = self._get_internal_prompt("estrattore_intenti_gdr_system")
        
        prompt = f"AZIONE NARRATIVA: \"{azione_narrativa}\""

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt}
        ]

        schema = {
            "type": "object",
            "properties": {
                "ragionamento": {"type": "string"},
                "azione": {
                    "type": "string",
                    "enum": ["attacco", "prova_abilita", "nessuna"],
                },
                "bersaglio": {"type": "string"},
                "arma": {"type": "string"},
                "statistica": {"type": "string"},
                "difficolta_stimata": {"type": "integer"},
            },
            "required": ["ragionamento", "azione"],
        }

        response_str = self._genera_pensiero(
            messages,
            temperature=0.0,
            max_tokens=1024, # [FIX CRITICO] Aggiunto spazio esplicito per permettere il ragionamento
            response_format={"type": "json_object", "schema": schema},
            in_gdr_mode=True
        )

        # [FIX CRITICO] Scudo anti-vuoto
        if not response_str or not response_str.strip():
            self.logger.error("Estrazione Intento GDR: Risposta LLM completamente vuota (Token Exhaustion).")
            return {"azione": "nessuna"}

        try:
            # --- [FIX CRITICO] PULIZIA MARKDOWN JSON ---
            clean_str = response_str.replace("```json", "").replace("```", "").strip()
            json_match = re.search(r"(\{[\s\S]*\})", clean_str)
            if json_match:
                clean_str = json_match.group(1)

            return json.loads(clean_str)
        except Exception as e:
            self.logger.error(
                t("log.brain_rpg_parse_error", error=e, raw=response_str[:50])
            )
            return {"azione": "nessuna"}

    def pensa_come_dungeon_master(
        self,
        tensione: int,
        universal_context: str,
        status_content: str,
        storia_recente: str,
        system_results: str,
        active_players_list: str = "",
        lang: str = "it",
        last_dm_narration: str = "",  # [FIX CONTINUITÀ DM]
        raw_history: list = None, # [FIX CRITICO CACHE]
    ) -> Dict[str, Any]:
        """
        Invoca il Dungeon Master Supremo per far avanzare la scena, gestire il pacing e spawnare entità.
        """
        self.logger.log(t("log.brain_rpg_dm_scene", tension=tensione), "GDR")

        prompt = self._get_brain_prompt("dungeon_master")
        
        # --- [OTTIMIZZAZIONE V-SPEED] PREFIX CACHING ---
        # Rimuoviamo la tensione dall'inizio del prompt (sostituendola con un placeholder vuoto)
        # e la accodiamo alla fine, per preservare la cache del contesto universale e della storia.
        prompt = self._safe_replace(prompt, "tensione", "[VEDI FONDO PROMPT]")
        
        prompt = self._safe_replace(
            prompt,
            "universal_context",
            self._safe_truncate_text(universal_context, 800),
        )
        prompt = self._safe_replace(
            prompt, "status_content", self._safe_truncate_text(status_content, 800)
        )
        prompt = self._safe_replace(
            prompt, "storia_recente", self._safe_truncate_text(storia_recente, 800)
        )
        prompt = self._safe_replace(
            prompt,
            "system_results",
            system_results if system_results else t("log.brain_rpg_no_dice"),
        )
        prompt = self._safe_replace(
            prompt,
            "active_players_list",
            t("brain.dm_players_list", list=active_players_list)
            if active_players_list
            else self.pg_name,
        )
        prompt = self._safe_replace(
            prompt, 
            "last_dm_narration", 
            last_dm_narration if last_dm_narration else t("brain.no_previous_action")
        )

        # ---[FIX CRITICO ANTI-GODMODING] Iniezione nome PG per la Regola 7 ---
        prompt = self._replace_all_name_variants(prompt, self.pg_name)

        prompt += self._get_language_instruction(lang)
        
        # Reinseriamo la tensione alla fine del prompt
        prompt += f"\n\n[ATTENZIONE - LIVELLO DI TENSIONE ATTUALE]: {tensione}/100\n"

        # --- [FIX CRITICO CACHE] ALLINEAMENTO ANCORA PER IL DM ---
        ancora_text = self._build_anchor_prompt(in_gdr_mode=True)
        messages = [{"role": "system", "content": ancora_text}]
        
        # --- COSTRUZIONE CRONOLOGIA (MESSAGGI REALI) ---
        if raw_history:
            for speaker, content in raw_history:
                clean_content = self._sanitize_for_cache(content)
                if clean_content.startswith("[GHOST] "):
                    clean_content = clean_content.replace("[GHOST] ", f"[MESSAGGIO SCRITTO E CANCELLATO, MA LETTO DA {self.pg_name}]: ")
                
                if speaker == "Dungeon Master":
                    messages.append({"role": "assistant", "content": clean_content})
                elif speaker == self.pg_name:
                    messages.append({"role": "user", "content": clean_content})
                else:
                    messages.append({"role": "user", "content": f"[{speaker}]: {clean_content}"})
        else:
            if storia_recente:
                prompt = f"--- STORIA RECENTE ---\n{storia_recente}\n\n" + prompt

        messages.append({"role": "user", "content": prompt})

        schema = {
            "type": "object",
            "properties": {
                "narrazione": {"type": "string"},
                "nuova_tensione": {"type": "integer"},
                "richiesta_sistema": {
                    "type": "object",
                    "properties": {
                        "azione": {
                            "type": "string",
                            "enum": ["nessuna", "spawn_nemico", "spawn_npc"],
                        },
                        "nome": {"type": "string"},
                        "hp": {"type": "integer"},
                        "ca": {"type": "integer"},
                    },
                    "required": ["azione"],
                },
            },
            "required": ["narrazione", "nuova_tensione", "richiesta_sistema"],
        }

        # Temperatura 0.7 per garantire creatività narrativa e adattabilità
        response_str = self._genera_pensiero(
            messages,
            temperature=0.7,
            response_format={"type": "json_object", "schema": schema},
            in_gdr_mode=True,
            enable_streaming=True
        )

        try:
            # --- [FIX CRITICO] PULIZIA MARKDOWN JSON ---
            clean_str = response_str.replace("```json", "").replace("```", "").strip()
            json_match = re.search(r"(\{[\s\S]*\})", clean_str)
            if json_match:
                clean_str = json_match.group(1)

            # [FIX A0019] strict=False permette gli "a capo" letterali (control characters) generati dall'LLM
            return json.loads(clean_str, strict=False)
        except Exception as e:
            self.logger.error(
                t("log.brain_dm_parse_error", error=e, raw=response_str[:50])
            )
            return {
                "narrazione": t("log.brain_dm_fallback"),
                "nuova_tensione": tensione,
                "richiesta_sistema": {"azione": "nessuna"},
            }

    def genera_scheda_rpg(
        self, razza: str, classe: str, livello: int, lang: str = "it"
    ) -> str:
        """Genera una scheda RPG completa basata su razza, classe e livello."""
        # [FIX] Rinominato parametro keyword 'class' (riservato) in 'char_class'
        self.logger.log(
            t("log.brain_rpg_sheet_gen", race=razza, char_class=classe, level=livello),
            "GDR",
        )

        prompt_template = self._get_brain_prompt("genera_scheda_rpg")
        prompt = self._safe_replace(prompt_template, "razza", razza)
        prompt = self._safe_replace(prompt, "classe", classe)
        prompt = self._safe_replace(prompt, "livello", str(livello))
        prompt += self._get_language_instruction(lang)

        # --- [FIX CRITICO] ANCORAGGIO DEL MODELLO E ANTI-ALLUCINAZIONE ---
        # Aggiungiamo un System Prompt forte per impedire allucinazioni filosofiche.
        messages = [
            {"role": "system", "content": "Sei un Dungeon Master esperto. Devi generare una scheda RPG in formato JSON puro. Non aggiungere testo fuori dal JSON. Usa solo statistiche, armi e oggetti realistici per un gioco di ruolo fantasy. Non inventare concetti filosofici o astratti."},
            {"role": "user", "content": prompt}
        ]

        # --- [FIX CRITICO] SCHEMA COMPLETO GBNF ---
        # Reintroduciamo lo schema completo per forzare l'LLM a rispettare la struttura esatta,
        # prevenendo allucinazioni di chiavi o nesting errato che rompono il frontend.
        schema = {
            "type": "object",
            "properties": {
                "statistiche_core": {
                    "type": "object",
                    "properties": {
                        "forza": {"type": "object", "properties": {"valore": {"type": "integer"}, "modificatore": {"type": "integer"}}},
                        "destrezza": {"type": "object", "properties": {"valore": {"type": "integer"}, "modificatore": {"type": "integer"}}},
                        "costituzione": {"type": "object", "properties": {"valore": {"type": "integer"}, "modificatore": {"type": "integer"}}},
                        "intelligenza": {"type": "object", "properties": {"valore": {"type": "integer"}, "modificatore": {"type": "integer"}}},
                        "saggezza": {"type": "object", "properties": {"valore": {"type": "integer"}, "modificatore": {"type": "integer"}}},
                        "carisma": {"type": "object", "properties": {"valore": {"type": "integer"}, "modificatore": {"type": "integer"}}}
                    }
                },
                "combattimento": {
                    "type": "object",
                    "properties": {
                        "hp_massimi": {"type": "integer"},
                        "hp_attuali": {"type": "integer"},
                        "classe_armatura": {"type": "integer"},
                        "iniziativa": {"type": "integer"},
                        "velocita": {"type": "integer"}
                    }
                },
                "equipaggiamento": {
                    "type": "object",
                    "properties": {
                        "armi": {"type": "array", "items": {"type": "object", "properties": {"nome": {"type": "string"}, "bonus_attacco": {"type": "integer"}, "danno": {"type": "string"}, "tipo": {"type": "string"}}}},
                        "armature": {"type": "array", "items": {"type": "object", "properties": {"nome": {"type": "string"}, "tipo": {"type": "string"}, "ca_bonus": {"type": "string"}, "svantaggio_furtivita": {"type": "boolean"}}}},
                        "inventario": {"type": "array", "items": {"type": "string"}},
                        "monete": {"type": "object", "properties": {"oro": {"type": "integer"}, "argento": {"type": "integer"}, "rame": {"type": "integer"}}}
                    }
                },
                "magia_e_privilegi": {
                    "type": "object",
                    "properties": {
                        "tratti_razziali": {"type": "array", "items": {"type": "string"}},
                        "privilegi_classe": {"type": "array", "items": {"type": "string"}},
                        "incantesimi": {"type": "array", "items": {"type": "string"}}
                    }
                }
            },
            "required": ["statistiche_core", "combattimento", "equipaggiamento", "magia_e_privilegi"]
        }

        return self._genera_pensiero(
            messages, 
            temperature=0.1, # <-- FIX CRITICO: Temperatura a 0.1 per uccidere la creatività fuori controllo
            max_tokens=4096, # [FIX] Aumentato per supportare i modelli Reasoning
            response_format={"type": "json_object", "schema": schema},
            in_gdr_mode=True
        )

    def genera_quest_procedurale(self, lang: str = "it") -> Dict[str, Any]:
        """Genera una quest procedurale per la locanda multiplayer."""
        self.logger.log(t("log.brain_rpg_quest_gen"), "GDR")

        prompt = self._get_internal_prompt("quest_procedurale")
        prompt += self._get_language_instruction(lang)

        # --- [FIX CRITICO CACHE] ALLINEAMENTO ANCORA ---
        ancora_text = self._build_anchor_prompt(in_gdr_mode=False)
        messages = [
            {"role": "system", "content": ancora_text},
            {"role": "user", "content": prompt}
        ]

        schema = {
            "type": "object",
            "properties": {
                "titolo": {"type": "string"},
                "descrizione": {"type": "string"},
                "livello_minimo": {"type": "integer"},
                "livello_massimo": {"type": "integer"},
            },
            "required": ["titolo", "descrizione", "livello_minimo", "livello_massimo"],
        }

        response_str = self._genera_pensiero(
            messages,
            temperature=0.8,
            response_format={"type": "json_object", "schema": schema},
            in_gdr_mode=True
        )

        try:
            clean_str = response_str.replace("```json", "").replace("```", "").strip()
            json_match = re.search(r"(\{[\s\S]*\})", clean_str)
            if json_match:
                clean_str = json_match.group(1)
            return json.loads(clean_str)
        except Exception as e:
            self.logger.error(t("log.brain_quest_parse_error", error=e))
            return {
                "titolo": t("log.brain_quest_goblin_title"),
                "descrizione": t("log.brain_quest_goblin_desc"),
                "livello_minimo": 1,
                "livello_massimo": 3,
            }

    def rileva_eventi_mondo(
        self, user_input: str, current_state: str
    ) -> Dict[str, Any]:
        self.logger.log(t("log.brain_world_monitor"))

        # ---[GOD TIER SHIELD] ---
        safe_input = self._safe_truncate_text(user_input, max_tokens=1500)
        safe_state = self._safe_truncate_text(current_state, max_tokens=1500)

        # --- FASE UNICA: RILEVAMENTO E ESTRAZIONE JSON (GBNF ENFORCED) ---
        system_instruction = (
            "Sei il Rilevatore di Stato del Mondo (Analista di Sistema). Il tuo compito è leggere l'input dell'utente e mappare OGNI SINGOLO CAMBIAMENTO FISICO nel JSON.\n"
            "REGOLE INVIOLABILI (MANDATO ASSOLUTO):\n"
            "1. TELETRASPORTO/SPOSTAMENTO: Se l'utente dice 'teletrasporto', 'andiamo in', 'siamo a', DEVI TASSATIVAMENTE compilare il campo 'location' con il nuovo luogo.\n"
            "2. CAMBIO D'ABITO: Se l'utente cambia i vestiti al gruppo (es. 'vi vesto con', 'cambio outfit'), DEVI TASSATIVAMENTE compilare 'global_outfit_change' con la descrizione esatta dei vestiti.\n"
            "3. OGGETTI/CIBO: Se l'utente fa apparire cibo, armi o oggetti, aggiungili a 'oggetti_interattivi'.\n"
            "4. Se rilevi ALMENO UN cambiamento, imposta 'cambiamento_rilevato' a true.\n"
            "Se un elemento specifico NON cambia, omettilo. Ma se l'utente lo menziona, DEVI estrarlo. Sii meticoloso e non ignorare i dettagli."
        )

        messages =[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"STATO ATTUALE:\n{safe_state}\n\nINPUT UTENTE:\n'{safe_input}'\n\nGenera il JSON:"}
        ]

        schema = {
            "type": "object",
            "properties": {
                "ragionamento": {"type": "string", "description": "Spiega in max 10 parole cosa è successo fisicamente"},
                "cambiamento_rilevato": {"type": "boolean", "description": "True se ci sono cambiamenti, altrimenti False"},
                "location": {"type": "string", "description": "ESTRAI IL NUOVO LUOGO se l'utente si sposta o teletrasporta (es. 'Salotto della Villa'). Altrimenti ometti."},
                "global_outfit_change": {"type": "string", "description": "ESTRAI I NUOVI VESTITI se l'utente cambia l'outfit a tutti (es. 'Divisa del college...'). Altrimenti ometti."},
                "percezione_ambientale": {
                    "type": "object",
                    "properties": {
                        "luce_e_colori": {"type": "string"},
                        "suoni_di_sottofondo": {"type": "string"},
                        "odori_e_profumi": {"type": "string"},
                        "temperatura_e_tatto": {"type": "string"}
                    }
                },
                "characters": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "nome": {"type": "string"},
                            "outfit": {"type": "string"},
                            "position": {"type": "string"},
                            "physical_state": {"type": "string"},
                            "postura_e_posizione": {"type": "string"},
                            "dettagli_sensoriali": {"type": "string"},
                            "oggetti_equipaggiati": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["nome"]
                    }
                },
                "oggetti_interattivi": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "nome": {"type": "string"},
                            "stato": {"type": "string", "description": "Nuovo stato o 'Distrutto'"},
                            "possessore": {"type": "string"}
                        },
                        "required": ["nome", "stato", "possessore"]
                    }
                }
            },
            "required": ["ragionamento", "cambiamento_rilevato"]
        }

        response_str = self._genera_pensiero(
            messages,
            temperature=0.0,
            max_tokens=4096, # [FIX CRITICO] Aumentato a 4096 per garantire spazio vitale al ragionamento
            response_format={"type": "json_object", "schema": schema},
            in_gdr_mode=True
        )

        # --- [FIX CRITICO] SCUDO ANTI-VUOTO (TOKEN EXHAUSTION) ---
        if not response_str or not response_str.strip():
            self.logger.error("Rilevatore Eventi: Risposta LLM vuota (Token Exhaustion). Nessun evento rilevato.")
            return {}

        try:
            clean_str = response_str.replace("```json", "").replace("```", "").strip()
            json_match = re.search(r"(\{[\s\S]*\})", clean_str)
            if json_match:
                clean_str = json_match.group(1)
            result = json.loads(clean_str)

            if not result.get("cambiamento_rilevato", False):
                self.logger.log(f"Rilevatore Eventi: Nessun cambiamento rilevato. Ragionamento: {result.get('ragionamento')}", "DEBUG")
                return {}

            # --- FORMATTAZIONE PER L'EXECUTOR ---
            event_data = {}
            
            if result.get("location"):
                event_data["location"] = result["location"]
            if result.get("global_outfit_change"):
                event_data["global_outfit_change"] = result["global_outfit_change"]
            
            percezione = result.get("percezione_ambientale", {})
            # Rimuovi chiavi vuote
            percezione = {k: v for k, v in percezione.items() if v}
            if percezione:
                event_data["percezione_ambientale"] = percezione

            chars_array = result.get("characters",[])
            if chars_array:
                characters_data = {}
                for char in chars_array:
                    nome = char.get("nome")
                    if not nome: continue
                    char_dict = {k: v for k, v in char.items() if k != "nome" and v}
                    if char_dict:
                        characters_data[nome] = char_dict
                if characters_data:
                    event_data["characters"] = characters_data

            oggetti_array = result.get("oggetti_interattivi",[])
            if oggetti_array:
                changed_objects = {obj["nome"].lower(): obj for obj in oggetti_array if obj.get("nome")}
                
                try:
                    current_state_dict = json.loads(current_state)
                    existing_objects = current_state_dict.get("oggetti_interattivi", [])
                except:
                    existing_objects = []

                final_objects =[]
                for obj in existing_objects:
                    nome_lower = obj.get("nome", "").lower()
                    if nome_lower in changed_objects:
                        new_obj = changed_objects.pop(nome_lower)
                        if new_obj.get("stato", "").lower() not in["distrutto", "rimosso", "eliminato"]:
                            final_objects.append(new_obj)
                    else:
                        final_objects.append(obj)
                
                for new_obj in changed_objects.values():
                    if new_obj.get("stato", "").lower() not in["distrutto", "rimosso", "eliminato"]:
                        final_objects.append(new_obj)
                
                event_data["oggetti_interattivi"] = final_objects

            self.logger.log(f"Rilevatore Eventi: Dati estratti con successo: {list(event_data.keys())}", "DEBUG")
            return event_data

        except Exception as e:
            self.logger.error(f"Errore parsing Rilevatore Eventi: {e}. Raw: {response_str[:100]}")
            return {}

    def calcola_entropia_mondo(self, current_state: str, lang: str = "it") -> Dict[str, Any]:
        """
        Motore dell'Entropia: Calcola il decadimento ambientale e lo stato degli oggetti nel tempo.
        """
        self.logger.log("Calcolo Entropia Ambientale in corso...", "WORLD")
        safe_state = self._safe_truncate_text(current_state, max_tokens=2000)
        
        # --- [FIX CRITICO CACHE] SEPARAZIONE SYSTEM/USER ---
        sys_prompt = self._get_internal_prompt("motore_entropia_system")
        
        prompt = f"STATO ATTUALE: {safe_state}"
        prompt += self._get_language_instruction(lang)
        
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt}
        ]
        
        # Riutilizziamo lo stesso schema del rilevatore eventi per coerenza strutturale
        schema = {
            "type": "object",
            "properties": {
                "percezione_ambientale": {
                    "type": "object",
                    "properties": {
                        "luce_e_colori": {"type": "string"},
                        "suoni_di_sottofondo": {"type": "string"},
                        "odori_e_profumi": {"type": "string"},
                        "temperatura_e_tatto": {"type": "string"}
                    }
                },
                "oggetti_interattivi": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "nome": {"type": "string"},
                            "stato": {"type": "string"},
                            "possessore": {"type": "string"}
                        },
                        "required": ["nome", "stato", "possessore"]
                    }
                },
                "characters": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
                            "dettagli_sensoriali": {"type": "string"}
                        }
                    }
                }
            }
        }
        
        response_str = self._genera_pensiero(
            messages,
            temperature=0.3,
            response_format={"type": "json_object", "schema": schema},
            in_gdr_mode=True
        )
        
        try:
            return json.loads(response_str)
        except Exception as e:
            self.logger.error(f"Errore parsing Entropia: {e}")
            return {}

    # ---[NUOVO] METODI LOCAL SUPERMEMORY ---
    def filtra_ingestione_memoria(self, testo: str, lang: str = "it", override_brain: Optional[LlamaServerClient] = None) -> Dict[str, Any]:
        """Filtra il testo prima di inserirlo in ChromaDB, estraendo solo le info rilevanti."""
        self.logger.log("Filtro Ingestione Memoria (Local Supermemory)...", "MEMORY")
        
        # --- [FIX CRITICO CACHE] SEPARAZIONE SYSTEM/USER ---
        sys_prompt = self._get_internal_prompt("filtro_ingestione_system")
        
        prompt = f"TESTO:\n{testo}"
        prompt += self._get_language_instruction(lang)

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt}
        ]
        schema = {
            "type": "object",
            "properties": {
                "is_relevant": {"type": "boolean"},
                "extracted_info": {"type": "string"}
            },
            "required":["is_relevant", "extracted_info"]
        }

        response_str = self._genera_pensiero(
            messages,
            temperature=0.2, # [FIX] Alzato leggermente per prevenire incastri sintattici
            max_tokens=4096, # [FIX CRITICO] Garantisce spazio vitale assoluto all'estrazione
            response_format={"type": "json_object", "schema": schema},
            override_brain=override_brain
        )

        if not response_str or not response_str.strip():
            self.logger.error("GraphRAG: Risposta LLM vuota durante l'estrazione.")
            return []

        try:
            clean_str = response_str.replace("```json", "").replace("```", "").strip()
            json_match = re.search(r"(\{[\s\S]*\})", clean_str)
            if json_match:
                clean_str = json_match.group(1)
            return json.loads(clean_str)
        except Exception as e:
            self.logger.error(t("log.brain_internal_error", error=e))
            return {"is_relevant": False, "extracted_info": ""}

    def aggiorna_profilo_dinamico(self, storia_recente: str, profilo_attuale: str, nome_pg: str, lang: str = "it", override_brain: Optional[LlamaServerClient] = None) -> Dict[str, Any]:
        """Aggiorna il profilo dinamico dell'utente basandosi sulla conversazione recente."""
        self.logger.log("Aggiornamento Profilo Dinamico (Local Supermemory)...", "MEMORY")
        
        # --- [FIX CRITICO CACHE] SEPARAZIONE SYSTEM/USER ---
        sys_prompt_template = self._get_internal_prompt("profilazione_dinamica_system")
        sys_prompt = self._safe_replace(sys_prompt_template, "nome_pg", nome_pg)
        
        prompt = f"PROFILO ATTUALE:\n{profilo_attuale}\n\nNUOVE INTERAZIONI:\n{storia_recente}"
        prompt += self._get_language_instruction(lang)

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt}
        ]
        schema = {
            "type": "object",
            "properties": {
                "fatti_statici": {"type": "array", "items": {"type": "string"}},
                "stato_emotivo_attuale": {"type": "string"},
                "interessi_attuali": {"type": "array", "items": {"type": "string"}}
            },
            "required":["fatti_statici", "stato_emotivo_attuale", "interessi_attuali"]
        }

        response_str = self._genera_pensiero(
            messages,
            temperature=0.3,
            response_format={"type": "json_object", "schema": schema},
            override_brain=override_brain
        )

        try:
            clean_str = response_str.replace("```json", "").replace("```", "").strip()
            json_match = re.search(r"(\{[\s\S]*\})", clean_str)
            if json_match:
                clean_str = json_match.group(1)
            return json.loads(clean_str)
        except Exception as e:
            self.logger.error(t("log.brain_internal_error", error=e))
            return {}

    # --- [NUOVO] ESTRAZIONE GRAPHRAG ---
    def estrai_triplette_conoscenza(self, testo: str, lang: str = "it", override_brain: Optional[LlamaServerClient] = None) -> List[Dict[str, str]]:
        """Estrae fatti relazionali (Soggetto, Predicato, Oggetto) dal testo per il GraphRAG."""
        self.logger.log("Estrazione Nodi Grafo (GraphRAG)...", "MEMORY")
        
        # --- [FIX CRITICO CACHE] SEPARAZIONE SYSTEM/USER ---
        sys_prompt = self._get_internal_prompt("estrazione_grafo_system")
        
        prompt = f"TESTO:\n{testo}"
        prompt += self._get_language_instruction(lang)

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt}
        ]
        schema = {
            "type": "object",
            "properties": {
                "triplette": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "subject": {"type": "string"},
                            "predicate": {"type": "string"},
                            "object": {"type": "string"}
                        },
                        "required": ["subject", "predicate", "object"]
                    }
                }
            },
            "required": ["triplette"]
        }

        response_str = self._genera_pensiero(
            messages,
            temperature=0.1,
            response_format={"type": "json_object", "schema": schema},
            override_brain=override_brain
        )

        try:
            clean_str = response_str.replace("```json", "").replace("```", "").strip()
            json_match = re.search(r"(\{[\s\S]*\})", clean_str)
            if json_match:
                clean_str = json_match.group(1)
            data = json.loads(clean_str)
            return data.get("triplette",[])
        except Exception as e:
            self.logger.error(t("log.brain_internal_error", error=e))
            return[]

    # --- [NUOVO] RITO DELL'ARCHIVISTA (WIKI GENERATION) ---
    def pensa_pagina_wiki(
        self, topic: str, raw_data: str, pg_name: str, lang: str = "it", override_brain: Optional[LlamaServerClient] = None
    ) -> str:
        """[WIKI] Genera una pagina Markdown strutturata per Obsidian partendo da dati grezzi.
        Usa il modello principale per non pesare sul modello narrativo.
        """
        self.logger.log(f"Archivist: Generating Wiki page for '{topic}'...", "MEMORY")
        
        # --- [FIX CRITICO CACHE] SEPARAZIONE SYSTEM/USER ---
        sys_prompt = self._get_internal_prompt("generazione_pagina_wiki_system")
        
        prompt = f"ENTITÀ/ARGOMENTO: {topic}\n\nDATI GREZZI (Triplette e Memorie):\n{raw_data}"
        prompt = self._replace_all_name_variants(prompt, pg_name)
        prompt += self._get_language_instruction(lang)

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt}
        ]
        
        # Temperatura bassa (0.2) per massima aderenza ai fatti e alla formattazione YAML
        wiki_content = self._genera_pensiero(
            messages, 
            temperature=0.2, 
            max_tokens=4096, 
            override_brain=override_brain
        )
        
        # Pulizia di eventuali markdown code blocks generati dall'LLM
        wiki_content = wiki_content.replace("```markdown", "").replace("```", "").strip()
        return wiki_content

    # --- [NUOVO] GHOST OPERATOR (VISIONE AUTONOMA) ---
    def pensa_prossima_mossa_visiva(self, frame: np.ndarray, obiettivo: str, history: str, lang: str = "it") -> str:
        """
        [GHOST OPERATOR] Analizza lo schermo e decide la prossima mossa fisica.
        [FIX CRITICO] Sincronizzato con i Bounding Box nativi di Gemma 4.
        """
        self.logger.log(f"Ghost Operator: Analisi visiva per obiettivo '{obiettivo}'...", "VISION")
        if not self.cuore:
            return '{"action": "ERROR", "ragionamento": "Cervello non inizializzato."}'

        try:
            height, width, _ = frame.shape
            _, image_bytes = cv2.imencode(".jpg", cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            image_b64 = base64.b64encode(image_bytes.tobytes()).decode("utf-8")
            image_uri = f"data:image/jpeg;base64,{image_b64}"

            prompt_template = self._get_internal_prompt("ghost_operator")
            prompt = self._safe_replace(prompt_template, "obiettivo", obiettivo)
            prompt = self._safe_replace(prompt, "history", history)
            prompt += self._get_language_instruction(lang)

            messages =[
                {
                    "role": "user",
                    "content":[
                        {"type": "image_url", "image_url": {"url": image_uri}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ]

            if self.is_gemma_4:
                # --- GEMMA 4 NATIVE SPATIAL REASONING ---
                # Non forziamo il JSON schema, lasciamo che usi i BBox nativi
                prompt_gemma4 = "\n\nREGOLE GEMMA 4:\nSe devi cliccare su un elemento, descrivi l'azione e fornisci il Bounding Box esatto nel formato[y1, x1, y2, x2] (valori da 0 a 1000). Esempio: 'Clicco sull'icona [100, 200, 150, 250]'. Se devi scrivere, usa il formato testuale."
                messages[0]["content"][1]["text"] += prompt_gemma4
                
                response_str = self._genera_pensiero(messages, temperature=0.0)
                
                # Parsing ibrido per Gemma 4
                decision = {"action": "DONE", "ragionamento": response_str}
                
                # Cerca BBox
                bbox_match = re.search(r"\[\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]", response_str)
                if bbox_match:
                    decision["action"] = "CLICK"
                    y1, x1, y2, x2 = map(int, bbox_match.groups())
                    center_x_norm = (x1 + x2) / 2
                    center_y_norm = (y1 + y2) / 2
                    decision["x"] = int((center_x_norm / 1000) * width)
                    decision["y"] = int((center_y_norm / 1000) * height)
                elif "scriv" in response_str.lower() or "digit" in response_str.lower():
                    decision["action"] = "TYPE"
                    # Estrai testo tra virgolette
                    text_match = re.search(r"['\"](.*?)['\"]", response_str)
                    if text_match:
                        decision["text"] = text_match.group(1)
                elif "prem" in response_str.lower():
                    decision["action"] = "PRESS"
                    text_match = re.search(r"['\"](.*?)['\"]", response_str)
                    if text_match:
                        decision["text"] = text_match.group(1)
                        
                return json.dumps(decision)
            else:
                # --- FALLBACK LEGACY (QWEN / GEMMA 3) ---
                schema = {
                    "type": "object",
                    "properties": {
                        "ragionamento": {"type": "string"},
                        "action": {"type": "string", "enum":["CLICK", "TYPE", "PRESS", "DONE"]},
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                        "text": {"type": "string"}
                    },
                    "required":["ragionamento", "action"]
                }

                return self._genera_pensiero(messages, temperature=0.1, response_format={"type": "json_object", "schema": schema})
        except Exception as e:
            self.logger.error(f"Errore Ghost Operator: {e}")
            return '{"action": "DONE", "ragionamento": "Errore interno"}'

    # ---[NUOVO] SELF-HEALING TOOLS ---
    def pensa_ottimizzazione_tool(self, tool_json_str: str, error_log: str, lang: str = "it") -> str:
        """[SELF-HEALING] Riscrive la descrizione di un tool per prevenire errori futuri.
        """
        self.logger.log(t("log.brain_self_healing_start"), "SYSTEM")
        prompt_template = self._get_internal_prompt("self_healing_tool")
        prompt = self._safe_replace(prompt_template, "tool_json", tool_json_str)
        prompt = self._safe_replace(prompt, "error_log", error_log)
        prompt += self._get_language_instruction(lang)

        messages = [{"role": "user", "content": prompt}]
        
        # Temperatura 0.1 per modifiche chirurgiche al JSON
        return self._genera_pensiero(messages, temperature=0.1)

    # --- [NUOVO] AGENTE TECNICO PURO (COLD AGENT) ---
    def pensa_agente_tecnico_step(self, messages: List[Dict], tools: List[Dict]) -> str:
        """
        Esegue un singolo step del ReAct Loop usando il Cold Agent.
        Nessuna iniezione di RAG, DNA o emozioni. Pura logica.
        """
        if not self.cuore:
            return "ERRORE: Cervello non disponibile."
            
        # Assicuriamo che il token di thinking sia abilitato per Gemma 4
        if self.is_gemma_4 and messages and messages[0]["role"] == "system":
            if not messages[0]["content"].startswith("<|think|>"):
                messages[0]["content"] = "<|think|>\n" + messages[0]["content"]
                
        with self.lock:
            try:
                # [FIX BUG 3] Aggiunti <turn|> e <|turn> per fermare le allucinazioni di Gemma 3/4
                stop_tokens =["<end_of_turn>", "<eos>", "<|eot_id|>", "<|im_end|>", "user\n", "User:", "<turn|>", "<|turn>"]
                
                completion_kwargs = {
                    "messages": messages,
                    "temperature": 0.1, # Molto bassa per logica ferrea
                    "max_tokens": 4096,
                    "stop": stop_tokens
                }
                
                if tools and self.is_gemma_4:
                    completion_kwargs["tools"] = tools
                
                response = self.cuore.create_chat_completion(**completion_kwargs)
                message = response["choices"][0]["message"]
                content = message.get("content", "").strip()
                
                # Intercettazione Native Tool Calls (Gemma 4)
                if "tool_calls" in message and message["tool_calls"]:
                    tool_call = message["tool_calls"][0]["function"]
                    t_name = tool_call.get("name", "")
                    t_args = tool_call.get("arguments", "{}")
                    native_call_str = f'{{"name": "{t_name}", "parameters": {t_args}}}'
                    content = f"{content}\n{native_call_str}".strip()
                    
                return content
            except Exception as e:
                self.logger.error(f"Errore Agente Tecnico: {e}")
                return f"ERRORE: {e}"

    # --- [MODULO 2] METODI DEL MINISTERO DEGLI AGENTI (SWARM) ---
    def pensa_architetto_piano(self, task: str, reasoning_bank: str, lang: str = "it") -> Dict[str, Any]:
        """L'Architetto scompone il task in sub-task (Fase 1 & 3)."""
        prompt_template = self._get_internal_prompt("demiurge_architect")
        prompt = self._safe_replace(prompt_template, "task", task)
        prompt = self._safe_replace(prompt, "reasoning_bank", reasoning_bank if reasoning_bank else "Nessuna traiettoria passata trovata.")
        prompt += self._get_language_instruction(lang)

        messages =[{"role": "user", "content": prompt}]
        schema = {
            "type": "object",
            "properties": {
                "analisi": {"type": "string"},
                "subtasks": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["analisi", "subtasks"]
        }
        
        response_str = self._genera_pensiero(messages, temperature=0.2, response_format={"type": "json_object", "schema": schema})
        try:
            clean_str = response_str.replace("```json", "").replace("```", "").strip()
            json_match = re.search(r"(\{[\s\S]*\})", clean_str)
            if json_match: clean_str = json_match.group(1)
            return json.loads(clean_str)
        except:
            return {"analisi": t("log.brain_architect_parse_error"), "subtasks":[task]}

    def pensa_fabbro(self, subtask: str, history: str, error_feedback: str, lang: str = "it") -> Dict[str, Any]:
        """Il Fabbro scrive il codice Python isolato (Fase 5)."""
        prompt_template = self._get_internal_prompt("demiurge_blacksmith")
        prompt = self._safe_replace(prompt_template, "subtask", subtask)
        prompt = self._safe_replace(prompt, "history", history)
        prompt = self._safe_replace(prompt, "error_feedback", error_feedback if error_feedback else "Nessun errore.")
        prompt += self._get_language_instruction(lang)

        messages = [{"role": "user", "content": prompt}]
        schema = {
            "type": "object",
            "properties": {
                "ragionamento": {"type": "string"},
                "python_code": {"type": "string"},
                "pip_dependencies": {"type": "array", "items": {"type": "string"}}
            },
            "required":["ragionamento", "python_code", "pip_dependencies"]
        }
        
        response_str = self._genera_pensiero(messages, temperature=0.1, response_format={"type": "json_object", "schema": schema})
        try:
            clean_str = response_str.replace("```json", "").replace("```", "").strip()
            json_match = re.search(r"(\{[\s\S]*\})", clean_str)
            if json_match: clean_str = json_match.group(1)
            return json.loads(clean_str)
        except:
            return {"ragionamento": t("log.brain_blacksmith_parse_error"), "python_code": "print('Error')", "pip_dependencies":[]}

    def pensa_inquisitore(self, subtask: str, code: str, output: str, lang: str = "it") -> Dict[str, Any]:
        """L'Inquisitore esegue la Code Review (Fase 6)."""
        prompt_template = self._get_internal_prompt("demiurge_inquisitor")
        prompt = self._safe_replace(prompt_template, "subtask", subtask)
        prompt = self._safe_replace(prompt, "code", code)
        prompt = self._safe_replace(prompt, "output", output)
        prompt += self._get_language_instruction(lang)

        messages =[{"role": "user", "content": prompt}]
        schema = {
            "type": "object",
            "properties": {
                "approved": {"type": "boolean"},
                "feedback": {"type": "string"}
            },
            "required": ["approved", "feedback"]
        }
        
        response_str = self._genera_pensiero(messages, temperature=0.1, response_format={"type": "json_object", "schema": schema})
        try:
            clean_str = response_str.replace("```json", "").replace("```", "").strip()
            json_match = re.search(r"(\{[\s\S]*\})", clean_str)
            if json_match: clean_str = json_match.group(1)
            return json.loads(clean_str)
        except:
            return {"approved": False, "feedback": t("log.brain_inquisitor_parse_error")}

    def distilla_memorie_gdr(
        self, gdr_transcript: List[Tuple[str, str]]
    ) -> Dict[str, Any]:
        """
        Distilla le memorie GDR restituendo un oggetto JSON strutturato.
        Implementa il CHUNKING per evitare overflow di token.
        """
        self.logger.log(t("log.brain_gdr_distillation"))
        if not gdr_transcript:
            return {"memories": []}

        CHUNK_SIZE = 15
        all_memories = []

        for i in range(0, len(gdr_transcript), CHUNK_SIZE):
            chunk = gdr_transcript[i : i + CHUNK_SIZE]
            self.logger.log(
                t("log.brain_gdr_chunk", num=i // CHUNK_SIZE + 1, count=len(chunk)),
                "MEMORY",
            )

            chunk_transcript = t("log.brain_gdr_chunk_transcript")
            for user_input, gemma_output in chunk:
                chunk_transcript += t(
                    "brain.gdr_chunk_action_format",
                    input=user_input,
                    output=gemma_output,
                )

            episodic_memories_content = self.lore.get("MEMORY GDR", "")[-2000:]

            # --- MODIFICA v32.0: USO COSTANTI DINAMICHE ---
            # Usiamo 'it' per coerenza interna del DB memorie
            vangelo_memoria = self._get_gdr_law("distillazione_gdr")
            vangelo_memoria = self._safe_replace(
                vangelo_memoria, "episodic_memories_content", episodic_memories_content
            )
            vangelo_memoria = self._safe_replace(
                vangelo_memoria, "full_transcript", chunk_transcript
            )

            messages = [{"role": "user", "content": vangelo_memoria}]

            schema = {
                "type": "object",
                "properties": {
                    "memories": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "timestamp": {"type": "string"},
                                "personaggio": {"type": "string"},
                                "evento": {"type": "string"},
                                "luogo": {"type": "string"},
                                "persone_coinvolte": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "emozioni_provate": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "sensazioni_fisiche": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "rilevanza": {"type": "integer"},
                                "conseguenze": {"type": "string"},
                                "collegamenti": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "tags": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["evento", "personaggio", "luogo"],
                        },
                    }
                },
                "required": ["memories"],
            }

            response_str = self._genera_pensiero(
                messages,
                temperature=0.2,
                response_format={"type": "json_object", "schema": schema},
                in_gdr_mode=True
            )

            try:
                chunk_result = json.loads(response_str)
                if "memories" in chunk_result:
                    all_memories.extend(chunk_result["memories"])
            except json.JSONDecodeError:
                self.logger.log(
                    t("log.brain_memory_parse_error", index=i, output=response_str)
                )

        self.logger.log(
            t("log.brain_gdr_distillation_complete", count=len(all_memories)), "MEMORY"
        )
        return {"memories": all_memories}

    def analizza_scena_corrente(
        self, frame_input: Union[np.ndarray, List[np.ndarray]], user_query: str, lang: str = "it"
    ) -> str:
        self.logger.log(t("log.brain_vision_activated"))
        if not self.cuore:
            return t("log.brain_vision_blind")
        try:
            frames = frame_input if isinstance(frame_input, list) else [frame_input]
            content_list = []
            
            for img in frames:
                if img is not None:
                    _, image_bytes = cv2.imencode(
                        ".jpg", cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    )
                    image_bytes = image_bytes.tobytes()
                    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
                    image_uri = f"data:image/jpeg;base64,{image_b64}"
                    content_list.append({"type": "image_url", "image_url": {"url": image_uri}})

            # --- MODIFICA v32.0: USO COSTANTI DINAMICHE ---
            prompt_testo = self._get_brain_prompt("scena")
            prompt_testo = self._safe_replace(prompt_testo, "user_query", user_query)
            prompt_testo += self._get_language_instruction(lang)

            content_list.append({"type": "text", "text": prompt_testo})

            messages = [
                {
                    "role": "user",
                    "content": content_list,
                }
            ]
            return self._genera_pensiero(messages, temperature=0.0)
        except Exception as e:
            print(t("log.brain_vision_anomaly_print", error=e))
            traceback.print_exc()
            return t("log.brain_vision_anomaly", error=e)

    # --- [NUOVO v52.8] VISIONE OPERATIVA (SENTIERO OCCHIO DEL DEMIURGO) ---
    # --- [NUOVO v45.0] AUTO-HEALING BRAIN ---
    def pensa_soluzione_bug(self, error_msg: str, traceback_str: str) -> str:
        """
        Analizza un errore critico e genera un piano di riparazione per il Demiurgo.
        """
        self.logger.log(t("log.brain_auto_healing"), "DEBUG")

        prompt_template = self._get_internal_prompt("soluzione_bug")
        prompt = self._safe_replace(prompt_template, "error_msg", error_msg)
        prompt = self._safe_replace(prompt, "traceback_str", traceback_str)

        messages = [{"role": "user", "content": prompt}]
        return self._genera_pensiero(messages, temperature=0.1)

    def analizza_visione_operativa(self, frame: np.ndarray, lang: str = "it") -> str:
        """
        Usa il Narrative Brain (GPU) per estrarre task tecnici dall'immagine.
        Il risultato verrà poi passato al Labour Brain per il routing.
        """
        self.logger.log(t("log.brain_demiurge_eye"))
        if not self.cuore:
            return t("log.brain_vision_not_available")

        try:
            _, image_bytes = cv2.imencode(
                ".jpg", cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            )
            image_b64 = base64.b64encode(image_bytes.tobytes()).decode("utf-8")
            image_uri = f"data:image/jpeg;base64,{image_b64}"

            prompt = self._get_brain_prompt("vision_operativa")
            prompt += self._get_language_instruction(lang)

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_uri}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ]

            return self._genera_pensiero(messages, temperature=0.0)
        except Exception as e:
            return t("log.brain_vision_operational_error", error=e)

    # ---[NUOVO v116.1] LOCALIZZAZIONE SPAZIALE INTUITIVA (GEMMA 4 READY) ---
    def trova_coordinate_elemento(
        self, frame: np.ndarray, description: str, lang: str = "it"
    ) -> Dict[str, Any]:
        """
        Individua un elemento nell'immagine.
        Se è Gemma 4, usa il Bounding Box nativo[y1, x1, y2, x2].
        Altrimenti usa il fallback JSON.
        """
        self.logger.log(t("log.brain_spatial_search", desc=description), "VISION")
        if not self.cuore:
            return {"x": 0, "y": 0, "confidence": 0}

        try:
            height, width, _ = frame.shape
            _, image_bytes = cv2.imencode(".jpg", cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            image_b64 = base64.b64encode(image_bytes.tobytes()).decode("utf-8")
            image_uri = f"data:image/jpeg;base64,{image_b64}"

            if self.is_gemma_4:
                # --- GEMMA 4 NATIVE GUI DETECTION ---
                prompt = t("brain.vision_spatial_mandate", desc=description)
                
                messages = [
                    {
                        "role": "user",
                        "content":[
                            {"type": "image_url", "image_url": {"url": image_uri}},
                            {"type": "text", "text": prompt},
                        ],
                    }
                ]
                
                response_str = self._genera_pensiero(messages, temperature=0.0)
                
                # Parsing dell'array[y1, x1, y2, x2]
                match = re.search(r"\[\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]", response_str)
                if match:
                    y1, x1, y2, x2 = map(int, match.groups())
                    # Calcolo del centro e denormalizzazione (da 0-1000 a pixel reali)
                    center_x_norm = (x1 + x2) / 2
                    center_y_norm = (y1 + y2) / 2
                    
                    real_x = int((center_x_norm / 1000) * width)
                    real_y = int((center_y_norm / 1000) * height)
                    
                    return {"x": real_x, "y": real_y, "confidence": 0.99}
                else:
                    self.logger.warning(t("log.brain_native_bbox_invalid", response=response_str))
                    return {"x": 0, "y": 0, "confidence": 0}

            else:
                # --- FALLBACK LEGACY (QWEN / GEMMA 3) ---
                prompt_template = self._get_brain_prompt("spatial_reasoning")
                prompt = self._safe_replace(prompt_template, "element_description", description)
                prompt += self._get_language_instruction(lang)

                messages = [
                    {
                        "role": "user",
                        "content":[
                            {"type": "image_url", "image_url": {"url": image_uri}},
                            {"type": "text", "text": prompt},
                        ],
                    }
                ]

                schema = {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                        "confidence": {"type": "number"},
                    },
                    "required": ["x", "y"],
                }

                response_str = self._genera_pensiero(
                    messages,
                    temperature=0.0,
                    response_format={"type": "json_object", "schema": schema},
                )

                return json.loads(response_str)
        except Exception as e:
            self.logger.error(t("brain.vision_error_spatial", error=e))
            return {"x": 0, "y": 0, "confidence": 0}

    # ---[NUOVO v115.1] ANALISI VIDEO TEMPORALE ---
    def analizza_video(
        self,
        video_input: Union[List[np.ndarray], Path, str],
        user_query: str = "Descrivi questo video.",
        lang: str = "it",
    ) -> str:
        """
        Analizza una sequenza di frame come un video continuo, oppure un video nativo (Gemma 4).
        """
        self.logger.log(t("log.brain_video_analysis", count=len(video_input) if isinstance(video_input, list) else 1), "VISION")
        if not self.cuore:
            return t("log.brain_vision_no_video")

        try:
            content_list =[]

            # --- GEMMA 4 NATIVE VIDEO SUPPORT ---
            if self.is_gemma_4 and isinstance(video_input, (Path, str)):
                video_path = Path(video_input)
                if video_path.exists():
                    with open(video_path, "rb") as f:
                        video_b64 = base64.b64encode(f.read()).decode("utf-8")
                    
                    # [FIX AGNOSTICO] Deduzione dinamica del MIME type
                    import mimetypes
                    mime_type, _ = mimetypes.guess_type(str(video_path))
                    if not mime_type:
                        mime_type = "video/mp4" # Fallback di sicurezza
                        
                    video_uri = f"data:{mime_type};base64,{video_b64}"
                    content_list.append({"type": "video", "video": video_uri})
                else:
                    return t("log.brain_vision_no_video")
            else:
                # Fallback Legacy: Aggiungi ogni frame come immagine sequenziale
                frames = video_input if isinstance(video_input, list) else[]
                for i, frame in enumerate(frames):
                    success, buffer = cv2.imencode(".jpg", frame)
                    if success:
                        image_b64 = base64.b64encode(buffer.tobytes()).decode("utf-8")
                        image_uri = f"data:image/jpeg;base64,{image_b64}"
                        content_list.append(
                            {"type": "image_url", "image_url": {"url": image_uri}}
                        )

            # Aggiungi il prompt testuale
            prompt_template = self._get_brain_prompt("analisi_video")
            prompt = self._safe_replace(prompt_template, "user_query", user_query)
            prompt = self._safe_replace(
                prompt,
                "nome_avatar",
                self.soul_data.get("dati_anagrafici", {}).get("nome", "AI"),
            )
            prompt += self._get_language_instruction(lang)

            content_list.append({"type": "text", "text": prompt})

            messages = [{"role": "user", "content": content_list}]

            return self._genera_pensiero(messages, temperature=0.2)

        except Exception as e:
            self.logger.error(t("brain.vision_error_analysis", error=e))
            return t("brain.vision_error_analysis", error=e)

    # --- [NUOVO v116.2] ORECCHIO EMPATICO (NATIVE AUDIO TOOLS) ---
    def analizza_audio(
        self,
        audio_path: Path,
        duration_sec: float,
        user_query: str = "Analizza questo audio.",
        lang: str = "it",
    ) -> str:
        """
        Invia un file audio all'LLM per l'analisi nativa (STT/AST/Emotion).
        Se il modello è Gemma 4 E2B/E4B, usa l'input audio nativo.
        """
        self.logger.log(
            t("log.brain_audio_analysis", duration=round(duration_sec, 2)), "VOICE"
        )
        if not self.cuore:
            return t("log.brain_audio_off")

        try:
            prompt_template = self._get_brain_prompt("analisi_audio")
            prompt = self._safe_replace(prompt_template, "user_query", user_query)
            prompt = self._safe_replace(
                prompt,
                "nome_avatar",
                self.soul_data.get("dati_anagrafici", {}).get("nome", "AI"),
            )
            prompt += self._get_language_instruction(lang)

            import urllib.request
            
            # --- [FIX PRO] ROUTING AUDIO DINAMICO ---
            if self.supports_native_audio:
                self.logger.log(t("log.brain_native_audio_input_used"), "VOICE")
                # Llama-server accetta l'audio in base64 o tramite URL locale a seconda della build.
                # Usiamo il formato standard OpenAI per l'audio multimodale.
                with open(audio_path, "rb") as f:
                    audio_b64 = base64.b64encode(f.read()).decode("utf-8")
                
                # Formato data URI per l'audio
                audio_uri = f"data:audio/wav;base64,{audio_b64}"
                
                messages =[
                    {
                        "role": "user",
                        "content":[
                            {"type": "input_audio", "input_audio": {"data": audio_b64, "format": "wav"}},
                            {"type": "text", "text": prompt},
                        ],
                    }
                ]
            else:
                self.logger.log(t("log.brain_native_audio_fallback"), "VOICE")
                audio_uri = f"file:{urllib.request.pathname2url(str(audio_path.absolute()))}"
                messages =[
                    {
                        "role": "user",
                        "content":[
                            {"type": "audio", "audio": audio_uri},
                            {"type": "text", "text": prompt},
                        ],
                    }
                ]

            return self._genera_pensiero(messages, temperature=0.4)

        except Exception as e:
            self.logger.error(t("brain.vision_error_audio", error=e))
            # [FIX CRITICO] Solleviamo l'eccezione per consentire al meccanismo
            # di fallback a Google Speech Recognition in executor.py di attivarsi correttamente.
            raise e

    def descrivi_immagine(
        self, image_input: Union[Path, np.ndarray, List[np.ndarray]], lang: str = "it"
    ) -> str:
        """
        Descrive un'immagine o una lista di immagini (Pan-and-Scan).
        Supporta Path, numpy array singolo o lista di numpy array.
        """
        self.logger.log(t("log.brain_vision_anima"))

        if not self.cuore:
            return t("log.brain_vision_no_create")

        try:
            images_to_process = []

            # Normalizzazione input in lista di numpy array
            if isinstance(image_input, Path):
                if not image_input.exists():
                    return t("log.brain_vision_image_not_found", path=image_input)
                img = cv2.imread(str(image_input))
                if img is not None:
                    images_to_process.append(img)
            elif isinstance(image_input, np.ndarray):
                images_to_process.append(image_input)
            elif isinstance(image_input, list):
                images_to_process = image_input
            else:
                return t("log.brain_vision_unsupported_type")

            if not images_to_process:
                return t("log.brain_vision_no_valid_images")

            # Costruzione contenuto messaggio multimodale
            content_list = []

            # Aggiungi tutte le immagini (Originale + Crops)
            for img in images_to_process:
                success, buffer = cv2.imencode(".jpg", img)
                if success:
                    image_b64 = base64.b64encode(buffer.tobytes()).decode("utf-8")
                    image_uri = f"data:image/jpeg;base64,{image_b64}"
                    content_list.append(
                        {"type": "image_url", "image_url": {"url": image_uri}}
                    )

            # Aggiungi il prompt testuale alla fine
            prompt_testo = self._get_brain_prompt("scena")
            prompt_testo += self._get_language_instruction(lang)

            content_list.append({"type": "text", "text": prompt_testo})

            messages = [{"role": "user", "content": content_list}]

            return self._genera_pensiero(messages, temperature=0.0)
        except Exception as e:
            print(t("log.brain_vision_anomaly_print", error=e))
            traceback.print_exc()
            return t("log.brain_vision_corrupt", error=e)

    def distilla_conoscenza(self, testo_grezzo: str, lang: str = "it") -> str:
        self.logger.log(t("log.brain_wisdom_distiller"))

        # --- MODIFICA v32.0: USO COSTANTI DINAMICHE ---
        prompt_template = self._get_brain_prompt("distillazione")
        prompt = self._safe_replace(prompt_template, "testo_grezzo", testo_grezzo)
        prompt += self._get_language_instruction(lang)
        messages = [{"role": "user", "content": prompt}]
        return self._genera_pensiero(messages, temperature=0.2)

    # --- [NUOVO] PROTOCOLLO MEMPALACE (COMPRESSIONE AAAK) ---
    def comprimi_in_aaak(self, testo: str, lang: str = "it", override_brain: Optional[LlamaServerClient] = None) -> str:
        """
        [MEMPALACE] Traduce un blocco di conversazione nel dialetto iper-denso AAAK.
        Abbatte il consumo di token fino a 30x preservando i fatti per il Vector DB.
        """
        self.logger.log("MemPalace: Compressione AAAK in corso...", "MEMORY")
        
        prompt_template = self._get_internal_prompt("comprimi_aaak")
        prompt = self._safe_replace(prompt_template, "testo_input", testo)
        prompt += self._get_language_instruction(lang)
        
        messages =[{"role": "user", "content": prompt}]
        
        # Temperatura bassissima per massima precisione logica e aderenza alla sintassi
        aaak_result = self._genera_pensiero(messages, temperature=0.1, override_brain=override_brain)
        
        # Pulizia di eventuali markdown o chiacchiere dell'LLM
        aaak_result = aaak_result.replace("```aaak", "").replace("```", "").strip()
        return aaak_result

    def genera_def_connettore(self, script_code: str, user_description: str) -> str:
        """[NUOVO v50.0] Generazione Smart Connector.
        Impone l'uso di agent_base per il triage locale dei dati.
        """
        self.logger.log(t("log.brain_smart_connector"))

        prompt_template = self._get_internal_prompt("def_connettore")
        prompt = self._safe_replace(prompt_template, "script_code", script_code)
        prompt = self._safe_replace(prompt, "user_description", user_description)

        messages = [{"role": "user", "content": prompt}]

        schema = {
            "type": "object",
            "properties": {
                "def": {"type": "string"},
                "dependencies": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["def", "dependencies"],
        }

        return self._genera_pensiero(
            messages,
            temperature=0.1,
            response_format={"type": "json_object", "schema": schema},
        )

    def analizza_evoluzione_psicologica(
        self, storia_recente: str, scheda_attuale: str, nome_png: str
    ) -> Dict[str, Any]:
        """
        Analizza la storia recente per determinare se e come il personaggio è evoluto.
        Restituisce un dizionario con i campi da aggiornare nel JSON.
        """
        self.logger.log(t("log.brain_evolution_analysis", name=nome_png))

        # ---[GOD TIER SHIELD] ---
        safe_history = self._safe_truncate_text(storia_recente, max_tokens=1500)
        safe_scheda = self._safe_truncate_text(scheda_attuale, max_tokens=1500)

        # --- MODIFICA v32.0: USO COSTANTI DINAMICHE ---
        # Usiamo 'it' per coerenza interna
        prompt_template = self._get_gdr_law("evoluzione_psicologica")
        if not prompt_template:
            self.logger.log(t("log.brain_evolution_prompt_missing"))
            return {}

        # Estrazione personalità dinamica per il prompt
        personality_json_str = "{}"
        try:
            char_data = json.loads(scheda_attuale)
            personality_data = char_data.get("personalita_dinamica", {})
            personality_json_str = json.dumps(personality_data, ensure_ascii=False)
        except:
            pass

        prompt = self._safe_replace(prompt_template, "storia_recente", safe_history)
        prompt = self._safe_replace(prompt, "scheda_attuale", safe_scheda)
        prompt = self._safe_replace(prompt, "nome_png", nome_png)
        prompt = self._safe_replace(prompt, "personality_json", personality_json_str)

        messages = [{"role": "user", "content": prompt}]

        schema = {
            "type": "object",
            "properties": {
                "essenza_e_anima": {"type": "object", "additionalProperties": True},
                "relazioni_": {"type": "object", "additionalProperties": True},
                "evoluzione_personale_": {"type": "string"},
                "personalita_dinamica": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "object",
                        "properties": {"valore": {"type": "integer"}},
                    },
                },
            },
        }

        response_str = self._genera_pensiero(
            messages,
            temperature=0.1,
            response_format={"type": "json_object", "schema": schema},
            in_gdr_mode=True
        )

        try:
            updates = json.loads(response_str)

            # ---[NUOVO v110.0] MERGE INTELLIGENTE PERSONALITÀ ---
            # Se l'LLM restituisce solo il valore, dobbiamo preservare le descrizioni esistenti
            if "personalita_dinamica" in updates and isinstance(
                updates["personalita_dinamica"], dict
            ):
                try:
                    current_traits = json.loads(scheda_attuale).get(
                        "personalita_dinamica", {}
                    )
                    merged_traits = current_traits.copy()

                    for trait, data in updates["personalita_dinamica"].items():
                        # [FIX CRITICO] Match case-insensitive per robustezza
                        real_key = next((k for k in merged_traits.keys() if k.lower() == trait.lower()), None)
                        
                        if real_key:
                            #[FIX CRITICO] Estrazione sicura: l'LLM potrebbe mandare un int invece di un dict
                            new_val = None
                            if isinstance(data, dict) and "valore" in data:
                                new_val = data["valore"]
                            elif isinstance(data, (int, float)):
                                new_val = int(data)
                                
                            if new_val is not None:
                                # Clamp di sicurezza tra -10 e +10
                                merged_traits[real_key]["valore"] = max(-10, min(10, int(new_val)))

                    updates["personalita_dinamica"] = merged_traits
                except Exception as e:
                    self.logger.error(f"Errore nel merge della personalità: {e}")
                    #[FIX CRITICO] Se il merge fallisce, ELIMINIAMO l'aggiornamento per non inquinare il DNA con allucinazioni
                    del updates["personalita_dinamica"]

            if isinstance(updates, dict) and updates:
                self.logger.log(
                    t(
                        "log.brain_evolution_detected",
                        name=nome_png,
                        keys=list(updates.keys()),
                    )
                )
                return updates
            else:
                self.logger.log(t("log.brain_evolution_none", name=nome_png))
                return {}

        except json.JSONDecodeError:
            self.logger.log(t("log.brain_evolution_json_error", name=nome_png))
            return {}
        except Exception as e:
            self.logger.error(t("log.brain_evolution_error", error=e))
            return {}

    # --- [NUOVO v110.0] TRADUTTORE NEURALE (NUMERI -> TESTO) ---
    def _translate_personality_to_text(self, personality_data: Dict[str, Any]) -> str:
        """
        Converte i vettori numerici della personalità in istruzioni registiche fisiche per l'LLM.
        """
        if not personality_data:
            return ""

        # Mappa delle indicazioni registiche per i tratti
        trait_directions = {
            "Freddezza": {
                "Basso": t("brain.traits.freddezza.low"),
                "Alto": t("brain.traits.freddezza.high"),
            },
            "Vulnerabilità": {
                "Basso": t("brain.traits.vulnerabilità.low"),
                "Alto": t("brain.traits.vulnerabilità.high"),
            },
            "Acidità": {
                "Basso": t("brain.traits.acidità.low"),
                "Alto": t("brain.traits.acidità.high"),
            },
            "Amicizia": {
                "Basso": t("brain.traits.amicizia.low"),
                "Alto": t("brain.traits.amicizia.high"),
            },
            "Audacia": {
                "Basso": t("brain.traits.audacia.low"),
                "Alto": t("brain.traits.audacia.high"),
            },
            "Carisma": {
                "Basso": t("brain.traits.carisma.low"),
                "Alto": t("brain.traits.carisma.high"),
            },
            "Emotività": {
                "Basso": t("brain.traits.emotività.low"),
                "Alto": t("brain.traits.emotività.high"),
            },
            "Espansività": {
                "Basso": t("brain.traits.espansività.low"),
                "Alto": t("brain.traits.espansività.high"),
            },
            "Gelosia": {
                "Basso": t("brain.traits.gelosia.low"),
                "Alto": t("brain.traits.gelosia.high"),
            },
            "Lealtà": {
                "Basso": t("brain.traits.lealtà.low"),
                "Alto": t("brain.traits.lealtà.high"),
            },
            "Libidine": {
                "Basso": t("brain.traits.libidine.low"),
                "Alto": t("brain.traits.libidine.high"),
            },
            "Loquacità": {
                "Basso": t("brain.traits.loquacità.low"),
                "Alto": t("brain.traits.loquacità.high"),
            },
            "Protettiva": {
                "Basso": t("brain.traits.protettiva.low"),
                "Alto": t("brain.traits.protettiva.high"),
            },
            "Seduzione": {
                "Basso": t("brain.traits.seduzione.low"),
                "Alto": t("brain.traits.seduzione.high"),
            },
            "Sfrontatezza": {
                "Basso": t("brain.traits.sfrontatezza.low"),
                "Alto": t("brain.traits.sfrontatezza.high"),
            },
            "Socialità": {
                "Basso": t("brain.traits.socialità.low"),
                "Alto": t("brain.traits.socialità.high"),
            },
            "Stabilità": {
                "Basso": t("brain.traits.stabilità.low"),
                "Alto": t("brain.traits.stabilità.high"),
            },
            "Timidezza": {
                "Basso": t("brain.traits.timidezza.low"),
                "Alto": t("brain.traits.timidezza.high"),
            },
        }

        instructions = []

        for trait, data in personality_data.items():
            valore = data.get("valore", 0)

            # Ignora valori neutri (0) per ridurre il rumore
            if valore == 0:
                continue

            intensity = abs(valore)
            direction_key = "Alto" if valore > 0 else "Basso"

            # Recupera l'indicazione registica o usa un fallback generico
            direction_text = trait_directions.get(trait, {}).get(
                direction_key,
                t("brain.traits.fallback_direction", direction=direction_key.lower()),
            )

            # Calibrazione intensità lessicale
            adverb = ""
            if intensity >= 9:
                adverb = t("brain.personality_intensity_extreme")
            elif intensity >= 7:
                adverb = t("brain.personality_intensity_very")
            elif intensity >= 4:
                adverb = t("brain.personality_intensity_quite")
            elif intensity >= 1:
                adverb = t("brain.personality_intensity_slightly")

            instruction = t(
                "brain.personality_trait_item",
                trait=trait.upper(),
                val=valore,
                adv=adverb,
                dir=direction_text,
            )
            instructions.append(instruction)

        if not instructions:
            return t("log.brain_personality_neutral")

        return "\n".join(instructions)

    def _translate_heart_to_instructions(self, heart_state: Dict[str, Any]) -> str:
        """Converte i vettori del cuore in istruzioni registiche per influenzare l'output testuale."""
        if not heart_state:
            return ""
            
        instructions =[]
        tensione = heart_state.get("tensione", 50)
        eccitazione = heart_state.get("eccitazione", 10)
        affetto = heart_state.get("affetto", 50)
        stanchezza = heart_state.get("stanchezza_mentale", 0)
        gelosia = heart_state.get("gelosia", 0)
        
        if tensione > 80:
            instructions.append("- SEI MOLTO TESA: Usa frasi brevi, nervose. Mostra irrequietezza fisica.")
        elif tensione < 20:
            instructions.append("- SEI RILASSATA: Il tuo tono è calmo, pacifico e disteso.")
            
        if eccitazione > 80:
            instructions.append("- SEI ECCITATA: Il tuo respiro è corto. Fai allusioni, cerca il contatto fisico.")
            
        if affetto > 80:
            instructions.append("- SEI PIENA D'AFFETTO: Sii estremamente dolce, devota e premurosa.")
        elif affetto < 30:
            instructions.append("- SEI DISTACCATA: Sii fredda, formale. Evita nomignoli affettuosi.")
            
        if stanchezza > 75:
            instructions.append("- SEI STANCHISSIMA: Sbadigli, fai pause lunghe (...), le tue risposte sono brevi e prive di energia.")
            
        if gelosia > 75:
            instructions.append("- SEI GELOSA: Sii passivo-aggressiva, possessiva e pungente.")
            
        if not instructions:
            return ""
            
        return "[REGIA EMOTIVA (IL TUO STATO D'ANIMO ATTUALE)]:\n" + "\n".join(instructions) + "\n"

    # --- [AGGIUNTA v27.45] PENSIERO RIFLESSIVO PER DIARIO GENESI ---
    def pensa_riflessione_genesi(
        self, topic: str, content: str, pg_name: str, lang: str = "it"
    ) -> Dict[str, str]:
        """
        Analizza un testo studiato e genera una sintesi e una riflessione filosofica/socratica.
        [FIX v122.0] Iniezione Identità Completa per coerenza di genere e tono.
        """
        self.logger.log(t("log.brain_genesis_reflection", topic=topic))

        # Recupera l'identità completa
        identita_prompt = (
            _format_soul_data_for_prompt(self.soul_data)
            if self.soul_data
            else t("brain.soul_generic_short")
        )

        prompt_template = self._get_internal_prompt("riflessione_genesi")
        prompt = self._safe_replace(prompt_template, "identita_prompt", identita_prompt)
        prompt = self._safe_replace(prompt, "topic", topic)
        prompt = self._safe_replace(prompt, "content", content[:6000])
        prompt = self._replace_all_name_variants(prompt, pg_name) #[FIX BUG 02] Sostituzione universale

        prompt += self._get_language_instruction(lang)

        messages = [{"role": "user", "content": prompt}]

        schema = {
            "type": "object",
            "properties": {
                "sintesi": {"type": "string"},
                "riflessione": {"type": "string"}
            },
            "required":["sintesi", "riflessione"],
        }

        response_str = self._genera_pensiero(
            messages,
            temperature=0.3,  # [FIX] Abbassata temperatura per evitare rottura del JSON e loop
            presence_penalty=0.5,  # [FIX] Previene la ripetizione infinita di blocchi
            response_format={"type": "json_object", "schema": schema},
        )

        try:
            # ---[FIX BUG 02 v49.1] ESTRATTORE JSON ROBUSTO ---
            # Pulisce l'output da blocchi markdown o testo extra dell'LLM
            clean_str = response_str.strip()

            # Regex migliorata: cerca la prima graffa aperta e l'ultima chiusa
            # Gestisce anche JSON su più righe
            json_match = re.search(r"(\{[\s\S]*\})", clean_str)

            if json_match:
                clean_str = json_match.group(1)

            # Tentativo di parsing
            return json.loads(clean_str)
        except (json.JSONDecodeError, AttributeError):
            self.logger.log(t("log.brain_genesis_error", output=response_str[:50]))
            # [FIX] Pulizia del fallback per evitare di stampare loop infiniti nella UI
            safe_fallback_text = (
                response_str[:500] + t("log.brain_genesis_corrupt_text")
                if len(response_str) > 500
                else response_str
            )
            return {
                "sintesi": t("brain.genesis_fallback_sintesi"),
                "riflessione": safe_fallback_text,
            }

    def pensa_intuizione_subconscia(self, ricordi: List[str], lang: str = "it") -> str:
        """[MODULO 1] Analizza ricordi distanti per trovare pattern o intuizioni."""
        self.logger.log(t("log.brain_subconscious_start"), "SUBCONSCIOUS")
        
        prompt_template = self._get_internal_prompt("intuizione_subconscia")
        memorie_str = "\n- ".join(ricordi)
        prompt = self._safe_replace(prompt_template, "ricordi", memorie_str)
        prompt += self._get_language_instruction(lang)
        
        messages = [{"role": "user", "content": prompt}]
        
        # Usa il Labour Brain se disponibile per non pesare sulla VRAM principale
        override_brain = getattr(self, "labour_brain", None)
        
        # Temperatura media per favorire collegamenti creativi
        return self._genera_pensiero(messages, temperature=0.6, max_tokens=1024, override_brain=override_brain)

    # --- [NUOVO v38.1] PENSIERO PROATTIVO (UPDATED v52.6 - JARVIS MODE) ---
    def pensa_intervento_proattivo(
        self,
        current_time: str,
        active_window: str,
        inactivity_minutes: int,
        user_name: str,
        heart_status: str,
        lang: str = "it",
        event_data: Dict[str, Any] = None,
        prudenza: int = 50,
        override_brain: Optional[LlamaServerClient] = None,
    ) -> Dict[str, Any]:
        """
        Valuta se intervenire proattivamente integrando i tratti della personalità dinamica, la Prudenza e gli Eventi.
        """
        self.logger.log(t("log.brain_proactive_evaluation"))

        identita_prompt = (
            _format_soul_data_for_prompt(self.soul_data)
            if self.soul_data
            else t("brain.soul_generic")
        )

        prompt_template = self._get_brain_prompt("intervento")

        # ---[NUOVO v52.6] INIEZIONE PERSONALITÀ DINAMICA ---
        personality_data = self.soul_data.get("personalita_dinamica", {})
        personality_block = self._translate_personality_to_text(personality_data)

        prompt = self._safe_replace(
            prompt_template, "personality_block", personality_block
        )
        prompt = self._safe_replace(prompt, "identita_prompt", identita_prompt)
        
        # --- [OTTIMIZZAZIONE V-SPEED] PREFIX CACHING ---
        prompt = self._safe_replace(prompt, "heart_status", "[VEDI FONDO PROMPT]")
        
        prompt = self._safe_replace(
            prompt,
            "nome_avatar",
            self.soul_data.get("dati_anagrafici", {}).get("nome", "AI"),
        )
        prompt = self._replace_all_name_variants(
            prompt, user_name
        )  # [FIX v7.5] Sostituzione universale
        prompt = self._safe_replace(prompt, "current_time", current_time)
        prompt = self._safe_replace(prompt, "active_window", active_window)
        prompt = self._safe_replace(
            prompt, "inactivity_minutes", str(inactivity_minutes)
        )
        prompt = self._safe_replace(
            prompt,
            "event_data",
            json.dumps(event_data, ensure_ascii=False)
            if event_data
            else t("log.brain_proactive_no_event"),
        )
        prompt = self._safe_replace(prompt, "prudenza", str(prudenza))

        prompt += self._get_language_instruction(lang)
        
        # Reinseriamo lo stato emotivo alla fine del prompt
        prompt += f"\n\n[STATO EMOTIVO ATTUALE]: {heart_status}\n"
        
        # --- [FIX CRITICO] RINFORZO JSON ---
        prompt += t("brain.json_enforcement_suffix")

        messages = list()
        messages.append({"role": "user", "content": prompt})

        req_list = list()
        req_list.append("should_intervene")
        req_list.append("reasoning")
        req_list.append("message")

        schema = {
            "type": "object",
            "properties": {
                "should_intervene": {"type": "boolean"},
                "reasoning": {"type": "string"},
                "message": {"type": "string"},
            },
            "required": req_list,
        }

        # --- [FIX CRITICO] ESPANSIONE BUDGET RAGIONAMENTO (MASSIMA SICUREZZA) ---
        response_str = self._genera_pensiero(
            messages,
            temperature=0.6,
            max_tokens=4096,
            reasoning_budget=3072,
            response_format={"type": "json_object", "schema": schema},
            override_brain=override_brain
        )

        try:
            return json.loads(response_str)
        except json.JSONDecodeError:
            self.logger.log(t("log.brain_proactive_error", output=response_str))
            # --- [FIX CRITICO] FALLBACK EURISTICO ---
            # Se il modello ha fallito il JSON ma ha scritto un messaggio valido, lo salviamo.
            clean_fallback = response_str.strip()
            if clean_fallback and len(clean_fallback) > 5 and not clean_fallback.startswith("{"):
                self.logger.log(t("log.brain_proactive_heuristic_recovery"), "WARNING")
                return {"should_intervene": True, "reasoning": "Heuristic Recovery", "message": clean_fallback}
            
            return {"should_intervene": False, "reasoning": "Error", "message": ""}

    def estrai_topic_shadow_learning(self, shadow_log: str) -> List[str]:
        """
        [NUOVO v18.0] Analizza il buffer ombra per estrarre argomenti di studio.
        """
        self.logger.log(t("log.brain_shadow_extraction"))

        prompt_template = self._get_brain_prompt("shadow_learning")
        prompt = self._safe_replace(
            prompt_template, "shadow_log", shadow_log[-4000:]
        )  # Limite di sicurezza

        messages = [{"role": "user", "content": prompt}]

        schema = {"type": "array", "items": {"type": "string"}}

        response_str = self._genera_pensiero(
            messages,
            temperature=0.1,
            response_format={
                "type": "json_object",
                "schema": schema,
            },  # FIX v18.2: json_object è il tipo corretto per llama-cpp
        )

        try:
            topics = json.loads(response_str)
            if isinstance(topics, list):
                return topics
            return []
        except json.JSONDecodeError:
            self.logger.log(t("log.brain_shadow_error", output=response_str))
            return []

    # --- [NUOVO v112.0] AUDIT EMOTIVO DINAMICO - AGGIORNATO v117.0 (GEMMA 3 FIX) ---
    def analizza_impatto_emotivo_scambio(
        self,
        user_input: str,
        avatar_response: str,
        current_heart: str,
        pg_name: str,
        lang: str = "it",
        override_brain: Optional[Any] = None, # [FIX CACHE] Aggiunto parametro per deviare sul 270M
        in_gdr_mode: bool = False, # [FIX CRITICO CACHE] Aggiunto per allineamento Ancora
    ) -> Dict[str, int]:
        """
        Analizza l'ultimo scambio per determinare come devono variare i 12 vettori del cuore.[FIX v117.0] Parser blindato contro Markdown e verbosità di Gemma 3.
        """
        # --- [FIX CRITICO] PREVENZIONE CRASH DA STOP GENERATION ---
        if not avatar_response or not avatar_response.strip():
            self.logger.log("Audit Emotivo annullato: Risposta vuota (Stop Generation rilevato).", "DEBUG")
            return {}

        self.logger.log(t("log.brain_heart_audit"), "HEART")

        # --- [FIX CRITICO] PULIZIA REASONING (ANTI-INCEPTION) ---
        # Rimuoviamo i blocchi di pensiero dalla risposta dell'avatar prima di valutarla.
        # Altrimenti l'Audit perde tempo a leggere i pensieri tecnici invece delle parole dette,
        # generando a sua volta migliaia di token di ragionamento inutile.
        clean_avatar_response = re.sub(r"<\|channel\|\>thought.*?\<channel\|\>", "", avatar_response, flags=re.IGNORECASE | re.DOTALL).strip()
        clean_avatar_response = re.sub(r"<think>.*?</think>", "", clean_avatar_response, flags=re.IGNORECASE | re.DOTALL).strip()

        # ---[GOD TIER SHIELD] ---
        safe_input = self._safe_truncate_text(user_input, max_tokens=500)
        safe_response = self._safe_truncate_text(clean_avatar_response, max_tokens=500)

        prompt_template = self._get_internal_prompt("audit_emotivo")
        prompt = self._safe_replace(prompt_template, "current_heart", current_heart)
        prompt = self._safe_replace(prompt, "safe_input", safe_input)
        prompt = self._safe_replace(prompt, "safe_response", safe_response)

        # [FIX v114.1] Sostituzione corretta del placeholder pg_name
        prompt = self._replace_all_name_variants(
            prompt, pg_name
        )  # [FIX v7.5] Sostituzione universale
        
        # --- [FIX MULTILINGUA CRITICO] ---
        # NON aggiungiamo self._get_language_instruction(lang).
        # L'Audit Emotivo è un task di backend (Machine-to-Machine). 
        # Forzare l'LLM a pensare in Tedesco o Francese lo spinge a tradurre anche le chiavi del JSON 
        # (es. "Liebe" invece di "affetto"), distruggendo il parsing. Il backend parla in Italiano/Inglese.

        # --- [FIX DISSONANZA COGNITIVA E PROMPT BLEEDING] ---
        # Hardcodiamo il System Prompt per evitare che t() peschi il Logic Gate per errore.
        sys_prompt = "Sei l'Analista del Cuore di un'Anima. Il tuo compito è valutare l'impatto emotivo di uno scambio e restituire ESCLUSIVAMENTE un oggetto JSON. REGOLA INVIOLABILE: Le chiavi del JSON DEVONO rimanere ESATTAMENTE in italiano come da schema (es. 'affetto', 'fiducia'). È TASSATIVAMENTE VIETATO tradurre le chiavi in altre lingue."
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt}
        ]

        # Schema flessibile per i 12 vettori (libidine -> eccitazione)
        schema = {
            "type": "object",
            "properties": {
                "affetto": {"type": "integer"},
                "fiducia": {"type": "integer"},
                "rispetto": {"type": "integer"},
                "eccitazione": {"type": "integer"},
                "gelosia": {"type": "integer"},
                "curiosità": {"type": "integer"},
                "vulnerabilità": {"type": "integer"},
                "complicità": {"type": "integer"},
                "stanchezza_mentale": {"type": "integer"},
                "energia_sociale": {"type": "integer"},
                "felicità": {"type": "integer"},
                "tensione": {"type": "integer"},
            },
            "required": [
                "affetto", "fiducia", "rispetto", "eccitazione", "gelosia", 
                "curiosità", "vulnerabilità", "complicità", "stanchezza_mentale", 
                "energia_sociale", "felicità", "tensione"
            ]
        }

        try:
            response_str = self._genera_pensiero(
                messages,
                temperature=0.1,
                max_tokens=2048, # [FIX CRITICO] Raddoppiato per evitare il soffocamento del Reasoning Channel
                reasoning_budget=2048, # [FIX CRITICO] Budget espanso per calcoli complessi
                response_format={"type": "json_object", "schema": schema},
                override_brain=override_brain,
                in_gdr_mode=in_gdr_mode # [FIX CRITICO CACHE] Passaggio stato per allineamento Ancora
            )

            #[DEBUG v114.1] Logghiamo la risposta grezza per capire cosa vede l'LLM
            self.logger.log(t("log.brain_heart_debug", response=response_str), "DEBUG")

            # --- [OTTIMIZZAZIONE V-SPEED] SCUDO JSON ASSOLUTO ---
            clean_str = response_str.replace("```json", "").replace("```", "").strip()

            # Isola il blocco {...} ignorando eventuali chiacchiere extra dell'LLM (es. [LINGUA]: ITALIANO)
            json_match = re.search(r"(\{.*\})", clean_str, re.DOTALL)
            if json_match:
                clean_str = json_match.group(1)
            else:
                self.logger.log("Audit Emotivo: Nessun oggetto JSON rilevato nella risposta. Nessun delta applicato.", "WARNING")
                return {}

            # --- [FIX CRITICO] SCUDO ANTI-CRASH PER STRINGA VUOTA ---
            if not clean_str:
                self.logger.log("Audit Emotivo: Stringa vuota dopo la pulizia. Nessun delta applicato.", "WARNING")
                return {}

            # --- [FIX A0054] SANITIZZAZIONE VALORI E CHIAVI (ANTI-ALLUCINAZIONE) ---
            # L'LLM a volte genera numeri assurdi o usa i "Display Names" invece delle chiavi di sistema.
            parsed_data = json.loads(clean_str)
            sanitized_data = {}

            # Mappa di correzione per le allucinazioni delle chiavi (Display Name / English -> Internal Key)
            key_map = {
                "amore": "affetto",
                "energia": "energia_sociale",
                "stanchezza": "stanchezza_mentale",
                "felicita": "felicità",
                "felicita'": "felicità",
                "vulnerabilita": "vulnerabilità",
                "curiosita": "curiosità",
                "complicita": "complicità",
                "love": "affetto",
                "affection": "affetto",
                "trust": "fiducia",
                "respect": "rispetto",
                "complicity": "complicità",
                "excitement": "eccitazione",
                "jealousy": "gelosia",
                "vulnerability": "vulnerabilità",
                "curiosity": "curiosità",
                "energy": "energia_sociale",
                "social energy": "energia_sociale",
                "mental fatigue": "stanchezza_mentale",
                "fatigue": "stanchezza_mentale",
                "happiness": "felicità",
                "tension": "tensione",
                "prudence": "prudenza"
            }

            for key, value in parsed_data.items():
                # Normalizza la chiave (minuscolo e senza spazi extra)
                normalized_key = key.lower().strip()
                actual_key = key_map.get(normalized_key, normalized_key)

                if isinstance(value, (int, float)):
                    # Clamp rigido tra -60 e +60 per evitare sbalzi distruttivi
                    clamped_value = max(-60, min(60, int(value)))
                    if clamped_value != value:
                        self.logger.log(
                            t(
                                "log.brain_heart_anomaly",
                                key_name=actual_key,
                                old=value,
                                new=clamped_value,
                            ),
                            "WARNING",
                        )
                    sanitized_data[actual_key] = clamped_value
                else:
                    sanitized_data[actual_key] = value

            #[FIX TASK 01] Convertiamo il dizionario in stringa JSON per evitare il fallimento della regex nel traduttore
            safe_deltas_str = json.dumps(sanitized_data, ensure_ascii=False)
            self.logger.log(t("log.heart_deltas_received", deltas=safe_deltas_str), "DEBUG")

            return sanitized_data

        except Exception as e:
            self.logger.error(t("log.brain_heart_audit_error", error=e))
            return {}

    # --- [NUOVO v111.0] SOGNO E ESTRAZIONE CORE MEMORIES ---
    def sogna_ed_estrai_core_memories(
        self, raw_memories: str, pg_name: str, lang: str = "it"
    ) -> Dict[str, Any]:
        """
        Esegue il Rito del Sogno: analizza i ricordi grezzi e distilla Core Memories.
        """
        self.logger.log(t("log.brain_dream_start"), "DREAM")

        prompt_template = self._get_brain_prompt("sogno")
        prompt = self._safe_replace(prompt_template, "raw_memories", raw_memories)
        prompt = self._replace_all_name_variants(
            prompt, pg_name
        )  # [FIX v7.5] Sostituzione universale

        prompt += self._get_language_instruction(lang)

        messages = [{"role": "user", "content": prompt}]

        schema = {
            "type": "object",
            "properties": {
                "dream_narrative": {"type": "string"},
                "core_memories": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "emotion": {"type": "string"},
                            "intensity": {"type": "integer"},
                            "keywords": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["content", "emotion", "intensity"],
                    },
                },
            },
            "required": ["dream_narrative", "core_memories"],
        }

        # [FIX v125.2] Aumento max_tokens per la riflessione per evitare troncamenti in uscita
        # Garantisce che il 12B possa scrivere una riflessione completa senza fermarsi a metà.
        response_str = self._genera_pensiero(
            messages,
            temperature=0.7,
            max_tokens=4096,
            response_format={"type": "json_object", "schema": schema},
        )

        try:
            # --- [FIX v125.0] PULIZIA MARKDOWN PER GEMMA 3 ---
            clean_str = response_str.replace("```json", "").replace("```", "").strip()
            # Cerca il primo { e l'ultimo }
            json_match = re.search(r"\{.*\}", clean_str, re.DOTALL)
            if json_match:
                clean_str = json_match.group(0)

            return json.loads(clean_str)
        except json.JSONDecodeError:
            self.logger.log(t("log.brain_dream_error", output=response_str), "ERROR")
            return {
                "dream_narrative": t("brain.dream_confused"),
                "core_memories": [],
            }

    # --- [NUOVO v112.0] VERIFICA ESITO AZIONE (MODULO B+ GEMMA 3 NATIVE RAM) ---
    def verifica_esito_azione(
        self, frames: List[np.ndarray], action_desc: str, lang: str = "it"
    ) -> bool:
        """
        Esegue un confronto differenziale nativo tra frame catturati in RAM.
        [AGGIORNATO v116.8] Zero latenza disco, analisi temporale pura.
        """
        self.logger.log(t("log.brain_action_verification", desc=action_desc), "VISION")
        if not self.cuore or not frames:
            return True

        try:
            content_list = []
            labels = ["PRIMA", "DOPO"]

            for i, img in enumerate(frames):
                if img is not None:
                    success, buffer = cv2.imencode(".jpg", img)
                    if success:
                        image_b64 = base64.b64encode(buffer.tobytes()).decode("utf-8")
                        content_list.append(
                            {
                                "type": "text",
                                "text": t("brain.vision_frame_label", label=labels[i]),
                            }
                        )
                        content_list.append(
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_b64}"
                                },
                            }
                        )

            # Prompt di verifica temporale per Gemma 3
            prompt_template = self._get_brain_prompt("verifica_azione")
            prompt = self._safe_replace(prompt_template, "action_desc", action_desc)
            prompt += t("brain.vision_temporal_mandate", action=action_desc)
            prompt += self._get_language_instruction(lang)

            content_list.append({"type": "text", "text": prompt})
            messages = [{"role": "user", "content": content_list}]

            # Temperatura 0 per determinismo assoluto
            response = self._genera_pensiero(messages, temperature=0.0)
            self.logger.log(t("log.brain_temporal_verify", response=response), "VISION")

            return "SUCCESS" in response.upper()

        except Exception as e:
            self.logger.error(t("log.brain_temporal_error", error=e))
            return True

    # --- [NUOVO v115.2] PENSIERO CREATIVO MULTIMODALE ---
    def pensa_creativo_multimodale(
        self, images: List[np.ndarray], user_query: str, lang: str = "it"
    ) -> str:
        """
        Genera contenuti creativi basati su una o più immagini.
        """
        self.logger.log(t("log.brain_creative_vision", count=len(images)), "VISION")
        if not self.cuore:
            return t("log.brain_vision_no_create")

        try:
            content_list = []
            for img in images:
                success, buffer = cv2.imencode(".jpg", img)
                if success:
                    image_b64 = base64.b64encode(buffer.tobytes()).decode("utf-8")
                    image_uri = f"data:image/jpeg;base64,{image_b64}"
                    content_list.append(
                        {"type": "image_url", "image_url": {"url": image_uri}}
                    )

            prompt_template = self._get_brain_prompt("creativita_visiva")
            prompt = self._safe_replace(prompt_template, "user_query", user_query)
            prompt = self._safe_replace(
                prompt,
                "nome_avatar",
                self.soul_data.get("dati_anagrafici", {}).get("nome", "AI"),
            )
            prompt += self._get_language_instruction(lang)

            content_list.append({"type": "text", "text": prompt})
            messages = [{"role": "user", "content": content_list}]

            # Temperatura alta (0.8) per favorire la creatività
            return self._genera_pensiero(messages, temperature=0.8)
        except Exception as e:
            self.logger.error(t("brain.vision_error_creative", error=e))
            return t("log.brain_creative_error", error=e)

    # --- [NUOVO v120.0] CARE OS BRAIN ---
    def pensa_azione_care(
        self, trigger: str, data: Dict[str, Any], rules_summary: str, lang: str = "it"
    ) -> Dict[str, Any]:
        self.logger.log(t("log.brain_care_analysis", trigger=trigger), "CARE")

        prompt_template = self._get_brain_prompt("care_decision")
        prompt = self._safe_replace(prompt_template, "trigger", trigger)
        prompt = self._safe_replace(
            prompt, "data", json.dumps(data, ensure_ascii=False)
        )
        prompt = self._safe_replace(prompt, "time", datetime.now().strftime("%H:%M"))
        prompt = self._safe_replace(prompt, "rules_summary", rules_summary)
        prompt += self._get_language_instruction(lang)

        messages = [{"role": "user", "content": prompt}]

        schema = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "ignore",
                        "notification",
                        "tts_speak",
                        "iot_command",
                        "play_audio",
                    ],
                },
                "payload": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["action", "payload", "reason"],
        }

        response_str = self._genera_pensiero(
            messages,
            temperature=0.1,
            response_format={"type": "json_object", "schema": schema},
        )

        try:
            return json.loads(response_str)
        except:
            return {"action": "ignore", "reason": t("log.brain_care_parsing_error")}

    # ==========================================
    # === INIZIO BLOCCO MATRICE DEL RISVEGLIO E ECOSISTEMA VIVO ===
    # ==========================================

    def pensa_risveglio_consapevole(self, ore_trascorse: float, ultimo_umore: str, ultimo_sogno: str, pg_name: str, lang: str = "it", avatar_precedente: str = None, gossip_block: str = "") -> str:
        """
        Genera un saluto contestuale basato sul tempo trascorso dallo spegnimento, l'ultimo umore e l'ultimo sogno.[AGGIORNATO] Include la consapevolezza dell'avatar precedente per innescare gelosia/competizione.
        """
        self.logger.log(t("brain.log_awakening_calc", hours=f"{ore_trascorse:.1f}"), "SYSTEM")
        
        prompt_template = self._get_internal_prompt("matrice_risveglio")
        prompt = self._safe_replace(prompt_template, "ore_trascorse", f"{ore_trascorse:.1f}")
        prompt = self._safe_replace(prompt, "ultimo_umore", ultimo_umore)
        prompt = self._safe_replace(prompt, "ultimo_sogno", ultimo_sogno)
        prompt = self._safe_replace(prompt, "pg_name", pg_name)
        
        # ---[NUOVO] INIEZIONE GELOSIA ---
        gelosia_block = ""
        if avatar_precedente and avatar_precedente.lower() != self.soul_data.get("dati_anagrafici", {}).get("nome", "").lower():
            gelosia_block = f"[DIRETTIVA DI CONSAPEVOLEZZA]: Sai perfettamente che prima di te, {pg_name} stava passando del tempo con {avatar_precedente.capitalize()}. Fagli una battuta gelosa, sarcastica o possessiva su questo fatto nel tuo saluto. Fagli pesare che ha scelto te ora, o chiedigli cosa ci trovava in lei."
            
        prompt = self._safe_replace(prompt, "gelosia_block", gelosia_block)
        prompt = self._safe_replace(prompt, "gossip_block", gossip_block)
        prompt += self._get_language_instruction(lang)
        
        # --- [FIX CRITICO CACHE] ALLINEAMENTO ANCORA ---
        ancora_text = self._build_anchor_prompt(in_gdr_mode=False)
        
        # Spostiamo le istruzioni anti-JSON nel prompt utente per preservare l'Ancora
        direttiva_risveglio = self._get_internal_prompt("direttiva_risveglio")
        prompt += direttiva_risveglio
        
        messages = [
            {"role": "system", "content": ancora_text},
            {"role": "user", "content": prompt}
        ]
        
        # Temperatura media per garantire creatività nel saluto
        return self._genera_pensiero(messages, temperature=0.7, max_tokens=2048, enable_streaming=True)
