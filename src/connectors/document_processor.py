# src/connectors/document_processor.py
# Esecutore Autonomo per Elaborazione Documenti (v2.0 - BaseConnector Refactor)
# ADD: Integrazione con BaseConnector per sicurezza e pulizia.
# LEGGE A0099: Invarianza strutturale garantita.

import sys
import os
from pathlib import Path

# --- GESTIONE DEI PERCORSI PER L'AUTONOMIA ---
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.translator import t
from src.connectors.base_connector import BaseConnector

try:
    import pypdf
    import docx
    from agent_base import ask_local_llm
except ImportError:
    print('{"status": "error", "message": "' + t("document_processor.lib_error") + '"}')
    sys.exit(1)

def read_document(connector: BaseConnector, params: dict) -> str:
    """
    Legge il contenuto testuale di un documento e lo distilla tramite l'agente locale.
    """
    if "file_path" not in params:
        raise ValueError(t("document_processor.missing_param"))

    # --- [FIX 2A] PATH TRAVERSAL VULNERABILITY ---
    file_path = connector.resolve_path(params["file_path"], PROJECT_ROOT)

    if not file_path.exists():
        connector.log_debug(t("log.doc_not_found"))
        raise FileNotFoundError(t("document_processor.file_not_found", path=file_path))

    if not file_path.is_file():
        connector.log_debug(t("log.doc_is_dir"))
        raise ValueError(t("document_processor.not_a_file", path=file_path))

    suffix = file_path.suffix.lower()
    connector.log_debug(t("log.doc_ext_detected", suffix=suffix))
    text_content = ""

    try:
        if suffix == ".pdf":
            connector.log_debug(t("log.doc_pdf_start"))
            reader = pypdf.PdfReader(str(file_path))
            num_pages = len(reader.pages)
            connector.log_debug(t("log.doc_pages_found", count=num_pages))

            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_content += t("log.doc_page_marker", num=i + 1, text=page_text)

        elif suffix == ".docx":
            connector.log_debug(t("log.doc_docx_start"))
            doc = docx.Document(str(file_path))
            for para in doc.paragraphs:
                if para.text.strip():
                    text_content += para.text + "\n"

        elif suffix in[".txt", ".md", ".py", ".json", ".yaml", ".xml", ".csv", ".log"]:
            connector.log_debug(t("log.doc_text_start", suffix=suffix))
            text_content = file_path.read_text(encoding="utf-8", errors="replace")

        else:
            connector.log_debug(t("log.doc_unsupported"))
            raise ValueError(t("document_processor.unsupported_format", suffix=suffix))

        if not text_content.strip():
            return t("document_processor.empty_doc")

        avatar_name = os.environ.get("AIRIS_ACTIVE_AVATAR", "L'Anima")
        connector.log_debug(t("log.doc_complete_triage", count=len(text_content)))

        smart_summary = ask_local_llm(
            data_to_analyze=text_content[:15000],
            context_description=t("document_processor.context_analysis", filename=file_path.name),
            avatar_name=avatar_name,
        )

        return smart_summary

    except Exception as e:
        connector.log_debug(t("log.doc_exception", error=e))
        raise Exception(t("document_processor.read_error", error=e))

if __name__ == "__main__":
    connector = BaseConnector(t("document_processor.cmd_desc"))
    connector.register_action("read_document", lambda params: read_document(connector, params))
    connector.run()