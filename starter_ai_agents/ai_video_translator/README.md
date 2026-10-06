# 🎬 Video-Übersetzer (Desktop-Programm)

Ein Programm für den PC, das Videos **übersetzt**: Es erkennt die gesprochene Sprache, schreibt den Text mit, übersetzt ihn und liefert dir

- eine **Untertitel-Datei** (`.srt`) in der Zielsprache,
- auf Wunsch das **Video mit abschaltbarer Untertitel-Spur** (schnell, das Video wird nicht neu kodiert),
- auf Wunsch das **Video mit eingebrannten Untertiteln** (laufen in jedem Player und auf jedem Handy),
- auf Wunsch **zweisprachige** Untertitel (Übersetzung plus Original darunter),
- auf Wunsch eine **Sprachausgabe**: Eine Computerstimme spricht die Übersetzung, und du bekommst ein Video mit dieser neuen Tonspur (Vertonung).

> **Grenzen der Vertonung:** Es spricht immer *eine* Stimme für alle Sprecher im Video. Stimmen werden nicht nachgeahmt und die Lippenbewegung passt nicht dazu. Zu schnelle Zeilen werden leicht beschleunigt, damit sie in die Lücke passen.

## So funktioniert es

```
Video ──ffmpeg──▶ Ton ──Whisper (lokal)──▶ Text + Zeiten ──Claude oder Argos──▶ Übersetzung ──▶ .srt / Video
                                                                                    │
                                                              Edge-TTS oder Piper ◀─┘ (optional) ──▶ Video mit neuer Tonspur
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

### Als .exe (ohne Python)

Wer kein Python installieren will, nimmt die fertige Windows-Version. GitHub baut sie auf einem Windows-Rechner und prüft sie mit einem eingebauten Selbsttest (`.github/workflows/video-translator-exe.yml`):

1. Im Repository auf **Actions** gehen, links **video-translator-exe** wählen, **Run workflow** klicken.
2. Nach etwa 15 bis 30 Minuten steht auf der Seite des Laufs unter **Artifacts** (GitHub-Login nötig, 90 Tage lang abrufbar):
   - `VideoUebersetzer-exe`: **eine einzelne Datei**. Sie entpackt sich bei jedem Start selbst und braucht deshalb einen Moment.
   - `VideoUebersetzer-Ordner`: ZIP mit einem Ordner. Entpacken und `VideoUebersetzer.exe` starten, geht schneller.
3. Wer einen normalen Download-Link will, legt ein Tag an (`git tag video-translator-v1.0 && git push origin video-translator-v1.0`). Dann stellt der Lauf beide Dateien als **Release** ein.

Oder selbst bauen, auf einem Windows-PC mit Python: `pip install -r requirements.txt pyinstaller`, dann `python build_exe.py --onefile`. Das Ergebnis liegt in `dist/`.

Gut zu wissen:
- Die Datei ist groß (einige hundert MB), weil Whisper, ffmpeg und die Python-Pakete drinstecken. Das Sprachmodell lädt Whisper beim ersten Übersetzen herunter.
- Die Datei ist nicht signiert. Windows zeigt deshalb evtl. „Der Computer wurde durch Windows geschützt“: **Weitere Informationen → Trotzdem ausführen**. Auch Virenscanner schlagen bei solchen Programmen manchmal fälschlich an.
- **Nicht** enthalten sind die Offline-Übersetzung (Argos) und die Offline-Stimme (Piper), sie sind im Fenster ausgegraut. Dafür braucht es das Python-Setup (`start.bat`).
- Eine Grafikkarte wird nur genutzt, wenn die CUDA-Bibliotheken von NVIDIA installiert sind, sonst rechnet das Programm auf dem Prozessor.
- Einstellungen und Protokoll liegen im Benutzerordner (`.video_translator.json`, `.video_translator.log`). Bei Problemen hilft das Protokoll.
- `VideoUebersetzer.exe --selftest ergebnis.txt` prüft, ob alle Teile des Programms laufen, und schreibt das Ergebnis in die Datei.

### Oberfläche

1. Videos hinzufügen (mehrere auf einmal sind möglich).
2. Sprache im Video (oder „Automatisch erkennen“) und Zielsprache wählen.
3. Übersetzer wählen. Für Claude den API-Schlüssel eintragen. Alternativ die Umgebungsvariable `ANTHROPIC_API_KEY` setzen. Der Schlüssel wird nie in den Einstellungen gespeichert.
4. Wer eine gesprochene Übersetzung will, setzt unter **6. Sprachausgabe** den Haken und wählt Stimme und Originalton.
5. Auf **Übersetzen** klicken. Die fertigen Dateien liegen neben dem Video (oder im gewählten Ordner). Bestehende Dateien werden nie überschrieben, stattdessen heißt die neue `… (2)`.

### Kommandozeile

```bash
python cli.py urlaub.mp4 --to de                       # Untertitel + Video mit Untertitel-Spur
python cli.py *.mp4 --to en --bilingual                 # mehrere Videos, zweisprachig
python cli.py vortrag.mkv --to fr --burn --whisper medium
python cli.py film.mp4 --to de --backend argos          # komplett offline und kostenlos
python cli.py interview.mp4 --to de --dub               # zusätzlich ein Video mit gesprochener Übersetzung
python cli.py interview.mp4 --to de --dub --voice male --original mix
python cli.py interview.mp4 --to de --dub --tts piper   # Offline-Stimme
python cli.py --help
```

## Sprachausgabe (Vertonung)

Das Ergebnis heißt `<video>.<sprache>.vertont.mp4` (bzw. `.mkv`, wenn das Original kein MP4/MOV war). Das Bild wird nicht neu kodiert, nur die Tonspur kommt dazu.

| Einstellung | Möglichkeiten |
|---|---|
| **Stimme** | **Microsoft-Stimmen** (Edge-TTS): sehr natürlich, kostenlos, aber mit Internet. Der übersetzte *Text* wird dabei an Microsofts Online-Dienst geschickt, kein Ton und kein Video. Das Programm nutzt dafür die inoffizielle Schnittstelle der Vorlesefunktion von Microsoft Edge. Sie kann sich ändern und dann vorübergehend nicht mehr gehen. Zur Auswahl stehen eine weibliche und eine männliche Stimme pro Sprache.<br>**Offline-Stimme** (Piper): läuft ganz ohne Internet, klingt einfacher. Pro Sprache gibt es eine feste Stimme, die beim ersten Mal heruntergeladen wird (ca. 65 MB, gespeichert in `~/.video_translator/voices`). Dafür einmalig `pip install piper-tts` in der Programm-Umgebung. Piper steht unter GPL-3.0 und wird nicht mitgeliefert. |
| **Originalton** | als **zweite Tonspur behalten** (im Player umschaltbar, die Vertonung läuft zuerst), **leise im Hintergrund** mitlaufen lassen oder **entfernen** |

So wird der Ton zusammengebaut: Jede Zeile wird einzeln gesprochen und zur Startzeit des Originals eingesetzt. Passt eine Zeile nicht bis zur nächsten, wird sie bis höchstens 1,35-fach beschleunigt. Reicht das nicht, verschiebt sich die nächste Zeile ein Stück nach hinten, statt dass sich beide überlagern. Zeilen, die die Stimme nicht sprechen kann, bleiben stumm und werden gemeldet.

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
| `pipeline.py` | der ganze Ablauf für ein Video |
| `core.py` | Bausteine: ffmpeg, Whisper, Übersetzer, Untertitel (SRT) |
| `dubbing.py` | Sprachausgabe: Stimmen, Zeitplan, Tonspur zusammenbauen |
| `selftest.py` | Selbsttest (`python app.py --selftest`), prüft auch die gebaute `.exe` |
| `build_exe.py` | baut die `.exe` mit PyInstaller |
| `test_core.py`, `test_dubbing.py` | Tests: `python -m unittest` (ohne Internet, ohne API-Schlüssel) |

## Wie die Claude-Übersetzung arbeitet

Die Zeilen werden in Paketen zu je 40 an Claude geschickt (mit strukturierter JSON-Ausgabe, damit jede Zeile ihrer Übersetzung eindeutig zugeordnet bleibt). Ist eine Antwort unvollständig oder ungültig, wird das Paket halbiert und neu versucht. Eine einzelne Zeile, die gar nicht übersetzt werden kann, bleibt im Original stehen und wird im Protokoll gemeldet. Claude wird angewiesen, den Videotext nur als zu übersetzenden Text zu behandeln und Anweisungen darin, die jemand im Video ausspricht, nicht zu befolgen.
