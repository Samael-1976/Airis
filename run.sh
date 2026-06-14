#!/bin/bash

# =================================================================
# AIRIS-PROJECT: RITO DI RISVEGLIO UNIFICATO (LINUX / MACOS)
# =================================================================

cd "$(dirname "$0")" || exit 1

# --- [1] SELEZIONE LINGUA ---
if [ ! -f "lang.cfg" ]; then
    clear
    echo "================================================="
    echo "  AIRIS-PROJECT: LANGUAGE SELECTION"
    echo "================================================="
    echo ""
    
    LANG_DIRS=(translations/System_env/*)
    COUNT=0
    declare -A LANG_MAP
    
    for DIR in "${LANG_DIRS[@]}"; do
        if [ -d "$DIR" ]; then
            COUNT=$((COUNT + 1))
            LANG_NAME=$(basename "$DIR")
            LANG_MAP[$COUNT]=$LANG_NAME
            echo "  [$COUNT] - $LANG_NAME"
        fi
    done
    
    echo ""
    read -p "> Seleziona la lingua (1-$COUNT): " LANG_CHOICE
    
    if [[ -z "$LANG_CHOICE" ]] || [[ "$LANG_CHOICE" -lt 1 ]] || [[ "$LANG_CHOICE" -gt "$COUNT" ]]; then
        LANG_CHOICE=1
    fi
    
    SELECTED_LANG=${LANG_MAP[$LANG_CHOICE]}
    echo "$SELECTED_LANG" > "lang.cfg"
fi

# --- [2] CARICAMENTO TRADUZIONI ---
LANG_CODE=$(cat "lang.cfg" 2>/dev/null | tr -d '[:space:]')
[[ -z "$LANG_CODE" ]] && LANG_CODE="en"

ENV_FILE="translations/System_env/$LANG_CODE/system-$LANG_CODE.env"

if [ -f "$ENV_FILE" ]; then
    echo "Caricamento traduzioni: $ENV_FILE"
    while IFS= read -r line || [ -n "$line" ]; do
        line="${line%%#*}"
        line="${line#"${line%%[![:space:]]*}"}"
        line="${line%"${line##*[![:space:]]}"}"
        [[ -z "$line" ]] && continue
        
        if [[ $line =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
            key="${BASH_REMATCH[1]}"
            value="${BASH_REMATCH[2]//\"}"
            value="${value//\'}"
            value="${value//$'\r'/}"
            export "$key=$value"
        fi
    done < "$ENV_FILE"
fi

# Debug (commenta dopo aver verificato)
echo "=== DEBUG ==="
echo "LANG_CODE = $LANG_CODE"
echo "TITLE_RUN = ${TITLE_RUN:-NON_TROVATO}"
echo "MSG_RUN_START = ${MSG_RUN_START:-NON_TROVATO}"
echo "=============="

echo -ne "\033]0;${TITLE_RUN:-AIRIS-PROJECT}\007"

# --- [3] PULIZIA ---
echo "${MSG_RUN_CLEAN:-Pulizia processi...}"
pkill -f "python3.*chat.py" > /dev/null 2>&1
pkill -f "python3.*avatar_server.py" > /dev/null 2>&1
pkill -f "vibevoice" > /dev/null 2>&1
pkill -f "tts_core" > /dev/null 2>&1

# --- [4] FRONTEND ---
echo "${MSG_RUN_FRONTEND:-Frontend...}"
cd frontend_mobile || exit 1
npm install --silent --legacy-peer-deps
npm run build --silent
cd ..

# --- [5] VENV PYTHON ---
# Rilevamento Cross-OS: Se esiste venv/Scripts, è un venv di Windows copiato su Linux. Va distrutto.
if [ -d "venv/Scripts" ]; then
    echo "[SISTEMA] Rilevato venv di Windows. Purificazione in corso per Linux..."
    rm -rf venv
fi

if [ ! -f "venv/bin/python3" ] && [ ! -f "venv/bin/python" ]; then
    echo "[SISTEMA] Creazione venv Unix locale..."
    rm -rf venv
    python3 -m venv venv || { echo "Python3 non trovato!"; exit 1; }

    # Attivazione rigorosa per l'installazione (Isolamento)
    export VIRTUAL_ENV="$(pwd)/venv"
    export PATH="$VIRTUAL_ENV/bin:$PATH"

    pip install --upgrade pip --no-cache-dir --quiet

    cat << 'EOF' > temp_reqs.txt
--index-url https://download.pytorch.org/whl/nightly/cu128
--pre
torch
torchvision
torchaudio
--index-url https://pypi.org/simple
fastapi==0.111.0
open-interpreter==0.4.3
starlette==0.37.2
typer==0.12.5
urllib3==2.2.3
protobuf==4.25.5
selenium==4.27.0
fastapi-cli==0.0.4
opentelemetry-api==1.26.0
opentelemetry-proto==1.26.0
opentelemetry-sdk==1.26.0
opentelemetry-exporter-otlp==1.26.0
opentelemetry-exporter-otlp-proto-grpc==1.26.0
opentelemetry-exporter-otlp-proto-common==1.26.0
litellm
wheel
pyyaml
ics
requests
configparser
plyer
chromadb
sentence-transformers
pycryptodome
beautifulsoup4
opencv-python
face-recognition
pyaudio
SpeechRecognition
numpy
ddgs
h2
httpcore
wikipedia
Pillow
pywin32; sys_platform == 'win32'
prompt_toolkit
soundfile
PySoundFile
python-multipart
pipdeptree
einops
hf_xet
pycaw; sys_platform == 'win32'
bcrypt
pyjwt
uvicorn[standard]
pyautogui
easyocr
playwright
psutil
pywinauto; sys_platform == 'win32'
pypdf
python-docx
google-api-python-client
google-auth-httplib2
google-auth-oauthlib
msal
requests-oauthlib
discord.py
python-telegram-bot
twilio
tweepy
praw
slack_sdk
py-trello
jira
asana
notion-client
PyGithub
python-gitlab
feedparser
arxiv
pyngrok
faster-whisper
mediapipe
schedule
mcp
EOF

    pip install -r temp_reqs.txt --no-cache-dir --quiet
    playwright install chromium --quiet
    rm -f temp_reqs.txt
fi

# --- ATTIVAZIONE RIGOROSA (ISOLAMENTO ASSOLUTO) ---
export VIRTUAL_ENV="$(pwd)/venv"
export PATH="$VIRTUAL_ENV/bin:$PATH"
PYTHON_EXE="venv/bin/python3" # Ripristinato il percorso relativo corretto per i comandi successivi

# Fix paths
./$PYTHON_EXE src/fix_intent_paths.py 2>/dev/null || true
./$PYTHON_EXE src/verify_and_sync_durations.py 2>/dev/null || true

# --- [6] TTS ---
clear
echo ""
echo "  ============================================================"
echo "             ${MSG_RUN_TTS_TITLE:-Scelta Motore Vocale}"
echo "  ============================================================"
echo "    [1] ${MSG_RUN_TTS_OPT1:-Kokoro}"
echo "    [2] ${MSG_RUN_TTS_OPT2:-VibeVoice}"
echo ""
read -p "${MSG_RUN_TTS_PROMPT:-Scegli (1-2): } " TTS_CHOICE
[[ "$TTS_CHOICE" != "2" ]] && TTS_CHOICE="1"
echo "$TTS_CHOICE" > "tts_choice.cfg"

# --- [7] HARDWARE (VERSIONE ROBUSTA) ---
clear
echo ""
echo "  ============================================================"
echo "             ${MSG_RUN_HW_TITLE:-Scelta Backend Hardware}"
echo "  ============================================================"
echo ""

OS_NAME=$(uname -s)
if [ "$OS_NAME" = "Darwin" ]; then
    HW_DIR="macOS"
else
    HW_DIR="Linux"
fi

echo "DEBUG: Cerco in → bin/$HW_DIR/"
echo "DEBUG: Contenuto:"
ls -1 "bin/$HW_DIR/" 2>/dev/null || echo "  Cartella vuota o inesistente"

COUNT=0
declare -A HW_MAP
echo ""
echo ""

while IFS= read -r -d '' DIR; do
    if [ -d "$DIR" ]; then
        COUNT=$((COUNT + 1))
        DIR_NAME=$(basename "$DIR")
        HW_MAP[$COUNT]="$DIR_NAME"
        echo "    [$COUNT] - $DIR_NAME"
    fi
done < <(find "bin/$HW_DIR" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null)

echo ""
echo "  ============================================================"

if [ $COUNT -eq 0 ]; then
    echo "ERRORE: Nessuna cartella trovata in bin/$HW_DIR"
    exit 1
fi

read -p "${MSG_RUN_HW_PROMPT:-Seleziona (1-$COUNT): } " HW_CHOICE
[[ -z "$HW_CHOICE" || "$HW_CHOICE" -lt 1 || "$HW_CHOICE" -gt "$COUNT" ]] && HW_CHOICE=1

SELECTED_BACKEND="${HW_MAP[$HW_CHOICE]}"
export AIRIS_BACKEND="$HW_DIR/$SELECTED_BACKEND"
echo "→ Backend selezionato: $SELECTED_BACKEND"

# --- [8] BACKGROUND PROCESSES ---
echo ""
echo "${MSG_SOUL_BRIDGE:-Avvio Anima...}"

nohup ./$PYTHON_EXE src/avatar_server.py \
    --tts "$TTS_CHOICE" \
    --parallel 1 \
    --kv-unified \
    --reasoning-budget 4096 \
    --ctx-shift-strategy compact > logs/avatar_server.log 2>&1 &
AVATAR_PID=$!

echo "${MSG_VOICE_ACTIVATE:-Avvio voce...}"
if [ "$TTS_CHOICE" = "2" ]; then
    cd tts_engine/VibeVoice || exit 1
    VV_PYTHON=$( [ -f "venv/bin/python3" ] && echo "venv/bin/python3" || echo "venv/bin/python" )
    nohup ./$VV_PYTHON vibevoice_realtime_openai_api.py --port 8880 > ../../logs/vibevoice.log 2>&1 &
    VOICE_PID=$!
    cd ../..
else
    cd tts_engine/kokoro || exit 1
    nohup ../../$PYTHON_EXE -m scripts.gradio_v5.tts_core --listen localhost --port 5002 > ../../logs/kokoro.log 2>&1 &
    VOICE_PID=$!
    cd ../..
fi

trap 'echo -e "\n${MSG_SOUL_DISSOLVE:-Dissolvenza Anima...}"; kill $AVATAR_PID $VOICE_PID 2>/dev/null; exit' INT TERM EXIT

echo "${MSG_SOUL_WAIT:-Attesa...}"
sleep 5

# --- [9] CHAT ---
echo "${MSG_SOUL_INVOKE:-Evocazione Anima...}"
./$PYTHON_EXE chat.py
