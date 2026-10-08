"""Offline translation between German, Russian and English.

The model files come from the Argos Translate project (CTranslate2 + SentencePiece, trained on OPUS data)
and are used directly. That keeps PyTorch out: ctranslate2 is part of the program anyway because Whisper
needs it, and sentencepiece is tiny. Each direction is downloaded once (150-200 MB) into
~/.video_translator/models and checked against a fixed SHA-256 sum before it is used.

Russian <-> German goes through English (two hops), as there are no direct models.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import re
import shutil
import ssl
import tempfile
import threading
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlparse

from core import (
    ArgosTranslator, LogFn, PipelineError, ProgressFn, check_cancel, is_frozen, language_label, noop,
)

MODELS_DIR = Path.home() / ".video_translator" / "models"
SUPPORTED = ("de", "en", "ru")

# (from, to) -> (download URL, SHA-256 of the downloaded file)
PACKAGES: dict[tuple[str, str], tuple[str, str]] = {
    ("en", "de"): ("https://argos-net.com/v1/translate-en_de-1_3.argosmodel",
                   "6cd847f0c06c9c66013e6b0932e07fd54a6d90894659c02bf6c5247b72fb25b1"),
    ("de", "en"): ("https://argos-net.com/v1/translate-de_en-1_3.argosmodel",
                   "becc2b0011f8249fcb89be9ecb75ba0d876b1fab93c28ee6ff0420936897d637"),
    ("en", "ru"): ("https://argos-net.com/v1/translate-en_ru-1_9.argosmodel",
                   "591d743ae103752b88ffc38785c50421320f4eff93c8967e0d3d2e14d4e27811"),
    ("ru", "en"): ("https://argos-net.com/v1/translate-ru_en-1_9.argosmodel",
                   "e9ba8bf722d10a4a4c39f74289d5938fd47eac08dbe4ed0afd22d89445a5c3ac"),
}

# Only these members of the downloaded archive are used (the rest is for Argos' own sentence splitter).
_KEEP = ("model/config.json", "model/model.bin", "model/shared_vocabulary.json", "sentencepiece.model")
_CHUNK = 64  # sentences per call, so that progress and cancelling stay responsive
# The model server (behind Cloudflare) answers Python's default "Python-urllib" identifier with 403.
USER_AGENT = "VideoUebersetzer/1.0"


def route(src: str, target: str, packages=PACKAGES) -> list[tuple[str, str]]:
    """The model directions needed to get from src to target (one hop, or two via English)."""
    if (src, target) in packages:
        return [(src, target)]
    if (src, "en") in packages and ("en", target) in packages:
        return [(src, "en"), ("en", target)]
    raise PipelineError(_unsupported_message(src, target))


def _unsupported_message(src: Optional[str], target: str) -> str:
    wish = f"{language_label(src) if src else 'Videosprache'} -> {language_label(target)}"
    message = f"Die Offline-Übersetzung beherrscht nur Deutsch, Russisch und Englisch (gewünscht: {wish}). "
    if is_frozen():
        return message + "Wähle Claude als Übersetzer."
    return message + "Wähle Claude als Übersetzer oder installiere 'argostranslate' für weitere Sprachen (pip install argostranslate)."


_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+(?=[\"'«„“(\[]?[A-ZÄÖÜА-ЯЁ0-9])")


def split_sentences(text: str) -> list[str]:
    """Split on sentence ends so that long subtitle lines are translated sentence by sentence."""
    parts = [s.strip() for s in _SENTENCE_END.split(text.strip()) if s.strip()]
    return parts or [text]


# ---------------------------------------------------------------- download

def _ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context()  # the system's certificate store (on Windows: the Windows one)


def _model_folder(models_dir: Path, url: str) -> Path:
    return models_dir / Path(urlparse(url).path).stem  # e.g. translate-en_de-1_3


def _installed(folder: Path) -> bool:
    return all((folder / name).is_file() for name in _KEEP)


def _extract(archive: Path, destination: Path) -> None:
    """Unpack only the files we use, to paths we choose ourselves (nothing from the archive's own paths)."""
    found = set()
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            _, _, relative = info.filename.partition("/")  # drop the archive's top folder
            if relative in _KEEP:
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info) as source, open(target, "wb") as out:
                    shutil.copyfileobj(source, out, length=1 << 20)
                found.add(relative)
    missing = set(_KEEP) - found
    if missing:
        raise PipelineError(f"Das Sprachpaket hat ein unbekanntes Format (es fehlt: {', '.join(sorted(missing))}).")


def ensure_model(pair: tuple[str, str], models_dir: Path = MODELS_DIR, packages=PACKAGES,
                 log: LogFn = noop, cancel: Optional[threading.Event] = None) -> Path:
    """The folder of an installed model, downloading and checking it first if needed."""
    url, expected_sha = packages[pair]
    folder = _model_folder(models_dir, url)
    if _installed(folder):
        return folder

    label = f"{language_label(pair[0])} -> {language_label(pair[1])}"
    models_dir.mkdir(parents=True, exist_ok=True)
    fd, archive_name = tempfile.mkstemp(suffix=".part", dir=models_dir)
    archive = Path(archive_name)
    staging = folder.with_name(folder.name + ".tmp")
    try:
        with os.fdopen(fd, "wb") as out:
            log(f"Lade Übersetzungsmodell {label} (einmalig, 150-200 MB) ...")
            digest = hashlib.sha256()
            try:
                request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(request, context=_ssl_context(), timeout=60) as response:
                    total = int(response.headers.get("Content-Length") or 0)
                    done, next_report = 0, 0.1
                    while chunk := response.read(1 << 20):
                        check_cancel(cancel)
                        out.write(chunk)
                        digest.update(chunk)
                        done += len(chunk)
                        if total and done / total >= next_report:
                            log(f"  {int(done / total * 100)} % geladen")
                            next_report = (int(done / total * 10) + 1) / 10
            except (urllib.error.URLError, OSError, TimeoutError) as e:
                raise PipelineError(
                    f"Das Übersetzungsmodell {label} konnte nicht geladen werden ({e}). "
                    "Besteht eine Internetverbindung? Es wird nur beim ersten Mal gebraucht."
                ) from e
        if digest.hexdigest() != expected_sha:
            raise PipelineError(
                f"Das Übersetzungsmodell {label} ist beschädigt oder wurde verändert (Prüfsumme stimmt nicht). "
                "Bitte noch einmal versuchen."
            )
        shutil.rmtree(staging, ignore_errors=True)
        _extract(archive, staging)
        shutil.rmtree(folder, ignore_errors=True)
        os.replace(staging, folder)  # the folder is either complete or not there
    finally:
        archive.unlink(missing_ok=True)
        shutil.rmtree(staging, ignore_errors=True)
    return folder


# ---------------------------------------------------------------- translating

class _Engine:
    """One direction: SentencePiece for the text pieces, CTranslate2 for the translation itself."""

    def __init__(self, folder: Path):
        try:
            import ctranslate2
            import sentencepiece
        except ImportError as e:
            raise PipelineError(f"Für die Offline-Übersetzung fehlt ein Paket ({e.name}).") from e
        self.pieces = sentencepiece.SentencePieceProcessor(model_file=str(folder / "sentencepiece.model"))
        self.translator = ctranslate2.Translator(
            str(folder / "model"), device="cpu", compute_type="auto", inter_threads=1,
            intra_threads=max(1, min(8, os.cpu_count() or 4)),
        )

    def translate(self, sentences: list[str]) -> list[str]:
        tokens = [self.pieces.encode(s, out_type=str) for s in sentences]
        results = self.translator.translate_batch(
            tokens, beam_size=4, length_penalty=0.2, replace_unknowns=True, max_batch_size=1024, batch_type="tokens",
        )
        return [self.pieces.decode_pieces(r.hypotheses[0]).strip() for r in results]


EngineFactory = Callable[[Path], "_Engine"]


class LocalTranslator:
    """German, Russian and English, in every direction between them."""

    def __init__(self, target: str, log: LogFn = noop, models_dir: Path = MODELS_DIR, packages=PACKAGES,
                 engine_factory: EngineFactory = _Engine):
        self.target, self.log = target, log
        self.models_dir, self.packages, self.engine_factory = Path(models_dir), packages, engine_factory

    def _folders(self, src: str, cancel=None) -> list[tuple[tuple[str, str], Path]]:
        return [(pair, ensure_model(pair, self.models_dir, self.packages, self.log, cancel))
                for pair in route(src, self.target, self.packages)]

    def preflight(self, src: Optional[str]) -> None:
        if src:  # fetch the models now, not after an hour of speech recognition
            self._folders(src)

    def translate(self, texts: list[str], src: Optional[str], progress: ProgressFn = noop,
                  cancel: Optional[threading.Event] = None) -> list[str]:
        if not src:
            raise PipelineError("Die Sprache im Video konnte nicht bestimmt werden.")
        hops = self._folders(src, cancel)
        current = list(texts)
        for index, (_pair, folder) in enumerate(hops):
            engine = self.engine_factory(folder)
            current = self._hop(engine, current, lambda f, i=index: progress((i + f) / len(hops)), cancel)
            del engine  # frees the model before the next one is loaded
        return current

    @staticmethod
    def _hop(engine, texts: list[str], progress: ProgressFn, cancel) -> list[str]:
        # Flatten to sentences, translate in chunks, put the lines back together.
        owners: list[int] = []
        sentences: list[str] = []
        for i, text in enumerate(texts):
            for sentence in split_sentences(text):
                owners.append(i)
                sentences.append(sentence)
        translated: list[str] = []
        for start in range(0, len(sentences), _CHUNK):
            check_cancel(cancel)
            chunk = sentences[start:start + _CHUNK]
            speakable = [s for s in chunk if re.search(r"\w", s)]  # "♪" or "..." stay as they are
            done = iter(engine.translate(speakable)) if speakable else iter(())
            translated.extend(next(done) if re.search(r"\w", s) else s for s in chunk)
            progress(min((start + _CHUNK) / len(sentences), 1.0))
        lines: list[list[str]] = [[] for _ in texts]
        for owner, sentence in zip(owners, translated):
            lines[owner].append(sentence)
        return [" ".join(parts).strip() or original for parts, original in zip(lines, texts)]


class OfflineTranslator:
    """The built-in models for German/Russian/English; for other languages Argos Translate, if installed.

    Argos is only available in the Python setup (it needs PyTorch), never in the packaged .exe."""

    def __init__(self, target: str, log: LogFn = noop, local: Optional[LocalTranslator] = None, argos=None):
        self.target, self.log = target, log
        self.local = local or LocalTranslator(target, log)
        self._argos = argos

    def _argos_translator(self):
        if self._argos is None and not is_frozen() and importlib.util.find_spec("argostranslate"):
            self._argos = ArgosTranslator(self.target, self.log)
        return self._argos

    def _pick(self, src: Optional[str]):
        if self.target in SUPPORTED and src in SUPPORTED:
            return self.local
        argos = self._argos_translator()
        if argos is None:
            raise PipelineError(_unsupported_message(src, self.target))
        return argos

    def preflight(self, src: Optional[str]) -> None:
        if src is None:
            # Language still unknown (automatic detection): only the target can be judged now.
            if self.target not in SUPPORTED and self._argos_translator() is None:
                raise PipelineError(_unsupported_message(None, self.target))
            return
        self._pick(src).preflight(src)

    def translate(self, texts: list[str], src: Optional[str], progress: ProgressFn = noop,
                  cancel: Optional[threading.Event] = None) -> list[str]:
        return self._pick(src).translate(texts, src, progress, cancel)
