"""Dubbing: speak the translated cues with a text-to-speech engine and lay them over the video's timeline.

Two engines are available, both optional installs:
  - EdgeTts  (pip install edge-tts):  very natural Microsoft voices, free, needs an internet connection
  - PiperTts (pip install piper-tts): offline, one downloaded voice (~65 MB) per language
"""

from __future__ import annotations

import asyncio
import subprocess
import threading
import wave
from pathlib import Path
from typing import Optional, Protocol

import numpy as np  # installed together with faster-whisper

from core import (
    LANGUAGES, Cue, LogFn, PipelineError, ProgressFn, check_cancel, install_hint, noop, run_ffmpeg,
    subprocess_flags,
)

DUB_RATE = 24000  # sample rate of the generated dubbing track (mono, 16 bit)
MAX_SPEEDUP = 1.35  # speech faster than this stops being pleasant; the rest is allowed to run late
ORIGINAL_AUDIO_MODES = ("keep", "mix", "drop")  # second track / quietly in the background / removed


class TtsEngine(Protocol):
    def preflight(self) -> None: ...

    def synthesize_all(self, texts: list[str], work_dir: Path, progress: ProgressFn,
                       cancel: Optional[threading.Event]) -> list[Optional[Path]]:
        """One audio file per text (None for empty texts and lines that could not be spoken)."""


# ---------------------------------------------------------------- engines

# language -> (female voice, male voice); checked against Microsoft's live voice list before use
EDGE_VOICES: dict[str, tuple[str, str]] = {
    "de": ("de-DE-KatjaNeural", "de-DE-ConradNeural"),
    "en": ("en-US-AriaNeural", "en-US-GuyNeural"),
    "fr": ("fr-FR-DeniseNeural", "fr-FR-HenriNeural"),
    "es": ("es-ES-ElviraNeural", "es-ES-AlvaroNeural"),
    "it": ("it-IT-ElsaNeural", "it-IT-DiegoNeural"),
    "pt": ("pt-BR-FranciscaNeural", "pt-BR-AntonioNeural"),
    "nl": ("nl-NL-ColetteNeural", "nl-NL-MaartenNeural"),
    "pl": ("pl-PL-ZofiaNeural", "pl-PL-MarekNeural"),
    "cs": ("cs-CZ-VlastaNeural", "cs-CZ-AntoninNeural"),
    "sv": ("sv-SE-SofieNeural", "sv-SE-MattiasNeural"),
    "tr": ("tr-TR-EmelNeural", "tr-TR-AhmetNeural"),
    "ru": ("ru-RU-SvetlanaNeural", "ru-RU-DmitryNeural"),
    "uk": ("uk-UA-PolinaNeural", "uk-UA-OstapNeural"),
    "ar": ("ar-SA-ZariyahNeural", "ar-SA-HamedNeural"),
    "hi": ("hi-IN-SwaraNeural", "hi-IN-MadhurNeural"),
    "zh": ("zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural"),
    "ja": ("ja-JP-NanamiNeural", "ja-JP-KeitaNeural"),
    "ko": ("ko-KR-SunHiNeural", "ko-KR-InJoonNeural"),
}

PIPER_VOICES: dict[str, str] = {
    "de": "de_DE-thorsten-medium", "en": "en_US-lessac-medium", "fr": "fr_FR-siwis-medium",
    "es": "es_ES-davefx-medium", "it": "it_IT-paola-medium", "pt": "pt_BR-faber-medium",
    "nl": "nl_NL-pim-medium", "pl": "pl_PL-gosia-medium", "cs": "cs_CZ-jirka-medium",
    "sv": "sv_SE-nst-medium", "tr": "tr_TR-dfki-medium", "ru": "ru_RU-irina-medium",
    "uk": "uk_UA-ukrainian_tts-medium", "ar": "ar_JO-kareem-medium", "hi": "hi_IN-priyamvada-medium",
    "zh": "zh_CN-huayan-medium", "ja": "ja_JP-hi_fi_captain-medium", "ko": "ko_KR-kss-medium",
}


def pick_edge_voice(voices: list[dict], lang: str, gender: str) -> str:
    """The preferred voice if Microsoft still offers it, otherwise any plain voice of that language."""
    wanted = "Male" if gender == "male" else "Female"
    preferred = EDGE_VOICES[lang][1 if gender == "male" else 0]
    if any(v["ShortName"] == preferred for v in voices):
        return preferred
    pool = sorted(
        (v["ShortName"] for v in voices
         if v["ShortName"].startswith(f"{lang}-") and v["Gender"] == wanted and "Multilingual" not in v["ShortName"]),
        key=lambda name: (name.rsplit("-", 1)[0] != preferred.rsplit("-", 1)[0], name),  # same region first
    )
    if not pool:
        raise PipelineError(f"Es gibt keine Microsoft-Stimme für '{lang}' ({'männlich' if gender == 'male' else 'weiblich'}).")
    return pool[0]


class EdgeTts:
    CONCURRENCY = 4
    ATTEMPTS = 3

    def __init__(self, lang: str, gender: str = "female", log: LogFn = noop):
        self.lang, self.gender, self.log = lang, gender, log
        self.voice = ""

    def preflight(self) -> None:
        try:
            import edge_tts
        except ImportError as e:
            raise PipelineError(f"Für die Microsoft-Stimmen fehlt 'edge-tts'. {install_hint('edge-tts')}") from e
        try:
            voices = asyncio.run(edge_tts.list_voices())
        except Exception as e:
            raise PipelineError(
                "Die Microsoft-Stimmen sind nicht erreichbar. Besteht eine Internetverbindung? "
                f"({type(e).__name__}) Alternativ: die Offline-Stimme (Piper) wählen."
            ) from e
        self.voice = pick_edge_voice(voices, self.lang, self.gender)
        self.log(f"Stimme: {self.voice}")

    def synthesize_all(self, texts, work_dir, progress, cancel):
        return asyncio.run(self._synthesize_all(texts, Path(work_dir), progress, cancel))

    async def _synthesize_all(self, texts, work_dir, progress, cancel):
        import edge_tts

        results: list[Optional[Path]] = [None] * len(texts)
        todo = [i for i, t in enumerate(texts) if t.strip()]
        slots = asyncio.Semaphore(self.CONCURRENCY)
        finished = 0

        async def speak(i: int) -> None:
            nonlocal finished
            async with slots:
                check_cancel(cancel)
                path = work_dir / f"clip_{i:05d}.mp3"
                error: Optional[Exception] = None
                for attempt in range(self.ATTEMPTS):
                    try:
                        await edge_tts.Communicate(texts[i], self.voice).save(str(path))
                        if path.stat().st_size > 0:
                            results[i] = path
                            break
                    except Exception as e:  # network hiccup, throttling, "no audio received", ...
                        error = e
                    await asyncio.sleep(1 + 2 * attempt)
                else:
                    self.log(f"Warnung: Zeile {i + 1} konnte nicht gesprochen werden ({error or 'keine Audiodaten'}).")
                finished += 1
                progress(finished / len(todo))

        await asyncio.gather(*(speak(i) for i in todo))
        return results


class PiperTts:
    def __init__(self, lang: str, log: LogFn = noop, voices_dir: Optional[Path] = None):
        self.lang, self.log = lang, log
        self.voices_dir = Path(voices_dir) if voices_dir else Path.home() / ".video_translator" / "voices"
        self._voice = None

    def preflight(self) -> None:
        try:
            from piper import PiperVoice
            from piper.download_voices import download_voice
        except ImportError as e:
            raise PipelineError(f"Für die Offline-Stimme fehlt 'piper-tts'. {install_hint('piper-tts')}") from e
        name = PIPER_VOICES.get(self.lang)
        if name is None:
            raise PipelineError(f"Für '{self.lang}' gibt es keine Offline-Stimme. Nutze die Microsoft-Stimmen.")
        model = self.voices_dir / f"{name}.onnx"
        if not (model.exists() and model.with_name(model.name + ".json").exists()):
            self.log(f"Lade Offline-Stimme '{name}' (einmalig, ca. 65 MB) ...")
            self.voices_dir.mkdir(parents=True, exist_ok=True)
            try:
                download_voice(name, self.voices_dir, force_redownload=True)
            except Exception as e:
                raise PipelineError(f"Die Stimme '{name}' konnte nicht geladen werden ({type(e).__name__}: {e}).") from e
        self._voice = PiperVoice.load(model)
        self.log(f"Stimme: {name}")

    def synthesize_all(self, texts, work_dir, progress, cancel):
        results: list[Optional[Path]] = [None] * len(texts)
        todo = [i for i, t in enumerate(texts) if t.strip()]
        for done, i in enumerate(todo, start=1):
            check_cancel(cancel)
            path = Path(work_dir) / f"clip_{i:05d}.wav"
            try:
                with wave.open(str(path), "wb") as w:
                    self._voice.synthesize_wav(texts[i], w)
                results[i] = path
            except Exception as e:
                self.log(f"Warnung: Zeile {i + 1} konnte nicht gesprochen werden ({type(e).__name__}: {e}).")
            progress(done / len(todo))
        return results


def make_tts(engine: str, lang: str, gender: str = "female", log: LogFn = noop) -> TtsEngine:
    return PiperTts(lang, log) if engine == "piper" else EdgeTts(lang, gender, log)


# ---------------------------------------------------------------- timeline

def plan_clip(cue_start: float, next_start: float, length: float, cursor: float,
              max_speedup: float = MAX_SPEEDUP) -> tuple[float, float]:
    """Where a spoken clip starts and how much faster it must be played to end before the next line.

    `cursor` is when the previous clip ended: a clip that had to run late pushes this one back
    instead of overlapping it. Speech is only ever sped up, never slowed down.
    """
    start = max(cue_start, cursor)
    room = max(next_start - start, 0.2)
    rate = min(max(length / room, 1.0), max_speedup) if length > 0 else 1.0
    return start, rate


def _decode(ffmpeg: str, clip: Path, tempo: float = 1.0) -> np.ndarray:
    """Decode any audio file to mono 16-bit samples at DUB_RATE, optionally sped up by `tempo`."""
    cmd = [ffmpeg, "-v", "error", "-nostdin", "-i", str(clip), "-ac", "1", "-ar", str(DUB_RATE)]
    if tempo > 1.0:
        cmd += ["-filter:a", f"atempo={tempo:.4f}"]
    proc = subprocess.run(cmd + ["-f", "s16le", "pipe:1"], capture_output=True, creationflags=subprocess_flags())
    if proc.returncode != 0:
        raise PipelineError("Sprachausgabe konnte nicht gelesen werden:\n" + proc.stderr.decode(errors="replace")[-500:])
    return np.frombuffer(proc.stdout, dtype=np.int16)


def _mix_in(track: np.ndarray, pcm: np.ndarray, offset: int) -> None:
    if offset >= len(track):
        return
    n = min(len(pcm), len(track) - offset)
    mixed = track[offset:offset + n].astype(np.int32) + pcm[:n]
    track[offset:offset + n] = np.clip(mixed, -32768, 32767)


def build_dub_track(
    ffmpeg: str,
    cues: list[Cue],
    engine: TtsEngine,
    total_seconds: float,
    work_dir: Path,
    out_wav: Path,
    log: LogFn = noop,
    progress: ProgressFn = noop,
    cancel: Optional[threading.Event] = None,
) -> int:
    """Speak every cue and write one track as long as the video. Returns how many lines stayed silent."""
    total = max(total_seconds, cues[-1].end)
    clips = engine.synthesize_all([c.text for c in cues], work_dir, lambda f: progress(0.85 * f), cancel)

    track = np.zeros(int(total * DUB_RATE) + 1, dtype=np.int16)
    cursor, sped_up, silent = 0.0, 0, 0
    for i, (cue, clip) in enumerate(zip(cues, clips)):
        check_cancel(cancel)
        if clip is None:
            silent += bool(cue.text.strip())
            continue
        pcm = _decode(ffmpeg, clip)
        next_start = cues[i + 1].start if i + 1 < len(cues) else total
        start, rate = plan_clip(cue.start, next_start, len(pcm) / DUB_RATE, cursor)
        if rate > 1.0:
            pcm = _decode(ffmpeg, clip, tempo=rate)
            sped_up += 1
        _mix_in(track, pcm, int(start * DUB_RATE))
        cursor = start + len(pcm) / DUB_RATE
        progress(0.85 + 0.15 * (i + 1) / len(cues))
    if sped_up:
        log(f"{sped_up} Zeilen wurden leicht beschleunigt, damit sie in die Lücke passen.")

    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(DUB_RATE)
        w.writeframes(track.tobytes())
    return silent


# ---------------------------------------------------------------- muxing

def mux_dub(ffmpeg: str, video: Path, dub_wav: Path, out: Path, original: str, lang: str,
            duration: Optional[float], progress: ProgressFn = noop,
            cancel: Optional[threading.Event] = None) -> None:
    """Video stream is copied untouched; the dub becomes the (default) audio track."""
    iso3 = LANGUAGES.get(lang, ("", lang))[1]
    args = ["-i", str(video), "-i", str(dub_wav)]
    if original == "mix":
        # amix halves every input, so double it again afterwards; the limiter catches peaks.
        args += ["-filter_complex",
                 "[0:a:0]volume=0.25[bg];[bg][1:a]amix=inputs=2:duration=first:dropout_transition=0,"
                 "volume=2,alimiter=limit=0.97[a]",
                 "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k"]
    elif original == "drop":
        args += ["-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k"]
    else:
        args += ["-map", "0:v", "-map", "1:a", "-map", "0:a:0", "-c:v", "copy",
                 "-c:a:0", "aac", "-b:a:0", "192k", "-c:a:1", "copy",
                 "-disposition:a:0", "default", "-disposition:a:1", "0",
                 "-metadata:s:a:1", "title=Originalton", "-metadata:s:a:1", "handler_name=Originalton"]
    # MP4 players show handler_name as the track name, MKV players show title: set both.
    name = f"Vertonung ({lang})"
    args += ["-metadata:s:a:0", f"language={iso3}", "-metadata:s:a:0", f"title={name}",
             "-metadata:s:a:0", f"handler_name={name}", str(out)]
    run_ffmpeg(ffmpeg, args, duration, progress, cancel)
