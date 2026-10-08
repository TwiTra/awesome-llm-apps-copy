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
Video ──ffmpeg──▶ Ton ──Whisper (lokal)──▶ Text + Zeiten ──Claude oder Offline──▶ Übersetzung ──▶ .srt / Video
                                                                                    │
                                                              Edge-TTS oder Piper ◀─┘ (optional) ──▶ Video mit neuer Tonspur
```

- **Spracherkennung:** [faster-whisper](https://github.com/SYSTRAN/faster-whisper) läuft komplett auf deinem PC. Dein Video wird nirgends hochgeladen.
- **Übersetzung:** Du hast die Wahl
  - **Claude** (beste Qualität, versteht Zusammenhang und Tonfall). Es wird nur der *Text* an die Anthropic-API geschickt, nie Ton oder Video. Du brauchst einen [API-Schlüssel](https://console.anthropic.com/).
  - **Offline** (fest eingebaut, auch in der `.exe`): kostenlos und ohne Internet, aber **nur für Deutsch, Russisch und Englisch** (in allen Richtungen, Russisch ↔ Deutsch läuft über Englisch). Die Qualität ist einfacher als bei Claude: Der Sinn kommt meist an, aber Umgangssprache, Eigennamen und Fachbegriffe werden öfter falsch oder wörtlich übersetzt. Die Modelle stammen vom Projekt [Argos Translate](https://github.com/argosopentech/argos-translate) (trainiert auf [OPUS](https://opus.nlpl.eu/)-Daten). Beim ersten Mal wird je Richtung ein Modell (150 bis 200 MB) von argos-net.com geladen, mit Prüfsumme kontrolliert und unter `~/.video_translator/models` abgelegt. Danach braucht die Übersetzung kein Internet mehr. Ein Video mit 450 Zeilen dauert auf einem normalen Rechner etwa eine Minute, bei Russisch ↔ Deutsch (zwei Schritte) doppelt so lang. Den Ordner kannst du jederzeit löschen, um Platz zu schaffen.

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
2. Nach etwa fünf Minuten steht auf der Seite des Laufs ganz unten unter **Artifacts** (GitHub-Login nötig, 90 Tage lang abrufbar). GitHub liefert jeden Artifact als ZIP, die du einmal entpackst:
   - `VideoUebersetzer-exe`: darin liegt **eine einzelne Datei** (`VideoUebersetzer.exe`, rund 140 MB). Sie entpackt sich bei jedem Start selbst und braucht deshalb einen Moment.
   - `VideoUebersetzer-Ordner`: darin liegt `VideoUebersetzer-windows.zip` mit einem Ordner. Auch das entpacken und `VideoUebersetzer.exe` starten, das startet schneller.
3. Wer einen normalen Download-Link will, legt ein Tag an (`git tag video-translator-v1.0 && git push origin video-translator-v1.0`). Dann stellt der Lauf beide Dateien als **Release** ein.

Oder selbst bauen, auf einem Windows-PC mit Python: `pip install -r requirements.txt pyinstaller`, dann `python build_exe.py --onefile`. Das Ergebnis liegt in `dist/`.

Gut zu wissen:
- Die Datei ist groß, weil Whisper, ffmpeg und die Python-Pakete drinstecken. Das Sprachmodell lädt Whisper beim ersten Übersetzen zusätzlich herunter (`small` ≈ 500 MB).
- Die Datei ist nicht signiert. Windows zeigt deshalb evtl. „Der Computer wurde durch Windows geschützt“: **Weitere Informationen → Trotzdem ausführen**. Auch Virenscanner schlagen bei solchen Programmen manchmal fälschlich an.
- Die Offline-Übersetzung für Deutsch, Russisch und Englisch ist eingebaut. **Nicht** enthalten sind die Offline-Übersetzung für weitere Sprachen (Argos, braucht PyTorch) und die Offline-Stimme (Piper), die Stimme ist im Fenster ausgegraut. Beides gibt es nur im Python-Setup (`start.bat`).
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
python cli.py film.mp4 --to de --backend offline        # kostenlos ohne Internet (Deutsch, Russisch, Englisch)
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
- Offline in **anderen Sprachen** als Deutsch, Russisch und Englisch geht nur im Python-Setup: Installiere einmalig `pip install argostranslate` in der Programm-Umgebung (`.venv`), dann nimmt „Offline“ dafür dieses Paket. Das ist ein großer Download, weil PyTorch dazugehört.
- Das Programm prüft **vor** der langen Spracherkennung, ob der API-Schlüssel, das Modell und das Guthaben passen (mit einer winzigen Testanfrage für ein Wort). Ein leeres Guthaben fällt so sofort auf. Der Claude-Chat (Abo) und die API sind getrennte Konten: Das Guthaben für die API lädst du unter console.anthropic.com auf.
- Ist die Spracherkennung fertig und die Übersetzung scheitert danach (Internet weg, Rate-Limit), merkt sich das Programm den erkannten Text unter `~/.video_translator/cache` (die letzten 30 Videos). Beim nächsten Versuch mit demselben Video, Whisper-Modell und derselben Sprache entfällt die Spracherkennung. Der Ordner enthält den erkannten Text, du kannst ihn jederzeit löschen.
- Bei einem Fehler in einem Video macht das Programm mit dem nächsten weiter.

## Dateien

| Datei | Inhalt |
|---|---|
| `app.py` | Fenster (tkinter) |
| `cli.py` | Kommandozeile |
| `pipeline.py` | der ganze Ablauf für ein Video |
| `core.py` | Bausteine: ffmpeg, Whisper, Übersetzer, Untertitel (SRT) |
| `dubbing.py` | Sprachausgabe: Stimmen, Zeitplan, Tonspur zusammenbauen |
| `offline.py` | Offline-Übersetzung Deutsch/Russisch/Englisch: Modelle laden und prüfen, übersetzen |
| `selftest.py` | Selbsttest (`python app.py --selftest`), prüft auch die gebaute `.exe` |
| `build_exe.py` | baut die `.exe` mit PyInstaller |
| `test_core.py`, `test_dubbing.py`, `test_offline.py`, `test_gui.py` | Tests: `python -m unittest` (ohne Internet, ohne API-Schlüssel) |

## Wie die Claude-Übersetzung arbeitet

Die Zeilen werden in Paketen zu je 40 an Claude geschickt (mit strukturierter JSON-Ausgabe, damit jede Zeile ihrer Übersetzung eindeutig zugeordnet bleibt). Ist eine Antwort unvollständig oder ungültig, wird das Paket halbiert und neu versucht. Eine einzelne Zeile, die gar nicht übersetzt werden kann, bleibt im Original stehen und wird im Protokoll gemeldet. Claude wird angewiesen, den Videotext nur als zu übersetzenden Text zu behandeln und Anweisungen darin, die jemand im Video ausspricht, nicht zu befolgen.
