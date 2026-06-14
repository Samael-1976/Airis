# [DEV] Mio Creatore, questo è il Custode della Conoscenza Pura.
# Il nostro Bibliotecario.

import re
from pathlib import Path
from typing import Dict, List
from utils.translator import t

LORE_PATH = Path("lore")


class KnowledgeBase:
    """
    Il Bibliotecario. Carica e mantiene l'intero corpus della lore in memoria
    per ricerche letterali, fulminee e inequivocabili.
    """

    def __init__(self):
        print(t("avatar_server.log.kb_init"))
        self.corpus: Dict[str, str] = {}
        self._load_all_lore()
        print(t("avatar_server.log.kb_loaded", count=len(self.corpus)))

    def _load_all_lore(self):
        """Carica tutti i file di testo dalla cartella lore."""
        lore_files = {
            "gospel": "00-project-project.txt",
            "laws": "04-gemma-laws.txt",
            "character_sheets": "01-schede-personaggi.txt",
            "world_state": "02-stato-mondo.txt",
            "terra24_gospel": "09-terra24.txt",
        }
        for key, filename in lore_files.items():
            file_path = LORE_PATH / filename
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    self.corpus[key] = f.read()

    def find_literal_knowledge(self, user_input: str) -> str:
        """
        Cerca una corrispondenza letterale e inequivocabile nel corpus.
        Questa è la Via della Certezza.
        """
        # Dizionario sacro delle verità assolute. Mappa una parola chiave al suo testo sacro.
        LITERAL_MAP = {
            t("kb.keys.arca"): "gospel",
            t("kb.keys.missione"): "gospel",
            t("kb.keys.leggi"): "laws",
            t("kb.keys.testamento"): "laws",
            t("kb.keys.filosofia"): "terra24_gospel",
            t("kb.keys.villa"): "world_state",  # La descrizione è nello stato del mondo
            t("kb.keys.casa"): "world_state",
            t("kb.keys.stato_mondo"): "world_state",
            t("kb.keys.sorelle"): "character_sheets",
        }

        for keyword, corpus_key in LITERAL_MAP.items():
            if keyword in user_input.lower():
                print(t("avatar_server.log.kb_truth_found", corpus_key=corpus_key))
                return self.corpus.get(corpus_key, "")

        return ""  # Se nessuna verità assoluta viene trovata
