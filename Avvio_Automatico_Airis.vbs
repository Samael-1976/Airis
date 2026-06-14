' Avvio_Automatico_Airis.vbs (v3.0 - Basato sull'Originale Funzionante)
' Avvia i server in background e POI esegue il Risveglia_Airis.bat principale.

' --- Oggetti di sistema (Tuo codice originale) ---
Dim objShell, scriptPath, objFSO, scriptDir
Set objFSO = CreateObject("Scripting.FileSystemObject")
scriptPath = WScript.ScriptFullName
scriptDir = objFSO.GetParentFolderName(scriptPath)

' --- [AGGIUNTA] Creazione dell'oggetto WScript.Shell per i processi in background ---
Set objShell = CreateObject("WScript.Shell")

' ---[NUOVO v118.3] Gestione Scelta Motore Vocale e Backend ---
Dim serverCorpo, serverVoce, ttsChoice, backendChoice
If WScript.Arguments.Count > 0 Then
    ttsChoice = WScript.Arguments(0)
    If ttsChoice = "" Then ttsChoice = "1"
Else
    ttsChoice = "1" ' Default Kokoro
End If

If WScript.Arguments.Count > 1 Then
    backendChoice = WScript.Arguments(1)
    If backendChoice = "" Then backendChoice = "Windows/Windows x64 (CPU)"
Else
    backendChoice = "Windows/Windows x64 (CPU)" ' Fallback sicuro
End If

serverCorpo = """" & scriptDir & "\venv\python.exe"" """ & scriptDir & "\src\avatar_server.py"" --tts " & ttsChoice

' Deleghiamo la logica di scelta del Venv direttamente al file Batch
serverVoce = """" & scriptDir & "\Avvia_Voce.bat"""

' Esecuzione server (0 = nascosto)
objShell.Run "cmd /c " & serverCorpo, 0, False
objShell.Run "cmd /c " & serverVoce, 0, False

' Pausa per stabilizzazione
WScript.Sleep 5000 

Dim batFile, objShellApp
batFile = scriptDir & "\Risveglia_Airis.bat"
Set objShellApp = CreateObject("Shell.Application")

' Passiamo la scelta del backend come argomento al file Risveglia_Airis.bat
'[FIX DEBUG] Rimosso "runas" per evitare crash UAC
objShellApp.ShellExecute batFile, """" & backendChoice & """", scriptDir, "", 1 

' --- Pulizia (Tuo codice originale + aggiunta) ---
Set objShellApp = Nothing
Set objShell = Nothing
Set objFSO = Nothing