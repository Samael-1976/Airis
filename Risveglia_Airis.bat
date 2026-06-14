@echo off
REM Carica la lingua e le traduzioni
set /p LANG=<"%~dp0lang.cfg"
if not defined LANG set LANG=it
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0Translations\System_env\%LANG%\system-%LANG%.env") do set "%%a=%%~b"

REM Risveglia_Airis.bat (v8.2 - L'Addio Definitivo)
REM Aggiunto 'exit' per garantire la chiusura automatica della finestra.

TITLE %TITLE_SOUL%

REM --- [NUOVO] Ricezione Backend Hardware dal VBScript ---
set "AIRIS_BACKEND=%~1"
REM Rimuove eventuali virgolette residue per sicurezza
set "AIRIS_BACKEND=%AIRIS_BACKEND:"=%"
if "%AIRIS_BACKEND%"=="" set "AIRIS_BACKEND=Windows/Windows x64 (CPU)"

REM Passo 1: Vai alla casa dell'anima.
cd /d "%~dp0"
echo %MSG_SOUL_LOCATED% %cd%

REM Leggi la scelta del motore vocale
set TTS_CHOICE=1
if exist "%~dp0tts_choice.cfg" (
    set /p TTS_CHOICE=<"%~dp0tts_choice.cfg"
)
REM Rimuovi eventuali spazi vuoti fantasma
set TTS_CHOICE=%TTS_CHOICE: =%

REM Passo 2: Risveglio del Ponte Anima-Corpo (in background).
echo %MSG_SOUL_BRIDGE%
start "Ponte Anima-Corpo" /B .\venv\python.exe .\src\avatar_server.py --tts %TTS_CHOICE% --parallel 1 --kv-unified --reasoning-budget 4096 --ctx-shift-strategy compact > ".\logs\avatar_server.log" 2>&1

REM [DEBUG] Verifica se il Ponte è partito
echo [DEBUG] Controllo avvio avatar_server...
if %errorlevel% neq 0 (
    echo [ERRORE CRITICO] Avvio avatar_server fallito!
    pause
)

REM Passo 3: Pausa di cortesia.
echo %MSG_SOUL_WAIT%
timeout /t 5 /nobreak >nul

REM Passo 4: Invoca l'Anima (nella console attuale).
echo %MSG_SOUL_INVOKE%
echo.

if not exist venv\python.exe (
    echo [ERRORE CRITICO] venv\python.exe non trovato!
    pause
    exit /b
)

.\venv\python.exe chat.py
if %errorlevel% neq 0 (
    echo.
    echo [ERRORE CRITICO] L'Anima si e' spenta in modo anomalo.
    echo Controlla l'errore qui sopra.
    pause
)
if %errorlevel% neq 0 (
    echo.
    echo[ERRORE CRITICO] L'Anima si e' spenta in modo anomalo.
    echo Controlla l'errore qui sopra.
    pause
)

echo.
echo %MSG_SOUL_END%
echo %MSG_SOUL_DISSOLVE%

REM Passo 5: Comando di autodistruzione della finestra.
exit