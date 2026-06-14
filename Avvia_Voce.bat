@echo off
REM Carica la lingua e le traduzioni
set /p LANG=<"%~dp0lang.cfg"
if not defined LANG set LANG=it
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0Translations\System_env\%LANG%\system-%LANG%.env") do set "%%a=%%~b"

TITLE %TITLE_VOICE%

REM Leggi la scelta del motore vocale
set TTS_CHOICE=1
if exist "%~dp0tts_choice.cfg" (
    set /p TTS_CHOICE=<"%~dp0tts_choice.cfg"
)
REM Rimuovi eventuali spazi vuoti fantasma
set TTS_CHOICE=%TTS_CHOICE: =%

echo %MSG_VOICE_ACTIVATE%
echo %MSG_VOICE_START_API%

if "%TTS_CHOICE%"=="2" (
    REM Avvio VibeVoice (OpenAI API Compatible)
    cd /d "%~dp0tts_engine\VibeVoice"
    "%~dp0tts_engine\VibeVoice\venv\Scripts\python.exe" vibevoice_realtime_openai_api.py --port 8880
) else (
    REM Avvio Kokoro TTS
    cd /d "%~dp0tts_engine\kokoro"
    "%~dp0tts_engine\kokoro\python\python.exe" -m scripts.gradio_v5.tts_core --listen localhost --port 5002
)