@echo off
chcp 65001
:: --- [NUOVO] SELEZIONE LINGUA AL PRIMO AVVIO ---
if not exist "%~dp0lang.cfg" (
    setlocal enabledelayedexpansion
    cls
    echo =================================================
    echo   AIRIS-PROJECT: LANGUAGE SELECTION / SELEZIONE LINGUA
    echo =================================================
    echo.
    set count=0
    for /d %%D in ("%~dp0Translations\System_env\*") do (
        set /a count+=1
        set "lang_!count!=%%~nxD"
        echo   [!count!] - %%~nxD
    )
    echo.
    set /p lang_choice="> Select your language / Seleziona la lingua (1-!count!): "
    
    :: Fallback di sicurezza
    if "!lang_choice!"=="" set lang_choice=1
    if !lang_choice! GTR !count! set lang_choice=1
    if !lang_choice! LSS 1 set lang_choice=1
    
    for %%A in (!lang_choice!) do set "SELECTED_LANG=!lang_%%A!"
    :: Scrive nel file senza spazi finali
    echo !SELECTED_LANG!>"%~dp0lang.cfg"
    endlocal
)
:: ------------------------------------------------

REM Carica la lingua e le traduzioni
set /p LANG=<"%~dp0lang.cfg"
if not defined LANG set LANG=en
for /f "usebackq tokens=1,* delims==" %%a in ("%~dp0Translations\System_env\%LANG%\system-%LANG%.env") do set "%%a=%%~b"

:: --- [NUOVO v1.1] AUTO-PATCHER PERCORSI (AGNOSTICISMO ROOT) ---
set "BASE_DIR=%~dp0"
set "BASE_DIR=%BASE_DIR:~0,-1%"

if exist "venv\pyvenv.cfg" (
    REM Patch pyvenv.cfg: aggiorna la stringa 'command' con il percorso attuale
    powershell -NoProfile -Command "(Get-Content 'venv\pyvenv.cfg') -replace '(?<=-m venv ).*', '%BASE_DIR%\venv' | Set-Content 'venv\pyvenv.cfg'" >nul 2>&1
)

if exist "venv\Scripts\activate.bat" (
    REM Patch activate.bat: aggiorna la variabile VIRTUAL_ENV per la portabilita' del terminale
    powershell -NoProfile -Command "(Get-Content 'venv\Scripts\activate.bat') -replace '(?<=set \"\"VIRTUAL_ENV=).*(?=\"\")', '%BASE_DIR%\venv' | Set-Content 'venv\Scripts\activate.bat'" >nul 2>&1
)
:: -------------------------------------------------------------

TITLE %TITLE_RUN%

:: --- PULIZIA PREVENTIVA (ZOMBIE KILLER) ---
echo %MSG_RUN_CLEAN%
REM Uccide i processi cercando sia i vecchi titoli (per sicurezza) che i nuovi titoli tradotti
taskkill /FI "WINDOWTITLE eq Progetto Airis - Anima di Airis" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Progetto Airis - Voce di Airis" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq %TITLE_SOUL%" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq %TITLE_VOICE%" /F >nul 2>&1

:: Uccide python se sta girando chat.py o avatar_server.py (euristica base)
wmic process where "name='python.exe' and commandline like '%%chat.py%%'" call terminate >nul 2>&1
wmic process where "name='python.exe' and commandline like '%%avatar_server.py%%'" call terminate >nul 2>&1
wmic process where "name='python.exe' and commandline like '%%vibevoice_realtime_openai_api.py%%'" call terminate >nul 2>&1
echo %MSG_RUN_CLEAN_DONE%

echo %MSG_RUN_START%
echo %MSG_RUN_DESC%
echo %MSG_RUN_WAIT%

:: --- NUOVO PASSO: FORGIATURA AUTOMATICA FRONTEND ---
echo %MSG_RUN_FRONTEND%
@echo off

REM [NUOVO] Diciamo al sistema di usare il Node.js portatile per questo script
set "PATH=%~dp0node_portable;%PATH%"

pushd frontend_mobile
echo %MSG_RUN_NPM%
call npm install react-rnd
call npm install --legacy-peer-deps
echo %MSG_RUN_BROWSER%
call npm i baseline-browser-mapping@latest -D
echo %MSG_RUN_BUILD%
call npm run build
REM echo %MSG_RUN_I18NEXT%
REM call npm install i18next react-i18next
echo %MSG_RUN_FIX%
call npm audit fix
popd

@echo on
echo %MSG_RUN_FRONTEND_READY%
:: --------------------------------------------------

:: --- NUOVO PASSO: RIPARAZIONE DEI SENTIERI (FIX PATHS) ---
echo %MSG_RUN_FIX_PATHS%
"%~dp0venv\python.exe" src\fix_intent_paths.py
echo %MSG_RUN_PATHS_DONE%
:: --------------------------------------------------

:: --- NUOVO PASSO: SINCRONIZZAZIONE DURATE VIDEO ---
echo %MSG_RUN_SYNC%
"%~dp0venv\python.exe" src\verify_and_sync_durations.py
echo %MSG_RUN_SYNC_DONE%
:: --------------------------------------------------

:: --- [NUOVO v118.3] SCELTA MOTORE VOCALE ---
@echo off
cls
echo.
echo  ============================================================
echo             %MSG_RUN_TTS_TITLE%
echo  ============================================================
echo.
echo    [1] %MSG_RUN_TTS_OPT1%
echo    [2] %MSG_RUN_TTS_OPT2%
echo.
echo  ============================================================
echo.

%SYSTEMROOT%\System32\choice.exe /C 12 /T 30 /D 2 /N /M "%MSG_RUN_TTS_PROMPT% "
set TTS_CHOICE=%errorlevel%

REM Salva la scelta per gli script successivi (sintassi sicura anti-spazio)
> "%~dp0tts_choice.cfg" echo %TTS_CHOICE%
:: -------------------------------------------

:: --- [NUOVO] SCELTA PIATTAFORMA HARDWARE DINAMICA ---
cls
setlocal enabledelayedexpansion
echo.
echo  ============================================================
echo             %MSG_RUN_HW_TITLE%
echo  ============================================================
echo.

set count=0
for /d %%D in ("%~dp0bin\Windows\*") do (
    set /a count+=1
    set "backend_!count!=%%~nxD"
    echo    [!count!] - %%~nxD
)

echo.
echo  ============================================================
echo.
set /p choice="%MSG_RUN_HW_PROMPT% (1-!count!): "

:: -------------------------------------------

:: Fallback di sicurezza se l'utente preme solo invio o inserisce un valore errato
        if "!choice!"=="" set choice=1
        if !choice! GTR !count! set choice=1
        if !choice! LSS 1 set choice=1

        for %%A in (!choice!) do set "SELECTED_BACKEND=!backend_%%A!"
        :: Il prefisso Windows/ è necessario perché la struttura è bin/Windows/NOME_CARTELLA
        set "AIRIS_BACKEND=Windows/!SELECTED_BACKEND!"

:: -------------------------------------------

    REM Esegue lo script VBScript passando la scelta del motore e del backend hardware.
    cscript //Nologo "Avvio_Automatico_Airis.vbs" "%TTS_CHOICE%" "!AIRIS_BACKEND!"
    
    if !errorlevel! neq 0 (
        echo.
        echo !MSG_RUN_VBS_ERROR!
        pause
        exit /b
    )
    endlocal

echo.
echo %MSG_RUN_SUCCESS_1%
echo %MSG_RUN_SUCCESS_2%
echo %MSG_RUN_SUCCESS_3%
timeout /t 3 >nul
exit