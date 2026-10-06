"""Command line interface: python cli.py video.mp4 --to de"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core import (
    DEFAULT_CLAUDE_MODEL, LANGUAGES, WHISPER_MODELS, Options, PipelineError, process_video,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Übersetzt Videos: Untertitel (.srt) und optional ein Video mit Untertiteln.")
    p.add_argument("videos", nargs="+", type=Path, help="ein oder mehrere Videos")
    p.add_argument("--to", dest="target", default="de", choices=sorted(LANGUAGES), help="Zielsprache (Standard: de)")
    p.add_argument("--from", dest="source", default=None, choices=sorted(LANGUAGES),
                   help="Sprache im Video (Standard: automatisch erkennen)")
    p.add_argument("--backend", choices=["claude", "argos"], default="claude",
                   help="claude = beste Qualität (API-Schlüssel nötig), argos = kostenlos und offline")
    p.add_argument("--claude-model", default=DEFAULT_CLAUDE_MODEL)
    p.add_argument("--api-key", default="", help="Anthropic-API-Schlüssel (sonst ANTHROPIC_API_KEY)")
    p.add_argument("--whisper", dest="whisper_model", default="small", choices=WHISPER_MODELS,
                   help="Whisper-Modell: größer = genauer, aber langsamer")
    p.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    p.add_argument("--bilingual", action="store_true", help="Originaltext unter der Übersetzung anzeigen")
    p.add_argument("--no-soft-video", dest="soft_video", action="store_false",
                   help="kein Video mit Untertitel-Spur erzeugen (nur .srt)")
    p.add_argument("--burn", dest="burn_video", action="store_true", help="Untertitel zusätzlich ins Bild einbrennen")
    p.add_argument("--out-dir", type=Path, default=None, help="Ausgabeordner (Standard: neben dem Video)")
    args = p.parse_args(argv)

    opts = Options(
        target_lang=args.target, source_lang=args.source, backend=args.backend, api_key=args.api_key,
        claude_model=args.claude_model, whisper_model=args.whisper_model, device=args.device,
        bilingual=args.bilingual, soft_video=args.soft_video, burn_video=args.burn_video, output_dir=args.out_dir,
    )

    last_percent = -1

    def progress(fraction: float) -> None:
        nonlocal last_percent
        percent = int(fraction * 100)
        if percent != last_percent:
            last_percent = percent
            print(f"\r  {percent:3d}%", end="", flush=True)

    failed = 0
    for video in args.videos:
        print(f"\n== {video}")
        last_percent = -1
        try:
            process_video(video, opts, log=lambda msg: print(f"\r{msg}"), progress=progress)
        except Exception as e:  # keep going with the remaining videos
            failed += 1
            detail = str(e) if isinstance(e, PipelineError) else f"{type(e).__name__}: {e}"
            print(f"\nFehler: {detail}", file=sys.stderr)
    print()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
