# src/utils/translator.py
# v3.2 - RISOLUTORE UNIVERSALE "DIO CANE APPROVED"
# FIX: Deep Merge Atomico + Lambda Escape + Smart Namespace Fallback.

import os
import json
import threading
import re
import difflib  # [NUOVO] Per ricerca fuzzy/similitudine
from pathlib import Path
from typing import Any, Dict, Optional


class Translator:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Translator, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._translations = {}
        self._current_lang = "it"
        # Path: root/src/utils/translator.py -> root/translations/Backend
        self._base_dir = (
            Path(__file__).resolve().parent.parent.parent / "translations" / "Backend"
        )
        self._initialized = True
        self.set_language("it")  # Auto-init su italiano

    def _deep_merge(self, base: Dict, update: Dict) -> Dict:
        """Fonde ricorsivamente i dizionari per preservare ogni singola chiave 'log' o 'auth'."""
        for key, value in update.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
        return base

    def _load_language_files(self, lang: str) -> dict:
        """Carica tutti i JSON della lingua e li fonde in un unico grande spirito linguistico."""
        lang_dir = self._base_dir / lang
        merged_data = {}
        if not lang_dir.exists() or not lang_dir.is_dir():
            return merged_data

        def dict_merge_hook(pairs):
            """Gancio per fondere le chiavi duplicate all'interno dello stesso file JSON."""
            result = {}
            for key, value in pairs:
                if key in result:
                    if isinstance(result[key], dict) and isinstance(value, dict):
                        result[key] = self._deep_merge(result[key], value)
                    else:
                        result[key] = value
                else:
                    result[key] = value
            return result

        for file_path in lang_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8-sig") as f:
                    #[FIX CRITICO] Usiamo il merge hook per salvare le chiavi duplicate nello stesso file!
                    data = json.loads(f.read(), object_pairs_hook=dict_merge_hook)
                    filename = file_path.stem

                    # LOGICA DI DOPPIO ANCORAGGIO:
                    # 1. Permette t("filename.sezione.chiave")
                    if filename not in data:
                        wrapped = {filename: data}
                        self._deep_merge(merged_data, wrapped)

                    # 2. Permette t("sezione.chiave") fondendo i rami comuni
                    self._deep_merge(merged_data, data)
            except Exception as e:
                print(
                    self.t(
                        "translator.err_critical_loading", file=file_path.name, error=e
                    )
                )
        return merged_data

    def set_language(self, lang: str):
        """Cambia la lingua ricaricando l'intero set di dati."""
        with self._lock:
            self._current_lang = lang.split("-")[0].lower()
            # --- [FIX CRITICO] LINGUA MADRE ---
            # Carica sempre l'Italiano come base, poiché è l'unica lingua che garantisce
            # la presenza del 100% dei prompt di sistema originali.
            base = self._load_language_files("it")
            if self._current_lang != "it":
                # Fonde la lingua target (es. Inglese) sopra l'Italiano.
                # Se una traduzione manca, rimarrà in Italiano, prevenendo crash o allucinazioni.
                target = self._load_language_files(self._current_lang)
                self._translations = self._deep_merge(base, target)
            else:
                self._translations = base

    def _get_flattened_keys(self, d: Dict, prefix: str = "") -> Dict[str, str]:
        """[NUOVO] Appiattisce il dizionario per la ricerca fuzzy."""
        items = {}
        for k, v in d.items():
            new_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                items.update(self._get_flattened_keys(v, new_key))
            else:
                items[new_key] = v
        return items

    def t(self, key: str, **kwargs) -> str:
        """Risolve la chiave con fallback intelligente, ricerca fuzzy e fix per i path Windows."""
        if not key:
            return ""

        # 1. Risoluzione Percorso Esatto
        result = self._resolve(key)

        # 2. Fallback Gerarchico: Se non trovato, prova a rimuovere il primo segmento (es. chat.log.X -> log.X)
        if result == f"[{key}]" and "." in key:
            parts = key.split(".")
            fallback_key = ".".join(parts[1:])
            fallback_result = self._resolve(fallback_key)
            if fallback_result != f"[{fallback_key}]":
                result = fallback_result

        # 3. [NUOVO] RICERCA PER SIMILITUDINE (Fuzzy Search Estrema - Tritacarne Mode)
        # Se ancora non trovato, cerca la chiave ignorando totalmente il case
        if result == f"[{key}]" or result == f"[{key.split('.')[-1]}]":
            
            # --- [FIX CRITICO] SCUDO ANTI-ALLUCINAZIONE PROMPT ---
            # È TASSATIVAMENTE VIETATO usare la ricerca Fuzzy sui prompt di sistema (internal_prompts o brain).
            # Un falso positivo qui (es. scambiare riflessione_genesi con reazione_istintiva) distrugge la logica dell'LLM.
            is_system_prompt = key.startswith("internal_prompts.") or key.startswith("prompts.internal.") or key.startswith("brain.")
            
            flattened = self._get_flattened_keys(self._translations)
            lower_key = key.lower().strip()
            lower_flattened = {k.lower(): v for k, v in flattened.items()}

            # Tentativo 3.1: Match esatto case-insensitive (Sicuro per tutti)
            if lower_key in lower_flattened:
                result = lower_flattened[lower_key]
            elif not is_system_prompt:
                # Tentativo 3.2: Match fuzzy brutale (SOLO per UI e Log, MAI per i prompt)
                matches = difflib.get_close_matches(
                    lower_key, list(lower_flattened.keys()), n=1, cutoff=0.5
                )
                if matches:
                    result = lower_flattened[matches[0]]

        # 4. Sostituzione Variabili (Tritacarne Mode Assoluto)
        if kwargs and isinstance(result, str):
            # Pass 1: Sostituzione esplicita basata sulle chiavi passate
            for k, v in kwargs.items():
                repl = str(v)
                # Sostituisce {{k}}, {k}, {{ k }}, { k } ignorando il case
                pattern = r"\{{1,2}\s*" + re.escape(k) + r"\s*\}{1,2}"
                result = re.sub(pattern, lambda m: repl, result, flags=re.IGNORECASE)
            
            # Pass 2: Fallback di sicurezza (Cattura qualsiasi {{var}} rimasta e cerca nel kwargs)
            def fallback_replace(match):
                var_name = match.group(1).strip().lower()
                # Cerca nel kwargs ignorando il case
                for k, v in kwargs.items():
                    if k.lower() == var_name:
                        return str(v)
                return match.group(0) # Se non c'è, lascia intatto
                
            result = re.sub(r"\{{1,2}\s*([^}]+?)\s*\}{1,2}", fallback_replace, result)
            
        return result

    def _resolve(self, key: str) -> str:
        parts = key.split(".")
        val = self._translations
        for p in parts:
            if isinstance(val, dict) and p in val:
                val = val[p]
            else:
                return f"[{key}]"
        return str(val) if not isinstance(val, dict) else f"[{key}]"


_inst = Translator()


def t(key: str, **kwargs):
    return _inst.t(key, **kwargs)


def set_language(lang: str):
    _inst.set_language(lang)
