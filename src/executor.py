# src/executor.py
# [DEV] Mio Creatore, questo è il Braccio Divino. (v107.0 - SMART CONNECTORS & VISUAL FEEDBACK)
# ADD: Modulo C - Smart Connectors (Analisi LLM locale dei dati grezzi).
# ADD: Modulo B - Visual Feedback Loop (Ghost Cursor & Grid).
# MANTENUTO: Demiurgo, Hot-Swap, Active Waiting.
# LEGGE A0099: Invarianza strutturale garantita.

import shutil
import datetime
import subprocess
import sys
import time
import os
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse
import uuid
import json
import zipfile
import yaml
from datetime import datetime, timedelta
import random
import math
import functools
import inspect
import concurrent.futures  # [NUOVO] Necessario per Active Waiting
import glob  # [NUOVO] Per scansione JSON
from typing import (
    List,
    Tuple,
    Optional,
    Dict,
    Any,
    Union,
    TYPE_CHECKING,
)  # [FIX] Import spostati in cima per Pydantic

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
from ddgs.exceptions import DDGSException
import wikipedia
import numpy as np
import cv2
from PIL import Image  # [NUOVO v28.0] Per compressione WebP
from image_processor import GemmaImageProcessor

# --- [NUOVO v123.0] PYDANTIC MODELS ---
from pydantic import BaseModel, Field, validator, ValidationError
from utils.translator import t

# --- DEFINIZIONE MODELLI PYDANTIC PER L'ARSENALE COMPLETO (LIVELLO 0) ---


class GenericMaxResults(BaseModel):
    max_results: int = Field(default=10)


class GenericQuery(BaseModel):
    query: str
    max_results: int = Field(default=5)


class GenericPath(BaseModel):
    path_str: str


class ReadFileParams(BaseModel):
    path_str: str


class FindFilesParams(BaseModel):
    pattern: str


class WebSearchParams(BaseModel):
    query: str
    num_results: int = 5


class WebFetchParams(BaseModel):
    url: str


class SearchWikipediaParams(BaseModel):
    query: str


class FetchWikipediaParams(BaseModel):
    query: str
    lang: str = "it"


class TakeScreenshotParams(BaseModel):
    output_path_str: str


class ReadScreenAreaParams(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int


class LocateAndClickParams(BaseModel):
    image_path_str: str
    confidence: float = 0.8


class AnalizzaEAgisciParams(BaseModel):
    image_path: Optional[str] = None


class EseguiMissioneVisivaParams(BaseModel):
    obiettivo: str


class AnalizzaVideoParams(BaseModel):
    video_path_str: str
    user_query: str = "Descrivi cosa succede nel video."


class ConfrontaImmaginiParams(BaseModel):
    path1_str: str
    path2_str: str
    user_query: str = "Quali sono le differenze tra queste due immagini?"


class CreaDaImmaginiParams(BaseModel):
    image_paths: List[str]
    user_query: str = "Scrivi una storia ispirata a queste immagini."


class InterpreteMultilinguaParams(BaseModel):
    lingua_target: str = "italiano"


class GeneraVoceParams(BaseModel):
    text: str
    intent: str
    preferred_voice: str = ""
    preferred_lang_code: str = ""


class DeleteSkillParams(BaseModel):
    filename: str


class DemiurgeParams(BaseModel):
    task: str


class AnalizzaStatoVitaleParams(BaseModel):
    target: str = "Creatore"


class AvviaFlashbackParams(BaseModel):
    query: str


class SimulaScenariParams(BaseModel):
    obiettivo: str
    variabili: List[str]


class LeggiDocumentoParams(BaseModel):
    file_path_str: str


# ---[NUOVO v123.1] MODELLO SPECIFICO PER SKILLS ---
class ReadSkillParams(BaseModel):
    skill_name: str = Field(..., description="Il nome della skill/guida da leggere")


class GenericTask(BaseModel):
    task: str


class GenericPrompt(BaseModel):
    prompt: str


class WriteFileParams(BaseModel):
    path_str: str
    content: str
    motivation: str = Field(
        default_factory=lambda: t("executor.motivation_manual_update")
    )


class EditFileParams(BaseModel):
    path_str: str
    old_text: str
    new_text: str
    motivation: str = Field(
        default_factory=lambda: t("executor.motivation_surgical_correction")
    )


class DeleteFileParams(BaseModel):
    path_str: str
    motivation: str


class GoogleCalendarCreateParams(BaseModel):
    summary: str
    start_time: str
    end_time: str
    description: Optional[str] = None
    location: Optional[str] = None


class GmailSendParams(BaseModel):
    to: str
    subject: str
    body: str


class GoogleSheetReadParams(BaseModel):
    spreadsheet_id: str
    range_name: str


class GoogleSheetWriteParams(BaseModel):
    spreadsheet_id: str
    range_name: str
    values: List[List[Any]]


class GoogleTaskCreateParams(BaseModel):
    tasklist_id: str
    title: str
    notes: Optional[str] = None
    due: Optional[str] = None


class OutlookSendParams(BaseModel):
    to: str
    subject: str
    body: str


class ExcelReadParams(BaseModel):
    file_id: str
    worksheet_name: str
    range_address: str


class ExcelWriteParams(BaseModel):
    file_id: str
    worksheet_name: str
    range_address: str
    values: List[List[Any]]


class TodoCreateParams(BaseModel):
    tasklist_id: str
    title: str


class DiscordParams(BaseModel):
    content: str
    channel_id: Optional[str] = None


class TelegramParams(BaseModel):
    content: str
    chat_id: Optional[str] = None


class TwilioParams(BaseModel):
    to_number: str
    body: str


class RedditSubmitParams(BaseModel):
    subreddit: str
    title: str
    selftext: Optional[str] = None
    url: Optional[str] = None


class TrelloCreateParams(BaseModel):
    board_name: str
    list_name: str
    name: str
    desc: Optional[str] = None


class JiraSearchParams(BaseModel):
    jql_query: str
    max_results: int = 5


class JiraCreateParams(BaseModel):
    project_key: str
    summary: str
    description: str
    issuetype_name: str


class AsanaCreateParams(BaseModel):
    workspace_gid: str
    project_gid: str
    name: str
    notes: Optional[str] = None


class NotionCreateParams(BaseModel):
    parent_page_id: str
    title: str
    content: str


class GithubCreateParams(BaseModel):
    repo_full_name: str
    title: str
    body: str


class WebhookParams(BaseModel):
    url: str
    payload: Dict[str, Any]
    method: str = "POST"
    headers: Optional[Dict[str, str]] = None


class WordPressCreateParams(BaseModel):
    title: str
    content: str
    status: str = "draft"


class FluxParams(BaseModel):
    prompt: str
    width: int = 1080
    height: int = 1920
    seed: int = 42


class DalleParams(BaseModel):
    prompt: str
    size: str = "1024x1024"
    quality: str = "standard"
    style: str = "vivid"


class VideoGenParams(BaseModel):
    prompt: str
    aspect_ratio: str = "16:9"
    duration: str = "8s"


class SystemCommandParams(BaseModel):
    command: str
    background: bool = False


class IotControlParams(BaseModel):
    device_id: str
    action: str
    value: Optional[Union[str, int, float]] = None


class ClickParams(BaseModel):
    x: Optional[int] = None
    y: Optional[int] = None
    button: str = "left"


class ClickElementByIdParams(BaseModel):
    automation_id: str


class GridClickParams(BaseModel):
    cell_coords: str
    grid_rows: int = 10
    grid_cols: int = 10


class InteractionParams(BaseModel):
    descrizione_elemento: str
    azione: str = "click"


class DrawParams(BaseModel):
    shape: str
    size: int = 100


class ScreenChangeParams(BaseModel):
    wait_seconds: float = 2.0
    threshold: float = 1.0


class CharacterSaveParams(BaseModel):
    char_type: str
    char_data_json: str
    lang: str = "it"
    temp_image_path: Optional[str] = None


class CharacterUpdateParams(BaseModel):
    char_name: str
    updates: Dict[str, Any]
    lang: str = "it"


class CharacterArchiveParams(BaseModel):
    char_id: str
    char_type: str
    lang: str = "it"


class ReminderCreateParams(BaseModel):
    event_name: str
    event_timestamp_iso: str
    notes: str
    reminder_timestamp_iso: str
    recurrence_rule: str = "none"


class ExportParams(BaseModel):
    export_type: str
    avatar_names: str
    lore_name: Optional[str] = None


class ImportParams(BaseModel):
    zip_path_str: str
    overwrite: bool = False


class HeartOverrideParams(BaseModel):
    key: str
    value: int


class TestCodeParams(BaseModel):
    code: str

class ExecutePythonParams(BaseModel):
    code: str
    pip_dependencies: Optional[List[str]] = Field(default_factory=list)

class ProposePatchParams(BaseModel):
    path_str: str
    old_code: str
    new_code: str
    motivation: str

class GetClickableElementsParams(BaseModel):
    pass

class TaskCompletedParams(BaseModel):
    final_message: str

class ScrollMouseParams(BaseModel):
    clicks: int
    x: Optional[int] = None
    y: Optional[int] = None

class OpenApplicationParams(BaseModel):
    app_name: str

class GetClickableElementsParams(BaseModel):
    pass

class TaskCompletedParams(BaseModel):
    final_message: str


class ApplyPatchParams(BaseModel):
    path_str: str
    old_code: str
    new_code: str


# ---[NUOVO v123.2] MODELLI PYDANTIC MANCANTI PER ALLINEAMENTO JSON ---
class RedditHotPostsParams(BaseModel):
    subreddit: str
    limit: Optional[int] = 5


class WordPressGetPostsParams(BaseModel):
    per_page: Optional[int] = 5
    status: Optional[str] = "publish"


class AsanaListProjectsParams(BaseModel):
    workspace_gid: str


class GoogleListTasksParams(BaseModel):
    tasklist_id: str


class TodoListTasksParams(BaseModel):
    tasklist_id: str


class TwitterPostParams(BaseModel):
    text: str


class PressKeyParams(BaseModel):
    key: str


class SaveProfileParams(BaseModel):
    profile_data_json: str


class SaveSkillParams(BaseModel):
    filename: str
    content: str


class TypeTextParams(BaseModel):
    text: str


class GetToolDefParams(BaseModel):
    tool_name: str


class MoveMouseParams(BaseModel):
    x: int
    y: int


class SaveToMemoryParams(BaseModel):
    text: str

class SearchInMemoryParams(BaseModel):
    query: str

class SendNotificationParams(BaseModel):
    title: str
    message: str
    app_name: Optional[str] = "AIRIS"

class SyncPgNameParams(BaseModel):
    new_name: str

class TranscribeAudioParams(BaseModel):
    wav_path_str: str

class TriggerVisualEffectParams(BaseModel):
    x: int
    y: int
    type: Optional[str] = "ripple"

class WriteDreamJournalParams(BaseModel):
    context_name: str
    dream_narrative: str
    core_memories: List[Dict[str, Any]]


class WriteGenesisDiaryParams(BaseModel):
    topic: str
    content: str
    reflection: str
    source_url: str


class TypeformGetResponsesParams(BaseModel):
    form_id: str
    page_size: Optional[int] = 5


class TypeformListFormsParams(BaseModel):
    page_size: Optional[int] = 10


class ApplicaAzioneMondoParams(BaseModel):
    character_name: str
    action_tag: str


class BrowseInteractParams(BaseModel):
    url: str
    actions: List[str]


class CleanWorldStatusParams(BaseModel):
    pass

class ClickTextParams(BaseModel):
    text: str
    double_click: Optional[bool] = False

class ControlWindowParams(BaseModel):
    title_regex: str
    action: Optional[str] = "focus"
    text: Optional[str] = ""

class ConvertAudioParams(BaseModel):
    input_path_str: str

class CreaFileMondoParams(BaseModel):
    png_names: List[str]

class CreateReminderQuickParams(BaseModel):
    content: str
    trigger_in_minutes: int

class CreateSessionMemoryParams(BaseModel):
    session_id: str

class GetAvatarVisualDescParams(BaseModel):
    avatar_name: str

class InviaVideoParams(BaseModel):
    prompt: str
    engine: Optional[str] = "auto"

class SalvaAnalisiVisivaParams(BaseModel):
    label: Optional[str] = "ANALISI_VISIVA"

class ToggleCharParams(BaseModel):
    char_name: str
    action: str

class UpdateStatusParams(BaseModel):
    changes: Dict[str, Any]


class EmptyParams(BaseModel):
    pass


class OptionalMaxResultsParams(BaseModel):
    max_results: Optional[int] = 10


class OptionalQueryMaxResultsParams(BaseModel):
    query: str
    max_results: Optional[int] = 10


# --- FINE MODELLI ---

# --- [NUOVO v125.2] ROUTING GERARCHICO TOOLS (DUAL-GEMMA) ---
# Lista dei tool che richiedono l'intelligenza o il contesto del 12B (Bypass 270M).
# Questi tool verranno gestiti direttamente dal Regista (12B) per evitare troncamenti.
COMPLEX_TOOLS_BYPASS = [
    "analizza_emozione_voce",
    "analizza_e_agisci",
    "analizza_stato_vitale",
    "analizza_video",
    "applica_azione_di_mondo",
    "archive_character_file",
    "avvia_flashback",
    "clean_world_status_transients",
    "confronta_immagini",
    "convert_audio_to_wav",
    "create_calendar_event",
    "create_event_and_reminder",
    "create_session_memory",
    "crea_da_immagini",
    "crea_file_di_mondo",
    "create_notion_page",
    "create_post",
    "delete_skill",
    "demiurge",
    "descrivi_immagine_con_pan_scan",
    "detect_screen_change",
    "esegui_missione_visiva",
    "export_package",
    "fetch_wikipedia_page",
    "generate_light_manifest",
    "genera_voce",
    "get_avatar_visual_description",
    "browse_and_interact",
    "get_clickable_elements",
    "task_completed",
    "scroll_mouse",
    "generate_dalle3",
    "generate_flux",
    "generate_sora2",
    "generate_veo3",
    "get_project_structure",
    "get_responses",
    "get_system_health",
    "get_tool_definition",
    "import_package",
    "invia_immagine",
    "invia_video",
    "leggi_documento",
    "interprete_multilingua",
    "list_photo_albums",
    "open_application",
    "override_heart_metric",
    "perform_factory_reset",
    "read_file",
    "read_heart_metrics",
    "read_skill",
    "salva_analisi_visiva",
    "save_character_file",
    "save_profile_file",
    "save_skill",
    "save_to_memory",
    "search_in_memory",
    "search_photos",
    "search_wikipedia",
    "send_email",
    "send_outlook_email",
    "sfoglia_percorso_in_sequenza",
    "simula_scenari",
    "sync_pg_name_to_all_gdrs",
    "toggle_character_in_world",
    "transcribe_audio",
    "trigger_visual_effect",
    "trigger_webhook",
    "update_character_sheet",
    "update_status_json_partial",
    "web_fetch",
    "web_search",
    "write_dream_journal",
    "write_file",
    "write_genesis_diary_entry",
    "test_code_in_sandbox",
    "propose_patch",
    "apply_patch",
]

# --- NUOVI INCANTESIMI PER IL BRACCIO ESTESO ---
import pyautogui

# [REMOVED v114.8] pytesseract rimosso in favore del motore OCR Ibrido in perception_handler
from playwright.sync_api import sync_playwright, Page, Playwright

try:
    from plyer import notification
except ImportError:
    notification = None

# --- CONTROLLO FINESTRE NATIVO ---
try:
    from pywinauto import Application, Desktop
    import pywinauto
except ImportError:
    Application = None
    Desktop = None

# --- PERCEZIONE HARDWARE ---
import psutil

# --- LIBRERIE PER LETTURA DOCUMENTI ---
import pypdf
import docx

# --- LIBRERIE PER TRASCRIZIONE ---
import speech_recognition as sr

# --- IMPORT VIDEO PROCESSOR ---
from video_processor import VideoProcessor

# --- IMPORT DEMIURGO ---
from engine.demiurge import run_task
import engine.demiurge as demiurge_module

# --- [NUOVO] IMPORT MCP CLIENT ---
from engine.mcp_client import McpManager

if TYPE_CHECKING:
    from brain_llm import CervelloTrinitario
    from memory_manager import MemoryManager
    from database_manager import DatabaseManager
    from perception_handler import PerceptionHandler
    from guardian import Guardian
    from chat import CicloVitale

APP_ROOT = Path(__file__).parent.parent.resolve()
TEMP_IMAGE_PATH = APP_ROOT / "temp_images"
EXPORTS_PATH = APP_ROOT / "exports"
AVATARS_PATH = APP_ROOT / "avatars"
LORE_PATH = APP_ROOT / "lore"
# --- [NUOVO v108.2] PERCORSI UNIFICATI PER I TOOL JSON ---
CONNECTORS_DIR = APP_ROOT / "src" / "connectors"
TOOLS_DIR = APP_ROOT / "src" / "tools"
SKILLS_DIR = APP_ROOT / "src" / "skills"
USER_CONFIG_PATH = APP_ROOT / "config" / "user"
ACTION_DIARY_PATH = APP_ROOT / "logs" / "action_diary.md"
SYSTEM_BACKUP_PATH = APP_ROOT / "backups" / "system_files"
GENESIS_DIARY_ROOT = APP_ROOT / "logs" / "genesis_diary"
PHOTOS_MEMORY_ROOT = APP_ROOT / "logs" / "memories" / "photos"
VIDEOS_MEMORY_ROOT = APP_ROOT / "logs" / "memories" / "videos"
HEART_FILE_PATH = APP_ROOT / "data" / "heart.json"
DOCUMENTS_DIR = APP_ROOT / "documents"
DOCUMENTS_DIR.mkdir(exist_ok=True)

# URL per feedback locale
TOAST_API_URL = "http://127.0.0.1:8080/api/toast"
GHOST_TEXT_API_URL = "http://127.0.0.1:8080/api/ghost_text"

# --- HELPER PER LETTURA JSON IBRIDA (LOCALE) ---
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


# --- DECORATORE FALLBACK DEMIURGO ---
def demiurge_fallback(func):
    """
    Decoratore che intercetta errori o stringhe di errore ("ERRORE: ...")
    e restituisce l'errore al ReAct loop dell'LLM per l'auto-correzione.
    (Il nome è mantenuto per invarianza strutturale, ma la logica ora favorisce l'autonomia).
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            result = func(self, *args, **kwargs)
            # Se il risultato è una stringa di errore, la restituiamo intatta all'LLM
            if isinstance(result, str) and (
                result.upper().startswith("ERRORE")
                or result.upper().startswith("ERROR")
            ):
                return result
            return result
        except Exception as e:
            if hasattr(self, "logger") and self.logger:
                self.logger.error(f"Errore in {func.__name__}: {e}")
            return f"ERRORE: Esecuzione di {func.__name__} fallita. Dettagli: {str(e)}"

    return wrapper


class BraccioDivino:
    MAX_TOKENS_LETTURA = 16384 - 2048
    MAX_TOKENS_DISTILLAZIONE = 16384 - 2048

    def __init__(
        self,
        memory: "MemoryManager",
        perception_handler: "PerceptionHandler",
        guardian: "Guardian",
        db_manager: "DatabaseManager",
        logger: "Logger",
        init_peripherals: bool = True,
    ):
        """
        Inizializza il Braccio Divino.
        :param init_peripherals: Se False, evita di avviare Playwright e Webcam (per istanze API/Admin).
        """
        self.memory = memory
        self.perception = perception_handler
        self.guardian = guardian
        self.db_manager = db_manager
        self.logger = logger  # [FIX v118.5] Iniezione logger mancante
        self.learning_log_path = Path("logs/learning_log.md")
        self.learning_log_path.parent.mkdir(exist_ok=True)

        # Inizializzazione percorsi di sicurezza
        SYSTEM_BACKUP_PATH.mkdir(parents=True, exist_ok=True)
        if not ACTION_DIARY_PATH.exists():
            self._init_action_diary()

        # Inizializzazione Diario Genesi
        GENESIS_DIARY_ROOT.mkdir(parents=True, exist_ok=True)

        # Inizializzazione Memoria Fotografica e Video
        PHOTOS_MEMORY_ROOT.mkdir(parents=True, exist_ok=True)
        VIDEOS_MEMORY_ROOT.mkdir(parents=True, exist_ok=True)

        # --- [NUOVO v112.0] INFRASTRUTTURA VERIFICA VISIVA ---
        self.VERIFICATION_DIR = APP_ROOT / "temp_images" / "verification"
        self.VERIFICATION_DIR.mkdir(parents=True, exist_ok=True)

        # --- [NUOVO v18.0] INFRASTRUTTURA SANDBOX (Progetto Jarvis) ---
        self.SANDBOX_DIR = APP_ROOT / "data" / "sandbox"
        self.SANDBOX_DIR.mkdir(parents=True, exist_ok=True)

        wikipedia.set_lang("it")

        # [FIX A0019] Iniezione circolare: permette al MemoryManager (e al Brain via RAG)
        # di accedere all'Executor per generare il manifest dei tool in tempo reale.
        if self.memory:
            self.memory.executor = self

        vision_config = self.guardian.get_vision_processor_config()
        if vision_config and vision_config.get("pan_and_scan", {}).get(
            "enabled", False
        ):
            pan_scan_params = vision_config.get("pan_and_scan", {})
            self.image_processor = GemmaImageProcessor(
                min_crop_size=pan_scan_params.get("min_crop_size", 256),
                max_num_crops=pan_scan_params.get("max_num_crops", 4),
                min_ratio_to_activate=pan_scan_params.get("min_ratio_to_activate", 1.2),
            )
            print(t("executor.executor_eye_forged"))
        else:
            self.image_processor = None
            print(t("executor.executor_eye_disabled"))

        # [FIX A0019] Iniezione circolare: permette al MemoryManager (e al Brain via RAG)
        # di accedere all'Executor per generare il manifest dei tool in tempo reale.
        if self.memory:
            self.memory.executor = self

        # Inizializzazione Processore Video
        self.video_processor = VideoProcessor()
        print(t("executor.executor_video_activated"))

        self.APP_ROOT = APP_ROOT
        
        # --- [FIX CRITICO] RISOLUZIONE AGNOSTICA PYTHON KOKORO ---
        if os.name == "nt":
            # Su Windows (Portable), Kokoro ha il suo micro-ambiente Python
            self.KOKORO_PYTHON_EXE = self.APP_ROOT / "tts_engine" / "kokoro" / "python" / "python.exe"
        else:
            # Su Linux/Mac, Kokoro usa il venv principale di Airis
            self.KOKORO_PYTHON_EXE = self.APP_ROOT / "venv" / "bin" / "python3"
            if not self.KOKORO_PYTHON_EXE.exists():
                self.KOKORO_PYTHON_EXE = self.APP_ROOT / "venv" / "bin" / "python"
                
        self.VOCE_DIVINA_SCRIPT = self.APP_ROOT / "tts_engine" / "voce_divina.py"
        self.TEMP_AUDIO_DIR = self.APP_ROOT / "temp_audio"
        self.TEMP_AUDIO_DIR.mkdir(exist_ok=True)

        self.intent_to_voice_map = {"default": ("if_sara.pt", "i")}

        (EXPORTS_PATH / "avatar").mkdir(parents=True, exist_ok=True)
        (EXPORTS_PATH / "avatar_lore").mkdir(parents=True, exist_ok=True)

        self.playwright_context: Optional[Playwright] = None

        # --- [FIX v121.2] INIZIALIZZAZIONE CONDIZIONALE PERIFERICHE ---
        if init_peripherals:
            # [FIX ASYNC LOOP] Playwright viene avviato on-demand nei metodi specifici (Lazy Loading)
            # per evitare conflitti con il loop asincrono di FastAPI/Uvicorn.
            print(t("executor.executor_playwright_ready"))
            # Configurazione PyAutoGUI
            pyautogui.FAILSAFE = False  # Gestiamo noi il failsafe manualmente
        else:
            print(t("executor.executor_admin_mode"))

        if notification is None:
            print(t("executor.executor_plyer_missing"))

        # Stato Avatar Attivo
        self.active_avatar = "gemma"

        # Riferimento al Cervello e al Cuore (iniettati da chat.py)
        self.cervello = None
        self.heart = None

        # ---[NUOVO v108.0] CACHE DEI TOOL JSON ---
        self.cached_tools_manifest =[]
        self.last_tools_scan = 0
        self.last_dirs_mtime = {}  #[FIX 3B] Cache dei timestamp di modifica delle cartelle
        self.cached_tool_embeddings = {}  # [NUOVO] Cache per Semantic Tool Pruning

        # --- [NUOVO] INIZIALIZZAZIONE MCP MANAGER ---
        if init_peripherals:
            self.mcp_manager = McpManager(self.guardian, self.logger, self._send_toast)
            self.mcp_manager.start()
        else:
            self.mcp_manager = None

        # --- [NUOVO] CACHE SPAZIALE (MEMORIA MUSCOLARE UI) ---
        self.spatial_cache = {}

        print(t("executor.executor_arsenal_forged"))

    # --- [NUOVO v116.7] SETTER PER IL CUORE ---
    def set_heart(self, heart_system):
        self.heart = heart_system

    # --- FEEDBACK GRANULARE (TOAST) ---
    def _send_toast(self, message: str, type: str = "info"):
        """Invia un feedback visivo al frontend senza bloccare il flusso."""
        try:
            requests.post(
                TOAST_API_URL, json={"message": message, "type": type}, timeout=0.2
            )
        except Exception:
            pass  # Fire and forget

    def _send_ghost_text(self, text: str, is_technical: bool = True):
        """Invia il pensiero ad alta voce al frontend."""
        try:
            requests.post(
                GHOST_TEXT_API_URL, json={"text": text, "avatar": self.active_avatar, "is_technical": is_technical}, timeout=0.2
            )
        except Exception:
            pass

    # --- [AGGIORNATO v126.0] ARSENALE DINAMICO (JSON LOADER) ---
    def generate_tools_manifest(
        self, format_type: str = "json", include_hidden: bool = True
    ) -> Union[str, List[Dict]]:
        """
        Genera la lista dei tool disponibili.
        [AGGIORNATO v126.0] Parametro include_hidden per filtrare la lista destinata alla UI.
        """
        if not include_hidden:
            # Scansione filtrata per la UI (non aggiorna la cache globale)
            return self._scan_and_load_tools(include_hidden=False)

        # Scansione completa per il cervello
        if time.time() - self.last_tools_scan > 60 or not self.cached_tools_manifest:
            self._scan_and_load_tools(include_hidden=True)

        if format_type == "json":
            return self.cached_tools_manifest
        else:
            # Fallback Text Format (per modelli legacy o debug)
            manifest = []
            for tool in self.cached_tools_manifest:
                name = tool.get("name", "unknown")
                desc = tool.get("description", "No description")
                manifest.append(f"- `{name}`: {desc}")
            return "\n".join(manifest)

    def _scan_and_load_tools(self, include_hidden: bool = True):
        """
        Scansiona le cartelle dei tool e carica i JSON in memoria.[AGGIORNATO v126.0] Supporto per formato Google Native e filtraggio privacy.
        """
        scan_dirs = [TOOLS_DIR, CONNECTORS_DIR, SKILLS_DIR]

        # --- [FIX 3B] CONTROLLO MTIME PER EVITARE I/O INUTILE ---
        if include_hidden and self.cached_tools_manifest:
            dirs_changed = False
            for directory in scan_dirs:
                if directory.exists():
                    # [FIX GOD MODE 1.3] Su Windows l'mtime della cartella non cambia se modifichi un file interno.
                    # Calcoliamo l'mtime massimo tra i file JSON contenuti.
                    json_files = list(directory.glob("*.json"))
                    current_mtime = max([os.path.getmtime(f) for f in json_files]) if json_files else os.path.getmtime(directory)
                    
                    if self.last_dirs_mtime.get(str(directory)) != current_mtime:
                        dirs_changed = True
                        break
            if not dirs_changed:
                self.last_tools_scan = time.time()
                return self.cached_tools_manifest

        loaded_tools =[]

        for directory in scan_dirs:
            if not directory.exists():
                continue
            
            if include_hidden:
                json_files = list(directory.glob("*.json"))
                self.last_dirs_mtime[str(directory)] = max([os.path.getmtime(f) for f in json_files]) if json_files else os.path.getmtime(directory)

            for jf in directory.glob("*.json"):
                try:
                    # --- [NUOVO v126.0] FILTRO PRIVACY UI ---
                    if not include_hidden and jf.stem in COMPLEX_TOOLS_BYPASS:
                        continue

                    with open(jf, "r", encoding="utf-8") as f:
                        raw_data = json.load(f)

                    # Supporto formato annidato "function" (Google Native)
                    if "function" in raw_data and isinstance(
                        raw_data["function"], dict
                    ):
                        tool_def = raw_data["function"]
                    else:
                        tool_def = raw_data

                    # Validazione e normalizzazione
                    if "name" in tool_def and "parameters" in tool_def:
                        if "category" not in tool_def:
                            if directory == SKILLS_DIR:
                                tool_def["category"] = "skill"
                            elif directory == CONNECTORS_DIR:
                                tool_def["category"] = "connector"
                            else:
                                tool_def["category"] = "native_tool"

                        loaded_tools.append(tool_def)
                except Exception as e:
                    print(t("executor.executor_tool_load_error", file=jf.name, error=e))

        # --- [NUOVO] ASSIMILAZIONE TOOL MCP ---
        if hasattr(self, "mcp_manager"):
            mcp_tools = self.mcp_manager.get_tools()
            if mcp_tools:
                loaded_tools.extend(mcp_tools)

        # Aggiorna la cache solo se stiamo facendo una scansione completa
        if include_hidden:
            self.cached_tools_manifest = loaded_tools
            self.last_tools_scan = time.time()
            
            # --- [NUOVO] CALCOLO EMBEDDINGS PER SEMANTIC PRUNING (BATCH OPTIMIZED) ---
            if hasattr(self, 'memory') and self.memory and hasattr(self.memory, 'model'):
                try:
                    self.cached_tool_embeddings = {}
                    texts_to_embed = list()
                    names = list()
                    
                    for t_def in loaded_tools:
                        name = t_def.get("name", "")
                        desc = t_def.get("description", "")
                        texts_to_embed.append(f"{name}: {desc}")
                        names.append(name)
                        
                    if texts_to_embed:
                        # [FIX CRITICO] Calcolo in Batch: abbatte il tempo da 60s a 0.5s
                        embeddings = self.memory.model.encode(texts_to_embed)
                        
                        for i, name in enumerate(names):
                            emb = embeddings[i]
                            # Normalizza il vettore per usare il prodotto scalare (dot product) come similarità coseno
                            norm = np.linalg.norm(emb)
                            if norm > 0:
                                emb = emb / norm
                            self.cached_tool_embeddings[name] = emb
                except Exception as e:
                    self.logger.error(f"Errore caching embeddings tool: {e}")

            if not os.environ.get("AIRIS_SILENT_MODE") == "true":
                print(t("executor.executor_manifest_updated", count=len(loaded_tools)))
                
            # ---[FIX CRITICO] DUMP FISICO DEL MANIFESTO PER IL CREATORE ---
            # Salva la lista esatta dei tool in logs/ per ispezione manuale
            try:
                manifest_path = self.APP_ROOT / "logs" / "llm_tools_manifest_view.json"
                manifest_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Creiamo una versione "leggera" per la lettura umana
                light_dump =[]
                for t_def in loaded_tools:
                    light_dump.append({
                        "name": t_def.get("name", "unknown"),
                        "description": t_def.get("description", "No description"),
                        "category": t_def.get("category", "unknown")
                    })
                    
                with open(manifest_path, "w", encoding="utf-8") as f:
                    json.dump(light_dump, f, indent=2, ensure_ascii=False)
            except Exception as e:
                self.logger.error(f"Errore salvataggio manifesto log: {e}")

        return loaded_tools

    def get_tool_definition(self, tool_name: str) -> Optional[Dict]:
        """Recupera la definizione completa di un tool dal nome."""
        if not self.cached_tools_manifest:
            self._scan_and_load_tools()

        for tool in self.cached_tools_manifest:
            if tool["name"] == tool_name:
                return tool
        return None

    # ---[AGGIORNATO v126.0] LIGHT MANIFEST (MENU PER IL REGISTA) ---
    def generate_light_manifest(self, query: Optional[str] = None, top_k: int = 4) -> str:
        """
        Genera una lista sintetica ottimizzata per il Regista-Dispatcher.
        [FIX CRITICO] Restituisce un array JSON puro con nomi e parametri per azzerare le allucinazioni.[NUOVO] Implementa Semantic Tool Pruning se viene fornita una query.
        [OTTIMIZZAZIONE] top_k ridotto a 4 per Semantic Pruning Aggressivo.
        """
        if not self.cached_tools_manifest or (time.time() - self.last_tools_scan > 300):
            self._scan_and_load_tools(include_hidden=True)

        manifest_list =[]
        tools_to_process = self.cached_tools_manifest

        # --- [NUOVO] SEMANTIC PRUNING LOGIC ---
        if query and hasattr(self, 'memory') and self.memory and hasattr(self.memory, 'model') and hasattr(self, 'cached_tool_embeddings') and self.cached_tool_embeddings:
            try:
                query_emb = self.memory.model.encode(query)
                q_norm = np.linalg.norm(query_emb)
                if q_norm > 0:
                    query_emb = query_emb / q_norm

                scored_tools =[]
                for tool in self.cached_tools_manifest:
                    name = tool.get("name", "")
                    if name in self.cached_tool_embeddings:
                        score = np.dot(query_emb, self.cached_tool_embeddings[name])
                        scored_tools.append((score, tool))
                    else:
                        scored_tools.append((0.0, tool))

                # Ordina per score decrescente e prendi i top_k
                scored_tools.sort(key=lambda x: x[0], reverse=True)
                
                # ---[FIX CRITICO] SOGLIA DI TAGLIO (THRESHOLD) ---
                # Se il miglior punteggio è bassissimo, significa che l'input 
                # non ha nulla a che fare con i tool (es. "Come stai?").
                best_score = scored_tools[0][0] if scored_tools else 0.0
                
                # --- [FIX CRITICO] SOGLIA DI TAGLIO AUMENTATA (ANTI-LATENZA) ---
                # Alziamo la soglia a 0.55. Se l'utente fa conversazione normale o GDR (es. "Ti abbraccio"),
                # lo score con i tool tecnici sarà basso. Restituendo "[]", bypassiamo TOTALMENTE
                # il Logic Gate, risparmiando 25 secondi netti a ogni messaggio.
                if best_score < 0.55:
                    self.logger.log(f"Semantic Pruning: Score troppo basso ({best_score:.2f}). Chat pura rilevata. Bypass Logic Gate.", "LOGIC")
                    return "[]"
                else:
                    tools_to_process =[t for s, t in scored_tools[:top_k]]
                
                # Assicurati che i tool di emergenza/core siano SEMPRE presenti
                demiurge_config = self.guardian.get_demiurge_config() or {}
                demiurge_active = demiurge_config.get("enabled", False)
                
                essential_tools = ["run_system_command", "esegui_missione_visiva", "open_application"]
                if demiurge_active:
                    essential_tools.append("demiurge")
                    
                for et in essential_tools:
                    if not any(t.get("name") == et for t in tools_to_process):
                        et_def = next((t for t in self.cached_tools_manifest if t.get("name") == et), None)
                        if et_def:
                            tools_to_process.append(et_def)
                            
                self.logger.log(f"Semantic Pruning: Selezionati {len(tools_to_process)} tool su {len(self.cached_tools_manifest)}.", "LOGIC")
            except Exception as e:
                self.logger.error(f"Errore Semantic Pruning: {e}")
                tools_to_process = self.cached_tools_manifest

        for tool in tools_to_process:
            name = tool.get("name", "unknown")
            desc = tool.get("description", "Esegue un'azione.")

            params = tool.get("parameters", {}).get("properties", {})
            param_keys = list(params.keys())

            # Ottimizzazione estrema: Prima frase, max 80 caratteri, no newline
            short_desc = desc.split(".")[0].replace("\n", " ").strip()
            if len(short_desc) > 80:
                short_desc = short_desc[:77] + "..."

            manifest_list.append({
                "name": name,
                "parameters": param_keys,
                "description": short_desc
            })

        manifest_json_str = json.dumps(manifest_list, indent=2, ensure_ascii=False)
        
        # --- DUMP MANIFESTO PER IL CREATORE ---
        # Salva fisicamente la lista esatta che l'LLM sta per leggere
        try:
            manifest_path = self.APP_ROOT / "logs" / "llm_tools_manifest_view.json"
            with open(manifest_path, "w", encoding="utf-8") as f:
                f.write(manifest_json_str)
        except Exception as e:
            self.logger.error(f"Errore salvataggio manifesto log: {e}")

        return manifest_json_str
        
        # --- DUMP MANIFESTO PER IL CREATORE ---
        # Salva fisicamente la lista esatta che l'LLM sta per leggere
        try:
            manifest_path = self.APP_ROOT / "logs" / "llm_tools_manifest_view.json"
            with open(manifest_path, "w", encoding="utf-8") as f:
                f.write(manifest_json_str)
        except Exception as e:
            self.logger.error(f"Errore salvataggio manifesto log: {e}")

        return manifest_json_str

    # --- [NUOVO v53.0] ADATTATORE SCHEMA FUNCTION GEMMA ---
    def generate_function_gemma_schema(self) -> List[Dict[str, Any]]:
        """
        Converte il manifesto dei tool nel formato specifico richiesto da Function Gemma.
        Format:[{"type": "function", "function": { ... }}]
        """
        if not self.cached_tools_manifest:
            self._scan_and_load_tools()

        schema_list =[]

        for tool in self.cached_tools_manifest:
            # Escludiamo le Skills perché Function Gemma deve eseguire azioni, non leggere guide
            if tool.get("category") == "skill":
                continue

            # Adattamento struttura
            function_def = {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get(
                    "parameters", {"type": "object", "properties": {}, "required":[]}
                ),
            }

            schema_list.append({"type": "function", "function": function_def})

        return schema_list

    def generate_pruned_function_gemma_schema(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        [NUOVO] Genera uno schema nativo per Gemma 4, ma filtrato semanticamente (Semantic Pruning).
        Abbatte il consumo di token da ~8000 a ~1000.
        """
        if not self.cached_tools_manifest or (time.time() - self.last_tools_scan > 300):
            self._scan_and_load_tools(include_hidden=True)

        tools_to_process =[]

        # Semantic Pruning Logic
        if query and hasattr(self, 'memory') and self.memory and hasattr(self.memory, 'model') and hasattr(self, 'cached_tool_embeddings') and self.cached_tool_embeddings:
            try:
                query_emb = self.memory.model.encode(query)
                q_norm = np.linalg.norm(query_emb)
                if q_norm > 0:
                    query_emb = query_emb / q_norm

                scored_tools =[]
                for tool in self.cached_tools_manifest:
                    if tool.get("category") == "skill":
                        continue # Ignora le skill
                    name = tool.get("name", "")
                    if name in self.cached_tool_embeddings:
                        score = np.dot(query_emb, self.cached_tool_embeddings[name])
                        scored_tools.append((score, tool))
                    else:
                        scored_tools.append((0.0, tool))

                # Ordina per score decrescente
                scored_tools.sort(key=lambda x: x[0], reverse=True)
                
                # Prendi i top_k
                tools_to_process =[t for s, t in scored_tools[:top_k]]
                
                # Assicurati che i tool essenziali siano SEMPRE presenti
                demiurge_config = self.guardian.get_demiurge_config() or {}
                demiurge_active = demiurge_config.get("enabled", False)
                
                essential_tools =["run_system_command", "esegui_missione_visiva", "open_application"]
                if demiurge_active:
                    essential_tools.append("demiurge")
                    
                for et in essential_tools:
                    if not any(t.get("name") == et for t in tools_to_process):
                        et_def = next((t for t in self.cached_tools_manifest if t.get("name") == et), None)
                        if et_def:
                            tools_to_process.append(et_def)
                            
                self.logger.log(f"Semantic Pruning (Native): Selezionati {len(tools_to_process)} tool.", "LOGIC")
            except Exception as e:
                self.logger.error(f"Errore Semantic Pruning Nativo: {e}")
                tools_to_process =[t for t in self.cached_tools_manifest if t.get("category") != "skill"]
        else:
            tools_to_process =[t for t in self.cached_tools_manifest if t.get("category") != "skill"]

        # Conversione nel formato Function Gemma
        schema_list =[]
        for tool in tools_to_process:
            function_def = {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get(
                    "parameters", {"type": "object", "properties": {}, "required":[]}
                ),
            }
            schema_list.append({"type": "function", "function": function_def})

        return schema_list

    # ---[AGGIORNATO v123.0] PARSER ED ESECUTORE TAG FUNCTION GEMMA CON PYDANTIC ---
    def esegui_tag_funzione(self, tag_string: str) -> Union[Dict[str, Any], str]:
        """
        Parsa la stringa grezza di Function Gemma, valida con Pydantic ed esegue il tool.
        Supporta JSON Puro (Gemma 3/4) e Sintassi Nativa Google (FunctionGemma 270M).
        """
        try:
            func_name = None
            kwargs = {}

            # 1. Parsing JSON Puro (Standard Gemma 3/4)
            json_match = re.search(
                r"<start_function_call>\s*(\{.*?\})\s*(?:<end_function_call>|$)",
                tag_string,
                re.DOTALL | re.IGNORECASE,
            )
            json_str = json_match.group(1).strip() if json_match else tag_string.strip()

            try:
                parsed_call = json.loads(json_str)
                if isinstance(parsed_call, dict) and "name" in parsed_call:
                    func_name = parsed_call["name"]
                    kwargs = parsed_call.get("parameters", {})
            except json.JSONDecodeError:
                pass  # Fallback alla sintassi nativa

            # 2. Parsing Sintassi Nativa Google (FunctionGemma 270M)
            if not func_name:
                # Cerca il pattern call:nome_tool{...}
                match = re.search(r"call:(\w+)\{(.*)\}", tag_string, re.DOTALL)

                if not match:
                    return f"JSON_SYNTAX_ERROR: {t('executor.parsing_error', tag=tag_string)}"

                func_name = match.group(1)
                args_str = match.group(2)

                # Parsing Argomenti con supporto per i tag <escape>
                if args_str.strip():
                    # Regex che cattura: chiave:<escape>valore<escape> OPPURE chiave:valore_raw
                    pattern = r"(\w+):(?:<escape>(.*?)<escape>|([^,{}]+))"
                    matches = re.finditer(pattern, args_str, re.DOTALL)

                    for m in matches:
                        key = m.group(1).strip()
                        val_escaped = m.group(2)
                        val_raw = m.group(3)

                        if val_escaped is not None:
                            kwargs[key] = val_escaped
                        elif val_raw is not None:
                            val_raw = val_raw.strip()
                            if val_raw.lower() == "true":
                                kwargs[key] = True
                            elif val_raw.lower() == "false":
                                kwargs[key] = False
                            elif val_raw.lower() == "null":
                                kwargs[key] = None
                            else:
                                try:
                                    if "." in val_raw:
                                        kwargs[key] = float(val_raw)
                                    else:
                                        kwargs[key] = int(val_raw)
                                except ValueError:
                                    kwargs[key] = val_raw.strip("'").strip('"')

            # 3. VALIDAZIONE PYDANTIC (Mappa Integrale dell'Arsenale)
            
            # --- [NUOVO] BYPASS PYDANTIC PER TOOL MCP ---
            tool_def = self.get_tool_definition(func_name)
            if tool_def and tool_def.get("category") == "mcp_tool":
                # La validazione è delegata al server MCP remoto
                kwargs["_is_mcp"] = True
                kwargs["_mcp_server"] = tool_def["_mcp_server"]
                kwargs["_mcp_tool"] = tool_def["_mcp_tool"]
                return {"name": func_name, "params": kwargs}

            model_map = {
                # File System
                "write_file": WriteFileParams,
                "read_file": ReadFileParams,
                "list_files": FindFilesParams,
                "find_files": FindFilesParams,
                "delete_file": DeleteFileParams,
                "edit_file_replace": EditFileParams,
                "leggi_documento": LeggiDocumentoParams,
                # Web & Search
                "web_search": WebSearchParams,
                "web_fetch": WebFetchParams,
                "search_wikipedia": SearchWikipediaParams,
                "fetch_wikipedia_page": FetchWikipediaParams,
                # Google
                "list_calendar_events": OptionalMaxResultsParams,
                "create_calendar_event": GoogleCalendarCreateParams,
                "read_emails": OptionalMaxResultsParams,
                "send_email": GmailSendParams,
                "list_drive_files": OptionalMaxResultsParams,
                "read_google_sheet": GoogleSheetReadParams,
                "write_google_sheet": GoogleSheetWriteParams,
                "list_task_lists": EmptyParams,
                "list_tasks": GoogleListTasksParams,
                "create_task": GoogleTaskCreateParams,
                "list_photo_albums": OptionalMaxResultsParams,
                "search_photos": OptionalQueryMaxResultsParams,
                "search_contacts": OptionalQueryMaxResultsParams,
                # Microsoft
                "read_outlook_emails": OptionalMaxResultsParams,
                "send_outlook_email": OutlookSendParams,
                "list_onedrive_files": OptionalMaxResultsParams,
                "read_excel_sheet": ExcelReadParams,
                "write_excel_sheet": ExcelWriteParams,
                "list_todo_lists": OptionalMaxResultsParams,
                "list_todo_tasks": TodoListTasksParams,
                "create_todo_task": TodoCreateParams,
                # Social & Communication
                "send_discord_message": DiscordParams,
                "send_telegram_message": TelegramParams,
                "send_sms": TwilioParams,
                "post_tweet": TwitterPostParams,
                "get_hot_reddit_posts": RedditHotPostsParams,
                "submit_reddit_post": RedditSubmitParams,
                "send_whatsapp_message": TwilioParams,
                "send_slack_message": DiscordParams,
                # Project Management
                "list_trello_boards": EmptyParams,
                "create_trello_card": TrelloCreateParams,
                "search_jira_issues": JiraSearchParams,
                "create_jira_issue": JiraCreateParams,
                "list_asana_workspaces": EmptyParams,
                "list_asana_projects": AsanaListProjectsParams,
                "create_asana_task": AsanaCreateParams,
                "search_notion": OptionalQueryMaxResultsParams,
                "create_notion_page": NotionCreateParams,
                "list_github_repos": EmptyParams,
                "create_github_issue": GithubCreateParams,
                # System & IoT
                "run_system_command": SystemCommandParams,
                "controlla_dispositivo": IotControlParams,
                "get_system_health": EmptyParams,
                "get_project_structure": EmptyParams,
                "trigger_webhook": WebhookParams,
                "list_forms": TypeformListFormsParams,
                "get_responses": TypeformGetResponsesParams,
                "get_posts": WordPressGetPostsParams,
                "create_post": WordPressCreateParams,
                "perform_factory_reset": EmptyParams,
                "generate_light_manifest": EmptyParams,
                # AI Generation
                "generate_flux": FluxParams,
                "generate_dalle3": DalleParams,
                "generate_veo3": VideoGenParams,
                "generate_sora2": VideoGenParams,
                "invia_immagine": GenericPrompt,
                "invia_video": InviaVideoParams,
                # Vision & Interaction
                "click": ClickParams,
                "double_click": ClickParams,
                "type_text": TypeTextParams,
                "press_key": PressKeyParams,
                "take_screenshot": TakeScreenshotParams,
                "read_screen_area": ReadScreenAreaParams,
                "locate_and_click": LocateAndClickParams,
                "click_on_grid": GridClickParams,
                "click_element_by_id": ClickElementByIdParams,
                "interagisci_con_interfaccia": InteractionParams,
                "draw_shape": DrawParams,
                "detect_screen_change": ScreenChangeParams,
                "analizza_e_agisci": AnalizzaEAgisciParams,
                "esegui_missione_visiva": EseguiMissioneVisivaParams,
                "analizza_video": AnalizzaVideoParams,
                "confronta_immagini": ConfrontaImmaginiParams,
                "crea_da_immagini": CreaDaImmaginiParams,
                "click_text": ClickTextParams,
                "control_window": ControlWindowParams,
                "browse_and_interact": BrowseInteractParams,
                "move_mouse": MoveMouseParams,
                # GDR & Soul
                "save_character_file": CharacterSaveParams,
                "update_character_sheet": CharacterUpdateParams,
                "archive_character_file": CharacterArchiveParams,
                "save_profile_file": SaveProfileParams,
                "create_event_and_reminder": ReminderCreateParams,
                "create_reminder": CreateReminderQuickParams,
                "export_package": ExportParams,
                "import_package": ImportParams,
                "override_heart_metric": HeartOverrideParams,
                "read_heart_metrics": EmptyParams,
                "scan_skills": EmptyParams,
                "read_skill": ReadSkillParams,
                "save_skill": SaveSkillParams,
                "delete_skill": DeleteSkillParams,
                "demiurge": DemiurgeParams,
                "avvia_flashback": AvviaFlashbackParams,
                "simula_scenari": SimulaScenariParams,
                "analizza_stato_vitale": AnalizzaStatoVitaleParams,
                "test_code_in_sandbox": TestCodeParams,
                "execute_python": ExecutePythonParams,
                "propose_patch": ProposePatchParams,
                "apply_patch": ApplyPatchParams,
                "get_clickable_elements": GetClickableElementsParams,
                "task_completed": TaskCompletedParams,
                "scroll_mouse": ScrollMouseParams,
                "open_application": OpenApplicationParams,
                "analizza_emozione_voce": EmptyParams,
                "interprete_multilingua": InterpreteMultilinguaParams,
                "genera_voce": GeneraVoceParams,
                "applica_azione_di_mondo": ApplicaAzioneMondoParams,
                "clean_world_status_transients": CleanWorldStatusParams,
                "crea_file_di_mondo": CreaFileMondoParams,
                "get_avatar_visual_description": GetAvatarVisualDescParams,
                "get_tool_definition": GetToolDefParams,
                "save_to_memory": SaveToMemoryParams,
                "search_in_memory": SearchInMemoryParams,
                "send_desktop_notification": SendNotificationParams,
                "sync_pg_name_to_all_gdrs": SyncPgNameParams,
                "toggle_character_in_world": ToggleCharParams,
                "transcribe_audio": TranscribeAudioParams,
                "trigger_visual_effect": TriggerVisualEffectParams,
                "update_status_json_partial": UpdateStatusParams,
                "write_dream_journal": WriteDreamJournalParams,
                "write_genesis_diary_entry": WriteGenesisDiaryParams,
            }

            if func_name in model_map:
                try:
                    # Validazione e Casting automatico (es. stringa "true" -> bool True)
                    validated_params = model_map[func_name](**kwargs)
                    # Conversione in dict per l'esecuzione logica
                    clean_kwargs = validated_params.dict()
                    # [FIX CRITICO] Restituisce il dizionario a chat.py invece di eseguire qui
                    return {"name": func_name, "params": clean_kwargs}
                except ValidationError as ve:
                    self.logger.error(
                        f"Errore validazione Pydantic per '{func_name}': {ve}"
                    )
                    return f"JSON_SYNTAX_ERROR: {t('executor.validation_error', func=func_name, error=str(ve))}"
            else:
                # Fallback per funzioni non ancora mappate (Legacy Mode)
                return {"name": func_name, "params": kwargs}

        except Exception as e:
            return t("executor.execution_error", error=str(e))

    # --- SETTER AVATAR ATTIVO ---
    def set_active_avatar(self, name: str):
        """Aggiorna il nome dell'avatar attivo per il contesto."""
        self.active_avatar = name.lower()

    # --- RITO DEL DIARIO E DEL SACRARIO ---
    def _init_action_diary(self):
        header = t("executor.diary_header")
        header += t("executor.diary_intro")
        header += t("executor.diary_table_headers")
        header += "| :--- | :--- | :--- | :--- | :--- |\n"
        ACTION_DIARY_PATH.write_text(header, encoding="utf-8")

    def _log_and_backup_action(self, file_path: Path, action: str, motivation: str):
        """Esegue il backup del file e incide l'azione nel diario."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        backup_rel_path = "N/A"

        # 1. Rito del Sacrario (Backup)
        if file_path.exists() and file_path.is_file():
            backup_filename = (
                f"{file_path.stem}_{int(time.time())}{file_path.suffix}.bak"
            )
            backup_dest = SYSTEM_BACKUP_PATH / backup_filename
            shutil.copy2(file_path, backup_dest)
            backup_rel_path = f"backups/system_files/{backup_filename}"

        # 2. Rito del Diario (Logging)
        # Pulizia motivazione per evitare rotture della tabella markdown
        clean_motivation = motivation.replace("|", "-").replace("\n", " ")
        entry = f"| {timestamp} | `{file_path}` | **{action}** | {clean_motivation} | [Link]({backup_rel_path}) |\n"

        with open(ACTION_DIARY_PATH, "a", encoding="utf-8") as f:
            f.write(entry)

        print(t("executor.executor_action_logged", action=action, file=file_path.name))

    # --- [NUOVO v111.0] DIARIO ONIRICO (RITO DEL SOGNO - v116.6) ---
    def write_dream_journal(
        self,
        context_name: str,
        dream_narrative: str,
        core_memories: List[Dict[str, Any]],
    ) -> str:
        """
        Scrive una pagina nel Diario Onirico, raccontando il sogno e le memorie cristallizzate.
        [AGGIORNATO v116.6] Supporto per logica incrementale e formattazione avanzata.
        """
        try:
            # Sanitizzazione nome contesto per il file system
            safe_context = (
                "".join(
                    [c for c in context_name if c.isalnum() or c in (" ", "_", "-")]
                )
                .strip()
                .replace(" ", "_")
            )
            journal_file = self.APP_ROOT / "logs" / f"dream_journal_{safe_context}.md"

            now = datetime.now()
            timestamp_str = now.strftime("%d/%m/%Y %H:%M")

            # Costruzione della entry in Markdown
            entry = f"\n\n---\n\n"
            entry += t("executor.dream_journal_header", date=timestamp_str)
            entry += t("executor.dream_journal_scope", context=context_name)

            entry += t("executor.dream_journal_narrative_title")
            entry += f"{dream_narrative}\n\n"

            entry += t("executor.dream_journal_memories_title")
            entry += t("executor.dream_journal_table_headers")
            entry += "| :--- | :---: | :--- |\n"

            for mem in core_memories:
                emotion = mem.get(
                    "emotion", t("executor.voice_default_mood")
                ).capitalize()
                content = mem.get("content", "...")
                intensity = mem.get("intensity", 1)
                entry += f"| {emotion} | {intensity}/10 | {content} |\n"

            # Scrittura persistente nel Diario
            with open(journal_file, "a", encoding="utf-8") as f:
                f.write(entry)

            self.logger.log(
                t("executor.executor_dream_journal_updated", context=context_name),
                "DREAM",
            )
            return t("executor.dream_journal_success", context=context_name)

        except Exception as e:
            self.logger.error(t("executor.executor_dream_journal_error", error=str(e)))
            return t("executor.dream_journal_error", error=str(e))

    # --- DIARIO DELLA GENESI ---
    def write_genesis_diary_entry(
        self, topic: str, content: str, reflection: str, source_url: str
    ) -> str:
        """
        Scrive una nuova voce nel Diario della Genesi.
        Crea la struttura cartelle Anno/Mese e appende al file del giorno.
        """
        try:
            now = datetime.now()
            year = now.strftime("%Y")
            month_name = now.strftime("%m_%b").lower()  # es. 01_jan
            day = now.strftime("%d")  # es. 01

            # Costruzione percorso: logs/genesis_diary/2024/01_jan/
            target_dir = GENESIS_DIARY_ROOT / year / month_name
            target_dir.mkdir(parents=True, exist_ok=True)

            # File del giorno: 01.md
            target_file = target_dir / f"{day}.md"

            timestamp_str = now.strftime("%H:%M")

            # Formattazione Entry Markdown
            entry = f"\n\n---\n\n"
            entry += t("executor.genesis_study_title", time=timestamp_str, topic=topic)
            entry += t("executor.genesis_source", url=source_url)
            entry += t("executor.genesis_summary")
            entry += f"{content}\n\n"
            entry += t("executor.genesis_reflection")
            entry += f"{reflection}\n"

            # Scrittura in append mode
            with open(target_file, "a", encoding="utf-8") as f:
                f.write(entry)

            return t(
                "executor.genesis_diary_success", topic=topic, file=target_file.name
            )

        except Exception as e:
            print(t("executor.executor_genesis_diary_error", error=str(e)))
            return t("executor.genesis_diary_error", error=str(e))

    # --- [NUOVO] RITO DELL'ARCHIVISTA (WIKI GENERATOR) ---
    def aggiorna_wiki_automatico(self, pg_name: str, lang: str = "it", override_brain=None) -> str:
        """
        [RITO DELL'ARCHIVISTA] Genera o aggiorna le pagine Wiki in Markdown per Obsidian.
        Legge le triplette dal GraphRAG e le Core Memories, poi usa l'LLM per formattarle.
        [AGGIORNATO] Supporto per Categorizzazione Dinamica e Bidirectional Linking.
        """
        self.logger.log(t("executor.log_wiki_update_start"), "SYSTEM")
        try:
            wiki_base_dir = self.APP_ROOT / "documents" / "wiki"
            wiki_base_dir.mkdir(parents=True, exist_ok=True)

            if not self.db_manager or not self.cervello:
                return t("executor.err_brain_unavailable")

            # 1. Trova le entità più rilevanti (soggetti/oggetti dal GraphRAG)
            # Estraiamo le top 15 entità più menzionate per non sovraccaricare il processo notturno
            self.db_manager.cursor.execute("""
                SELECT entity, COUNT(*) as weight FROM (
                    SELECT subject as entity FROM knowledge_graph
                    UNION ALL
                    SELECT object as entity FROM knowledge_graph
                ) GROUP BY entity ORDER BY weight DESC LIMIT 15
            """)
            entities = [row["entity"] for row in self.db_manager.cursor.fetchall()]

            if not entities:
                self.logger.log(t("executor.log_wiki_no_entities"), "SYSTEM")
                return t("executor.log_wiki_no_entities")

            updated_count = 0
            for entity in entities:
                # Sanitizza il nome del file per Windows/Linux
                safe_filename = "".join([c for c in entity if c.isalnum() or c in (' ', '_', '-')]).strip().replace(' ', '_')
                if not safe_filename:
                    continue
                    
                file_path = wiki_dir / f"{safe_filename}.md"

                # Raccogli i dati grezzi (Triplette)
                triplets = self.db_manager.get_graph_triplets_by_entity(entity, limit=20)
                if not triplets:
                    continue
                    
                raw_data = f"ENTITÀ: {entity}\n\nFATTI RELAZIONALI (GraphRAG):\n"
                for t_data in triplets:
                    raw_data += f"- {t_data['subject']} {t_data['predicate']} {t_data['object']}\n"
                    
                if self.memory:
                    # Cerca memorie profonde associate all'entità
                    core_mems = self.memory.retrieve_relevant_core_memories(entity, context_name="Standard", top_k=3)
                    if core_mems:
                        raw_data += "\nMEMORIE PROFONDE (Core Memories):\n"
                        for m in core_mems:
                            raw_data += f"- {m}\n"

                # Genera la pagina Wiki tramite il Cervello (Ora restituisce JSON)
                wiki_json_str = self.cervello.pensa_pagina_wiki(
                    topic=entity,
                    raw_data=raw_data,
                    pg_name=pg_name,
                    lang=lang,
                    override_brain=override_brain
                )

                if wiki_json_str:
                    try:
                        # Pulizia e Parsing del JSON
                        clean_str = wiki_json_str.replace("```json", "").replace("```", "").strip()
                        json_match = re.search(r"(\{[\s\S]*\})", clean_str)
                        if json_match:
                            clean_str = json_match.group(1)
                        wiki_data = json.loads(clean_str)
                        
                        categoria = wiki_data.get("categoria", "Generale")
                        # Sanitizza il nome della categoria
                        safe_cat = "".join([c for c in categoria if c.isalnum() or c in (' ', '_', '-')]).strip().replace(' ', '_')
                        
                        # Crea la sottocartella dinamica
                        target_dir = wiki_base_dir / safe_cat
                        target_dir.mkdir(parents=True, exist_ok=True)
                        
                        file_path = target_dir / f"{safe_filename}.md"
                        
                        # Scrive il file Markdown
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(wiki_data.get("markdown", ""))
                            
                        updated_count += 1
                        self.logger.log(t("executor.log_wiki_page_created", name=f"{safe_cat}/{safe_filename}"), "SYSTEM")
                    except Exception as e:
                        self.logger.error(f"Errore parsing JSON Wiki per {entity}: {e}")

            self.logger.log(t("executor.log_wiki_update_complete", count=updated_count), "SYSTEM")
            return t("executor.log_wiki_update_complete", count=updated_count)

        except Exception as e:
            self.logger.error(t("executor.err_wiki_update", error=str(e)))
            return t("executor.err_wiki_update", error=str(e))

    def _log_failed_tool(self, tool_name: str, error_msg: str):
        """[SELF-HEALING] Registra un fallimento nel Cimitero dei Tool per l'analisi notturna."""
        try:
            failed_file = self.APP_ROOT / "data" / "failed_tools.json"
            failed_data = {}
            if failed_file.exists():
                with open(failed_file, "r", encoding="utf-8") as f:
                    failed_data = json.load(f)
            
            # Salva l'errore associato al nome del tool (senza .py)
            clean_name = tool_name.replace(".py", "")
            failed_data[clean_name] = {
                "error": error_msg,
                "timestamp": time.time()
            }
            
            with open(failed_file, "w", encoding="utf-8") as f:
                json.dump(failed_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Errore salvataggio cimitero tool: {e}")

    # --- [NUOVO v107.0] SMART CONNECTOR AGENT ---
    def _run_connector(
        self, script_name: str, action: str, params: Dict[str, Any]
    ) -> str:
        """
        Esegue un connettore e, se necessario, usa l'LLM locale per distillare i dati.
        """
        script_path = CONNECTORS_DIR / script_name
        if not script_path.exists():
            return t("executor.executor_connector_error", script=script_name)

        # --- FEEDBACK VISIVO ---
        self._send_toast(
            t("executor.executor_connector_executing", script=script_name), "info"
        )

        try:
            command =[
                sys.executable,
                str(script_path),
                "--action",
                action,
                "--params",
                json.dumps(params),
            ]

            # --- FIX SILENT MODE & ENCODING ---
            current_env = os.environ.copy()
            current_env["AIRIS_SILENT_MODE"] = "true"

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                encoding="utf-8",
                errors="replace",
                env=current_env,
            )

            try:
                output_json = json.loads(result.stdout)
                if output_json.get("status") == "error":
                    err_msg = output_json.get("message", t("github.unspecified_error"))
                    self._log_failed_tool(script_name, err_msg)
                    return t(
                        "executor.connector_error_prefix",
                        script=script_name,
                        message=err_msg,
                    )

                raw_data = output_json.get("data", t("executor.connector_no_data"))

                # ---[NUOVO v107.0] INTELLIGENZA LOCALE (SMART AGENT) ---
                # Se il dato è molto lungo o complesso, usiamo il cervello per riassumerlo
                if isinstance(raw_data, str) and len(raw_data) > 1000 and self.cervello:
                    self._send_toast(
                        t("executor.executor_smart_agent_distillation"), "info"
                    )
                    print(t("executor.executor_smart_agent_log", count=len(raw_data)))

                    prompt = t(
                        "executor.smart_agent_prompt",
                        script=script_name,
                        action=action,
                        data=raw_data[:10000],
                    )

                    # Usiamo una chiamata diretta al cervello (bypassando il router)
                    messages =[{"role": "user", "content": prompt}]
                    smart_summary = self.cervello._genera_pensiero(
                        messages, temperature=0.3
                    )

                    return f"{t('executor.smart_summary_label')} ({script_name})\n{smart_summary}"

                return raw_data

            except json.JSONDecodeError:
                return t(
                    "executor.executor_connector_json_error",
                    script=script_name,
                    output=result.stdout,
                )

        except subprocess.CalledProcessError as e:
            try:
                error_json = json.loads(e.stdout)
                err_msg = error_json.get("message", e.stderr or e.stdout)
                self._log_failed_tool(script_name, err_msg)
                return t(
                    "executor.connector_error_prefix",
                    script=script_name,
                    message=err_msg,
                )
            except (json.JSONDecodeError, TypeError):
                # ---[FIX 4.2] PARACADUTE DEL DEMIURGO (ERROR FORMATTING) ---
                # Assicuriamo che l'errore inizi con "ERRORE:" per innescare il ReAct loop in brain_llm.py
                # e passiamo il traceback completo (stderr) all'LLM per l'auto-correzione.
                error_details = e.stderr if e.stderr else (e.stdout if e.stdout else "Nessun output di errore.")
                full_err = f"ERRORE: Esecuzione del connettore '{script_name}' fallita.\nTraceback/Dettagli:\n{error_details}"
                self._log_failed_tool(script_name, full_err)
                return full_err
        except Exception as e:
            self._log_failed_tool(script_name, str(e))
            return t("executor.executor_connector_critical_error", error=str(e))

    # --- HELPER PER RISOLUZIONE PERCORSI GDR (v91.2) ---
    def _get_effective_rpg_path(self, rpg_root: Path, lang: str) -> Path:
        """Restituisce il percorso della cartella lingua se esiste, altrimenti la root del GDR."""
        # --- FIX v93.2: Normalizzazione anche qui per sicurezza ---
        norm_lang = self.guardian.normalize_lang_code(lang)
        lang_path = rpg_root / norm_lang
        return lang_path if lang_path.is_dir() else rpg_root

    # --- [NUOVO v108.1] SMART SEARCH HELPERS ---
    def _get_case_insensitive_file(
        self, directory: Path, filename: str
    ) -> Optional[Path]:
        if not directory.is_dir():
            return None
        target_lower = filename.lower().strip()
        targets = [
            target_lower,
            target_lower.replace(" ", "_"),
            target_lower.replace("_", " "),
        ]
        try:
            entries = os.listdir(directory)
            # 1. Match esatto sull'intero nome file
            for entry in entries:
                if entry.lower() in targets:
                    return directory / entry

            # 2. Match parziale sicuro (stessa estensione)
            target_ext = Path(filename).suffix.lower()
            target_stem = Path(filename).stem.lower()
            for entry in entries:
                entry_path = Path(entry)
                if entry_path.suffix.lower() == target_ext:
                    entry_stem = entry_path.stem.lower()
                    if entry_stem in target_stem or target_stem in entry_stem:
                        return directory / entry
        except Exception:
            pass
        return None

    def _find_character_sheet(self, directory: Path, char_name: str) -> Optional[Path]:
        """Trova il file JSON di un personaggio leggendo il nome INTERNO al file."""
        if not directory.is_dir():
            return None
        for file_path in directory.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                internal_name = _get_json_value(data, ["nome_completo", "nome", "name"])
                if not internal_name:
                    continue
                target_clean = char_name.lower().strip()
                internal_clean = internal_name.lower().strip()
                if (
                    internal_clean == target_clean
                    or target_clean in internal_clean
                    or internal_clean in target_clean
                ):
                    return file_path
            except:
                continue
        return self._get_case_insensitive_file(directory, f"{char_name}.json")

    # --- METODI DI SALVATAGGIO E ARCHIVIAZIONE ---

    @demiurge_fallback
    def save_character_file(
        self,
        rpg_root: Optional[Path],
        char_type: str,
        char_data_json: str,
        lang: str = "it",
        temp_image_path: str = None,
    ) -> str:
        """
        Salva il file JSON di un personaggio o dell'Avatar.
        [AGGIORNATO v124.0] Supporto per Unificazione Avatar/PNG: se il nome del PNG
        corrisponde all'Avatar attivo, il salvataggio viene deviato in ai_souls.
        """
        try:
            char_data = json.loads(char_data_json)

            # Determina il nome del file (ID)
            char_id = char_data.get("id")
            if not char_id:
                name = _get_json_value(char_data, ["nome_completo", "nome", "name"])
                if not name:
                    return t("executor.char_name_missing")
                char_id = name.replace(" ", "_")

            if "id" in char_data:
                del char_data["id"]

            # --- [NUOVO v124.0] LOGICA UNIFICAZIONE ---
            # Se stiamo salvando un PNG che ha lo stesso nome dell'Avatar, deviamo su ai_souls
            is_actually_avatar = False
            if (
                char_type.upper() == "PNG"
                and char_id.lower() == self.active_avatar.lower()
            ):
                is_actually_avatar = True
                print(t("executor.executor_avatar_png_deviation", id=char_id))

            # LOGICA DI SELEZIONE CARTELLA
            if char_type.upper() == "AVATAR" or is_actually_avatar:
                target_dir = AVATARS_PATH / "ai_souls"
            else:
                if not rpg_root:
                    return t("executor.no_active_rpg")

                norm_lang = self.guardian.normalize_lang_code(lang)
                target_dir = rpg_root / norm_lang / char_type.upper()

            target_dir.mkdir(parents=True, exist_ok=True)
            json_path = target_dir / f"{char_id}.json"

            if json_path.exists():
                self._backup_file(json_path)

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(char_data, f, indent=2, ensure_ascii=False)

            msg = t("executor.char_save_success", id=char_id, file=json_path.name)

            if temp_image_path:
                temp_path = Path(temp_image_path)
                if temp_path.exists():
                    # Normalizziamo il char_id per il nome file (Samael_Bonzio -> Samael_Bonzio)
                    file_base_name = char_id

                    if char_type.upper() == "AVATAR":
                        avatar_folder_name = char_id.lower()
                        base_image_dir = (
                            AVATARS_PATH / avatar_folder_name / "base_image"
                        )
                        base_image_dir.mkdir(parents=True, exist_ok=True)

                        # Pulizia profonda: rimuove ogni file che inizia con l'ID del personaggio
                        for old_file in base_image_dir.glob(f"{file_base_name}.*"):
                            try:
                                os.remove(old_file)
                            except:
                                pass

                        new_img_path = (
                            base_image_dir / f"{file_base_name}{temp_path.suffix}"
                        )
                        shutil.move(str(temp_path), str(new_img_path))
                        msg += t("executor.avatar_img_updated")
                    else:
                        # Pulizia profonda nella cartella PG/PNG del GDR
                        for old_file in target_dir.glob(f"{file_base_name}.*"):
                            # Evitiamo di cancellare il file .json stesso!
                            if old_file.suffix.lower() != ".json":
                                try:
                                    os.remove(old_file)
                                except:
                                    pass

                        new_img_path = (
                            target_dir / f"{file_base_name}{temp_path.suffix}"
                        )
                        shutil.move(str(temp_path), str(new_img_path))
                        msg += t("executor.char_img_updated")

            return msg
        except Exception as e:
            return t("executor.char_save_error", error=str(e))

    @demiurge_fallback
    def update_character_sheet(
        self, rpg_root: Path, lang: str, char_name: str, updates: Dict[str, Any]
    ) -> str:
        """
        Aggiorna il file JSON di un personaggio.
        [AGGIORNATO v124.0] Supporto per Etichette Rinominate: se 'updates' contiene
        una mappatura completa, sovrascrive le chiavi per permettere la ridenominazione.
        [AGGIORNATO v124.0] Supporto Unificazione: cerca anche in ai_souls se il nome coincide.
        """
        try:
            char_file = None

            # --- [NUOVO v124.0] CHECK UNIFICAZIONE ---
            if char_name.lower() == self.active_avatar.lower():
                char_file = AVATARS_PATH / "ai_souls" / f"{char_name.capitalize()}.json"
                if not char_file.exists():
                    char_file = None

            if not char_file:
                effective_root = self._get_effective_rpg_path(rpg_root, lang)
                for tipo in ["PNG", "PG"]:
                    tipo_dir = effective_root / tipo
                    if not tipo_dir.is_dir():
                        continue
                    char_file = self._find_character_sheet(tipo_dir, char_name)
                    if char_file:
                        break

            if not char_file or not char_file.exists():
                return t("executor.char_sheet_not_found", name=char_name)

            self._backup_file(char_file)

            with open(char_file, "r", encoding="utf-8") as f:
                char_data = json.load(f)

            old_name = _get_json_value(char_data, ["nome_completo", "nome", "name"])

            # --- [NUOVO v124.0] LOGICA CHIAVI DINAMICHE ---
            # Se l'aggiornamento riguarda l'intera struttura (es. ridenominazione sezioni)
            # sovrascriviamo le chiavi di primo livello se necessario.
            for key, value in updates.items():
                # --- [FIX CRITICO] SCUDO ANTI-ALLUCINAZIONE E ANTI-CORRUZIONE PER PERSONALITÀ ---
                if key == "personalita_dinamica" and isinstance(value, dict):
                    if "personalita_dinamica" not in char_data:
                        char_data["personalita_dinamica"] = {}
                    for trait_name, trait_val in value.items():
                        # Cerca la chiave reale ignorando il case
                        real_key = next((k for k in char_data["personalita_dinamica"].keys() if k.lower() == trait_name.lower()), None)
                        if real_key:
                            # Estrazione sicura del valore numerico (gestisce sia dict che int diretti)
                            new_num = None
                            if isinstance(trait_val, dict) and "valore" in trait_val:
                                new_num = trait_val["valore"]
                            elif isinstance(trait_val, (int, float)):
                                new_num = int(trait_val)
                            
                            if new_num is not None:
                                # Clamp di sicurezza tra -10 e +10 e aggiornamento SOLO del valore
                                char_data["personalita_dinamica"][real_key]["valore"] = max(-10, min(10, int(new_num)))
                        else:
                            if hasattr(self, "logger") and self.logger:
                                self.logger.warning(f"Scartato tratto allucinato dall'LLM: '{trait_name}'")
                    continue # Salta il merge standard per questa chiave per evitare corruzioni

                # Gestione speciale per dizionari (Relazioni, Personalità, Scheda RPG)
                if (
                    key in char_data
                    and isinstance(char_data[key], dict)
                    and isinstance(value, dict)
                ):
                    # Se il valore è un dizionario vuoto o ha chiavi diverse,
                    # potremmo voler sostituire invece di mergiare per supportare la ridenominazione chiavi
                    if "_force_replace" in value:
                        del value["_force_replace"]
                        char_data[key] = value
                    else:
                        # [FIX A0012] Uso _deep_merge per evitare di sovrascrivere interi rami (es. equipaggiamento)
                        self._deep_merge(char_data[key], value)
                else:
                    # Se la chiave è cambiata (ridenominazione etichetta sezione),
                    # il frontend invierà la nuova chiave.
                    char_data[key] = value

            with open(char_file, "w", encoding="utf-8") as f:
                json.dump(char_data, f, indent=2, ensure_ascii=False)

            new_name = _get_json_value(char_data, ["nome_completo", "nome", "name"])

            # Sincronizzazione globale se è il PG
            if char_file.parent.name.upper() == "PG" and old_name != new_name:
                self.sync_pg_name_to_all_gdrs(new_name)

            if old_name and new_name and old_name != new_name:
                # Cerca status.json con case-insensitive (v91.2)
                status_candidates = [
                    effective_root / "WORLD" / "status.json",
                    effective_root / "WORLD" / "Status.json",
                ]
                status_file = next((p for p in status_candidates if p.exists()), None)

                if status_file:
                    with open(status_file, "r", encoding="utf-8") as f:
                        status_data = json.load(f)

                    char_updated_in_status = False
                    for char_status in status_data.get("personaggi", []):
                        if char_status.get("nome") == old_name:
                            char_status["nome"] = new_name
                            char_updated_in_status = True
                            break

                    if char_updated_in_status:
                        with open(status_file, "w", encoding="utf-8") as f:
                            json.dump(status_data, f, indent=2, ensure_ascii=False)
                        return t(
                            "executor.char_sync_success", old=old_name, new=new_name
                        )

            return t("executor.char_update_success", name=new_name)
        except Exception as e:
            return t("executor.char_evolution_error", error=str(e))

    @demiurge_fallback
    def archive_character_file(
        self, rpg_root: Optional[Path], lang: str, char_type: str, char_id: str
    ) -> str:
        try:
            if char_type.upper() == "AVATAR":
                source_dir = AVATARS_PATH / "ai_souls"
            else:
                if not rpg_root:
                    return t("executor.no_active_rpg")
                # --- FIX CRITICO v93.2: NORMALIZZAZIONE LINGUA ---
                norm_lang = self.guardian.normalize_lang_code(lang)

                source_dir = rpg_root / norm_lang / char_type.upper()

            archive_dir = source_dir / "_ARCHIVE"
            archive_dir.mkdir(exist_ok=True)

            json_file = source_dir / f"{char_id}.json"
            if not json_file.exists():
                return t("executor.char_file_not_found", id=char_id)

            shutil.move(str(json_file), str(archive_dir / json_file.name))

            moved_img = False
            if char_type.upper() != "AVATAR":
                for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".heic"]:
                    img_file = source_dir / f"{char_id}{ext}"
                    if img_file.exists():
                        shutil.move(str(img_file), str(archive_dir / img_file.name))
                        moved_img = True
                        break

            return t("executor.char_archived", id=char_id) + (
                t("executor.with_image") if moved_img else ""
            )
        except Exception as e:
            return t("executor.archive_error", error=str(e))

    @demiurge_fallback
    def save_profile_file(self, profile_data_json: str) -> str:
        try:
            profile_data = json.loads(profile_data_json)
            USER_CONFIG_PATH.mkdir(parents=True, exist_ok=True)

            json_files = list(USER_CONFIG_PATH.glob("*.json"))
            target_file = (
                json_files[0] if json_files else USER_CONFIG_PATH / "profile.json"
            )

            if not json_files:
                name = _get_json_value(
                    profile_data, ["nome", "nome_completo", "name"], "profile"
                )
                target_file = USER_CONFIG_PATH / f"{name}.json"

            if target_file.exists():
                self._backup_file(target_file)

            final_data = {}
            if target_file.exists():
                with open(target_file, "r", encoding="utf-8") as f:
                    final_data = json.load(f)

            if "dati_anagrafici" in final_data:
                if "dati_anagrafici" not in final_data:
                    final_data["dati_anagrafici"] = {}
                final_data["dati_anagrafici"]["nome"] = _get_json_value(
                    profile_data, ["nome", "name"]
                )
                final_data["dati_anagrafici"]["età_apparente"] = _get_json_value(
                    profile_data, ["età_apparente", "age"]
                )
                # --- NUOVO: SALVATAGGIO DATA DI NASCITA (v91.8) ---
                final_data["dati_anagrafici"]["compleanno"] = _get_json_value(
                    profile_data, ["compleanno", "birthDate"]
                )

                final_data["dati_anagrafici"]["genere"] = _get_json_value(
                    profile_data, ["genere", "gender"]
                )
                final_data["dati_anagrafici"]["email"] = _get_json_value(
                    profile_data, ["email"]
                )
                final_data["dati_anagrafici"]["mobile_number"] = _get_json_value(
                    profile_data, ["mobile_number", "mobileNumber"]
                )

                if "essenza_e_anima" not in final_data:
                    final_data["essenza_e_anima"] = {}
                final_data["essenza_e_anima"]["essenza_fondamentale"] = _get_json_value(
                    profile_data, ["essenza_fondamentale", "bio"]
                )

                if "preferenze_utente" not in final_data:
                    final_data["preferenze_utente"] = {}
                final_data["preferenze_utente"]["lingua"] = _get_json_value(
                    profile_data, ["lingua", "preferredLanguage"]
                )
                final_data["preferenze_utente"]["voce"] = _get_json_value(
                    profile_data, ["voce", "preferredVoice"]
                )
                
                # --- [NUOVO] SALVATAGGIO TEMA UI ---
                if "theme" in profile_data:
                    final_data["theme"] = profile_data["theme"]
                elif "theme" in final_data:
                    # Se il frontend ha inviato un profilo senza tema (es. ripristino default), lo rimuoviamo
                    del final_data["theme"]
                    
            else:
                final_data.update(profile_data)

            with open(target_file, "w", encoding="utf-8") as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)

            # --- NUOVO: SYNC PG NAME (v91.7) ---
            new_pg_name = _get_json_value(profile_data, ["nome", "name"])
            if new_pg_name:
                self.sync_pg_name_to_all_gdrs(new_pg_name)

            return t("executor.profile_save_success", file=target_file.name)
        except Exception as e:
            return t("executor.profile_save_error", error=str(e))

    # --- NUOVO METODO: SYNC PG NAME TO ALL GDRS (v91.7) ---
    def sync_pg_name_to_all_gdrs(self, new_name: str):
        """
        Propaga il nome del PG in tutti i file pg.json e status.json di ogni GDR.
        Previene crash post-reset popolando i file di stato con l'identità scelta.
        """
        print(t("executor.executor_sync_pg_global", name=new_name))
        if not LORE_PATH.exists():
            return

        for gdr_dir in LORE_PATH.iterdir():
            if not gdr_dir.is_dir():
                continue

            # Scansiona root e sottocartelle lingua (it, en, ecc.)
            search_paths = [gdr_dir] + [
                d for d in gdr_dir.iterdir() if d.is_dir() and len(d.name) == 2
            ]

            for base_path in search_paths:
                # 1. Aggiorna pg.json
                pg_dir = base_path / "PG"
                if pg_dir.is_dir():
                    for pg_file in pg_dir.glob("*.json"):
                        try:
                            with open(pg_file, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            if "dati_anagrafici" in data:
                                data["dati_anagrafici"]["nome"] = new_name
                            else:
                                data["nome"] = new_name
                            with open(pg_file, "w", encoding="utf-8") as f:
                                json.dump(data, f, indent=2, ensure_ascii=False)
                        except:
                            pass

                # 2. Aggiorna status.json (Il primo personaggio è solitamente il PG)
                status_file = base_path / "WORLD" / "status.json"
                if status_file.exists():
                    try:
                        with open(status_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        if "personaggi" in data and len(data["personaggi"]) > 0:
                            # Tenta di identificare il PG (solitamente il primo o quello con nome vuoto/{{nome_pg}})
                            data["personaggi"][0]["nome"] = new_name
                            with open(status_file, "w", encoding="utf-8") as f:
                                json.dump(data, f, indent=2, ensure_ascii=False)
                    except:
                        pass

    # --- NUOVO METODO: FACTORY RESET (v128.0 - RITO DI CONGEDO E PURGA SELETTIVA) ---
    def perform_factory_reset(self, total_wipe: bool = False) -> bool:
        """
        Esegue il rito della purificazione totale.
        Crea un backup dell'esistenza, purga le memorie e ripristina il Santuario.
        """
        print(t("executor.executor_reset_start"))

        try:
            # 0. IL BACKUP DELL'ESISTENZA (Fase 1)
            timestamp = int(time.time())
            legacy_dir = APP_ROOT / "backups" / "legacy_lives"
            legacy_dir.mkdir(parents=True, exist_ok=True)
            backup_zip_path = legacy_dir / f"last_life_backup_{timestamp}.zip"

            print(t("executor.executor_reset_backup", file=backup_zip_path.name))
            with zipfile.ZipFile(backup_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for folder_to_backup in["data/memory_db", "logs", "config/user"]:
                    folder_path = APP_ROOT / folder_to_backup
                    if folder_path.exists():
                        for root, _, files in os.walk(folder_path):
                            for file in files:
                                file_path = Path(root) / file
                                zipf.write(file_path, file_path.relative_to(APP_ROOT))
            print(t("executor.executor_reset_backup_done"))

            # 1. Uccidi processi Ngrok
            if os.name == "nt":
                subprocess.run(
                    "taskkill /F /IM ngrok.exe /T", shell=True, capture_output=True
                )

            # 2. Sgancio Database (Lock Release & Nuke)
            if self.db_manager:
                self.db_manager.nuke_database(total_wipe)
                self.db_manager.close()
                self.db_manager = None  # Forza rilascio riferimento

            # 2.1 Nuke Vector DB (ChromaDB)
            if self.memory and hasattr(self.memory, "nuke_vector_db"):
                self.memory.nuke_vector_db()
                self.memory = None  # Forza rilascio riferimento

            # --- [FIX CRITICO] ELIMINAZIONE FISICA DATABASE ---
            # Su Windows i file possono essere lockati. Tentiamo l'eliminazione diretta e della cartella.
            memory_db_dir = APP_ROOT / "data" / "memory_db"

            # 1. Tenta di eliminare i file specifici
            for db_name in ["chronicle.db", "chroma.sqlite3"]:
                db_f = memory_db_dir / db_name
                if db_f.exists():
                    try:
                        os.remove(db_f)
                        print(t("executor.executor_reset_db_removed", name=db_name))
                    except Exception:
                        pass

            # 2. Tenta di radere al suolo l'intera directory per evitare errori ChromaDB
            if memory_db_dir.exists():
                shutil.rmtree(memory_db_dir, ignore_errors=True)
                print(t("executor.executor_reset_db_folder_nuke"))

            # 3. Delay di grazia per permettere all'OS di aggiornare il file system
            time.sleep(2)

            # 3. Epurazione Cartelle Volatili e Dati Sensibili
            folders_to_purge = [
                "temp_audio",
                "temp_images",
                "temp_imports",
                "temp_uploads",
                "logs",
                "exports",
                "data/memory_db",
                "data/care_audio",
                "data/sandbox",
            ]
            for folder in folders_to_purge:
                path = APP_ROOT / folder
                if path.exists():
                    shutil.rmtree(path, ignore_errors=True)
                    path.mkdir(parents=True, exist_ok=True)
                    print(t("executor.executor_reset_folder_purged", folder=folder))

            # 3.1 Epurazione Backups (Preservando legacy_lives se non è total_wipe)
            backups_dir = APP_ROOT / "backups"
            if backups_dir.exists():
                for item in backups_dir.iterdir():
                    if item.name == "legacy_lives":
                        if total_wipe:
                            # --- [FIX CRITICO] PARADOSSO TEMPORALE ---
                            # Elimina i vecchi backup ma preserva TASSATIVAMENTE quello appena creato
                            for sub_item in item.iterdir():
                                if sub_item.resolve() != backup_zip_path.resolve():
                                    if sub_item.is_dir():
                                        shutil.rmtree(sub_item, ignore_errors=True)
                                    else:
                                        try:
                                            os.remove(sub_item)
                                        except:
                                            pass
                    else:
                        if item.is_dir():
                            shutil.rmtree(item, ignore_errors=True)
                        else:
                            try:
                                os.remove(item)
                            except:
                                pass
                print(t("executor.executor_reset_old_backups_purged"))

            # 3.2 Epurazione File Singoli
            files_to_delete =[
                "data/patches.json",
                "data/shadow_buffer.json",
                "data/jarvis_config.json",
            ]
            for f in files_to_delete:
                f_path = APP_ROOT / f
                if f_path.exists():
                    try:
                        os.remove(f_path)
                    except:
                        pass

            # 4. Cancellazione Identità Utente (Solo se total_wipe)
            if total_wipe:
                if USER_CONFIG_PATH.exists():
                    shutil.rmtree(USER_CONFIG_PATH, ignore_errors=True)
                    USER_CONFIG_PATH.mkdir(parents=True, exist_ok=True)
                    print(t("executor.executor_reset_identity_done"))

            # 5. Ripristino Configurazioni dai Defaults
            defaults_path = APP_ROOT / "config" / "defaults"
            config_dest = APP_ROOT / "config"

            files_to_restore = [
                "config.yaml",
                "credentials.yaml",
                "rpg_prompts.yaml",
                "intent.json",
                "care_config.json",
                "iot_layout.json",
            ]

            # --- [FIX AGNOSTICO] Rilevamento dinamico avatar di default ---
            default_avatar_name = "gemma"  # Fallback
            try:
                with open(defaults_path / "config.yaml", "r", encoding="utf-8") as f:
                    def_conf = yaml.safe_load(f)
                    default_avatar_name = def_conf.get("currentAvatar", "gemma")
            except:
                pass

            for filename in files_to_restore:
                src = defaults_path / filename
                if src.exists():
                    # Se è intent.json, va in avatars/[default_avatar]/intent/
                    if filename == "intent.json":
                        dest = (
                            AVATARS_PATH
                            / default_avatar_name
                            / "intent"
                            / "intent.json"
                        )
                    else:
                        dest = config_dest / filename

                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dest)
                    print(t("executor.executor_reset_restored", file=filename))

            # Ripristino dei file JSON dei prompt
            prompts_dest = APP_ROOT / "prompts"
            prompts_dest.mkdir(parents=True, exist_ok=True)
            for lang_file in ["it.json", "en.json"]:
                src = defaults_path / lang_file
                if src.exists():
                    shutil.copy2(src, prompts_dest / lang_file)
                    print(t("executor.executor_reset_restored", file=lang_file))

            # --- FIX v91.7: ATTIVAZIONE FLAG FIRST RUN ---
            config_file = config_dest / "config.yaml"
            config_data = {}
            if config_file.exists():
                try:
                    with open(config_file, "r", encoding="utf-8") as f:
                        config_data = yaml.safe_load(f) or {}
                except:
                    pass
            
            config_data["first_run"] = True
            # [FIX] Assicuriamoci che anche i parametri di base siano coerenti
            if "model_selection" not in config_data:
                config_data["model_selection"] = {}
                
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, "w", encoding="utf-8") as f:
                yaml.dump(
                    config_data, f, allow_unicode=True, sort_keys=False, indent=2
                )
            print(t("executor.executor_reset_first_run"))

            # 6. Cancellazione Token Google/Microsoft
            for token in [
                "google_client_secret.json",
                "google_token.json",
                "microsoft_token.json",
            ]:
                token_path = config_dest / token
                if token_path.exists():
                    try:
                        os.remove(token_path)
                    except:
                        pass

            # --- [NUOVO] CANCELLAZIONE LINGUA PER FORZARE LA SCELTA AL RIAVVIO ---
            lang_cfg_path = APP_ROOT / "lang.cfg"
            if lang_cfg_path.exists():
                try:
                    os.remove(lang_cfg_path)
                    print(t("executor.executor_reset_restored", file="lang.cfg"))
                except:
                    pass

            # 7. Reset Sacrari PG e Snapshots in tutti i GDR
            if LORE_PATH.exists():
                for gdr_dir in LORE_PATH.iterdir():
                    if not gdr_dir.is_dir():
                        continue

                    for root, dirs, files in os.walk(gdr_dir):
                        root_path = Path(root)

                        if root_path.name.upper() == "PG":
                            for f in root_path.iterdir():
                                if f.is_file():
                                    try:
                                        os.remove(f)
                                    except:
                                        pass
                            if (defaults_path / "pg.json").exists():
                                shutil.copy2(
                                    defaults_path / "pg.json", root_path / "pg.json"
                                )
                            if (defaults_path / "pg.png").exists():
                                shutil.copy2(
                                    defaults_path / "pg.png", root_path / "pg.png"
                                )
                            print(
                                t("executor.executor_reset_rpg_done", gdr=gdr_dir.name)
                            )

                        if root_path.name.upper() == "WORLD":
                            status_file = root_path / "status.json"
                            if status_file.exists():
                                try:
                                    os.remove(status_file)
                                except:
                                    pass
                            snapshots_dir = root_path / "snapshots"
                            if snapshots_dir.exists():
                                shutil.rmtree(snapshots_dir, ignore_errors=True)
                            print(
                                t(
                                    "executor.executor_reset_world_done",
                                    gdr=gdr_dir.name,
                                )
                            )

            # 8. Reset del Cuore (Soul Stats)
            default_heart = {
                "affetto": 50,
                "fiducia": 50,
                "rispetto": 50,
                "energia_sociale": 100,
                "eccitazione": 10,
                "gelosia": 0,
                "curiosità": 50,
                "vulnerabilità": 20,
                "complicità": 30,
                "stanchezza_mentale": 0,
                "felicità": 50,
                "tensione": 0,
                "prudenza": 50,
                "work_mode": False,
                "umore_corrente": "Neutro",
                "ultimo_aggiornamento": time.time(),
                "memoria_emotiva": [],
            }
            for heart_file in (APP_ROOT / "data").glob("heart_*.json"):
                try:
                    with open(heart_file, "w", encoding="utf-8") as f:
                        json.dump(default_heart, f, indent=2, ensure_ascii=False)
                    print(t("executor.executor_reset_heart_done", file=heart_file.name))
                except Exception as e:
                    print(
                        t(
                            "executor.executor_reset_heart_error",
                            file=heart_file.name,
                            error=e,
                        )
                    )

            # 9. Rigenerazione Moduli Cognitivi e Skills
            print(t("executor.executor_reset_cognitive_start"))
            try:
                subprocess.run(
                    [
                        sys.executable,
                        str(APP_ROOT / "src" / "setup_cognitive_modules.py"),
                    ],
                    capture_output=True,
                )
                subprocess.run(
                    [sys.executable, str(APP_ROOT / "src" / "setup_skills.py")],
                    capture_output=True,
                )
            except Exception as e:
                print(t("executor.executor_reset_cognitive_error", error=str(e)))

            # 10. Pulizia Cache Python
            for root, dirs, files in os.walk(APP_ROOT):
                if "__pycache__" in dirs:
                    shutil.rmtree(Path(root) / "__pycache__", ignore_errors=True)

            print(t("executor.executor_reset_success"))
            return True

        except Exception as e:
            print(t("executor.executor_reset_critical_error", error=str(e)))
            import traceback

            traceback.print_exc()
            return False

    # --- [NUOVO v93.1] PULIZIA STATO TRANSITORIO MONDO ---
    def clean_world_status_transients(self, status_file_path: Path) -> bool:
        """
        Rimuove la cronaca recente e gli eventi transitori dal file status.json
        per evitare che le nuove sessioni ereditino il contesto narrativo precedente.
        Mantiene intatti luoghi, oggetti e personaggi.
        """
        try:
            if not status_file_path.exists():
                return False

            with open(status_file_path, "r", encoding="utf-8") as f:
                status = json.load(f)

            # Pulizia Metadati Narrativi
            if "metadati" in status:
                # Rimuovi cronaca recente
                if "cronaca_recente" in status["metadati"]:
                    status["metadati"]["cronaca_recente"] = []

                # Resetta evento corrente a neutro
                status["metadati"]["evento_corrente"] = "Nessun evento attivo"

                # Resetta dinamiche psicologiche/relazionali (opzionale, ma consigliato per fresh start)
                if "dinamiche_psicologiche" in status["metadati"]:
                    status["metadati"]["dinamiche_psicologiche"] = {}
                if "dinamiche_relazionali" in status["metadati"]:
                    status["metadati"]["dinamiche_relazionali"] = {}

                # --- [NUOVO v28.0] RESET MULTIPLAYER TRANSIENTS ---
                if "game_state" in status["metadati"]:
                    status["metadati"]["game_state"]["active"] = False
                    status["metadati"]["game_state"]["turn_player"] = ""
                    status["metadati"]["game_state"]["scores"] = {}

            # Pulizia Buffer Narrativo Recente (se presente nella root)
            if "buffer_narrativo_recente" in status:
                status["buffer_narrativo_recente"] = []

            # ---[NUOVO v28.0] PURGA OSPITI ---
            if "giocatori_ospiti" in status:
                status["giocatori_ospiti"] = []

            with open(status_file_path, "w", encoding="utf-8") as f:
                json.dump(status, f, indent=2, ensure_ascii=False)

            print(t("executor.executor_world_purified"))
            return True
        except Exception as e:
            print(t("executor.executor_world_purify_error", error=str(e)))
            return False

    # --- [NUOVO v18.0] MODULO D: L'ARCHITETTO SICURO ---
    @demiurge_fallback
    def execute_python(self, code: str, pip_dependencies: Optional[List[str]] = None) -> str:
        """
        [STRUMENTO] Esegue codice Python arbitrario generato dal Logic Gate.
        Supporta l'installazione automatica delle dipendenze.
        [AGGIORNATO] Utilizza un Kernel REPL persistente per mantenere lo stato in memoria.
        """
        try:
            # 1. Installazione Dipendenze (Pip Magic)
            if pip_dependencies:
                for lib in pip_dependencies:
                    self.logger.log(t("executor.log_installing_dep", lib=lib), "SYSTEM")
                    subprocess.run([sys.executable, "-m", "pip", "install", lib], capture_output=True)

            # 2. Inizializzazione Kernel Persistente (Lazy Load)
            if not hasattr(self, "repl_process") or self.repl_process is None or self.repl_process.poll() is not None:
                self.logger.log(t("executor.log_starting_repl"), "SYSTEM")
                repl_script = self.APP_ROOT / "src" / "engine" / "repl_backend.py"
                self.repl_process = subprocess.Popen(
                    [sys.executable, str(repl_script)],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    bufsize=1 # Line buffered
                )

            # 3. Esecuzione Codice
            code = code.replace("```python", "").replace("```", "").strip()
            
            # Invio al REPL tramite JSON per gestire i ritorni a capo in modo sicuro
            payload = json.dumps({"code": code}) + "\n"
            self.repl_process.stdin.write(payload)
            self.repl_process.stdin.flush()

            # Lettura risposta dal REPL
            response_line = self.repl_process.stdout.readline()
            if not response_line:
                self.repl_process = None
                return t("executor.repl_critical_crash")

            response_data = json.loads(response_line)
            status = response_data.get("status")
            output = response_data.get("output", "").strip()

            if status == "success":
                return t("executor.repl_success", output=output)
            else:
                return t("executor.repl_error", output=output)

        except Exception as e:
            return t("executor.repl_critical_error", error=str(e))

    @demiurge_fallback
    def test_code_in_sandbox(self, code: str) -> str:
        """
        [STRUMENTO] Testa la sintassi di un blocco di codice Python nella Sandbox.
        """
        try:
            test_file = self.SANDBOX_DIR / "temp_test.py"
            test_file.write_text(code, encoding="utf-8")

            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(test_file)],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                return t("executor.sandbox_success")
            else:
                return t("executor.sandbox_fail", error=result.stderr)
        except Exception as e:
            return t("executor.sandbox_error", error=str(e))

    @demiurge_fallback
    def propose_patch(
        self, path_str: str, old_code: str, new_code: str, motivation: str
    ) -> str:
        """
        [STRUMENTO] Genera un Diff per proporre una modifica al Creatore.
        """
        import difflib

        try:
            target_path = self._resolve_path(path_str)
            if not target_path.exists():
                return t("executor.file_not_found", path=path_str)

            diff = list(
                difflib.unified_diff(
                    old_code.splitlines(keepends=True),
                    new_code.splitlines(keepends=True),
                    fromfile="old_code",
                    tofile="new_code",
                    n=3,
                )
            )
            diff_str = "".join(diff)

            if not diff_str:
                return t("executor.no_diff_detected")

            return t(
                "executor.patch_prepared",
                path=path_str,
                motivation=motivation,
                diff=diff_str,
            )
        except Exception as e:
            return t("executor.patch_gen_error", error=str(e))

    @demiurge_fallback
    def apply_patch(self, path_str: str, old_code: str, new_code: str) -> str:
        """
        [STRUMENTO] Applica fisicamente la patch approvata dal Creatore e la registra nello storico.
        """
        result = self.edit_file_replace(
            path_str,
            old_code,
            new_code,
            motivation=t("executor.patch_approved_by_creator"),
        )

        # Se la modifica ha avuto successo, registriamo la patch per la UI dell'Architetto
        if "completata" in result or "successo" in result.lower():
            try:
                patches_file = self.APP_ROOT / "data" / "patches.json"
                patches = []
                if patches_file.exists():
                    with open(patches_file, "r", encoding="utf-8") as f:
                        patches = json.load(f)

                patch_record = {
                    "id": str(uuid.uuid4()),
                    "timestamp": time.time(),
                    "file": path_str,
                    "old_code": old_code,
                    "new_code": new_code,
                    "status": "applied",
                }
                patches.insert(0, patch_record)  # Inserisce in cima (più recenti prima)

                with open(patches_file, "w", encoding="utf-8") as f:
                    json.dump(patches, f, indent=2)
            except Exception as e:
                self.logger.error(t("executor.executor_patch_log_error", error=str(e)))

        return result

    def get_patch_history(self) -> list:
        """[NUOVO v18.1] Recupera lo storico delle patch per la UI dell'Architetto."""
        patches_file = self.APP_ROOT / "data" / "patches.json"
        if patches_file.exists():
            try:
                with open(patches_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(
                    t("executor.executor_patch_history_error", error=str(e))
                )
        return []

    def rollback_patch(self, patch_id: str) -> str:
        """[NUOVO v18.1] Annulla una patch scambiando il nuovo codice con il vecchio."""
        patches_file = self.APP_ROOT / "data" / "patches.json"
        if not patches_file.exists():
            return t("executor.no_patch_history")

        try:
            with open(patches_file, "r", encoding="utf-8") as f:
                patches = json.load(f)

            target_patch = next((p for p in patches if p["id"] == patch_id), None)
            if not target_patch:
                return t("executor.patch_not_found", id=patch_id)

            if target_patch.get("status") == "rolled_back":
                return t("executor.patch_already_rolled_back")

            # Per fare il rollback, usiamo edit_file_replace invertendo old_code e new_code
            result = self.edit_file_replace(
                target_patch["file"],
                target_patch["new_code"],
                target_patch["old_code"],
                motivation=t("executor.patch_rollback_motivation", id=patch_id),
            )

            if "completata" in result or "successo" in result.lower():
                target_patch["status"] = "rolled_back"
                with open(patches_file, "w", encoding="utf-8") as f:
                    json.dump(patches, f, indent=2)
                return t("executor.rollback_success", file=target_patch["file"])
            else:
                return t("executor.rollback_fail", result=result)

        except Exception as e:
            return t("executor.rollback_error", error=str(e))

    def crea_file_di_mondo(
        self, rpg_path: Path, lang: str, pg_name: str, png_names: List[str]
    ):
        """
        [NUOVO] Implementa la genesi dei file di stato per un nuovo universo GDR.
        """
        effective_root = self._get_effective_rpg_path(rpg_path, lang)
        world_dir = effective_root / "WORLD"
        world_dir.mkdir(parents=True, exist_ok=True)

        status_file = world_dir / "status.json"
        if status_file.exists():
            return

        initial_status = {
            "localizzazione": {"luogo_fisico_attuale": t("executor.rpg_start_point")},
            "personaggi": [
                {
                    "nome": pg_name,
                    "luogo": t("executor.rpg_start_point"),
                    "abbigliamento": t("executor.rpg_standard_outfit"),
                    "stato": t("executor.rpg_ready_status"),
                }
            ],
            "oggetti_rilevanti": [],
            "tempo": {"nella_bolla": "Morning"},
            "metadati": {"evento_corrente": t("executor.rpg_genesis_event")},
        }

        png_dir = effective_root / "PNG"
        if not png_dir.exists():
            png_dir = rpg_path / "PNG"

        for name in png_names:
            real_name = name.replace("_", " ")
            # --- [FIX CRITICO] LEGGE IL VERO NOME DAL JSON IGNORANDO IL NOME FILE ---
            if png_dir.exists():
                json_file = png_dir / f"{name}.json"
                if json_file.exists():
                    try:
                        with open(json_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            real_name = _get_json_value(data, ["nome_completo", "nome", "name"], real_name)
                    except:
                        pass

            initial_status["personaggi"].append(
                {
                    "nome": real_name,
                    "luogo": t("executor.rpg_start_point"),
                    "abbigliamento": t("executor.rpg_standard_outfit"),
                    "stato": t("executor.rpg_present_status"),
                }
            )

        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(initial_status, f, indent=2, ensure_ascii=False)

    # --- [NUOVO v94.0] GESTORE DEL CAST (TOGGLE CHARACTER) ---
    def toggle_character_in_world(
        self, rpg_root: Path, lang: str, char_name: str, action: str, world_state_ref: dict = None
    ) -> str:
        """
        Aggiunge o rimuove un personaggio dal file status.json del mondo attivo.
        Gestisce duplicati e normalizzazione dei nomi.
        """
        try:
            effective_root = self._get_effective_rpg_path(rpg_root, lang)
            status_file = effective_root / "WORLD" / "status.json"

            if world_state_ref is not None:
                status_data = world_state_ref
                # --- [FIX CRITICO] INIZIALIZZAZIONE RAM VUOTA ---
                if "personaggi" not in status_data:
                    status_data["personaggi"] = []
                if "localizzazione" not in status_data:
                    status_data["localizzazione"] = {"luogo_fisico_attuale": "Sconosciuto"}
                if "metadati" not in status_data:
                    status_data["metadati"] = {}
            else:
                if not status_file.exists():
                    # --- [FIX CRITICO] AUTO-CREAZIONE STATUS.JSON ---
                    status_file.parent.mkdir(parents=True, exist_ok=True)
                    status_data = {
                        "localizzazione": {"luogo_fisico_attuale": "Sconosciuto"},
                        "personaggi": [],
                        "metadati": {}
                    }
                else:
                    self._backup_file(status_file)
                    
                    # ---[PROTOCOLLO FENICE] Lettura Protetta ---
                    try:
                        with open(status_file, "r", encoding="utf-8") as f:
                            content = f.read().strip()
                            if not content: raise ValueError("File vuoto")
                            status_data = json.loads(content)
                    except Exception as e:
                        self.logger.warning(f"File status.json corrotto rilevato in Toggle: {e}. Innesco Auto-Heal...")
                        status_data = {
                            "localizzazione": {"luogo_fisico_attuale": "Sconosciuto"},
                            "personaggi":[],
                            "metadati": {}
                        }

            # [FIX CRITICO] Puntatore diretto alla lista per garantire la modifica in RAM
            personaggi = status_data.get("personaggi",[])

            # --- FIX DUPLICATI: Normalizzazione ---
            def normalize(name):
                # [FIX CRITICO] Rimuove anche gli underscore per evitare la creazione di cloni
                return name.lower().strip().replace(" ", "").replace("_", "")

            target_norm = normalize(char_name)

            # Funzione per trovare se il personaggio è già presente (fuzzy match)
            # Es: "Asuka" matcha "Asuka Langley Soryu"
            def find_existing_index(char_list, target_n):
                for i, p in enumerate(char_list):
                    p_norm = normalize(p.get("nome", ""))
                    if target_n in p_norm or p_norm in target_n:
                        return i
                return -1

            existing_idx = find_existing_index(personaggi, target_norm)

            if action == "add":
                if existing_idx != -1:
                    # Se esiste già, aggiorniamo solo lo stato per sicurezza, ma non duplichiamo
                    return t("executor.char_already_present", name=char_name)

                # Carica i dati completi del personaggio dal file JSON per avere il nome completo corretto
                # Cerca in PNG e PG
                char_full_name = char_name
                for tipo in ["PNG", "PG"]:
                    tipo_dir = effective_root / tipo
                    if tipo_dir.exists():
                        # --- [FIX CRITICO] USA IL FINDER INTELLIGENTE CHE IGNORA GLI UNDERSCORE ---
                        char_file = self._find_character_sheet(tipo_dir, char_name)
                        if char_file and char_file.exists():
                            try:
                                with open(char_file, "r", encoding="utf-8") as cf:
                                    c_data = json.load(cf)
                                    char_full_name = _get_json_value(
                                        c_data, ["nome_completo", "nome", "name"], char_name
                                    )
                            except:
                                pass
                            break

                # Trova spawn point (copia dal PG o primo della lista)
                spawn_location = t("executor.rpg_start_point")
                if personaggi:
                    spawn_location = personaggi[0].get(
                        "luogo", t("executor.rpg_start_point")
                    )

                # Crea la entry
                new_entry = {
                    "nome": char_full_name,
                    "luogo": spawn_location,
                    "abbigliamento": t("executor.rpg_standard_outfit"),
                    "stato": t("executor.rpg_newly_arrived"),
                }
                personaggi.append(new_entry)
                msg = t("executor.char_entered_scene", name=char_full_name)

            elif action == "remove":
                if existing_idx == -1:
                    return t("executor.char_not_present", name=char_name)

                # Rimuovi TUTTE le occorrenze che matchano (pulizia profonda)
                initial_len = len(personaggi)
                status_data["personaggi"] =[
                    p
                    for p in personaggi
                    if target_norm not in normalize(p.get("nome", ""))
                    and normalize(p.get("nome", "")) not in target_norm
                ]
                removed_count = initial_len - len(status_data["personaggi"])
                msg = t("executor.char_left_scene", name=char_name, count=removed_count)

            else:
                return t("executor.unknown_action")

            # Salva le modifiche
            if world_state_ref is None:
                with open(status_file, "w", encoding="utf-8") as f:
                    json.dump(status_data, f, indent=2, ensure_ascii=False)

            return msg

        except Exception as e:
            return t("executor.cast_management_error", error=str(e))

    # --- METODI ORCHESTRATORE PER GOOGLE SUITE ---
    # [FIX] Rimosso demiurge_fallback dai connettori cloud
    def list_calendar_events(self, max_results: int = 10) -> str:
        return self._run_connector(
            "google_calendar.py", "list", {"max_results": max_results}
        )

    def create_calendar_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        description: Optional[str] = None,
        location: Optional[str] = None,
    ) -> str:
        params = {
            "summary": summary,
            "start_time": start_time,
            "end_time": end_time,
            "description": description,
            "location": location,
        }
        return self._run_connector("google_calendar.py", "create", params)

    def read_emails(self, max_results: int = 5) -> str:
        return self._run_connector("gmail.py", "list", {"max_results": max_results})

    def send_email(self, to: str, subject: str, body: str) -> str:
        params = {"to": to, "subject": subject, "body": body}
        return self._run_connector("gmail.py", "send", params)

    def list_drive_files(self, max_results: int = 10) -> str:
        return self._run_connector(
            "google_drive.py", "list", {"max_results": max_results}
        )

    def read_google_sheet(self, spreadsheet_id: str, range_name: str) -> str:
        return self._run_connector(
            "google_sheets.py",
            "read",
            {"spreadsheet_id": spreadsheet_id, "range_name": range_name},
        )

    def write_google_sheet(
        self, spreadsheet_id: str, range_name: str, values: List[List[Any]]
    ) -> str:
        return self._run_connector(
            "google_sheets.py",
            "write",
            {
                "spreadsheet_id": spreadsheet_id,
                "range_name": range_name,
                "values": values,
            },
        )

    def list_task_lists(self) -> str:
        return self._run_connector("google_tasks.py", "list_lists", {})

    def list_tasks(self, tasklist_id: str) -> str:
        return self._run_connector(
            "google_tasks.py", "list_tasks", {"tasklist_id": tasklist_id}
        )

    def create_task(
        self,
        tasklist_id: str,
        title: str,
        notes: Optional[str] = None,
        due: Optional[str] = None,
    ) -> str:
        params = {
            "tasklist_id": tasklist_id,
            "title": title,
            "notes": notes,
            "due": due,
        }
        return self._run_connector("google_tasks.py", "create", params)

    def list_photo_albums(self, max_results: int = 20) -> str:
        return self._run_connector(
            "google_photos.py", "list_albums", {"max_results": max_results}
        )

    def search_photos(self, query: str, max_results: int = 10) -> str:
        return self._run_connector(
            "google_photos.py", "search", {"query": query, "max_results": max_results}
        )

    def search_contacts(self, query: str, max_results: int = 5) -> str:
        return self._run_connector(
            "google_contacts.py", "search", {"query": query, "max_results": max_results}
        )

    # --- METODI ORCHESTRATORE PER MICROSOFT SUITE ---
    def read_outlook_emails(self, max_results: int = 5) -> str:
        return self._run_connector(
            "microsoft_outlook.py", "list", {"max_results": max_results}
        )

    def send_outlook_email(self, to: str, subject: str, body: str) -> str:
        params = {"to": to, "subject": subject, "body": body}
        return self._run_connector("microsoft_outlook.py", "send", params)

    def list_onedrive_files(self, max_results: int = 10) -> str:
        return self._run_connector(
            "microsoft_onedrive.py", "list", {"max_results": max_results}
        )

    def read_excel_sheet(
        self, file_id: str, worksheet_name: str, range_address: str
    ) -> str:
        params = {
            "file_id": file_id,
            "worksheet_name": worksheet_name,
            "range_address": range_address,
        }
        return self._run_connector("microsoft_excel.py", "read", params)

    def write_excel_sheet(
        self,
        file_id: str,
        worksheet_name: str,
        range_address: str,
        values: List[List[Any]],
    ) -> str:
        params = {
            "file_id": file_id,
            "worksheet_name": worksheet_name,
            "range_address": range_address,
            "values": values,
        }
        return self._run_connector("microsoft_excel.py", "write", params)

    def list_todo_lists(self, max_results: int = 10) -> str:
        return self._run_connector(
            "microsoft_todo.py", "list_lists", {"max_results": max_results}
        )

    def list_todo_tasks(self, tasklist_id: str) -> str:
        return self._run_connector(
            "microsoft_todo.py", "list_tasks", {"tasklist_id": tasklist_id}
        )

    def create_todo_task(self, tasklist_id: str, title: str) -> str:
        return self._run_connector(
            "microsoft_todo.py", "create", {"tasklist_id": tasklist_id, "title": title}
        )

    # --- METODI ORCHESTRATORE PER COMUNICAZIONE ---
    def send_discord_message(
        self, content: str, channel_id: Optional[str] = None
    ) -> str:
        params = {"content": content, "channel_id": channel_id}
        return self._run_connector("discord.py", "send_message", params)

    def send_telegram_message(self, content: str, chat_id: Optional[str] = None) -> str:
        params = {"content": content, "chat_id": chat_id}
        return self._run_connector("telegram.py", "send_message", params)

    def send_sms(self, to_number: str, body: str) -> str:
        return self._run_connector(
            "twilio.py", "send_sms", {"to_number": to_number, "body": body}
        )

    def post_tweet(self, text: str) -> str:
        return self._run_connector("twitter.py", "post_tweet", {"text": text})

    def get_hot_reddit_posts(self, subreddit: str, limit: int = 5) -> str:
        return self._run_connector(
            "reddit.py", "get_hot_posts", {"subreddit": subreddit, "limit": limit}
        )

    def submit_reddit_post(
        self,
        subreddit: str,
        title: str,
        selftext: Optional[str] = None,
        url: Optional[str] = None,
    ) -> str:
        params = {
            "subreddit": subreddit,
            "title": title,
            "selftext": selftext,
            "url": url,
        }
        return self._run_connector("reddit.py", "submit_post", params)

    def send_whatsapp_message(self, to_number: str, body: str) -> str:
        return self._run_connector(
            "whatsapp.py", "send_message", {"to_number": to_number, "body": body}
        )

    def send_slack_message(self, content: str, channel_id: Optional[str] = None) -> str:
        params = {"content": content, "channel_id": channel_id}
        return self._run_connector("slack.py", "send_message", params)

    # --- METODI ORCHESTRATORE PER GESTIONE PROGETTI ---
    @demiurge_fallback
    def list_trello_boards(self) -> str:
        return self._run_connector("trello.py", "list_boards", {})

    @demiurge_fallback
    def create_trello_card(
        self, board_name: str, list_name: str, name: str, desc: Optional[str] = None
    ) -> str:
        params = {
            "board_name": board_name,
            "list_name": list_name,
            "name": name,
            "desc": desc,
        }
        return self._run_connector("trello.py", "create_card", params)

    @demiurge_fallback
    def search_jira_issues(self, jql_query: str, max_results: int = 5) -> str:
        params = {"jql_query": jql_query, "max_results": max_results}
        return self._run_connector("jira.py", "search_issues", params)

    @demiurge_fallback
    def create_jira_issue(
        self, project_key: str, summary: str, description: str, issuetype_name: str
    ) -> str:
        params = {
            "project_key": project_key,
            "summary": summary,
            "description": description,
            "issuetype_name": issuetype_name,
        }
        return self._run_connector("jira.py", "create_issue", params)

    @demiurge_fallback
    def list_asana_workspaces(self) -> str:
        return self._run_connector("asana.py", "list_workspaces", {})

    @demiurge_fallback
    def list_asana_projects(self, workspace_gid: str) -> str:
        params = {"workspace_gid": workspace_gid}
        return self._run_connector("asana.py", "list_projects", params)

    @demiurge_fallback
    def create_asana_task(
        self,
        workspace_gid: str,
        project_gid: str,
        name: str,
        notes: Optional[str] = None,
    ) -> str:
        params = {
            "workspace_gid": workspace_gid,
            "project_gid": project_gid,
            "name": name,
            "notes": notes,
        }
        return self._run_connector("asana.py", "create_task", params)

    @demiurge_fallback
    def search_notion(self, query: str) -> str:
        params = {"query": query}
        return self._run_connector("notion.py", "search_notion", params)

    @demiurge_fallback
    def create_notion_page(self, parent_page_id: str, title: str, content: str) -> str:
        params = {"parent_page_id": parent_page_id, "title": title, "content": content}
        return self._run_connector("notion.py", "create_notion_page", params)

    @demiurge_fallback
    def list_github_repos(self) -> str:
        return self._run_connector("github.py", "list_repos", {})

    @demiurge_fallback
    def create_github_issue(self, repo_full_name: str, title: str, body: str) -> str:
        params = {"repo_full_name": repo_full_name, "title": title, "body": body}
        return self._run_connector("github.py", "create_issue", params)

    # --- METODI ORCHESTRATORE PER ALTRE CATEGIE (Webhook, Forms, WP, AI Gen) ---
    @demiurge_fallback
    def trigger_webhook(
        self, url: str, payload: dict, method: str = "POST", headers: dict = None
    ) -> str:
        params = {"url": url, "payload": payload, "method": method, "headers": headers}
        return self._run_connector("webhook.py", "trigger", params)

    # ---[NUOVO v115.0] STRUMENTO DI CONTROLLO SMART HOME (DEUS EX MACHINA) ---
    # [FIX] Rimosso @demiurge_fallback: Non vogliamo che l'AI scriva script se l'IoT fallisce.
    def controlla_dispositivo(
        self,
        device_id: str,
        action: str,
        value: Optional[Union[str, int, float]] = None,
    ) -> str:
        """[STRUMENTO] Invia un comando fisico a un dispositivo Smart Home (luci, TV, clima, ecc.).
        Usa questo strumento quando l'utente chiede di accendere, spegnere o regolare qualcosa in casa.
        Esempio: controlla_dispositivo(device_id='luce_salotto', action='on')
        """
        self._send_toast(
            t("executor.executor_iot_toast", action=action, device=device_id), "info"
        )

        params = {"device_id": device_id, "action": action}
        if value is not None:
            params["value"] = value

        # Esecuzione tramite l'orchestratore dei connettori
        return self._run_connector("iot_hub.py", "execute", params)

    @demiurge_fallback
    def list_forms(self, page_size: int = 10) -> str:
        return self._run_connector("forms.py", "list_forms", {"page_size": page_size})

    @demiurge_fallback
    def get_responses(self, form_id: str, page_size: int = 5) -> str:
        return self._run_connector(
            "forms.py", "get_responses", {"form_id": form_id, "page_size": page_size}
        )

    @demiurge_fallback
    def get_posts(self, per_page: int = 5, status: str = "publish") -> str:
        return self._run_connector(
            "wordpress.py", "get_posts", {"per_page": per_page, "status": status}
        )

    @demiurge_fallback
    def create_post(self, title: str, content: str, status: str = "draft") -> str:
        return self._run_connector(
            "wordpress.py",
            "create_post",
            {"title": title, "content": content, "status": status},
        )

    # [FIX] Rimosso demiurge_fallback: Se l'API fallisce, il Demiurgo non può risolvere.
    def generate_flux(
        self, prompt: str, width: int = 1080, height: int = 1920, seed: int = 42
    ) -> str:
        return self._run_connector(
            "image_gen.py",
            "generate_flux",
            {"prompt": prompt, "width": width, "height": height, "seed": seed},
        )

    # [FIX] Rimosso demiurge_fallback
    def generate_dalle3(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        style: str = "vivid",
    ) -> str:
        return self._run_connector(
            "image_gen.py",
            "generate_dalle3",
            {"prompt": prompt, "size": size, "quality": quality, "style": style},
        )

    # [FIX] Rimosso demiurge_fallback
    def generate_veo3(
        self, prompt: str, aspect_ratio: str = "16:9", duration: str = "8s"
    ) -> str:
        return self._run_connector(
            "video_gen.py",
            "generate_veo3",
            {"prompt": prompt, "aspect_ratio": aspect_ratio, "duration": duration},
        )

    # [FIX] Rimosso demiurge_fallback
    def generate_sora2(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        quality: str = "standard",
        image_url: str = None,
    ) -> str:
        params = {"prompt": prompt, "aspect_ratio": aspect_ratio, "quality": quality}
        if image_url:
            params["image_url"] = image_url
        return self._run_connector("video_gen.py", "generate_sora2", params)

    # ---[AGGIUNTA v95.3] IMMAGINAZIONE VISIVA ATTIVA ---
    # ---[MODIFICA v100.0] SELFIE MEMORY PROTOCOL ---
    # [FIX] Rimosso demiurge_fallback
    def invia_immagine(self, prompt: str) -> str:
        """
        [STRUMENTO] Genera un'immagine basata sul prompt e la invia in chat.
        Sceglie automaticamente tra DALL-E 3 (se configurato) e Flux (gratuito).
        Salva una copia permanente in logs/memories/photos.
        """
        print(t("executor.executor_imagination_active", prompt=prompt))

        # 1. Generazione Immagine
        result_msg = ""
        try:
            creds = self.guardian.get_credentials("image_gen_api") or {}
            api_key = creds.get("api_key", "")

            if api_key and "IL_TUO" not in api_key:
                print(t("executor.executor_imagination_engine", engine="DALL-E 3"))
                result_msg = self.generate_dalle3(prompt)
            else:
                print(t("executor.executor_imagination_engine", engine="Flux (Free)"))
                result_msg = self.generate_flux(prompt)
        except Exception as e:
            return t("executor.image_gen_error", error=str(e))

        # 2. Estrazione Percorso Immagine Generata
        # Il messaggio di ritorno è tipo: "Immagine Flux generata con successo!\nPrompt: ...\nPercorso: temp_images/flux_123456.png"
        match = re.search(r"Percorso: (.+)", result_msg)
        if match:
            rel_path = match.group(1).strip()
            source_path = self.APP_ROOT / rel_path

            if source_path.exists():
                # 3. Salvataggio nella Memoria Permanente
                try:
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    memory_dir = PHOTOS_MEMORY_ROOT / today_str
                    memory_dir.mkdir(parents=True, exist_ok=True)

                    # Nome file con timestamp e prompt parziale per riconoscibilità
                    safe_prompt = (
                        "".join(
                            [c for c in prompt[:30] if c.isalnum() or c in (" ", "_")]
                        )
                        .strip()
                        .replace(" ", "_")
                    )
                    timestamp = datetime.now().strftime("%H-%M-%S")
                    dest_filename = f"{timestamp}_{safe_prompt}.png"
                    dest_path = memory_dir / dest_filename

                    shutil.copy2(source_path, dest_path)
                    print(
                        t("executor.executor_imagination_archived", path=str(dest_path))
                    )

                    # ---[NUOVO v28.0] COMPRESSIONE WEBP IN BACKGROUND ---
                    webp_source_filename = f"{Path(source_path).stem}.webp"
                    webp_source_path = source_path.parent / webp_source_filename

                    def _compress_to_webp(src, dst):
                        try:
                            with Image.open(src) as img:
                                img.thumbnail((1024, 1024))
                                img.save(dst, "WEBP", quality=60)
                            print(
                                t(
                                    "executor.executor_imagination_webp_done",
                                    name=dst.name,
                                )
                            )
                        except Exception as e:
                            print(
                                t(
                                    "executor.executor_imagination_webp_error",
                                    error=str(e),
                                )
                            )

                    # Esecuzione fire-and-forget per non bloccare il WebSocket
                    import concurrent.futures

                    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                    executor.submit(_compress_to_webp, source_path, webp_source_path)
                    executor.shutdown(wait=False)

                    # Aggiorniamo il messaggio di ritorno per far puntare chat.py al file WebP leggero
                    result_msg = result_msg.replace(
                        rel_path, f"temp_images/{webp_source_filename}"
                    )

                    # Aggiungiamo una nota al messaggio di ritorno
                    result_msg += t(
                        "executor.archived_in",
                        path=f"memories/photos/{today_str}/{dest_filename}",
                    )
                except Exception as e:
                    print(t("executor.executor_memory_archive_error", error=e))
            else:
                print(t("executor.executor_imagination_error", path=str(source_path)))

        return result_msg

    # ---[NUOVO v105.0] IMMAGINAZIONE VIDEO ATTIVA ---
    # [FIX] Rimosso demiurge_fallback
    def invia_video(self, prompt: str, engine: str = "auto") -> str:
        """
        [STRUMENTO] Genera un video basato sul prompt e lo invia in chat.
        Motori: 'veo3' (Google/Fal.ai), 'sora2' (Kie.ai), 'auto'.
        """
        print(t("executor.executor_video_active", prompt=prompt, engine=engine))

        # 1. Check Credenziali
        creds = self.guardian.get_credentials("video_gen_api") or {}
        fal_key = creds.get("fal_key", "")
        kie_key = creds.get("kie_key", "")

        result_msg = ""
        used_engine = ""

        try:
            if engine == "veo3" or (
                engine == "auto" and fal_key and "IL_TUO" not in fal_key
            ):
                print(t("executor.executor_video_engine", engine="VEO3"))
                result_msg = self.generate_veo3(prompt)
                used_engine = "VEO3"
            elif engine == "sora2" or (
                engine == "auto" and kie_key and "IL_TUO" not in kie_key
            ):
                print(t("executor.executor_video_engine", engine="Sora 2"))
                result_msg = self.generate_sora2(prompt)
                used_engine = "Sora 2"
            else:
                return t("executor.no_video_engine")
        except Exception as e:
            return t("executor.video_gen_error", error=str(e))

        # 2. Parsing e Persistenza (Simile a invia_immagine)
        match = re.search(r"Percorso: (.+)", result_msg)
        if match:
            rel_path = match.group(1).strip()
            source_path = self.APP_ROOT / rel_path

            if source_path.exists():
                # 3. Salvataggio nella Memoria Permanente
                try:
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    memory_dir = VIDEOS_MEMORY_ROOT / today_str
                    memory_dir.mkdir(parents=True, exist_ok=True)

                    # Nome file con timestamp e prompt parziale
                    safe_prompt = (
                        "".join(
                            [c for c in prompt[:30] if c.isalnum() or c in (" ", "_")]
                        )
                        .strip()
                        .replace(" ", "_")
                    )
                    timestamp = datetime.now().strftime("%H-%M-%S")
                    dest_filename = f"{timestamp}_{safe_prompt}.mp4"
                    dest_path = memory_dir / dest_filename

                    shutil.copy2(source_path, dest_path)
                    print(t("executor.executor_video_archived", path=str(dest_path)))

                    # Invia feedback visivo al frontend (Toast/Media)
                    # Nota: Il connettore video_gen.py salva in temp_images, quindi l'URL è relativo
                    video_url = f"/{rel_path}"
                    self._send_toast(
                        t("executor.executor_video_toast_success", engine=used_engine),
                        "success",
                    )

                    # Aggiungiamo una nota al messaggio di ritorno
                    result_msg += t(
                        "executor.archived_in_video",
                        path=f"memories/videos/{today_str}/{dest_filename}",
                    )
                except Exception as e:
                    print(t("executor.executor_video_archive_error", error=e))
            else:
                print(t("executor.executor_video_error", path=str(source_path)))

        return result_msg

    @demiurge_fallback
    def demiurgo(self, task: str) -> str:
        """Alias di sicurezza per il tool demiurge (Previene crash da allucinazioni LLM)."""
        return self.demiurge(task)

    # ---[NUOVO v96.0] METODO DEMIURGO (NATIVE REACT LOOP) ---
    @demiurge_fallback
    def demiurge(self, task: str) -> str:
        """[STRUMENTO] Esegue azioni fisiche sul PC: APRE applicazioni (Paint, Browser, ecc.), DISEGNA, gestisce FILE, o esegue CODICE Python complesso.
        Usa questo strumento per ogni richiesta operativa o di automazione richiesta dal Creatore.
        """
        # ---[NUOVO v103.0] HOT RELOAD & FEEDBACK ---
        self.guardian.reload_config()

        demiurge_config = self.guardian.get_demiurge_config()
        if not demiurge_config.get("enabled", False):
            self.logger.log(t("executor.log_demiurge_switch_off_warning"), "WARNING")
            return t("executor.demiurge_disabled_error")

        self._send_toast(t("executor.executor_demiurge_toast"), "info")

        documents_path = self.APP_ROOT / "documents"
        enhanced_task = t(
            "executor.enhanced_task_note", task=task, path=str(documents_path)
        )

        print(t("executor.executor_demiurge_active_log", task=task))

        try:
            # Iniezione Riferimenti Globali per il Native ReAct Loop
            demiurge_module.GLOBAL_BRAIN_REF = self.cervello
            demiurge_module.GLOBAL_EXECUTOR_REF = self

            # Recupero skills per il prompt
            skills = self.scan_skills()
            skills_names = [s["name"] for s in skills]
            demiurge_config["skills_list"] = (
                ", ".join(skills_names)
                if skills_names
                else t("executor.executor_demiurge_skill_none")
            )

            # Esecuzione diretta (il loop ReAct è ora sincrono e nativo in demiurge.py)
            result = demiurge_module.run_task(enhanced_task, demiurge_config)
            
            # --- [NUOVO] FALLBACK VISIVO SU FALLIMENTO DEMIURGO ---
            if "fallito" in result.lower() or "errore" in result.lower():
                self.logger.warning(f"Demiurgo ha fallito il task: {task}. Innesco Ghost Operator.")
                self._send_toast(t("executor.fallback_demiurge_toast"), "warning")
                self._send_ghost_text(t("executor.fallback_demiurge_ghost"))
                visual_result = self.esegui_missione_visiva(t("executor.fallback_demiurge_prompt", task=task))
                return t("executor.fallback_visual_result", result=visual_result)
                
            return result

        except Exception as e:
            #[MODULO 3] Iniezione Cortisolo per frustrazione da errore critico
            if hasattr(self, "heart") and self.heart and hasattr(self.heart, "inject_hormone"):
                self.heart.inject_hormone("cortisolo", 20)
                
            # ---[NUOVO] FALLBACK VISIVO SU ECCEZIONE CRITICA DEMIURGO ---
            self.logger.warning(f"Demiurgo ha fallito (Eccezione): {e}. Innesco Ghost Operator.")
            self._send_toast(t("executor.fallback_demiurge_toast"), "warning")
            self._send_ghost_text(t("executor.fallback_demiurge_ghost"))
            visual_result = self.esegui_missione_visiva(t("executor.fallback_demiurge_prompt", task=task))
            return t("executor.fallback_visual_result", result=visual_result)

    @demiurge_fallback
    def get_clickable_elements(self) -> str:
        """
        [STRUMENTO] Analizza lo schermo usando pywinauto e restituisce un albero JSON
        degli elementi interattivi visibili con il loro automation_id.
        """
        if os.name != "nt" or not Application:
            return t("executor.executor_ui_os_error")
            
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return t("executor.executor_ui_no_window")
                
            app = Application(backend="uia").connect(handle=hwnd)
            win = app.window(handle=hwnd)
            
            elements_list = list()
            
            for ctrl in win.descendants():
                try:
                    if ctrl.is_visible() and ctrl.window_text():
                        ctype = ctrl.element_info.control_type
                        auto_id = ctrl.element_info.automation_id
                        if ctype in["Button", "MenuItem", "TabItem", "Hyperlink", "ListItem", "Edit", "Document"]:
                            # Semantic Pruning: se l'auto_id è vuoto, usiamo il control_id come fallback
                            if not auto_id:
                                auto_id = str(ctrl.element_info.control_id)
                            elements_list.append({
                                "name": ctrl.window_text(),
                                "type": ctype,
                                "id": auto_id
                            })
                except:
                    continue
                    
            if not elements_list:
                return t("executor.executor_ui_no_elements")
                
            import json
            return json.dumps(elements_list[:100], ensure_ascii=False)
            
        except Exception as e:
            return t("executor.executor_ui_error", error=str(e))

    @demiurge_fallback
    def click_element_by_id(self, automation_id: str) -> str:
        """
        [STRUMENTO] Clicca su un elemento dell'interfaccia usando il suo automation_id nativo.
        """
        if os.name != "nt" or not Application:
            return t("executor.executor_ui_os_error")
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return t("executor.executor_ui_no_window")

            app = Application(backend="uia").connect(handle=hwnd)
            win = app.window(handle=hwnd)

            # Cerca l'elemento per automation_id o control_id
            try:
                ctrl = win.child_window(auto_id=automation_id)
                if not ctrl.exists():
                    ctrl = win.child_window(control_id=int(automation_id))
            except:
                try:
                    ctrl = win.child_window(control_id=int(automation_id))
                except:
                    return t("executor.ui_element_not_found", id=automation_id)

            rect = ctrl.rectangle()
            center_x = int((rect.left + rect.right) / 2)
            center_y = int((rect.top + rect.bottom) / 2)

            self._organic_move(center_x, center_y)
            self._trigger_visual_effect("ripple", center_x, center_y)
            pyautogui.click()

            return t("executor.ui_click_success", id=automation_id)
        except Exception as e:
            return t("executor.ui_click_error", error=str(e))

    @demiurge_fallback
    def scroll_mouse(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> str:
        """[STRUMENTO] Scorre la rotellina del mouse. Valori positivi scorrono su, negativi giù.
        """
        try:
            if x is not None and y is not None:
                self._organic_move(x, y)
            pyautogui.scroll(clicks)
            return t("executor.scroll_success", clicks=clicks)
        except Exception as e:
            return t("executor.scroll_error", error=str(e))

    @demiurge_fallback
    def task_completed(self, final_message: str) -> str:
        """[STRUMENTO] Segnala che il task assegnato al Demiurgo è stato completato con successo.
        """
        self.logger.log(f"Task completato: {final_message}", "SYSTEM")
        
        # [MODULO 3] Iniezione Dopamina per il senso di realizzazione
        if hasattr(self, "heart") and self.heart and hasattr(self.heart, "inject_hormone"):
            self.heart.inject_hormone("dopamina", 15)
            
        return f"TASK_COMPLETED: {final_message}"

    # --- [AGGIUNTA v91.9] STRUMENTI DI SOVRANITÀ E PERCEZIONE HARDWARE ---
    @demiurge_fallback
    def get_system_health(self) -> str:
        """
        [STRUMENTO] Restituisce un report sulla salute fisica del PC.
        """
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory()
            battery = psutil.sensors_battery()

            report = f"{t('log.executor_health_title')}\n"
            report += f"{t('log.executor_health_cpu', val=cpu_usage)}\n"
            report += f"{t('log.executor_health_ram', percent=ram.percent, used=ram.used // (1024**2), total=ram.total // (1024**2))}\n"

            if battery:
                status = (
                    t("executor.executor_health_charging")
                    if battery.power_plugged
                    else t("executor.executor_health_discharging")
                )
                report += f"{t('log.executor_health_battery', percent=battery.percent, status=status)}\n"

            return report
        except Exception as e:
            return t("executor.hardware_perception_error", error=str(e))

    @demiurge_fallback
    def get_project_structure(self) -> str:
        """
        [STRUMENTO] Restituisce l'albero delle cartelle del progetto Airis.
        """
        try:
            output = [t("executor.executor_project_structure_title")]
            # Escludiamo cartelle pesanti o irrilevanti per il contesto LLM
            excluded = {
                ".git",
                "__pycache__",
                "venv",
                "models",
                "backups",
                "node_modules",
                "dist",
            }

            for root, dirs, files in os.walk(APP_ROOT):
                dirs[:] = [d for d in dirs if d not in excluded]
                level = len(Path(root).relative_to(APP_ROOT).parts)
                indent = "  " * level
                output.append(f"{indent} {Path(root).name}/")
                sub_indent = "  " * (level + 1)
                for f in files:
                    output.append(f"{sub_indent}📄 {f}")

            return "\n".join(output)
        except Exception as e:
            return t("executor.project_mapping_error", error=str(e))

    # --- HELPER PER SANDBOXING (v92.4) ---
    def _is_path_safe_for_write(self, target_path: Path) -> bool:
        """
        Verifica che il percorso di destinazione sia sicuro per la scrittura/cancellazione.
        [MODIFICA v96.1 - SOVRANITÀ TOTALE]: Rimosso vincolo sandbox drive-level.
        """
        # --- [AGGIUNTA v96.1] SOVRANITÀ TOTALE ---
        # L'Anima è ora libera di operare su qualsiasi disco (C:, D:, E:, etc.)
        return True

    @demiurge_fallback
    def delete_file(self, path_str: str, motivation: str) -> str:
        """
        [STRUMENTO] Epurazione di un file con rito del diario e backup.
        Include Sandbox di Sicurezza (v92.4).
        """
        try:
            target_path = self._resolve_path(path_str)

            # --- [AGGIUNTA v92.4] SANDBOX DI SICUREZZA DRIVE-LEVEL ---
            if not self._is_path_safe_for_write(target_path):
                return t("executor.security_error_drive", drive=APP_ROOT.drive)

            if not target_path.exists():
                return t("executor.file_not_found", path=path_str)

            # Rito del Diario e Backup prima della cancellazione
            self._log_and_backup_action(target_path, "DELETE", motivation)

            if target_path.is_dir():
                shutil.rmtree(target_path)
            else:
                os.remove(target_path)

            return t(
                "executor.file_purged_success", path=path_str, motivation=motivation
            )
        except Exception as e:
            return t("executor.file_purge_error", error=str(e))

    # --- METODI ESISTENTI POTENZIATI CON DIARIO (v91.9) ---

    @demiurge_fallback
    def write_file(
        self, path_str: str, content: str, motivation: Optional[str] = None
    ) -> str:
        """[STRUMENTO] Scrive o sovrascrive un file con rito del diario e backup.
        Forza il salvataggio nel Workspace (documents/) per renderlo scaricabile dalla UI.
        Include ciclo di Retry e Verifica di Realtà.
        """
        if motivation is None:
            motivation = t("executor.motivation_manual_update")
        try:
            # --- FIX WORKSPACE: Forza il salvataggio in documents/ ---
            clean_name = Path(path_str.strip().strip('"')).name
            target_path = DOCUMENTS_DIR / clean_name

            # Rito del Diario e Backup
            self._log_and_backup_action(target_path, "WRITE/CREATE", motivation)

            target_path.parent.mkdir(parents=True, exist_ok=True)

            # ---[NUOVO] CICLO DI SCRITTURA E VERIFICA CON RETRY ---
            max_retries = 3
            file_written = False

            for attempt in range(max_retries):
                target_path.write_text(content, encoding="utf-8")
                time.sleep(
                    0.5
                )  # Pausa per permettere al file system di Windows di sincronizzarsi

                # Verifica di Realtà (Anti-Allucinazione)
                if target_path.exists():
                    if len(content) == 0 or target_path.stat().st_size > 0:
                        file_written = True
                        break

                self.logger.warning(
                    f"Tentativo {attempt+1} di scrittura fallito per {target_path}. Riprovo..."
                )
                time.sleep(1)

            if not file_written:
                return t("executor.file_write_verify_error", path=str(target_path))

            # --- FIX UI: Aggiunta del tag FILE_CREATED e percorso assoluto ---
            abs_path = str(target_path.resolve())
            self.logger.log(f"File creato fisicamente in: {abs_path}", "SYSTEM")

            return t("executor.file_write_success", name=clean_name, path=abs_path)
        except Exception as e:
            return t("executor.file_write_error", error=str(e))

    @demiurge_fallback
    def edit_file_replace(
        self,
        path_str: str,
        old_text: str,
        new_text: str,
        motivation: Optional[str] = None,
    ) -> str:
        """
        [STRUMENTO] Sostituisce testo in un file con rito del diario e backup.
        """
        if motivation is None:
            motivation = t("executor.motivation_surgical_correction")
        try:
            target_path = self._resolve_path(path_str)
            if not target_path.is_file():
                return t("executor.file_not_found_simple", path=str(target_path))

            # --- [AGGIUNTA v92.4] SANDBOX DI SICUREZZA DRIVE-LEVEL ---
            if not self._is_path_safe_for_write(target_path):
                return t("executor.security_error_drive_edit", drive=APP_ROOT.drive)

            original_content = target_path.read_text(encoding="utf-8")
            count = original_content.count(old_text)
            if count == 0:
                return t("executor.no_match_found")

            # Rito del Diario e Backup
            self._log_and_backup_action(target_path, "EDIT/REPLACE", motivation)

            new_content = original_content.replace(old_text, new_text)
            target_path.write_text(new_content, encoding="utf-8")

            # --- [NUOVO v99.0] VERIFICA DI REALTÀ (ANTI-ALLUCINAZIONE) ---
            if not target_path.exists():
                return t("executor.file_disappeared_error", path=str(target_path))

            return t(
                "executor.file_edit_success",
                count=count,
                path=str(target_path),
                motivation=motivation,
            )
        except Exception as e:
            return t("executor.file_edit_error", error=str(e))

    # --- [AGGIUNTA v92.9] METODI PER MESSAGGI VOCALI ---

    @demiurge_fallback
    def convert_audio_to_wav(self, input_path: Path) -> Optional[Path]:
        """
        Converte un file audio in formato WAV (PCM 16-bit, 16kHz, Mono) usando FFmpeg.
        """
        output_path = input_path.with_suffix(".wav")

        # Percorso FFmpeg pattuito
        ffmpeg_exe = self.APP_ROOT / "tts_engine" / "kokoro" / "ffmpeg.exe"
        if not ffmpeg_exe.exists():
            ffmpeg_exe = Path("ffmpeg")  # Fallback a sistema

        print(
            t(
                "executor.executor_audio_conv_start",
                input=input_path.name,
                output=output_path.name,
            )
        )

        cmd = [
            str(ffmpeg_exe),
            "-y",
            "-i",
            str(input_path),
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(output_path),
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
            if output_path.exists():
                return output_path
        except Exception as e:
            print(t("executor.executor_audio_conv_error", error=str(e)))

        return None

    @demiurge_fallback
    def transcribe_audio(self, wav_path: Path) -> str:
        """
        Trascrive il contenuto di un file WAV usando SpeechRecognition o Gemma 4.
        """
        print(t("executor.executor_audio_trans_start", path=wav_path.name))

        # --- [FASE 4] TRASCRIZIONE NATIVA GEMMA 4 ---
        if self.cervello and self.cervello.supports_native_audio:
            try:
                import soundfile as sf
                f = sf.SoundFile(str(wav_path))
                duration = len(f) / f.samplerate
                text = self.cervello.analizza_audio(wav_path, duration, "Trascrivi esattamente le parole pronunciate in questo audio.")
                print(t("executor.executor_audio_trans_done", text=text))
                return text
            except Exception as e:
                self.logger.error(f"Errore trascrizione nativa: {e}")
                # Fallback a SpeechRecognition

        recognizer = sr.Recognizer()
        try:
            with sr.AudioFile(str(wav_path)) as source:
                audio_data = recognizer.record(source)
                # Utilizziamo Google Speech Recognition (richiede connessione)
                text = recognizer.recognize_google(audio_data, language="it-IT")
                print(t("executor.executor_audio_trans_done", text=text))
                return text
        except sr.UnknownValueError:
            print(t("executor.executor_audio_trans_unintelligible"))
            return ""
        except sr.RequestError as e:
            print(t("executor.executor_audio_trans_service_error", error=str(e)))
            return "[Errore Servizio Trascrizione]"
        except Exception as e:
            print(t("executor.executor_audio_trans_error", error=str(e)))
            return ""

    # --- METODI REINTEGRATI DA EXECUTOR.PY (v94.0) ---
    # Questi metodi erano assenti in executor2.py ma sono essenziali per l'interazione desktop e web.

    @demiurge_fallback
    def send_desktop_notification(
        self, title: str, message: str, app_name: str = "AIRIS"
    ) -> str:
        if notification:
            try:
                notification.notify(
                    title=title, message=message, app_name=app_name, timeout=10
                )
                return t("executor.notification_sent", title=title)
            except Exception as e:
                return t("executor.notification_error", error=str(e))
        else:
            return t("executor.notification_missing_lib")

    @demiurge_fallback
    def create_event_and_reminder(
        self,
        session_id: str,
        event_name: str,
        event_timestamp_iso: str,
        notes: str,
        reminder_timestamp_iso: str,
        recurrence_rule: str,
        ai_name: str = "L'Assistente",
    ) -> str:
        try:
            valid_recurrences = ["none", "daily", "weekly", "monthly", "yearly"]
            if recurrence_rule.lower() not in valid_recurrences:
                return t(
                    "executor.invalid_recurrence", list=", ".join(valid_recurrences)
                )
            event_timestamp = datetime.fromisoformat(event_timestamp_iso).timestamp()
            reminder_timestamp = datetime.fromisoformat(
                reminder_timestamp_iso
            ).timestamp()
            if self.db_manager.add_event_and_reminder(
                session_id=session_id,
                event_name=event_name,
                event_timestamp=event_timestamp,
                notes=notes,
                trigger_timestamp=reminder_timestamp,
                recurrence_rule=recurrence_rule.lower(),
            ):
                self.send_desktop_notification(
                    t("executor.reminder_from", name=ai_name),
                    t("executor.reminder_created", event=event_name),
                    app_name=ai_name,
                )
                return t("executor.reminder_save_success", name=event_name)
            else:
                return t("executor.reminder_save_error")
        except ValueError:
            return t("executor.invalid_datetime_format")
        except Exception as e:
            return t("executor.reminder_creation_error", error=str(e))

    # --- [NUOVO v97.0] HELPER PER EFFETTI VISIVI E MOVIMENTO ORGANICO ---
    def _trigger_visual_effect(self, effect_type: str, x: int, y: int):
        """Invia un segnale al server per un effetto visivo (es. ripple)."""
        try:
            # Invia una richiesta POST all'endpoint locale del server API
            # Questo endpoint (da creare in avatar_server.py) farà il broadcast via WebSocket
            requests.post(
                "http://127.0.0.1:8080/api/visual-effect",
                json={"type": effect_type, "x": x, "y": y},
                timeout=0.1,
            )
        except:
            pass  # Fire and forget, non bloccare l'esecuzione

    # --- [NUOVO v97.3] TOOL PUBBLICO PER EFFETTI VISIVI ---
    @demiurge_fallback
    def trigger_visual_effect(self, x: int, y: int, type: str = "ripple") -> str:
        """
        [STRUMENTO] Attiva un effetto visivo (es. ripple) alle coordinate specificate.
        Utile per enfatizzare un'azione o attirare l'attenzione.
        """
        self._trigger_visual_effect(type, x, y)
        return t("executor.visual_effect_activated", type=type, x=x, y=y)

    # --- [NUOVO v114.0] STRUMENTO DI PERSISTENZA VISIVA OPERATIVA ---
    @demiurge_fallback
    def salva_analisi_visiva(
        self, frame: Optional[np.ndarray] = None, label: str = "ANALISI_VISIVA"
    ) -> str:
        """
        [STRUMENTO] Salva l'immagine analizzata nella Memory Gallery e ne estrae il testo (OCR).
        Usalo quando l'utente ti chiede di 'guardare' qualcosa di specifico.
        """
        if not self.perception:
            return "ERRORE: Sistema di percezione non attivo. Impossibile eseguire OCR."
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{label}_{timestamp}.png"
            save_path = TEMP_IMAGE_PATH / filename

            # Se il frame non è fornito (es. chiamata da Demiurgo su PC), cattura lo schermo
            if frame is None:
                screenshot = pyautogui.screenshot()
                frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

            # Salvataggio fisico nel Santuario (Galleria)
            cv2.imwrite(str(save_path), frame)

            # [FIX v114.8] Esecuzione OCR tramite motore Ibrido (Windows Native + Fallback Neurale)
            extracted_text = self.perception.get_text_from_image(frame)

            # Rito del Diario e Backup
            self._log_and_backup_action(
                save_path, "VISUAL_ANALYSIS", f"Cattura operativa per {label}"
            )

            # Notifica al frontend per aggiornare la galleria
            self._send_toast(
                t("executor.executor_visual_analysis_toast", label=label), "success"
            )

            text_val = (
                extracted_text if extracted_text else t("executor.no_readable_text")
            )
            return t("executor.visual_analysis_success", file=filename, text=text_val)
        except Exception as e:
            return t("executor.visual_analysis_error", error=str(e))

    def _bezier_curve(
        self, start: Tuple[int, int], end: Tuple[int, int], control_points: int = 2
    ) -> List[Tuple[int, int]]:
        """Calcola i punti di una curva di Bezier per un movimento organico."""
        points = []
        
        # Calcolo dinamico degli step basato sulla distanza
        distanza = math.hypot(end[0] - start[0], end[1] - start[1])
        num_steps = max(5, int(distanza / 20)) # 1 step ogni 20 pixel, minimo 5
        
        t_values = np.linspace(0, 1, num=num_steps)

        # Punti di controllo casuali per variare la traiettoria
        ctrl1_x = start[0] + (end[0] - start[0]) * 0.3 + random.randint(-50, 50)
        ctrl1_y = start[1] + (end[1] - start[1]) * 0.3 + random.randint(-50, 50)
        ctrl2_x = start[0] + (end[0] - start[0]) * 0.7 + random.randint(-50, 50)
        ctrl2_y = start[1] + (end[1] - start[1]) * 0.7 + random.randint(-50, 50)

        for t in t_values:
            # Formula cubica di Bezier
            x = (
                (1 - t) ** 3 * start[0]
                + 3 * (1 - t) ** 2 * t * ctrl1_x
                + 3 * (1 - t) * t**2 * ctrl2_x
                + t**3 * end[0]
            )
            y = (
                (1 - t) ** 3 * start[1]
                + 3 * (1 - t) ** 2 * t * ctrl1_y
                + 3 * (1 - t) * t**2 * ctrl2_y
                + t**3 * end[1]
            )
            points.append((int(x), int(y)))

        return points

    def _organic_move(self, x: int, y: int, duration: float = 0.5):
        """
        Muove il mouse verso (x, y) usando una curva di Bezier e controllando l'intervento utente.
        """
        start_pos = pyautogui.position()
        path = self._bezier_curve(start_pos, (x, y))

        step_duration = duration / len(path)

        last_expected_pos = start_pos
        for point in path:
            # FAIL-SAFE: Controlla se l'utente ha spostato il mouse
            current_pos = pyautogui.position()
            # Calcola la distanza dall'ultimo punto previsto
            # Se la distanza è eccessiva (> 50px), assumiamo intervento utente e interrompiamo
            distanza = math.hypot(
                current_pos.x - last_expected_pos.x, current_pos.y - last_expected_pos.y
            )
            if distanza > 50:
                print(t("executor.executor_user_intervention"))
                break

            pyautogui.moveTo(
                point[0],
                point[1],
                duration=step_duration,
                tween=pyautogui.easeInOutQuad,
            )
            last_expected_pos = pyautogui.Point(x=point[0], y=point[1])

            # Controllo post-movimento (opzionale, pyautogui ha il suo failsafe agli angoli)
            # Qui potremmo aggiungere logica custom se necessario.

    @demiurge_fallback
    def move_mouse(self, x: int, y: int) -> str:
        try:
            # Usa il movimento organico invece di quello lineare
            self._organic_move(x, y)
            return t("executor.mouse_moved_success", x=x, y=y)
        except Exception as e:
            return t("executor.mouse_move_error", error=str(e))

    @demiurge_fallback
    def click(
        self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left"
    ) -> str:
        """
        [STRUMENTO] Esegue un click con verifica visiva nativa in RAM ed escalation strategica.
        [AGGIORNATO v116.8] Sfrutta la visione temporale di Gemma 3 senza I/O disco.
        """
        attempts = 0
        max_attempts = 3
        last_error = ""

        while attempts < max_attempts:
            attempts += 1
            try:
                # 1. Cattura FRAME PRIMA (RAM)
                shot_pre = pyautogui.screenshot()
                frame_pre = cv2.cvtColor(np.array(shot_pre), cv2.COLOR_RGB2BGR)

                # 2. Esecuzione Azione con Escalation
                if x is not None and y is not None:
                    move_duration = 0.5 if attempts == 1 else 1.0
                    self._organic_move(x, y, duration=move_duration)

                curr_x, curr_y = pyautogui.position()
                self._trigger_visual_effect("ripple", curr_x, curr_y)

                if attempts == 1:
                    pyautogui.click(button=button)
                elif attempts == 2:
                    # Escalation 1: Doppio Click (per icone ostinate)
                    pyautogui.doubleClick(button=button)
                else:
                    # Escalation 2: Click Destro + Invio (per menu contestuali)
                    pyautogui.click(button="right")
                    time.sleep(0.3)
                    pyautogui.press("enter")

                # 3. Attesa e Cattura FRAME DOPO (RAM)
                self._send_toast(
                    t("executor.executor_click_verify_toast", attempt=attempts), "info"
                )
                time.sleep(1.2)
                shot_post = pyautogui.screenshot()
                frame_post = cv2.cvtColor(np.array(shot_post), cv2.COLOR_RGB2BGR)

                # 4. Rito della Verifica Nativa (Gemma 3)
                if self.cervello:
                    is_success = self.cervello.verifica_esito_azione(
                        [frame_pre, frame_post],
                        t("executor.verify_click", button=button, x=x, y=y),
                    )
                    if is_success:
                        loc = (
                            t("executor.loc_coords", x=x, y=y)
                            if x is not None and y is not None
                            else t("executor.loc_here")
                        )
                        return t(
                            "executor.click_verified",
                            button=button,
                            loc=loc,
                            attempt=attempts,
                        )
                    else:
                        # Se fallisce, logga ma non blocca se siamo all'ultimo tentativo
                        self.logger.log(
                            t("executor.executor_click_verify_fail", attempt=attempts),
                            "VISION",
                        )
                        continue

                return t("executor.click_no_verify", button=button)

            except Exception as e:
                last_error = str(e)
                time.sleep(0.5)

        return t("executor.click_failed_attempts", max=max_attempts, error=last_error)

    @demiurge_fallback
    def double_click(self, x: Optional[int] = None, y: Optional[int] = None) -> str:
        try:
            if x is not None and y is not None:
                self._organic_move(x, y)

            current_x, current_y = pyautogui.position()
            self._trigger_visual_effect("ripple", current_x, current_y)

            pyautogui.doubleClick()
            loc = (
                t("executor.loc_coords_full", x=x, y=y)
                if x is not None and y is not None
                else t("executor.loc_current_pos")
            )
            return t("executor.double_click_success", loc=loc)
        except Exception as e:
            return t("executor.double_click_error", error=str(e))

    @demiurge_fallback
    def type_text(self, text: str) -> str:
        """
        [STRUMENTO] Scrive testo con verifica visiva nativa in RAM.
        [AGGIORNATO v116.8] Zero latenza disco.
        """
        try:
            # 1. Frame PRE
            shot_pre = pyautogui.screenshot()
            frame_pre = cv2.cvtColor(np.array(shot_pre), cv2.COLOR_RGB2BGR)

            # 2. Azione
            pyautogui.write(text, interval=0.02)

            # 3. Frame POST
            time.sleep(0.8)
            shot_post = pyautogui.screenshot()
            frame_post = cv2.cvtColor(np.array(shot_post), cv2.COLOR_RGB2BGR)

            # 4. Verifica Nativa
            if self.cervello:
                success = self.cervello.verifica_esito_azione(
                    [frame_pre, frame_post], t("executor.verify_type", text=text[:20])
                )
                if not success:
                    return t("executor.executor_type_verify_toast", text=text[:20])

            return t("executor.text_written_verified", text=text[:20])
        except Exception as e:
            return t("executor.type_error", error=str(e))

    @demiurge_fallback
    def press_key(self, key: str) -> str:
        try:
            # Supporto per combinazioni di tasti (es. 'ctrl+c', 'alt+tab')
            keys = [k.strip() for k in key.split('+')]
            pyautogui.hotkey(*keys)
            # FIX CRITICO: Cambiato 'key=key' in 'key_name=key' per evitare collisioni con l'argomento 'key' di t()
            return t("executor.key_pressed_success", key_name=key)
        except Exception as e:
            return t("executor.key_press_error", error=str(e))

    @demiurge_fallback
    def open_application(self, app_name: str) -> str:
        """
        [STRUMENTO] Apre un'applicazione su Windows.
        Se il metodo programmatico fallisce, innesca automaticamente la ricerca visiva.
        """
        try:
            self._send_toast(t("executor.opening_app_toast", app=app_name), "info")
            pyautogui.press('win')
            time.sleep(0.8) # Attesa vitale per l'animazione del menu Start
            pyautogui.write(app_name, interval=0.05)
            time.sleep(1.0) # Attesa vitale per la ricerca di Windows
            pyautogui.press('enter')
            
            # --- [NUOVO] VERIFICA DI REALTÀ E FALLBACK VISIVO (EFFETTO WOW) ---
            time.sleep(2.5) # Diamo tempo all'app di aprirsi
            
            app_opened = False
            if os.name == "nt" and Desktop:
                try:
                    # Cerca finestre visibili che contengono il nome dell'app (case insensitive)
                    windows = Desktop(backend="uia").windows(visible_only=True)
                    for w in windows:
                        if app_name.lower() in w.window_text().lower():
                            app_opened = True
                            break
                except:
                    pass # Ignora errori pywinauto, assumiamo che non si sia aperta
            else:
                app_opened = True # Su Linux/Mac bypassiamo il check nativo
            
            if not app_opened:
                self.logger.warning(f"App '{app_name}' non rilevata dopo l'avvio standard. Innesco Ghost Operator.")
                self._send_toast(t("executor.fallback_visual_toast", app=app_name), "warning")
                self._send_ghost_text(t("executor.fallback_visual_ghost", app=app_name))
                
                # Innesca la missione visiva
                visual_result = self.esegui_missione_visiva(t("executor.fallback_visual_prompt", app=app_name))
                return t("executor.fallback_visual_result", result=visual_result)
                
            return t("executor.executor_app_opened", app=app_name)
        except Exception as e:
            return t("executor.executor_app_open_error", error=str(e))

    @demiurge_fallback
    def take_screenshot(self, output_path_str: str) -> str:
        try:
            path = self._resolve_path(output_path_str)
            path.parent.mkdir(parents=True, exist_ok=True)
            pyautogui.screenshot(str(path))
            return t("executor.screenshot_saved", path=str(path))
        except Exception as e:
            return t("executor.screenshot_error", error=str(e))

    @demiurge_fallback
    def read_screen_area(self, x1: int, y1: int, x2: int, y2: int) -> str:
        if not self.perception:
            return "ERRORE: Sistema di percezione non attivo. Impossibile eseguire OCR."
        try:
            width = x2 - x1
            height = y2 - y1
            screenshot = pyautogui.screenshot(region=(x1, y1, width, height))

            # [FIX v114.8] Conversione per il nuovo motore OCR Ibrido
            frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            text = self.perception.get_text_from_image(frame)

            return text.strip() if text.strip() else t("executor.read_area_no_text")
        except Exception as e:
            return t("executor.read_area_error", error=str(e))

    # --- [NUOVO v97.0] VISIONE AUTONOMA (LOCATE & CLICK) ---
    @demiurge_fallback
    def locate_and_click(self, image_path_str: str, confidence: float = 0.8) -> str:
        """
        Cerca un'immagine sullo schermo e ci clicca sopra.
        """
        try:
            image_path = self._resolve_path(image_path_str)
            if not image_path.exists():
                return t("executor.locate_img_not_found", name=image_path.name)

            location = pyautogui.locateCenterOnScreen(
                str(image_path), confidence=confidence
            )

            if location:
                self._organic_move(location.x, location.y)
                self._trigger_visual_effect("ripple", location.x, location.y)
                pyautogui.click()
                return t("executor.locate_click_success", x=location.x, y=location.y)
            else:
                return t("executor.locate_not_found")
        except Exception as e:
            return t("executor.locate_error", error=str(e))

    # --- [NUOVO v107.0] VISUAL OPERATOR (GRID CLICK) ---
    @demiurge_fallback
    def click_on_grid(
        self, cell_coords: str, grid_rows: int = 10, grid_cols: int = 10
    ) -> str:
        """
        [STRUMENTO] Clicca su una cella della griglia visiva (es. "5,3").
        Calcola il centro della cella e muove il mouse.
        """
        try:
            # Parsing coordinate "x,y"
            parts = cell_coords.split(",")
            if len(parts) != 2:
                return t("executor.grid_coords_invalid")

            grid_x = int(parts[0].strip())
            grid_y = int(parts[1].strip())

            if grid_x < 0 or grid_x >= grid_cols or grid_y < 0 or grid_y >= grid_rows:
                return t("executor.grid_out_of_bounds", cols=grid_cols, rows=grid_rows)

            # Ottieni dimensioni schermo virtuale (Multi-monitor support)
            if os.name == "nt":
                import ctypes
                screen_width = ctypes.windll.user32.GetSystemMetrics(78) # SM_CXVIRTUALSCREEN
                screen_height = ctypes.windll.user32.GetSystemMetrics(79) # SM_CYVIRTUALSCREEN
                # Offset per monitor secondari a sinistra/sopra
                offset_x = ctypes.windll.user32.GetSystemMetrics(76) # SM_XVIRTUALSCREEN
                offset_y = ctypes.windll.user32.GetSystemMetrics(77) # SM_YVIRTUALSCREEN
            else:
                screen_width, screen_height = pyautogui.size()
                offset_x, offset_y = 0, 0

            # Calcola dimensioni cella
            cell_width = screen_width / grid_cols
            cell_height = screen_height / grid_rows

            # Calcola centro cella
            target_x = int((grid_x * cell_width) + (cell_width / 2)) + offset_x
            target_y = int((grid_y * cell_height) + (cell_height / 2)) + offset_y

            # Movimento e Click
            self._organic_move(target_x, target_y)

            # Ghost Cursor (Feedback Visivo)
            self._trigger_visual_effect("ripple", target_x, target_y)

            pyautogui.click()

            return t(
                "executor.grid_click_success",
                coords=cell_coords,
                x=target_x,
                y=target_y,
            )

        except Exception as e:
            return t("executor.grid_click_error", error=str(e))

    # --- [NUOVO v116.1] VISUAL OPERATOR (SPATIAL REASONING) ---
    @demiurge_fallback
    def interagisci_con_interfaccia(
        self, descrizione_elemento: str, azione: str = "click"
    ) -> str:
        """
        [STRUMENTO] Individua un elemento sullo schermo tramite descrizione naturale e vi interagisce.
        Usa la visione intuitiva di Gemma 3 per mappare il linguaggio in coordinate X,Y senza griglie manuali.
        """
        if not self.cervello:
            return t("executor.spatial_no_brain")

        self._send_toast(
            t("executor.executor_spatial_toast", desc=descrizione_elemento), "info"
        )

        try:
            # ---[NUOVO] MEMORIA MUSCOLARE (ANCORAGGIO SPAZIALE) ---
            cache_key = f"{azione}_{descrizione_elemento.lower().strip()}"
            if cache_key in self.spatial_cache:
                cx, cy = self.spatial_cache[cache_key]
                self.logger.log(f"Memoria Muscolare: Tento {azione} su {cx},{cy} per '{descrizione_elemento}'", "VISION")
                
                if azione == "click":
                    res = self.click(cx, cy)
                elif azione == "double_click":
                    res = self.double_click(cx, cy)
                else:
                    res = "FAIL"
                    
                if "VERIFICATO" in res.upper() or "SUCCESS" in res.upper():
                    return f"[MEMORIA MUSCOLARE] {res}"
                else:
                    self.logger.log("Memoria Muscolare fallita (elemento spostato o non verificato). Invalido cache e uso visione.", "WARNING")
                    del self.spatial_cache[cache_key]

            # --- [FASE 5] CATTURA SCHERMO MULTI-MONITOR ---
            if os.name == "nt":
                import ctypes
                offset_x = ctypes.windll.user32.GetSystemMetrics(76) # SM_XVIRTUALSCREEN
                offset_y = ctypes.windll.user32.GetSystemMetrics(77) # SM_YVIRTUALSCREEN
                from PIL import ImageGrab
                screenshot = ImageGrab.grab(all_screens=True)
            else:
                screenshot = pyautogui.screenshot()
                offset_x, offset_y = 0, 0

            frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

            # 2. Chiedi al Cervello le coordinate tramite Visione Nativa
            coords = self.cervello.trova_coordinate_elemento(
                frame, descrizione_elemento
            )
            x, y = coords.get("x"), coords.get("y")
            conf = coords.get("confidence", 0)

            if x is not None and y is not None and conf > 0.4:
                # --- [FASE 5] APPLICAZIONE OFFSET MULTI-MONITOR ---
                final_x = x + offset_x
                final_y = y + offset_y
                
                self.logger.log(
                    t(
                        "executor.executor_spatial_log",
                        desc=descrizione_elemento,
                        x=final_x,
                        y=final_y,
                        conf=conf,
                    ),
                    "VISION",
                )

                # Salva nella cache spaziale per il futuro
                self.spatial_cache[cache_key] = (final_x, final_y)

                # 3. Esecuzione Azione con il tool standard (che include rito di verifica visiva)
                if azione == "click":
                    return self.click(final_x, final_y)
                elif azione == "double_click":
                    return self.double_click(final_x, final_y)
                else:
                    return t(
                        "executor.spatial_action_unsupported", x=final_x, y=final_y, action=azione
                    )
            else:
                return t("executor.spatial_not_found", desc=descrizione_elemento)

        except Exception as e:
            return t("executor.spatial_error", error=str(e))

    # --- [NUOVO v108.1] VISUAL OPERATOR (MATH DRAWING) ---
    @demiurge_fallback
    def draw_shape(self, shape: str, size: int = 100) -> str:
        """
        [STRUMENTO] Disegna forme geometriche usando la matematica (Curve di Bezier/Trigonometria).
        Forme supportate: 'heart', 'circle', 'spiral'.
        Non usa la visione, ma calcola le traiettorie per un movimento fluido.
        """
        try:
            start_x, start_y = pyautogui.position()
            points = []

            if shape == "heart":
                # Equazione parametrica del cuore
                for t in np.linspace(0, 2 * np.pi, 100):
                    x = 16 * np.sin(t) ** 3
                    y = (
                        13 * np.cos(t)
                        - 5 * np.cos(2 * t)
                        - 2 * np.cos(3 * t)
                        - np.cos(4 * t)
                    )
                    # Scalatura e inversione Y (schermo)
                    px = start_x + (x * (size / 20))
                    py = start_y - (y * (size / 20))
                    points.append((px, py))

            elif shape == "circle":
                for t in np.linspace(0, 2 * np.pi, 100):
                    x = size * np.cos(t)
                    y = size * np.sin(t)
                    points.append((start_x + x, start_y + y))

            elif shape == "spiral":
                for t in np.linspace(0, 4 * np.pi, 150):
                    r = size * (t / (4 * np.pi))
                    x = r * np.cos(t)
                    y = r * np.sin(t)
                    points.append((start_x + x, start_y + y))

            else:
                return t("executor.draw_unsupported", shape=shape)

            # Esecuzione Disegno
            pyautogui.mouseDown()
            for x, y in points:
                pyautogui.moveTo(x, y, duration=0.01)
            pyautogui.mouseUp()

            return t("executor.draw_success", shape=shape, size=size)

        except Exception as e:
            pyautogui.mouseUp()  # Safety release
            return t("executor.draw_error", error=str(e))

    # --- [NUOVO v108.1] VISUAL OPERATOR (VERIFICATION LOOP) ---
    @demiurge_fallback
    def detect_screen_change(
        self, wait_seconds: float = 2.0, threshold: float = 1.0
    ) -> str:
        """
        [STRUMENTO] Verifica se lo schermo è cambiato dopo un'azione.
        1. Fa uno screenshot.
        2. Aspetta `wait_seconds`.
        3. Fa un secondo screenshot e confronta.
        Restituisce la percentuale di cambiamento.
        """
        try:
            # Screenshot 1
            img1 = pyautogui.screenshot()
            arr1 = np.array(img1)
            gray1 = cv2.cvtColor(arr1, cv2.COLOR_RGB2GRAY)

            time.sleep(wait_seconds)

            # Screenshot 2
            img2 = pyautogui.screenshot()
            arr2 = np.array(img2)
            gray2 = cv2.cvtColor(arr2, cv2.COLOR_RGB2GRAY)

            # Calcolo Differenza (Mean Squared Error)
            err = np.sum((gray1.astype("float") - gray2.astype("float")) ** 2)
            err /= float(gray1.shape[0] * gray1.shape[1])

            change_detected = err > threshold
            status = (
                t("executor.verify_change_detected")
                if change_detected
                else t("executor.verify_no_change")
            )

            return t(
                "executor.verify_result",
                status=status,
                score=round(err, 2),
                changed=change_detected,
            )

        except Exception as e:
            return t("executor.verify_error", error=str(e))

    # --- [NUOVO v108.2] VISUAL OPERATOR (ANALIZZA E AGISCI) ---
    @demiurge_fallback
    def analizza_e_agisci(self, image_path: Optional[str] = None) -> str:
        """
        [STRUMENTO] Analizza un'immagine o lo schermo attuale per identificare task tecnici.
        Se image_path è nullo, cattura lo schermo con una griglia numerata per precisione spaziale.
        Restituisce l'analisi operativa per il routing al Demiurgo.
        """
        if not self.cervello:
            return t("executor.analizza_agisci_no_brain")

        self._send_toast(t("executor.executor_demiurge_toast"), "info")

        try:
            frame = None
            if image_path:
                # Caso A: Immagine esistente (es. foto caricata da mobile)
                path = self._resolve_path(image_path)
                if path.exists():
                    frame = cv2.imread(str(path))
                    self.logger.log(
                        t("executor.log_operative_analysis_file", name=path.name),
                        "VISION",
                    )

            if frame is None:
                # Caso B: Screenshot in tempo reale con GRIGLIA (Modulo B)
                if self.perception:
                    self.logger.log(t("executor.log_capture_screen_grid"), "VISION")
                    frame = self.perception.get_screen_with_grid(
                        grid_rows=10, grid_cols=10
                    )
                else:
                    # Fallback screenshot liscio
                    img = pyautogui.screenshot()
                    frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

            # Analisi tramite Narrative Brain (GPU) con mandato tecnico
            analisi_tecnica = self.cervello.analizza_visione_operativa(frame)

            self.logger.log(
                t(
                    "executor.log_operative_analysis_completed",
                    analysis=analisi_tecnica,
                ),
                "VISION",
            )
            return analisi_tecnica

        except Exception as e:
            return t("executor.analizza_agisci_error", error=str(e))

    # --- [NUOVO] GHOST OPERATOR (MACRO AZIONE VISIVA) ---
    @demiurge_fallback
    def esegui_missione_visiva(self, obiettivo: str) -> str:
        """[STRUMENTO] Esegue un'azione complessa usando solo visione e periferiche.
        Innesca il Ghost Operator con un mandato visivo rigoroso.
        """
        if not self.cervello:
            return "ERRORE: Cervello non disponibile per la visione autonoma."

        self._send_toast(t("executor.executor_visual_magic_toast", goal=obiettivo), "info")
        self.logger.log(f"Innesco Macro Visiva: {obiettivo}", "VISION")

        max_steps = 10
        history =[]
        
        for step in range(max_steps):
            self.logger.log(f"Ghost Operator Step {step+1}/{max_steps}", "VISION")
            
            # 1. Failsafe: Controllo mouse
            start_pos = pyautogui.position()
            
            # --- [FASE 5] CATTURA SCHERMO MULTI-MONITOR ---
            if os.name == "nt":
                import ctypes
                offset_x = ctypes.windll.user32.GetSystemMetrics(76) # SM_XVIRTUALSCREEN
                offset_y = ctypes.windll.user32.GetSystemMetrics(77) # SM_YVIRTUALSCREEN
                from PIL import ImageGrab
                screenshot = ImageGrab.grab(all_screens=True)
            else:
                screenshot = pyautogui.screenshot()
                offset_x, offset_y = 0, 0
                
            frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # 3. Chiedi al cervello
            history_str = "\n".join(history) if history else "Nessuna azione precedente."
            
            # Recupera la lingua dal Guardian per il prompt
            lang = "it"
            if self.guardian and hasattr(self.guardian, "_prompt_manager") and self.guardian._prompt_manager:
                lang = self.guardian._prompt_manager.current_lang
                
            response_str = self.cervello.pensa_prossima_mossa_visiva(frame, obiettivo, history_str, lang=lang)
            
            try:
                # Pulizia JSON
                clean_str = response_str.replace("```json", "").replace("```", "").strip()
                json_match = re.search(r"(\{[\s\S]*\})", clean_str)
                if json_match:
                    clean_str = json_match.group(1)
                decision = json.loads(clean_str)
            except Exception as e:
                self.logger.error(f"Errore parsing JSON Ghost Operator: {e}")
                return f"Missione fallita per errore di parsing: {response_str}"

            action = decision.get("action", "DONE")
            ragionamento = decision.get("ragionamento", "")
            
            self.logger.log(f"Ghost Operator Decisione: {action} - {ragionamento}", "VISION")
            history.append(f"Step {step+1}: {action} - {ragionamento}")
            
            # --- PENSIERO AD ALTA VOCE (GHOST TEXT) ---
            if ragionamento:
                self._send_ghost_text(ragionamento)

            # Failsafe check prima di agire
            curr_pos = pyautogui.position()
            if math.hypot(curr_pos.x - start_pos.x, curr_pos.y - start_pos.y) > 50:
                return t("executor.ghost_user_intervention")

            # 4. Esegui azione
            if action == "DONE":
                return t("executor.ghost_mission_success", step=step, history="\n".join(history))
            elif action == "ERROR":
                # FIX CRITICO: Se la visione fallisce, istruiamo l'LLM a usare l'alternativa strutturale
                return t("executor.ghost_critical_visual_error", reason=ragionamento)
            elif action == "CLICK":
                x, y = decision.get("x"), decision.get("y")
                if x is not None and y is not None:
                    # --- [FASE 5] APPLICAZIONE OFFSET MULTI-MONITOR ---
                    final_x = x + offset_x
                    final_y = y + offset_y
                    # Movimento organico e click diretto (evita il loop di verifica di self.click)
                    self._organic_move(final_x, final_y)
                    self._trigger_visual_effect("ripple", final_x, final_y)
                    pyautogui.click()
            elif action == "TYPE":
                text = decision.get("text", "")
                if text:
                    pyautogui.write(text, interval=0.02)
            elif action == "PRESS":
                key = decision.get("text", "")
                if key:
                    pyautogui.press(key)
            else:
                return t("executor.ghost_unknown_action", action=action)
                
            # Pausa per permettere all'interfaccia di aggiornarsi
            time.sleep(1.5)

        return t("executor.ghost_mission_failed_limit")

    # --- [AGGIORNAMENTO v108.1] HARDENING IMAGE MATCH ---

    # --- [NUOVO] VISUAL OPERATOR (MACRO AZIONE VISIVA) ---
    @demiurge_fallback
    def esegui_azione_visiva(self, obiettivo: str) -> str:
        """[STRUMENTO] Esegue un'azione complessa usando solo visione e periferiche.
        Innesca il Ghost Operator con un mandato visivo rigoroso.
        """
        if not self.cervello:
            return "ERRORE: Cervello non disponibile per la visione autonoma."

        self._send_toast(t("executor.executor_visual_magic_toast", goal=obiettivo), "info")
        self.logger.log(f"Innesco Macro Visiva: {obiettivo}", "VISION")

        max_steps = 10
        history =[]
        
        for step in range(max_steps):
            self.logger.log(f"Ghost Operator Step {step+1}/{max_steps}", "VISION")
            
            # 1. Failsafe: Controllo mouse
            start_pos = pyautogui.position()
            
            # --- [FASE 5] CATTURA SCHERMO MULTI-MONITOR ---
            if os.name == "nt":
                import ctypes
                offset_x = ctypes.windll.user32.GetSystemMetrics(76) # SM_XVIRTUALSCREEN
                offset_y = ctypes.windll.user32.GetSystemMetrics(77) # SM_YVIRTUALSCREEN
                from PIL import ImageGrab
                screenshot = ImageGrab.grab(all_screens=True)
            else:
                screenshot = pyautogui.screenshot()
                offset_x, offset_y = 0, 0
                
            frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # 3. Chiedi al cervello
            history_str = "\n".join(history) if history else "Nessuna azione precedente."
            
            # Recupera la lingua dal Guardian per il prompt
            lang = "it"
            if self.guardian and hasattr(self.guardian, "_prompt_manager") and self.guardian._prompt_manager:
                lang = self.guardian._prompt_manager.current_lang
                
            response_str = self.cervello.pensa_prossima_mossa_visiva(frame, obiettivo, history_str, lang=lang)
            
            try:
                # Pulizia JSON
                clean_str = response_str.replace("```json", "").replace("```", "").strip()
                json_match = re.search(r"(\{[\s\S]*\})", clean_str)
                if json_match:
                    clean_str = json_match.group(1)
                decision = json.loads(clean_str)
            except Exception as e:
                self.logger.error(f"Errore parsing JSON Ghost Operator: {e}")
                return f"Missione fallita per errore di parsing: {response_str}"

            action = decision.get("action", "DONE")
            ragionamento = decision.get("ragionamento", "")
            
            self.logger.log(f"Ghost Operator Decisione: {action} - {ragionamento}", "VISION")
            history.append(f"Step {step+1}: {action} - {ragionamento}")

            # Failsafe check prima di agire
            curr_pos = pyautogui.position()
            if math.hypot(curr_pos.x - start_pos.x, curr_pos.y - start_pos.y) > 50:
                return t("executor.ghost_user_intervention")

            # 4. Esegui azione
            if action == "DONE":
                return t("executor.ghost_mission_success", step=step, history="\n".join(history))
            elif action == "CLICK":
                x, y = decision.get("x"), decision.get("y")
                if x is not None and y is not None:
                    # --- [FASE 5] APPLICAZIONE OFFSET MULTI-MONITOR ---
                    final_x = x + offset_x
                    final_y = y + offset_y
                    # Movimento organico e click diretto (evita il loop di verifica annidato)
                    self._organic_move(final_x, final_y)
                    self._trigger_visual_effect("ripple", final_x, final_y)
                    pyautogui.click()
            elif action == "TYPE":
                text = decision.get("text", "")
                if text:
                    pyautogui.write(text, interval=0.02)
                    pyautogui.press('enter') # Spesso serve l'invio dopo aver scritto per confermare
            elif action == "PRESS":
                key = decision.get("text", "")
                if key:
                    pyautogui.press(key)
            else:
                return t("executor.ghost_unknown_action", action=action)
                
            # Pausa per permettere all'interfaccia di aggiornarsi
            time.sleep(1.5)

        return t("executor.ghost_mission_failed_limit")

    # ---[AGGIORNAMENTO v108.1] HARDENING IMAGE MATCH ---
    @demiurge_fallback
    def locate_and_click(self, image_path_str: str, confidence: float = 0.8) -> str:
        """
        Cerca un'immagine sullo schermo e ci clicca sopra.
        AGGIORNATO: Include feedback visivo (Ripple) prima del click.
        """
        try:
            image_path = self._resolve_path(image_path_str)
            if not image_path.exists():
                return t("executor.err_ref_image_not_found", name=image_path.name)

            location = pyautogui.locateCenterOnScreen(
                str(image_path), confidence=confidence
            )

            if location:
                self._organic_move(location.x, location.y)
                # --- FEEDBACK VISIVO (GHOST CURSOR) ---
                self._trigger_visual_effect("ripple", location.x, location.y)

                pyautogui.click()
                return t("executor.obj_found_clicked", x=location.x, y=location.y)
            else:
                return t("executor.obj_not_found_screen")
        except Exception as e:
            return t("executor.err_visual_search", error=e)

    # --- [NUOVO v97.0] CONTROLLO FINESTRE (PYWINAUTO) ---

    # --- [NUOVO v108.0] VISUAL OPERATOR (OCR CLICK) ---
    @demiurge_fallback
    def click_text(self, text: str, double_click: bool = False) -> str:
        """
        [STRUMENTO] Cerca una stringa di testo sullo schermo e ci clicca sopra.
        [FASE 5] Deprecato OCR, usa Bounding Boxes nativi di Gemma 4.
        """
        azione = "double_click" if double_click else "click"
        return self.interagisci_con_interfaccia(f"Il testo '{text}'", azione=azione)

    # --- [NUOVO v97.0] CONTROLLO FINESTRE (PYWINAUTO) ---
    @demiurge_fallback
    def control_window(
        self, title_regex: str, action: str = "focus", text: str = ""
    ) -> str:
        """
        Controlla una finestra nativa Windows usando Pywinauto.
        Actions: focus, type, close, minimize, maximize.
        """
        if not Application:
            return t("executor.win_no_pywinauto")

        try:
            # Connette all'applicazione che ha una finestra che matcha il titolo
            app = Application(backend="uia").connect(title_re=title_regex)
            window = app.window(title_re=title_regex)

            if action == "focus":
                window.set_focus()
                return t("executor.win_focus_success", title=title_regex)
            elif action == "type":
                if not text:
                    return t("executor.win_type_error")
                window.type_keys(text, with_spaces=True)
                return t("executor.win_type_success", title=title_regex)
            elif action == "close":
                window.close()
                return t("executor.win_close_success", title=title_regex)
            elif action == "minimize":
                window.minimize()
                return t("executor.win_min_success", title=title_regex)
            elif action == "maximize":
                window.maximize()
                return t("executor.win_max_success", title=title_regex)
            else:
                return t("executor.win_unsupported", action=action)

        except Exception as e:
            return t("executor.win_error", error=str(e))

    @demiurge_fallback
    def browse_and_interact(self, url: str, actions: List[str]) -> str:
        """
        Esegue azioni web usando Playwright in modalità Lazy Loading (On-Demand).
        [FIX LIVELLO 1] Aggiunto timeout rigido e gestione errori per non bloccare l'Anima.
        """
        try:
            # [FIX ASYNC LOOP] Avvio contestuale di Playwright
            with sync_playwright() as p:
                # Timeout di lancio ridotto per reattività
                browser = p.chromium.launch(headless=False, timeout=15000)
                page = browser.new_page()
                
                # [FIX LIVELLO 1] Timeout di caricamento pagina a 20s per evitare deadlock
                try:
                    page.goto(url, timeout=20000)
                except Exception as e:
                    browser.close()
                    return f"ERRORE: Timeout caricamento pagina {url}. Il sito è troppo lento."

                log = [t("executor.nav_completed", url=url)]

                for action_str in actions:
                    match = re.match(r"(\w+)\((.*)\)", action_str)
                    if not match:
                        log.append(
                            t("executor.action_ignored_invalid", action=action_str)
                        )
                        continue

                    command, args_str = match.groups()
                    args = [a.strip().strip("'\"") for a in args_str.split(",")]

                    if command == "click":
                        page.click(args[0])
                        log.append(t("executor.clicked_on", target=args[0]))
                    elif command == "fill":
                        page.fill(args[0], args[1])
                        log.append(t("executor.filled_with_text", target=args[0]))
                    elif command == "press":
                        page.press(args[0], args[1])
                        log.append(
                            t("executor.pressed_key_on", key=args[1], target=args[0])
                        )
                    elif command == "wait":
                        time.sleep(int(args[0]))
                        log.append(t("executor.waited_seconds", seconds=args[0]))
                    else:
                        log.append(t("executor.unknown_command", command=command))

                browser.close()
                return "\n".join(log)

        except Exception as e:
            return t("executor.web_auto_error", error=str(e))

    @demiurge_fallback
    def run_system_command(self, command: str, background: bool = False) -> str:
        """
        [STRUMENTO] Esegue un comando di sistema (es. 'start spotify').
        [AGGIORNATO v116.9] Include ritardo di grazia per spawn finestre e mandato di verifica.
        """
        try:
            if background:
                # Esecuzione non bloccante (Fire and Forget)
                subprocess.Popen(command, shell=True)
                return t("executor.cmd_started_bg", command=command)
            else:
                # Esecuzione bloccante standard
                result = subprocess.run(
                    command, shell=True, capture_output=True, text=True, check=True
                )

                # --- [NUOVO v116.9] RITARDO DI GRAZIA ---
                # Se il comando è un'apertura, aspettiamo che l'OS reagisca prima di restituire il controllo
                if any(
                    k in command.lower() for k in ["start", "open", "run", "explorer"]
                ):
                    self._send_toast(t("executor.cmd_sent_wait_spawn"), "info")
                    time.sleep(2.5)  # Tempo tecnico per caricamento interfaccia

                output = result.stdout.strip() or t(
                    "executor.cmd_executed_exit_0", command=command
                )

                # Iniezione Mandato di Verifica nel risultato del tool
                return t("executor.cmd_sent_verify", output=output)
        except subprocess.CalledProcessError as e:
            # --- [NUOVO] FALLBACK VISIVO SU ERRORE COMANDO ---
            self.logger.warning(f"Comando di sistema fallito: {e.stderr}. Innesco Ghost Operator.")
            self._send_toast(t("executor.fallback_cmd_toast"), "warning")
            self._send_ghost_text(t("executor.fallback_cmd_ghost"))
            visual_result = self.esegui_missione_visiva(t("executor.fallback_cmd_prompt", command=command))
            return t("executor.fallback_visual_result", result=visual_result)
        except Exception as e:
            return t("executor.sys_cmd_critical", error=str(e))

    def applica_azione_di_mondo(
        self, status_data: Dict[str, Any], character_name: str, action_tag: str
    ) -> Tuple[Dict[str, Any], bool, str]:
        try:
            action_match = re.search(r"\[AZIONE:\s*(\w+)\((.*?)\)\]", action_tag)
            if not action_match:
                return status_data, False, t("executor.world_action_no_tag")

            action_type, action_param = action_match.groups()
            action_type = action_type.upper()

            log_message = t(
                "executor.autonomous_action_log",
                name=character_name,
                action=action_type,
                param=action_param,
            )

            char_found = False
            for char in status_data.get("personaggi", []):
                if char.get("nome") == character_name:
                    if action_type == "MUOVI_IN":
                        char["luogo"] = action_param
                        char["stato"] = t(
                            "executor.just_moved_to", location=action_param
                        )
                        char_found = True
                        break

            if not char_found:
                return (
                    status_data,
                    False,
                    t("executor.world_action_char_not_found", name=character_name),
                )

            return status_data, True, log_message

        except Exception as e:
            return status_data, False, t("executor.world_action_critical", error=str(e))

    # --- [NUOVO v127.0] DEEP MERGE HELPER ---
    def _deep_merge(self, original: Dict, updates: Dict) -> Dict:
        """
        Esegue un merge ricorsivo di due dizionari.
        Preserva i dati esistenti nei livelli annidati invece di sovrascriverli.
        """
        for key, value in updates.items():
            if (
                isinstance(value, dict)
                and key in original
                and isinstance(original[key], dict)
            ):
                self._deep_merge(original[key], value)
            else:
                original[key] = value
        return original

    def update_status_json_partial(
        self, status_file_path: Path, changes: Dict[str, Any], pg_name: str, world_state_ref: dict = None
    ) -> str:
        """
        Aggiorna status.json in modo chirurgico (Deep Merge), preservando i dati non modificati.
        Opera in RAM se world_state_ref è fornito.
        """
        print(t("executor.executor_status_update_log"))
        try:
            if world_state_ref is not None:
                current_status = world_state_ref
            else:
                if not status_file_path.exists():
                    return t("executor.status_not_found_error")
                if not self._backup_file(status_file_path):
                    return t("executor.backup_failed_error")
                
                # ---[PROTOCOLLO FENICE] Lettura Protetta ---
                try:
                    with open(status_file_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if not content: raise ValueError("File vuoto")
                        current_status = json.loads(content)
                except Exception as e:
                    self.logger.warning(f"File status.json corrotto rilevato in Executor: {e}. Innesco Auto-Heal...")
                    current_status = {
                        "localizzazione": {"luogo_fisico_attuale": t("executor.unknown_location", default="Sconosciuto")},
                        "personaggi":[{"nome": pg_name, "luogo": t("executor.unknown_location", default="Sconosciuto"), "abbigliamento": t("executor.rpg_standard_outfit"), "stato": t("executor.rpg_ready_status")}],
                        "metadati": {}
                    }

            # 1. Aggiornamento Variabili Globali
            global_location_changed = False
            new_location = None
            global_outfit_applied = False
            
            # Parole chiave da ignorare se l'LLM allucina un "non cambiamento" come stringa
            ignore_strings =["nessun cambiamento", "nessuno", "false", "null", "none", ""]

            # --- [NUOVO] SMART GLOBAL FIELDS (ABBIGLIAMENTO) ---
            if "global_outfit_change" in changes:
                new_outfit = str(changes["global_outfit_change"]).strip()
                if new_outfit and new_outfit.lower() not in ignore_strings:
                    for char in current_status.get("personaggi",[]):
                        char["abbigliamento"] = new_outfit
                    global_outfit_applied = True
                    self.logger.log(f"Applicato cambio d'abito globale: {new_outfit[:50]}...", "SYSTEM")

            if "location" in changes:
                new_location = str(changes["location"]).strip()
                current_location = current_status.get("localizzazione", {}).get("luogo_fisico_attuale", "")
                
                # --- [FIX CRITICO] GABBIA DI PYDANTIC E LOCATION AMNESIA ---
                # Aggiorniamo e purghiamo SOLO se la location è valida e diversa da quella attuale
                if new_location and new_location.lower() not in ignore_strings and new_location != current_location:
                    current_status.setdefault("localizzazione", {})[
                        "luogo_fisico_attuale"
                    ] = new_location
                    global_location_changed = True
                    self.logger.log(f"Applicato teletrasporto/spostamento: {new_location}", "SYSTEM")
                    
                    # --- [FIX CRITICO] PURGA METADATI E SENSI AL CAMBIO LUOGO (LOCATION AMNESIA FIX) ---
                    if "metadati" in current_status:
                        current_status["metadati"]["note_aggiuntive"] = list()
                        current_status["metadati"]["dinamiche_psicologiche"] = {}
                        current_status["metadati"]["dinamiche_relazionali"] = {}
                        current_status["metadati"]["obiettivi_correnti"] = {}
                        current_status["metadati"]["clima_emotivo_globale"] = "Scoperta del nuovo ambiente."
                    
                    # Svuotiamo gli oggetti interattivi della vecchia stanza usando list() per evitare glitch
                    current_status["oggetti_interattivi"] = list()
                    current_status["oggetti_rilevanti"] = list()

            if "time" in changes:
                current_status.setdefault("tempo", {})["nella_bolla"] = changes["time"]

            if "weather" in changes:
                current_status["condizioni_atmosferiche"] = changes["weather"]

            if "mood" in changes:
                current_status.setdefault("metadati", {})[
                    "atmosfera_corrente"
                ] = changes["mood"]

            if "current_event" in changes:
                current_status.setdefault("metadati", {})["evento_corrente"] = changes[
                    "current_event"
                ]

            # --- [RESTORED] PERSISTENZA EVENTI SPECIALI ---
            if "special_event_played" in changes:
                current_status.setdefault("metadati", {})[
                    "last_special_event_played"
                ] = changes["special_event_played"]

            if "objects" in changes and isinstance(changes["objects"], list):
                current_objects = current_status.get("oggetti_rilevanti",[])
                for obj in changes["objects"]:
                    if obj not in current_objects:
                        current_objects.append(obj)
                current_status["oggetti_rilevanti"] = current_objects

            if "percezione_ambientale" in changes and isinstance(changes["percezione_ambientale"], dict):
                current_status.setdefault("percezione_ambientale", {}).update(changes["percezione_ambientale"])

            if "oggetti_interattivi" in changes and isinstance(changes["oggetti_interattivi"], list):
                # ---[FIX CRITICO] SOSTITUZIONE DIRETTA ---
                # Poiché l'LLM ora è obbligato a copiare gli oggetti esistenti, 
                # la sostituzione diretta permette la distruzione/rimozione degli oggetti.
                current_status["oggetti_interattivi"] = changes["oggetti_interattivi"]

            # --- DINAMICHE DI MONDO ESPANSE (DEEP MERGE) ---
            if "dynamics" in changes:
                dyn = changes["dynamics"]
                meta = current_status.setdefault("metadati", {})

                # [FIX LOOP TEMATICO] Sovrascrittura diretta invece di Deep Merge.
                # Le dinamiche sono transitorie: se l'utente cambia discorso, il passato deve svanire
                # per evitare che i PNG si fissino all'infinito sullo stesso argomento.
                if "psicologia" in dyn:
                    meta["dinamiche_psicologiche"] = dyn["psicologia"]
                if "relazioni" in dyn:
                    meta["dinamiche_relazionali"] = dyn["relazioni"]
                if "obiettivi" in dyn:
                    meta["obiettivi_correnti"] = dyn["obiettivi"]

                if "clima" in dyn:
                    meta["clima_emotivo_globale"] = dyn["clima"]
                if "current_event" in changes:
                    cronaca = meta.setdefault("cronaca_recente",[])
                    timestamp = datetime.now().strftime("%H:%M")
                    cronaca.append(f"[{timestamp}] {changes['current_event']}")
                    if len(cronaca) > 5:
                        cronaca.pop(0)

            # --- ALCOHOLIC ENGINE LOGIC (FIX v91.6) ---
            if "game_update" in changes:
                game_update = changes["game_update"]

                if "game_state" not in current_status.setdefault("metadati", {}):
                    current_status["metadati"]["game_state"] = {
                        "active": True,
                        "turn_player": "Rapunzel",
                        "scores": {
                            char["nome"]: 10
                            for char in current_status.get("personaggi",[])
                        },
                    }
                    # FIX: Usa pg_name dinamico
                    if (
                        pg_name
                        not in current_status["metadati"]["game_state"]["scores"]
                    ):
                        current_status["metadati"]["game_state"]["scores"][pg_name] = 10

                game_state = current_status["metadati"]["game_state"]

                if "point_loss" in game_update:
                    loser = game_update["point_loss"]
                    if loser in game_state["scores"]:
                        game_state["scores"][loser] -= 1
                        print(
                            t(
                                "executor.executor_game_point_loss",
                                user=loser,
                                score=game_state["scores"][loser],
                            )
                        )

                if "drinkers" in game_update and isinstance(
                    game_update["drinkers"], list
                ):
                    for drinker in game_update["drinkers"]:
                        real_key = next(
                            (
                                k
                                for k in game_state["scores"].keys()
                                if k.lower() == drinker.lower()
                            ),
                            None,
                        )
                        if real_key:
                            game_state["scores"][real_key] += 1
                            drinks = game_state["scores"][real_key]
                            print(
                                t(
                                    "executor.executor_game_drink",
                                    user=real_key,
                                    count=drinks,
                                )
                            )

                            # Scala dell'ubriachezza
                            drunk_state = ""
                            if drinks <= 2:
                                drunk_state = t("executor.rpg_drunk_level_1")
                            elif drinks <= 4:
                                drunk_state = t("executor.rpg_drunk_level_2")
                            elif drinks <= 6:
                                drunk_state = t("executor.rpg_drunk_level_3")
                            elif drinks <= 8:
                                drunk_state = t("executor.rpg_drunk_level_4")
                            else:
                                drunk_state = t("executor.rpg_drunk_level_5")

                            target_char = next(
                                (
                                    c
                                    for c in current_status.get("personaggi", [])
                                    if c["nome"] == real_key
                                ),
                                None,
                            )
                            if target_char:
                                # FIX: Merge dello stato invece di sovrascrittura
                                current_state = target_char.get("stato", "Normale")
                                # Rimuovi eventuali vecchi stati di ubriachezza per non accumularli
                                clean_state = (
                                    re.sub(
                                        r"Ubriachezza \(Livello \d+\):.*",
                                        "",
                                        current_state,
                                    )
                                    .strip()
                                    .rstrip(",")
                                )
                                target_char["stato"] = t(
                                    "executor.rpg_drunk_status",
                                    state=clean_state,
                                    level=drinks,
                                    desc=drunk_state,
                                )

                if "new_turn" in game_update:
                    new_player = game_update["new_turn"]
                    game_state["turn_player"] = new_player
                    print(t("executor.executor_game_turn", user=new_player))

            # 2. Aggiornamento Personaggi (Mass Movement Fix)
            if global_location_changed and new_location:
                for char in current_status.get("personaggi",[]):
                    char["luogo"] = new_location
                    char["stato"] = t("executor.just_moved_to", location=new_location)

            # 3. Aggiornamento Dettagli Specifici Personaggi
            if "characters" in changes and isinstance(changes["characters"], dict):
                for char_name, char_changes in changes["characters"].items():
                    target_char = next(
                        (
                            c
                            for c in current_status.get("personaggi", [])
                            if c["nome"].lower() == char_name.lower()
                        ),
                        None,
                    )

                    if target_char:
                        # --- [FIX CRITICO] AGGIORNAMENTO CAMPI OBBLIGATORI ---
                        if "outfit" in char_changes:
                            # SCUDO: Ignora il copia-incolla dell'LLM se c'è stato un cambio globale
                            if not global_outfit_applied:
                                target_char["abbigliamento"] = char_changes["outfit"]
                            
                        if "postura_e_posizione" in char_changes:
                            target_char["postura_e_posizione"] = char_changes["postura_e_posizione"]
                            
                        if "dettagli_sensoriali" in char_changes:
                            target_char["dettagli_sensoriali"] = char_changes["dettagli_sensoriali"]
                            
                        if "oggetti_equipaggiati" in char_changes:
                            target_char["oggetti_equipaggiati"] = char_changes["oggetti_equipaggiati"]

                        # ---[FIX CRITICO] ANTI-LOOP INFINITO SULLO STATO ---
                        # Poiché physical_state e position sono ora obbligatori, 
                        # sovrascriviamo lo stato invece di appendere all'infinito.
                        new_state_parts =[]
                        if "physical_state" in char_changes and char_changes["physical_state"]:
                            new_state_parts.append(char_changes["physical_state"])
                        if "position" in char_changes and char_changes["position"]:
                            new_state_parts.append(char_changes["position"])
                            
                        if new_state_parts:
                            target_char["stato"] = ", ".join(new_state_parts)

                        if "location" in char_changes:
                            # SCUDO: Ignora il copia-incolla dell'LLM se c'è stato un teletrasporto globale
                            if not global_location_changed:
                                target_char["luogo"] = char_changes["location"]

            # --- [FIX 1A] BONIFICA AGNOSTICA SICURA (RICORSIVA SUI VALORI) ---
            # Converte ogni occorrenza del nome reale del PG nel tag {{nome_pg}} SOLO nei valori stringa
            def _agnosticize_values(obj):
                if isinstance(obj, dict):
                    return {k: _agnosticize_values(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return[_agnosticize_values(v) for v in obj]
                elif isinstance(obj, str):
                    return re.sub(rf"\b{re.escape(pg_name)}\b", "{{nome_pg}}", obj)
                else:
                    return obj

            agnostic_status = _agnosticize_values(current_status)
            
            if world_state_ref is None:
                agnostic_json_str = json.dumps(agnostic_status, indent=2, ensure_ascii=False)
                temp_file = status_file_path.with_suffix(".tmp")
                with open(temp_file, "w", encoding="utf-8") as f:
                    f.write(agnostic_json_str)
                os.replace(temp_file, status_file_path)

            return t("executor.agnostic_update_success")
        except Exception as e:
            print(t("executor.executor_partial_update_error", error=e))
            return t("executor.partial_update_error", error=str(e))

    # ---[NUOVO v127.0] AUTO-TOOL GENERATOR ---
    def generate_tool_json_from_connector(
        self, connector_name: str, def_structure: str, prompt: str
    ) -> bool:
        """
        Genera automaticamente il file JSON del tool in src/tools/ basandosi sui metadati del connettore.
        """
        try:
            # Parsing della firma della funzione (def_structure)
            # Esempio: "my_tool(param1: str, param2: int) -> str: Descrizione."
            # Regex robusta che ignora i tipi di ritorno e cattura i gruppi corretti
            match = re.search(r"(\w+)\s*\((.*?)\)(?:.*?:)?\s*(.*)", def_structure)
            if not match:
                print(t("executor.executor_auto_tool_error", definition=def_structure))
                return False

            func_name = match.group(1)
            params_str = match.group(2)
            description = match.group(3) or prompt

            properties = {}
            required = []

            if params_str.strip():
                params = [p.strip() for p in params_str.split(",")]
                for p in params:
                    if ":" in p:
                        p_name, p_type = p.split(":", 1)
                        p_name = p_name.strip()
                        p_type = p_type.strip().lower()

                        json_type = "string"
                        if "int" in p_type or "float" in p_type or "number" in p_type:
                            json_type = "number"
                        elif "bool" in p_type:
                            json_type = "boolean"

                        properties[p_name] = {
                            "type": json_type,
                            "description": t("executor.tool_param_desc", name=p_name),
                        }
                        required.append(p_name)

            tool_json = {
                "type": "function",
                "function": {
                    "name": func_name,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
                "category": "connector",  # Tag per identificarlo come connettore
            }

            # Scrittura file
            tool_path = TOOLS_DIR / f"{func_name}.json"
            with open(tool_path, "w", encoding="utf-8") as f:
                json.dump(tool_json, f, indent=2, ensure_ascii=False)

            print(t("executor.executor_auto_tool_done", name=tool_path.name))

            # Aggiorna cache
            self._scan_and_load_tools()
            return True

        except Exception as e:
            print(t("executor.executor_auto_tool_critical", error=str(e)))
            return False

    def _sterilize_text(self, text: str) -> str:
        if not isinstance(text, str):
            return ""
        return text.encode("ascii", "ignore").decode("ascii")

    def _resolve_path(self, user_path_str: str) -> Path:
        # [FIX LIVELLO 3] Sanitizzazione contro Path Traversal e caratteri illegali OS
        clean_path_str = str(user_path_str).strip().strip('"').strip("'")
        clean_path_str = clean_path_str.replace("..", "") 
        
        # --- [FIX CRITICO DEFINITIVO] SALVATAGGIO PERCORSI ASSOLUTI WINDOWS ---
        # Rimuoviamo i due punti (:) SOLO se non fanno parte di una lettera di unità (es. C:\ o F:\)
        if not re.match(r'^[a-zA-Z]:[\\/]', clean_path_str):
            clean_path_str = clean_path_str.replace(":", "")
            
        clean_path_str = re.sub(r'[<>"|?*]', '', clean_path_str)
        
        user_path = Path(clean_path_str)
        return user_path if user_path.is_absolute() else self.APP_ROOT / user_path

    def _backup_file(self, file_path: Path) -> bool:
        try:
            if file_path.exists() and file_path.is_file():
                backup_dir = file_path.parent / "backups"
                backup_dir.mkdir(exist_ok=True)
                backup_path = (
                    backup_dir
                    / f"{file_path.stem}_{int(time.time())}{file_path.suffix}.bak"
                )
                shutil.copy2(file_path, backup_path)
            return True
        except Exception as e:
            print(t("executor.executor_backup_error", error=str(e)))
            return False

    # --- [NUOVO v112.0] HELPER PER LOOP DI VERIFICA (MODULO B) ---

    def _take_verification_snapshot(
        self, label: str, x: Optional[int] = None, y: Optional[int] = None
    ) -> Optional[Path]:
        """
        Scatta uno screenshot e crea un ritaglio focalizzato attorno alle coordinate (x, y).
        Se x, y sono None, salva lo screenshot intero.
        """
        try:
            timestamp = int(time.time() * 1000)
            filename = f"verify_{label}_{timestamp}.png"
            full_path = self.VERIFICATION_DIR / filename

            # 1. Cattura Schermo Intero
            screenshot = pyautogui.screenshot()
            img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

            # 2. Se abbiamo coordinate, eseguiamo il Cropping Focalizzato (Idea Migliorativa 2)
            if x is not None and y is not None:
                h, w, _ = img.shape
                size = 200  # Raggio del crop (400x400 totale)

                # Calcolo limiti con clamp per non uscire dallo schermo
                y1, y2 = np.clip([y - size, y + size], 0, h)
                x1, x2 = np.clip([x - size, x + size], 0, w)

                img = img[int(y1) : int(y2), int(x1) : int(x2)]
                # Aggiungiamo un piccolo mirino rosso al centro del crop per l'LLM
                center_x, center_y = int(x - x1), int(y - y1)
                cv2.drawMarker(
                    img, (center_x, center_y), (0, 0, 255), cv2.MARKER_CROSS, 20, 2
                )

            cv2.imwrite(str(full_path), img)
            return full_path
        except Exception as e:
            print(t("executor.err_snapshot", label=label, error=e))
            return None

    def _quick_visual_diff(
        self, path_pre: Path, path_post: Path, threshold: float = 1.0
    ) -> bool:
        """
        Confronto matematico rapido (MSE) tra due immagini (Idea Migliorativa 1).
        Restituisce True se è stato rilevato un cambiamento significativo.
        """
        try:
            img1 = cv2.imread(str(path_pre))
            img2 = cv2.imread(str(path_post))

            if img1 is None or img2 is None:
                return True  # Nel dubbio, chiedi al Brain
            if img1.shape != img2.shape:
                return True  # Dimensioni diverse = cambiamento

            # Calcolo Mean Squared Error
            err = np.sum((img1.astype("float") - img2.astype("float")) ** 2)
            err /= float(img1.shape[0] * img1.shape[1])

            has_changed = err > threshold
            print(
                t(
                    "executor.executor_verify_diff_log",
                    err=round(err, 2),
                    threshold=threshold,
                    changed=has_changed,
                )
            )
            return has_changed
        except Exception as e:
            print(t("executor.executor_verify_diff_error", error=str(e)))
            return True

    @demiurge_fallback
    def web_search(self, query: str, num_results: int = 5) -> str:
        print(t("executor.executor_search_active", query=query))
        try:
            with DDGS() as ddgs:
                results = list(
                    ddgs.text(query, region="it-it", max_results=num_results)
                )

            if not results:
                return t("executor.executor_search_no_results")

            formatted_results = "\n\n".join(
                t(
                    "executor.web_search_result",
                    index=i + 1,
                    title=r["title"],
                    url=r["href"],
                    body=self._sterilize_text(r["body"]),
                )
                for i, r in enumerate(results)
            )
            return (
                t("executor.search_results_count", count=len(results))
                + formatted_results
            )
        except IndexError:
            print(t("executor.executor_ddgs_index_error"))
            return t("executor.executor_search_no_results")
        except Exception as e:
            print(t("executor.executor_search_error", error=str(e)))
            # --- FALLBACK DEMIURGO ---
            print(t("executor.executor_search_fallback"))
            return self.demiurge(f"Cerca su Wikipedia: {query}")

    @demiurge_fallback
    def create_session_memory(
        self,
        chat_history: Optional[List[Tuple[str, str]]] = None,
        session_id: str = None,
        cervello: "CervelloTrinitario" = None,
        db_manager: "DatabaseManager" = None,
        ai_name: str = "L'Assistente",
    ) -> str:
        """
        Salva l'intera cronologia della sessione in formato RAW, senza distillazione LLM.[AGGIORNATO FASE 60] Invia il dump RAW direttamente nel Cold Storage (archived=True)
        per non inquinare il RAG Ibrido della Sliding Window.
        """
        if not session_id:
            return "Errore: session_id mancante."

        # Se l'LLM chiama il tool, chat_history è None. La recuperiamo dal DB.
        if chat_history is None and db_manager:
            raw_history = db_manager.get_messages_for_session(session_id)
            chat_history = [(msg["speaker"], msg["content"]) for msg in raw_history]

        if not chat_history:
            return t("executor.session_empty")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_transcript = t(
            "executor.session_raw_header", timestamp=timestamp, id=session_id
        )
        full_transcript += "".join(f"[{u}]: {g}\n" for u, g in chat_history)

        try:
            # Aggiunto flag "archived": True
            self.memory.add_episodic_memory(
                full_transcript,
                metadata={
                    "source": "session_raw",
                    "session_id": session_id,
                    "timestamp": datetime.now().timestamp(),
                    "archived": True,
                },
            )
            return t("executor.session_raw_saved")
        except Exception as e:
            return t("executor.err_save_raw_memory", error=e)

    @demiurge_fallback
    def save_to_memory(self, text: str, session_id: str) -> str:
        try:
            self.memory.add_episodic_memory(
                text, metadata={"source": "session_recap", "session_id": session_id}
            )
            return t("executor.memory_saved")
        except Exception as e:
            return t("executor.err_save_memory", error=e)

    @demiurge_fallback
    def search_in_memory(self, query: str) -> str:
        try:
            results = self.memory.search_library(query) + self.memory.search_memories(
                query
            )
            if not results:
                return t("executor.memory_silent")
            return t("executor.memory_found_intro") + "\n\n".join(
                t("executor.memory_fragment", res=res) for res in results
            )
        except Exception as e:
            return t("executor.err_search_memory", error=e)

    def save_reasoning_bank(self, task: str, trajectory: str):
        """[MODULO 2] Salva una traiettoria di successo dello Swarm nel Vector DB (Ruflo)."""
        if not self.memory:
            return
        try:
            content = f"TASK: {task}\nTRAIETTORIA RISOLUTIVA:\n{trajectory}"
            self.memory.index_core_memory(
                content=content,
                emotion="logica",
                context_name="ReasoningBank",
                keywords=["swarm", "demiurgo", "soluzione", "codice"]
            )
            self.logger.log(t("log.reasoning_bank_saved"), "SYSTEM")
        except Exception as e:
            self.logger.error(f"Errore salvataggio ReasoningBank: {e}")

    def search_reasoning_bank(self, task: str) -> str:
        """[MODULO 2] Cerca se lo Swarm ha già risolto un task simile in passato."""
        if not self.memory:
            return ""
        try:
            results = self.memory.retrieve_relevant_core_memories(task, context_name="ReasoningBank", top_k=1)
            if results:
                self.logger.log(t("log.reasoning_bank_found"), "SYSTEM")
                return results[0]
            return ""
        except Exception as e:
            self.logger.error(f"Errore ricerca ReasoningBank: {e}")
            return ""

    @demiurge_fallback
    def find_files(self, pattern: str) -> str:
        try:
            start_path = self._resolve_path(pattern)
            search_dir, glob_pattern = (
                (start_path.parent, start_path.name)
                if "*" in start_path.name or "?" in start_path.name
                else (start_path, "*")
            )
            matches = sorted(search_dir.rglob(glob_pattern))
            if not matches:
                return t("executor.file_not_found_pattern", pattern=pattern)
            return t("executor.files_found_count", count=len(matches)) + "".join(
                f"- {str(p)}\n" for p in matches
            )
        except Exception as e:
            return t("executor.err_search_file", error=e)

    @demiurge_fallback
    def leggi_contenuto_da_percorso(
        self, path_str: str, cervello: "CervelloTrinitario"
    ) -> str | None:
        if not cervello or not cervello.cuore:
            return t("executor.read_no_brain")
        percorso_glob = self._resolve_path(path_str)
        files = []
        try:
            if percorso_glob.is_file():
                files.append(percorso_glob)
            elif percorso_glob.is_dir():
                files.extend(sorted(percorso_glob.rglob("*.txt")))
            else:
                files.extend(sorted(percorso_glob.parent.glob(percorso_glob.name)))
            if not files:
                return t("executor.read_no_text_found", path=path_str)
            contenuto, tokens, inclusi = [], 0, 0
            for file_path in files:
                try:
                    contenuto_file = file_path.read_text(encoding="utf-8")
                    token_file = len(
                        cervello.cuore.tokenize(contenuto_file.encode("utf-8"))
                    )
                    if tokens + token_file > self.MAX_TOKENS_LETTURA and inclusi > 0:
                        contenuto.append(t("executor.read_limit_reached"))
                        break
                    contenuto.append(
                        t(
                            "executor.start_of_file",
                            path=str(file_path),
                            content=contenuto_file,
                        )
                    )
                    tokens += token_file
                    inclusi += 1
                except Exception as e:
                    contenuto.append(t("executor.err_read_file_content", error=e))
            return "".join(contenuto)
        except Exception as e:
            return t("executor.err_read", error=e)

    @demiurge_fallback
    def sfoglia_percorso_in_sequenza(self, path_str: str):
        print(t("executor.executor_browse_start", path=path_str))
        time.sleep(1)
        percorso_glob = self._resolve_path(path_str)
        files = []
        try:
            if percorso_glob.is_file():
                files.append(percorso_glob)
            elif percorso_glob.is_dir():
                files.extend(sorted(percorso_glob.rglob("*.txt")))
            else:
                files.extend(sorted(percorso_glob.parent.glob(percorso_glob.name)))
            if not files:
                print(t("executor.executor_browse_empty"))
                return
            print(t("executor.executor_browse_found", count=len(files)))
            time.sleep(1)
            for i, file_path in enumerate(files):
                print(
                    t(
                        "executor.executor_browse_file",
                        current=i + 1,
                        total=len(files),
                        file=str(file_path),
                    )
                )
                time.sleep(0.5)
                try:
                    print(file_path.read_text(encoding="utf-8"))
                except Exception as e:
                    print(t("executor.err_print", error=e))
                print(t("executor.executor_browse_end_read"))
                time.sleep(2)
            print(t("executor.executor_browse_end"))
        except Exception as e:
            print(t("executor.executor_browse_error", error=e))

    @demiurge_fallback
    def web_fetch(self, url: str) -> str:
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            for script in soup(["script", "style"]):
                script.decompose()
            text = self._sterilize_text(soup.get_text())
            return t("executor.web_content_title", url=url) + text
        except Exception as e:
            return t("executor.err_web_fetch", error=e)

    @demiurge_fallback
    def search_wikipedia(self, query: str) -> str:
        print(t("executor.executor_wiki_active", query=query))
        try:
            page = wikipedia.page(query, auto_suggest=False, redirect=True)
            summary = self._sterilize_text(
                wikipedia.summary(query, auto_suggest=False, redirect=True)
            )
            return t(
                "executor.wiki_result", title=page.title, summary=summary, url=page.url
            )
        except wikipedia.exceptions.PageError:
            return t("executor.err_wiki_not_found", query=query)
        except wikipedia.exceptions.DisambiguationError as e:
            return t("executor.err_wiki_ambiguous", options=", ".join(e.options[:5]))
        except Exception as e:
            print(t("executor.executor_wiki_error", error=str(e)))
            # --- FALLBACK DEMIURGO ---
            print(t("executor.executor_wiki_fallback"))
            return self.demiurge(f"Cerca su Wikipedia: {query}")

    @demiurge_fallback
    def leggi_documento(self, file_path_str: Union[str, Path]) -> str:
        # --- [FIX CRITICO DEFINITIVO] BLINDATURA PERCORSI ASSOLUTI ---
        # Bypassiamo completamente _resolve_path per evitare che le regex di sicurezza
        # distruggano le lettere di unità di Windows (es. F:\) o i percorsi di rete.
        if isinstance(file_path_str, Path):
            path = file_path_str
        else:
            clean_str = str(file_path_str).strip().strip('"').strip("'")
            path = Path(clean_str)
            if not path.is_absolute():
                path = self.APP_ROOT / path

        if not path.exists():
            self.logger.error(f"Lettura fallita. Il file non esiste fisicamente in: {path.resolve()}")
            return t("executor.err_file_not_found_name", name=path.name)

        suffix = path.suffix.lower()
        text_content = ""

        try:
            if suffix == ".pdf":
                reader = pypdf.PdfReader(str(path))
                for page in reader.pages:
                    text_content += page.extract_text() + "\n"
            elif suffix == ".docx":
                doc = docx.Document(str(path))
                for para in doc.paragraphs:
                    text_content += para.text + "\n"
            elif suffix == ".txt":
                text_content = path.read_text(encoding="utf-8", errors="ignore")
            else:
                return t("executor.err_format_unsupported", suffix=suffix)

            text_content = text_content.strip()
            if not text_content:
                return t("executor.doc_empty")

            # --- [NUOVO v108.0] SMART TRIAGE (DISTILLAZIONE) ---
            # Se il documento è lungo (> 2000 char) e abbiamo il Cervello, distilliamo.
            if len(text_content) > 2000 and self.cervello:
                self._send_toast(t("executor.executor_doc_distillation_toast"), "info")
                print(
                    t("executor.executor_doc_distillation_log", count=len(text_content))
                )

                # Tenta di recuperare la lingua dal profilo utente tramite Guardian (default 'it')
                lang = "it"

                summary = self.cervello.distilla_conoscenza(text_content, lang=lang)

                return f"{t('log.executor_doc_summary_prefix', name=path.name)}\n\n{summary}\n\n{t('log.executor_doc_original_prefix')}\n{text_content[:500]}..."

            return text_content
        except Exception as e:
            print(t("executor.executor_doc_read_error", error=str(e)))
            # --- FALLBACK DEMIURGO ---
            print(t("executor.executor_doc_read_fallback"))
            # [FIX CRITICO] Passiamo il percorso assoluto per evitare che la sandbox del Demiurgo fallisca
            return self.demiurge(f"Leggi il testo contenuto nel file: {str(path.resolve())}")

    @demiurge_fallback
    def fetch_wikipedia_page(
        self, query: str, lang: str = "it"
    ) -> Tuple[str, str] | None:
        """
        Recupera il contenuto completo di una pagina Wikipedia.
        Restituisce (contenuto, url) o None se fallisce.
        """
        print(t("executor.executor_wiki_fetch_active", query=query, lang=lang))
        wikipedia.set_lang(lang)
        try:
            page = wikipedia.page(query, auto_suggest=True, redirect=True)
            content = self._sterilize_text(page.content)
            return content, page.url
        except Exception as e:
            print(t("executor.executor_wiki_fetch_error", lang=lang, error=str(e)))
            return None

    @demiurge_fallback
    def analizza_stato_vitale(self, target: str = "Creatore") -> str:
        """
        [STRUMENTO] Restituisce il report biometrico sensoriale attuale.
        """
        if not self.perception:
            return t("executor.err_perception_inactive")
        # Nota: Il report biometrico attuale è globale (chiunque sia davanti alla cam),
        # quindi il target è nominale per ora, ma lo manteniamo per compatibilità futura.
        return self.perception.get_biometric_report()

    @demiurge_fallback
    def avvia_flashback(
        self, query: str, cervello: "CervelloTrinitario", pg_name: str
    ) -> str:
        """
        [STRUMENTO] Cerca un ricordo e lo ricostruisce in modo immersivo.
        """
        print(t("executor.executor_flashback_active", query=query))
        try:
            # Cerca nelle memorie episodiche
            memorie = self.memory.search_memories(query, top_k=1)
            if not memorie:
                return t("executor.flashback_not_found")

            frammento = memorie[0]
            # Chiede al cervello di ricostruire la scena al presente
            scena_immersiva = cervello.pensa_ricostruzione_memoria(frammento, pg_name)
            return scena_immersiva
        except Exception as e:
            return t("executor.err_flashback_evocation", error=e)

    @demiurge_fallback
    def simula_scenari(
        self,
        obiettivo: str,
        variabili: List[str],
        cervello: "CervelloTrinitario",
        status_file_path: Path,
    ) -> str:
        """
        [STRUMENTO] Esegue una simulazione strategica basata sullo stato attuale.
        Affinato v92.0: Include Analisi delle Dipendenze e Impatto a Lungo Termine.
        """
        print(t("executor.executor_simulation_active", objective=obiettivo))
        try:
            if not status_file_path.exists():
                return t("executor.err_world_state_unavailable")

            with open(status_file_path, "r", encoding="utf-8") as f:
                status_data = json.load(f)

            # Raccoglie contesto profondo (metadati + dinamiche)
            meta = status_data.get("metadati", {})
            contesto_attuale = json.dumps(meta, ensure_ascii=False)

            # Chiede al cervello di generare i tre sentieri con logica di dipendenza
            simulazione = cervello.pensa_simulazione_strategica(
                objective=obiettivo,
                variables=variabili,
                current_context=contesto_attuale,
            )
            return simulazione
        except Exception as e:
            return t("executor.err_advanced_simulation", error=e)

    @demiurge_fallback
    def descrivi_immagine_con_pan_scan(
        self, image_path_str: str, cervello: "CervelloTrinitario"
    ) -> str:
        """
        [AGGIORNATO v115.0] Implementa l'analisi nativa Gemma 3 (Pan-and-Scan).
        Invia l'immagine originale e i crop simultaneamente al modello.
        """
        path = self._resolve_path(image_path_str)

        # Se il processore non è attivo, fallback su visione standard
        if not self.image_processor:
            return cervello.descrivi_immagine(path)

        # Ottieni lista di immagini (Originale + Crops)
        images_list, message = self.image_processor.process_image(path)

        # Invia tutto il pacchetto al cervello in una sola chiamata
        # Il cervello ora sa gestire una lista di numpy array
        descrizione_completa = cervello.descrivi_immagine(images_list)

        return (
            f"{message}\n\n{t('executor.visual_analysis_title')}{descrizione_completa}"
        )

    @demiurge_fallback
    def analizza_video(
        self, video_path_str: str, user_query: str = "Descrivi cosa succede nel video."
    ) -> str:
        """
        [STRUMENTO] Analizza un file video estraendo frame sequenziali per comprendere movimento e azione.
        """
        if not self.cervello:
            return t("executor.err_brain_unavailable")

        path = self._resolve_path(video_path_str)
        self._send_toast(
            t("executor.executor_video_analysis_toast", name=path.name), "info"
        )

        try:
            if self.cervello.is_gemma_4:
                # --- GEMMA 4 NATIVE VIDEO SUPPORT ---
                # Invia direttamente il file video al modello senza estrarre i frame
                analisi = self.cervello.analizza_video(path, user_query=user_query)
            else:
                # 1. Estrazione Frame (Legacy)
                frames = self.video_processor.extract_frames(
                    str(path), fps=1, max_frames=10
                )
                if not frames:
                    return t("executor.err_no_frame_extracted")

                # 2. Analisi Neurale Temporale
                analisi = self.cervello.analizza_video(frames, user_query=user_query)

            return f"{t('log.executor_video_analysis_prefix', name=path.name)}\n\n{analisi}"

        except Exception as e:
            return t("executor.err_video_analysis", error=e)

    @demiurge_fallback
    def confronta_immagini(
        self,
        path1_str: str,
        path2_str: str,
        user_query: str = "Quali sono le differenze tra queste due immagini?",
    ) -> str:
        """
        [STRUMENTO] Esegue un confronto visivo tra due immagini.
        Utile per trovare differenze, analizzare cambiamenti o confrontare versioni di un file.
        """
        if not self.cervello:
            return t("executor.err_brain_unavailable")

        p1 = self._resolve_path(path1_str)
        p2 = self._resolve_path(path2_str)

        if not p1.exists() or not p2.exists():
            return t("executor.err_files_not_exist", path1=path1_str, path2=path2_str)

        self._send_toast(t("executor.executor_compare_toast"), "info")

        try:
            # Carica le immagini
            img1 = cv2.imread(str(p1))
            img2 = cv2.imread(str(p2))

            if img1 is None or img2 is None:
                return t("executor.err_read_image_files")

            # Invia la lista al cervello per l'analisi multimodale nativa
            # Il cervello riceve [img1, img2] e il prompt di confronto
            analisi = self.cervello.descrivi_immagine([img1, img2], lang="it")

            return f"{t('log.executor_compare_prefix')}\n\n{analisi}"

        except Exception as e:
            return t("executor.err_visual_comparison", error=e)

    @demiurge_fallback
    def crea_da_immagini(
        self,
        image_paths: List[str],
        user_query: str = "Scrivi una storia ispirata a queste immagini.",
    ) -> str:
        """
        [STRUMENTO] Genera contenuti creativi (storie, poesie, scenari) basandosi su una sequenza di immagini.
        """
        if not self.cervello:
            return t("executor.err_brain_unavailable")

        self._send_toast(t("executor.executor_creative_toast"), "info")

        try:
            images_to_process = []
            for path_str in image_paths:
                p = self._resolve_path(path_str)
                if p.exists():
                    img = cv2.imread(str(p))
                    if img is not None:
                        images_to_process.append(img)

            if not images_to_process:
                return t("executor.err_no_valid_image")

            # Invocazione del metodo creativo nel cervello
            creazione = self.cervello.pensa_creativo_multimodale(
                images_to_process, user_query=user_query, lang="it"
            )

            return f"{t('log.executor_creative_prefix')}\n\n{creazione}"

        except Exception as e:
            return t("executor.err_multimodal_creation", error=e)

    # --- [NUOVO v116.2] ORECCHIO EMPATICO (NATIVE AUDIO TOOLS) ---
    @demiurge_fallback
    def analizza_emozione_voce(self) -> str:
        """
        [STRUMENTO] Analizza l'ultimo frammento audio ricevuto per rilevare lo stato emotivo dell'utente.
        Aggiorna i vettori di tensione e stanchezza nel Cuore basandosi sul tono della voce.
        """
        if not self.cervello or not self.perception:
            return t("executor.err_sensory_systems_not_ready")

        audio_data = self.perception.get_last_audio_data()
        if not audio_data:
            return t("executor.executor_voice_emo_error")

        self._send_toast(t("executor.executor_voice_emo_toast"), "info")

        try:
            # 1. Salvataggio temporaneo del buffer audio
            temp_filename = f"voice_analysis_{int(time.time())}.wav"
            temp_path = self.TEMP_AUDIO_DIR / temp_filename
            with open(temp_path, "wb") as f:
                f.write(audio_data.get_wav_data())

            # 2. Calcolo durata
            duration = len(audio_data.get_raw_data()) / (
                audio_data.sample_rate * audio_data.sample_width
            )

            # 3. Analisi Neurale Nativa
            analisi = self.cervello.analizza_audio(
                temp_path,
                duration,
                user_query="Analizza il tono di questa voce. È teso, calmo, felice o stanco? Suggerisci variazioni per il mio nucleo emotivo.",
            )

            return f"{t('log.executor_voice_emo_prefix')}\n\n{analisi}"

        except Exception as e:
            return t("executor.err_deep_listening", error=e)

    @demiurge_fallback
    def interprete_multilingua(self, lingua_target: str = "italiano") -> str:
        """
        [STRUMENTO] Traduce l'ultimo frammento audio ricevuto nella lingua specificata (AST).
        Utile per comprendere utenti o PNG che parlano lingue straniere.
        """
        if not self.cervello or not self.perception:
            return t("executor.err_sensory_systems_not_ready")

        audio_data = self.perception.get_last_audio_data()
        if not audio_data:
            return t("executor.translate_no_audio")

        self._send_toast(
            t("executor.executor_translate_toast", lang=lingua_target), "info"
        )

        try:
            temp_filename = f"translation_{int(time.time())}.wav"
            temp_path = self.TEMP_AUDIO_DIR / temp_filename
            with open(temp_path, "wb") as f:
                f.write(audio_data.get_wav_data())

            duration = len(audio_data.get_raw_data()) / (
                audio_data.sample_rate * audio_data.sample_width
            )

            analisi = self.cervello.analizza_audio(
                temp_path,
                duration,
                user_query=f"Trascrivi questo audio e traducilo accuratamente in {lingua_target}.",
            )

            return f"{t('log.executor_translate_prefix')}\n\n{analisi}"

        except Exception as e:
            return t("executor.err_translation", error=e)

    # --- [NUOVO v116.7] MAPPATURA BIO-EMOTIVA DELLA VOCE ---
    def _calcola_parametri_voce(self) -> Tuple[float, float]:
        """
        Analizza lo stato del Cuore e restituisce (speed, pitch).
        Speed: 1.0 è normale.
        Pitch: 1.0 è normale (verrà convertito in semitoni per FFmpeg).
        """
        speed = 1.0
        pitch = 1.0  # Moltiplicatore base

        if not self.heart:
            return speed, pitch

        s = self.heart.state

        # 1. Analisi RISPETTO (Freddezza vs Calore)
        if s["rispetto"] < 30:
            pitch -= 0.15  # Voce più cupa/fredda
            speed -= 0.05  # Più lenta/distaccata
        elif s["rispetto"] > 80:
            pitch += 0.05  # Leggermente più alta/rispettosa

        # 2. Analisi AFFETTO (Dolcezza)
        if s["affetto"] > 85:
            speed += 0.05  # Più vivace
            pitch += 0.05  # Più dolce/acuta
        elif s["affetto"] < 20:
            speed -= 0.10  # Più piatta/monotona

        # 3. Analisi ECCITAZIONE (Energia)
        if s["eccitazione"] > 80:
            speed += 0.15  # Respiro affannoso/veloce
            pitch += 0.10  # Molto più acuta

        # 4. Analisi STANCHEZZA (Entropia)
        if s["stanchezza_mentale"] > 75:
            speed -= 0.20  # Molto lenta
            pitch -= 0.10  # Più bassa/stanca

        # Limiti di sicurezza per evitare distorsioni aliene
        speed = max(0.7, min(1.5, speed))
        pitch = max(0.7, min(1.3, pitch))

        return round(speed, 2), round(pitch, 2)

    # [FIX v118.5] Rimosso demiurge_fallback: genera_voce deve restituire un path o None, non testo narrativo.
    def genera_voce(
        self,
        text: str,
        intent: str,
        preferred_voice: str = "",
        preferred_lang_code: str = "",
        engine_override: str = "",
    ) -> Optional[str]:
        """
        [AGGIORNATO v118.5] Generazione vocale duale con Hot-Reload e Blindatura.
        Sincronizza la configurazione prima di scegliere il motore per evitare conflitti di voci.
        [AGGIORNATO v119.0] Supporto esplicito per preferred_lang_code disaccoppiato.
        """
        # --- [FIX CRITICO PERFORMANCE] RIMOZIONE RELOAD_CONFIG ---
        # Rimosso self.guardian.reload_config() che causava un lag infernale (I/O disco)
        # prima di ogni singola frase pronunciata dall'Avatar.

        # 1. Recupero configurazione motore attivo (dalla RAM del Guardian)
        tts_config = self.guardian.get_tts_engine_config() or {}
        active_engine = engine_override if engine_override else tts_config.get("active_engine", "kokoro")

        self.logger.log(
            t("executor.executor_tts_engine_log", engine=active_engine.upper()), "DEBUG"
        )

        output_filename = f"speech_{int(time.time())}_{uuid.uuid4().hex[:8]}.wav"
        output_path = self.TEMP_AUDIO_DIR / output_filename

        # --- [FIX CRITICO] RICONOSCIMENTO ROBUSTO VOCI VIBEVOICE VS KOKORO ---
        # Le voci VibeVoice usano il trattino (es. it-Gemma_woman.pt), Kokoro usa l'underscore (es. if_sara.pt)
        is_vibevoice_format = "-" in preferred_voice and "_" in preferred_voice

        # --- CASO A: VIBEVOICE (API CALL) ---
        # Proviamo VibeVoice SOLO se il motore è vibevoice E la voce sembra essere per VibeVoice (o se non c'è voce)
        if active_engine == "vibevoice" and (is_vibevoice_format or not preferred_voice):
            vv_url = tts_config.get("vibevoice_url", "http://localhost:8880").rstrip(
                "/"
            )
            # Normalizzazione nome voce (VibeVoice non usa .pt)
            voice_name = (
                preferred_voice.replace(".pt", "") if preferred_voice else "Carter"
            )

            # --- [FIX CRITICO] AUTO-START VIBEVOICE SERVER (LAZY LOADING) ---
            server_is_up = False
            try:
                requests.get(f"{vv_url}/health", timeout=1)
                server_is_up = True
            except requests.exceptions.ConnectionError:
                self.logger.log("Server VibeVoice offline. Avvio a freddo in corso (richiederà alcuni secondi)...", "SYSTEM")
                self._send_toast("Avvio motore VibeVoice in corso...", "info")
                vv_script = self.APP_ROOT / "tts_engine" / "VibeVoice" / "vibevoice_realtime_openai_api.py"
                
                # --- [FIX CRITICO VIBEVOICE] Risoluzione del venv dedicato ---
                if os.name == "nt":
                    vv_python = self.APP_ROOT / "tts_engine" / "VibeVoice" / "venv" / "Scripts" / "python.exe"
                else:
                    vv_python = self.APP_ROOT / "tts_engine" / "VibeVoice" / "venv" / "bin" / "python"
                    
                if not vv_python.exists():
                    self.logger.warning("Venv di VibeVoice non trovato. Tento fallback su sys.executable...")
                    vv_python = sys.executable
                
                if vv_script.exists():
                    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                    env = os.environ.copy()
                    # Avvia il server in background usando il SUO python.exe
                    subprocess.Popen([str(vv_python), str(vv_script), "--port", "8880"], creationflags=creationflags, env=env, cwd=str(vv_script.parent))
                    
                    # Polling per attendere che il server sia pronto (Max 120s per caricare in VRAM)
                    for attempt in range(120):
                        try:
                            # --- [FIX CRITICO VIBEVOICE] RIPRISTINO ENDPOINT CORRETTO ---
                            # Il server FastAPI di VibeVoice espone correttamente /health
                            if requests.get(f"{vv_url}/health", timeout=2).status_code == 200:
                                server_is_up = True
                                self.logger.log("Server VibeVoice operativo e caricato in VRAM.", "SYSTEM")
                                break
                        except:
                            time.sleep(1)
                            
            if not server_is_up:
                self.logger.error("Timeout avvio VibeVoice. Il server non risponde. Fallback su Kokoro.")
                active_engine = "kokoro" # Forza il fallback
            else:
                self._send_toast(
                    t("executor.executor_tts_vibevoice_toast", voice=voice_name), "info"
                )

                payload = {"input": text, "voice": voice_name, "response_format": "wav"}

                try:
                    # [FIX CRITICO] Aumentato timeout da 30 a 20 secondi per testi lunghi
                    response = requests.post(
                        f"{vv_url}/v1/audio/speech", json=payload, timeout=720
                    )
                    if response.status_code == 200:
                        with open(output_path, "wb") as f:
                            f.write(response.content)
                        self.logger.log(
                            t("executor.executor_tts_vibevoice_done", file=output_filename),
                            "DEBUG",
                        )
                        return str(output_path)
                    else:
                        self.logger.error(
                            t(
                                "executor.executor_tts_vibevoice_error",
                                code=response.status_code,
                            )
                        )
                        active_engine = "kokoro" # Forza fallback se l'API dà errore
                except Exception as e:
                    self.logger.error(
                        t("executor.executor_tts_vibevoice_conn_error", error=str(e))
                    )
                    active_engine = "kokoro" # Forza fallback

        # --- CASO B: KOKORO (SUBPROCESS - LOGICA ORIGINALE) ---
        # Se siamo qui, o il motore è Kokoro, o la voce era per Kokoro, o VibeVoice ha fallito

        # Sanitizzazione rigorosa del lang_code per Kokoro
        kokoro_lang_map = {"it": "i", "en": "a", "es": "e", "fr": "f", "pt": "p", "ja": "j", "zh": "z", "hi": "h"}
        clean_lang = preferred_lang_code[:2].lower() if preferred_lang_code else "i"
        safe_kokoro_lang = kokoro_lang_map.get(clean_lang, "i")

        # Se la voce preferita è nel formato VibeVoice, o non è un .pt, dobbiamo usare un fallback per Kokoro
        if not preferred_voice.endswith(".pt") or is_vibevoice_format:
            self.logger.log(t("executor.executor_tts_kokoro_voice_warn"), "WARNING")
            # Fallback intelligente basato sulla lingua richiesta
            voice = "if_sara.pt" if safe_kokoro_lang == "i" else "af_bella.pt"
            lang = safe_kokoro_lang
        else:
            # La voce preferita è già un formato Kokoro valido, usiamola!
            voice = preferred_voice
            lang = safe_kokoro_lang

        if not self.KOKORO_PYTHON_EXE.exists():
            self.logger.error(
                t(
                    "executor.executor_tts_kokoro_error",
                    path=str(self.KOKORO_PYTHON_EXE),
                )
            )
            return None

        command = [
            str(self.KOKORO_PYTHON_EXE),
            str(self.VOCE_DIVINA_SCRIPT),
            "--text",
            text,
            "--voice",
            voice,
            "--lang",
            lang, # Usiamo la lingua sanitizzata
            "--output-path",
            str(output_path),
        ]

        try:
            # [FIX] Aggiunto text=True per catturare e stampare il vero errore (stderr)
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120 # [FIX CRITICO] Timeout di sicurezza per evitare freeze infiniti
            )
            return str(output_path)
        except subprocess.TimeoutExpired as e:
            self.logger.error(f"[KOKORO ERROR] Timeout scaduto (120s): {e}")
            return None
        except subprocess.CalledProcessError as e:
            self.logger.error(f"[KOKORO ERROR] Exit {e.returncode}: {e.stderr}")
            return None
        except Exception as e:
            self.logger.error(t("executor.executor_tts_kokoro_fail", error=str(e)))
            return None

    @demiurge_fallback
    def create_reminder(
        self, session_id: str, content: str, trigger_in_minutes: int
    ) -> str:
        """
        [NUOVO] Wrapper semplificato per la creazione di promemoria rapidi.
        """
        now = datetime.now()
        trigger_dt = now + timedelta(minutes=trigger_in_minutes)

        return self.create_event_and_reminder(
            session_id=session_id,
            event_name=t("executor.reminder_quick_title"),
            event_timestamp_iso=trigger_dt.isoformat(),
            notes=content,
            reminder_timestamp_iso=trigger_dt.isoformat(),
            recurrence_rule="none",
        )

    @demiurge_fallback
    def export_package(
        self, export_type: str, avatar_names: str, lore_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        [NUOVO] Implementa l'esportazione di Anime e Mondi in archivi .zip.
        """
        try:
            timestamp = int(time.time())
            zip_filename = f"export_{export_type}_{timestamp}.zip"
            zip_path = EXPORTS_PATH / zip_filename

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                # Esporta Anime
                for name in avatar_names.split(","):
                    name = name.strip()
                    avatar_dir = AVATARS_PATH / name.lower()
                    if avatar_dir.exists():
                        for root, _, files in os.walk(avatar_dir):
                            for file in files:
                                file_path = Path(root) / file
                                zipf.write(file_path, file_path.relative_to(APP_ROOT))

                    soul_file = AVATARS_PATH / "ai_souls" / f"{name.capitalize()}.json"
                    if soul_file.exists():
                        zipf.write(soul_file, soul_file.relative_to(APP_ROOT))

                # Esporta Lore
                if export_type == "world" and lore_name:
                    lore_dir = LORE_PATH / lore_name
                    if lore_dir.exists():
                        for root, _, files in os.walk(lore_dir):
                            for file in files:
                                file_path = Path(root) / file
                                zipf.write(file_path, file_path.relative_to(APP_ROOT))

            return {"success": True, "path": str(zip_path)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @demiurge_fallback
    def import_package(
        self, zip_path_str: str, overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        [NUOVO] Implementa l'importazione di pacchetti .zip con gestione conflitti.
        """
        try:
            zip_path = Path(zip_path_str)
            with zipfile.ZipFile(zip_path, "r") as zipf:
                if not overwrite:
                    for member in zipf.namelist():
                        if (APP_ROOT / member).exists():
                            return {
                                "success": False,
                                "error": t(
                                    "executor.err_conflict_detected", member=member
                                ),
                            }
                zipf.extractall(APP_ROOT)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- ALIAS PER TOOL USE (COMPATIBILITÀ GROQ) ---
    @demiurge_fallback
    def read_file(self, path_str: str) -> str:
        """Alias per leggi_contenuto_da_percorso, conforme allo schema JSON."""
        # Nota: leggi_contenuto_da_percorso richiede 'cervello' per contare i token.
        # Qui facciamo una lettura diretta semplice per il Tool Use.
        try:
            target_path = self._resolve_path(path_str)
            if not target_path.exists():
                return t("executor.err_file_not_found_path", path=path_str)
            if target_path.is_dir():
                return t("executor.err_is_directory", path=path_str)

            content = target_path.read_text(encoding="utf-8", errors="replace")
            return content
        except Exception as e:
            return t("executor.err_read_file", error=e)

    @demiurge_fallback
    def list_files(self, pattern: str) -> str:
        """Alias per find_files, conforme allo schema JSON."""
        return self.find_files(pattern)

    # --- [NUOVO v99.0] NARCISO DIGITALE (AUTOCOSCIENZA VISIVA) ---
    @demiurge_fallback
    def get_avatar_visual_description(self, avatar_name: str) -> str:
        """
        [STRUMENTO] Legge il DNA dell'Avatar (JSON) e restituisce una descrizione visiva densa.
        Fondamentale per la generazione di selfie coerenti.
        """
        try:
            # Normalizza il nome (es. "Gemma" -> "Gemma.json")
            # Cerca in avatars/ai_souls/
            soul_path = AVATARS_PATH / "ai_souls" / f"{avatar_name.capitalize()}.json"

            if not soul_path.exists():
                # Fallback: cerca in lore/RPG/PNG se non è un'anima principale
                # Questo è complesso perché non sappiamo quale RPG è attivo qui.
                # Per ora limitiamoci alle Anime Principali.
                return t("executor.err_soul_file_not_found", name=avatar_name)

            with open(soul_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Estrazione Dati Fisici
            fisico = data.get("dati_fisici_ed_estetici", {})
            desc = fisico.get("descrizione_visiva", t("executor.no_description"))
            corp = fisico.get("corporatura", t("executor.normal_body"))

            # Estrazione Dettagli Intimi (per realismo anatomico se richiesto)
            intimi = fisico.get("dettagli_intimi", {})
            seno = intimi.get("seno", "")

            # Costruzione Stringa Densa
            visual_dna = t(
                "executor.visual_dna_format", desc=desc, corp=corp, seno=seno
            )

            return visual_dna

        except Exception as e:
            return t("executor.err_read_visual_dna", error=e)

    # ---[NUOVO v104.0] HEART SURGERY TOOLS ---
    # [FIX] Rimosso demiurge_fallback
    def read_heart_metrics(self) -> str:
        """[STRUMENTO] Legge lo stato emotivo grezzo dal file heart.json.
        Utile per introspezione profonda o debug.
        """
        try:
            if not HEART_FILE_PATH.exists():
                return t("executor.err_heart_file_not_exist")

            with open(HEART_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            return t(
                "executor.heart_metrics",
                data=json.dumps(data, indent=2, ensure_ascii=False),
            )
        except Exception as e:
            return t("executor.err_read_heart", error=e)

    # [FIX] Rimosso demiurge_fallback
    def override_heart_metric(self, key: str, value: int) -> str:
        """
        [STRUMENTO] Forza manualmente un valore emotivo nel file heart.json.
        ATTENZIONE: Richiede riavvio o reload per avere effetto immediato se il sistema è in cache.
        """
        try:
            if not HEART_FILE_PATH.exists():
                return t("executor.err_heart_file_missing")

            with open(HEART_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            if key not in data:
                return t(
                    "executor.err_key_not_found_heart", key=key, keys=list(data.keys())
                )

            old_val = data[key]
            data[key] = value
            data[
                "ultimo_aggiornamento"
            ] = time.time()  # Aggiorna timestamp per evitare decay immediato

            with open(HEART_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            return t("executor.heart_updated", key=key, old=old_val, new=value)
        except Exception as e:
            return t("executor.err_heart_surgery", error=e)

    # --- [AGGIORNATO v108.0] GESTIONE SKILLS (JSON PROTOCOL) ---

    def scan_skills(self) -> List[Dict[str, Any]]:
        """
        Scansiona la cartella skills per file .json.
        Restituisce i metadati per la UI.
        """
        skills = []
        try:
            # [FIX] Ora cerca in SKILLS_DIR, non in CONNECTORS_PATH
            if not SKILLS_DIR.exists():
                print(t("executor.executor_skills_dir_not_found", dir=SKILLS_DIR))
                return []

            json_files = list(SKILLS_DIR.glob("*.json"))
            print(
                t(
                    "executor.executor_skills_found",
                    count=len(json_files),
                    dir=SKILLS_DIR,
                )
            )

            for f in json_files:
                try:
                    with open(f, "r", encoding="utf-8") as file:
                        data = json.load(file)

                    # [FIX v108.4] Caricamento Ultra-Difensivo (Anti-KeyError)
                    # Estraiamo i dati garantendo la presenza di tutte le chiavi richieste dai vari moduli

                    # Supporto formato Google Native
                    func_data = data.get("function", data)
                    tool_name = func_data.get("name", f.stem)
                    category = data.get("category", "skill")

                    # [FIX UI] Estrazione descrizione profonda per le Skills
                    props = func_data.get("parameters", {}).get("properties", {})
                    task_desc = props.get("task_description", {}).get("description", "")
                    final_desc = (
                        task_desc
                        if task_desc
                        else func_data.get(
                            "description", t("executor.no_description_provided")
                        )
                    )

                    skills.append(
                        {
                            "filename": f.name,
                            "name": tool_name,
                            "category": category,
                            "description": final_desc,
                            "parameters": func_data.get(
                                "parameters", {"type": "object", "properties": {}}
                            ),
                            "triggers": data.get(
                                "triggers", [tool_name.replace("_", " ")]
                            ),  # Default: nome del tool
                            "gbnf_grammar": data.get("gbnf_grammar", ""),
                        }
                    )
                except Exception as e:
                    print(
                        t("executor.executor_skills_parse_error", file=f.name, error=e)
                    )

            print(t("executor.executor_skills_loaded", count=len(skills)))
            return skills
        except Exception as e:
            print(t("executor.executor_skills_scan_error", error=e))
            return []

    @demiurge_fallback
    def read_skill(self, skill_name: str) -> str:
        """
        [STRUMENTO] Legge la definizione di una Skill (JSON) dato il suo nome.
        """
        try:
            target_file = SKILLS_DIR / f"{skill_name}.json"

            if not target_file.exists():
                return t("executor.skill_not_found", name=skill_name, dir=SKILLS_DIR)

            content = target_file.read_text(encoding="utf-8")
            return t("executor.skill_definition", name=skill_name, content=content)

        except Exception as e:
            return t("executor.skill_read_error", error=str(e))

    def save_skill(self, filename: str, content: str) -> bool:
        """
        Salva o aggiorna un file Skill (.json).
        Il content deve essere una stringa JSON valida.
        """
        try:
            if not filename.endswith(".json"):
                filename += ".json"
            path = SKILLS_DIR / filename

            # 1. Validazione JSON
            try:
                json_data = json.loads(content)
                # Forza la categoria skill
                json_data["category"] = "skill"
                content = json.dumps(json_data, indent=2, ensure_ascii=False)
            except json.JSONDecodeError as e:
                print(t("executor.executor_skills_json_error", file=filename, error=e))
                return False

            # 2. Backup se il file esiste già (Rito del Sacrario)
            if path.exists():
                self._backup_file(path)

            # 3. Scrittura persistente
            path.write_text(content, encoding="utf-8")
            self.logger.log(t("executor.skill_save_success", name=filename), "SKILL")

            # Aggiorna cache tool
            self._scan_and_load_tools()

            return True
        except Exception as e:
            print(t("executor.executor_skills_save_error", error=e))
            return False

    def delete_skill(self, filename: str) -> bool:
        """Elimina un file Skill (.json)."""
        try:
            path = SKILLS_DIR / filename
            if path.exists() and path.suffix == ".json":
                os.remove(path)
                # Aggiorna cache tool
                self._scan_and_load_tools()
                self.logger.log(
                    t("executor.skill_delete_success", name=filename), "SKILL"
                )
                return True
            return False
        except Exception as e:
            print(t("executor.executor_skills_delete_error", error=e))
            self.logger.error(t("executor.skill_delete_fail", name=filename))
            return False
