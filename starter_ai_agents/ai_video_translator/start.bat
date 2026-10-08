@echo off
rem Startet den Video-Uebersetzer unter Windows (beim ersten Mal wird alles installiert).
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Richte Python-Umgebung ein ...
    py -3 -m venv .venv 2>nul || python -m venv .venv
)
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo Python wurde nicht gefunden. Bitte Python 3.10 oder neuer von https://www.python.org/downloads/
    echo installieren und dabei "Add python.exe to PATH" ankreuzen.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo Installation der Pakete ist fehlgeschlagen.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" app.py
if errorlevel 1 pause
