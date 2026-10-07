"""The whole job for one video: transcribe, translate, write subtitles, optionally dub."""

from __future__ import annotations

import hashlib
import json
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from core import (
    DEFAULT_CLAUDE_MODEL, ArgosTranslator, ClaudeTranslator, Cue, LogFn, PipelineError, ProgressFn,
    build_srt, burn_subtitles, embed_soft_subtitles, extract_audio, find_ffmpeg, language_label, noop,
    probe_duration, transcribe, unique_path,
)
from dubbing import build_dub_track, make_tts, mux_dub


@dataclass
class Options:
    target_lang: str = "de"
    source_lang: Optional[str] = None  # None = detect automatically
    backend: str = "claude"  # "claude" | "argos"
    api_key: str = ""
    claude_model: str = DEFAULT_CLAUDE_MODEL
    whisper_model: str = "small"
    device: str = "auto"  # "auto" | "cpu" | "cuda"
    bilingual: bool = False
    soft_video: bool = True  # copy of the video with a switchable subtitle track
    burn_video: bool = False  # copy of the video with the subtitles drawn into the picture
    dub: bool = False  # copy of the video with the translation spoken by a synthetic voice
    tts_engine: str = "edge"  # "edge" (online, very natural) | "piper" (offline)
    voice_gender: str = "female"  # "female" | "male" (Microsoft voices only)
    original_audio: str = "keep"  # "keep" as 2nd track | "mix" quietly in the background | "drop"
    output_dir: Optional[Path] = None  # None = next to the video


# A finished speech recognition is worth keeping: if the translation then fails (empty credit balance,
# no internet, rate limit), the next attempt does not have to transcribe the whole video again.
CACHE_DIR = Path.home() / ".video_translator" / "cache"
CACHE_KEEP = 30  # newest transcripts to keep


def _cache_file(video: Path, opts: Options) -> Path:
    stat = video.stat()
    key = json.dumps([str(video.resolve()), stat.st_size, stat.st_mtime_ns, opts.whisper_model, opts.source_lang or "auto"])
    return CACHE_DIR / (hashlib.sha1(key.encode("utf-8")).hexdigest()[:20] + ".json")


def _load_transcript(path: Path) -> Optional[tuple[list[Cue], str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        cues = [Cue(float(c["start"]), float(c["end"]), str(c["text"])) for c in data["cues"]]
        return (cues, str(data["language"])) if cues else None
    except (OSError, ValueError, KeyError, TypeError):
        return None  # missing or damaged: just transcribe again


def _save_transcript(path: Path, cues: list[Cue], language: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"language": language, "cues": [{"start": c.start, "end": c.end, "text": c.text} for c in cues]}
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        for old in sorted(path.parent.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)[CACHE_KEEP:]:
            old.unlink(missing_ok=True)
    except OSError:
        pass  # a cache is a convenience, never a reason to fail


def make_translator(opts: Options, log: LogFn = noop):
    if opts.backend == "argos":
        return ArgosTranslator(opts.target_lang, log)
    return ClaudeTranslator(opts.target_lang, opts.claude_model or DEFAULT_CLAUDE_MODEL, opts.api_key, log)


class _Budget:
    """Splits the 0..1 progress bar between the stages that will actually run."""

    def __init__(self, progress: ProgressFn, weights: dict[str, float]):
        self._progress = progress
        total = sum(weights.values())
        self._spans: dict[str, tuple[float, float]] = {}
        done = 0.0
        for name, weight in weights.items():
            self._spans[name] = (done / total, (done + weight) / total)
            done += weight

    def stage(self, name: str) -> ProgressFn:
        lo, hi = self._spans[name]
        return lambda f: self._progress(lo + (hi - lo) * max(0.0, min(f, 1.0)))

    def done(self, name: str) -> None:
        self._progress(self._spans[name][1])


def _video_suffix(video: Path) -> str:
    # MP4-family containers keep their extension; anything else goes into MKV, which takes everything.
    return video.suffix if video.suffix.lower() in (".mp4", ".m4v", ".mov") else ".mkv"


def process_video(
    video: Path,
    opts: Options,
    log: LogFn = noop,
    progress: ProgressFn = noop,
    cancel: Optional[threading.Event] = None,
) -> list[Path]:
    """Translate one video. Returns the files that were written."""
    video = Path(video)
    if not video.is_file():
        raise PipelineError(f"Datei nicht gefunden: {video}")
    out_dir = Path(opts.output_dir) if opts.output_dir else video.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    ffmpeg = find_ffmpeg(need_subtitles_filter=opts.burn_video)
    # Cheap checks first, so a problem does not show up after an hour of transcribing.
    translator = make_translator(opts, log)
    translator.preflight(opts.source_lang)
    tts = make_tts(opts.tts_engine, opts.target_lang, opts.voice_gender, log) if opts.dub else None
    if tts:
        tts.preflight()

    budget = _Budget(progress, {
        "audio": 3, "transcribe": 50, "translate": 15,
        "tts": 12 if tts else 0, "dubmux": 3 if tts else 0,
        "soft": 3 if opts.soft_video else 0, "burn": 12 if opts.burn_video else 0,
    })

    cache_file = _cache_file(video, opts)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        cached = _load_transcript(cache_file)
        if cached:
            cues, src = cached
            log("Spracherkennung aus dem Zwischenspeicher geladen: Dieses Video war schon einmal so weit.")
            budget.done("audio")
            budget.done("transcribe")
        else:
            log("Extrahiere Tonspur ...")
            extract_audio(ffmpeg, video, work / "audio.wav", cancel)
            budget.done("audio")

            log("Erkenne Sprache und schreibe Text mit (das dauert je nach Länge und Modell) ...")
            cues, src = transcribe(work / "audio.wav", opts.whisper_model, opts.source_lang, opts.device,
                                   log, budget.stage("transcribe"), cancel)
            if not cues:
                raise PipelineError("In diesem Video wurde keine Sprache erkannt.")
            _save_transcript(cache_file, cues, src)
        log(f"{len(cues)} Textabschnitte erkannt.")

        if src == opts.target_lang:
            log("Das Video ist bereits in der Zielsprache - es wird nicht übersetzt.")
            translated = [c.text for c in cues]
            if tts:
                log("Vertonung übersprungen: Die Sprache im Video ist schon die Zielsprache.")
                tts = None
        else:
            log(f"Übersetze {language_label(src)} -> {language_label(opts.target_lang)} ...")
            translated = translator.translate([c.text for c in cues], src, budget.stage("translate"), cancel)
        budget.done("translate")
        final = [Cue(c.start, c.end, t, original=c.text) for c, t in zip(cues, translated)]

        written: list[Path] = []
        srt_path = unique_path(out_dir / f"{video.stem}.{opts.target_lang}.srt")
        srt_path.write_text(build_srt(final, opts.bilingual), encoding="utf-8")
        written.append(srt_path)
        log(f"Untertitel gespeichert: {srt_path}")

        duration = probe_duration(ffmpeg, video)
        if tts:
            log("Spreche die Übersetzung ein ...")
            dub_wav = work / "dub.wav"
            silent = build_dub_track(ffmpeg, final, tts, duration or 0.0, work, dub_wav, log,
                                     budget.stage("tts"), cancel)
            if silent:
                log(f"Hinweis: {silent} Zeile(n) blieben stumm.")
            budget.done("tts")
            out = unique_path(out_dir / f"{video.stem}.{opts.target_lang}.vertont{_video_suffix(video)}")
            log("Erzeuge Video mit der gesprochenen Übersetzung ...")
            mux_dub(ffmpeg, video, dub_wav, out, opts.original_audio, opts.target_lang, duration,
                    budget.stage("dubmux"), cancel)
            written.append(out)
            log(f"Video gespeichert: {out}")

    if opts.soft_video:
        out = unique_path(out_dir / f"{video.stem}.{opts.target_lang}{_video_suffix(video)}")
        log("Erzeuge Video mit Untertitel-Spur ...")
        embed_soft_subtitles(ffmpeg, video, srt_path, out, opts.target_lang, duration, budget.stage("soft"), cancel)
        written.append(out)
        log(f"Video gespeichert: {out}")
    if opts.burn_video:
        out = unique_path(out_dir / f"{video.stem}.{opts.target_lang}.eingebrannt.mp4")
        log("Brenne Untertitel ins Bild (neu kodieren, das kann dauern) ...")
        burn_subtitles(ffmpeg, video, srt_path, out, duration, budget.stage("burn"), cancel)
        written.append(out)
        log(f"Video gespeichert: {out}")
    progress(1.0)
    return written
