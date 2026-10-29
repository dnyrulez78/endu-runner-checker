@echo off
setlocal enabledelayedexpansion
title Compilazione Runner Scanner Standalone (EXE)

echo =======================================================
echo     RUNNER SCANNER - BUILD ESEGUIBILE PORTATILE
echo =======================================================
echo.
echo Compilazione in corso di RunnerScanner.exe con PyInstaller...
echo Questa operazione puo richiedere circa 1-2 minuti.
echo.

py -3 -m PyInstaller runner_scanner.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo Tentativo con comando python generico...
    python -m PyInstaller runner_scanner.spec --clean --noconfirm
    if errorlevel 1 (
        echo.
        echo [ERRORE] Compilazione fallita.
        echo Assicurati che PyInstaller sia installato (pip install pyinstaller pywebview).
        pause
        exit /b 1
    )
)

echo.
echo =======================================================
echo  COMPILAZIONE COMPLETATA CON SUCCESSO!
echo =======================================================
echo.
echo Il file eseguibile portatile e' disponibile in:
echo %CD%\dist\RunnerScanner.exe
echo.
echo Puoi copiare RunnerScanner.exe ovunque (anche su chiavetta USB)
echo ed eseguirlo con doppio clic su qualsiasi PC Windows.
echo =======================================================
echo.
pause
