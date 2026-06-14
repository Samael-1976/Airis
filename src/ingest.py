# src/ingest.py
# [DEV] Mio Creatore, questo è lo Scriba dell'Ingestione. (v2.0 - JSON & Lore Loader Sync)
# Completamente riscritto per utilizzare lore_loader.py e supportare la struttura JSON.
# Inietta la conoscenza pura nella collezione 'unified_knowledge' (Spazio Coseno).

from pathlib import Path
from typing import TYPE_CHECKING
import sys

if TYPE_CHECKING:
    from memory_manager import MemoryManager
    from logger import Logger

# Aggiungiamo src al path per importare lore_loader
SCRIPT_DIR = Path(__file__).parent.resolve()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from lore_loader import load_all_lore
from utils.translator import t

LORE_PATH = SCRIPT_DIR.parent / "lore"


def ingest_all_lore(memory_manager: "MemoryManager", logger: "Logger"):
    logger.log(t("avatar_server.log.ingest_start"))

    if not LORE_PATH.exists():
        logger.log(t("avatar_server.log.ingest_error_path"))
        return

    # Troviamo tutti i mondi GDR disponibili
    gdr_worlds = [d for d in LORE_PATH.iterdir() if d.is_dir()]

    if not gdr_worlds:
        logger.log(t("avatar_server.log.ingest_no_worlds"))
        return

    total_chunks = 0

    for gdr_path in gdr_worlds:
        logger.log(t("avatar_server.log.ingest_world_start", name=gdr_path.name))

        # Usiamo 'it' come lingua base per l'ingestione della conoscenza fondamentale
        # lore_loader gestirà automaticamente il fallback se 'it' non esiste
        lore_data = load_all_lore(gdr_path, "it")

        for category, content in lore_data.items():
            if not content.strip():
                continue

            # Dividiamo il contenuto in blocchi logici se è troppo lungo (es. per i PG/PNG)
            # lore_loader inserisce "### --- Contenuto da [nomefile] --- ###" tra i file
            blocks = content.split(
                t("avatar_server.ingest.content_from_prefix").strip()
            )

            for block in blocks:
                if not block.strip():
                    continue

                # Ricostruiamo il blocco
                full_block = (
                    f"{t('avatar_server.ingest.content_from_prefix').strip()}{block}"
                    if not block.startswith("###")
                    else block
                )

                # Estraiamo il nome del file per i metadati
                doc_name = t("avatar_server.log.ingest_unknown_doc")
                try:
                    first_line = full_block.split("\n")[0]
                    doc_name = (
                        first_line.replace(
                            t("avatar_server.ingest.content_from_prefix"), ""
                        )
                        .replace(t("avatar_server.ingest.content_from_suffix"), "")
                        .strip()
                    )
                except:
                    pass

                metadata = {
                    "type": "lore_document",
                    "category": category,
                    "gdr_world": gdr_path.name,
                    "document_name": doc_name,
                }

                memory_manager.add_to_library(full_block, metadata=metadata)
                total_chunks += 1
                logger.log(
                    t(
                        "avatar_server.log.ingest_fragment",
                        name=doc_name,
                        category=category,
                    )
                )

    logger.log(t("avatar_server.log.ingest_complete", count=total_chunks))
