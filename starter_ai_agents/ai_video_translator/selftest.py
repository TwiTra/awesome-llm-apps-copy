"""Self-test of an installation or of the packaged .exe.

    VideoUebersetzer.exe --selftest ergebnis.txt     (the .exe has no console, so it writes a file)
    python app.py --selftest

Exercises every part that can break in a packaged build (bundled ffmpeg, Whisper + its VAD model,
the Claude client, TTS packages, the window) without needing an API key or a microphone.
The first run downloads Whisper's smallest model (~75 MB).
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import traceback
import wave
from pathlib import Path
from typing import Callable, Optional

OK, WARN, FAIL = "OK", "WARN", "FAIL"


class Skip(Exception):
    """A check that cannot run here (e.g. no display); reported as a warning, not a failure."""


def _tone(path: Path, seconds: float, rate: int = 22050, amplitude: float = 0.5) -> None:
    import numpy as np

    t = np.arange(int(seconds * rate)) / rate
    samples = (amplitude * np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(samples.tobytes())


def check_imports() -> str:
    import importlib

    names = ["tkinter", "numpy", "faster_whisper", "ctranslate2", "onnxruntime", "av", "anthropic",
             "edge_tts", "certifi", "imageio_ffmpeg", "core", "dubbing", "pipeline"]
    for name in names:
        importlib.import_module(name)
    return f"{len(names)} Module"


def check_ffmpeg() -> str:
    import core

    exe = core.find_ffmpeg()
    first = subprocess.run([exe, "-version"], capture_output=True, text=True,
                           creationflags=core.subprocess_flags()).stdout.splitlines()[0]
    return f"{first} [{exe}]"


def check_libass() -> str:
    import core

    try:
        core.find_ffmpeg(need_subtitles_filter=True)
    except core.PipelineError as e:
        raise Skip(f"{e} (Untertitel einbrennen geht dann nicht, die Untertitel-Spur schon)") from e
    return "Untertitel einbrennen möglich"


def check_video_roundtrip() -> str:
    import core
    from core import Cue

    ffmpeg = core.find_ffmpeg()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        video = tmp_dir / "clip.mp4"
        subprocess.run(
            [ffmpeg, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=160x120:d=1",
             "-f", "lavfi", "-i", "sine=frequency=440:duration=1", "-shortest",
             "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", str(video)],
            check=True, creationflags=core.subprocess_flags())
        wav = tmp_dir / "audio.wav"
        core.extract_audio(ffmpeg, video, wav)
        srt = tmp_dir / "clip.de.srt"
        srt.write_text(core.build_srt([Cue(0, 1, "Hallo Welt", original="Hello world")], bilingual=True), encoding="utf-8")
        seen: list[float] = []
        out = tmp_dir / "soft.mp4"
        core.embed_soft_subtitles(ffmpeg, video, srt, out, "de", core.probe_duration(ffmpeg, video), seen.append, None)
        if not out.exists() or out.stat().st_size == 0:
            raise RuntimeError("Video mit Untertitel-Spur wurde nicht erzeugt")
        return f"Ton extrahiert ({wav.stat().st_size} Bytes), Untertitel-Spur eingebettet"


def check_whisper() -> str:
    import core

    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "quiet.wav"
        _tone(wav, 3.0, rate=16000, amplitude=0.0)  # silence: the VAD model runs and finds no speech
        cues, language = core.transcribe(wav, "tiny", None, "cpu")
    return f"Modell 'tiny' und Sprachaktivitäts-Erkennung laufen ({len(cues)} Textabschnitte in Stille, Sprache '{language}')"


def check_claude_client() -> str:
    import anthropic
    import httpx2

    import core

    def handler(request: "httpx2.Request") -> "httpx2.Response":
        lines = json.loads(json.loads(request.content)["messages"][0]["content"])["lines"]
        body = {"id": "msg_1", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
                "content": [{"type": "text", "text": json.dumps(
                    {"translations": [{"id": line["id"], "text": "DE:" + line["text"]} for line in lines]})}],
                "stop_reason": "end_turn", "stop_sequence": None,
                "usage": {"input_tokens": 1, "output_tokens": 1}}
        return httpx2.Response(200, json=body)

    client = anthropic.Anthropic(api_key="selftest",
                                 http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(handler)))
    result = core.ClaudeTranslator("de", core.DEFAULT_CLAUDE_MODEL, client=client).translate(["Hello"], "en")
    if result != ["DE:Hello"]:
        raise RuntimeError(f"unerwartetes Ergebnis: {result}")
    return "Anfrage und Antwort verarbeitet (simulierter Server)"


def check_edge_tts() -> str:
    import certifi
    import edge_tts

    edge_tts.Communicate("Hallo", "de-DE-KatjaNeural")
    if not Path(certifi.where()).exists():
        raise RuntimeError("Zertifikatsdatei fehlt: " + certifi.where())
    return "edge-tts und Zertifikate vorhanden"


def check_dub_track() -> str:
    import core
    import dubbing
    from core import Cue

    class Tone:
        def preflight(self) -> None:
            pass

        def synthesize_all(self, texts, work_dir, progress, cancel):
            out = []
            for i, _ in enumerate(texts):
                path = Path(work_dir) / f"tone_{i}.wav"
                _tone(path, 0.5)
                out.append(path)
            return out

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "dub.wav"
        silent = dubbing.build_dub_track(core.find_ffmpeg(), [Cue(0.2, 0.9, "a"), Cue(1.0, 1.5, "b")],
                                         Tone(), 2.0, Path(tmp), out)
        if silent or out.stat().st_size < 1000:
            raise RuntimeError("Tonspur der Sprachausgabe ist leer")
    return "Tonspur der Sprachausgabe zusammengebaut"


def check_window() -> str:
    import tkinter

    import app

    try:
        window = app.App()
    except tkinter.TclError as e:
        raise Skip(f"kein Bildschirm verfügbar ({e})") from e
    try:
        window.update()
        window.title()
    finally:
        window.destroy()
    return "Fenster lässt sich aufbauen"


CHECKS: list[tuple[str, Callable[[], str]]] = [
    ("Pakete", check_imports),
    ("ffmpeg", check_ffmpeg),
    ("ffmpeg: Untertitel einbrennen", check_libass),
    ("Video: Ton holen, Untertitel einbetten", check_video_roundtrip),
    ("Whisper + Sprachaktivität", check_whisper),
    ("Claude-Anbindung", check_claude_client),
    ("Microsoft-Stimmen", check_edge_tts),
    ("Sprachausgabe: Tonspur", check_dub_track),
    ("Fenster", check_window),
]


def run(report_path: Optional[Path] = None) -> int:
    lines: list[str] = []
    failed = 0
    for name, check in CHECKS:
        try:
            status, detail = OK, check()
        except Skip as e:
            status, detail = WARN, str(e)
        except Exception as e:
            status, detail = FAIL, f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=4)}"
            failed += 1
        line = f"[{status}] {name}: {detail}"
        lines.append(line)
        if sys.stdout is not None:
            print(line, flush=True)
    lines.append("SELFTEST " + ("FEHLGESCHLAGEN" if failed else "BESTANDEN"))
    if sys.stdout is not None:
        print(lines[-1], flush=True)
    if report_path is not None:
        Path(report_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 1 if failed else 0
