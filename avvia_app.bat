@echo off
setlocal enabledelayedexpansion
title ENDU Runner Scanner

echo =======================================================
echo         ENDU ROAD RUNNING CHECKER AND RESULTS
echo =======================================================
echo.
echo Avvio in corso dell'applicazione...
echo.

set "PY_CMD="

REM 1. Verifica con py (Python Launcher ufficiale di Windows)
py -3 -c "import sys" >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=py -3"
    goto found_python
)

REM 2. Verifica con comando python generico (se funzionante e non alias vuoto di Windows)
python -c "import sys" >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=python"
    goto found_python
)

REM 3. Ricerca automatica nelle cartelle di installazione utente standard
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
    if exist "%%D\python.exe" (
        "%%D\python.exe" -c "import sys" >nul 2>&1
        if not errorlevel 1 (
            set "PY_CMD="%%D\python.exe""
            goto found_python
        )
    )
)

REM 4. Ricerca automatica nelle cartelle di installazione Program Files
for /d %%D in ("%ProgramFiles%\Python*") do (
    if exist "%%D\python.exe" (
        "%%D\python.exe" -c "import sys" >nul 2>&1
        if not errorlevel 1 (
            set "PY_CMD="%%D\python.exe""
            goto found_python
        )
    )
)

REM 5. Ricerca in Program Files (x86)
if defined ProgramFiles(x86) (
    for /d %%D in ("%ProgramFiles(x86)%\Python*") do (
        if exist "%%D\python.exe" (
            "%%D\python.exe" -c "import sys" >nul 2>&1
            if not errorlevel 1 (
                set "PY_CMD="%%D\python.exe""
                goto found_python
            )
        )
    )
)

REM Se nessun Python valido e' stato trovato
goto no_python

:found_python
echo [OK] Interprete Python trovato: !PY_CMD!
echo.
echo Verifica delle librerie necessarie (fastapi, uvicorn, httpx)...
!PY_CMD! -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo.
    echo [AVVISO] Installazione automatica con output dettagliato...
    !PY_CMD! -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERRORE] Impossibile installare le librerie richieste.
        echo Verifica la tua connessione a Internet e riprova.
        pause
        exit /b 1
    )
)

echo.
echo =======================================================
echo  Server in esecuzione!
echo  Apri il tuo browser all'indirizzo:
echo  http://localhost:8000
echo =======================================================
echo Premi CTRL+C in questa finestra per arrestare il server.
echo.

!PY_CMD! app.py
goto end

:no_python
echo =======================================================
echo  [ERRORE] Python non e' installato su questo computer!
echo =======================================================
echo.
echo Su questo PC Windows non e' ancora presente Python.
echo.
echo COME RISOLVERE IN 1 MINUTO:
echo -------------------------------------------------------
echo 1. Si aprira' subito la pagina ufficiale di download:
echo    https://www.python.org/downloads/
echo.
echo 2. Clicca sul pulsante giallo "Download Python 3.xx".
echo.
echo 3. Avvia il file scaricato.
echo.
echo    *** PASSAGGIO FONDAMENTALE ***
echo    Nella primissima schermata, METTI LA SPUNTA in basso su:
echo    [X] "Add python.exe to PATH"
echo.
echo 4. Clicca su "Install Now".
echo.
echo 5. Al termine dell'installazione, fai di nuovo doppio clic
echo    su questo file "avvia_app.bat"!
echo =======================================================
echo.
start https://www.python.org/downloads/
pause

:end
