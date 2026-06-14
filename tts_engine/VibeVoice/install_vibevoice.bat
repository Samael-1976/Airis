@echo off
cls
echo =================================================================
echo ANIVERSE-PROJECT: RITO DI ASSIMILAZIONE VIBEVOICE v1.0
echo                  (Installazione Isolata del Motore Emotivo)
echo =================================================================
echo.
echo Questo script creera' un ambiente virtuale dedicato per VibeVoice
echo all'interno di tts_engine/vibevoice/ per garantire la stabilita'
echo del Santuario principale.
echo.
pause

:: Naviga nella cartella del connettore
cd /d "%~dp0"

:: 1. Creazione Santuario Locale (venv)
echo [SAGGIO] Creazione dell'ambiente virtuale isolato...
if not exist venv\ (
    python -m venv venv
    echo         ... Santuario creato.
) else (
    echo         ... Santuario gia' esistente.
)

:: 2. Verifica Prerequisiti (Git)
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRORE] Git non trovato! E' necessario per scaricare il motore VibeVoice.
    echo          Scaricalo da: https://git-scm.com/download/win
    pause
    exit /b
)

:: 3. Attivazione e Aggiornamento
echo [SAGGIO] Preparazione degli strumenti di forgiatura...
call venv\Scripts\activate
python -m pip install --upgrade pip

:: 4. Installazione Dipendenze (Dal requirements allineato)
echo [SAGGIO] Installazione delle pergamene di VibeVoice...
echo         (Questo processo scarichera' circa 2GB di dati, attendi...)

:: Installazione speculare al core di Yana (CUDA 12.8 Nightly)
python -m pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128

:: Installazione del resto delle dipendenze dal file dedicato
python -m pip install -r requirements-vibevoice-openai-api.txt

echo.
echo =================================================================
echo [SUCCESSO] VibeVoice e' stato assimilato correttamente!
echo =================================================================
echo.
echo Per avviare il server API di VibeVoice, usa il comando:
echo venv\Scripts\python.exe vibevoice_realtime_openai_api.py --port 8880
echo.
echo Ricorda di attivare il motore nelle impostazioni di Yana (Care OS).
echo.
pause