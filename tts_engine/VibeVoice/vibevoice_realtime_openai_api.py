#!/usr/bin/env python3
"""
VibeVoice OpenAI-Compatible TTS Server

A FastAPI server that wraps VibeVoice-Realtime-0.5B with an OpenAI-compatible API,
enabling integration with Open WebUI and other OpenAI TTS-compatible applications.

Usage:
    python vibevoice_realtime_openai_api.py --port 8880
"""

import argparse
import copy
import io
import os
import subprocess
import time
import traceback
import urllib.request
import logging  # [NUOVO] Per silenziamento log
import warnings  # [NUOVO] Per silenziamento avvisi
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

# --- [NUOVO v118.2] SILENZIAMENTO LOG E AVVISI ---
# Nasconde i messaggi "Some weights... were not initialized"
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("librosa").setLevel(logging.ERROR)
# Nasconde il messaggio "You should probably TRAIN this model"
warnings.filterwarnings("ignore", message=".*should probably TRAIN this model.*")
warnings.filterwarnings("ignore", category=UserWarning)

# Set HuggingFace cache BEFORE importing any HF libraries
# Only use HF_HOME (TRANSFORMERS_CACHE is deprecated in v5)
# MODELS_DIR can be overridden via env var for Docker volume mounts
MODELS_DIR = Path(os.environ.get("MODELS_DIR", Path(__file__).parent / "models"))
os.environ["HF_HOME"] = str(MODELS_DIR / "huggingface")

import numpy as np
import torch
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field
import uvicorn
import scipy.io.wavfile as wavfile

# --- [FIX CRITICO] INIEZIONE PATH PER TRADUTTORE ---
import sys

_SCRIPT_DIR = Path(__file__).parent.resolve()
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from utils.translator import t

# VibeVoice imports (after setting HF_HOME)
from vibevoice.modular.modeling_vibevoice_streaming_inference import (
    VibeVoiceStreamingForConditionalGenerationInference,
)
from vibevoice.processor.vibevoice_streaming_processor import (
    VibeVoiceStreamingProcessor,
)

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

SAMPLE_RATE = 24000
DEFAULT_MODEL_PATH = "microsoft/VibeVoice-Realtime-0.5B"

# CFG scale for generation (configurable via env var)
CFG_SCALE = float(os.environ.get("CFG_SCALE", "1.25"))

# Voices directory
VOICES_DIR = MODELS_DIR / "voices"

# --- [NUOVO v118.3] MAPPATURA BANDIERE E LINGUE ---
LANG_TO_FLAG = {
    "de": "🇩🇪",
    "en": "🇺🇸",
    "fr": "🇫🇷",
    "in": "🇮🇳",
    "it": "🇮🇹",
    "jp": "🇯🇵",
    "kr": "🇰🇷",
    "nl": "🇳🇱",
    "pl": "🇵🇱",
    "pt": "🇵🇹",
    "sp": "🇪🇸",
}

# OpenAI voice name mapping to VibeVoice voices (Fallback legacy)
OPENAI_TO_VIBEVOICE_MAP = {
    "alloy": "en-Carter_man",
    "echo": "en-Davis_man",
    "fable": "en-Emma_woman",
    "onyx": "en-Frank_man",
    "nova": "en-Grace_woman",
    "shimmer": "en-Mike_man",
}

# Supported audio formats
SUPPORTED_FORMATS = ["mp3", "wav", "opus", "flac", "aac", "pcm"]

# ------------------------------------------------------------------------------
# Model Download Utilities
# ------------------------------------------------------------------------------


def ensure_voices_downloaded() -> None:
    """
    [MODIFICA v118.3] Rimosso download automatico.
    Verifica solo l'esistenza della cartella per le voci locali.
    """
    if not VOICES_DIR.exists():
        print(t("vibevoice.log.creating_voices_dir", dir=VOICES_DIR))
        VOICES_DIR.mkdir(parents=True, exist_ok=True)


def get_model_cache_dir() -> str:
    """Get model cache directory"""
    model_cache = MODELS_DIR / "huggingface"
    model_cache.mkdir(parents=True, exist_ok=True)
    return str(model_cache)


# ------------------------------------------------------------------------------
# Pydantic Models
# ------------------------------------------------------------------------------


class TTSRequest(BaseModel):
    """OpenAI-compatible TTS request"""

    input: str = Field(..., description="Text to synthesize", max_length=4096)
    voice: str = Field(default="Carter", description="Voice ID")
    model: str = Field(
        default="tts-1", description="Model ID (ignored, for compatibility)"
    )
    response_format: str = Field(default="mp3", description="Audio format")
    speed: float = Field(default=1.0, description="Speed (not yet supported)")
    stream: bool = Field(default=False, description="Enable streaming response")


class VoiceInfo(BaseModel):
    """Voice information"""

    voice_id: str
    name: str
    type: str
    gender: Optional[str] = None


class VoicesResponse(BaseModel):
    """Response for /v1/audio/voices endpoint"""

    voices: List[VoiceInfo]


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    service: str
    model_loaded: bool
    device: str
    features: Dict[str, Any]


# ------------------------------------------------------------------------------
# TTS Service
# ------------------------------------------------------------------------------


class VibeVoiceTTSService:
    """Service for managing VibeVoice model and generating speech"""

    def __init__(self, model_path: str, device: str = "cuda"):
        self.model_path = model_path
        self.device = device
        self.processor: Optional[VibeVoiceStreamingProcessor] = None
        self.model: Optional[VibeVoiceStreamingForConditionalGenerationInference] = None
        self.voice_presets: Dict[str, Path] = {}
        self._voice_cache: Dict[str, Any] = {}
        self._torch_device = torch.device(device)

    def load(self) -> None:
        """Load model and voice presets"""
        # Set HuggingFace cache to models folder
        os.environ["HF_HOME"] = get_model_cache_dir()

        # Download voice presets
        ensure_voices_downloaded()

        print(t("vibevoice.log.loading_processor", path=self.model_path))
        self.processor = VibeVoiceStreamingProcessor.from_pretrained(self.model_path)

        # Determine dtype and attention implementation based on device
        # [PATCH v118.1] Forzatura SDPA su Windows per evitare dipendenza flash-attn
        if self.device == "cuda":
            load_dtype = torch.bfloat16
            device_map = "cuda"
            # Flash Attention 2 è instabile su Windows nativo, usiamo SDPA (nativo in Torch)
            attn_impl = "sdpa"
        elif self.device == "mps":
            load_dtype = torch.float32
            device_map = None
            attn_impl = "sdpa"
        else:  # cpu
            load_dtype = torch.float32
            device_map = "cpu"
            attn_impl = "sdpa"

        print(t("vibevoice.log.loading_model", dtype=load_dtype, attn=attn_impl))

        try:
            # [PATCH v118.1] Caricamento diretto con SDPA per stabilità
            self.model = (
                VibeVoiceStreamingForConditionalGenerationInference.from_pretrained(
                    self.model_path,
                    torch_dtype=load_dtype,
                    device_map=device_map,
                    attn_implementation=attn_impl,
                )
            )
            if self.device == "mps":
                self.model.to("mps")
        except Exception as e:
            # Fallback estremo se anche SDPA fallisce (es. dtype non supportato)
            print(t("vibevoice.log.model_loading_issue", error=e))
            self.model = VibeVoiceStreamingForConditionalGenerationInference.from_pretrained(
                self.model_path,
                torch_dtype=torch.float32,  # Fallback a float32 se bfloat16 fallisce
                device_map=device_map,
                attn_implementation="sdpa",
            )

        self.model.eval()
        self.model.set_ddpm_inference_steps(num_steps=5)

        # Load voice presets
        self._load_voice_presets()
        print(t("vibevoice.log.model_ready", device=self.device))

    def _load_voice_presets(self) -> None:
        """
        [MODIFICA v118.3] Scanner Dinamico Metadati.
        Mappa i file .pt estraendo Lingua, Nome e Genere.
        """
        if not VOICES_DIR.exists():
            print(t("vibevoice.log.voices_dir_not_found", dir=VOICES_DIR))
            return

        count = 0
        for pt_file in VOICES_DIR.glob("*.pt"):
            full_id = pt_file.stem  # e.g., "it-Gemma_woman"
            self.voice_presets[full_id] = pt_file
            count += 1

        print(t("vibevoice.log.found_local_voices", count=count, dir=VOICES_DIR))

    def get_available_voices(self) -> List[VoiceInfo]:
        """
        [MODIFICA v118.3] Generazione Lista Voci con Bandiere e Genere.
        """
        voices = []

        # Scansiona i file caricati in self.voice_presets
        for voice_id, path in self.voice_presets.items():
            try:
                # Parsing: it-Gemma_woman
                # 1. Lingua
                lang_part = voice_id.split("-")[0] if "-" in voice_id else "???"
                flag = LANG_TO_FLAG.get(lang_part.lower(), "🌐")

                # 2. Nome e Genere
                # Rimuove la parte lingua: Gemma_woman
                name_gender_part = (
                    voice_id.split("-", 1)[1] if "-" in voice_id else voice_id
                )

                name = (
                    name_gender_part.split("_")[0]
                    if "_" in name_gender_part
                    else name_gender_part
                )
                gender_raw = (
                    name_gender_part.split("_")[1]
                    if "_" in name_gender_part
                    else "unknown"
                )

                gender_label = (
                    t("vibevoice.gender_woman")
                    if "woman" in gender_raw.lower()
                    else t("vibevoice.gender_man")
                    if "man" in gender_raw.lower()
                    else t("vibevoice.gender_other")
                )

                # Costruisce il nome visualizzato: 🇮🇹 Gemma (Woman)
                display_name = f"{flag} {name} ({gender_label})"

                voices.append(
                    VoiceInfo(
                        voice_id=voice_id,
                        name=display_name,
                        type="vibevoice-native",
                        gender=gender_raw.lower(),
                    )
                )
            except Exception as e:
                print(t("vibevoice.log.failed_parse_metadata", id=voice_id, error=e))

        # Ordina per lingua (bandiera)
        voices.sort(key=lambda x: x.name)

        # --- [NUOVO v118.4] AGGIUNTA ALIAS OPENAI ---
        # Aggiungiamo gli alias OpenAI in fondo alla lista per compatibilità
        for openai_name, vibevoice_id in OPENAI_TO_VIBEVOICE_MAP.items():
            voices.append(
                VoiceInfo(
                    voice_id=openai_name,
                    name=t("vibevoice.alias_label", name=openai_name.capitalize()),
                    type="openai-compatible",
                    gender="unknown",
                )
            )

        return voices

    # [ELIMINATO v118.4] get_available_voices duplicato rimosso per permettere il funzionamento dello scanner dinamico.

    def _resolve_voice(self, voice: str) -> str:
        """Resolve voice name to VibeVoice voice"""
        # Check if it's an OpenAI voice name
        if voice.lower() in OPENAI_TO_VIBEVOICE_MAP:
            voice = OPENAI_TO_VIBEVOICE_MAP[voice.lower()]

        # Check if voice exists
        if voice not in self.voice_presets:
            available = [v for v in self.voice_presets.keys() if "-" not in v]
            print(t("vibevoice.log.voice_not_found", voice=voice, available=available))
            voice = "Carter"

        return voice

    def _get_voice_prompt(self, voice: str) -> Any:
        """Load or get cached voice prompt"""
        if voice not in self._voice_cache:
            voice_path = self.voice_presets[voice]
            print(t("vibevoice.log.loading_voice_prompt", path=voice_path))
            self._voice_cache[voice] = torch.load(
                voice_path, map_location=self._torch_device, weights_only=False
            )
        return self._voice_cache[voice]

    def generate_speech(
        self, text: str, voice: str, cfg_scale: float = 1.5
    ) -> np.ndarray:
        """Generate speech from text

        Args:
            text: Text to synthesize
            voice: Voice name
            cfg_scale: CFG scale for generation

        Returns:
            Audio samples as numpy array (float32, 24kHz)
        """
        if not self.model or not self.processor:
            raise RuntimeError(t("vibevoice.err_model_not_loaded"))

        voice = self._resolve_voice(voice)
        prefilled_outputs = self._get_voice_prompt(voice)

        # Clean text
        text = text.strip().replace("'", "'")

        # Prepare inputs
        inputs = self.processor.process_input_with_cached_prompt(
            text=text,
            cached_prompt=prefilled_outputs,
            padding=True,
            return_tensors="pt",
            return_attention_mask=True,
        )

        # Move to device
        for k, v in inputs.items():
            if torch.is_tensor(v):
                inputs[k] = v.to(self._torch_device)

        print(t("vibevoice.log.generating_speech", chars=len(text), voice=voice))
        start_time = time.time()

        # Generate
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=None,
            cfg_scale=cfg_scale,
            tokenizer=self.processor.tokenizer,
            generation_config={"do_sample": False},
            verbose=False,
            all_prefilled_outputs=copy.deepcopy(prefilled_outputs),
        )

        elapsed = time.time() - start_time

        # Extract audio
        if outputs.speech_outputs and outputs.speech_outputs[0] is not None:
            audio = outputs.speech_outputs[0]
            if torch.is_tensor(audio):
                audio = audio.detach().cpu().to(torch.float32).numpy()
            else:
                audio = np.asarray(audio, dtype=np.float32)

            if audio.ndim > 1:
                audio = audio.reshape(-1)

            # Normalize
            peak = np.max(np.abs(audio))
            if peak > 1.0:
                audio = audio / peak

            duration = len(audio) / SAMPLE_RATE
            rtf = elapsed / duration if duration > 0 else float("inf")
            print(
                t(
                    "vibevoice.log.generated_audio",
                    duration=f"{duration:.2f}",
                    elapsed=f"{elapsed:.2f}",
                    rtf=f"{rtf:.2f}",
                )
            )

            return audio
        else:
            raise RuntimeError(t("vibevoice.err_no_audio_generated"))


# ------------------------------------------------------------------------------
# Audio Format Conversion
# ------------------------------------------------------------------------------


def convert_audio(
    audio: np.ndarray, format: str, sample_rate: int = SAMPLE_RATE
) -> bytes:
    """Convert audio to specified format using ffmpeg

    Args:
        audio: Audio samples (float32, mono)
        format: Output format (mp3, wav, opus, flac, aac, pcm)
        sample_rate: Sample rate

    Returns:
        Audio bytes in specified format
    """
    format = format.lower()

    if format == "pcm":
        # Raw PCM16 little-endian
        pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
        return pcm.tobytes()

    if format == "wav":
        # Use scipy for WAV
        buffer = io.BytesIO()
        wavfile.write(
            buffer, sample_rate, (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
        )
        return buffer.getvalue()

    # Use ffmpeg for other formats
    # Prepare input WAV
    wav_buffer = io.BytesIO()
    wavfile.write(
        wav_buffer, sample_rate, (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    )
    wav_data = wav_buffer.getvalue()

    # ffmpeg format mappings
    format_args = {
        "mp3": ["-f", "mp3", "-codec:a", "libmp3lame", "-q:a", "2"],
        "opus": ["-f", "opus", "-codec:a", "libopus"],
        "flac": ["-f", "flac", "-codec:a", "flac"],
        "aac": ["-f", "adts", "-codec:a", "aac"],
    }

    if format not in format_args:
        raise ValueError(t("vibevoice.err_unsupported_format", format=format))

    # Run ffmpeg
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "wav",
        "-i",
        "pipe:0",
        *format_args[format],
        "pipe:1",
    ]

    try:
        result = subprocess.run(cmd, input=wav_data, capture_output=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(t("vibevoice.log.ffmpeg_failed", error=e.stderr.decode()))
        raise RuntimeError(t("vibevoice.err_audio_conversion", error=e))
    except FileNotFoundError:
        raise RuntimeError(t("vibevoice.err_ffmpeg_not_found"))


def get_content_type(format: str) -> str:
    """Get MIME content type for audio format"""
    types = {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "opus": "audio/opus",
        "flac": "audio/flac",
        "aac": "audio/aac",
        "pcm": "audio/pcm",
    }
    return types.get(format.lower(), "application/octet-stream")


# --- [NUOVO v118.5] RITO DI EPURAZIONE PORTA ---
def kill_process_on_port(port: int):
    """Libera la porta specificata uccidendo eventuali processi orfani."""
    try:
        if os.name == "nt":
            # Scansione socket attivi su Windows
            result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
            lines = result.stdout.splitlines()
            for line in lines:
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    pid = parts[-1]
                    if pid != "0":
                        # Esecuzione chirurgica della terminazione
                        subprocess.run(
                            ["taskkill", "/F", "/PID", pid], capture_output=True
                        )
        else:
            # Fallback per sistemi Unix-like
            result = subprocess.run(
                ["lsof", "-t", f"-i:{port}"], capture_output=True, text=True
            )
            pids = result.stdout.strip().split()
            for pid in pids:
                if pid:
                    subprocess.run(["kill", "-9", pid], capture_output=True)
    except Exception:
        pass  # Silenzio in caso di errore per non bloccare lo startup


# ------------------------------------------------------------------------------
# FastAPI Application
# ------------------------------------------------------------------------------

# Global service instance
tts_service: Optional[VibeVoiceTTSService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup and shutdown"""
    global tts_service

    # --- Startup ---
    model_path = os.environ.get("VIBEVOICE_MODEL_PATH", DEFAULT_MODEL_PATH)
    device = os.environ.get(
        "VIBEVOICE_DEVICE", "cuda" if torch.cuda.is_available() else "cpu"
    )

    tts_service = VibeVoiceTTSService(model_path=model_path, device=device)
    try:
        tts_service.load()
    except Exception as e:
        print(t("vibevoice.log.model_loading_failed", error=e))
        traceback.print_exc()

    yield

    # --- Shutdown ---
    if tts_service and tts_service.model:
        del tts_service.model
        torch.cuda.empty_cache()


app = FastAPI(
    title="VibeVoice TTS Server",
    description="OpenAI-compatible TTS API powered by VibeVoice-Realtime-0.5B",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="ok",
        service="vibevoice-realtime-openai-api",
        model_loaded=tts_service is not None and tts_service.model is not None,
        device=tts_service.device if tts_service else "unknown",
        features={
            "streaming": False,
            "formats": SUPPORTED_FORMATS,
            "sample_rate": SAMPLE_RATE,
        },
    )


@app.get("/v1/audio/voices", response_model=VoicesResponse)
async def list_voices():
    """List available voices (OpenAI-compatible)"""
    if not tts_service:
        raise HTTPException(
            status_code=503, detail=t("vibevoice.err_service_not_ready")
        )

    return VoicesResponse(voices=tts_service.get_available_voices())


@app.get("/v1/audio/models")
async def list_models():
    """List available TTS models (OpenAI-compatible)"""
    return {
        "object": "list",
        "data": [
            {
                "id": "tts-1",
                "object": "model",
                "created": 1699000000,
                "owned_by": "vibevoice",
                "name": "VibeVoice-Realtime-0.5B",
            },
            {
                "id": "tts-1-hd",
                "object": "model",
                "created": 1699000000,
                "owned_by": "vibevoice",
                "name": "VibeVoice-Realtime-0.5B",
            },
        ],
    }


@app.post("/v1/audio/speech")
async def create_speech(request: TTSRequest):
    """Generate speech from text (OpenAI-compatible)"""
    if not tts_service:
        raise HTTPException(
            status_code=503, detail=t("vibevoice.err_service_not_ready")
        )

    # Validate input
    if not request.input or not request.input.strip():
        raise HTTPException(status_code=400, detail=t("vibevoice.err_input_required"))

    if len(request.input) > 4096:
        raise HTTPException(status_code=400, detail=t("vibevoice.err_input_too_long"))

    if request.response_format.lower() not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=t("vibevoice.err_unsupported_format_api", formats=SUPPORTED_FORMATS),
        )

    try:
        # Generate speech
        audio = tts_service.generate_speech(
            text=request.input,
            voice=request.voice,
            cfg_scale=CFG_SCALE,
        )

        # Convert to requested format
        audio_bytes = convert_audio(audio, request.response_format)
        content_type = get_content_type(request.response_format)

        return Response(
            content=audio_bytes,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=speech.{request.response_format}"
            },
        )

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="VibeVoice OpenAI-Compatible TTS Server"
    )
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8880, help="Port to bind")
    parser.add_argument(
        "--model-path", type=str, default=DEFAULT_MODEL_PATH, help="Model path"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda",
        choices=["cuda", "cpu", "mps"],
        help="Device",
    )
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    # Set environment variables for startup
    os.environ["VIBEVOICE_MODEL_PATH"] = args.model_path
    os.environ["VIBEVOICE_DEVICE"] = args.device

    print(t("vibevoice.startup_msg", host=args.host, port=args.port))
    print(t("vibevoice.endpoint_msg", host=args.host, port=args.port))

    uvicorn.run(
        "vibevoice_realtime_openai_api:app" if args.reload else app,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    # To suppress warnings, run with: python -W ignore vibevoice_realtime_openai_api.py
    main()
