@echo off
setlocal
title ENDU Road Running Checker

echo =======================================================
echo          ENDU ROAD RUNNING REGISTRATION CHECKER
echo =======================================================
echo.
echo Avvio in corso dell'applicazione...
echo.

REM Verifica presenza di Python
where python >nul 2>&1
if errorlevel 1 goto no_python

REM Verifica e installazione dipendenze
echo Verifica delle librerie necessarie...
python -m pip install -r requirements.txt --quiet

echo.
echo =======================================================
echo  Server avviato! Apri il browser su:
echo  http://localhost:8000
echo =======================================================
echo Premi CTRL+C in qualsiasi momento per arrestare il server.
echo.

python app.py
goto end

:no_python
echo [ERRORE] Python non e' installato o non e' configurato nel PATH di Windows.
echo Scarica e installa Python da https://www.python.org/
echo Assicurati di selezionare la casella: "Add Python to PATH".
echo.
pause

:end
