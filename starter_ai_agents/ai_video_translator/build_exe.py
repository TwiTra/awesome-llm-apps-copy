"""Build the stand-alone program with PyInstaller (run this on Windows to get a .exe).

    pip install -r requirements.txt pyinstaller
    python build_exe.py                     # folder dist/VideoUebersetzer/  (starts fast)
    python build_exe.py --onefile           # single dist/VideoUebersetzer.exe  (starts slower)
    python build_exe.py --test --zip        # also run the self-test on the result and zip the folder

Offline translation for German/Russian/English is built in (offline.py: ctranslate2 + sentencepiece, the
models are downloaded on first use). Two extras are left out on purpose: argostranslate (needs PyTorch) and
piper-tts (GPL), and nothing can be pip-installed into a packaged program. The window greys out the offline voice.
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
import tempfile
from importlib.util import find_spec
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAME = "VideoUebersetzer"

# Packages whose data files or native libraries PyInstaller's import scan does not find on its own
# (Whisper's VAD model, ctranslate2/onnxruntime/av libraries, the bundled ffmpeg, TLS certificates).
COLLECT_ALL = ["faster_whisper", "ctranslate2", "sentencepiece", "onnxruntime", "av", "imageio_ffmpeg", "certifi",
               "anthropic", "httpx2", "edge_tts", "hf_xet"]
EXCLUDE = ["torch", "matplotlib", "pytest", "IPython", "scipy", "pandas", "argostranslate", "piper"]


def build(onefile: bool) -> Path:
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--name", NAME,
           "--distpath", str(HERE / "dist"), "--workpath", str(HERE / "build"), "--specpath", str(HERE / "build"),
           "--paths", str(HERE), "--hidden-import", "selftest"]
    cmd.append("--onefile" if onefile else "--onedir")
    for package in COLLECT_ALL:
        if find_spec(package):  # hf_xet is only there on some installs
            cmd += ["--collect-all", package]
    for module in EXCLUDE:
        cmd += ["--exclude-module", module]
    cmd.append(str(HERE / "app.py"))
    print(" ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=HERE)

    suffix = ".exe" if platform.system() == "Windows" else ""
    return HERE / "dist" / (f"{NAME}{suffix}" if onefile else f"{NAME}/{NAME}{suffix}")


def selftest(exe: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "selftest.txt"
        result = subprocess.run([str(exe), "--selftest", str(report)], timeout=1800)
        print(report.read_text(encoding="utf-8") if report.exists() else "(kein Bericht geschrieben)", flush=True)
        if result.returncode != 0:
            sys.exit(f"Selbsttest der gebauten Datei fehlgeschlagen (Exit-Code {result.returncode})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--onefile", action="store_true", help="one single file instead of a folder")
    parser.add_argument("--test", action="store_true", help="run the self-test on the result")
    parser.add_argument("--zip", action="store_true", help="zip the folder (not with --onefile)")
    args = parser.parse_args()

    exe = build(args.onefile)
    print(f"\nGebaut: {exe} ({exe.stat().st_size / 1e6:.0f} MB)", flush=True)
    if args.test:
        selftest(exe)
    if args.zip and not args.onefile:
        archive = shutil.make_archive(str(HERE / "dist" / f"{NAME}-{platform.system().lower()}"), "zip",
                                      HERE / "dist", NAME)
        print(f"Zip: {archive} ({Path(archive).stat().st_size / 1e6:.0f} MB)", flush=True)


if __name__ == "__main__":
    main()
