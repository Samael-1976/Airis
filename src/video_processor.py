# src/video_processor.py
# [DEV] Il Cronista Visivo (v1.0)
# Modulo per l'estrazione di frame sequenziali da video per l'analisi temporale di Gemma 3.

import subprocess
import os
import cv2
import numpy as np
from pathlib import Path
from typing import List, Optional
from utils.translator import t

# Percorso FFmpeg (lo stesso usato da Kokoro)
APP_ROOT = Path(__file__).parent.parent.resolve()
FFMPEG_EXE = APP_ROOT / "tts_engine" / "kokoro" / "ffmpeg.exe"

if not FFMPEG_EXE.exists():
    # Fallback su comando di sistema se l'exe locale non c'è
    FFMPEG_EXE = "ffmpeg"


class VideoProcessor:
    def __init__(self, temp_dir: Path = APP_ROOT / "temp_images" / "video_frames"):
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def extract_frames(
        self, video_path: str, fps: int = 1, max_frames: int = 10
    ) -> List[np.ndarray]:
        """
        Estrae frame da un video a un dato framerate.
        Restituisce una lista di numpy array (immagini) pronti per il cervello.
        """
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(
                t("avatar_server.log.video_not_found", path=video_path)
            )

        # Pulizia cartella temporanea frame precedenti
        for f in self.temp_dir.glob("*.jpg"):
            try:
                os.remove(f)
            except:
                pass

        output_pattern = self.temp_dir / "frame_%03d.jpg"

        # Comando FFmpeg per estrarre frame
        # -i input -vf fps=1 (1 frame al secondo) output
        cmd = [
            str(FFMPEG_EXE),
            "-y",  # Sovrascrivi
            "-i",
            str(path),
            "-vf",
            f"fps={fps}",
            str(output_pattern),
        ]

        try:
            # Esegui ffmpeg (silenzioso)
            subprocess.run(
                cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError as e:
            print(t("avatar_server.log.video_processor_error", error=str(e)))
            return []

        # Carica i frame generati
        frames = []
        frame_files = sorted(list(self.temp_dir.glob("frame_*.jpg")))

        # Se ci sono troppi frame, campioniamo uniformemente per stare nel limite
        if len(frame_files) > max_frames:
            indices = np.linspace(0, len(frame_files) - 1, max_frames, dtype=int)
            frame_files = [frame_files[i] for i in indices]

        for f_path in frame_files:
            img = cv2.imread(str(f_path))
            if img is not None:
                frames.append(img)

        return frames

    def buffer_to_frames(
        self, frame_buffer: List[np.ndarray], max_frames: int = 10
    ) -> List[np.ndarray]:
        """
        Converte un buffer di frame (es. dalla webcam) in una sequenza temporale.
        Se il buffer è troppo grande, campiona.
        """
        if not frame_buffer:
            return []

        if len(frame_buffer) > max_frames:
            indices = np.linspace(0, len(frame_buffer) - 1, max_frames, dtype=int)
            return [frame_buffer[i] for i in indices]

        return list(frame_buffer)
