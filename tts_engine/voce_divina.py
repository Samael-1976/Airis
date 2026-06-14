# --- Il Ponte Vocale (v1.3 - GPU Stability & Tag Safety) ---

import os
import sys
import argparse
import soundfile as sf
from pathlib import Path

# --- [FIX CRITICO] INIEZIONE PATH PER TRADUTTORE ---
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.translator import t

# --- GESTIONE CRITICA DEI PERCORSI v2.0 ---
try:
    SCRIPT_DIR = Path(__file__).parent.resolve()
    PROJECT_ROOT = SCRIPT_DIR.parent

    # 0. Aggiungi src al path per permettere l'importazione del traduttore
    SRC_DIR = PROJECT_ROOT / "src"
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))

    # 1. Trova la radice del progetto Kokoro, che è la cartella genitore di "python", "model", ecc.
    #    Lo script si trova in "tts_engine", quindi la radice di Kokoro è "tts_engine/kokoro".
    KOKORO_ROOT = SCRIPT_DIR / "kokoro"
    if not KOKORO_ROOT.exists():
        raise FileNotFoundError(t("voce_divina.err_root_not_found", path=KOKORO_ROOT))

    # 2. Aggiungi il percorso corretto delle librerie Python di Kokoro
    KOKORO_LIB_PATH = KOKORO_ROOT / "python" / "Lib" / "site-packages"
    if not KOKORO_LIB_PATH.exists():
        raise FileNotFoundError(
            t("voce_divina.err_lib_not_found", path=KOKORO_LIB_PATH)
        )
    sys.path.insert(0, str(KOKORO_LIB_PATH))

    # 3. Imposta la home di Hugging Face per usare la cache locale di Kokoro (fondamentale)
    os.environ["HF_HOME"] = str(KOKORO_ROOT / "hub")

    # --- IMPORTAZIONI CRITICHE ---
    import torch
    import traceback
    import re  # [NUOVO] Per pulizia tag di emergenza
    from kokoro.pipeline import KPipeline
    from kokoro.model import KModel

except Exception as e:
    print(t("voce_divina.err_critical_init", error=e), file=sys.stderr)
    sys.exit(1)


def generate_speech(text: str, voice_pt: str, lang_code: str, output_path: str):
    """
    Genera audio con Kokoro (Standard).
    """
    try:
        # --- PULIZIA TAG DI EMERGENZA (Safety Net) ---
        # Se il backend invia per errore dei tag [INTENT] o [AZIONE], li rimuoviamo qui per non farli leggere
        text = re.sub(r"\[(INTENT|AZIONE|USA_STRUMENTO|SISTEMA).*?\]", "", text).strip()

        if not text:
            print(t("voce_divina.warn_empty_text"), file=sys.stderr)
            return

        # ---[LA CORREZIONE FONDAMENTALE] ---
        config_path = KOKORO_ROOT / "model" / "config.json"
        model_path = KOKORO_ROOT / "model" / "kokoro-v1_0.pth"
        voice_file_path = KOKORO_ROOT / "model" / "audio" / voice_pt

        if not config_path.exists():
            raise FileNotFoundError(
                t("voce_divina.err_config_not_found", path=config_path)
            )
        if not model_path.exists():
            raise FileNotFoundError(
                t("voce_divina.err_model_not_found", path=model_path)
            )
        if not voice_file_path.exists():
            # --- [FIX CRITICO] PARACADUTE ANTI-CRASH ---
            # Invece di crashare, logghiamo l'errore su stderr e usiamo una voce di default sicura
            print(
                t(
                    "voce_divina.err_voice_not_found",
                    voice=voice_pt,
                    path=voice_file_path.parent,
                ),
                file=sys.stderr
            )
            fallback_voice = "if_sara.pt" if lang_code == "i" else "af_bella.pt"
            voice_file_path = KOKORO_ROOT / "model" / "audio" / fallback_voice
            print(t("voce_divina.log_fallback_voice", voice=fallback_voice), file=sys.stderr)
            
            if not voice_file_path.exists():
                raise FileNotFoundError(f"ERRORE FATALE: Anche la voce di fallback {fallback_voice} è mancante!")

        # --- RILEVAMENTO HARDWARE (GPU ACCELERATION) ---
        device = "cuda" if torch.cuda.is_available() else "cpu"
        # Usiamo stderr per i log tecnici per non sporcare l'output del percorso file
        print(
            t("voce_divina.log_hardware", device=device.upper(), text=text[:30]),
            file=sys.stderr,
        )

        # Inizializziamo il modello
        model = KModel(config=str(config_path), model=str(model_path))

        # Spostiamo il modello sul device corretto
        model.to(device).eval()

        # --- FIX v1.3: Rimozione 'device' dal costruttore KPipeline ---
        # La pipeline erediterà il device dal modello caricato.
        pipeline = KPipeline(lang_code=lang_code, model=model)

        # Speed fisso a 1.0
        generator = pipeline(text, voice=str(voice_file_path), speed=1.0)
        _, _, audio = next(generator)

        if audio is None or len(audio) == 0:
            raise ValueError(t("voce_divina.err_empty_output"))

        # Salvataggio standard
        sf.write(output_path, audio, 24000)

        # Stampiamo solo il percorso del file su stdout per il Braccio Divino
        print(output_path, end="")

    except Exception as e:
        print(t("voce_divina.err_generation", error=e), file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=t("voce_divina.cli_desc"))
    parser.add_argument(
        "--text", type=str, required=True, help=t("voce_divina.cli_help_text")
    )
    parser.add_argument(
        "--voice", type=str, required=True, help=t("voce_divina.cli_help_voice")
    )
    parser.add_argument(
        "--lang", type=str, required=True, help=t("voce_divina.cli_help_lang")
    )
    parser.add_argument(
        "--output-path", type=str, required=True, help=t("voce_divina.cli_help_output")
    )

    args = parser.parse_args()

    generate_speech(
        text=args.text,
        voice_pt=args.voice,
        lang_code=args.lang,
        output_path=args.output_path,
    )
