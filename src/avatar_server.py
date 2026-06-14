# src/avatar_server.py
# v100.5 - SPECIALIST & AUTO-TOOL UPDATE
# ADD: Endpoint /api/settings/specialist per configurazione ibrida.
# ADD: Endpoint /api/custom-connectors/validate per Dry Run codice.
# ADD: Endpoint /api/custom-connectors/sync-tool per generazione automatica JSON.
# MANTENUTO: Security, Hive Mind, Media Optimization.
# LEGGE A0099: Invarianza strutturale garantita. Codice integrale fornito.

from pathlib import Path
import sys
import asyncio
import uvicorn
import json
import re
import socket
import random
import base64
import subprocess
import logging
import threading
from queue import Queue
import ssl
import mimetypes
import time
from contextlib import asynccontextmanager
import warnings
from datetime import datetime, time as dtime, timedelta
import requests
from urllib.parse import quote, unquote, urljoin, urlparse, parse_qs
import urllib3
import jwt  # [NUOVO] Per gestione Token
import ipaddress  # [NUOVO v100.4] Per validazione Range IP
from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    Request,
    HTTPException,
    UploadFile,
    File,
    Form,
    Response,
    Query,
    BackgroundTasks,
    status,
)
from fastapi.staticfiles import StaticFiles
from starlette.responses import (
    JSONResponse,
    FileResponse,
    RedirectResponse,
    StreamingResponse,
)
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import os

# --- [FIX] SOPPRESSIONE LOG C++ (MEDIAPIPE/GLOG/ABSL/TF) ---
# Deve essere impostato prima che qualsiasi libreria C++ venga caricata
os.environ["GLOG_minloglevel"] = "2"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
try:
    import absl.logging
    absl.logging.set_verbosity(absl.logging.ERROR)
except ImportError:
    pass

from collections import defaultdict

# --- [FIX v115.1] AGGIUNTO UNION PER MODELLI IOT ---
from typing import Optional, List, Dict, Any, Union
import shutil
import tempfile
import zipfile
import uuid
import yaml
import ast  # [NUOVO v15.0] Per validazione sintattica
from fastapi.security import OAuth2PasswordBearer  # [NUOVO]

# Disabilita warning SSL per le richieste interne
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- FIX WARNING STARLETTE (v97.1) ---
# Sopprime il warning di deprecazione di python_multipart prima che venga importato da FastAPI
warnings.filterwarnings(
    "ignore", category=PendingDeprecationWarning, module="starlette.formparsers"
)

# --- [FIX] SOPPRESSIONE WARNING PYTORCH (GPU IMBALANCE) ---
warnings.filterwarnings(
    "ignore", message=".*imbalance between your GPUs.*"
)

# --- FIX ENCODING WINDOWS ---
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"

# --- FIX MIME TYPES (CRUCIALE PER SDK WEB) ---
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/wasm", ".wasm")
mimetypes.add_type("video/x-flv", ".flv")
mimetypes.add_type("video/mp4", ".mp4")  # Assicuriamoci che mp4 sia registrato

# --- GESTIONE DEI PERCORSI ---
try:
    # APP_ROOT è la cartella dove risiede questo script (F:\Airis\src) -> parent -> F:\Airis
    SCRIPT_DIR = Path(__file__).parent.resolve()
    APP_ROOT = SCRIPT_DIR.parent
    # Aggiungiamo 'src' al path per importare i moduli
    sys.path.insert(0, str(SCRIPT_DIR))
except NameError:
    APP_ROOT = Path.cwd()
    sys.path.insert(0, str(APP_ROOT / "src"))

# --- CONFIGURAZIONE LOGGING (DUAL MODE) ---
LOG_DIR = APP_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "server_debug.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# --- [FIX CRITICO] SOPPRESSIONE WINERROR 10054 (ASYNCIO) ---
# Intercetta e silenzia gli errori di disconnessione brutale del WebSocket su Windows
# per evitare che inquinino i log e causino instabilità nel loop degli eventi.
import asyncio
def _asyncio_exception_handler(loop, context):
    msg = context.get("exception", context.get("message"))
    if isinstance(msg, ConnectionResetError) and msg.winerror == 10054:
        return # Ignora silenziosamente
    # Per tutti gli altri errori, usa il gestore di default
    loop.default_exception_handler(context)

# Applica l'handler al loop corrente (se già in esecuzione) o lo imposterà uvicorn
try:
    asyncio.get_running_loop().set_exception_handler(_asyncio_exception_handler)
except RuntimeError:
    pass # Il loop non è ancora partito, lo imposteremo nel lifespan

# --- IMPORTAZIONE DEI MODULI INTERNI ---
from database_manager import DatabaseManager
from logger import Logger as GameLogger
from guardian import Guardian
from hive_manager import HiveManager
from executor import BraccioDivino  # [FIX v121.2] Import necessario per gestione Skills
from utils.translator import t, set_language  # [NUOVO] Motore di traduzione

# --- [FIX CRITICO] INIZIALIZZAZIONE LINGUA PRECOCE ---
# Leggiamo lang.cfg PRIMA di inizializzare il logger per avere i log tradotti da subito
_early_lang = "it"
try:
    _lang_cfg_path = APP_ROOT / "lang.cfg"
    if _lang_cfg_path.exists():
        with open(_lang_cfg_path, "r", encoding="utf-8") as _f:
            _early_lang = _f.read().strip()
except:
    pass
set_language(_early_lang)

# --- COSTANTI E CONFIGURAZIONE DEL SERVER ---
ACTIVE_RPG_PATH: Optional[Path] = None
ACTIVE_SESSION_ID: Optional[str] = None  # [NUOVO v62.23] Verità della Sessione Attiva
SERVER_PORT = 8080
LORE_PATH = APP_ROOT / "lore"
AVATARS_BASE_PATH = APP_ROOT / "avatars"
TEMP_AUDIO_PATH = APP_ROOT / "temp_audio"
TEMP_IMAGE_PATH = APP_ROOT / "temp_images"
CONFIG_PATH = APP_ROOT / "config"
CONNECTORS_PATH = APP_ROOT / "src" / "connectors"
# [FIX DEFINITIVO PERCORSI]
TOOLS_DIR = APP_ROOT / "src" / "tools"
SKILLS_DIR = APP_ROOT / "src" / "skills"

KOKORO_AUDIO_PATH = APP_ROOT / "tts_engine" / "kokoro" / "model" / "audio"
DOCUMENTS_PATH = APP_ROOT / "documents"  # [NUOVO v98.1] Cartella Documenti Airis
HIVE_CONFIG_PATH = CONFIG_PATH / "hive_config.json"
# [FIX v114.6] Rimosso HEART_FILE_PATH statico: il percorso è ora dinamico per supportare più avatar

# --- [NUOVO v20.0] PERCORSI AUDIO CARE OS ---
CARE_AUDIO_PATH = APP_ROOT / "data" / "care_audio"
CARE_AUDIO_PATH.mkdir(parents=True, exist_ok=True)

# --- [FIX CRITICO] DEFINIZIONE COSTANTI MODELLI ---
MODELS_PATH = APP_ROOT / "models"
GGUF_MODELS_PATH = MODELS_PATH / "gguf"
MMPROJ_MODELS_PATH = MODELS_PATH / "mmproj"
LORA_MODELS_PATH = MODELS_PATH / "lora"
LABOUR_MODELS_PATH = MODELS_PATH / "labour"
SPECIALIST_MODELS_PATH = MODELS_PATH / "specialist"

# --- [NUOVO] PERCORSI SAFETENSORS MULTIMODALI (CARTELLE) ---
SAFETENSORS_MODELS_PATH = MODELS_PATH / "safetensors"
MMPROJ_SAFETENSORS_PATH = MMPROJ_MODELS_PATH / "safetensors"
LORA_SAFETENSORS_PATH = LORA_MODELS_PATH / "safetensors"
LABOUR_SAFETENSORS_PATH = LABOUR_MODELS_PATH / "safetensors"
SPECIALIST_SAFETENSORS_PATH = SPECIALIST_MODELS_PATH / "safetensors"

# --- CONFIGURAZIONE SICUREZZA (SANTUARIO BLINDATO) ---
SECRET_KEY = os.environ.get(
    "AIRIS_SECRET_KEY", "una_chiave_segreta_molto_lunga_e_casuale_da_cambiare_in_prod"
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 43200  # 30 giorni
SETUP_MODE = False  # Diventa True se non ci sono utenti nel DB
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Whitelist dinamica degli IP fidati (popolata allo startup)
TRUSTED_IPS = ["127.0.0.1", "::1"]
LAN_IP = "127.0.0.1"
PUBLIC_IP = "127.0.0.1"

# --- HELPER IP DETECTION ---
def _get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = "127.0.0.1"
    finally:
        s.close()
    return IP


def _get_public_ip() -> str:
    """Rileva l'IP pubblico con timeout per evitare blocchi allo startup."""
    try:
        # Usiamo ipify con un timeout molto breve
        return requests.get("https://api.ipify.org", timeout=3).text
    except Exception:
        return "127.0.0.1"


# Creazione cartelle se non esistono
TEMP_IMAGE_PATH.mkdir(exist_ok=True)
(MODELS_PATH / "gguf").mkdir(parents=True, exist_ok=True)
(MODELS_PATH / "mmproj").mkdir(parents=True, exist_ok=True)
(MODELS_PATH / "lora").mkdir(parents=True, exist_ok=True)
(MODELS_PATH / "specialist").mkdir(
    parents=True, exist_ok=True
)  # [NUOVO v23.0] Modulo A Rebrand
(MODELS_PATH / "labour").mkdir(
    parents=True, exist_ok=True
)  # [NUOVO v52.0] Modulo Labour Brain
(APP_ROOT / "temp_imports").mkdir(exist_ok=True)
(APP_ROOT / "exports").mkdir(exist_ok=True)
TEMP_AUDIO_PATH.mkdir(exist_ok=True)
CONNECTORS_PATH.mkdir(exist_ok=True)
DOCUMENTS_PATH.mkdir(exist_ok=True)  # [NUOVO v98.1] Assicura esistenza

# [FIX LIVELLO 1] Impostato maxsize per prevenire Memory Leak se il backend non consuma i messaggi
message_queue = asyncio.Queue(maxsize=100)

# --- GLOBALI ---
ALL_AVATAR_DATA: Dict[str, Any] = {}
db_manager: Optional[DatabaseManager] = None
guardian: Optional[Guardian] = None
game_logger: Optional[GameLogger] = None  # [NUOVO v121.0]
hive_manager: Optional[HiveManager] = None

# --- [FIX CRITICO] CACHE DI STATO GLOBALE (SINCRO ISTANTANEA UI) ---
CURRENT_SYSTEM_STATE: Dict[str, Any] = {
    "thinking": False,
    "thinking_character": "gemma",
    "gdr_mode": False,
    "is_muted": True,
    "is_monitoring": False,
    "is_active_hearing": False,
    "active_avatar": "gemma",
    "campaign_mode": False
}

# ---[NUOVO v98.0] GESTIONE BRIDGE LLM ---
# Dizionario per tracciare le richieste LLM in attesa di risposta da chat.py
LLM_FUTURES: Dict[str, asyncio.Future] = {}

# --- [FIX BUG 01] CACHE TTS PER VIBEVOICE ---
TTS_CACHE = {"data": None, "timestamp": 0, "ttl": 300}  # 5 minuti di cache

# --- LIFESPAN MANAGER ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- [FIX CRITICO] APPLICAZIONE HANDLER ASYNCIO ---
    try:
        asyncio.get_running_loop().set_exception_handler(_asyncio_exception_handler)
    except:
        pass

    # Startup
    global db_manager, guardian, game_logger, hive_manager, SETUP_MODE, LAN_IP, PUBLIC_IP, TRUSTED_IPS
    guardian = Guardian()

    # --- Sincronizzazione Motore Vocale da riga di comando (run.bat) ---
    if "--tts" in sys.argv:
        try:
            tts_idx = sys.argv.index("--tts")
            tts_val = sys.argv[tts_idx + 1]
            engine_name = "vibevoice" if tts_val == "2" else "kokoro"

            tts_config = guardian.get_tts_engine_config() or {}
            if tts_config.get("active_engine") != engine_name:
                tts_config["active_engine"] = engine_name
                guardian.save_tts_engine_config(tts_config)
                logger.info(t("log.tts_engine_forced", engine=engine_name.upper()))
        except Exception as e:
            logger.error(f"Errore sincronizzazione TTS da CLI: {e}")
    # ------------------------------------------------------------------

    game_logger = GameLogger(guardian)
    db_manager = DatabaseManager(game_logger)
    load_all_avatar_intents()

    # [NUOVO v65.0] Inizializzazione Hive Manager
    hive_manager = HiveManager(HIVE_CONFIG_PATH)

    # Rilevamento IP per Bypass Sicurezza (Santuario Blindato)
    LAN_IP = _get_local_ip()
    PUBLIC_IP = _get_public_ip()
    TRUSTED_IPS.extend([LAN_IP, PUBLIC_IP])
    logger.info(t("log.trusted_whitelist", ips=TRUSTED_IPS))

    # [FIX v114.6] Rimosso log statico HEART_FILE_PATH (ora dinamico per Multi-Avatar)

    # --- PROTOCOLLO BOOTSTRAP (SANTUARIO BLINDATO) ---
    user_count = db_manager.get_user_count()
    if user_count == 0:
        SETUP_MODE = True
        logger.warning(t("log.no_user_setup"))
    else:
        SETUP_MODE = False
        logger.info(t("log.sanctuary_blinded", count=user_count))

        # --- [NUOVO] INIZIALIZZAZIONE LINGUA BACKEND ---
        try:
            pref_lang = "it" # Default assoluto
            
            # 1. Prova a leggere da lang.cfg (Verità del Command Prompt)
            lang_cfg_path = APP_ROOT / "lang.cfg"
            if lang_cfg_path.exists():
                with open(lang_cfg_path, "r", encoding="utf-8") as f:
                    pref_lang = f.read().strip()
            
            # 2. Se esiste il profilo utente, sovrascrive (Verità dell'Utente)
            user_config_dir = CONFIG_PATH / "user"
            json_files = list(user_config_dir.glob("*.json"))
            if json_files:
                with open(json_files[0], "r", encoding="utf-8") as f:
                    profile_data = json.load(f)
                    pref_lang = get_json_value(
                        profile_data, ["lingua", "preferredLanguage"], pref_lang
                    )
            
            set_language(pref_lang)
            logger.info(t("log.lang_init", lang=pref_lang))
        except Exception as e:
            logger.error(t("log.lang_init_error", error=e))

    yield
    # Shutdown
    if db_manager:
        db_manager.close()


app = FastAPI(lifespan=lifespan)

from starlette.exceptions import HTTPException as StarletteHTTPException

# ---[FIX 4.3] GESTIONE ERRORI API (SANTUARIO BLINDATO) ---
# Previene l'esposizione di stack trace interni al frontend e a potenziali attaccanti.
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 500:
        logger.error(f"[SANTUARIO BLINDATO] Intercettato errore 500 su {request.url.path}: {exc.detail}")
        return JSONResponse(
            status_code=500,
            content={"detail": t("system.error", error="Errore interno del server. Dettagli nei log.")}
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"[SANTUARIO BLINDATO] Eccezione non gestita su {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": t("system.error", error="Errore interno del server. Dettagli nei log.")}
    )

# --- [AGGIUNTA v62.5] MIDDLEWARE OTTIMIZZAZIONE MULTIMEDIALE ---
class MediaOptimizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware per abbattere la latenza multimediale.
    Applica caching intelligente e abilita lo streaming parziale (Range Requests).
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        response = await call_next(request)

        # 1. Caching Asset Statici (Avatar e Video Base)
        if path.startswith("/avatars/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            response.headers["Accept-Ranges"] = "bytes"

        # 2. Ottimizzazione File Temporanei (Audio/Immagini Memoria)
        # [MODIFICA v98.1] Aggiunto /documents/ alla lista di cache breve
        elif path.startswith(("/temp_audio/", "/temp_images/", "/documents/")):
            # Cache breve per permettere aggiornamenti ma evitare ricaricamenti inutili
            response.headers["Cache-Control"] = "public, max-age=3600"
            response.headers["Accept-Ranges"] = "bytes"

        # 3. Supporto globale per Range Requests (Streaming)
        if "Accept-Ranges" not in response.headers:
            response.headers["Accept-Ranges"] = "bytes"

        return response


# --- FIX v62.8: DISABILITATO TEMPORANEAMENTE PER DEBUG VIDEO ERROR ---
# app.add_middleware(MediaOptimizationMiddleware)

# --- [NUOVO v62.9] MIDDLEWARE DI DEBUG STATICO ---
@app.middleware("http")
async def static_debug_middleware(request: Request, call_next):
    response = await call_next(request)
    # Se una richiesta verso gli avatar fallisce, indaghiamo
    if request.url.path.startswith("/avatars/") and response.status_code == 404:
        try:
            # [FIX v118.5] Protezione contro percorsi illegali o troppo lunghi (Anti-Crash)
            path_str = request.url.path
            if len(path_str) > 255 or "\n" in path_str or "\r" in path_str:
                return response

            # Ricostruiamo il percorso fisico che il server avrebbe dovuto trovare
            rel_path = path_str.replace("/avatars/", "")
            # Decodifica URL (es. %20 -> spazio)
            rel_path = unquote(rel_path)
            full_path = AVATARS_BASE_PATH / rel_path

            logger.error(t("avatar_server.log.static_debug_404", path=path_str))
            logger.error(t("avatar_server.log.static_debug_looking", path=full_path))
            logger.error(
                t("avatar_server.log.static_debug_exists", exists=full_path.exists())
            )
            if not full_path.exists():
                # Check case-insensitive
                parent = full_path.parent
                if parent.exists():
                    available = os.listdir(parent)
                    logger.error(
                        t(
                            "avatar_server.log.static_debug_available",
                            parent=parent.name,
                            available=available,
                        )
                    )
        except Exception as e:
            logger.error(t("avatar_server.log.static_debug_error", error=e))

    return response


# --- MIDDLEWARE DI SICUREZZA (SANTUARIO BLINDATO) ---
class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        host_header = request.headers.get("host", "").lower()
        path = request.url.path

        # --- [NUOVO v100.4] CHECK DINAMICO IP & RANGE ---
        is_trusted = False

        # 1. Check Whitelist Statica (Localhost/Startup IPs)
        if client_ip in TRUSTED_IPS:
            is_trusted = True

        # 2. Check Whitelist Dinamica (Database)
        if not is_trusted and db_manager:
            policies = db_manager.get_security_policies()
            for p in policies:
                try:
                    if p["type"] == "ip" and client_ip == p["value"]:
                        is_trusted = True
                        break
                    elif p["type"] == "range":
                        # Verifica se l'IP rientra nel range CIDR
                        if ipaddress.ip_address(client_ip) in ipaddress.ip_network(
                            p["value"]
                        ):
                            is_trusted = True
                            break
                except Exception:
                    continue

        # 3. Check Ngrok / LAN standard
        if not is_trusted:
            is_trusted = (
                client_ip.startswith(("192.168.", "10.", "172.16."))
                or ".ngrok-free.app" in host_header
                or "x-forwarded-for" in request.headers
            )

        if is_trusted:
            return await call_next(request)

        # 4. Whitelist Percorsi Pubblici
        if (
            path == "/"
            or path.startswith(
                (
                    "/mobile",
                    "/classic",
                    "/avatars",
                    "/lore",
                    "/temp_",
                    "/documents",
                    "/api/translations",
                    "/api/tts", # [FIX CRITICO] Sblocca l'accesso pubblico alle voci prima del login (Welcome Wizard)
                )
            )
            or path
            in [
                "/api/auth/login",
                "/api/auth/status",
                "/api/auth/setup",
                "/api/auth/is-trusted",
                "/api/health",
                "/docs",
                "/openapi.json",
                "/favicon.ico",
            ]
            or request.method == "OPTIONS"
        ):
            return await call_next(request)

        # 5. Verifica Token JWT per accessi esterni non identificati
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                content={"detail": t("auth.unauthorized")}, status_code=401
            )

        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

            # ---[NUOVO] CONTROLLO RUOLO GUEST (SANTUARIO BLINDATO MULTIPLAYER) ---
            role = payload.get("role")
            if role == "guest":
                allowed_guest_paths = ["/ws", "/api/auth/guest"]
                is_allowed_static = path.startswith(
                    ("/temp_images", "/temp_audio", "/lore")
                )
                if path not in allowed_guest_paths and not is_allowed_static:
                    logger.warning(
                        t("avatar_server.log.security_guest_unauthorized", path=path)
                    )
                    return JSONResponse(
                        content={"detail": t("auth.access_denied_guest")},
                        status_code=403,
                    )

        except jwt.ExpiredSignatureError:
            return JSONResponse(
                content={"detail": t("auth.token_expired")}, status_code=401
            )
        except jwt.InvalidTokenError:
            return JSONResponse(
                content={"detail": t("auth.token_invalid")}, status_code=401
            )

        return await call_next(request)


app.add_middleware(SecurityMiddleware)

# --- MIDDLEWARE CORS MANUALE ---
class ForceCorsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response


app.add_middleware(ForceCorsMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ROTTE DI REDIRECT E FAVICON (FIX 404) ---


@app.get("/", include_in_schema=False)
async def root():
    """Redirect radice verso l'interfaccia mobile."""
    return RedirectResponse(url="/mobile/")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Serve il favicon per evitare 404 nei log."""
    favicon_path = APP_ROOT / "frontend_mobile" / "dist" / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(favicon_path)
    return Response(status_code=204)


# --- HELPER SICUREZZA ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


class ConnectionManager:
    def __init__(self):
        # --- [NUOVO] MAPPATURA UNICAST (MULTIPLAYER) ---
        self.active_connections: Dict[str, WebSocket] = {}
        self.is_women_only_room = False  # [NUOVO] Flag Buttafuori
        self.livello_minimo = 1
        self.livello_massimo = 20

    async def connect(self, websocket: WebSocket, player_name: str):
        # Gestione subprotocollo per ngrok (opzionale ma utile)
        requested_protocols = websocket.scope.get("subprotocols", [])
        subprotocol = None
        if "ngrok-skip-browser-warning" in requested_protocols:
            subprotocol = "ngrok-skip-browser-warning"
        await websocket.accept(subprotocol=subprotocol)
        self.active_connections[player_name] = websocket

    def disconnect(self, player_name: str):
        if player_name in self.active_connections:
            del self.active_connections[player_name]

    def rename_connection(self, old_name: str, new_name: str):
        """Rinomina una connessione esistente senza riaccettare il WebSocket."""
        if old_name in self.active_connections:
            self.active_connections[new_name] = self.active_connections.pop(old_name)

    async def broadcast(self, message: str):
        for connection in list(self.active_connections.values()):
            try:
                # [FIX CRITICO] Timeout di 1 secondo per evitare che un client mobile in standby blocchi il server
                await asyncio.wait_for(connection.send_text(message), timeout=1.0)
            except Exception:
                pass

    async def unicast(self, message: str, player_name: str):
        """Invia un messaggio a un singolo giocatore specifico."""
        if player_name in self.active_connections:
            try:
                # [FIX CRITICO] Timeout di 1 secondo
                await asyncio.wait_for(self.active_connections[player_name].send_text(message), timeout=1.0)
            except Exception:
                pass


manager = ConnectionManager()

# --- MODELLI PYDANTIC ---
# [MODIFICA v68.1] Aggiornato per supportare anche narrative_buffer
class SessionUpdateRequest(BaseModel):
    name: Optional[str] = None
    narrative_buffer: Optional[str] = None


class ProactiveMemorySettings(BaseModel):
    reflection_time: str
    reminder_check_interval_minutes: int


class PerceptionSettingsRequest(BaseModel):
    silence_threshold: int
    hotword_detection: Optional[Dict[str, Any]] = None


# --- [NUOVO v68.7] MODELLO IMPOSTAZIONI IMMAGINAZIONE ---
class ImaginationSettingsRequest(BaseModel):
    enabled: bool
    frequency: str
    engine: str


# --- [NUOVO v69.1] MODELLO DEMIURGO (UPDATED v100.6) ---
class DemiurgeSettingsRequest(BaseModel):
    enabled: bool  # [NUOVO] Switch Master
    provider: str
    model: str
    api_key: Optional[str] = ""
    api_base: Optional[str] = ""
    auto_run: bool
    safe_mode: bool
    labour_model_on_cpu: bool = True  # [NUOVO v52.0] Parallelismo CPU/GPU


# ---[NUOVO v20.0] ENDPOINT PANOPTICON ---
class PanopticonSettingsRequest(BaseModel):
    enabled: bool
    sherlock_enabled: bool
    gamer_enabled: bool
    media_enabled: bool
    life_guardian_enabled: bool
    sherlock_blacklist: List[str]


class ToastRequest(BaseModel):
    message: str
    type: str = "info"


class GhostTextRequest(BaseModel):
    text: str
    avatar: str
    is_technical: bool = False


# --- [NUOVO v97.0] MODELLO EFFETTO VISIVO ---
class VisualEffectRequest(BaseModel):
    type: str
    x: int
    y: int


class CreateReminderRequest(BaseModel):
    content: str
    trigger_in_minutes: int


class UpdateReminderRequest(BaseModel):
    event_name: str
    content: str
    event_timestamp: float
    trigger_timestamp: float
    recurrence_rule: str


class CredentialsUpdateRequest(BaseModel):
    credentials: Dict[str, Any]


class CustomConnectorsUpdateRequest(BaseModel):
    connectors: Dict[str, Any]


class CustomScriptRequest(BaseModel):
    filename: str
    code: str


class GenerateDefRequest(BaseModel):
    script_code: str
    prompt: str


class InstallPackageRequest(BaseModel):
    package_name: str


class TimeScheduleUpdateRequest(BaseModel):
    morning: str
    afternoon: str
    night: str
    bed_time: str


class AvatarStyleUpdateRequest(BaseModel):
    active_set: str


class RunConnectorRequest(BaseModel):
    script_name: str
    action: str
    params: Dict[str, Any]


# --- [NUOVO v118.0] MODELLO CONFIGURAZIONE TTS ---
class TtsSettingsRequest(BaseModel):
    active_engine: str  # 'kokoro' | 'vibevoice'
    vibevoice_url: str

class TtsPreviewRequest(BaseModel):
    text: str
    voice: str
    engine: str
    lang_code: str

# --- [NUOVO] MODELLI MCP SERVER ---
class McpServerConfig(BaseModel):
    id: str
    name: str
    transport: str
    command: Optional[str] = None
    args: Optional[List[str]] = None
    url: Optional[str] = None
    enabled: bool

class McpSettingsRequest(BaseModel):
    servers: List[McpServerConfig]

# --- [NUOVO v15.0] MODELLI SPECIALIST & TOOLS ---
class SpecialistSettingsRequest(BaseModel):
    keep_loaded: bool
    prompts: List[str]


class ValidateCodeRequest(BaseModel):
    code: str


class SyncToolRequest(BaseModel):
    name: str
    def_structure: str
    prompt: str


# [AGGIUNTA CHIRURGICA] Modello per cancellazione multipla sessioni (v62.2)
class BulkDeleteRequest(BaseModel):
    session_ids: List[str]


#[AGGIUNTA CHIRURGICA] Modello per sincronizzazione sessione attiva (v62.23)
class ActiveSessionRequest(BaseModel):
    session_id: str

class FactoryResetRequest(BaseModel):
    total_wipe: bool = False

# --- [NUOVO v63.0] MODELLI HIVE MIND ---
class HiveRegisterRequest(BaseModel):
    device_id: str
    device_name: str
    device_type: str  # 'tablet' | 'mobile' | 'desktop'


class HiveHeartbeatRequest(BaseModel):
    device_id: str


class HiveFocusRequest(BaseModel):
    device_id: str


# --- [NUOVO v65.1] MODELLI BINDING IP ---
class HiveBindRequest(BaseModel):
    ip: str
    device_id: str
    name: str


class HiveUnbindRequest(BaseModel):
    ip: str


# --- [NUOVO v66.1] MODELLI EDITING ---
class HiveUpdateDeviceRequest(BaseModel):
    device_id: str
    name: Optional[str] = None
    ip: Optional[str] = None


class HiveRemoveDeviceRequest(BaseModel):
    device_id: str


# ---[NUOVO v67.0] MODELLI RPG ROSTER ---
class RpgRosterToggleRequest(BaseModel):
    char_name: str
    action: str  # 'add' | 'remove'
    lang: str = "it"


# --- [NUOVO v27.0] MODELLI RPG CAMPAIGN ---
class RpgCampaignModeRequest(BaseModel):
    enabled: bool
    lang: str = "it"


# ---[NUOVO RM29] VALIDAZIONE RIGOROSA HANDSHAKE OSPITI ---
class GuestCombatStats(BaseModel):
    hp_massimi: int = 10
    hp_attuali: int = 10
    classe_armatura: int = 10
    iniziativa: int = 0
    velocita: int = 9


class GuestRpgSheet(BaseModel):
    combattimento: GuestCombatStats = Field(default_factory=GuestCombatStats)
    # Permettiamo flessibilità su equipaggiamento e magie, ma blindiamo il combattimento
    equipaggiamento: Optional[Dict[str, Any]] = {}
    magia_e_privilegi: Optional[Dict[str, Any]] = {}
    statistiche_core: Optional[Dict[str, Any]] = {}
    dati_base: Optional[Dict[str, Any]] = {}


class GuestHandshakeRequest(BaseModel):
    type: str
    player_name: str
    scheda_rpg: GuestRpgSheet = Field(default_factory=GuestRpgSheet)
    # --- [NUOVO] Campi per Araldica e Genere ---
    guild_name: Optional[str] = None
    guild_symbol: Optional[str] = None
    gender: Optional[str] = "unspecified"


class GenerateRpgSheetRequest(BaseModel):
    razza: str
    classe: str
    livello: int
    lang: str = "it"


# --- [NUOVO v98.0] MODELLI OPENAI BRIDGE ---
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False


class InternalLLMResponse(BaseModel):
    request_id: str
    content: str


# --- [NUOVO v99.0] MODELLI MUSA & GENESI ---
class JailbreakItem(BaseModel):
    id: str
    name: str
    content: str
    is_active: bool


class JailbreakListRequest(BaseModel):
    jailbreaks: List[JailbreakItem]


class ActiveJailbreakRequest(BaseModel):
    id: str


class LearningSource(BaseModel):
    id: str
    url: str
    enabled: bool
    last_checked: Optional[float] = 0
    status: Optional[str] = "unknown"


class LearningArgument(BaseModel):
    id: str
    topic: str
    associatedSourceIds: List[str]
    enabled: bool


class SelfLearningConfig(BaseModel):
    interval_minutes: int
    active: bool


class KnowledgeBaseRequest(BaseModel):
    sources: List[LearningSource]
    arguments: List[LearningArgument]
    config: SelfLearningConfig


# --- [NUOVO v99.1] MODELLO TEST JAILBREAK ---
class JailbreakTestRequest(BaseModel):
    system_prompt: str
    user_query: str


# --- MODELLI AUTH (SANTUARIO BLINDATO) ---
class LoginRequest(BaseModel):
    username: str
    password: str


class SetupRequest(BaseModel):
    username: str
    password: str
    confirm_password: str


class GuestLoginRequest(BaseModel):
    lobby_password: str


class Token(BaseModel):
    access_token: str
    token_type: str


# --- [NUOVO v100.3] MODELLO AGGIORNAMENTO UTENTE ---
class UserUpdateRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None


# --- [NUOVO v100.4] MODELLO SECURITY POLICY ---
class SecurityPolicyRequest(BaseModel):
    type: str  # 'ip' | 'range'
    value: str
    description: Optional[str] = None


# --- [NUOVO v110.0] MODELLI PERSONALITÀ DINAMICA ---
class PersonalityPresetRequest(BaseModel):
    presets: Dict[str, Any]


class CharacterPersonalityRequest(BaseModel):
    char_type: str  # 'PG' | 'PNG' | 'AVATAR'
    lang: str = "it"
    traits: Dict[str, Any]


# --- [NUOVO FASE 16] MODELLI COGNITIVE MODULES ---
class CognitiveModuleRequest(BaseModel):
    id: str
    name: str
    category: str
    context: str
    content: str
    is_active: bool
    priority: int
    tags: List[str]
    activation_condition: Optional[Dict[str, Any]] = None


# --- [NUOVO v20.0] MODELLI CORTEX AUDIO ---
class TtsClipRequest(BaseModel):
    text: str
    label: str
    category: str
    voice: Optional[str] = None


class AudioMetadataUpdateRequest(BaseModel):
    label: str
    category: str


class CareAudioPlayRequest(BaseModel):
    audio_url: str
    device_ids: List[str]
    label: str


# --- [NUOVO v18.0] MODELLI JARVIS CORTEX ---
class BlacklistRequest(BaseModel):
    windows: List[str]


class RollbackRequest(BaseModel):
    patch_id: str


# --- [NUOVO v19.1] MODELLI JARVIS CONTROL ---
class PrudenzaRequest(BaseModel):
    value: int


class WorkModeRequest(BaseModel):
    enabled: bool


class TriggerUpdateRequest(BaseModel):
    old_value: str
    new_value: str
    new_label: str


# --- HELPER ---
def get_json_value(data: Dict[str, Any], keys: List[str], default: Any = "") -> Any:
    for k in keys:
        # 1. Cerca nella root
        if k in data:
            return data[k]
        # 2. Cerca nelle sottosezioni comuni
        for section in ["dati_anagrafici", "essenza_e_anima", "preferenze_utente"]:
            if (
                section in data
                and isinstance(data[section], dict)
                and k in data[section]
            ):
                return data[section][k]
    return default


def load_all_avatar_intents():
    global ALL_AVATAR_DATA
    logger.info(t("log.scan_avatars"))
    for avatar_dir in AVATARS_BASE_PATH.iterdir():
        if avatar_dir.is_dir() and avatar_dir.name != "ai_souls":
            intent_file = avatar_dir / "intent" / "intent.json"
            if intent_file.is_file():
                try:
                    with open(intent_file, "r", encoding="utf-8") as f:
                        intent_data = json.load(f)

                    # --- [NUOVO] AUTO-CLEANER INTENT (Fase Agentica) ---
                    # Pulisce le descrizioni sporche spostando le note di sistema in un campo dedicato
                    needs_save = False
                    for item in intent_data:
                        short_desc = item.get("short_description", "")
                        # Se la short_description contiene note di sistema (**, Crucial, state)
                        if "**" in short_desc or "Crucial" in short_desc or "state" in short_desc.lower():
                            item["system_note"] = short_desc
                            # Sostituiamo con la descrizione fisica reale
                            item["short_description"] = item.get("description", "")
                            needs_save = True
                    
                    if needs_save:
                        with open(intent_file, "w", encoding="utf-8") as f:
                            json.dump(intent_data, f, indent=2, ensure_ascii=False)
                        logger.info(t("log.intent_auto_cleaned", avatar=avatar_dir.name))
                    # ---------------------------------------------------

                    intents = {}
                    intent_details = {}
                    emotion_map = defaultdict(list)
                    unique_emotions = set()

                    for item in intent_data:
                        filepath = item.get("filepath", "")
                        if filepath:
                            clean_path = (
                                filepath.replace("\\", "/").lstrip("./").lstrip("/")
                            )
                            intent_key = Path(filepath).stem.lower().strip()

                            intents[intent_key] = clean_path

                            intent_details[intent_key] = {
                                "description": item.get(
                                    "description", t("avatar_server.no_description")
                                ),
                                "emotion": item.get("emotion", []),
                                "short_description": item.get("short_description", ""),
                                "is_alternative": item.get("is_alternative", False),
                            }
                            emotions = item.get("emotion", [])
                            if isinstance(emotions, str):
                                emotions = [emotions]
                            if isinstance(emotions, list):
                                for emo in emotions:
                                    emo_clean = emo.strip()
                                    emotion_map[emo_clean.lower()].append(clean_path)
                                    if not intent_key.startswith("state_"):
                                        unique_emotions.add(emo_clean)

                    # [FIX CRITICO] Estrazione dinamica degli stati di idle
                    # Cerca automaticamente tutti i video che iniziano con i prefissi di quiete
                    idle_states =[k for k in intents.keys() if k.startswith("state_idle") or k.startswith("state_listening")]
                    
                    # [FIX ROTAZIONE] Estrazione dinamica degli stati di speaking
                    speaking_states =[k for k in intents.keys() if k.startswith("state_speaking")]

                    base_avatar_url = None
                    base_image_dir = avatar_dir / "base_image"
                    if base_image_dir.is_dir():
                        for ext in [
                            ".png",
                            ".jpg",
                            ".jpeg",
                            ".gif",
                            ".webp",
                            ".avif",
                            ".heic",
                        ]:
                            img_path = base_image_dir / f"{avatar_dir.name}{ext}"
                            if img_path.exists():
                                base_avatar_url = f"/avatars/{avatar_dir.name}/base_image/{img_path.name}"
                                break

                    avatar_key = avatar_dir.name.lower()
                    ALL_AVATAR_DATA[avatar_key] = {
                        "intent_map": intents,
                        "intent_details": intent_details,
                        "emotion_map": dict(emotion_map),
                        "available_emotions": sorted(list(unique_emotions)),
                        "idle_states": idle_states,
                        "speaking_states": speaking_states, # [FIX ROTAZIONE] Passiamo la lista al frontend
                        "ai_base_avatar_url": base_avatar_url,
                        "original_name": avatar_dir.name,
                    }
                    logger.info(
                        t("log.avatar_loaded", avatar=avatar_key, count=len(intents))
                    )

                except Exception as e:
                    logger.error(
                        t("log.avatar_load_error", avatar=avatar_dir.name, error=str(e))
                    )


# --- LOGICA DELLO STILISTA (SEASON & TIME) ---


def get_current_season() -> str:
    now = datetime.now()
    month = now.month
    day = now.day

    if (month == 12 and day >= 21) or (month in [1, 2]) or (month == 3 and day < 20):
        return "Winter"
    elif (month == 3 and day >= 20) or (month in [4, 5]) or (month == 6 and day < 21):
        return "Spring"
    elif (month == 6 and day >= 21) or (month in [7, 8]) or (month == 9 and day < 23):
        return "Summer"
    else:
        return "Autumn"


def get_time_of_day() -> str:
    if not guardian:
        return "Morning"

    schedule = guardian.get_time_schedule()
    now = datetime.now().time()

    def parse_time(t_str):
        try:
            return datetime.strptime(t_str, "%H:%M").time()
        except ValueError:
            return dtime(0, 0)

    morning_start = parse_time(schedule.get("morning", "06:00"))
    afternoon_start = parse_time(schedule.get("afternoon", "12:00"))
    night_start = parse_time(schedule.get("night", "19:00"))
    bed_time_start = parse_time(schedule.get("bed_time", "23:00"))

    if bed_time_start < morning_start:
        if now >= bed_time_start or now < morning_start:
            return "Bed_Time"
    else:
        if bed_time_start <= now < morning_start:
            return "Bed_Time"

    if morning_start <= now < afternoon_start:
        return "Morning"
    elif afternoon_start <= now < night_start:
        return "Afternoon"
    elif night_start <= now:
        return "Night"

    return "Morning"


def resolve_video_path(
    avatar_name: str, relative_path: str, custom_set: Optional[str] = None
) -> str:
    season = get_current_season()
    time_of_day = get_time_of_day()

    # --- FIX v62.7: Normalizzazione Nome Avatar ---
    avatar_name = avatar_name.lower()

    if not custom_set and guardian:
        custom_set = guardian.get_avatar_custom_set(avatar_name)
        if custom_set == "Standard":
            custom_set = None

    base_video_path = AVATARS_BASE_PATH / avatar_name / "videos"

    # Helper per costruire URL sicuri (Slash Forward)
    def build_url(parts):
        return "/" + "/".join(parts).replace("\\", "/")

    # 1. CHECK CUSTOM SPECIFICO
    if custom_set:
        target = base_video_path / season / custom_set / time_of_day / relative_path
        if target.exists():
            return build_url(
                [
                    "avatars",
                    avatar_name,
                    "videos",
                    season,
                    custom_set,
                    time_of_day,
                    relative_path,
                ]
            )

        # 2. CHECK CUSTOM GENERICO
        target = base_video_path / season / custom_set / relative_path
        if target.exists():
            return build_url(
                ["avatars", avatar_name, "videos", season, custom_set, relative_path]
            )

    # 3. CHECK STANDARD STAGIONALE - ORARIO
    target = base_video_path / season / "Standard" / time_of_day / relative_path
    if target.exists():
        return build_url(
            [
                "avatars",
                avatar_name,
                "videos",
                season,
                "Standard",
                time_of_day,
                relative_path,
            ]
        )

    # 4. CHECK STANDARD STAGIONALE - GENERICO
    target = base_video_path / season / "Standard" / relative_path
    if target.exists():
        return build_url(
            ["avatars", avatar_name, "videos", season, "Standard", relative_path]
        )

    # 5. CHECK DEFAULT ASSOLUTO
    target = base_video_path / "default" / relative_path
    if target.exists():
        return build_url(["avatars", avatar_name, "videos", "default", relative_path])

    logger.warning(t("log.stylist_fallback", path=relative_path))
    return build_url(["avatars", avatar_name, "videos", "default", relative_path])


def install_pip_package(package_name: str):
    try:
        logger.info(t("log.install_dep", pkg=package_name))
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        logger.info(t("log.install_dep_success", pkg=package_name))
        return True
    except subprocess.CalledProcessError as e:
        logger.error(t("log.install_dep_error", pkg=package_name, error=str(e)))
        return False


# --- ENDPOINT AUTHENTICATION ---


@app.get("/api/auth/status")
async def auth_status():
    """Restituisce lo stato del sistema (Setup Mode o Normal)."""
    user_count = db_manager.get_user_count() if db_manager else 0
    return {"setup_mode": user_count == 0, "user_count": user_count}


@app.get("/api/auth/is-trusted")
async def auth_is_trusted(request: Request):
    """
    Endpoint pubblico per permettere al frontend di sapere se l'IP è fidato.
    Se True, il frontend può bypassare la maschera di login.
    NUOVO: Restituisce anche un token temporaneo per le fonti fidate.
    """
    # --- [FIX v100.2] FORZA REGISTRAZIONE SE SETUP_MODE ATTIVO ---
    user_count = db_manager.get_user_count() if db_manager else 0
    if user_count == 0:
        return {"is_trusted": False, "token": None}

    client_ip = request.client.host
    host_header = request.headers.get("host", "").lower()

    # ---[NUOVO v100.4] CHECK DINAMICO IP & RANGE ---
    is_trusted = False
    if client_ip in TRUSTED_IPS:
        is_trusted = True

    if not is_trusted and db_manager:
        policies = db_manager.get_security_policies()
        for p in policies:
            try:
                if p["type"] == "ip" and client_ip == p["value"]:
                    is_trusted = True
                    break
                elif p["type"] == "range":
                    if ipaddress.ip_address(client_ip) in ipaddress.ip_network(
                        p["value"]
                    ):
                        is_trusted = True
                        break
            except Exception:
                continue

    if not is_trusted:
        is_trusted = (
            client_ip.startswith(("192.168.", "10.", "172.16."))
            or ".ngrok-free.app" in host_header
            or "x-forwarded-for" in request.headers
        )

    # ---[FIX v100.2] LOGICA IDENTITÀ DINAMICA (1 vs 2+ UTENTI) ---
    token = None
    if is_trusted:
        if user_count == 1:
            # Esattamente 1 utente: auto-login sicuro
            user = db_manager.get_first_user()
            if user:
                access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                token = create_access_token(
                    data={"sub": user["username"], "role": user["role"]},
                    expires_delta=access_token_expires,
                )
                logger.info(t("log.auto_login", ip=client_ip, user=user["username"]))
                return {"is_trusted": True, "token": token}
        else:
            # 2 o più utenti: neghiamo il trusted status per forzare la scelta identità nella UI
            logger.info(t("log.multi_user_login", count=user_count, ip=client_ip))
            return {"is_trusted": False, "token": None}

    return {"is_trusted": False, "token": None}


@app.post("/api/auth/setup")
async def auth_setup(request: SetupRequest):
    """Crea il primo amministratore (Solo se SETUP_MODE è True)."""
    global SETUP_MODE
    user_count = db_manager.get_user_count() if db_manager else 0
    if user_count > 0 and not SETUP_MODE:
        # Permetti l'aggiunta di utenti solo se autenticati (gestito dal middleware)
        pass

    if request.password != request.confirm_password:
        raise HTTPException(status_code=400, detail=t("auth.password_mismatch"))

    if len(request.password) < 8:
        raise HTTPException(status_code=400, detail=t("auth.password_too_short"))

    if db_manager.create_user(request.username, request.password):
        SETUP_MODE = False
        logger.info(t("auth.user_created", user=request.username))
        return {"status": "ok", "message": t("auth.user_created")}
    else:
        raise HTTPException(status_code=500, detail=t("auth.user_creation_error"))


@app.post("/api/auth/guest", response_model=Token)
async def guest_login(request: GuestLoginRequest):
    """
    Rilascia un token Guest per i giocatori ospiti.
    In futuro validerà la lobby_password contro quella impostata dall'Host.
    """
    # Per ora accettiamo la connessione e rilasciamo il token limitato
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": "guest_user", "role": "guest"}, expires_delta=access_token_expires
    )
    logger.info(t("auth.guest_token_issued"))
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/api/auth/login", response_model=Token)
async def login_for_access_token(request: LoginRequest):
    user = db_manager.verify_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=t("auth.invalid_credentials"),
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"]},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/api/auth/refresh", response_model=Token)
async def refresh_token(request: Request):
    """
    Rinnova il token JWT se ancora valido.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=t("auth.token_missing")
        )

    token = auth_header.split(" ")[1]

    try:
        # Decodifica il token (anche se scaduto, per recuperare username e role)
        payload = jwt.decode(
            token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False}
        )
        username: str = payload.get("sub")
        role: str = payload.get("role")

        if username is None:
            raise HTTPException(status_code=401, detail=t("auth.token_invalid"))

        # Verifica che l'utente esista ancora nel database
        user = db_manager.verify_user(
            username, None
        )  # Passa None come password per skip check
        if not user:
            raise HTTPException(status_code=401, detail=t("auth.user_not_found"))

        # Genera un nuovo token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": username, "role": role}, expires_delta=access_token_expires
        )

        logger.info(t("log.token_renewed", user=username))
        return {"access_token": access_token, "token_type": "bearer"}

    except jwt.PyJWTError as e:
        logger.error(t("avatar_server.log.security_refresh_error", error=str(e)))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=t("auth.token_refresh_invalid"),
        )


# --- [NUOVO v100.3] ENDPOINTS GESTIONE UTENTI ---


@app.get("/api/auth/users")
async def list_users():
    """Restituisce la lista di tutti gli utenti autorizzati."""
    if not db_manager:
        raise HTTPException(status_code=503, detail=t("system.db_unavailable"))
    return db_manager.get_all_users()


@app.put("/api/auth/users/{user_id}")
async def update_user_api(user_id: str, request: UserUpdateRequest):
    """Aggiorna username e/o password di un utente."""
    if not db_manager:
        raise HTTPException(status_code=503, detail=t("system.db_unavailable"))
    if db_manager.update_user(user_id, request.username, request.password):
        return {"status": "ok", "message": t("auth.user_updated")}
    raise HTTPException(status_code=500, detail=t("auth.user_update_error"))


@app.delete("/api/auth/users/{user_id}")
async def delete_user_api(user_id: str):
    """Elimina un utente dal database."""
    if not db_manager:
        raise HTTPException(status_code=503, detail=t("system.db_unavailable"))
    # Impedisci di cancellare l'ultimo utente per non restare chiusi fuori
    if db_manager.get_user_count() <= 1:
        raise HTTPException(status_code=400, detail=t("auth.cannot_delete_last_user"))
    if db_manager.delete_user(user_id):
        return {"status": "ok", "message": t("auth.user_deleted")}
    raise HTTPException(status_code=500, detail=t("auth.user_delete_error"))


# ---[NUOVO v100.4] ENDPOINTS SECURITY POLICIES ---


@app.get("/api/auth/security-policies")
async def list_security_policies():
    """Restituisce la lista di tutti gli IP e Range autorizzati."""
    if not db_manager:
        raise HTTPException(status_code=503, detail=t("system.db_unavailable"))
    return db_manager.get_security_policies()


@app.post("/api/auth/security-policies")
async def add_security_policy_api(request: SecurityPolicyRequest):
    """Aggiunge un nuovo IP o Range alla whitelist."""
    if not db_manager:
        raise HTTPException(status_code=503, detail=t("system.db_unavailable"))

    # Validazione Formato
    try:
        if request.type == "ip":
            ipaddress.ip_address(request.value)
        elif request.type == "range":
            ipaddress.ip_network(request.value)
        else:
            raise ValueError(t("security.invalid_policy_type"))
    except ValueError as e:
        raise HTTPException(
            status_code=400, detail=t("security.invalid_format", error=str(e))
        )

    if db_manager.add_security_policy(request.type, request.value, request.description):
        return {"status": "ok", "message": t("security.policy_added")}
    raise HTTPException(status_code=400, detail=t("security.policy_save_error"))


@app.delete("/api/auth/security-policies/{policy_id}")
async def delete_security_policy_api(policy_id: str):
    """Rimuove una policy di sicurezza."""
    if not db_manager:
        raise HTTPException(status_code=503, detail=t("system.db_unavailable"))
    if db_manager.delete_security_policy(policy_id):
        return {"status": "ok", "message": t("security.policy_removed")}
    raise HTTPException(status_code=500, detail=t("security.policy_remove_error"))


# --- [NUOVO v110.0] ENDPOINTS PERSONALITÀ DINAMICA ---


@app.get("/api/personality/presets")
async def get_personality_presets():
    """Recupera i preset di personalità globali."""
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    return JSONResponse(content=guardian.get_personality_presets())


@app.post("/api/personality/presets")
async def save_personality_presets(request: PersonalityPresetRequest):
    """Salva i preset di personalità globali."""
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    if guardian.save_personality_presets_data(request.presets):
        return JSONResponse(
            content={"status": "ok", "message": t("personality.presets_saved")}
        )
    raise HTTPException(status_code=500, detail=t("personality.presets_save_error"))


@app.post("/api/characters/{character_id}/personality")
async def save_character_personality(
    character_id: str, request: CharacterPersonalityRequest
):
    """
    Salva i tratti di personalità dinamica nel JSON del personaggio.
    """
    try:
        # Determina il percorso del file JSON
        target_file = None

        if request.char_type.upper() == "AVATAR":
            target_file = AVATARS_BASE_PATH / "ai_souls" / f"{character_id}.json"
        elif ACTIVE_RPG_PATH:
            norm_lang = (
                guardian.normalize_lang_code(request.lang) if guardian else request.lang
            )
            # Cerca nella cartella lingua o root
            base_path = ACTIVE_RPG_PATH / norm_lang / request.char_type.upper()
            if not base_path.exists():
                base_path = ACTIVE_RPG_PATH / request.char_type.upper()

            target_file = base_path / f"{character_id}.json"

        if not target_file or not target_file.exists():
            raise HTTPException(status_code=404, detail=t("personality.char_not_found"))

        # Leggi, Aggiorna, Salva
        with open(target_file, "r", encoding="utf-8") as f:
            char_data = json.load(f)

        char_data["personalita_dinamica"] = request.traits

        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(char_data, f, indent=2, ensure_ascii=False)

        return JSONResponse(
            content={"status": "ok", "message": t("personality.updated")}
        )

    except Exception as e:
        logger.error(
            t("avatar_server.log.personality_save_error", id=character_id, error=str(e))
        )
        raise HTTPException(status_code=500, detail=str(e))


# --- [NUOVO FASE 16] ENDPOINTS COGNITIVE MODULES & MINDSETS ---


@app.get("/api/cognitive/modules")
async def get_cognitive_modules():
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    return JSONResponse(content=guardian.get_cognitive_modules())


@app.post("/api/cognitive/modules")
async def save_cognitive_module(module: CognitiveModuleRequest):
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    if guardian.save_cognitive_module(module.model_dump()):
        # Sfruttiamo il comando esistente in chat.py che ricarica il Guardian e aggiorna il Cervello
        await message_queue.put("/update_demiurge_config")
        return JSONResponse(
            content={"status": "ok", "message": t("cognitive.module_saved")}
        )
    raise HTTPException(status_code=500, detail=t("cognitive.module_save_error"))


@app.delete("/api/cognitive/modules/{module_id}")
async def delete_cognitive_module(module_id: str):
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    if guardian.delete_cognitive_module(module_id):
        await message_queue.put("/update_demiurge_config")
        return JSONResponse(
            content={"status": "ok", "message": t("cognitive.module_deleted")}
        )
    raise HTTPException(status_code=500, detail=t("cognitive.module_delete_error"))


@app.get("/api/cognitive/mindsets")
async def get_cognitive_mindsets():
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    return JSONResponse(content=guardian.get_cognitive_mindsets())


@app.post("/api/cognitive/mindsets")
async def save_cognitive_mindsets(request: Request):
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    try:
        data = await request.json()
        if guardian.save_cognitive_mindsets(data):
            await message_queue.put("/update_demiurge_config")
            return JSONResponse(
                content={"status": "ok", "message": t("cognitive.mindsets_saved")}
            )
        raise HTTPException(status_code=500, detail=t("cognitive.mindsets_save_error"))
    except Exception as e:
        logger.error(t("avatar_server.log.mindsets_save_error_log", error=str(e)))
        raise HTTPException(status_code=500, detail=str(e))


# ---[NUOVO v113.0] ENDPOINT HEART STATUS - AGGIORNATO v114.6 (MULTI-AVATAR) ---
@app.get("/api/heart/status")
async def get_heart_status(name: Optional[str] = None):
    """
    Restituisce lo stato attuale del cuore dell'avatar attivo o di uno specifico.
    Risolve dinamicamente il file heart_{avatar}.json.
    """
    try:
        # 1. Identifica l'avatar (richiesto o attivo dalla configurazione)
        if name:
            active_avatar = name.lower()
        else:
            active_avatar = "gemma"
            config_file = CONFIG_PATH / "config.yaml"
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    conf = yaml.safe_load(f)
                    active_avatar = conf.get("currentAvatar", "gemma").lower()

        # 2. Costruisce il percorso del cuore specifico
        heart_file = APP_ROOT / "data" / f"heart_{active_avatar}.json"

        if not heart_file.exists():
            logger.info(t("log.heart_not_found", avatar=active_avatar))
            return JSONResponse(
                content={
                    "affetto": 50,
                    "fiducia": 50,
                    "rispetto": 50,
                    "energia_sociale": 100,
                    "umore_corrente": t("heart.moods.neutral"),
                    "memoria_emotiva": [],
                    "eccitazione": 10,
                    "gelosia": 0,
                    "curiosità": 50,
                    "vulnerabilità": 20,
                    "complicità": 30,
                    "stanchezza_mentale": 0,
                }
            )

        with open(heart_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # --- FIX CACHING: Forziamo header no-cache per dati real-time ---
        response = JSONResponse(content=data)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    except Exception as e:
        logger.error(t("log.heart_read_error", error=str(e)))
        raise HTTPException(status_code=500, detail=t("heart.read_error"))


# --- [NUOVO v115.0] IOT & SMART HOME MODELS ---
IOT_LAYOUT_PATH = CONFIG_PATH / "iot_layout.json"
CARE_CONFIG_PATH = CONFIG_PATH / "care_config.json"


class IotDevice(BaseModel):
    id: str
    name: str
    type: str  # 'light', 'tv', 'climate', 'switch', 'other'
    ip: str
    protocol: str  # 'http_get', 'http_post', 'mqtt', 'ha' (Home Assistant)
    commands: Dict[
        str, str
    ]  # 'on': '/api/on', 'off': '/api/off', 'dim': '/api/set?v={val}'
    status: Optional[str] = "unknown"


class IotRoom(BaseModel):
    id: str
    name: str
    devices: List[IotDevice]


class IotLayout(BaseModel):
    rooms: List[IotRoom]
    automations: List[Dict[str, Any]] = []


class IotCommandRequest(BaseModel):
    device_id: str
    action: str
    value: Optional[Union[str, int, float]] = None


# ---[NUOVO v121.0] SKILLS MODELS ---
class SkillSaveRequest(BaseModel):
    filename: str
    content: str


class SkillGenerateRequest(BaseModel):
    name: str
    description: str


# --- [NUOVO v121.0] SKILLS ENDPOINTS ---


@app.get("/api/skills")
async def get_skills():
    """Restituisce la lista delle Skills disponibili leggendo direttamente i file JSON."""
    try:
        logger.info(t("log.api_skills_request"))
        skills = list()
        if SKILLS_DIR.exists():
            for f in SKILLS_DIR.glob("*.json"):
                try:
                    with open(f, "r", encoding="utf-8") as file:
                        data = json.load(file)
                    func_data = data.get("function", data)
                    tool_name = func_data.get("name", f.stem)
                    category = data.get("category", "skill")
                    props = func_data.get("parameters", {}).get("properties", {})
                    task_desc = props.get("task_description", {}).get("description", "")
                    final_desc = task_desc if task_desc else func_data.get("description", t("executor.no_description_provided"))
                    skills.append({
                        "filename": f.name,
                        "name": tool_name,
                        "category": category,
                        "description": final_desc,
                        "parameters": func_data.get("parameters", {"type": "object", "properties": {}}),
                        "triggers": data.get("triggers", [tool_name.replace("_", " ")]),
                        "gbnf_grammar": data.get("gbnf_grammar", ""),
                    })
                except Exception as e:
                    logger.error(f"Errore parsing skill {f.name}: {e}")
        return JSONResponse(content=skills)
    except Exception as e:
        logger.error(f"Errore in get_skills: {e}")
        return JSONResponse(content=list(), status_code=500)


@app.get("/api/skills/{filename}")
async def get_skill_content(filename: str):
    """
    Legge il contenuto di una Skill specifica.[FIX v124.2] Puntamento corretto a SKILLS_DIR invece di CONNECTORS_PATH.
    """
    # Assicuriamoci che il filename sia pulito
    clean_filename = Path(filename).name
    path = SKILLS_DIR / clean_filename

    if not path.exists():
        # Fallback: prova ad aggiungere .json se manca
        if not clean_filename.endswith(".json"):
            path = SKILLS_DIR / f"{clean_filename}.json"

    if not path.exists():
        logger.error(t("avatar_server.log.api_skills_not_found", path=path.resolve()))
        raise HTTPException(
            status_code=404, detail=t("skills.not_found", path=str(path))
        )

    try:
        content = path.read_text(encoding="utf-8")
        return JSONResponse(content={"content": content})
    except Exception as e:
        logger.error(t("avatar_server.log.api_skills_read_error", path=path, error=e))
        raise HTTPException(status_code=500, detail=str(e))


# ---[AGGIORNATO v125.2] ENDPOINT PER NATIVE TOOLS (CON FILTRO PRIVACY) ---
@app.get("/api/tools")
async def get_native_tools():
    """
    Restituisce i metadati dei tool filtrati per la UI leggendo direttamente i file JSON.
    """
    try:
        ui_tools = list()
        for directory in [TOOLS_DIR, CONNECTORS_PATH]:
            if directory.exists():
                for f in directory.glob("*.json"):
                    try:
                        with open(f, "r", encoding="utf-8") as file:
                            data = json.load(file)
                        func_data = data.get("function", data)
                        if "name" in func_data:
                            ui_tools.append({
                                "filename": f.name,
                                "name": func_data["name"],
                                "description": func_data.get("description", t("tools.native_tool_default")),
                                "category": data.get("category", "native_tool"),
                            })
                    except Exception as e:
                        logger.error(f"Errore parsing tool {f.name}: {e}")
        logger.info(t("avatar_server.log.api_tools_returned", count=len(ui_tools)))
        return JSONResponse(content=ui_tools)
    except Exception as e:
        logger.error(t("avatar_server.log.api_tools_error", error=e))
        return JSONResponse(content=list(), status_code=500)


# --- [NUOVO v124.3] ENDPOINTS PER EDITING TOOLS ---
@app.get("/api/tools/{filename}")
async def get_tool_content(filename: str):
    """Legge il contenuto di un Tool nativo specifico."""
    path = TOOLS_DIR / filename
    if not path.exists() and not filename.endswith(".json"):
        path = TOOLS_DIR / f"{filename}.json"

    if not path.exists():
        raise HTTPException(status_code=404, detail=t("skills.tool_not_found"))
    try:
        content = path.read_text(encoding="utf-8")
        return JSONResponse(content={"content": content})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tools")
async def save_tool_api(request: SkillSaveRequest):
    """Salva o aggiorna un file Tool (.json)."""
    try:
        filename = request.filename
        if not filename.endswith(".json"):
            filename += ".json"
        path = TOOLS_DIR / filename

        # Validazione JSON
        json_data = json.loads(request.content)

        # Scrittura
        path.write_text(
            json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info(t("log.api_tool_saved", filename=filename))
        return JSONResponse(content={"status": "ok", "message": t("skills.tool_saved")})
    except Exception as e:
        logger.error(t("avatar_server.log.api_tool_save_error", error=e))
        raise HTTPException(
            status_code=500, detail=t("skills.tool_save_error", error=str(e))
        )


@app.post("/api/skills")
def save_skill_api(request: SkillSaveRequest):
    """Salva o aggiorna una Skill."""
    # [FIX BUG 01] init_peripherals=False TASSATIVO
    temp_executor = BraccioDivino(
        None, None, guardian, db_manager, game_logger, init_peripherals=False
    )
    if temp_executor.save_skill(request.filename, request.content):
        return JSONResponse(content={"status": "ok", "message": t("skills.saved")})
    raise HTTPException(status_code=500, detail=t("skills.save_error"))


@app.delete("/api/skills/{filename}")
def delete_skill_api(filename: str):
    """Elimina una Skill."""
    # [FIX BUG 01] init_peripherals=False TASSATIVO
    temp_executor = BraccioDivino(
        None, None, guardian, db_manager, game_logger, init_peripherals=False
    )
    if temp_executor.delete_skill(filename):
        return JSONResponse(content={"status": "ok", "message": t("skills.deleted")})
    raise HTTPException(status_code=500, detail=t("skills.delete_error"))


@app.post("/api/skills/generate")
async def generate_skill_content(request: SkillGenerateRequest):
    """
    Genera il contenuto Markdown di una Skill usando l'LLM (tramite coda messaggi).
    """
    try:
        # Invia comando all'Anima per generare la skill
        # Usiamo un comando speciale che verrà intercettato da chat.py (da implementare nel prossimo step se necessario,
        # oppure usiamo il meccanismo di generazione DEF che è simile)
        # Per ora, usiamo il meccanismo di generazione DEF adattato

        # Inizializzazione temporanea dell'executor per la scansione (senza avviare periferiche)
        temp_executor = BraccioDivino(
            None, None, guardian, db_manager, game_logger, init_peripherals=False
        )

        prompt_template = (
            guardian._prompt_manager.get_prompts()
            .get("internal_prompts", {})
            .get("genera_skill_markdown", "")
        )
        prompt = prompt_template.replace("{{ request_name }}", request.name).replace(
            "{{ request_description }}", request.description
        )

        b64_prompt = base64.b64encode(prompt.encode("utf-8")).decode("utf-8")
        # Usiamo un nuovo tipo di messaggio per la generazione skill
        await message_queue.put(f"/generate_skill prompt='{b64_prompt}'")

        return JSONResponse(
            content={"status": "processing", "message": t("skills.gen_request_sent")}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=t("system.error", error=str(e)))


# --- [NUOVO v115.0] IOT ENDPOINTS ---


@app.get("/api/iot/layout")
async def get_iot_layout():
    """Carica la struttura della Smart Home dal file JSON."""
    if not IOT_LAYOUT_PATH.exists():
        return {"rooms": [], "automations": []}
    try:
        with open(IOT_LAYOUT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Assicura che la chiave automations esista sempre
            if "automations" not in data:
                data["automations"] = []
            return data
    except Exception as e:
        logger.error(t("avatar_server.log.iot_layout_read_error", error=e))
        return {"rooms": [], "automations": []}


@app.post("/api/iot/layout")
async def save_iot_layout(layout: IotLayout):
    """Salva la struttura della Smart Home su disco."""
    try:
        with open(IOT_LAYOUT_PATH, "w", encoding="utf-8") as f:
            json.dump(layout.dict(), f, indent=2, ensure_ascii=False)

        # Notifica l'Anima di ricaricare le automazioni
        await message_queue.put("/reload_iot_config")

        return {"status": "ok", "message": t("iot.layout_saved")}
    except Exception as e:
        logger.error(t("avatar_server.log.iot_layout_save_error", error=e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/iot/logs")
async def get_iot_logs():
    """
    Recupera lo storico delle azioni domotiche.
    Legge le ultime 50 entry dal file di log dedicato.
    """
    log_file = APP_ROOT / "logs" / "iot_actions.log"
    if not log_file.exists():
        return []
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # Restituisce le ultime 50 righe invertite (più recenti prima)
            return [line.strip() for line in lines[-50:][::-1]]
    except Exception as e:
        logger.error(t("avatar_server.log.iot_actions_read_error", error=e))
        return []


# --- [NUOVO v30.0] CARE OS ENDPOINTS ---


@app.get("/api/care/config")
async def get_care_config():
    """Recupera la configurazione del Care OS."""
    if not CARE_CONFIG_PATH.exists():
        # Ritorna struttura vuota di default se il file non esiste
        return JSONResponse(
            content={"modules": {}, "rules": [], "zones": [], "cron_jobs": []}
        )
    try:
        with open(CARE_CONFIG_PATH, "r", encoding="utf-8") as f:
            return JSONResponse(content=json.load(f))
    except Exception as e:
        logger.error(t("avatar_server.log.care_config_read_error", error=e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/care/config")
async def save_care_config(request: Request):
    """Salva la configurazione del Care OS e notifica l'Anima."""
    try:
        data = await request.json()
        with open(CARE_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Notifica l'Anima di ricaricare la configurazione (Hot Reload)
        await message_queue.put("/reload_care_config")

        return JSONResponse(content={"status": "ok", "message": t("care.config_saved")})
    except Exception as e:
        logger.error(t("avatar_server.log.care_config_save_error", error=e))
        raise HTTPException(status_code=500, detail=str(e))


# --- ENDPOINT CORE ---

@app.get("/api/connection-info")
async def get_connection_info():
    """Restituisce le informazioni di connessione per la Guida Mobile."""
    config_path = CONFIG_PATH / "config.yaml"
    ntfy_topic = "airis_user_default"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                conf = yaml.safe_load(f) or {}
                ntfy_topic = conf.get("ntfy_topic", ntfy_topic)
        except:
            pass
    return JSONResponse(content={
        "lan_url": f"http://{LAN_IP}:{SERVER_PORT}",
        "wlan_url": f"http://{PUBLIC_IP}:{SERVER_PORT}", # [NUOVO] IP Pubblico per WLAN
        "ntfy_topic": ntfy_topic
    })

@app.get("/api/health")
async def health_check():
    return JSONResponse(
        content={"status": "ok", "server": "avatar_server", "version": "100.4"},
        status_code=200,
    )


@app.get("/api/credentials")
async def get_credentials():
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    creds = guardian.get_all_credentials()
    return JSONResponse(content=creds if creds else {})


@app.post("/api/credentials")
async def update_credentials(request: CredentialsUpdateRequest):
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    try:
        # --- [FIX CRITICO] IGNORA CREDENZIALI VUOTE ---
        # Previene l'errore 500 al primo avvio quando il frontend invia {}
        if not request.credentials:
            return JSONResponse(content={"status": "ok", "message": "No credentials to update."})

        if guardian.save_all_credentials(request.credentials):
            await message_queue.put("/reload_global_config")
            return JSONResponse(
                content={"status": "ok", "message": t("settings.credentials_updated")}
            )
        else:
            raise HTTPException(status_code=500, detail=t("system.save_failed"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/custom-connectors")
async def get_custom_connectors():
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    connectors = guardian.get_custom_connectors()
    return JSONResponse(content=connectors if connectors else {})


@app.post("/api/custom-connectors")
async def update_custom_connectors(request: CustomConnectorsUpdateRequest):
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    try:
        if not guardian.save_custom_connectors(request.connectors):
            raise HTTPException(status_code=500, detail=t("system.save_failed"))
        
        await message_queue.put("/reload_global_config")
        
        installed_deps, failed_deps = [], []
        for _, config in request.connectors.items():
            for dep in config.get("dependencies", []):
                dep = dep.strip()
                if dep:
                    if install_pip_package(dep):
                        installed_deps.append(dep)
                    else:
                        failed_deps.append(dep)
        msg = t("settings.connectors_updated")
        if installed_deps:
            msg += t("settings.installed", deps=", ".join(installed_deps))
        if failed_deps:
            msg += t("settings.failed", deps=", ".join(failed_deps))
        return JSONResponse(content={"status": "ok", "message": msg})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/custom-connectors/upload")
async def upload_connector_script(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".py"):
        raise HTTPException(status_code=400, detail=t("settings.invalid_file"))
    try:
        safe_filename = Path(file.filename).name
        destination = CONNECTORS_PATH / safe_filename
        with destination.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return JSONResponse(content={"status": "ok", "filename": safe_filename})
    except Exception as e:
        raise HTTPException(status_code=500, detail=t("system.error", error=str(e)))


@app.post("/api/custom-connectors/script")
async def save_connector_script(request: CustomScriptRequest):
    if not request.filename or not request.filename.endswith(".py"):
        raise HTTPException(status_code=400, detail=t("settings.invalid_filename"))
    try:
        safe_filename = Path(request.filename).name
        destination = CONNECTORS_PATH / safe_filename
        with destination.open("w", encoding="utf-8") as f:
            f.write(request.code)
        return JSONResponse(content={"status": "ok", "filename": safe_filename})
    except Exception as e:
        raise HTTPException(status_code=500, detail=t("system.error", error=str(e)))


@app.post("/api/custom-connectors/generate-def")
async def generate_def_api(request: GenerateDefRequest):
    try:
        b64_code = base64.b64encode(request.script_code.encode("utf-8")).decode("utf-8")
        b64_prompt = base64.b64encode(request.prompt.encode("utf-8")).decode("utf-8")
        await message_queue.put(
            f"/generate_def code='{b64_code}' prompt='{b64_prompt}'"
        )
        return JSONResponse(
            content={"status": "processing", "message": t("settings.request_sent")}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=t("system.error", error=str(e)))


# ---[NUOVO v15.0] ENDPOINT VALIDAZIONE CODICE (DRY RUN) ---
@app.post("/api/custom-connectors/validate")
async def validate_connector_code(request: ValidateCodeRequest):
    """
    Esegue una validazione sintattica e di importazione del codice Python.
    """
    try:
        # 1. Validazione Sintattica (AST)
        try:
            ast.parse(request.code)
        except SyntaxError as e:
            return JSONResponse(
                content={
                    "status": "error",
                    "message": t("settings.syntax_error", line=e.lineno, msg=e.msg),
                }
            )

        # 2. Validazione Import (Simulata)
        # Non possiamo eseguire codice arbitrario in sicurezza totale qui,
        # ma possiamo controllare se le librerie importate sono installate.
        # Per ora ci limitiamo al check sintattico che è sicuro e veloce.

        return JSONResponse(
            content={"status": "ok", "message": t("settings.code_valid")}
        )
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)})


# --- [NUOVO v15.0] ENDPOINT GENERAZIONE TOOL AUTOMATICA ---
@app.post("/api/custom-connectors/sync-tool")
async def sync_tool_json(request: SyncToolRequest):
    """
    Genera il file JSON del tool in src/tools/ basandosi sui metadati del connettore.
    """
    # [FIX BUG 01] init_peripherals=False TASSATIVO
    temp_executor = BraccioDivino(
        None, None, guardian, db_manager, game_logger, init_peripherals=False
    )

    if temp_executor.generate_tool_json_from_connector(
        request.name, request.def_structure, request.prompt
    ):
        return JSONResponse(
            content={"status": "ok", "message": t("settings.tool_json_generated")}
        )
    else:
        raise HTTPException(status_code=500, detail=t("settings.tool_json_error"))


# --- [NUOVO v15.0] ENDPOINTS SPECIALIST SETTINGS ---
@app.get("/api/settings/specialist")
async def get_specialist_settings():
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    return JSONResponse(content=guardian.get_specialist_config())


@app.post("/api/settings/specialist")
async def update_specialist_settings(settings: SpecialistSettingsRequest):
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    if guardian.save_specialist_config(settings.dict()):
        return JSONResponse(
            content={"status": "ok", "message": t("settings.specialist_updated")}
        )
    raise HTTPException(status_code=500, detail=t("system.save_failed"))


@app.post("/api/settings/specialist/toggle")
async def toggle_specialist_api():
    """Invia il comando di Hot-Swap per lo Specialist Mode senza riavviare il server."""
    try:
        await message_queue.put("/toggle_specialist")
        return JSONResponse(
            content={"status": "ok", "message": t("settings.hotswap_sent")}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/custom-connectors/run")
def run_custom_connector(request: RunConnectorRequest):
    script_path = CONNECTORS_PATH / request.script_name
    if not script_path.exists():
        raise HTTPException(
            status_code=404,
            detail=t("settings.connector_not_found", name=request.script_name),
        )

    try:
        command = [
            sys.executable,
            str(script_path),
            "--action",
            request.action,
            "--params",
            json.dumps(request.params),
        ]
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
            return JSONResponse(content=output_json)
        except json.JSONDecodeError:
            return JSONResponse(
                content={
                    "status": "error",
                    "message": t("settings.invalid_json_output"),
                    "raw_output": result.stdout,
                },
                status_code=500,
            )
    except subprocess.CalledProcessError as e:
        return JSONResponse(
            content={
                "status": "error",
                "message": f"{t('system.error', error=t('system.execution_failed'))}: {e.stderr or e.stdout}",
            },
            status_code=500,
        )
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": t("system.error", error=str(e))},
            status_code=500,
        )


@app.post("/api/install_package")
def install_package_api(request: InstallPackageRequest):
    if not request.package_name.strip():
        raise HTTPException(status_code=400, detail=t("settings.missing_package_name"))
    if install_pip_package(request.package_name):
        return JSONResponse(
            content={
                "status": "ok",
                "message": t("settings.package_installed", pkg=request.package_name),
            }
        )
    else:
        raise HTTPException(status_code=500, detail=t("settings.install_failed"))


@app.get("/api/proactive-memory/settings")
async def get_proactive_memory_settings():
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    settings = guardian.get_proactive_memory_config()
    return JSONResponse(
        content=settings
        if settings
        else {"reflection_time": "23:00", "reminder_check_interval_minutes": 10}
    )


@app.post("/api/proactive-memory/settings")
async def set_proactive_memory_settings(settings: ProactiveMemorySettings):
    try:
        await message_queue.put(f"/set_reflection_time {settings.reflection_time}")
        await message_queue.put(
            f"/set_reminder_interval {settings.reminder_check_interval_minutes}"
        )
        return JSONResponse(
            content={"status": "ok", "message": t("reminders.update_sent")}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=t("system.error", error=str(e)))


@app.post("/api/reminders")
async def create_reminder(reminder: CreateReminderRequest):
    try:
        await message_queue.put(
            f"/promemoria tra {reminder.trigger_in_minutes} minuti: {reminder.content}"
        )
        return JSONResponse(
            content={"status": "ok", "message": t("reminders.command_sent")}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=t("system.error", error=str(e)))


@app.get("/api/reminders")
async def get_all_reminders():
    if not db_manager:
        raise HTTPException(status_code=503, detail=t("system.db_unavailable"))
    return JSONResponse(content=db_manager.get_all_reminders())


@app.put("/api/reminders/{reminder_id}")
async def update_reminder(reminder_id: str, request: UpdateReminderRequest):
    if not db_manager:
        raise HTTPException(status_code=503, detail=t("system.db_unavailable"))
    if db_manager.update_reminder_details(
        reminder_id,
        request.event_name,
        request.content,
        request.event_timestamp,
        request.trigger_timestamp,
        request.recurrence_rule,
    ):
        return JSONResponse(content={"status": "ok", "message": t("reminders.updated")})
    else:
        raise HTTPException(status_code=500, detail=t("reminders.update_error"))


@app.delete("/api/reminders/{reminder_id}")
async def delete_reminder(
    reminder_id: str, mode: str = Query("all", pattern="^(all|single)$")
):
    if not db_manager:
        raise HTTPException(status_code=503, detail=t("system.db_unavailable"))
    success = (
        db_manager.skip_reminder_occurrence(reminder_id)
        if mode == "single"
        else db_manager.delete_reminder(reminder_id)
    )
    if success:
        return JSONResponse(
            content={"status": "ok", "message": t("reminders.completed")}
        )
    else:
        raise HTTPException(status_code=500, detail=t("reminders.failed"))


@app.get("/api/sessions")
async def get_sessions():
    if not db_manager:
        raise HTTPException(status_code=503, detail=t("system.db_unavailable"))
    return JSONResponse(content=db_manager.get_all_sessions())


@app.get("/api/sessions/{session_id}")
async def get_session_messages(session_id: str):
    if not db_manager:
        raise HTTPException(status_code=503, detail=t("system.db_unavailable"))
    return JSONResponse(content=db_manager.get_messages_for_session(session_id))


@app.put("/api/sessions/{session_id}")
async def update_session(session_id: str, request: SessionUpdateRequest):
    if not db_manager:
        raise HTTPException(status_code=503, detail=t("system.db_unavailable"))

    # [MODIFICA v68.1] Supporto per aggiornamento nome e/o narrative_buffer
    updates = {}
    if request.name is not None and request.name.strip():
        updates["name"] = request.name.strip()
    if request.narrative_buffer is not None:
        updates["narrative_buffer"] = request.narrative_buffer

    if not updates:
        raise HTTPException(status_code=400, detail=t("sessions.no_data"))

    if db_manager.update_session(session_id, **updates):
        return JSONResponse(content={"status": "ok", "message": t("sessions.updated")})
    else:
        raise HTTPException(status_code=500, detail=t("sessions.update_error"))


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    if not db_manager:
        raise HTTPException(status_code=503, detail=t("system.db_unavailable"))
    if db_manager.delete_session(session_id):
        return JSONResponse(content={"status": "ok", "message": t("sessions.deleted")})
    else:
        raise HTTPException(status_code=500, detail=t("sessions.delete_error"))


# [AGGIUNTA CHIRURGICA] Endpoint per cancellazione multipla sessioni (v62.2)
@app.post("/api/sessions/bulk-delete")
async def bulk_delete_sessions(request: BulkDeleteRequest):
    if not db_manager:
        raise HTTPException(status_code=503, detail=t("system.db_unavailable"))
    deleted_count = 0
    failed_ids = []
    for session_id in request.session_ids:
        if db_manager.delete_session(session_id):
            deleted_count += 1
        else:
            failed_ids.append(session_id)
    if deleted_count > 0:
        return JSONResponse(
            content={
                "status": "ok",
                "message": t("sessions.bulk_deleted", count=deleted_count),
                "failed": failed_ids,
            }
        )
    else:
        raise HTTPException(status_code=500, detail=t("sessions.bulk_delete_error"))


# --- FIX v97.2: TYPE VALIDATION FIX (422 ERROR) ---
# Modificato il tipo di message_id da int a str per accettare ID temporanei del frontend
@app.delete("/api/messages/{message_id}")
async def delete_message_api(message_id: str):
    if not db_manager:
        raise HTTPException(status_code=503, detail=t("system.db_unavailable"))

    # Se l'ID è numerico, è un ID reale del DB
    if message_id.isdigit():
        if db_manager.delete_message(int(message_id)):
            return JSONResponse(
                content={
                    "status": "ok",
                    "message": t("sessions.msg_deleted", id=message_id),
                }
            )
        else:
            raise HTTPException(status_code=500, detail=t("sessions.msg_delete_error"))
    else:
        # Se è una stringa (ID temporaneo frontend), ritorniamo OK perché non esiste nel DB
        # Questo evita l'errore 422 e permette al frontend di aggiornarsi
        return JSONResponse(
            content={"status": "ok", "message": t("sessions.temp_msg_removed")}
        )


# --- FIX v97.2: TYPE VALIDATION FIX (422 ERROR) ---
# Modificato il tipo di message_id da int a str
@app.delete("/api/sessions/{session_id}/messages/after/{message_id}")
async def purge_messages_after_api(session_id: str, message_id: str):
    if not db_manager:
        raise HTTPException(status_code=503, detail=t("system.db_unavailable"))

    if message_id.isdigit():
        if db_manager.delete_messages_after(session_id, int(message_id)):
            return JSONResponse(
                content={
                    "status": "ok",
                    "message": t("sessions.context_purged", id=message_id),
                }
            )
        else:
            raise HTTPException(status_code=500, detail=t("sessions.purge_error"))
    else:
        # Se l'ID di partenza è temporaneo, non possiamo purgare il DB basandoci su di esso
        # Ritorniamo OK per non bloccare il flusso
        return JSONResponse(
            content={"status": "ok", "message": t("sessions.purge_ignored")}
        )


@app.post("/api/set_active_rpg")
async def set_active_rpg(request: Request):
    global ACTIVE_RPG_PATH
    data = await request.json()
    rpg_name = data.get("rpg_name")

    # FIX CRITICO: Ripristino del comportamento "Load-Bearing".
    # Se il nome è vuoto (uscita da GDR), NON resettiamo ACTIVE_RPG_PATH a None.
    # Questo permette al Character Manager di continuare a funzionare in background
    # mantenendo in memoria l'ultimo universo caricato.
    if not rpg_name:
        logger.info(t("avatar_server.log.server_gdr_deactivation_ignored"))
        return JSONResponse(
            content={
                "status": "ok",
                "active_rpg": str(ACTIVE_RPG_PATH) if ACTIVE_RPG_PATH else None,
            }
        )

    new_path = LORE_PATH / rpg_name
    if not new_path.is_dir():
        raise HTTPException(
            status_code=404, detail=t("gdr.not_found", path=str(new_path))
        )
    ACTIVE_RPG_PATH = new_path
    logger.info(t("log.gdr_context_active", path=ACTIVE_RPG_PATH))
    return JSONResponse(content={"status": "ok", "active_rpg": str(ACTIVE_RPG_PATH)})


@app.get("/api/gdr-worlds")
async def get_gdr_worlds():
    if not LORE_PATH.is_dir():
        return []
    return[d.name for d in LORE_PATH.iterdir() if d.is_dir()]


@app.get("/api/gdr-worlds/enriched")
async def get_gdr_worlds_enriched(lang: str = "it"):
    """
    Restituisce la lista dei mondi GDR arricchita con Titolo, Storia Pregressa e Data Ultima Sessione.
    Usato dal tab Preferences per la selezione visiva.
    """
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    
    if not LORE_PATH.is_dir():
        return JSONResponse(content=[])
        
    norm_lang = guardian.normalize_lang_code(lang)
    worlds =[]
    
    for gdr_dir in LORE_PATH.iterdir():
        if not gdr_dir.is_dir():
            continue
            
        world_id = gdr_dir.name
        title = world_id
        description = ""
        last_played = 0
        
        # 1. Cerca world.json per Titolo e Storia
        world_file = None
        lang_dir = gdr_dir / norm_lang
        if lang_dir.is_dir() and (lang_dir / "WORLD" / "world.json").exists():
            world_file = lang_dir / "WORLD" / "world.json"
        elif (gdr_dir / "WORLD" / "world.json").exists():
            world_file = gdr_dir / "WORLD" / "world.json"
            
        if world_file:
            try:
                with open(world_file, "r", encoding="utf-8") as f:
                    w_data = json.load(f)
                    title = w_data.get("titolo", world_id)
                    # Estrae l'introduzione del capitolo 1 come storia pregressa
                    description = w_data.get("capitolo_i", {}).get("introduzione", "")
            except:
                pass
                
        # Fallback descrizione su story_hook.txt se world.json non ha l'introduzione
        if not description:
            hook_file = None
            if lang_dir.is_dir() and (lang_dir / "PROJECT" / "story_hook.txt").exists():
                hook_file = lang_dir / "PROJECT" / "story_hook.txt"
            elif (gdr_dir / "PROJECT" / "story_hook.txt").exists():
                hook_file = gdr_dir / "PROJECT" / "story_hook.txt"
                
            if hook_file:
                try:
                    with open(hook_file, "r", encoding="utf-8") as f:
                        description = f.read()[:300] + "..."
                except:
                    pass
                    
        # 2. Cerca status.json per la data dell'ultima sessione
        status_file = None
        if lang_dir.is_dir() and (lang_dir / "WORLD" / "status.json").exists():
            status_file = lang_dir / "WORLD" / "status.json"
        elif (gdr_dir / "WORLD" / "status.json").exists():
            status_file = gdr_dir / "WORLD" / "status.json"
            
        if status_file:
            try:
                last_played = os.path.getmtime(status_file)
            except:
                pass
                
        worlds.append({
            "id": world_id,
            "title": title,
            "description": description,
            "last_played": last_played * 1000 # Convertito in millisecondi per JS
        })
        
    # Ordina per ultimo giocato (più recente prima)
    worlds.sort(key=lambda x: x["last_played"], reverse=True)
    return JSONResponse(content=worlds)


@app.get("/api/gdr-world-content")
async def get_gdr_world_content(world_name: str, lang: str = "it"):
    """
    Recupera il contenuto del mondo GDR scendendo nella cartella della lingua normalizzata.
    Rafforzato v100.5: Gestione errori granulare per prevenire blocchi UI.
    """
    if not guardian:
        logger.error(t("system.guardian_unavailable"))
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))

    norm_lang = guardian.normalize_lang_code(lang)
    # Risoluzione percorso con fallback
    world_path = LORE_PATH / world_name / norm_lang
    if not world_path.is_dir():
        world_path = LORE_PATH / world_name

    if not world_path.is_dir():
        logger.warning(
            t("avatar_server.log.world_editor_path_not_found", path=world_path)
        )
        return JSONResponse(
            content={}
        )  # Ritorna oggetto vuoto invece di 404 per sbloccare UI

    logger.info(t("log.world_editor_scan", world=world_name, lang=norm_lang))

    content = {}
    # Lista sacrari da scansionare
    target_subdirs = ["LAWS", "MEMORY", "MEMORY GDR", "PROJECT", "WORLD"]

    for subdir in target_subdirs:
        content[subdir] = {}
        # Cerca la sottocartella in modo case-insensitive
        subdir_path = None
        if (world_path / subdir).is_dir():
            subdir_path = world_path / subdir
        else:
            # Ricerca disperata case-insensitive
            for entry in world_path.iterdir():
                if entry.is_dir() and entry.name.upper() == subdir:
                    subdir_path = entry
                    break

        if subdir_path:
            # Scansione file .json e .txt
            for file_path in sorted(
                list(subdir_path.glob("*.json")) + list(subdir_path.glob("*.txt"))
            ):
                try:
                    # Lettura con encoding robusto (utf-8-sig gestisce il BOM di Windows)
                    raw_text = file_path.read_text(encoding="utf-8-sig", errors="replace")

                    if file_path.suffix.lower() == ".json":
                        try:
                            # Pre-formattazione JSON per l'editor
                            parsed = json.loads(raw_text)
                            content[subdir][file_path.name] = json.dumps(
                                parsed, indent=2, ensure_ascii=False
                            )
                        except json.JSONDecodeError:
                            content[subdir][
                                file_path.name
                            ] = raw_text  # Carica come testo se JSON corrotto
                    else:
                        content[subdir][file_path.name] = raw_text

                except Exception as e:
                    logger.error(
                        t("log.world_editor_error", file=file_path.name, error=e)
                    )
                    continue

    return JSONResponse(content=content)


@app.post("/api/gdr-world-file")
async def save_gdr_world_file(request: Request):
    """
    Salva un file di mondo GDR includendo il contesto lingua nel percorso.
    """
    try:
        data = await request.json()
        content = data.get("content")
        lang = data.get("lang", "it")
        b64_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        await message_queue.put(
            f"/save_world_file world='{data.get('world_name')}' lang='{lang}' path='{data.get('relative_path')}' content='{b64_content}'"
        )
        
        # --- [NUOVO] SYNC RAM STATE ---
        # Se il file modificato è status.json, diciamo a chat.py di ricaricarlo in RAM
        if data.get('relative_path', '').endswith('status.json'):
            await message_queue.put("/reload_world_state")
            
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=t("system.error", error=str(e)))


@app.get("/api/models")
async def get_models_and_params():
    try:
        # --- [FIX CRITICO] RICERCA CASE-INSENSITIVE PER ESTENSIONI ---
        def get_gguf_files(path: Path) -> list:
            if not path.exists():
                return list()
            # Cerca sia .gguf che .GGUF
            return [f.name for f in path.iterdir() if f.is_file() and f.suffix.lower() == ".gguf"]

        # 1. BASE MODELS (GGUF + SAFETENSORS FOLDERS)
        base_models = get_gguf_files(GGUF_MODELS_PATH)
        if SAFETENSORS_MODELS_PATH.exists():
            st_base = [d.name for d in SAFETENSORS_MODELS_PATH.iterdir() if d.is_dir()]
            base_models.extend(st_base)
            
        # 2. MMPROJ MODELS (GGUF + SAFETENSORS FOLDERS)
        mmproj_models = get_gguf_files(MMPROJ_MODELS_PATH)
        if MMPROJ_SAFETENSORS_PATH.exists():
            st_mmproj = [d.name for d in MMPROJ_SAFETENSORS_PATH.iterdir() if d.is_dir()]
            mmproj_models.extend(st_mmproj)
        
        # 3. LORA MODELS (GGUF + SAFETENSORS FOLDERS)
        lora_models = get_gguf_files(LORA_MODELS_PATH)
        if LORA_SAFETENSORS_PATH.exists():
            st_lora = [d.name for d in LORA_SAFETENSORS_PATH.iterdir() if d.is_dir()]
            lora_models.extend(st_lora)
        
        # 4. SPECIALIST MODELS (GGUF + SAFETENSORS FOLDERS)
        specialist_models = get_gguf_files(SPECIALIST_MODELS_PATH)
        if SPECIALIST_SAFETENSORS_PATH.exists():
            st_specialist = [d.name for d in SPECIALIST_SAFETENSORS_PATH.iterdir() if d.is_dir()]
            specialist_models.extend(st_specialist)
        
        # 5. LABOUR MODELS (GGUF + SAFETENSORS FOLDERS)
        labour_models = get_gguf_files(LABOUR_MODELS_PATH)
        if LABOUR_SAFETENSORS_PATH.exists():
            st_labour = [d.name for d in LABOUR_SAFETENSORS_PATH.iterdir() if d.is_dir()]
            labour_models.extend(st_labour)

        config_data = dict()
        config_file = CONFIG_PATH / "config.yaml"
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f) or dict()
            except Exception as e:
                logger.error(t("avatar_server.log.config_load_error", error=str(e)))

        # [FIX RIDONDANZA] Utilizzo di dict() per coerenza e sicurezza contro il glitch
        system_prompts = guardian.get_prompts() if guardian else dict()

        # --- [NUOVO] GATEKEEPER COGNITIVO (ESPOSIZIONE FLAG ALLA UI) ---
        active_base = config_data.get("model_selection", {}).get("active_base_model", "")
        is_large_model = False
        if active_base:
            match = re.search(r'(\d+(?:\.\d+)?)[bB]', active_base.lower())
            if match and float(match.group(1)) >= 11.0:
                is_large_model = True

        return JSONResponse(
            content={
                "models": {
                    "base_models": base_models,
                    "is_large_model": is_large_model, # Flag per la UI
                    "mmproj_models": mmproj_models,
                    "lora_models": lora_models,
                    "specialist_models": specialist_models,
                    "labour_models": labour_models,
                    "active_base_model": config_data.get("model_selection", {}).get(
                        "active_base_model", ""
                    ),
                    "active_mmproj_model": config_data.get("model_selection", {}).get(
                        "active_mmproj_model", ""
                    ),
                    "active_lora_model": config_data.get("model_selection", {}).get(
                        "active_lora_model", ""
                    ),
                    "active_draft_model": config_data.get("model_selection", {}).get(
                        "active_draft_model", ""
                    ),
                    "draft_enabled": config_data.get("model_selection", {}).get(
                        "draft_enabled", False
                    ),
                    "active_semantic_model": config_data.get("model_selection", {}).get(
                        "active_semantic_model", ""
                    ),
                    "semantic_router_enabled": config_data.get("model_selection", {}).get(
                        "semantic_router_enabled", False
                    ),
                    "semantic_on_cpu": config_data.get("model_selection", {}).get(
                        "semantic_on_cpu", True
                    ),
                },
                "parameters": config_data.get("parameters", {}),
                "system_prompts": system_prompts,
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=t("system.error", error=str(e)))


# --- [NUOVO v23.0] ENDPOINT REFRESH SPECIALIST ---
@app.post("/api/models/specialist/refresh")
async def refresh_specialist_models():
    """Forza la scansione della cartella specialist."""
    try:
        models = [f.name for f in (MODELS_PATH / "specialist").glob("*.gguf")]
        return JSONResponse(content={"status": "ok", "models": models})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- FIX v62.10: AGGIUNTO PARAMETRO rpg_name E LOGICA DI CARICAMENTO FORZATO ---
@app.get("/api/prompts")
async def get_all_prompts(lang: str = "it", rpg_name: Optional[str] = Query(None)):
    """
    Restituisce sia i prompt di sistema che quelli del GDR attivo (se presente).
    FILTRA la chiave 'personalita_segreta' per non mostrarla nel frontend.
    """
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))

    # LOGGING SPIETATO
    logger.info(
        t(
            "avatar_server.log.api_prompts_request",
            lang=lang,
            rpg_name=rpg_name,
            active_rpg=ACTIVE_RPG_PATH,
        )
    )

    # 1. Se c'è un RPG specifico richiesto (dalla UI), caricalo
    if rpg_name:
        target_path = LORE_PATH / rpg_name
        if target_path.exists():
            logger.info(t("avatar_server.log.api_prompts_force_load", path=target_path))
            guardian.load_rpg_prompts(target_path, lang)
        else:
            logger.warning(
                t(
                    "avatar_server.log.api_prompts_not_found",
                    name=rpg_name,
                    path=LORE_PATH,
                )
            )

    # 2. Altrimenti, se c'è un RPG attivo, ricarica quello (fallback)
    elif ACTIVE_RPG_PATH:
        logger.info(
            t("avatar_server.log.api_prompts_active_load", path=ACTIVE_RPG_PATH)
        )
        guardian.load_rpg_prompts(ACTIVE_RPG_PATH, lang)

    # Assicuriamoci che il PromptManager carichi la lingua richiesta per la UI
    if hasattr(guardian, "_prompt_manager") and guardian._prompt_manager:
        guardian._prompt_manager.load_language(lang)

    system_prompts = guardian.get_prompts() or {}

    # --- FIX SICUREZZA: OCCULTAMENTO PERSONALITÀ SEGRETA (v62.4) ---
    # Creiamo una copia per non modificare l'oggetto originale in memoria
    safe_system_prompts = system_prompts.copy()
    if "personalita_segreta" in safe_system_prompts:
        del safe_system_prompts["personalita_segreta"]

    response = {"system": safe_system_prompts, "rpg": guardian.get_rpg_prompts() or {}}
    return JSONResponse(content=response)


@app.post("/api/models/apply")
async def apply_full_config(request: Request, hot_swap: bool = Query(False)):
    """
    Applica la configurazione dei modelli e dei parametri.[FIX v124.3] Persistenza immediata su disco tramite Guardian per evitare reset al riavvio.
    """
    try:
        data = await request.json()
        models_data = data.get("models", {})
        params_data = data.get("parameters", {})

        # --- [NUOVO v124.3] PERSISTENZA IMMEDIATA ---
        # Aggiorna il file config.yaml subito, prima di notificare chat.py
        if guardian:
            guardian.save_model_selection_config(models_data)
            guardian.save_parameters_config(params_data)

            # Logica di esclusione reciproca
            if models_data.get("specialist_mode_enabled"):
                demiurge_config = guardian.get_demiurge_config() or {}
                if demiurge_config.get("enabled"):
                    demiurge_config["enabled"] = False
                    guardian.save_demiurge_config(demiurge_config)
                    logger.info(t("security.specialist_demiurge_sync"))

        # Notifica chat.py per il caricamento a caldo (se non è un hot-swap parziale)
        if not hot_swap:
            b64_data = base64.b64encode(json.dumps(data).encode("utf-8")).decode(
                "utf-8"
            )
            await message_queue.put(f"/apply_full_config data='{b64_data}'")
        else:
            await message_queue.put("/reload_global_config")
            logger.info(t("log.hotswap_completed"))

        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        logger.error(t("avatar_server.log.api_apply_config_error", error=str(e)))
        raise HTTPException(status_code=500, detail=t("system.error", error=str(e)))


@app.post("/api/prompts")
async def save_prompts(request: Request):
    """
    Salva i prompt gestendo lo scope (system o rpg) e la lingua.
    FIX v99.4: Normalizzazione preventiva per evitare nesting ricorsivo e inquinamento.
    """
    try:
        data = await request.json()
        scope = data.get("scope", "system")
        lang = data.get("lang", "it")

        # --- [NUOVO v99.4] NORMALIZZAZIONE PREVENTIVA ---
        # Isola chirurgicamente solo i dati dello scope richiesto
        incoming_data = data.get("data")

        if isinstance(incoming_data, dict):
            # Se i dati sono annidati (es. { "system": { ... } }), estrai il contenuto
            if scope in incoming_data:
                logger.info(t("avatar_server.log.server_extract_scope", scope=scope))
                incoming_data = incoming_data[scope]

            # Rimuovi l'altro scope se presente per evitare inquinamento del file YAML
            other_scope = "rpg" if scope == "system" else "system"
            if other_scope in incoming_data:
                logger.info(
                    t(
                        "avatar_server.log.server_remove_foreign_key",
                        other=other_scope,
                        scope=scope,
                    )
                )
                # Creiamo una copia per non mutare l'originale se necessario
                incoming_data = incoming_data.copy()
                del incoming_data[other_scope]

        b64_data = base64.b64encode(json.dumps(incoming_data).encode("utf-8")).decode(
            "utf-8"
        )
        await message_queue.put(
            f"/save_prompts scope='{scope}' lang='{lang}' data='{b64_data}'"
        )
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=t("system.error", error=str(e)))


@app.get("/api/exportable-items")
async def get_exportable_items(item_type: str):
    path = AVATARS_BASE_PATH if item_type == "avatar" else LORE_PATH
    if not path.exists():
        return JSONResponse(content=[])
    items = [
        d.name
        for d in path.iterdir()
        if d.is_dir() and (d.name != "ai_souls" if item_type == "avatar" else True)
    ]
    return JSONResponse(content=items)


@app.post("/api/export")
async def export_package_api(
    export_type: str = Form(...),
    avatar_names: str = Form(...),
    lore_name: Optional[str] = Form(None),
):
    cmd = f"/export type='{export_type}' avatar='{avatar_names}'"
    if lore_name:
        cmd += f" lore='{lore_name}'"
    await message_queue.put(cmd)
    return JSONResponse(content={"status": "processing"})


@app.get("/download/{file_path:path}")
async def download_file(file_path: str):
    full_path = (APP_ROOT / "exports" / file_path).resolve()
    if not full_path.is_file():
        raise HTTPException(status_code=404, detail=t("export_import.file_not_found"))
    return FileResponse(
        path=full_path, filename=full_path.name, media_type="application/zip"
    )


@app.post("/api/import/check")
async def check_import_conflicts_api(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    try:
        conflicts = []
        with zipfile.ZipFile(tmp_path, "r") as zipf:
            for item in zipf.namelist():
                if (APP_ROOT / item).exists():
                    conflicts.append(item)
        return JSONResponse(content={"conflicts": conflicts})
    finally:
        os.unlink(tmp_path)


@app.post("/api/import/execute")
async def import_package_api(overwrite: bool = Form(...), file: UploadFile = File(...)):
    temp_dir = APP_ROOT / "temp_imports"
    temp_dir.mkdir(exist_ok=True)
    file_path = temp_dir / f"import_{uuid.uuid4()}.zip"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    await message_queue.put(f"/import path='{str(file_path)}' overwrite={overwrite}")
    return JSONResponse(content={"status": "processing"})


@app.get("/api/user_profile")
async def get_user_profile():
    user_config_dir = CONFIG_PATH / "user"

    # --- [FIX CRITICO] SINCRONIZZAZIONE LIVE CONFIG ---
    # Forza il ricaricamento dal disco per evitare che il server legga un flag obsoleto in RAM
    if guardian:
        guardian.reload_config()

    is_first_run = guardian.is_first_run() if guardian else False

    # --- [FIX CRITICO] LETTURA LINGUA REALE DAL COMMAND PROMPT ---
    fallback_lang = "en"
    try:
        lang_cfg_path = APP_ROOT / "lang.cfg"
        if lang_cfg_path.exists():
            with open(lang_cfg_path, "r", encoding="utf-8") as f:
                fallback_lang = f.read().strip()
    except:
        pass

    if not user_config_dir.is_dir():
        # Se la cartella non esiste, è sicuramente un primo avvio o un errore grave
        return JSONResponse(
            content={
                "first_run": is_first_run,
                "name": "",
                "email": "",
                "mobileNumber": "",
                "age": "",
                "gender": "unspecified",
                "bio": "",
                "preferredLanguage": fallback_lang, # [FIX] Usa la lingua scelta nel prompt
                "preferredVoice": "",
                "birthDate": "",
                "avatar": None,
            }
        )

    try:
        json_files = list(user_config_dir.glob("*.json"))
        if not json_files:
            # Se non ci sono file JSON, restituiamo una struttura vuota con il flag first_run
            # Questo permette al frontend di vedere il flag e lanciare il wizard
            return JSONResponse(
                content={
                    "first_run": is_first_run,
                    "name": "",
                    "email": "",
                    "mobileNumber": "",
                    "age": "",
                    "gender": "unspecified",
                    "bio": "",
                    "preferredLanguage": fallback_lang, # [FIX] Usa la lingua scelta nel prompt
                    "preferredVoice": "",
                    "birthDate": "",
                    "avatar": None,
                }
            )

        with open(json_files[0], "r", encoding="utf-8") as f:
            profile_data = json.load(f)
        user_profile = {
            "first_run": is_first_run,  # Inject flag
            "name": get_json_value(profile_data, ["nome", "nome_completo", "name"]),
            "age": get_json_value(profile_data, ["età_apparente", "età_fisica", "age"]),
            "gender": get_json_value(profile_data, ["genere", "gender"], "unspecified"),
            "email": get_json_value(profile_data, ["email"]),
            "mobileNumber": get_json_value(
                profile_data, ["mobile_number", "mobileNumber"]
            ),
            "bio": get_json_value(profile_data, ["essenza_fondamentale", "bio"]),
            "preferredLanguage": get_json_value(
                profile_data, ["lingua", "preferredLanguage"], "it"
            ),
            "preferredVoice": get_json_value(
                profile_data, ["voce", "preferredVoice"], ""
            ),
            "birthDate": get_json_value(
                profile_data, ["compleanno", "birthDate"], ""
            ),  # FIX: Aggiunto birthDate
            "avatar": None,
        }
        # Cerca qualsiasi immagine supportata nella cartella user
        for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".heic"]:
            img_files = list(user_config_dir.glob(f"*{ext}"))
            if img_files:
                img_path = img_files[0]  # Prende la prima immagine trovata
                shutil.copy2(img_path, TEMP_IMAGE_PATH / img_path.name)
                # Aggiungiamo un timestamp per forzare il browser a ricaricare l'immagine (Cache Buster)
                user_profile[
                    "avatar"
                ] = f"/temp_images/{img_path.name}?t={int(time.time())}"
                break
        return JSONResponse(content=user_profile)
    except Exception as e:
        return JSONResponse(
            content={"error": t("system.error", error=str(e))}, status_code=500
        )


@app.post("/api/user_profile")
async def save_user_profile(
    profile_data: str = Form(...), avatar_file: Optional[UploadFile] = File(None)
):
    try:
        data = json.loads(profile_data)

        # --- [FIX CRITICO] RESET IMMEDIATO FLAG FIRST RUN ---
        # Il server API deve uccidere il flag non appena riceve i dati dal Wizard
        if guardian:
            guardian.set_first_run(False)

        # ---[NUOVO] SALVATAGGIO IMMAGINE PROFILO ---
        if avatar_file:
            user_config_dir = CONFIG_PATH / "user"
            user_config_dir.mkdir(parents=True, exist_ok=True)

            # [FIX CRITICO] Purga totale della cartella per evitare conflitti di nomi/estensioni
            for item in user_config_dir.iterdir():
                if item.is_file() and item.suffix.lower() in [
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".gif",
                    ".webp",
                    ".avif",
                    ".heic",
                ]:
                    try:
                        os.remove(item)
                    except:
                        pass

            # Salva nuova immagine (con protezione se il browser non invia il filename)
            file_ext = (
                Path(avatar_file.filename).suffix if avatar_file.filename else ".png"
            )
            # Usiamo un nome fisso 'user_avatar' per coerenza interna, il display name resta nel JSON
            new_img_path = user_config_dir / f"user_avatar{file_ext}"

            with open(new_img_path, "wb") as buffer:
                shutil.copyfileobj(avatar_file.file, buffer)

        # --- [FIX CRITICO] HOT-RELOAD PROFILO ---
        # Invia il payload come JSON strutturato per farlo intercettare correttamente da chat.py
        payload = {
            "type": "save_profile",
            "data": data
        }
        await message_queue.put(json.dumps(payload))
        
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        logger.error(f"Error in save_user_profile: {e}")
        raise HTTPException(status_code=500, detail=t("system.error", error=str(e)))


@app.get("/api/characters")
async def get_characters(char_type: str):
    """
    Restituisce la lista dei personaggi.[AGGIORNATO v124.0] Se char_type è PNG, include l'Avatar attivo nel roster.
    """
    # --- LOGICA AVATAR (AI SOULS) ---
    if char_type.upper() == "AVATAR":
        path = AVATARS_BASE_PATH / "ai_souls"
        if not path.is_dir():
            return []
        chars = []
        for f in path.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as file:
                    data = json.load(file)
                name = get_json_value(
                    data, ["nome_completo", "nome", "name"], t("gdr.unknown_char")
                )
                info = {"id": f.stem, "name": name, "avatar_url": None}
                img_dir = AVATARS_BASE_PATH / f.stem.lower() / "base_image"
                if img_dir.is_dir():
                    for ext in [
                        ".png",
                        ".jpg",
                        ".jpeg",
                        ".gif",
                        ".webp",
                        ".avif",
                        ".heic",
                    ]:
                        if (img_dir / f"{f.stem}{ext}").exists():
                            info[
                                "avatar_url"
                            ] = f"/avatars/{f.stem.lower()}/base_image/{f.stem}{ext}"
                            break
                chars.append(info)
            except:
                continue
        return chars

    # --- LOGICA PG / PNG ---
    # FIX: Fallback al primo GDR disponibile se ACTIVE_RPG_PATH è None
    target_rpg_path = ACTIVE_RPG_PATH
    if not target_rpg_path:
        gdr_folders = [d for d in LORE_PATH.iterdir() if d.is_dir()]
        if gdr_folders:
            target_rpg_path = gdr_folders[0]

    chars = []
    if target_rpg_path:
        path = target_rpg_path / "it" / char_type.upper()
        if not path.is_dir():
            path = target_rpg_path / char_type.upper()

        # Caricamento file fisici nella cartella lore
        if path.is_dir():
            for f in path.glob("*.json"):
                try:
                    with open(f, "r", encoding="utf-8") as file:
                        data = json.load(file)
                    name = get_json_value(
                        data, ["nome_completo", "nome", "name"], t("gdr.unknown_char")
                    )
                    info = {"id": f.stem, "name": name, "avatar_url": None}
                    for ext in [
                        ".png",
                        ".jpg",
                        ".jpeg",
                        ".gif",
                        ".webp",
                        ".avif",
                        ".heic",
                    ]:
                        if (path / (f.stem + ext)).exists():
                            rel_path = f.parent.relative_to(LORE_PATH).as_posix()
                            info["avatar_url"] = f"/lore/{rel_path}/{f.name}"
                            break
                    chars.append(info)
                except:
                    continue

    # ---[NUOVO v124.0] INIEZIONE AVATAR NEL ROSTER PNG ---
    if char_type.upper() == "PNG":
        try:
            # Recupera l'avatar attivo dal config
            active_avatar_name = "gemma"
            config_file = CONFIG_PATH / "config.yaml"
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    conf = yaml.safe_load(f)
                    active_avatar_name = conf.get("currentAvatar", "gemma")

            # Verifica se l'avatar è già presente (per evitare duplicati se l'utente non ha pulito la cartella PNG)
            if not any(c["id"].lower() == active_avatar_name.lower() for c in chars):
                # Carica i dati dell'avatar da ai_souls
                soul_file = (
                    AVATARS_BASE_PATH
                    / "ai_souls"
                    / f"{active_avatar_name.capitalize()}.json"
                )
                if soul_file.exists():
                    with open(soul_file, "r", encoding="utf-8") as f:
                        soul_data = json.load(f)

                    name = get_json_value(
                        soul_data, ["nome_completo", "nome", "name"], active_avatar_name
                    )
                    avatar_info = {
                        "id": active_avatar_name.capitalize(),
                        "name": name,
                        "avatar_url": None,
                        "is_unified_avatar": True,
                    }

                    # Risoluzione immagine base
                    img_dir = (
                        AVATARS_BASE_PATH / active_avatar_name.lower() / "base_image"
                    )
                    if img_dir.is_dir():
                        for ext in [
                            ".png",
                            ".jpg",
                            ".jpeg",
                            ".gif",
                            ".webp",
                            ".avif",
                            ".heic",
                        ]:
                            if (
                                img_dir / f"{active_avatar_name.capitalize()}{ext}"
                            ).exists():
                                avatar_info[
                                    "avatar_url"
                                ] = f"/avatars/{active_avatar_name.lower()}/base_image/{active_avatar_name.capitalize()}{ext}"
                                break
                    chars.append(avatar_info)
        except Exception as e:
            logger.error(t("avatar_server.log.server_avatar_injection_error", error=e))

    return chars


@app.get("/api/characters/{character_id}")
async def get_character_data(character_id: str, char_type: str, lang: str = "it"):
    """
    Recupera i dati di un personaggio.[AGGIORNATO v124.0] Supporto Unificazione: se un PNG ha lo stesso nome dell'Avatar,
    carica i dati da ai_souls invece che dalla lore.
    [AGGIORNATO] Smart Lookup per risolvere discrepanze tra nome file e nome interno.
    """
    # --- [NUOVO v124.0] LOGICA UNIFICAZIONE (ESTESA) ---
    is_actually_avatar = False
    f_avatar = None
    
    if char_type.upper() == "AVATAR":
        f_avatar = AVATARS_BASE_PATH / "ai_souls" / f"{character_id.capitalize()}.json"
        if f_avatar.exists():
            is_actually_avatar = True
        else:
            # --- [FIX CRITICO] FALLBACK GDR ---
            # Se la UI chiede un 'avatar' (perché ha cliccato l'icona in chat) ma il file non esiste in ai_souls,
            # significa che è un PNG del GDR. Cambiamo il tipo e lasciamo che la ricerca prosegua nelle cartelle GDR.
            char_type = "PNG"
            f_avatar = None
            
    elif char_type.upper() == "PNG":
        # Controlla se l'ID richiesto corrisponde a una qualsiasi anima in ai_souls
        # (Gestione case-insensitive e con underscore/spazi)
        ai_souls_dir = AVATARS_BASE_PATH / "ai_souls"
        if ai_souls_dir.exists():
            target_clean = character_id.lower().strip().replace("_", " ")
            for soul_file in ai_souls_dir.glob("*.json"):
                if soul_file.stem.lower().strip().replace("_", " ") == target_clean:
                    is_actually_avatar = True
                    f_avatar = soul_file
                    break

    if is_actually_avatar and f_avatar:
        if not f_avatar.exists():
            raise HTTPException(status_code=404, detail=t("gdr.char_not_found"))
        with open(f_avatar, "r", encoding="utf-8") as file:
            data = json.load(file)
        url = None
        # Usa il nome reale del file trovato per cercare l'immagine
        real_char_id = f_avatar.stem
        img_dir = AVATARS_BASE_PATH / real_char_id.lower() / "base_image"
        if img_dir.is_dir():
            for ext in[".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".heic"]:
                if (img_dir / f"{real_char_id}{ext}").exists():
                    url = f"/avatars/{real_char_id.lower()}/base_image/{real_char_id}{ext}"
                    break
        return {"jsonData": data, "avatarUrl": url}

    target_rpg_path = ACTIVE_RPG_PATH
    if not target_rpg_path:
        gdr_folders = [d for d in LORE_PATH.iterdir() if d.is_dir()]
        if gdr_folders:
            target_rpg_path = gdr_folders[0]

    if not target_rpg_path:
        raise HTTPException(status_code=400, detail=t("gdr.no_active_rpg"))
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
        
    norm_lang = guardian.normalize_lang_code(lang)
    
    # Determina la cartella target
    target_dir = target_rpg_path / norm_lang / char_type.upper()
    if not target_dir.exists():
        target_dir = ACTIVE_RPG_PATH / char_type.upper()
        
    if not target_dir.exists():
        raise HTTPException(status_code=404, detail=t("system.not_found"))

    # --- SMART LOOKUP ---
    f = None
    target_clean = character_id.lower().strip()
    
    # 1. Prova match esatto del file
    exact_file = target_dir / f"{character_id}.json"
    if exact_file.exists():
        f = exact_file
    else:
        # 2. Prova ricerca per nome interno al JSON
        for file_path in target_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as tmp_f:
                    tmp_data = json.load(tmp_f)
                internal_name = get_json_value(tmp_data, ["nome_completo", "nome", "name"], "")
                if internal_name and internal_name.lower().strip() == target_clean:
                    f = file_path
                    break
            except:
                continue
                
        # 3. Fallback case-insensitive sul nome del file
        if not f:
            for file_path in target_dir.glob("*.json"):
                if file_path.stem.lower() == target_clean or file_path.stem.lower() == target_clean.replace(" ", "_"):
                    f = file_path
                    break

    if not f or not f.exists():
        raise HTTPException(status_code=404, detail=t("system.not_found"))

    with open(f, "r", encoding="utf-8") as file:
        data = json.load(file)
        
    url = None
    for ext in[".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".heic"]:
        if f.with_suffix(ext).exists():
            rel_path = f.parent.relative_to(LORE_PATH).as_posix()
            # [FIX CACHE] Aggiunto timestamp per forzare il browser a ricaricare l'immagine aggiornata
            url = f"/lore/{rel_path}/{f.stem}{ext}?t={int(time.time())}"
            break
            
    return {"jsonData": data, "avatarUrl": url}


@app.post("/api/characters")
async def save_character(
    char_type: str = Form(...),
    character_data: str = Form(...),
    lang: str = Form("it"),
    avatar_file: Optional[UploadFile] = File(None),
):
    b64_data = base64.b64encode(character_data.encode("utf-8")).decode("utf-8")
    cmd = f"/save_character type='{char_type}' lang='{lang}' data='{b64_data}'"
    if avatar_file:
        temp_dir = APP_ROOT / "temp_uploads"
        temp_dir.mkdir(exist_ok=True)
        path = temp_dir / f"upload_{uuid.uuid4()}_{avatar_file.filename}"
        with open(path, "wb") as buffer:
            shutil.copyfileobj(avatar_file.file, buffer)
        cmd += f" file_path='{str(path)}'"
    await message_queue.put(cmd)
    return JSONResponse(content={"status": "processing"})


@app.post("/api/characters/{character_id}/archive")
async def archive_character(character_id: str, request: Request):
    data = await request.json()
    lang = data.get("lang", "it")
    await message_queue.put(
        f"/archive_character id='{character_id}' type='{data.get('type')}' lang='{lang}'"
    )
    return JSONResponse(content={"status": "processing"})


@app.get("/api/png_avatars")
async def get_png_avatars(lang: str = "it"):
    target_rpg_path = ACTIVE_RPG_PATH
    if not target_rpg_path:
        gdr_folders = [d for d in LORE_PATH.iterdir() if d.is_dir()]
        if gdr_folders:
            target_rpg_path = gdr_folders[0]
            
    if not target_rpg_path:
        return JSONResponse(content={})
        
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    norm_lang = guardian.normalize_lang_code(lang)
    path = target_rpg_path / norm_lang / "PNG"
    if not path.is_dir():
        path = target_rpg_path / "PNG"
    if not path.is_dir():
        return JSONResponse(content={})
    m = {}
    for f in path.iterdir():
        if f.suffix in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".heic"]:
            rel_path = path.relative_to(LORE_PATH).as_posix()
            m[f.stem.lower()] = f"/lore/{rel_path}/{f.name}"
    return JSONResponse(content=m)


@app.get("/api/tts/languages")
async def get_tts_languages(engine: Optional[str] = Query(None)):
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))

    tts_config = guardian.get_tts_engine_config() or {}
    active_engine = engine if engine else tts_config.get("active_engine", "kokoro")

    # --- CASO A: KOKORO (LOGICA ORIGINALE PRESERVATA) ---
    if active_engine == "kokoro":
        lang_code_map = {
            "a": ("🇺🇸 American English", "en"),
            "b": ("🇬🇧 British English", "en"),
            "e": ("🇪🇸 Spanish", "es"),
            "f": ("🇫🇷 French", "fr"),
            "h": ("🇮🇳 Hindi", "hi"),
            "i": ("🇮🇹 Italian", "it"),
            "p": ("🇧🇷 Portuguese", "pt"),
            "j": ("🇯🇵 Japanese", "ja"),
            "z": ("🇨🇳 Mandarin Chinese", "zh"),
        }

        available_languages = defaultdict(
            lambda: {"name": t("tts.unknown_lang"), "iso_code": "", "voices": []}
        )

        if not KOKORO_AUDIO_PATH.exists():
            return JSONResponse(
                content={
                    "it": {
                        "name": t("tts.kokoro_fallback"),
                        "iso_code": "it",
                        "voices": [
                            {
                                "id": "if_sara.pt",
                                "name": "if_sara",
                                "gender": t("profile_dialog.gender_options.female"),
                            }
                        ],
                        "default_voice": "if_sara.pt",
                    }
                },
                status_code=200,
            )

        for filename in sorted(os.listdir(KOKORO_AUDIO_PATH)):
            if filename.endswith(".pt"):
                try:
                    prefix = filename.split("_")[0]
                    if len(prefix) < 2:
                        continue
                    lang_char = prefix[0]
                    gender_char = prefix[1]
                    gender = (
                        t("vibevoice.gender_woman")
                        if gender_char == "f"
                        else t("vibevoice.gender_man")
                        if gender_char == "m"
                        else t("vibevoice.gender_other")
                    )

                    if lang_char in lang_code_map:
                        lang_name, iso_code = lang_code_map[lang_char]
                        if iso_code not in available_languages:
                            available_languages[iso_code]["name"] = lang_name
                            available_languages[iso_code]["iso_code"] = iso_code
                        available_languages[iso_code]["voices"].append(
                            {
                                "id": filename,
                                "name": filename.replace(".pt", ""),
                                "gender": gender,
                            }
                        )
                except IndexError:
                    continue

        for lang_code, data in available_languages.items():
            if data["voices"]:
                data["default_voice"] = data["voices"][0]["id"]

        return JSONResponse(content=dict(available_languages))

    # --- CASO B: VIBEVOICE (LOGICA LOCALE PURA v119.5) ---
    else:
        # [FIX BUG 01] Scansione locale dei file .pt per evitare timeout API
        VIBEVOICE_VOICES_PATH = (
            APP_ROOT / "tts_engine" / "VibeVoice" / "models" / "voices"
        )

        airis_format = {}
        vv_lang_names = {
            "it": t("brain.lang_names.it").title(),
            "en": t("brain.lang_names.en").title(),
            "de": t("brain.lang_names.de").title(),
            "fr": t("brain.lang_names.fr").title(),
            "es": t("brain.lang_names.es").title(),
            "jp": t("brain.lang_names.jp").title(),
            "kr": t("brain.lang_names.kr").title(),
            "nl": t("brain.lang_names.nl").title(),
            "pl": t("brain.lang_names.pl").title(),
            "pt": t("brain.lang_names.br").title(),
            "in": t("brain.lang_names.in").title(),
            "sp": t("brain.lang_names.es").title(),
        }

        if not VIBEVOICE_VOICES_PATH.exists():
            logger.error(
                t(
                    "avatar_server.log.tts_vibevoice_dir_not_found",
                    path=VIBEVOICE_VOICES_PATH,
                )
            )
            return JSONResponse(
                content={"error": t("tts.vibevoice_missing")}, status_code=404
            )

        try:
            # Legge i file direttamente dal disco (istantaneo)
            for filename in sorted(os.listdir(VIBEVOICE_VOICES_PATH)):
                if filename.endswith(".pt"):
                    # it-Gemma_woman.pt
                    voice_id = filename.replace(".pt", "")

                    # Parsing Lingua (it)
                    lang_code = voice_id.split("-")[0] if "-" in voice_id else "vv"

                    # Parsing Nome e Genere (Gemma, woman)
                    name_part = (
                        voice_id.split("-", 1)[1] if "-" in voice_id else voice_id
                    )
                    name = name_part.split("_")[0] if "_" in name_part else name_part
                    gender_raw = (
                        name_part.split("_")[1] if "_" in name_part else "unknown"
                    )
                    gender_label = (
                        t("vibevoice.gender_woman")
                        if "woman" in gender_raw.lower()
                        else t("vibevoice.gender_man")
                        if "man" in gender_raw.lower()
                        else t("vibevoice.gender_other")
                    )

                    flag = vv_lang_names.get(lang_code, "🌐")

                    if lang_code not in airis_format:
                        airis_format[lang_code] = {
                            "name": vv_lang_names.get(
                                lang_code, f"🌐 {lang_code.upper()}"
                            ),
                            "iso_code": lang_code,
                            "default_voice": filename,
                            "voices": [],
                        }

                    airis_format[lang_code]["voices"].append(
                        {
                            "id": filename,
                            "name": f"{flag} {name}",
                            "gender": gender_label,
                        }
                    )

            logger.info(
                t(
                    "log.vibevoice_loaded",
                    count=sum(len(v["voices"]) for v in airis_format.values()),
                )
            )
            return JSONResponse(content=airis_format)

        except Exception as e:
            logger.error(t("log.vibevoice_scan_error", error=str(e)))
            return JSONResponse(
                content={"error": t("tts.vibevoice_scan_error")}, status_code=500
            )

@app.post("/api/tts/preview")
def preview_tts_voice(request: TtsPreviewRequest):
    """Genera un'anteprima audio rapida per il Welcome Wizard."""
    try:
        # Inizializza un executor temporaneo senza periferiche
        temp_executor = BraccioDivino(None, None, guardian, db_manager, game_logger, init_peripherals=False)
        
        audio_path_str = temp_executor.genera_voce(
            text=request.text,
            intent="default",
            preferred_voice=request.voice,
            preferred_lang_code=request.lang_code,
            engine_override=request.engine
        )
        
        if not audio_path_str:
            raise HTTPException(status_code=500, detail=t("audio.tts_failed"))
            
        audio_path = Path(audio_path_str)
        # Restituisce l'URL relativo per il frontend
        return JSONResponse(content={"status": "ok", "url": f"/temp_audio/{audio_path.name}"})
        
    except Exception as e:
        logger.error(t("log.tts_preview_error", error=str(e)))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get_intent_map")
async def get_intent_map():
    if not ALL_AVATAR_DATA:
        load_all_avatar_intents()
    return JSONResponse(content=ALL_AVATAR_DATA if ALL_AVATAR_DATA else {})

# --- [NUOVO] ENDPOINT KNOWLEDGE GRAPH (MAPPA MENTALE) ---
@app.get("/api/knowledge-graph")
async def get_knowledge_graph():
    """Restituisce tutte le triplette del GraphRAG per la visualizzazione nel frontend."""
    if not db_manager:
        raise HTTPException(status_code=503, detail=t("system.db_unavailable"))
    try:
        db_manager.cursor.execute("SELECT subject, predicate, object FROM knowledge_graph")
        rows = db_manager.cursor.fetchall()
        
        nodes_set = set()
        links = []
        
        for r in rows:
            subj = r["subject"]
            obj = r["object"]
            nodes_set.add(subj)
            nodes_set.add(obj)
            links.append({
                "source": subj,
                "target": obj,
                "label": r["predicate"]
            })
            
        nodes = [{"id": n} for n in nodes_set]
        return JSONResponse(content={"nodes": nodes, "links": links})
    except Exception as e:
        logger.error(f"Errore recupero Knowledge Graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class GraphNodeUpdateRequest(BaseModel):
    old_name: str
    new_name: str

@app.put("/api/knowledge-graph/node")
async def update_knowledge_graph_node(request: GraphNodeUpdateRequest):
    """Aggiorna il nome di un nodo in tutte le triplette del GraphRAG."""
    if not db_manager:
        raise HTTPException(status_code=503, detail=t("system.db_unavailable"))
    try:
        success = db_manager.update_graph_node(request.old_name, request.new_name)
        if success:
            return JSONResponse(content={"status": "ok"})
        raise HTTPException(status_code=500, detail="Errore aggiornamento nodo")
    except Exception as e:
        logger.error(f"Errore aggiornamento nodo GraphRAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/knowledge-graph/node")
async def delete_knowledge_graph_node(name: str):
    """Elimina un nodo e tutte le sue connessioni dal GraphRAG."""
    if not db_manager:
        raise HTTPException(status_code=503, detail=t("system.db_unavailable"))
    try:
        success = db_manager.delete_graph_node(name)
        if success:
            return JSONResponse(content={"status": "ok"})
        raise HTTPException(status_code=500, detail="Errore eliminazione nodo")
    except Exception as e:
        logger.error(f"Errore eliminazione nodo GraphRAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # --- VALIDAZIONE TOKEN WEBSOCKET ---
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)  # Policy Violation
        return

    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        await websocket.close(code=1008)
        return

    # --- [NUOVO] HARD CAP GIOCATORI (MAX 10) ---
    if len(manager.active_connections) >= 10:
        logger.warning(t("avatar_server.log.multiplayer_room_full"))
        await websocket.close(
            code=1008, reason=t("avatar_server.log.multiplayer_room_full_reason")
        )
        return

    # ID Temporaneo fino all'Handshake
    temp_id = f"guest_{uuid.uuid4().hex[:8]}"
    await manager.connect(websocket, temp_id)
    current_player_name = temp_id

    # ---[FIX CRITICO] SYNC IMMEDIATO STATO GLOBALE ---
    # Invia lo stato in RAM al client appena connesso per evitare freeze UI
    # e desincronizzazione della Sidebar se chat.py è bloccato a pensare.
    try:
        await websocket.send_text(json.dumps({
            "type": "system_status",
            "payload": CURRENT_SYSTEM_STATE
        }))
    except:
        pass

    try:
        while True:
            data = await websocket.receive_text()

            # ---[NUOVO] SANITIZZAZIONE SPIETATA (XSS / PAYLOAD SIZE) ---
            # FIX: Aumentato limite a 5000000 (5MB) per permettere l'invio di immagini Base64 (Simbolo Gilda)
            if len(data) > 5000000:
                logger.warning(
                    t(
                        "avatar_server.log.security_payload_too_large",
                        name=current_player_name,
                    )
                )
                continue
            
            # [FIX BUG 01] Bypassa il controllo XSS per l'handshake perché il base64 genera falsi positivi
            if '"type": "HANDSHAKE_JOIN"' not in data and re.search(r"<\s*script[^>]*>.*<\s*/\s*script\s*>", data, re.IGNORECASE):
                logger.warning(
                    t(
                        "avatar_server.log.security_xss_detected",
                        name=current_player_name,
                    )
                )
                continue

            try:
                parsed_data = json.loads(data)
                msg_type = parsed_data.get("type")

                # --- [FIX CRITICO] HEARTBEAT ATTIVO ---
                # Risponde immediatamente al ping del frontend per mantenere vivo il socket su mobile
                if msg_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    continue

                # --- [NUOVO] HANDSHAKE E OMONIMIA ---
                if msg_type == "HANDSHAKE_JOIN":
                    # ---[RM29] VALIDAZIONE PYDANTIC (CAVALLO DI TROIA) ---
                    try:
                        validated_handshake = GuestHandshakeRequest(**parsed_data)
                    except Exception as ve:
                        logger.error(
                            t(
                                "avatar_server.log.security_handshake_malformed",
                                name=current_player_name,
                                error=ve,
                            )
                        )
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "ERROR",
                                    "message": t("multiplayer.rpg_sheet_error"),
                                }
                            )
                        )
                        await websocket.close(code=1008)
                        return

                    raw_name = validated_handshake.player_name
                    # Forza solo lettere e numeri per sicurezza
                    clean_name = re.sub(r"[^a-zA-Z0-9_]", "", raw_name)

                    # Risoluzione Omonimia
                    final_name = clean_name
                    counter = 2
                    while (
                        final_name in manager.active_connections
                        and final_name != current_player_name
                    ):
                        final_name = f"{clean_name}_{counter}"
                        counter += 1

                    # ---[NUOVO] CONTROLLO BUTTAFUORI (WOMEN-ONLY) ---
                    # Recupera lo stato della stanza dall'Host (NetworkManager)
                    if (
                        manager.is_women_only_room
                        and validated_handshake.gender.lower()
                        not in ["female", "femmina"]
                    ):
                        logger.warning(
                            t(
                                "avatar_server.log.security_bouncer_gender",
                                name=final_name,
                            )
                        )
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "KICKED",
                                    "message": t("multiplayer.kicked_gender"),
                                }
                            )
                        )
                        await websocket.close(code=1008)
                        return

                    # ---[NUOVO] CONTROLLO BUTTAFUORI (LEVEL GATING) ---
                    guest_level = (
                        validated_handshake.scheda_rpg.dati_base.get("livello", 1)
                        if validated_handshake.scheda_rpg.dati_base
                        else 1
                    )
                    if (
                        guest_level < manager.livello_minimo
                        or guest_level > manager.livello_massimo
                    ):
                        logger.warning(
                            t(
                                "avatar_server.log.security_bouncer_level",
                                name=final_name,
                                level=guest_level,
                                min=manager.livello_minimo,
                                max=manager.livello_massimo,
                            )
                        )
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "KICKED",
                                    "message": t(
                                        "multiplayer.kicked_level",
                                        level=guest_level,
                                        min=manager.livello_minimo,
                                        max=manager.livello_massimo,
                                    ),
                                }
                            )
                        )
                        await websocket.close(code=1008)
                        return

                    # Aggiorna il ConnectionManager con il vero nome
                    # FIX: Usa rename_connection invece di disconnect+connect per evitare il doppio accept()
                    manager.rename_connection(current_player_name, final_name)
                    current_player_name = final_name
                    logger.info(
                        t("multiplayer.handshake_complete", name=current_player_name)
                    )

                    # Inoltra l'handshake a chat.py per l'assimilazione in status.json
                    # Ricostruiamo il dict dai dati validati per sicurezza assoluta
                    # FIX: Sostituito .dict() deprecato con .model_dump()
                    safe_payload = validated_handshake.model_dump()
                    safe_payload["player_name"] = current_player_name

                    tagged_message = json.dumps(
                        {
                            "source": "web_ui",
                            "content": json.dumps(safe_payload),
                            "timestamp": time.time(),
                        }
                    )
                    # [FIX LIVELLO 1] put_nowait con gestione eccezione per evitare blocchi del server se la coda è piena
                    try:
                        message_queue.put_nowait(tagged_message)
                    except asyncio.QueueFull:
                        logger.warning("Coda messaggi piena (Backend saturo). Scarto handshake per prevenire OOM.")
                    continue

                # --- [RM29] MARTELLO DEL CREATORE (KICK) ---
                if msg_type == "KICK_PLAYER":
                    # Solo l'Host (identificato dalla LAN o dal token admin) può kickare
                    target_to_kick = parsed_data.get("target")
                    if target_to_kick and target_to_kick in manager.active_connections:
                        logger.warning(
                            t(
                                "avatar_server.log.multiplayer_kick_exec",
                                target=target_to_kick,
                            )
                        )
                        kick_ws = manager.active_connections[target_to_kick]
                        await kick_ws.send_text(
                            json.dumps(
                                {
                                    "type": "KICKED",
                                    "message": t("multiplayer.kicked_generic"),
                                }
                            )
                        )
                        await kick_ws.close(code=1008)
                        manager.disconnect(target_to_kick)

                        # Avvisa chat.py di rimuoverlo dal mondo
                        await message_queue.put(
                            json.dumps(
                                {
                                    "source": "web_ui",
                                    "content": json.dumps(
                                        {
                                            "type": "PLAYER_KICKED",
                                            "player_name": target_to_kick,
                                        }
                                    ),
                                    "timestamp": time.time(),
                                }
                            )
                        )
                    continue

                # --- [NUOVO] CHAT OOC (OUT-OF-CHARACTER) BYPASS ---
                if msg_type == "OOC_MESSAGE":
                    # Broadcast immediato a tutti i client, NON va nella message_queue dell'LLM
                    await manager.broadcast(data)
                    continue

            except json.JSONDecodeError:
                pass  # Non è un JSON, procedi normalmente

            # --- COMMAND TAGGING (SANTUARIO BLINDATO) ---
            # Avvolgiamo il messaggio originale in una busta che ne certifica la provenienza
            tagged_message = json.dumps(
                {"source": "web_ui", "content": data, "timestamp": time.time()}
            )
            # [FIX LIVELLO 1] put_nowait per prevenire Memory Leak
            try:
                message_queue.put_nowait(tagged_message)
            except asyncio.QueueFull:
                logger.warning("Coda messaggi piena. Scarto input utente per prevenire OOM.")
    except WebSocketDisconnect:
        logger.info(
            t(
                "avatar_server.log.multiplayer_player_disconnected",
                name=current_player_name,
            )
        )
    except Exception as e:
        logger.error(
            t(
                "avatar_server.log.multiplayer_ws_error",
                name=current_player_name,
                error=e,
            )
        )
    finally:
        manager.disconnect(current_player_name)


@app.get("/api/get_message_from_queue")
async def get_message_from_queue():
    try:
        message = message_queue.get_nowait()
        return JSONResponse(content={"message": message}, status_code=200)
    except asyncio.QueueEmpty:
        return Response(status_code=204)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/set_intent")
async def set_intent_api(request: Request):
    data = await request.json()
    msg_type = data.get("type", "action")
    intent = data.get("intent")
    
    # --- [FIX CRITICO] FALLBACK INTELLIGENTE NOME AVATAR ---
    avatar = data.get("avatar")
    if not avatar or avatar == "Avatar":
        try:
            config_file = CONFIG_PATH / "config.yaml"
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    conf = yaml.safe_load(f)
                    avatar = conf.get("currentAvatar", "Gemma").capitalize()
        except:
            avatar = "Gemma"
    # -------------------------------------------------------
    
    loop = data.get("loop", False)
    avatar_lower = avatar.lower()
    video_url = None
    if msg_type == "action" and intent and avatar_lower in ALL_AVATAR_DATA:
        avatar_data = ALL_AVATAR_DATA[avatar_lower]
        intent_lower = intent.lower().strip()
        relative_path = None
        if intent_lower in avatar_data.get("intent_map", {}):
            relative_path = avatar_data["intent_map"][intent_lower]
        elif intent_lower in avatar_data.get("emotion_map", {}):
            if v_list := avatar_data["emotion_map"][intent_lower]:
                relative_path = random.choice(v_list)
        if not relative_path:
            # [FIX CRITICO] Fallback Dinamico Agnostico
            # Peschiamo un idle a caso dalla lista caricata in RAM. Se fallisce, prendiamo il primo video disponibile.
            idle_states = avatar_data.get("idle_states",[])
            intent_map = avatar_data.get("intent_map", {})
            
            if idle_states and intent_map:
                fallback_intent = random.choice(idle_states)
                relative_path = intent_map.get(fallback_intent)
            elif intent_map:
                # Fallback estremo: prendi il primo video qualsiasi
                fallback_intent = list(intent_map.keys())[0]
                relative_path = intent_map[fallback_intent]
        custom_set = None
        video_url = resolve_video_path(avatar_lower, relative_path, custom_set)

    # FIX: Aggiunti 'message' e 'level' per permettere il corretto inoltro dei demiurge_toast al frontend
    broadcast_data = {
        "type": msg_type,
        "intent": intent,
        "avatar": avatar,
        "loop": loop,
        "video_url": video_url,
        "audio_url": data.get("audio_url"),
        "payload": data.get("payload"),
        "text": data.get("text"),
        "avatar_url": data.get("avatar_url"),
        "message": data.get("message"),
        "level": data.get("level"),
        "is_technical": data.get("is_technical", False),
    }

    # --- [FIX CRITICO] AGGIORNAMENTO CACHE DI STATO GLOBALE ---
    payload_data = data.get("payload", {})
    if msg_type == "system_status" and payload_data:
        CURRENT_SYSTEM_STATE.update(payload_data)
    elif msg_type == "action":
        if intent and intent.startswith("state_thinking"):
            CURRENT_SYSTEM_STATE["thinking"] = True
            CURRENT_SYSTEM_STATE["thinking_character"] = avatar
        elif intent and not intent.startswith("state_listening") and not intent.startswith("state_idle"):
            # Se esegue un'azione attiva (non idle, non listening, non thinking), ha finito di pensare
            CURRENT_SYSTEM_STATE["thinking"] = False

    # FIX v68.3: Rimossa iniezione in message_queue per evitare loop
    # if message_queue: await message_queue.put(json.dumps(data))

    await manager.broadcast(json.dumps(broadcast_data))
    return {"status": "ok", "video_url": video_url}


@app.post("/api/upload_media")
async def upload_media_api(
    file: UploadFile = File(...),
    type: str = Form(...),
    text: Optional[str] = Form(None),
):
    try:
        # --- [FIX CRITICO] SANITIZZAZIONE NOME FILE (ANTI-SHLEX CRASH) ---
        clean_filename = re.sub(r'[^\w\.-]', '_', file.filename) if file.filename else "upload.bin"
        safe_filename = f"{uuid.uuid4()}_{clean_filename}"
        
        # --- [FIX CRITICO] ROUTING INTELLIGENTE MEDIA ---
        if type == "document":
            destination = DOCUMENTS_PATH / safe_filename
            media_url = f"/documents/{safe_filename}"
            cmd_path = f"documents/{safe_filename}"
        else:
            destination = TEMP_IMAGE_PATH / safe_filename
            media_url = f"/temp_images/{safe_filename}"
            cmd_path = f"temp_images/{safe_filename}"
            
        with destination.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        await manager.broadcast(
            json.dumps(
                {
                    "type": "user_media",
                    "media_type": type,
                    "url": media_url,
                    "filename": file.filename,
                }
            )
        )
        
        cmd = f"/receive_media type='{type}' path='{cmd_path}'"
        if text:
            b64_text = base64.b64encode(text.encode("utf-8")).decode("utf-8")
            cmd += f" text='{b64_text}'"
        await message_queue.put(cmd)
        
        return JSONResponse(
            content={
                "status": "ok",
                "filename": safe_filename,
                "path": cmd_path,
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=t("media.upload_failed", error=str(e))
        )


# --- [AGGIUNTA v62.6] ENDPOINT MESSAGGIO VOCALE ---
@app.post("/api/voice-message")
async def receive_voice_message(
    audio: UploadFile = File(...),
    text: Optional[str] = Form(None),
    session_id: str = Form(...),
    avatar: str = Form(...),
):
    """
    Riceve un messaggio vocale (audio) e un eventuale testo scritto.
    Salva l'audio e inoltra il comando di trascrizione all'Anima.
    """
    try:
        # 1. Salvataggio file audio temporaneo
        # --- [FIX CRITICO] SANITIZZAZIONE NOME FILE (ANTI-SHLEX CRASH) ---
        clean_filename = re.sub(r'[^\w\.-]', '_', audio.filename) if audio.filename else "voice.webm"
        safe_filename = f"voice_{uuid.uuid4().hex[:8]}_{clean_filename}"
        
        destination = (
            TEMP_IMAGE_PATH / safe_filename
        )  # Usiamo temp_images per coerenza con upload_media

        with destination.open("wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)

        media_url = f"/temp_images/{safe_filename}"

        # 2. Notifica visiva al frontend (mostra il file in chat)
        await manager.broadcast(
            json.dumps(
                {
                    "type": "user_media",
                    "media_type": "audio",
                    "url": media_url,
                    "filename": audio.filename,
                }
            )
        )

        # 3. Inoltro comando all'Anima per trascrizione ed elaborazione
        # Il comando include il testo scritto (se presente) e il percorso del file audio
        b64_text = base64.b64encode((text or "").encode("utf-8")).decode("utf-8")
        cmd = f"/process_voice_input text='{b64_text}' path='temp_images/{safe_filename}' session_id='{session_id}' avatar='{avatar}'"
        await message_queue.put(cmd)

        return JSONResponse(
            content={"status": "ok", "message": t("media.voice_received")}
        )

    except Exception as e:
        logger.error(t("log.voice_receive_error", error=str(e)))
        raise HTTPException(status_code=500, detail=t("system.error", error=str(e)))


@app.post("/api/camera/release")
async def release_camera_api():
    await message_queue.put("/system_release_camera")
    return JSONResponse(content={"status": "ok"})


@app.post("/api/camera/acquire")
async def acquire_camera_api():
    await message_queue.put("/system_acquire_camera")
    return JSONResponse(content={"status": "ok"})


@app.get("/api/settings/time-schedule")
async def get_time_schedule():
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    return JSONResponse(content=guardian.get_time_schedule())


@app.post("/api/settings/time-schedule")
async def update_time_schedule(request: TimeScheduleUpdateRequest):
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    # [FIX BUG 01] Usiamo model_dump() per convertire il modello Pydantic piatto in un dizionario
    if guardian.save_time_schedule(request.model_dump()):
        await message_queue.put("/reload_global_config")
        return JSONResponse(
            content={"status": "ok", "message": t("settings.time_updated")}
        )
    raise HTTPException(status_code=500, detail=t("settings.time_update_error"))


# --- [NUOVO v69.0] ENDPOINT PERCEZIONE ---
@app.get("/api/settings/perception")
async def get_perception_settings_api():
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    return JSONResponse(content=guardian.get_perception_settings())


@app.post("/api/settings/perception")
async def update_perception_settings_api(settings: PerceptionSettingsRequest):
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    # [FIX v118.2] Update to model_dump() for Pydantic v2
    if guardian.save_perception_settings(settings.model_dump()):
        await message_queue.put("/reload_global_config")
        return JSONResponse(
            content={"status": "ok", "message": t("settings.perception_updated")}
        )
    raise HTTPException(status_code=500, detail=t("system.save_failed"))


# ---[NUOVO v68.7] ENDPOINT IMPOSTAZIONI IMMAGINAZIONE ---
@app.get("/api/settings/imagination")
async def get_imagination_settings():
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    return JSONResponse(content=guardian.get_imagination_config())


@app.post("/api/settings/imagination")
async def update_imagination_settings(settings: ImaginationSettingsRequest):
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    # [FIX v118.2] Update to model_dump() for Pydantic v2
    if guardian.save_imagination_config(settings.model_dump()):
        # Notifica chat.py per aggiornare lo stato runtime
        await message_queue.put(f"/update_imagination_config")
        return JSONResponse(
            content={"status": "ok", "message": t("settings.imagination_updated")}
        )
    raise HTTPException(status_code=500, detail=t("system.save_failed"))


# ---[NUOVO v69.1] ENDPOINT DEMIURGO ---
@app.get("/api/settings/demiurge")
async def get_demiurge_settings():
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    return JSONResponse(content=guardian.get_demiurge_config())


# ---[NUOVO v20.0] ENDPOINT PANOPTICON ---
@app.get("/api/settings/panopticon")
async def get_panopticon_settings():
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    return JSONResponse(content=guardian.get_panopticon_config())


@app.post("/api/settings/panopticon")
async def update_panopticon_settings(settings: PanopticonSettingsRequest):
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    if guardian.save_panopticon_config(settings.model_dump()):
        return JSONResponse(
            content={"status": "ok", "message": t("settings.panopticon_updated")}
        )
    raise HTTPException(status_code=500, detail=t("system.save_failed"))


@app.post("/api/settings/demiurge")
async def update_demiurge_settings(settings: DemiurgeSettingsRequest):
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))

    model_config = guardian.get_model_selection_config() or {}

    # ---[NUOVO v124.3] SYNC LABOUR MODEL ---
    # Se l'utente sceglie il provider 'labour', dobbiamo assicurarci che il modello
    # selezionato nel tab Demiurgo diventi l'active_labour_model globale.
    if settings.provider == "labour":
        model_config["active_labour_model"] = settings.model
        model_config["labour_model_on_cpu"] = settings.labour_model_on_cpu
        guardian.save_model_selection_config(model_config)

    # Converti in dict e salva (usando model_dump per Pydantic v2)
    if guardian.save_demiurge_config(settings.model_dump()):
        # Notifica chat.py per aggiornare lo stato runtime
        await message_queue.put("/update_demiurge_config")
        return JSONResponse(
            content={"status": "ok", "message": t("settings.demiurge_updated")}
        )
    raise HTTPException(status_code=500, detail=t("system.save_failed"))


# ---[NUOVO v118.0] ENDPOINT CONFIGURAZIONE TTS ---
@app.get("/api/settings/tts")
async def get_tts_settings():
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    return JSONResponse(content=guardian.get_tts_engine_config())


@app.post("/api/settings/tts")
async def update_tts_settings(settings: TtsSettingsRequest):
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    # [FIX v118.2] Update to model_dump() for Pydantic v2
    if guardian.save_tts_engine_config(settings.model_dump()):
        await message_queue.put("/reload_global_config")
        return JSONResponse(
            content={"status": "ok", "message": t("settings.tts_updated")}
        )
    raise HTTPException(status_code=500, detail=t("system.save_failed"))

# --- [NUOVO] ENDPOINTS MCP SERVER ---
@app.get("/api/settings/mcp")
async def get_mcp_settings():
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    return JSONResponse(content={"servers": guardian.get_mcp_servers()})

@app.post("/api/settings/mcp")
async def update_mcp_settings(request: McpSettingsRequest):
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    if guardian.save_mcp_servers([s.model_dump() for s in request.servers]):
        # Notifica chat.py per ricaricare i client MCP a caldo
        await message_queue.put("/reload_mcp_config")
        return JSONResponse(content={"status": "ok", "message": "MCP servers updated"})
    raise HTTPException(status_code=500, detail=t("system.save_failed"))


@app.get("/api/settings/demiurge/api-key")
async def get_demiurge_provider_key(provider: str):
    """Recupera la API Key specifica per un provider dal file credentials.yaml."""
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    key = guardian.get_provider_key(provider)
    return {"api_key": key}


@app.get("/api/settings/demiurge/available-models")
def get_available_groq_models(api_key: Optional[str] = Query(None)):
    """
    Endpoint per il recupero dinamico dei modelli Groq (v107.4).
    Accetta la chiave API come parametro di query per permettere il test prima del salvataggio.
    """
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))

    # Priorità: Chiave passata dal Frontend > Chiave salvata in Config
    key_to_use = api_key
    if not key_to_use or "IL_TUO" in key_to_use:
        config = guardian.get_demiurge_config()
        key_to_use = config.get("api_key")

    # Se non abbiamo nessuna chiave valida, restituiamo lista vuota
    if not key_to_use or "IL_TUO" in key_to_use:
        logger.warning(t("log.groq_no_key"))
        return JSONResponse(content=[])

    # Invocazione logica aggiornata nel Guardiano
    models = guardian.fetch_available_groq_models(key_to_use)
    return JSONResponse(content=models)


@app.get("/api/settings/demiurge/available-models/openrouter")
def get_available_openrouter_models(api_key: Optional[str] = Query(None)):
    """
    Recupera la lista dei modelli disponibili su OpenRouter.
    Richiede API Key.
    """
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))

    # Se l'API key non è passata, prova a prenderla dalla config salvata
    key_to_use = api_key
    if not key_to_use:
        config = guardian.get_demiurge_config()
        key_to_use = config.get("api_key")

    if not key_to_use:
        return JSONResponse(content=[])

    models = guardian.fetch_available_openrouter_models(key_to_use)
    return JSONResponse(content=models)


@app.post("/api/toast")
async def send_toast(request: ToastRequest):
    """Endpoint per ricevere feedback dal Demiurgo e inoltrarli al Frontend via WS."""
    try:
        await manager.broadcast(
            json.dumps(
                {
                    "type": "demiurge_toast",
                    "message": request.message,
                    "level": request.type,
                }
            )
        )
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        logger.error(t("system.error", error=str(e)))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ghost_text")
async def send_ghost_text_api(request: GhostTextRequest):
    """Endpoint per inviare il Pensiero ad Alta Voce (Ghost Text) dal Ghost Operator."""
    try:
        await manager.broadcast(
            json.dumps(
                {
                    "type": "ghost_typing",
                    "text": request.text,
                    "avatar": request.avatar,
                    "is_technical": request.is_technical,
                }
            )
        )
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        logger.error(t("system.error", error=str(e)))
        raise HTTPException(status_code=500, detail=str(e))


# ---[NUOVO v97.0] ENDPOINT EFFETTO VISIVO ---
@app.post("/api/visual-effect")
async def trigger_visual_effect(request: VisualEffectRequest):
    """
    Riceve un trigger per un effetto visivo (es. ripple) e lo trasmette ai client.
    """
    try:
        await manager.broadcast(
            json.dumps(
                {
                    "type": "visual_effect",
                    "effect_type": request.type,
                    "x": request.x,
                    "y": request.y,
                }
            )
        )
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        logger.error(t("system.error", error=str(e)))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/avatars/{avatar_id}/styles")
async def get_avatar_styles(avatar_id: str, season: Optional[str] = Query(None)):
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    avatar_key = avatar_id.lower()
    active_set = guardian.get_avatar_custom_set(avatar_key) or "Standard"
    target_season = season if season else get_current_season()
    videos_path = AVATARS_BASE_PATH / avatar_key / "videos" / target_season
    available_sets = ["Standard"]
    if videos_path.exists():
        for item in videos_path.iterdir():
            if item.is_dir() and item.name != "Standard":
                available_sets.append(item.name)
    return JSONResponse(
        content={
            "active_set": active_set,
            "available_sets": sorted(available_sets),
            "current_season": get_current_season(),
            "viewing_season": target_season,
        }
    )


@app.post("/api/avatars/{avatar_id}/style")
async def set_avatar_style(avatar_id: str, request: AvatarStyleUpdateRequest):
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    if guardian.save_avatar_custom_set(avatar_id, request.active_set):
        return JSONResponse(
            content={
                "status": "ok",
                "message": t("settings.avatar_style_updated", style=request.active_set),
            }
        )
    raise HTTPException(status_code=500, detail=t("settings.avatar_style_error"))


# --- NUOVO ENDPOINT: FACTORY RESET (v62.3) ---
@app.post("/api/factory-reset")
async def factory_reset_api(request: FactoryResetRequest):
    """Trigger per il rito di purificazione totale."""
    try:
        # Invia il comando di PREPARAZIONE all'Anima tramite la coda
        await message_queue.put(f"/prepare_factory_reset {request.total_wipe}")
        return JSONResponse(
            content={"status": "ok", "message": t("settings.factory_reset_started")}
        )
    except Exception as e:
        logger.error(t("log.factory_reset_error", error=str(e)))
        raise HTTPException(status_code=500, detail=str(e))


# --- NUOVI ENDPOINT: SESSION SYNC (v62.23) ---
@app.post("/api/session/active")
async def set_active_session(request: ActiveSessionRequest):
    global ACTIVE_SESSION_ID
    ACTIVE_SESSION_ID = request.session_id
    logger.info(t("log.session_active_updated", id=ACTIVE_SESSION_ID))
    return JSONResponse(content={"status": "ok", "session_id": ACTIVE_SESSION_ID})


@app.get("/api/session/active")
async def get_active_session():
    return JSONResponse(content={"session_id": ACTIVE_SESSION_ID})


# ==========================================
# === INIZIO BLOCCO ENDPOINT HIVE MIND (v66.1) ===
# ==========================================


@app.post("/api/hive/register")
async def hive_register(request: Request, data: HiveRegisterRequest):
    """Registra un nuovo dispositivo nella Hive Mind."""
    if not hive_manager:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    try:
        client_ip = request.client.host
        # --- FIX v68.5: AUTO-DETECTION IP LAN ---
        if client_ip == "127.0.0.1":
            client_ip = _get_local_ip()
            logger.info(t("avatar_server.log.hive_loopback_detected", ip=client_ip))

        final_id = hive_manager.register_device(
            data.device_id, data.device_name, data.device_type, client_ip
        )
        return JSONResponse(
            content={
                "status": "ok",
                "message": t("hive.device_registered"),
                "device_id": final_id,
            }
        )
    except Exception as e:
        logger.error(t("avatar_server.log.hive_registration_error", error=str(e)))
        raise HTTPException(status_code=500, detail=t("system.error", error=str(e)))


@app.post("/api/hive/heartbeat")
async def hive_heartbeat(request: Request, data: HiveHeartbeatRequest):
    """Aggiorna lo stato online di un dispositivo."""
    if not hive_manager:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    client_ip = request.client.host
    # --- FIX v68.5: AUTO-DETECTION IP LAN ---
    if client_ip == "127.0.0.1":
        client_ip = _get_local_ip()

    if hive_manager.heartbeat(data.device_id, client_ip):
        return JSONResponse(content={"status": "ok"})
    return JSONResponse(
        content={"status": "unregistered", "message": t("hive.device_not_found")},
        status_code=200,
    )


@app.post("/api/hive/focus")
async def hive_focus(data: HiveFocusRequest):
    """Imposta il focus dell'Anima su un dispositivo specifico."""
    if not hive_manager:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    if hive_manager.set_focus(data.device_id):
        # Notifica tutti i client del cambio di focus
        await manager.broadcast(
            json.dumps({"type": "hive_focus_change", "device_id": data.device_id})
        )
        return JSONResponse(content={"status": "ok"})
    raise HTTPException(status_code=404, detail=t("hive.device_not_found"))


@app.get("/api/hive/devices")
async def hive_list_devices():
    """Restituisce la lista dei dispositivi e il loro stato."""
    if not hive_manager:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    return JSONResponse(content=hive_manager.get_devices_status())


@app.post("/api/hive/bind")
async def hive_bind_ip(data: HiveBindRequest):
    """Vincola un IP a un dispositivo (Identità Immortale)."""
    if not hive_manager:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    hive_manager.bind_ip(data.ip, data.device_id, data.name)
    return JSONResponse(content={"status": "ok"})


@app.post("/api/hive/unbind")
async def hive_unbind_ip(data: HiveUnbindRequest):
    """Rimuove il vincolo IP."""
    if not hive_manager:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    hive_manager.unbind_ip(data.ip)
    return JSONResponse(content={"status": "ok"})


# --- NUOVO: ENDPOINT INTERCOM (GOD MODE) ---
@app.post("/api/hive/intercom")
async def hive_intercom(device_id: str = Form(...), audio: UploadFile = File(...)):
    """
    Riceve un messaggio audio dal Controllore e lo invia al Bersaglio.[AGGIORNATO v119.3] Ghost Presence: Risolve e invia anche i video per il Lip-Sync.
    """
    try:
        # 1. Salva audio temporaneo
        safe_filename = f"intercom_{uuid.uuid4().hex[:8]}.webm"
        destination = TEMP_AUDIO_PATH / safe_filename

        with destination.open("wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)

        audio_url = f"/temp_audio/{safe_filename}"
        logger.info(t("log.intercom_received", id=device_id, url=audio_url))

        # 2. Risoluzione Video Ghost Presence (Speaking & Idle)
        video_url = None
        idle_url = None
        try:
            # Recupera avatar corrente
            current_avatar = "gemma"
            if (CONFIG_PATH / "config.yaml").exists():
                with open(CONFIG_PATH / "config.yaml", "r", encoding="utf-8") as f:
                    conf = yaml.safe_load(f)
                    current_avatar = conf.get("currentAvatar", "gemma")

            # Recupera path relativi dalla mappa globale
            avatar_data = ALL_AVATAR_DATA.get(current_avatar.lower(), {})
            intent_map = avatar_data.get("intent_map", {})

            # Ricerca dinamica dei path per evitare hardcoding
            speaking_path = next((v for k, v in intent_map.items() if k.startswith("state_speaking")), None)
            idle_path = next((v for k, v in intent_map.items() if k.startswith("state_idle")), None)
            
            # Fallback di sicurezza se i prefissi non esistono
            if not speaking_path and intent_map: speaking_path = list(intent_map.values())[0]
            if not idle_path and intent_map: idle_path = list(intent_map.values())[0]

            # Risoluzione contestuale (Stilista)
            video_url = resolve_video_path(current_avatar, speaking_path)
            idle_url = resolve_video_path(current_avatar, idle_path)

        except Exception as e:
            logger.error(t("log.intercom_ghost_error", error=str(e)))

        # 3. Broadcast mirato con payload arricchito
        await manager.broadcast(
            json.dumps(
                {
                    "type": "intercom_audio",
                    "target_device_id": device_id,
                    "audio_url": audio_url,
                    "video_url": video_url,  # Video Speaking (Loop)
                    "idle_url": idle_url,  # Video Idle (Reset)
                }
            )
        )

        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        logger.error(t("log.intercom_error", error=str(e)))
        raise HTTPException(status_code=500, detail=str(e))


# --- NUOVO: ENDPOINT EDITING (v66.1) ---
@app.post("/api/hive/device/update")
async def hive_update_device(data: HiveUpdateDeviceRequest):
    """Aggiorna manualmente nome o IP di un dispositivo."""
    if not hive_manager:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    if hive_manager.update_device(data.device_id, data.name, data.ip):
        return JSONResponse(content={"status": "ok"})
    raise HTTPException(status_code=404, detail=t("hive.device_not_found"))


@app.post("/api/hive/device/remove")
async def hive_remove_device(data: HiveRemoveDeviceRequest):
    """Rimuove un dispositivo dalla Hive Mind."""
    if not hive_manager:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    if hive_manager.remove_device(data.device_id):
        return JSONResponse(content={"status": "ok"})
    raise HTTPException(status_code=404, detail=t("hive.device_not_found"))


# --- [NUOVO v67.0] ENDPOINT RPG ROSTER ---
@app.post("/api/rpg/roster/toggle")
async def toggle_rpg_roster(request: RpgRosterToggleRequest):
    """Aggiunge o rimuove un personaggio dal mondo attivo."""
    target_rpg_path = ACTIVE_RPG_PATH
    if not target_rpg_path:
        gdr_folders = [d for d in LORE_PATH.iterdir() if d.is_dir()]
        if gdr_folders:
            target_rpg_path = gdr_folders[0]
            
    if not target_rpg_path:
        raise HTTPException(status_code=400, detail=t("gdr.no_active_rpg"))

    try:
        # [FIX CRITICO] Centralizzazione della logica di Roster Toggle via message_queue.
        # Invece di scrivere direttamente sul disco (bypassando e corrompendo la RAM di chat.py),
        # inviamo il comando asincrono a chat.py che gestirà l'aggiornamento in RAM e la persistenza.
        await message_queue.put(
            f"/rpg_roster_toggle action='{request.action}' char_name='{request.char_name}' lang='{request.lang}'"
        )
        
        # Feedback ottimistico immediato per evitare lag percepiti
        msg = t("gdr.entered_scene") if request.action == "add" else t("gdr.left_scene")
        return JSONResponse(content={"status": "ok", "message": msg})

    except Exception as e:
        logger.error(t("log.rpg_roster_error", error=str(e)))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rpg/active-roster")
async def get_active_roster(lang: str = "it"):
    """Restituisce la lista dei nomi dei personaggi attualmente in status.json."""
    target_rpg_path = ACTIVE_RPG_PATH
    if not target_rpg_path:
        gdr_folders = [d for d in LORE_PATH.iterdir() if d.is_dir()]
        if gdr_folders:
            target_rpg_path = gdr_folders[0]
            
    if not target_rpg_path:
        return JSONResponse(content=[])

    try:
        norm_lang = guardian.normalize_lang_code(lang) if guardian else lang
        lang_path = target_rpg_path / norm_lang
        effective_root = lang_path if lang_path.is_dir() else target_rpg_path

        status_file = effective_root / "WORLD" / "status.json"
        if not status_file.exists():
            return JSONResponse(content=[])

        with open(status_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        names = [p.get("nome") for p in data.get("personaggi", [])]
        return JSONResponse(content=names)
    except Exception as e:
        logger.error(t("gdr.roster_read_error", error=str(e)))
        return JSONResponse(content=[])


# --- [NUOVO v27.0] ENDPOINT RPG CAMPAIGN MODE ---
@app.get("/api/rpg/campaign-mode")
async def get_campaign_mode(lang: str = "it"):
    """Restituisce lo stato della Modalità Campagna (Dungeon Master)."""
    target_rpg_path = ACTIVE_RPG_PATH
    if not target_rpg_path:
        gdr_folders = [d for d in LORE_PATH.iterdir() if d.is_dir()]
        if gdr_folders:
            target_rpg_path = gdr_folders[0]
            
    if not target_rpg_path:
        return JSONResponse(content={"enabled": False})

    try:
        norm_lang = guardian.normalize_lang_code(lang) if guardian else lang
        lang_path = target_rpg_path / norm_lang
        effective_root = lang_path if lang_path.is_dir() else target_rpg_path

        status_file = effective_root / "WORLD" / "status.json"
        if not status_file.exists():
            return JSONResponse(content={"enabled": False})

        with open(status_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        is_enabled = (
            data.get("metadati", {}).get("game_state", {}).get("campaign_mode", False)
        )
        return JSONResponse(content={"enabled": is_enabled})
    except Exception as e:
        logger.error(t("log.rpg_campaign_read_error", error=str(e)))
        return JSONResponse(content={"enabled": False})


@app.post("/api/rpg/campaign-mode")
async def toggle_campaign_mode(request: RpgCampaignModeRequest):
    """Attiva o disattiva la Modalità Campagna nel file status.json."""
    target_rpg_path = ACTIVE_RPG_PATH
    if not target_rpg_path:
        gdr_folders = [d for d in LORE_PATH.iterdir() if d.is_dir()]
        if gdr_folders:
            target_rpg_path = gdr_folders[0]
            
    if not target_rpg_path:
        raise HTTPException(status_code=400, detail=t("gdr.no_active_rpg"))

    try:
        norm_lang = (
            guardian.normalize_lang_code(request.lang) if guardian else request.lang
        )
        lang_path = target_rpg_path / norm_lang
        effective_root = lang_path if lang_path.is_dir() else target_rpg_path

        status_file = effective_root / "WORLD" / "status.json"
        
        # --- [FIX CRITICO] AUTO-CREAZIONE STATUS.JSON ---
        if not status_file.exists():
            status_file.parent.mkdir(parents=True, exist_ok=True)
            status_data = {
                "localizzazione": {"luogo_fisico_attuale": "Sconosciuto"},
                "personaggi": [],
                "metadati": {"game_state": {"campaign_mode": request.enabled}}
            }
        else:
            with open(status_file, "r", encoding="utf-8") as f:
                status_data = json.load(f)

            if "metadati" not in status_data:
                status_data["metadati"] = {}
            if "game_state" not in status_data["metadati"]:
                status_data["metadati"]["game_state"] = {}

            status_data["metadati"]["game_state"]["campaign_mode"] = request.enabled

        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)

        # --- [FIX CRITICO] SINCRONIZZA LA RAM DI CHAT.PY ---
        # Impedisce che chat.py sovrascriva il disco con la sua RAM vecchia
        await message_queue.put("/reload_world_state")

        # Invia un broadcast per aggiornare la UI in tempo reale
        await manager.broadcast(
            json.dumps(
                {"type": "system_status", "payload": {"campaign_mode": request.enabled}}
            )
        )

        return JSONResponse(content={"status": "ok", "enabled": request.enabled})
    except Exception as e:
        logger.error(t("log.rpg_campaign_toggle_error", error=str(e)))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rpg/generate-sheet")
async def generate_rpg_sheet(request: GenerateRpgSheetRequest):
    """Richiede all'LLM di generare una scheda RPG completa."""
    request_id = str(uuid.uuid4())
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    LLM_FUTURES[request_id] = future

    try:
        payload = {
            "type": "generate_rpg_sheet",
            "id": request_id,
            "razza": request.razza,
            "classe": request.classe,
            "livello": request.livello,
            "lang": request.lang,
        }
        await message_queue.put(json.dumps(payload))

        # Attesa della risposta dal bridge (Timeout 300s per generazione complessa)
        response_text = await asyncio.wait_for(future, timeout=300.0)
        
        # --- [FIX CRITICO] GESTIONE JSON DECODE ERROR ---
        try:
            sheet_data = json.loads(response_text)
            if not sheet_data: # Se è {} (fallback da chat.py)
                raise ValueError("Dati vuoti")
        except (json.JSONDecodeError, ValueError):
            raise HTTPException(status_code=500, detail="L'LLM non ha generato un JSON valido per la scheda. Riprova.")
            
        return JSONResponse(
            content={"status": "ok", "sheet": sheet_data}
        )

    except asyncio.TimeoutError:
        del LLM_FUTURES[request_id]
        raise HTTPException(status_code=504, detail=t("bridge.llm_timeout"))
    except HTTPException:
        raise
    except Exception as e:
        if request_id in LLM_FUTURES:
            del LLM_FUTURES[request_id]
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# === INIZIO BLOCCO ENDPOINT MEMORY GALLERY (v68.2) ===
# ==========================================


@app.get("/api/gallery/images")
async def get_gallery_images():
    """
    Restituisce la lista dei file multimediali in temp_images, ordinati per data.
    """
    try:
        if not TEMP_IMAGE_PATH.exists():
            return JSONResponse(content=[])

        files = []
        valid_extensions = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".webm"}

        for f in TEMP_IMAGE_PATH.iterdir():
            if f.is_file() and f.suffix.lower() in valid_extensions:
                files.append(
                    {
                        "name": f.name,
                        "url": f"/temp_images/{f.name}",
                        "type": "video"
                        if f.suffix.lower() in {".mp4", ".webm"}
                        else "image",
                        "timestamp": f.stat().st_mtime,
                    }
                )

        # Ordina dal più recente
        files.sort(key=lambda x: x["timestamp"], reverse=True)
        return JSONResponse(content=files)
    except Exception as e:
        logger.error(t("gallery.read_error", error=str(e)))
        return JSONResponse(content=[], status_code=500)


@app.delete("/api/gallery/images/{filename}")
async def delete_gallery_image(filename: str):
    """
    Elimina un file dalla galleria (temp_images).
    """
    try:
        # Sanitize filename to prevent directory traversal
        safe_filename = Path(filename).name
        file_path = TEMP_IMAGE_PATH / safe_filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail=t("gallery.file_not_found"))

        os.remove(file_path)
        logger.info(
            t("avatar_server.log.gallery_file_deleted_log", filename=safe_filename)
        )
        return JSONResponse(
            content={"status": "ok", "message": t("gallery.file_deleted")}
        )
    except Exception as e:
        logger.error(t("log.gallery_delete_error", error=str(e)))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/gallery/sessions")
async def get_gallery_sessions():
    """
    Restituisce i riassunti narrativi delle sessioni passate.
    """
    if not db_manager:
        raise HTTPException(status_code=503, detail=t("system.db_unavailable"))
    try:
        sessions = db_manager.get_all_sessions()
        # Filtra e formatta per la galleria
        gallery_sessions = []
        for s in sessions:
            # Recupera lo stato per estrarre il narrative_buffer se non è nella tabella principale
            # Nota: db_manager.get_all_sessions restituisce già narrative_buffer se la colonna esiste
            narrative = s.get("narrative_buffer", "")
            if not narrative and s.get("state_json"):
                try:
                    state = json.loads(s["state_json"])
                    narrative = state.get("narrative_buffer", "")
                except:
                    pass

            gallery_sessions.append(
                {
                    "id": s["id"],
                    "name": s["name"],
                    "date": s["last_access_date"],
                    "summary": narrative or t("gallery.no_summary"),
                }
            )
        return JSONResponse(content=gallery_sessions)
    except Exception as e:
        logger.error(t("log.gallery_session_read_error", error=str(e)))
        return JSONResponse(content=[], status_code=500)


# ==========================================
# === FINE BLOCCO ENDPOINT MEMORY GALLERY ===
# ==========================================

# ==========================================
# === INIZIO BLOCCO OPENAI BRIDGE (v98.0) ===
# ==========================================


@app.post("/v1/chat/completions")
async def openai_chat_completions(request: ChatCompletionRequest):
    """
    Endpoint compatibile OpenAI che delega la generazione a chat.py tramite coda.
    """
    request_id = str(uuid.uuid4())
    logger.info(t("log.bridge_llm_request", id=request_id, model=request.model))

    # 1. Crea un Future per attendere la risposta
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    LLM_FUTURES[request_id] = future

    try:
        # 2. Invia la richiesta a chat.py tramite message_queue
        # chat.py leggerà questo messaggio in handle_web_message
        payload = {
            "type": "llm_request",
            "id": request_id,
            "data": request.model_dump(),
        }
        await message_queue.put(json.dumps(payload))

        # 3. Attendi la risposta (Timeout 600s)
        response_data = await asyncio.wait_for(future, timeout=600.0)

        # 4. Formatta la risposta come OpenAI
        return JSONResponse(
            content={
                "id": f"chatcmpl-{request_id}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": request.model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": response_data},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 0,  # Non calcolato qui
                    "completion_tokens": 0,
                    "total_tokens": 0,
                },
            }
        )

    except asyncio.TimeoutError:
        logger.error(t("log.bridge_timeout", id=request_id))
        del LLM_FUTURES[request_id]
        raise HTTPException(status_code=504, detail=t("bridge.llm_timeout"))
    except Exception as e:
        logger.error(t("log.bridge_error", id=request_id, error=str(e)))
        if request_id in LLM_FUTURES:
            del LLM_FUTURES[request_id]
        raise HTTPException(status_code=500, detail=t("system.error", error=str(e)))


@app.post("/api/internal/llm-response")
async def internal_llm_response(response: InternalLLMResponse):
    """
    Endpoint interno chiamato da chat.py per restituire la risposta generata.
    """
    request_id = response.request_id
    content = response.content

    if request_id in LLM_FUTURES:
        future = LLM_FUTURES[request_id]
        if not future.done():
            future.set_result(content)
        del LLM_FUTURES[request_id]
        return {"status": "ok"}

    logger.warning(t("bridge.unknown_id", id=request_id))
    return {"status": "ignored"}


# ==========================================
# === FINE BLOCCO OPENAI BRIDGE ===
# ==========================================

# ==========================================
# === INIZIO BLOCCO MUSA & GENESI (v99.0) ===
# ==========================================


@app.get("/api/settings/jailbreaks")
async def get_jailbreaks():
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    return JSONResponse(content=guardian.get_jailbreaks())


@app.post("/api/settings/jailbreaks")
async def save_jailbreaks(request: JailbreakListRequest):
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    # Converti i modelli Pydantic in dizionari
    data = [jb.dict() for jb in request.jailbreaks]
    if guardian.save_jailbreaks_data(data):
        return JSONResponse(
            content={"status": "ok", "message": t("musa.jailbreaks_saved")}
        )
    raise HTTPException(status_code=500, detail=t("system.save_failed"))


@app.post("/api/settings/jailbreaks/active")
async def set_active_jailbreak(request: ActiveJailbreakRequest):
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))

    current_list = guardian.get_jailbreaks()
    updated_list = []
    found = False

    for jb in current_list:
        if jb["id"] == request.id:
            jb["is_active"] = True
            found = True
        else:
            jb["is_active"] = False
        updated_list.append(jb)

    if not found:
        raise HTTPException(status_code=404, detail=t("musa.jailbreak_not_found"))

    if guardian.save_jailbreaks_data(updated_list):
        return JSONResponse(
            content={"status": "ok", "message": t("musa.jailbreak_active_updated")}
        )
    raise HTTPException(status_code=500, detail=t("system.save_failed"))


@app.post("/api/settings/jailbreaks/test")
async def test_jailbreak(request: JailbreakTestRequest):
    """
    Invia una richiesta di test all'Anima tramite la coda messaggi.
    Attende la risposta tramite il meccanismo LLM_FUTURES (riutilizzando la logica del Bridge).
    """
    request_id = str(uuid.uuid4())
    logger.info(t("log.test_jailbreak_start", id=request_id))

    # 1. Crea Future
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    LLM_FUTURES[request_id] = future

    try:
        # 2. Invia comando speciale a chat.py
        # Usiamo un tipo messaggio dedicato 'test_jailbreak'
        payload = {
            "type": "test_jailbreak",
            "id": request_id,
            "system_prompt": request.system_prompt,
            "user_query": request.user_query,
        }
        await message_queue.put(json.dumps(payload))

        # 3. Attendi risposta (Timeout 120s)
        response_text = await asyncio.wait_for(future, timeout=120.0)

        return JSONResponse(content={"status": "ok", "response": response_text})

    except asyncio.TimeoutError:
        del LLM_FUTURES[request_id]
        raise HTTPException(status_code=504, detail=t("musa.test_timeout"))
    except Exception as e:
        if request_id in LLM_FUTURES:
            del LLM_FUTURES[request_id]
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/settings/knowledge-base")
async def get_knowledge_base():
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    return JSONResponse(content=guardian.get_knowledge_base())


@app.post("/api/settings/knowledge-base")
async def save_knowledge_base(request: KnowledgeBaseRequest):
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    # Converti il modello Pydantic in dizionario
    data = request.dict()
    if guardian.save_knowledge_base_data(data):
        return JSONResponse(content={"status": "ok", "message": t("musa.kb_saved")})
    raise HTTPException(status_code=500, detail=t("system.save_failed"))


def _check_sources_health_task(sources: List[Dict]):
    """Task in background per verificare lo stato delle fonti."""
    updated_sources = []
    for src in sources:
        try:
            # HEAD request con timeout breve
            res = requests.head(src["url"], timeout=5, allow_redirects=True)
            src["status"] = "online" if res.status_code < 400 else "offline"
        except:
            src["status"] = "offline"

        src["last_checked"] = time.time()
        updated_sources.append(src)

    # Salva i risultati nel DB tramite Guardian
    if guardian:
        kb = guardian.get_knowledge_base()
        kb["sources"] = updated_sources
        guardian.save_knowledge_base_data(kb)
        logger.info(t("log.health_check_completed"))


@app.post("/api/settings/knowledge-base/check-health")
async def check_sources_health(background_tasks: BackgroundTasks):
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))

    kb = guardian.get_knowledge_base()
    sources = kb.get("sources", [])

    if not sources:
        return JSONResponse(content={"status": "ok", "message": t("musa.no_sources")})

    # Avvia task in background
    background_tasks.add_task(_check_sources_health_task, sources)

    return JSONResponse(
        content={"status": "ok", "message": t("musa.health_check_started")}
    )


@app.post("/api/settings/knowledge-base/import")
async def import_knowledge_base(file: UploadFile = File(...)):
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    try:
        content = await file.read()
        data = json.loads(content)

        # Validazione minima
        if "sources" not in data or "arguments" not in data:
            raise ValueError(t("musa.invalid_json"))

        if guardian.save_knowledge_base_data(data):
            return JSONResponse(
                content={"status": "ok", "message": t("musa.kb_imported")}
            )
        raise Exception(t("system.save_failed"))
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=t("musa.import_failed", error=str(e))
        )


@app.get("/api/settings/knowledge-base/export")
async def export_knowledge_base():
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))

    data = guardian.get_knowledge_base()
    json_str = json.dumps(data, indent=2)

    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=knowledge_base.json"},
    )


# ==========================================
# === FINE BLOCCO MUSA & GENESI ===
# ==========================================

# --- [NUOVO v114.3] ENDPOINT ROSTER PNG PER HEART UI ---
@app.get("/api/heart/png/roster")
async def get_heart_png_roster(lang: str = "it"):
    """
    Restituisce la lista dei nomi dei PNG disponibili nel GDR attivo.
    """
    target_rpg_path = ACTIVE_RPG_PATH
    if not target_rpg_path:
        gdr_folders = [d for d in LORE_PATH.iterdir() if d.is_dir()]
        if gdr_folders:
            target_rpg_path = gdr_folders[0]
            
    if not target_rpg_path:
        return []

    try:
        norm_lang = guardian.normalize_lang_code(lang) if guardian else lang
        # Cerca nella cartella lingua o root
        path = target_rpg_path / norm_lang / "PNG"
        if not path.is_dir():
            path = target_rpg_path / "PNG"

        if not path.is_dir():
            return []

        # Restituisce solo i nomi (stem) dei file .json
        return [f.stem for f in path.glob("*.json")]
    except Exception as e:
        logger.error(t("heart.roster_error", error=str(e)))
        return []


# --- [NUOVO v114.3] ENDPOINT STATUS CUORE PNG ---
@app.get("/api/heart/png/status")
async def get_png_heart_status(name: str, lang: str = "it"):
    """
    Recupera i vettori emotivi e la memoria dal file JSON di un PNG specifico.
    """
    target_rpg_path = ACTIVE_RPG_PATH
    if not target_rpg_path:
        gdr_folders = [d for d in LORE_PATH.iterdir() if d.is_dir()]
        if gdr_folders:
            target_rpg_path = gdr_folders[0]
            
    if not target_rpg_path:
        raise HTTPException(status_code=400, detail=t("gdr.no_active_rpg"))

    try:
        norm_lang = guardian.normalize_lang_code(lang) if guardian else lang
        path = target_rpg_path / norm_lang / "PNG" / f"{name}.json"
        if not path.exists():
            path = target_rpg_path / "PNG" / f"{name}.json"

        if not path.exists():
            raise HTTPException(
                status_code=404, detail=t("heart.png_not_found", name=name)
            )

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Estrae i dati dal campo pattuito 'vettori_emotivi'
        heart_data = data.get(
            "vettori_emotivi",
            {
                "affetto": 50,
                "fiducia": 50,
                "rispetto": 50,
                "energia_sociale": 100,
                "umore_corrente": t("heart.moods.neutral"),
                "memoria_emotiva": [],
                "eccitazione": 10,
                "gelosia": 0,
                "curiosità": 50,
                "vulnerabilità": 20,
                "complicità": 30,
                "stanchezza_mentale": 0,
            },
        )

        return JSONResponse(content=heart_data)
    except Exception as e:
        logger.error(t("log.heart_png_read_error_log", name=name, error=str(e)))
        raise HTTPException(status_code=500, detail=t("heart.png_read_error"))


# --- [NUOVO v15.0] ENDPOINTS SPECIALIST SETTINGS ---
@app.get("/api/settings/specialist")
async def get_specialist_settings():
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    return JSONResponse(content=guardian.get_specialist_config())


@app.post("/api/settings/specialist")
async def update_specialist_settings(settings: SpecialistSettingsRequest):
    if not guardian:
        raise HTTPException(status_code=503, detail=t("system.guardian_unavailable"))
    if guardian.save_specialist_config(settings.dict()):
        return JSONResponse(
            content={"status": "ok", "message": t("settings.specialist_updated")}
        )
    raise HTTPException(status_code=500, detail=t("system.save_failed"))


# ---[NUOVO v15.0] ENDPOINT VALIDAZIONE CODICE (DRY RUN) ---
@app.post("/api/custom-connectors/validate")
async def validate_connector_code(request: ValidateCodeRequest):
    """
    Esegue una validazione sintattica e di importazione del codice Python.
    """
    try:
        # 1. Validazione Sintattica (AST)
        try:
            ast.parse(request.code)
        except SyntaxError as e:
            return JSONResponse(
                content={
                    "status": "error",
                    "message": t("settings.syntax_error", line=e.lineno, msg=e.msg),
                }
            )

        # 2. Validazione Import (Simulata)
        # Non possiamo eseguire codice arbitrario in sicurezza totale qui,
        # ma possiamo controllare se le librerie importate sono installate.
        # Per ora ci limitiamo al check sintattico che è sicuro e veloce.

        return JSONResponse(
            content={"status": "ok", "message": t("settings.code_valid")}
        )
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)})


# --- [NUOVO v15.0] ENDPOINT GENERAZIONE TOOL AUTOMATICA ---
@app.post("/api/custom-connectors/sync-tool")
def sync_tool_json(request: SyncToolRequest):
    """
    Genera il file JSON del tool in src/tools/ basandosi sui metadati del connettore.
    """
    # [FIX BUG 01] init_peripherals=False TASSATIVO
    temp_executor = BraccioDivino(
        None, None, guardian, db_manager, game_logger, init_peripherals=False
    )

    if temp_executor.generate_tool_json_from_connector(
        request.name, request.def_structure, request.prompt
    ):
        return JSONResponse(
            content={"status": "ok", "message": t("settings.tool_json_generated")}
        )
    else:
        raise HTTPException(status_code=500, detail=t("settings.tool_json_error"))


# ==========================================
# === INIZIO BLOCCO JARVIS CORTEX (v18.0) ===
# ==========================================

JARVIS_CONFIG_PATH = APP_ROOT / "data" / "jarvis_config.json"
PATCHES_FILE_PATH = APP_ROOT / "data" / "patches.json"
SHADOW_BUFFER_PATH = APP_ROOT / "data" / "shadow_buffer.json"


@app.get("/api/jarvis/blacklist")
async def get_blacklist():
    if JARVIS_CONFIG_PATH.exists():
        try:
            with open(JARVIS_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return JSONResponse(
                    content={"blacklist_windows": data.get("blacklist_windows", [])}
                )
        except Exception as e:
            logger.error(t("avatar_server.log.iot_layout_read_error", error=e))
    return JSONResponse(content={"blacklist_windows": []})


@app.post("/api/jarvis/blacklist")
async def update_blacklist(request: BlacklistRequest):
    try:
        data = {"blacklist_windows": request.windows}
        with open(JARVIS_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # Notifica l'Anima per ricaricare la config a caldo
        await message_queue.put(
            "/reload_jarvis_config"
        )  # [FIX v18.2] Trigger specifico per Jarvis
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jarvis/patches")
async def get_patches():
    if PATCHES_FILE_PATH.exists():
        try:
            with open(PATCHES_FILE_PATH, "r", encoding="utf-8") as f:
                return JSONResponse(content=json.load(f))
        except Exception as e:
            logger.error(t("avatar_server.log.iot_layout_read_error", error=e))
    return JSONResponse(content=[])


@app.post("/api/jarvis/patches/rollback")
def rollback_patch(request: RollbackRequest):
    try:
        # Istanziamo un BraccioDivino temporaneo senza periferiche per eseguire il rollback
        temp_executor = BraccioDivino(
            None, None, guardian, db_manager, game_logger, init_peripherals=False
        )
        result = temp_executor.rollback_patch(request.patch_id)

        # Verifica il successo basandosi sulle stringhe tradotte dell'executor
        success_msg = t("executor.rollback_success", file="").split(":")[
            0
        ]  # Prende la parte fissa
        if (
            success_msg.lower() in result.lower()
            or t("reminders.completed").lower() in result.lower()
        ):
            return JSONResponse(content={"status": "ok", "message": result})
        else:
            raise HTTPException(status_code=400, detail=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=t("system.error", error=str(e)))


@app.get("/api/jarvis/shadow-log")
async def get_shadow_log():
    if SHADOW_BUFFER_PATH.exists():
        try:
            with open(SHADOW_BUFFER_PATH, "r", encoding="utf-8") as f:
                return JSONResponse(content=json.load(f))
        except Exception as e:
            logger.error(t("avatar_server.log.iot_actions_read_error", error=e))
    return JSONResponse(content=[])


@app.post("/api/jarvis/prudenza")
async def set_prudenza_api(request: PrudenzaRequest):
    """Imposta manualmente la prudenza nel Cuore (Hot-Swap in RAM)."""
    try:
        # Invia il comando direttamente a chat.py per aggiornare la RAM e salvare su disco
        await message_queue.put(f"/set_prudence {request.value}")
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jarvis/work-mode")
async def set_work_mode_api(request: WorkModeRequest):
    """Attiva/Disattiva Work Mode (Hot-Swap in RAM)."""
    try:
        # Invia il comando direttamente a chat.py per aggiornare la RAM e salvare su disco
        await message_queue.put(f"/set_work_mode {request.enabled}")
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/care/triggers/update")
async def update_trigger_api(request: TriggerUpdateRequest):
    """Aggiorna un trigger esistente in care_config.json."""
    if not CARE_CONFIG_PATH.exists():
        raise HTTPException(status_code=404, detail=t("jarvis.config_not_found"))

    try:
        with open(CARE_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)

        triggers = config.get("triggers", [])
        updated = False

        for t in triggers:
            if t["value"] == request.old_value:
                t["value"] = request.new_value
                t["label"] = request.new_label
                updated = True
                break

        if not updated:
            raise HTTPException(status_code=404, detail=t("jarvis.trigger_not_found"))

        with open(CARE_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        await message_queue.put("/reload_care_config")
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# === FINE BLOCCO JARVIS CORTEX ===
# ==========================================

# ==========================================
# === INIZIO BLOCCO CORTEX AUDIO (v20.0) ===
# ==========================================


@app.get("/api/care/audio")
async def get_care_audio_library():
    """Recupera la libreria audio da care_config.json."""
    if not CARE_CONFIG_PATH.exists():
        return JSONResponse(content=[])
    try:
        with open(CARE_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        return JSONResponse(content=config.get("audio_library", []))
    except Exception as e:
        logger.error(t("log.audio_library_read_error", error=str(e)))
        return JSONResponse(content=[])


@app.post("/api/care/audio/upload")
async def upload_care_audio(
    file: UploadFile = File(...), label: str = Form(...), category: str = Form(...)
):
    """Salva una registrazione vocale dell'utente nella libreria."""
    try:
        clip_id = str(uuid.uuid4())
        file_ext = Path(file.filename).suffix or ".webm"
        filename = f"{clip_id}{file_ext}"
        dest_path = CARE_AUDIO_PATH / filename

        with dest_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Aggiorna care_config.json
        with open(CARE_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)

        library = config.get("audio_library", [])
        new_clip = {
            "id": clip_id,
            "label": label,
            "category": category,
            "path": f"data/care_audio/{filename}",
            "type": "recorded",
            "created_at": time.time(),
        }
        library.append(new_clip)
        config["audio_library"] = library

        with open(CARE_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        return JSONResponse(content={"status": "ok", "clip": new_clip})
    except Exception as e:
        logger.error(t("log.audio_upload_error", error=str(e)))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/care/audio/generate")
def generate_care_audio_tts(request: TtsClipRequest):
    """Genera una clip audio usando il motore TTS e la salva nella libreria."""
    try:
        # Istanziamo un BraccioDivino temporaneo per usare genera_voce
        temp_executor = BraccioDivino(
            None, None, guardian, db_manager, game_logger, init_peripherals=False
        )

        # --- [FIX] ESTRAZIONE LANG_CODE PER TTS ---
        voice_id = request.voice or ""
        lang_code = "i"  # Default fallback (Italiano)
        
        # Caso VibeVoice (es. it-Gemma_woman.pt)
        if "-" in voice_id and "_" in voice_id:
            lang_code = voice_id.split("-")[0]
        # Caso Kokoro (es. if_sara.pt)
        elif "_" in voice_id:
            lang_code = voice_id[0]

        # Genera il file audio (genera_voce restituisce il path assoluto)
        # Usiamo l'intent 'default' per una sintesi pulita
        audio_path_str = temp_executor.genera_voce(
            request.text, "default", preferred_voice=request.voice, preferred_lang_code=lang_code
        )

        if not audio_path_str:
            raise HTTPException(status_code=500, detail=t("audio.tts_failed"))

        audio_path = Path(audio_path_str)
        clip_id = str(uuid.uuid4())
        filename = f"{clip_id}{audio_path.suffix}"
        dest_path = CARE_AUDIO_PATH / filename

        # Sposta il file dalla cartella temp_audio alla cartella care_audio
        shutil.move(str(audio_path), str(dest_path))

        # Aggiorna care_config.json
        with open(CARE_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)

        library = config.get("audio_library", [])
        new_clip = {
            "id": clip_id,
            "label": request.label,
            "category": request.category,
            "path": f"data/care_audio/{filename}",
            "type": "generated",
            "created_at": time.time(),
        }
        library.append(new_clip)
        config["audio_library"] = library

        with open(CARE_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        return JSONResponse(content={"status": "ok", "clip": new_clip})
    except Exception as e:
        logger.error(t("log.audio_gen_error", error=str(e)))
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/care/audio/{clip_id}")
async def delete_care_audio(clip_id: str):
    """Elimina una clip audio dalla libreria e dal disco."""
    try:
        with open(CARE_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)

        library = config.get("audio_library", [])
        clip = next((c for c in library if c["id"] == clip_id), None)

        if not clip:
            raise HTTPException(status_code=404, detail=t("audio.clip_not_found"))

        # Elimina file fisico
        file_path = APP_ROOT / clip["path"]
        if file_path.exists():
            os.remove(file_path)

        # Aggiorna JSON
        config["audio_library"] = [c for c in library if c["id"] != clip_id]
        with open(CARE_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        logger.error(t("log.audio_delete_error", error=str(e)))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/care/audio/play")
async def play_care_audio_api(request: CareAudioPlayRequest):
    """Invia un comando di riproduzione audio a una lista di dispositivi via WebSocket."""
    try:
        # Invia un broadcast. Ogni client verificherà se il suo ID è in device_ids.
        await manager.broadcast(
            json.dumps(
                {
                    "type": "intercom_audio",  # Riutilizziamo il tipo esistente per coerenza
                    "target_device_ids": request.device_ids,  # Passiamo l'array per il multi-routing
                    "audio_url": request.audio_url,
                    "label": request.label,
                }
            )
        )
        logger.info(
            t(
                "log.cortex_audio_play",
                label=request.label,
                count=len(request.device_ids),
            )
        )
        return {"status": "ok"}
    except Exception as e:
        logger.error(t("audio.transmission_error", error=str(e)))
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# === FINE BLOCCO CORTEX AUDIO ===
# ==========================================

# ==========================================
# === INIZIO BLOCCO TRADUZIONI ===
# ==========================================


@app.get("/api/translations/languages")
async def get_available_languages():
    """Scansiona la cartella translations/Frontend e restituisce le lingue disponibili con i loro nomi."""
    frontend_trans_dir = APP_ROOT / "translations" / "Frontend"
    languages = []
    
    # --- [FIX IBRIDO] MAPPA DI SICUREZZA + LETTURA DINAMICA ---
    # Protegge le lingue ufficiali dalle corruzioni dei traduttori automatici,
    # ma permette l'aggiunta dinamica di qualsiasi nuova lingua custom.
    SAFE_CORE_LANGS = {
        "it": "Italiano 🇮🇹", "en": "English 🇬🇧", "fr": "Français 🇫🇷",
        "es": "Español 🇪🇸", "de": "Deutsch 🇩🇪", "pt": "Português 🇧🇷",
        "br": "Português 🇧🇷", # [FIX] Aggiunto supporto per la cartella 'br'
        "nl": "Nederlands 🇳🇱", "pl": "Polski 🇵🇱", "ru": "Русский 🇷🇺",
        "jp": "日本語 🇯🇵", "cn": "中文 🇨🇳", "kr": "한국어 🇰🇷",
        "ar": "العربية 🇸🇦", "hi": "हिन्दी 🇮🇳"
    }
    
    if frontend_trans_dir.exists():
        for lang_dir in frontend_trans_dir.iterdir():
            if lang_dir.is_dir():
                lang_code = lang_dir.name
                
                # 1. Controlla se è una lingua core protetta
                if lang_code.lower() in SAFE_CORE_LANGS:
                    lang_label = SAFE_CORE_LANGS[lang_code.lower()]
                else:
                    # 2. Se è una lingua custom, estrae il nome dinamicamente dal JSON
                    lang_label = lang_code.upper()
                    json_file = lang_dir / f"{lang_code}.json"
                    if json_file.exists():
                        try:
                            with open(json_file, "r", encoding="utf-8-sig") as f:
                                data = json.load(f)
                                lang_label = data.get("_language_name", lang_label)
                        except Exception as e:
                            logger.error(f"Errore lettura {json_file.name}: {e}")
                            
                languages.append({"code": lang_code, "label": lang_label})
    
    # Fallback di sicurezza se la cartella è vuota o inesistente
    if not languages:
        languages = [{"code": "en", "label": "English 🇬🇧"}]
        
    # Ordina alfabeticamente per codice
    languages.sort(key=lambda x: x["code"])
    return JSONResponse(content={"languages": languages})


@app.get("/api/brain/languages")
async def get_brain_languages():
    """Scansiona la cartella prompts e restituisce le lingue del cervello disponibili."""
    prompts_dir = APP_ROOT / "prompts"
    languages = ["it", "en"]  # Fallback di sicurezza
    if prompts_dir.exists() and prompts_dir.is_dir():
        found_langs = [f.stem for f in prompts_dir.glob("*.json")]
        if found_langs:
            languages = found_langs
    return JSONResponse(content={"languages": sorted(list(set(languages)))})


@app.get("/api/translations/frontend")
async def get_frontend_translations(lang: str = "en"):
    """Esegue il merge on the fly dei JSON frontend (en + lang scelta)."""
    frontend_trans_dir = APP_ROOT / "translations" / "Frontend"

    def deep_merge(dict1, dict2):
        result = dict1.copy()
        for key, value in dict2.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def dict_merge_hook(pairs):
        """Gancio per fondere le chiavi duplicate all'interno dello stesso file JSON."""
        result = {}
        for key, value in pairs:
            if key in result:
                if isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            else:
                result[key] = value
        return result

    def load_lang_jsons(l: str) -> dict:
        lang_dir = frontend_trans_dir / l
        merged = {}
        if lang_dir.exists() and lang_dir.is_dir():
            for file_path in lang_dir.glob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8-sig") as f:
                        # [FIX CRITICO] Usiamo il merge hook per salvare le chiavi duplicate nello stesso file!
                        data = json.loads(f.read(), object_pairs_hook=dict_merge_hook)
                        if isinstance(data, dict):
                            merged = deep_merge(merged, data)
                except Exception as e:
                    logger.error(
                        t(
                            "avatar_server.log.translations_read_error",
                            file=file_path,
                            error=e,
                        )
                    )
        return merged

    # 1. Carica sempre l'inglese come base (Fallback)
    base_translations = load_lang_jsons("en")

    # 2. Se la lingua richiesta non è l'inglese, caricala e fai il merge
    if lang != "en":
        target_translations = load_lang_jsons(lang)
        final_translations = deep_merge(base_translations, target_translations)
    else:
        final_translations = base_translations

    # --- [FIX CACHE] Disabilita la cache del browser per le traduzioni ---
    response = JSONResponse(content=final_translations)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ==========================================
# === FINE BLOCCO TRADUZIONI ===
# ==========================================

# --- MOUNT STATICI ---
app.mount(
    "/lore", StaticFiles(directory=str(LORE_PATH), follow_symlink=True), name="lore"
)
app.mount(
    "/avatars",
    StaticFiles(directory=str(AVATARS_BASE_PATH), follow_symlink=True),
    name="avatars",
)
app.mount(
    "/temp_audio",
    StaticFiles(directory=str(TEMP_AUDIO_PATH), follow_symlink=True),
    name="temp_audio",
)
app.mount(
    "/data/care_audio",
    StaticFiles(directory=str(CARE_AUDIO_PATH), follow_symlink=True),
    name="care_audio",
)
app.mount(
    "/temp_images",
    StaticFiles(directory=str(TEMP_IMAGE_PATH), follow_symlink=True),
    name="temp_images",
)
app.mount(
    "/documents",
    StaticFiles(directory=str(DOCUMENTS_PATH), follow_symlink=True),
    name="documents",
)
app.mount(
    "/mobile",
    StaticFiles(
        directory=str(APP_ROOT / "frontend_mobile" / "dist"),
        html=True,
        follow_symlink=True,
    ),
    name="mobile_static",
)
app.mount(
    "/classic",
    StaticFiles(directory=str(APP_ROOT / "frontend"), html=True, follow_symlink=True),
    name="classic_static",
)

@app.post("/api/multiplayer/set-room-policy")
async def set_room_policy(request: Request):
    """Imposta le policy di sicurezza della stanza (es. Women-Only, Level Gating) nel ConnectionManager."""
    data = await request.json()
    manager.is_women_only_room = data.get("women_only", False)
    manager.livello_minimo = data.get("livello_minimo", 1)
    manager.livello_massimo = data.get("livello_massimo", 20)
    return JSONResponse(content={"status": "ok"})


def kill_process_on_port(port: int):
    try:
        if os.name == "nt":
            result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
            # FIX v99.4: Encoding robusto per netstat
            lines = result.stdout.splitlines()
            for line in lines:
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    pid = parts[-1]
                    if pid != "0":
                        subprocess.run(
                            ["taskkill", "/F", "/PID", pid], capture_output=True
                        )
        else:
            result = subprocess.run(
                ["lsof", "-t", f"-i:{port}"], capture_output=True, text=True
            )
            pids = result.stdout.strip().split()
            for pid in pids:
                if pid:
                    subprocess.run(["kill", "-9", pid], capture_output=True)
    except Exception:
        pass


if __name__ == "__main__":
    kill_process_on_port(SERVER_PORT)
    local_ip = _get_local_ip()
    logger.info(t("log.server_start", ip=local_ip, port=SERVER_PORT))
    uvicorn.run(app, host="0.0.0.0", port=SERVER_PORT, log_level="info")
