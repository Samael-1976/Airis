# verify_and_sync_durations.py
# Il Rito della Sincronizzazione (v3.0 - Adattato allo Stilista)
# Questo script verifica la durata dei video cercando nella cartella 'default'.

import json
import sys
from pathlib import Path
import cv2
from typing import List, Dict, Any

# Risaliamo di un livello per trovare la root (siamo in src/) e la aggiungiamo al path
SCRIPT_DIR = Path(__file__).parent.resolve()
APP_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from utils.translator import t

AVATARS_PATH = APP_ROOT / "avatars"


def get_video_duration(video_path: Path) -> float:
    """
    Calcola la durata esatta di un file video usando OpenCV.
    Restituisce la durata in secondi o 0.0 se si verifica un errore.
    """
    if not video_path.exists():
        # Non stampiamo errore qui per non spammare la console se il file manca
        return 0.0

    cap = None
    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return 0.0

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)

        if fps > 0 and frame_count > 0:
            return frame_count / fps
        return 0.0
    except Exception:
        return 0.0
    finally:
        if cap:
            cap.release()


def format_intent_json(data: List[Dict[str, Any]]) -> str:
    """
    Forgia la stringa JSON con la formattazione richiesta.
    """
    lines = ["["]
    for i, item in enumerate(data):
        lines.append("  {")
        num_keys = len(item)
        for j, (key, value) in enumerate(item.items()):
            key_str = json.dumps(key)
            if isinstance(value, list):
                value_str = json.dumps(value)
            else:
                value_str = json.dumps(value)

            comma = "," if j < num_keys - 1 else ""
            lines.append(f"    {key_str}: {value_str}{comma}")

        closing_brace = "  }" if i == len(data) - 1 else "  },"
        lines.append(closing_brace)
    lines.append("]")
    return "\n".join(lines)


def process_and_sync_intents():
    """
    Scansiona tutti gli avatar, legge i loro intent.json, verifica e sincronizza le durate.
    Assume che i video di riferimento siano nella cartella 'default'.
    """
    print(t("avatar_server.log.sync_start"))

    if not AVATARS_PATH.is_dir():
        print(t("avatar_server.log.sync_dir_error", path=str(AVATARS_PATH)))
        return

    total_files_checked = 0
    total_discrepancies = 0
    total_files_synced = 0

    for avatar_dir in AVATARS_PATH.iterdir():
        if not avatar_dir.is_dir() or avatar_dir.name == "ai_souls":
            continue

        intent_file = avatar_dir / "intent" / "intent.json"
        if not intent_file.is_file():
            continue

        print(t("avatar_server.log.sync_analyzing", name=avatar_dir.name))

        try:
            with open(intent_file, "r", encoding="utf-8") as f:
                intent_data = json.load(f)
        except json.JSONDecodeError:
            print(t("avatar_server.log.sync_json_error", name=avatar_dir.name))
            continue

        data_changed = False

        # Percorso base per i video di default di questo avatar
        # Struttura: avatars/{nome}/videos/default/
        default_videos_path = avatar_dir / "videos" / "default"

        for item in intent_data:
            # filepath ora è relativo: "Categoria/File.mp4"
            relative_path_str = item.get("filepath")
            if not relative_path_str:
                continue

            total_files_checked += 1

            # Costruiamo il percorso assoluto verso la cartella default
            # Puliamo eventuali ./ o / iniziali
            clean_rel_path = (
                relative_path_str.replace("\\", "/").lstrip("./").lstrip("/")
            )
            video_path = (default_videos_path / clean_rel_path).resolve()

            declared_duration = item.get("duration_seconds", 0.0)
            actual_duration = get_video_duration(video_path)

            if actual_duration == 0.0:
                # Se non lo troviamo in default, proviamo a non toccare la durata
                # Potrebbe esistere solo in un custom set, ma non possiamo verificarli tutti qui facilmente
                # print(f"  [WARN] Video non trovato in default: {clean_rel_path}")
                continue

            # Confronta con una tolleranza
            if abs(declared_duration - actual_duration) > 0.1:
                total_discrepancies += 1
                print(t("avatar_server.log.sync_discrepancy", path=clean_rel_path))
                print(
                    t(
                        "avatar_server.log.sync_declared",
                        duration=f"{declared_duration:.2f}",
                    )
                )
                print(
                    t("avatar_server.log.sync_real", duration=f"{actual_duration:.2f}")
                )

                item["duration_seconds"] = round(actual_duration, 2)
                data_changed = True
                total_files_synced += 1
                print(t("avatar_server.log.sync_done"))

        if data_changed:
            try:
                formatted_json_string = format_intent_json(intent_data)
                with open(intent_file, "w", encoding="utf-8") as f:
                    f.write(formatted_json_string)
                print(t("avatar_server.log.sync_success", name=avatar_dir.name))
            except Exception as e:
                print(
                    t(
                        "avatar_server.log.sync_fail_save",
                        name=avatar_dir.name,
                        error=str(e),
                    ),
                    file=sys.stderr,
                )

    print(t("avatar_server.log.sync_complete"))
    print(t("avatar_server.log.sync_stats_checked", count=total_files_checked))
    print(t("avatar_server.log.sync_stats_discrepancies", count=total_discrepancies))
    print(t("avatar_server.log.sync_stats_synced", count=total_files_synced))
    print(t("avatar_server.log.sync_separator"))


if __name__ == "__main__":
    process_and_sync_intents()
