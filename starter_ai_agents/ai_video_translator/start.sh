#!/usr/bin/env bash
# Startet den Video-Uebersetzer unter macOS/Linux (beim ersten Mal wird alles installiert).
set -e
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
    echo "Richte Python-Umgebung ein ..."
    python3 -m venv .venv
fi
.venv/bin/python -m pip install -q -r requirements.txt
exec .venv/bin/python app.py
