# src/perception_handler.py
# v25.0 - YAMNET AUDIO CLASSIFIER (ORECCHIO ASSOLUTO)
# ADD: Integrazione MediaPipe Audio Classifier per rilevamento eventi sonori (Pianto, Abbaio, Vetro).
# ADD: Download automatico del modello yamnet.tflite.
# FIX: Loop audio potenziato con buffer circolare e classificazione semantica.
# MANTENUTO: EasyOCR, Visione, Hardware Stats.
# LEGGE A0099: Invarianza strutturale garantita.

import cv2
import threading
import time
import numpy as np
import face_recognition
from datetime import datetime
import speech_recognition as sr
import pyaudio
import queue
import os
import shutil
import string
import sys
import random
import math
from pathlib import Path
import json
import io
import re
import ctypes
from difflib import SequenceMatcher
from collections import deque
from contextlib import contextmanager # [NUOVO] Per silenziatore C++

# --- [NUOVO] SILENZIATORE C++ A BASSO LIVELLO ---
@contextmanager
def suppress_cpp_stderr():
    """Dirotta temporaneamente lo stderr del sistema operativo verso devnull per zittire MediaPipe."""
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        old_stderr = os.dup(sys.stderr.fileno())
        os.dup2(devnull, sys.stderr.fileno())
        yield
    finally:
        os.dup2(old_stderr, sys.stderr.fileno())
        os.close(devnull)
        os.close(old_stderr)

# --- [NUOVO v30.0] CARE OS INTEGRATION ---
from care_engine import CareEngine
from utils.translator import t

try:
    import mediapipe as mp

    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    print(t("log.perception.mediapipe_warning"))

# --- [NUOVO v24.0] ENGINE OCR PROFESSIONALE ---
try:
    import easyocr

    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    print(t("log.perception.easyocr_warning"))

# --- NUOVO: IMPORT PER REGISTRO DI SISTEMA ---
if os.name == "nt":
    import winreg

# --- NUOVO: IMPORT WHISPER ---
try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None
    print(t("log.perception.whisper_warning"))

import pyautogui
from playwright.sync_api import sync_playwright, Page, Playwright

try:
    from plyer import notification
except ImportError:
    notification = None

# --- CONTROLLO FINESTRE NATIVO ---
try:
    from pywinauto import Application
except ImportError:
    Application = None

# --- PERCEZIONE HARDWARE ---
import psutil

# ---[NUOVO v20.0] AUDIO DUCKING (PANOPTICON) ---
try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume, IAudioMeterInformation
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL

    PYCAW_AVAILABLE = True
except ImportError:
    PYCAW_AVAILABLE = False
    print(t("log.perception.pycaw_warning"))

from typing import TYPE_CHECKING, List, Dict, Any, Optional, Tuple

if TYPE_CHECKING:
    from logger import Logger
    from database_manager import DatabaseManager
    from guardian import Guardian
    from brain_llm import CervelloTrinitario

# --- [FASE 4] DEFINIZIONE CARTELLA AUDIO TEMPORANEA ---
TEMP_AUDIO_DIR = Path(__file__).parent.parent.resolve() / "temp_audio"

# --- [NUOVO] LISTA NERA ALLUCINAZIONI WHISPER ---
HALLUCINATION_PHRASES = [
    t("log.perception.hallucination.subtitles_by"),
    t("log.perception.hallucination.subtitles_revision"),
    t("log.perception.hallucination.thanks_watching"),
    "copyright",
    t("log.perception.hallucination.all_rights_reserved"),
    t("log.perception.hallucination.subtitles"),
    t("log.perception.hallucination.translation"),
    "you",
    "thank you",
    "bye",
    "mbc",
    "...",
    ".",
    "?",
    "!",
    t("log.perception.hallucination.goodnight"),
    t("log.perception.hallucination.see_you_tomorrow"),
    t("log.perception.hallucination.see_you"),
    t("log.perception.hallucination.subscribe"),
    t("log.perception.hallucination.subtitles_of"),
    "community",
    "amara.org",
    t("log.perception.hallucination.subtitles_created_by"),
    "watching",
    "thanks for watching",
]


class PerceptionHandler:
    """
    Gestisce i flussi di dati da webcam (vista), microfono (udito attivo),
    schermo (Occhio di Sauron).
    """

    def __init__(
        self, logger: "Logger", db_manager: "DatabaseManager", guardian: "Guardian"
    ):
        self.logger = logger
        self.db_manager = db_manager
        self.guardian = guardian
        self.is_running = False
        self.heart = None # [FIX CRITICO] Inizializzazione attributo mancante

        # --- GESTIONE HARDWARE CONDIVISA ---
        self.mic_lock = threading.Lock()

        # --- ATTRIBUTI BIOMETRICI ---
        self.last_biometric_report = None
        self.prev_frame = None
        self.movement_intensity = 0.0
        self.last_sensory_timestamp = time.time()  # [NUOVO FASE 1.1] Sensore di Quiete Assoluta

        # Attributi Vista Locale
        self.video_capture = None
        self.vision_thread = None
        self.last_frame = None

        # --- [NUOVO v21.0] BUFFER CIRCOLARE VIDEO ---
        self.frame_buffer = deque(maxlen=30) # [FIX FASE 2.2] Aumentato a 30 per coprire 30 secondi di contesto visivo
        self.last_buffer_update = 0.0

        self.known_face_encodings: List[np.ndarray] = []
        self.known_souls_data: List[Dict[str, Any]] = []
        self.current_detected_souls: List[Dict[str, Any] | str] = []
        self.last_seen_times: Dict[str, float] = {}  # [NUOVO] Timer per Debounce Visivo
        self.camera_paused = threading.Event()
        self.analysis_paused = (
            threading.Event()
        )  # [FIX v20.5] Semaforo per evitare crash hardware

        # --- RIFONDAZIONE UDITO (Active Hearing + Whisper) ---
        self.active_hearing_thread = None
        self.is_active_hearing = False
        self.recognizer = sr.Recognizer()
        try:
            self.microphone = sr.Microphone()
            self.logger.log("Microfono di default inizializzato con successo.", "INIT")
        except Exception as e:
            self.logger.warning(f"Impossibile inizializzare il microfono di default (Nessun dispositivo rilevato?): {e}")
            self.microphone = None
        self.transcribed_text_queue = queue.Queue()
        self.udito_in_pausa = threading.Event()

        # --- [NUOVO v116.2] MEMORIA AUDIO NATIVA ---
        self.last_audio_data: Optional[sr.AudioData] = None

        # --- [NUOVO v23.0] RIFERIMENTO AL CERVELLO PER FALLBACK ---
        self.cervello: Optional["CervelloTrinitario"] = None

        # --- [NUOVO v24.0] INIZIALIZZAZIONE EASYOCR ---
        self.ocr_reader = None
        if EASYOCR_AVAILABLE:
            try:
                self.logger.log(t("log.perception.easyocr_init"), "INIT")
                self.ocr_reader = easyocr.Reader(["it", "en"], gpu=True)
                self.logger.log(t("log.perception.easyocr_ready"), "INIT")
            except Exception as e:
                self.logger.error(t("log.perception.easyocr_init_error", error=e))

        # Inizializzazione Whisper Locale
        self.whisper = None
        if WhisperModel:
            try:
                self.logger.log(t("log.perception.whisper_init"))
                self.whisper = WhisperModel("small", device="auto", compute_type="int8")
                self.logger.log(t("log.perception.whisper_ready"))
            except Exception as e:
                self.logger.error(t("log.perception.whisper_init_error", error=e))

        # Attributi Occhio di Sauron (Screen)
        self.monitoring_thread = None
        self.is_monitoring = False
        self.visual_context_queue = queue.Queue()
        self.tesseract_path: Optional[str] = None
        self.monitor_interval = 10

        # --- [NUOVO v20.0] STATO VISUAL DEBOUNCE ---
        self.last_sent_text = ""
        self.last_sent_time = 0

        # --- [FIX v18.2] DEBOUNCE HARDWARE ALERT ---
        self.last_hardware_push = 0.0

        # --- [NUOVO v30.0] CARE OS ENGINE ---
        self.care_engine = CareEngine(None, self.logger)
        self.care_audio_thread = None
        self.is_care_listening = False

        self.logger.log(t("log.perception.init_complete"))
        self._load_known_faces()
        self._calibrate_microphone()

        # --- [NUOVO FASE B] INIZIALIZZAZIONE VISIONE AVANZATA ---
        self.pose_landmarker = None
        self.object_detector = None
        self.face_landmarker = None  # [NUOVO v20.0] Vibe Check
        if MEDIAPIPE_AVAILABLE:
            self._init_vision_models()

    def set_brain(self, cervello: "CervelloTrinitario"):
        """Inietta il riferimento al cervello per il fallback neurale."""
        self.cervello = cervello

        # --- [NUOVO v120.0] INIEZIONE CERVELLO NEL CARE ENGINE ---
        if self.care_engine:
            self.care_engine.set_brain(cervello)

        self.logger.log(t("log.perception.neural_link"), "DEBUG")

    def set_executor(self, executor):
        """Inietta l'executor nel CareEngine (Post-Init)."""
        if self.care_engine:
            self.care_engine.executor = executor
            self.logger.log(t("log.perception.care_link"), "CARE")

    def set_event_hub(self, hub):
        """[NUOVO v18.0] Inietta l'EventHub per il paradigma Push."""
        self.event_hub = hub
        self.logger.log(t("log.perception.eventhub_link"), "SYSTEM")

    def set_heart(self, heart):
        """[FIX CRITICO] Inietta il riferimento al cuore per l'endocrinologia visiva."""
        self.heart = heart
        self.logger.log("PerceptionHandler: Collegamento con il Cuore stabilito.", "DEBUG")

    def _calibrate_microphone(self):
        try:
            self.logger.log(t("log.perception.ear_calibration"))
            with self.mic_lock:
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=2)
            self.logger.log(
                t(
                    "log.perception.ear_calibrated",
                    threshold=f"{self.recognizer.energy_threshold:.2f}",
                )
            )
        except Exception as e:
            print(t("log.perception.audio_calibration_error", error=e))

    def _load_known_faces(self):
        self.logger.log(t("log.perception.load_souls"))
        souls = self.db_manager.get_all_souls()
        if not souls:
            self.logger.log(t("log.perception.empty_archive"))
            return
        self.known_face_encodings = [np.array(s["face_encoding"]) for s in souls]
        self.known_souls_data = souls
        self.logger.log(t("log.perception.souls_loaded", count=len(souls)))

    def _find_tesseract_dynamically(self) -> bool:
        return False

    def set_tesseract_path(self, path: str) -> bool:
        return True

    # --- [NUOVO v24.0] MOTORE OCR PROFESSIONALE (EASYOCR) ---

    def get_text_from_image(self, image_np: np.ndarray) -> str:
        """Estrae testo usando EasyOCR con fallback neurale."""
        text = ""
        if self.ocr_reader:
            try:
                results = self.ocr_reader.readtext(image_np, detail=0)
                text = " ".join(results)
            except Exception as e:
                self.logger.error(t("log.perception.easyocr_error", error=e))

        if not text.strip() and self.cervello:
            self.logger.log(t("log.perception.fallback_trigger"), "VISION")
            text = self.cervello.analizza_visione_operativa(image_np)

        return text.strip()

    # --- OCCHIO DI SAURON (SCREEN MONITORING) ---
    def start_monitoring(self) -> Tuple[bool, str]:
        if self.is_monitoring:
            return True, t("log.perception.sauron_already_active")
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True
        )
        self.monitoring_thread.start()
        self.logger.log(t("log.perception.sauron_active"))
        return True, t("log.perception.sauron_active")

    def stop_monitoring(self) -> Tuple[bool, str]:
        if not self.is_monitoring:
            return True, t("log.perception.sauron_already_closed")
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=2)
        self.logger.log(t("log.perception.sauron_closed"))
        return True, t("log.perception.sauron_closed")

    def _monitoring_loop(self):
        """
        Ciclo di monitoraggio schermo con Debounce Visivo e Anti-Zombie.
        """
        keywords = t("log.perception.keywords_list").split(",")
        prev_screen_gray = None  # [NUOVO] Per Smart Vision Throttling

        while self.is_monitoring:
            try:
                # ---[NUOVO v20.0] PRIVACY SHIELD & SELECTIVE OCR ---
                active_window = self.get_active_window_title()
                panopticon_config = (
                    self.guardian.get_panopticon_config()
                    if hasattr(self.guardian, "get_panopticon_config")
                    else dict()
                )

                # 1. Privacy Shield (Blacklist Titoli)
                blacklist_titles = tuple(
                    t("log.perception.privacy_keywords").split(",")
                )
                user_blacklist = panopticon_config.get("sherlock_blacklist", list())

                is_private = False
                for b in blacklist_titles:
                    if b in active_window.lower():
                        is_private = True
                for b in user_blacklist:
                    if b.lower() in active_window.lower():
                        is_private = True

                if is_private:
                    self.logger.log(t("log.perception.privacy_shield"), "VISION")
                    time.sleep(self.monitor_interval)
                    continue

                # 2. Selective OCR (Cattura solo la finestra attiva se possibile)
                screenshot = None
                if Application and os.name == "nt":
                    try:
                        app = Application(backend="uia").connect(
                            title_re=f".*{re.escape(active_window)}.*", timeout=1
                        )
                        win = app.top_window()
                        rect = win.rectangle()
                        if rect.width() > 0 and rect.height() > 0:
                            screenshot = pyautogui.screenshot(
                                region=(
                                    rect.left,
                                    rect.top,
                                    rect.width(),
                                    rect.height(),
                                )
                            )
                    except Exception:
                        pass  # Fallback a full screen

                if screenshot is None:
                    screenshot = pyautogui.screenshot()

                img_np = np.array(screenshot)
                img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

                # ---[NUOVO] SMART VISION THROTTLING ---
                gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
                should_run_ocr = True

                # ---[NUOVO] SMART VISION THROTTLING ---
                gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
                should_run_ocr = True

                if prev_screen_gray is not None:
                    # [FIX] Controlliamo prima che le forme combacino per evitare l'errore di broadcasting
                    if gray.shape == prev_screen_gray.shape:
                        # Calcolo MSE (Mean Squared Error) per rilevare cambiamenti
                        err = np.sum(
                            (gray.astype("float") - prev_screen_gray.astype("float"))
                            ** 2
                        )
                        err /= float(gray.shape[0] * gray.shape[1])
                        if err < 1.0:  # Soglia di tolleranza per frame statico
                            should_run_ocr = False
                    else:
                        # Se le dimensioni sono diverse, l'area acquisita è cambiata
                        # (es. cambio finestra attiva), quindi forziamo l'OCR.
                        should_run_ocr = True

                prev_screen_gray = gray

                cleaned_text = ""
                if should_run_ocr:
                    raw_text = self.get_text_from_image(img_bgr)

                    # --- [NUOVO v20.0] HASHING SENSIBILE (Privacy Shield) ---
                    # Nasconde IBAN
                    raw_text = re.sub(
                        r"[a-zA-Z]{2}\d{2}[a-zA-Z0-9]{11,30}",
                        t("log.perception.iban_protected"),
                        raw_text,
                    )
                    # Nasconde Carte di Credito
                    raw_text = re.sub(
                        r"\b(?:\d[ -]*?){13,16}\b",
                        t("log.perception.card_protected"),
                        raw_text,
                    )
                    # Nasconde Email/Password vicine
                    raw_text = re.sub(
                        r"(?i)(password|pwd|pin)[\s:]+\S+",
                        r"\1: " + t("log.perception.data_protected"),
                        raw_text,
                    )

                    cleaned_text = raw_text

                if cleaned_text:
                    # --- [NUOVO] FILTRO SPECCHIO (ANTI-ALLUCINAZIONE VISIVA) ---
                    # Aggiunte parole chiave per bloccare la lettura della UI e dei menu
                    mirror_keywords = [
                        t("input_bar.placeholder").lower(),
                        "type a message",
                        "gemma >",
                        "samael >",
                        "airis",
                        "chatarea",
                        t("input_bar.placeholder").lower(),
                        t("character_editor.edit_character", name="").lower().strip(),
                        t("sidebar.gallery").lower(),
                        t("sidebar.settings").lower(),
                        t("sidebar.manage_models").lower(),
                    ]
                    cleaned_lower = cleaned_text.lower()
                    if any(k in cleaned_lower for k in mirror_keywords):
                        self.logger.log(t("log.perception.mirror_syndrome"), "VISION")
                        continue  # Salta l'invio al cervello

                    # ---[NUOVO v18.0] SHADOW LEARNING PUSH ---
                    if hasattr(self, "event_hub") and self.event_hub:
                        self.event_hub.push_event(
                            source="screen",
                            event_type="shadow_data",
                            data={
                                "text": cleaned_text,
                                "window": self.get_active_window_title(),
                            },
                        )

                    similarity = SequenceMatcher(
                        None, cleaned_text, self.last_sent_text
                    ).ratio()
                    time_since_last = time.time() - self.last_sent_time

                    should_send = False
                    reason = ""

                    if similarity < 0.9:
                        should_send = True
                        reason = t(
                            "log.perception.reason_new_content",
                            similarity=f"{similarity:.2f}",
                        )
                    elif time_since_last > 60:
                        should_send = True
                        reason = t("log.perception.reason_refresh")
                    elif (
                        any(k in cleaned_text.lower() for k in keywords)
                        and time_since_last > 10
                    ):
                        should_send = True
                        reason = t("log.perception.reason_keyword")

                    if should_send:
                        self.logger.log(
                            t("log.perception.sauron_send", reason=reason), "VISION"
                        )
                        self.visual_context_queue.put(cleaned_text)
                        self.last_sent_text = cleaned_text
                        self.last_sent_time = time.time()
                    else:
                        pass

            except Exception as e:
                self.logger.log(t("log.perception.eye_error", error=e))

            for _ in range(self.monitor_interval):
                if not self.is_monitoring:
                    break
                time.sleep(1)

    def get_visual_context(self) -> Optional[str]:
        try:
            return self.visual_context_queue.get_nowait()
        except queue.Empty:
            return None

    # --- [NUOVO v22.0] VISUAL OPERATOR (GRID OVERLAY) ---
    def get_screen_with_grid(
        self, grid_rows: int = 10, grid_cols: int = 10
    ) -> np.ndarray:
        """
        Cattura lo schermo e sovrappone una griglia numerata.
        """
        try:
            screenshot = pyautogui.screenshot()
            img_np = np.array(screenshot)
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

            height, width, _ = img_bgr.shape
            step_x = width // grid_cols
            step_y = height // grid_rows

            for i in range(1, grid_cols):
                x = i * step_x
                cv2.line(img_bgr, (x, 0), (x, height), (0, 255, 0), 1)

            for i in range(1, grid_rows):
                y = i * step_y
                cv2.line(img_bgr, (0, y), (width, y), (0, 255, 0), 1)

            for r in range(grid_rows):
                for c in range(grid_cols):
                    center_x = c * step_x + step_x // 2
                    center_y = r * step_y + step_y // 2
                    label = f"{c},{r}"
                    (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                    cv2.rectangle(
                        img_bgr,
                        (center_x - w // 2 - 2, center_y - h // 2 - 2),
                        (center_x + w // 2 + 2, center_y + h // 2 + 2),
                        (0, 0, 0),
                        -1,
                    )
                    cv2.putText(
                        img_bgr,
                        label,
                        (center_x - w // 2, center_y + h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 255),
                        1,
                    )

            return img_bgr

        except Exception as e:
            self.logger.error(t("log.perception.grid_gen_error", error=e))
            return np.zeros((100, 100, 3), dtype=np.uint8)

    # --- [NUOVO v22.1] VISUAL OPERATOR (OCR LOCATOR) ---
    def find_text_on_screen(self, query: str) -> Optional[Tuple[int, int]]:
        """
        Cerca una stringa di testo sullo schermo e restituisce le coordinate (x, y).
        """
        self.logger.log(t("log.perception.spatial_search", query=query), "VISION")

        if self.ocr_reader:
            try:
                screenshot = pyautogui.screenshot()
                img_np = np.array(screenshot)
                img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

                results = self.ocr_reader.readtext(img_bgr)

                query_lower = query.lower().strip()
                for (bbox, text, prob) in results:
                    text_lower = text.lower().strip()
                    if query_lower in text_lower or text_lower in query_lower:
                        tl, tr, br, bl = bbox
                        center_x = int((tl[0] + br[0]) / 2)
                        center_y = int((tl[1] + br[1]) / 2)
                        self.logger.log(
                            t(
                                "log.perception.text_found",
                                x=center_x,
                                y=center_y,
                                prob=f"{prob:.2f}",
                            ),
                            "VISION",
                        )
                        return (center_x, center_y)
            except Exception as e:
                self.logger.error(t("log.perception.spatial_search_error", error=e))

        if self.cervello:
            self.logger.log(t("log.perception.neural_fallback"), "VISION")
            grid_frame = self.get_screen_with_grid()
            analysis = self.cervello.analizza_visione_operativa(grid_frame)

            match = re.search(
                rf"{re.escape(query)}.*?cella\s+(\d+),(\d+)", analysis, re.IGNORECASE
            )
            if match:
                grid_x, grid_y = int(match.group(1)), int(match.group(2))
                sw, sh = pyautogui.size()
                target_x = int((grid_x * (sw / 10)) + (sw / 20))
                target_y = int((grid_y * (sh / 10)) + (sh / 20))
                return (target_x, target_y)

        return None

    # --- RIFONDAZIONE: ACTIVE HEARING (UDITO ATTIVO) ---
    def start_active_hearing(self) -> Tuple[bool, str]:
        if self.is_active_hearing and self.active_hearing_thread and self.active_hearing_thread.is_alive():
            return True, t("log.perception.hearing_already_active")
        
        # ---[FIX 2A] PREVENZIONE MICROFONO ZOMBIE ---
        # Assicuriamoci che il vecchio thread sia morto prima di riaprire il microfono
        if self.active_hearing_thread and self.active_hearing_thread.is_alive():
            self.is_active_hearing = False
            self.active_hearing_thread.join(timeout=2)

        self.is_active_hearing = True
        self.active_hearing_thread = threading.Thread(
            target=self._active_hearing_loop, daemon=True
        )
        self.active_hearing_thread.start()
        self.logger.log(t("log.perception.hearing_active"))
        return True, t("log.perception.hearing_active")

    def stop_active_hearing(self) -> Tuple[bool, str]:
        self.is_active_hearing = False
        if self.active_hearing_thread:
            self.active_hearing_thread.join(timeout=2)
        self.logger.log(t("log.perception.hearing_deactivated"))
        return True, t("log.perception.hearing_deactivated")

    # --- NUOVO: HELPER TRASCRIZIONE IBRIDA (WHISPER/GOOGLE) ---
    def _transcribe_audio(self, audio_data: sr.AudioData) -> str:
        """
        Trascrive l'audio usando Whisper (se disponibile) o Google (fallback).
        """
        text = ""

        if self.whisper:
            try:
                wav_bytes = audio_data.get_wav_data()
                audio_stream = io.BytesIO(wav_bytes)
                segments, info = self.whisper.transcribe(
                    audio_stream, beam_size=5, language="it"
                )
                text = " ".join([segment.text for segment in segments]).strip()
            except Exception as e:
                self.logger.error(t("log.perception.whisper_transcribe_error", error=e))

        if not text:
            try:
                text = self.recognizer.recognize_google(audio_data, language="it-IT")
            except sr.UnknownValueError:
                return ""
            except Exception as e:
                self.logger.error(t("log.perception.google_transcribe_error", error=e))
                return ""

        if not text:
            return ""

        text_lower = text.lower().strip()

        for phrase in HALLUCINATION_PHRASES:
            if phrase in text_lower:
                self.logger.log(
                    t("log.perception.filter_hallucination", text=text), "DEBUG"
                )
                return ""

        if len(text_lower) < 2:
            self.logger.log(t("log.perception.filter_short", text=text), "DEBUG")
            return ""

        if "grazie" in text_lower and len(text_lower.split()) < 3:
            self.logger.log(t("log.perception.filter_thanks", text=text), "DEBUG")
            return ""

        return text

    def _active_hearing_loop(self):
        """
        Ciclo di ascolto continuo. Se rileva voce, trascrive e invia alla coda.
        """
        self.logger.log(t("log.perception.hearing_init_loop"))
        while self.is_active_hearing:
            if self.udito_in_pausa.is_set():
                time.sleep(0.5)
                continue

            with self.mic_lock:
                try:
                    with self.microphone as source:
                        audio = self.recognizer.listen(
                            source, timeout=1, phrase_time_limit=15  # [FIX 2A] Timeout ridotto per sblocco rapido del thread
                        )

                    # --- [FASE 4] ASCOLTO AUDIO NATIVO ---
                    if self.cervello and self.cervello.supports_native_audio:
                        TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
                        temp_wav = TEMP_AUDIO_DIR / f"active_hearing_{int(time.time())}.wav"
                        with open(temp_wav, "wb") as f:
                            f.write(audio.get_wav_data())
                        text = f"[AUDIO_REF: {temp_wav}]"
                    else:
                        text = self._transcribe_audio(audio)

                    if text:
                        self.last_sensory_timestamp = time.time()  # [NUOVO FASE 1.1] Reset Quiete
                        self.last_audio_data = audio
                        self.logger.log(t("log.perception.hearing_to_queue", text=text))
                        self.transcribed_text_queue.put(text)

                except sr.WaitTimeoutError:
                    continue
                except Exception as e:
                    self.logger.log(t("log.perception.active_hearing_error", error=e))
                    time.sleep(1)

    # --- ASCOLTO COMANDO DIRETTO (PTT) ---
    def ascolta_comando_diretto(self) -> Optional[str]:
        if self.microphone is None:
            self.logger.warning("Ascolto vocale ignorato: nessun microfono disponibile sul sistema.")
            return ""
        self.logger.log(t("log.perception.ptt_start"))
        with self.mic_lock:
            try:
                with self.microphone as source:
                    self.logger.log(t("log.perception.ptt_open"))
                    audio = self.recognizer.listen(
                        source, timeout=5, phrase_time_limit=15
                    )

                self.logger.log(t("log.perception.ptt_captured"))
                
                # --- [FASE 4] ASCOLTO AUDIO NATIVO ---
                if self.cervello and self.cervello.supports_native_audio:
                    TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
                    temp_wav = TEMP_AUDIO_DIR / f"ptt_{int(time.time())}.wav"
                    with open(temp_wav, "wb") as f:
                        f.write(audio.get_wav_data())
                    text = f"[AUDIO_REF: {temp_wav}]"
                else:
                    text = self._transcribe_audio(audio)

                if text:
                    self.last_audio_data = audio
                    self.logger.log(t("log.perception.ptt_transcription", text=text))
                    return text
            except sr.WaitTimeoutError:
                self.logger.log(t("log.perception.ptt_timeout"))
            except Exception as e:
                self.logger.error(t("log.perception.ptt_error", error=e))
        return None

    # --- ANALISI ESPRESSIONE FACCIALE (GEOMETRICA) ---
    def _analyze_expression(self, landmarks: Dict[str, List[Tuple[int, int]]]) -> str:
        try:
            top_lip = landmarks["top_lip"]
            bottom_lip = landmarks["bottom_lip"]
            mouth_height = np.mean([p[1] for p in bottom_lip]) - np.mean(
                [p[1] for p in top_lip]
            )
            left_corner = top_lip[0]
            right_corner = top_lip[6]
            mouth_width = math.hypot(
                right_corner[0] - left_corner[0], right_corner[1] - left_corner[1]
            )
            mar = mouth_height / mouth_width if mouth_width > 0 else 0

            left_eye = landmarks["left_eye"]
            right_eye = landmarks["right_eye"]

            def get_eye_height(eye_points):
                top = np.mean([eye_points[1][1], eye_points[2][1]])
                bottom = np.mean([eye_points[4][1], eye_points[5][1]])
                return abs(bottom - top)

            avg_eye_height = (get_eye_height(left_eye) + get_eye_height(right_eye)) / 2

            if mar > 0.5:
                return t("log.perception.expression_surprise")
            elif mar > 0.3:
                return t("log.perception.expression_happy")
            elif avg_eye_height < 3.0:
                return t("log.perception.expression_tired")
            else:
                return t("log.perception.expression_neutral")
        except Exception:
            return t("log.perception.expression_error")

    # --- ANALISI BIOMETRICA SENSORIALE (EVOLUTA - OPZIONE 2) ---
    def _analizza_biometria_sensoriale(
        self, frame: Optional[np.ndarray], audio_data: Optional[Any]
    ):
        report = None

        if frame is not None:
            try:
                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                face_landmarks_list = face_recognition.face_landmarks(rgb_small_frame)

                if face_landmarks_list:
                    report = {
                        "tono_voce": t("log.perception.biometric.not_analyzed"),
                        "ritmo_respiratorio": t("log.perception.biometric.regular"),
                        "micro_espressioni": t("log.perception.biometric.neutral"),
                        "livello_stress_stimato": t("log.perception.biometric.low"),
                    }

                    if self.movement_intensity > 5.0:
                        report["ritmo_respiratorio"] = t(
                            "log.perception.biometric.accelerated"
                        )
                        report["livello_stress_stimato"] = t(
                            "log.perception.biometric.medium_high"
                        )
                    elif self.movement_intensity > 1.0:
                        report["ritmo_respiratorio"] = t(
                            "log.perception.biometric.slightly_irregular"
                        )
                    else:
                        report["ritmo_respiratorio"] = t(
                            "log.perception.biometric.calm_deep"
                        )

                    # --- [NUOVO v20.0] VIBE CHECK (MediaPipe FaceLandmarker) ---
                    vibe_status = t("log.perception.biometric.neutral")
                    if self.face_landmarker:
                        import mediapipe as mp

                        mp_image = mp.Image(
                            image_format=mp.ImageFormat.SRGB,
                            data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
                        )
                        face_result = self.face_landmarker.detect(mp_image)

                        if face_result and face_result.face_blendshapes:
                            blendshapes = face_result.face_blendshapes[0]
                            scores = dict()
                            for b in blendshapes:
                                scores[b.category_name] = b.score

                            brow_down = scores.get("browDownLeft", 0.0) + scores.get(
                                "browDownRight", 0.0
                            )
                            mouth_frown = scores.get(
                                "mouthFrownLeft", 0.0
                            ) + scores.get("mouthFrownRight", 0.0)
                            eye_blink = scores.get("eyeBlinkLeft", 0.0) + scores.get(
                                "eyeBlinkRight", 0.0
                            )

                            if brow_down > 0.8:
                                vibe_status = t("log.perception.vibe_stressed")
                            elif mouth_frown > 0.8:
                                vibe_status = t("log.perception.vibe_sad")
                            elif eye_blink > 1.2:
                                vibe_status = t("log.perception.vibe_tired")

                    # Fallback geometrico se MediaPipe fallisce
                    expression = self._analyze_expression(face_landmarks_list[0])
                    report["micro_espressioni"] = f"{expression} | Vibe: {vibe_status}"
            except Exception as e:
                report = None

        self.last_biometric_report = report

    def get_biometric_report(self) -> str:
        r = self.last_biometric_report
        if not r:
            return ""
        return t(
            "log.perception.biometric.report_template",
            respiro=r["ritmo_respiratorio"],
            espressione=r["micro_espressioni"],
            stress=r["livello_stress_stimato"],
        )

    def get_hardware_status(self) -> str:
        try:
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            battery = psutil.sensors_battery()

            if battery:
                status_label = (
                    t("settings.schedule.noise")
                    if battery.power_plugged
                    else t("settings.schedule.silence")
                )
                return t(
                    "log.perception.hardware_status_format",
                    cpu=cpu,
                    ram=ram,
                    battery=battery.percent,
                    status=status_label,
                )

            return t("log.perception.hardware_status_no_battery", cpu=cpu, ram=ram)
        except Exception:
            return t("log.perception.hw_not_detectable")

    # --- [NUOVO v19.2] RILEVAMENTO FINESTRA ATTIVA (WINDOWS) ---
    def get_active_window_title(self) -> str:
        if os.name == "nt":
            try:
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value
                return title if title else t("log.perception.window_unknown")
            except Exception as e:
                self.logger.error(t("log.perception.window_read_error_log", error=e))
                return t("log.perception.window_read_error")
        else:
            return t("log.perception.os_not_supported")

    # --- [NUOVO v19.4] RECUPERO PERCORSI DI SISTEMA REALI (WINDOWS) ---
    def get_system_paths(self) -> Dict[str, str]:
        paths = {
            "Desktop": "N/A",
            "Documents": "N/A",
            "Pictures": "N/A",
            "Videos": "N/A",
            "Music": "N/A",
        }

        if os.name != "nt":
            return paths

        try:
            reg_path = (
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            )
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
                mapping = {
                    "Desktop": "Desktop",
                    "Personal": "Documents",
                    "My Pictures": "Pictures",
                    "My Video": "Videos",
                    "My Music": "Music",
                }

                for reg_key, label in mapping.items():
                    try:
                        value, _ = winreg.QueryValueEx(key, reg_key)
                        expanded_value = os.path.expandvars(value)
                        paths[label] = expanded_value
                    except FileNotFoundError:
                        continue

            self.logger.log(
                t("log.perception.system_paths_mapped", path=paths["Desktop"]), "SYSTEM"
            )
        except Exception as e:
            self.logger.error(t("log.perception.system_paths_error", error=e))

        return paths

    def pausa_udito(self):
        if not self.udito_in_pausa.is_set():
            self.udito_in_pausa.set()
            self.logger.log(t("log.perception.ear_pause"))

    def riprendi_udito(self):
        if self.udito_in_pausa.is_set():
            self.udito_in_pausa.clear()
            self.logger.log(t("log.perception.ear_resume"))

    def release_camera(self):
        if not self.camera_paused.is_set():
            self.camera_paused.set()
            if self.video_capture and self.video_capture.isOpened():
                self.video_capture.release()
                self.logger.log(t("log.perception.webcam_released"))

    def acquire_camera(self):
        if self.camera_paused.is_set():
            self.logger.log(t("log.perception.webcam_reacquire"))
            try:
                self.video_capture = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                
                # --- [FIX CRITICO] FALLBACK WEBCAM ---
                if not self.video_capture.isOpened():
                    self.video_capture = cv2.VideoCapture(0)
                    
                if not self.video_capture.isOpened():
                    self.logger.log(t("log.perception.webcam_reacquire_error"))
                    self.video_capture = None
                else:
                    self.logger.log(t("log.perception.webcam_reacquired"))
            except Exception as e:
                self.logger.log(t("log.perception.webcam_reacquire_critical", error=e))
                self.video_capture = None
            finally:
                self.camera_paused.clear()

    def start_perception_loop(self):
        self.is_running = True
        self.logger.log(t("log.perception.webcam_open_attempt"))
        try:
            # Tentativo 1: DirectShow (Più veloce su Windows, ma sensibile ai driver)
            self.video_capture = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            
            # --- [FIX CRITICO] FALLBACK WEBCAM ---
            # Se DirectShow fallisce (es. telecamere virtuali o permessi), proviamo il backend di default
            if not self.video_capture.isOpened():
                self.logger.warning("DirectShow fallito. Tento fallback sul backend video predefinito...")
                self.video_capture = cv2.VideoCapture(0)
                
            if not self.video_capture.isOpened():
                print(t("log.perception.webcam_open_error"))
                self.video_capture = None
            else:
                self.vision_thread = threading.Thread(
                    target=self._vision_loop, daemon=True
                )
                self.vision_thread.start()
                self.logger.log(t("log.perception.webcam_opened"))
        except Exception as e:
            print(t("log.perception.vision_critical_error", error=e))
            self.video_capture = None

        # --- [NUOVO v30.0] AVVIO CARE AUDIO MONITOR ---
        self.is_care_listening = True
        self.care_audio_thread = threading.Thread(
            target=self._care_audio_loop, daemon=True
        )
        self.care_audio_thread.start()

    def stop_perception_loop(self):
        self.is_running = False
        self.is_care_listening = False  # Stop Care Audio
        self.stop_monitoring()
        self.stop_active_hearing()  # Ferma Active Hearing se attivo
        if self.vision_thread:
            self.vision_thread.join(timeout=2)
        if self.care_audio_thread:
            self.care_audio_thread.join(timeout=2)
        if self.video_capture:
            self.video_capture.release()
        self.logger.log(t("log.perception.perception_cycles_ended"))

    def _analyze_care_vision(self, frame: np.ndarray):
        """
        Analizza il frame per rilevare intrusioni e cadute (Care OS).
        Usa MediaPipe Object & Pose Detection.
        [FIX BUG 02] Master Check: Esegue l'analisi solo se i moduli sono attivi.
        """
        if not self.care_engine:
            return

        # Recupera stato moduli
        modules = self.care_engine.config.get("modules", {})
        baby_active = modules.get("baby_monitor", {}).get("enabled", False)
        pet_active = modules.get("pet_monitor", {}).get("enabled", False)
        elderly_active = modules.get("elderly_helper", {}).get("enabled", False)

        # Se nessun modulo visivo è attivo, esci subito (Risparmio Risorse & Anti-Spam)
        if not (baby_active or pet_active or elderly_active):
            return

        # Se i modelli non sono pronti, esci
        if not self.object_detector or not self.pose_landmarker:
            return

        import mediapipe as mp

        # Conversione Frame per MediaPipe
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
        )

        # 1. OBJECT DETECTION (Pet Monitor / Baby Monitor)
        # Esegui solo se richiesto dai moduli attivi
        if baby_active or pet_active:
            detections = self.object_detector.detect(mp_image)

            for detection in detections.detections:
                category = detection.categories[0]
                label = category.category_name.lower()  # 'dog', 'cat', 'person'
                score = category.score

                if score < 0.5:
                    continue

                # Calcola centro oggetto
                bbox = detection.bounding_box
                center_x = bbox.origin_x + (bbox.width / 2)
                center_y = bbox.origin_y + (bbox.height / 2)

                # Normalizza coordinate (0.0 - 1.0)
                h, w, _ = frame.shape
                norm_x = center_x / w
                norm_y = center_y / h

                # Check Zone
                for zone in self.care_engine.config.get("zones", []):
                    zx, zy, zw, zh = zone["coordinates"]
                    # Verifica se il centro dell'oggetto è nella zona
                    if zx <= norm_x <= zx + zw and zy <= norm_y <= zy + zh:
                        self.care_engine.process_trigger(
                            "visual_zone_entry",
                            {
                                "zone_id": zone["id"],
                                "zone_name": zone["name"],
                                "class_name": label,
                                "confidence": score,
                            },
                        )

        # 2. POSE DETECTION (Elderly Helper - Fall Detection)
        # Esegui solo se Elderly Helper è attivo
        if elderly_active:
            pose_result = self.pose_landmarker.detect(mp_image)

            if pose_result.pose_landmarks:
                for landmarks in pose_result.pose_landmarks:
                    if self._detect_fall(landmarks):
                        self.logger.log(t("log.perception.fall_detected"), "CARE")
                        self.care_engine.process_trigger(
                            "fall_detected",
                            {"confidence": 0.9, "timestamp": time.time()},
                        )

    # --- [NUOVO v119.0] INIZIALIZZAZIONE YAMNET ---
    def _init_yamnet(self):
        """Scarica e inizializza il modello YAMNet per la classificazione audio."""
        if not MEDIAPIPE_AVAILABLE:
            return

        try:
            from mediapipe.tasks import python
            from mediapipe.tasks.python import audio
            import urllib.request

            model_path = Path("models/yamnet.tflite")
            model_url = "https://storage.googleapis.com/mediapipe-models/audio_classifier/yamnet/float32/1/yamnet.tflite"

            if not model_path.exists():
                self.logger.log(t("log.perception.yamnet_download"), "INIT")
                model_path.parent.mkdir(parents=True, exist_ok=True)
                urllib.request.urlretrieve(model_url, model_path)
                self.logger.log(t("log.perception.yamnet_ready"), "INIT")

            base_options = python.BaseOptions(model_asset_path=str(model_path))
            options = audio.AudioClassifierOptions(
                base_options=base_options, max_results=3, score_threshold=0.3
            )
            with suppress_cpp_stderr():
                self.audio_classifier = audio.AudioClassifier.create_from_options(options)
            self.logger.log(t("log.perception.yamnet_init"), "INIT")

        except Exception as e:
            self.logger.error(t("log.perception.yamnet_init_error", error=e))
            self.audio_classifier = None

    # --- [NUOVO FASE B] INIZIALIZZAZIONE VISIONE (POSE & OBJECT) ---
    def _init_vision_models(self):
        """Scarica e inizializza i modelli di visione MediaPipe."""
        try:
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision
            import urllib.request

            # 1. Object Detector (EfficientDet-Lite0)
            obj_model_path = Path("models/efficientdet_lite0.tflite")
            obj_url = "https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite0/float32/1/efficientdet_lite0.tflite"

            if not obj_model_path.exists():
                self.logger.log(t("log.perception.efficientdet_download"), "INIT")
                obj_model_path.parent.mkdir(parents=True, exist_ok=True)
                urllib.request.urlretrieve(obj_url, obj_model_path)

            obj_options = vision.ObjectDetectorOptions(
                base_options=python.BaseOptions(model_asset_path=str(obj_model_path)),
                max_results=5,
                score_threshold=0.5,
            )
            with suppress_cpp_stderr():
                self.object_detector = vision.ObjectDetector.create_from_options(
                    obj_options
                )

            # 2. Pose Landmarker (Lite)
            pose_model_path = Path("models/pose_landmarker_lite.task")
            pose_url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"

            if not pose_model_path.exists():
                self.logger.log(t("log.perception.pose_download"), "INIT")
                urllib.request.urlretrieve(pose_url, pose_model_path)

            pose_options = vision.PoseLandmarkerOptions(
                base_options=python.BaseOptions(model_asset_path=str(pose_model_path)),
                num_poses=2,
                min_pose_detection_confidence=0.5,
            )
            with suppress_cpp_stderr():
                self.pose_landmarker = vision.PoseLandmarker.create_from_options(
                    pose_options
                )

            # 3. Face Landmarker (Vibe Check - Panopticon)
            face_model_path = Path("models/face_landmarker.task")
            face_url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"

            if not face_model_path.exists():
                self.logger.log(t("log.perception.face_download"), "INIT")
                urllib.request.urlretrieve(face_url, face_model_path)

            face_options = vision.FaceLandmarkerOptions(
                base_options=python.BaseOptions(model_asset_path=str(face_model_path)),
                output_face_blendshapes=True,
                output_facial_transformation_matrixes=True,
                num_faces=1,
            )
            with suppress_cpp_stderr():
                self.face_landmarker = vision.FaceLandmarker.create_from_options(
                    face_options
                )

            self.logger.log(t("log.perception.vision_advanced_ready"), "INIT")

        except Exception as e:
            self.logger.error(t("log.perception.vision_init_error", error=e))
            self.object_detector = None
            self.pose_landmarker = None

    def _detect_fall(self, landmarks) -> bool:
        """
        Euristica semplice per rilevare una caduta:
        1. Bounding box più largo che alto (Persona orizzontale).
        2. Centro di massa basso (vicino al pavimento).
        [FIX A0006] Resa molto più stringente per evitare falsi positivi quando l'utente è seduto vicino.
        """
        # Estrai coordinate Y (verticali)
        ys =[lm.y for lm in landmarks]
        xs = [lm.x for lm in landmarks]

        min_y, max_y = min(ys), max(ys)
        min_x, max_x = min(xs), max(xs)

        height = max_y - min_y
        width = max_x - min_x

        # 1. Deve essere nettamente orizzontale (rapporto 1.5 invece di 1.2)
        is_horizontal = width > (height * 1.5)
        
        # 2. Deve essere schiacciato sul fondo del frame (0.9 invece di 0.8)
        is_low = max_y > 0.9
        
        # 3. Il bounding box deve avere una dimensione minima per evitare glitch su detection parziali
        is_large_enough = width > 0.3

        return is_horizontal and is_low and is_large_enough

    def _care_audio_loop(self):
        """
        Monitora l'ambiente per suoni di allarme usando YAMNet (Orecchio Assoluto).
        """
        # --- [FIX CRITICO] BYPASS MICROFONO FANTASMA ---
        # Se l'inizializzazione principale ha fallito (nessun microfono di default),
        # disattiviamo silenziosamente il Care Audio Loop per evitare il crash di PyAudio (Errno -9996).
        if self.microphone is None:
            self.logger.warning("Care OS Audio disattivato: Nessun microfono di default rilevato sul sistema.")
            return

        self.logger.log(t("log.perception.yamnet_active"), "CARE")

        # Inizializza YAMNet se non fatto
        if not hasattr(self, "audio_classifier"):
            self._init_yamnet()

        # Configurazione Audio (YAMNet richiede 16kHz mono)
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000  # YAMNet standard
        BUFFER_SECONDS = 1.0  # YAMNet lavora su finestre di ~0.975s

        p = pyaudio.PyAudio()

        # Buffer circolare per accumulare 1 secondo di audio
        audio_buffer = deque(maxlen=int(RATE / CHUNK * BUFFER_SECONDS))

        try:
            stream = p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
            )

            while self.is_care_listening:
                if self.mic_lock.locked():
                    time.sleep(0.5)
                    continue

                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    audio_buffer.append(data)

                    # Analisi RMS per attivazione (Gate)
                    audio_data = np.frombuffer(data, dtype=np.int16).astype(np.float32)
                    rms = np.sqrt(np.mean(audio_data**2))

                    # Se c'è rumore significativo e il buffer è pieno
                    if (
                        rms > 500
                        and len(audio_buffer) == audio_buffer.maxlen
                        and self.audio_classifier
                    ):
                        # Ricostruisci il buffer completo
                        full_audio = b"".join(audio_buffer)

                        # Crea AudioData per MediaPipe
                        # Nota: MediaPipe richiede un array numpy float32 normalizzato [-1, 1] o int16
                        # Qui usiamo int16 diretto se supportato, o convertiamo
                        import mediapipe as mp

                        # Conversione byte -> numpy int16 -> float32
                        np_audio = (
                            np.frombuffer(full_audio, dtype=np.int16).astype(np.float32)
                            / 32768.0
                        )

                        # Crea contenitore MediaPipe
                        mp_audio = (
                            mp.tasks.components.containers.AudioData.create_from_array(
                                np_audio, sample_rate=RATE
                            )
                        )

                        # Classifica
                        results = self.audio_classifier.classify(mp_audio)

                        # Analisi Risultati
                        if results:
                            # Prendi la testa di classificazione (solitamente index 0)
                            categories = results[0].classifications[0].categories

                            for cat in categories:
                                trigger_type = None
                                label = cat.category_name.lower()
                                score = cat.score

                                # Mappatura Classi YAMNet -> Trigger Care OS
                                if score > 0.5:
                                    if (
                                        "crying" in label
                                        or "sobbing" in label
                                        or "baby" in label
                                    ):
                                        trigger_type = "audio_cry"
                                    elif "dog" in label or "bark" in label:
                                        trigger_type = "audio_bark"
                                    elif "glass" in label or "shatter" in label:
                                        trigger_type = "audio_glass"
                                    elif "scream" in label or "shout" in label:
                                        trigger_type = "audio_scream"

                                    if trigger_type:
                                        self.last_sensory_timestamp = time.time()  # [NUOVO FASE 1.1] Reset Quiete
                                        self.logger.log(
                                            t(
                                                "log.perception.yamnet_detection",
                                                label=label,
                                                score=f"{score:.2f}",
                                            ),
                                            "CARE",
                                        )
                                        self.care_engine.process_trigger(
                                            trigger_type,
                                            {
                                                "label": label,
                                                "confidence": score,
                                                "rms": rms,
                                            },
                                        )
                                        # Svuota buffer per evitare trigger doppi immediati
                                        audio_buffer.clear()
                                        break

                except Exception as e:
                    # self.logger.error(f"Audio Loop Error: {e}")
                    pass

        except Exception as e:
            self.logger.error(t("log.perception.care_audio_init_error", error=e))
        finally:
            if "stream" in locals():
                stream.stop_stream()
                stream.close()
            p.terminate()

    def _vision_loop(self):
        process_this_frame = True
        while self.is_running:
            if self.camera_paused.is_set():
                time.sleep(0.5)
                continue

            try:
                if not self.video_capture or not self.video_capture.isOpened():
                    time.sleep(1)
                    continue

                ret, frame = self.video_capture.read()
                if not ret:
                    time.sleep(0.1)
                    continue
                self.last_frame = frame.copy()

                # --- [NUOVO v30.0] CARE OS VISION ---
                # Salta l'analisi se il sistema è in pausa per il rito di apprendimento
                if not self.analysis_paused.is_set():
                    self._analyze_care_vision(frame)

                # --- [NUOVO v21.0] BUFFER CIRCOLARE VIDEO ---
                current_time = time.time()
                if current_time - self.last_buffer_update >= 1.0:
                    self.frame_buffer.append(frame.copy())
                    self.last_buffer_update = current_time

                if self.prev_frame is not None:
                    diff = cv2.absdiff(
                        cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), self.prev_frame
                    )
                    self.movement_intensity = np.mean(diff)
                    
                    # ---[NUOVO v129.0] MOTION DETECTION (EVENT-DRIVEN VISION) ---
                    # Se il movimento supera una soglia significativa (es. l'utente si alza o gesticola)
                    if self.movement_intensity > 12.0:
                        self.last_sensory_timestamp = time.time()  # [NUOVO FASE 1.1] Reset Quiete
                        now_motion = time.time()
                        # Debounce di 60 secondi per non spammare eventi
                        if now_motion - getattr(self, 'last_motion_trigger_time', 0) > 60:
                            self.logger.log(t("log.perception.motion_detected", intensity=f"{self.movement_intensity:.1f}"), "VISION")
                            if hasattr(self, "event_hub") and self.event_hub:
                                self.event_hub.push_event(
                                    source="camera",
                                    event_type="environmental_trigger",
                                    data={
                                        "event": "physical_movement_detected",
                                        "severity": "low"
                                    },
                                )
                            self.last_motion_trigger_time = now_motion

                self.prev_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # --- ANALISI BIOMETRICA ---
                if not self.analysis_paused.is_set() and int(time.time()) % 2 == 0:
                    self._analizza_biometria_sensoriale(self.last_frame, None)

                # --- [FIX v18.2] HARDWARE ALERT PUSH (DEBOUNCE) ---
                current_time_hw = time.time()
                if (
                    hasattr(self, "event_hub")
                    and self.event_hub
                    and (current_time_hw - self.last_hardware_push >= 10.0)
                ):
                    try:
                        cpu = psutil.cpu_percent()
                        ram = psutil.virtual_memory().percent
                        self.event_hub.push_event(
                            "system", "hardware_alert", {"cpu": cpu, "ram": ram}
                        )
                        self.last_hardware_push = current_time_hw
                    except Exception:
                        pass

                if process_this_frame and not self.analysis_paused.is_set():
                    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                    face_locations = face_recognition.face_locations(rgb_small_frame)
                    face_encodings = face_recognition.face_encodings(
                        rgb_small_frame, face_locations
                    )
                    detected = []
                    for face_encoding in face_encodings:
                        matches = face_recognition.compare_faces(
                            self.known_face_encodings, face_encoding
                        )
                        name = t("log.perception.unknown_user")
                        if True in matches:
                            face_distances = face_recognition.face_distance(
                                self.known_face_encodings, face_encoding
                            )
                            best_match_index = np.argmin(face_distances)
                            if (
                                matches[best_match_index]
                                and face_distances[best_match_index] < 0.6
                            ):
                                name = self.known_souls_data[best_match_index]
                        detected.append(name)

                    # --- [NUOVO] LOGICA ANTI-SFARFALLIO (DEBOUNCE 15 SECONDI) ---
                    raw_current_names = sorted(
                        [s["nome"] if isinstance(s, dict) else s for s in detected]
                    )
                    now = time.time()

                    # 1. Aggiorna i timer per chi è inquadrato in questo esatto frame
                    for n in raw_current_names:
                        self.last_seen_times[n] = now

                    # 2. Costruisci la lista stabile (chi è stato visto negli ultimi 15s)
                    debounced_names = []
                    for n, last_seen in list(self.last_seen_times.items()):
                        if now - last_seen <= 15.0:
                            debounced_names.append(n)
                        else:
                            del self.last_seen_times[n]  # Rimuovi definitivamente

                    debounced_names = sorted(list(set(debounced_names)))

                    # --- [FIX BUG 01] FILTRO ANTI-FANTASMA ---
                    # Se c'è almeno un volto noto (diverso da Sconosciuto), ignora i falsi positivi "Sconosciuto"
                    if (
                        len(debounced_names) > 1
                        and t("log.perception.unknown_user") in debounced_names
                    ):
                        debounced_names.remove(t("log.perception.unknown_user"))

                    previous_names = sorted(
                        [
                            s["nome"] if isinstance(s, dict) else s
                            for s in self.current_detected_souls
                        ]
                    )

                    # 3. Logga e aggiorna SOLO se la lista stabile è cambiata
                    if debounced_names != previous_names:
                        # --- FIX ANTI-SFARFALLIO DEFINITIVO ---
                        if not debounced_names:
                            # Se la lista è vuota, ignoriamo l'aggiornamento.
                            # L'Anima ricorderà l'ultimo volto visto all'infinito.
                            pass
                        else:
                            self.logger.log(
                                t(
                                    "log.perception.detection_changed",
                                    names=debounced_names,
                                )
                            )

                            self.last_sensory_timestamp = time.time()  # [NUOVO FASE 1.1] Reset Quiete
                            # Ricostruisci gli oggetti soul per mantenere la compatibilità con il resto del sistema
                            new_detected_souls =[]
                            for n in debounced_names:
                                soul_obj = next(
                                    (
                                        s
                                        for s in self.known_souls_data
                                        if s["nome"] == n
                                    ),
                                    n,
                                )
                                new_detected_souls.append(soul_obj)

                            self.current_detected_souls = new_detected_souls

                            # [MODULO 3] Iniezione Dopamina/Ossitocina al riconoscimento visivo
                            if hasattr(self, "heart") and self.heart and hasattr(self.heart, "inject_hormone"):
                                # Se vede qualcuno di noto, rilascia ormoni positivi
                                if any(isinstance(s, dict) for s in new_detected_souls):
                                    self.heart.inject_hormone("dopamina", 10)
                                    self.heart.inject_hormone("ossitocina", 5)

                            # ---[NUOVO v18.0] ENVIRONMENTAL TRIGGER PUSH ---
                            if hasattr(self, "event_hub") and self.event_hub:
                                self.event_hub.push_event(
                                    source="camera",
                                    event_type="environmental_trigger",
                                    data={
                                        "event": "user_recognized_by_webcam",
                                        "names": debounced_names,
                                        "severity": "medium",
                                    },
                                )

                process_this_frame = not process_this_frame
                time.sleep(0.33)
            except Exception as e:
                print(t("log.perception.vision_error", error=e))
                time.sleep(2)

    def get_transcribed_text(self) -> Optional[str]:
        try:
            return self.transcribed_text_queue.get_nowait()
        except queue.Empty:
            return None

    # --- [NUOVO v116.2] GETTER AUDIO GREZZO ---
    def get_last_audio_data(self) -> Optional[sr.AudioData]:
        return self.last_audio_data

    def get_latest_frame(self) -> Optional[np.ndarray]:
        return self.last_frame

    def get_last_sensory_timestamp(self) -> float:
        """[NUOVO FASE 1.1] Restituisce l'ultimo istante in cui i sensi hanno percepito qualcosa."""
        return self.last_sensory_timestamp

    # --- [NUOVO v21.0] GETTER CONTESTO VIDEO ---
    def get_video_context(self) -> List[np.ndarray]:
        return list(self.frame_buffer)

    def get_current_souls(self) -> List[Dict[str, Any] | str]:
        return self.current_detected_souls

    def get_status(self) -> str:
        status = []
        if self.vision_thread and self.vision_thread.is_alive():
            if self.camera_paused.is_set():
                status.append(t("log.perception.status_webcam_pause"))
            else:
                names = [
                    s["nome"] if isinstance(s, dict) else s
                    for s in self.current_detected_souls
                ]
                names_str = (
                    ", ".join(names)
                    if names
                    else t("log.perception.status_webcam_none")
                )
                status.append(
                    t("log.perception.status_webcam_detecting", names=names_str)
                )
        else:
            status.append(t("log.perception.status_webcam_closed"))

        if self.is_active_hearing:
            status.append(t("log.perception.status_hearing_active"))
        else:
            status.append(t("log.perception.status_hearing_disabled"))

        if self.is_monitoring:
            status.append(
                t("log.perception.status_sauron_active", interval=self.monitor_interval)
            )
        else:
            status.append(t("log.perception.status_sauron_closed"))

        status.append(
            t("log.perception.status_health", status=self.get_hardware_status())
        )
        status.append(
            t("log.perception.status_window", title=self.get_active_window_title())
        )

        return "\n".join(status)

    # ---[NUOVO v20.0] METODI AUDIO DUCKING E VOLUME (PANOPTICON) ---
    def get_system_audio_volume(self) -> float:
        """Restituisce il picco di volume attuale del sistema (0.0 - 1.0)."""
        if not PYCAW_AVAILABLE:
            return 0.0
        try:
            sessions = AudioUtilities.GetAllSessions()
            max_vol = 0.0
            for session in sessions:
                if session.Process:
                    meter = session._ctl.QueryInterface(IAudioMeterInformation)
                    peak = meter.GetPeakValue()
                    if peak > max_vol:
                        max_vol = peak
            return max_vol
        except Exception as e:
            self.logger.error(t("log.perception.system_volume_error", error=e))
            return 0.0

    def set_audio_ducking(self, active: bool):
        """Abbassa il volume delle applicazioni multimediali (Ducking)."""
        if not PYCAW_AVAILABLE:
            return
        try:
            sessions = AudioUtilities.GetAllSessions()
            target_apps = (
                "vlc.exe",
                "chrome.exe",
                "msedge.exe",
                "spotify.exe",
                "firefox.exe",
            )

            for session in sessions:
                if session.Process and session.Process.name().lower() in target_apps:
                    vol_ctrl = session.SimpleAudioVolume
                    if active:
                        # Salva il volume originale se non è già in ducking
                        if not hasattr(session, "original_volume"):
                            session.original_volume = vol_ctrl.GetMasterVolume()
                        vol_ctrl.SetMasterVolume(0.15, None)
                    else:
                        # Ripristina il volume originale
                        orig_vol = getattr(session, "original_volume", 1.0)
                        vol_ctrl.SetMasterVolume(orig_vol, None)
        except Exception as e:
            self.logger.error(t("log.perception.audio_ducking_error", error=e))
