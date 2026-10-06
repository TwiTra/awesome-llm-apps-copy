# 🎬 Video-Übersetzer (Desktop-Programm)

Ein Programm für den PC, das Videos **übersetzt**: Es erkennt die gesprochene Sprache, schreibt den Text mit, übersetzt ihn und liefert dir

- eine **Untertitel-Datei** (`.srt`) in der Zielsprache,
- auf Wunsch das **Video mit abschaltbarer Untertitel-Spur** (schnell, das Video wird nicht neu kodiert),
- auf Wunsch das **Video mit eingebrannten Untertiteln** (laufen in jedem Player und auf jedem Handy),
- auf Wunsch **zweisprachige** Untertitel (Übersetzung plus Original darunter).

> **Wichtig:** Das Programm erzeugt Untertitel, **keine neue Tonspur** (kein Synchronsprecher / Voice-over).

## So funktioniert es

```
Video ──ffmpeg──▶ Ton ──Whisper (lokal)──▶ Text + Zeiten ──Claude oder Argos──▶ Übersetzung ──▶ .srt / Video
```

- **Spracherkennung:** [faster-whisper](https://github.com/SYSTRAN/faster-whisper) läuft komplett auf deinem PC. Dein Video wird nirgends hochgeladen.
- **Übersetzung:** Du hast die Wahl
  - **Claude** (beste Qualität, versteht Zusammenhang und Tonfall). Es wird nur der *Text* an die Anthropic-API geschickt, nie Ton oder Video. Du brauchst einen [API-Schlüssel](https://console.anthropic.com/).
  - **Offline** mit [Argos Translate](https://github.com/argosopentech/argos-translate): kostenlos, ohne Internet (nach dem einmaligen Download der Sprachpakete), aber deutlich einfachere Qualität.

## Starten

Du brauchst [Python 3.10 oder neuer](https://www.python.org/downloads/) (unter Windows bei der Installation „Add python.exe to PATH“ ankreuzen).

| System | Start |
|---|---|
| Windows | Doppelklick auf **`start.bat`** |
| macOS / Linux | `./start.sh` (Linux: vorher `sudo apt install python3-tk`) |

Beim ersten Start werden die Pakete installiert (ein paar Minuten). Beim ersten Übersetzen lädt Whisper außerdem sein Sprachmodell herunter (`small` ≈ 500 MB).

ffmpeg musst du nicht extra installieren: Ein mitgeliefertes ffmpeg wird automatisch verwendet. Ein bereits installiertes ffmpeg wird bevorzugt.

### Oberfläche

1. Videos hinzufügen (mehrere auf einmal sind möglich).
2. Sprache im Video (oder „Automatisch erkennen“) und Zielsprache wählen.
3. Übersetzer wählen. Für Claude den API-Schlüssel eintragen. Alternativ die Umgebungsvariable `ANTHROPIC_API_KEY` setzen. Der Schlüssel wird nie in den Einstellungen gespeichert.
4. Auf **Übersetzen** klicken. Die fertigen Dateien liegen neben dem Video (oder im gewählten Ordner). Bestehende Dateien werden nie überschrieben, stattdessen heißt die neue `… (2)`.

### Kommandozeile

```bash
python cli.py urlaub.mp4 --to de                       # Untertitel + Video mit Untertitel-Spur
python cli.py *.mp4 --to en --bilingual                 # mehrere Videos, zweisprachig
python cli.py vortrag.mkv --to fr --burn --whisper medium
python cli.py film.mp4 --to de --backend argos          # komplett offline und kostenlos
python cli.py --help
```

## Tipps

| Whisper-Modell | Geschwindigkeit | Genauigkeit | Wann? |
|---|---|---|---|
| `tiny` / `base` | sehr schnell | gering | nur zum Ausprobieren |
| `small` | gut | gut | **Standard**, klare Sprache |
| `medium` | langsam | sehr gut | Dialekte, Nebengeräusche |
| `large-v3` | sehr langsam (ohne Grafikkarte) | am besten | wichtige Videos; mit NVIDIA-Grafikkarte flott |

- Mit einer NVIDIA-Grafikkarte (CUDA) ist „Gerät: auto“ deutlich schneller.
- Das Standard-Claude-Modell ist `claude-opus-5-5`. Ein kleineres Modell (z. B. `claude-haiku-4-5`) tippst du einfach ins Feld „Modell“, es ist günstiger und etwas weniger fein. Übersetzt wird nur der Text. Das kostet für ein Video von einer Stunde nach grober Schätzung deutlich weniger als einen Dollar.
- **Eingebrannte** Untertitel brauchen ein ffmpeg mit `libass` und kodieren das Video neu, das kann je nach Länge dauern. Das Programm prüft vorher, ob dein ffmpeg das kann, und sagt es, falls nicht. Dann hilft die Untertitel-Spur.
- **Offline-Übersetzung** installierst du einmalig zusätzlich mit `pip install argostranslate` in der Programm-Umgebung (`.venv`). Das ist ein großer Download, weil PyTorch dazugehört.
- Bei einem Fehler in einem Video macht das Programm mit dem nächsten weiter.

## Dateien

| Datei | Inhalt |
|---|---|
| `app.py` | Fenster (tkinter) |
| `cli.py` | Kommandozeile |
| `core.py` | Ablauf: ffmpeg, Whisper, Übersetzer, SRT, Ausgabe |
| `test_core.py` | Tests: `python -m unittest` (ohne Internet, ohne API-Schlüssel) |

## Wie die Claude-Übersetzung arbeitet

Die Zeilen werden in Paketen zu je 40 an Claude geschickt (mit strukturierter JSON-Ausgabe, damit jede Zeile ihrer Übersetzung eindeutig zugeordnet bleibt). Ist eine Antwort unvollständig oder ungültig, wird das Paket halbiert und neu versucht. Eine einzelne Zeile, die gar nicht übersetzt werden kann, bleibt im Original stehen und wird im Protokoll gemeldet. Claude wird angewiesen, den Videotext nur als zu übersetzenden Text zu behandeln und Anweisungen darin, die jemand im Video ausspricht, nicht zu befolgen.
