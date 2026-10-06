"""Desktop app (tkinter): pick videos, pick a language, click start."""

from __future__ import annotations

import json
import os
import queue
import re
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from core import DEFAULT_CLAUDE_MODEL, LANGUAGES, VIDEO_EXTENSIONS, Cancelled, PipelineError, language_label
from pipeline import Options, process_video

SETTINGS_FILE = Path.home() / ".video_translator.json"
AUTO = "Automatisch erkennen"
WHISPER_HINTS = {
    "tiny": "tiny (sehr schnell, ungenau)",
    "base": "base (schnell)",
    "small": "small (guter Kompromiss)",
    "medium": "medium (genau, langsam)",
    "large-v3": "large-v3 (am genauesten, braucht viel RAM/GPU)",
}


GENDER_LABELS = {"female": "Frau", "male": "Mann"}
ORIGINAL_LABELS = {
    "keep": "Als zweite Tonspur behalten (umschaltbar)",
    "mix": "Leise im Hintergrund mitlaufen lassen",
    "drop": "Entfernen",
}


def label_to_key(labels: dict[str, str], label: str, default: str) -> str:
    return next((key for key, text in labels.items() if text == label), default)


def language_code(label: str) -> str | None:
    m = re.search(r"\((\w+)\)$", label)
    return m.group(1) if m else None


def load_settings() -> dict:
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_settings(data: dict) -> None:
    try:
        SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass  # a settings file is a convenience, never a reason to fail


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Video-Übersetzer")
        self.minsize(900, 640)
        self.events: queue.Queue = queue.Queue()
        self.cancel_event = threading.Event()
        self.worker: threading.Thread | None = None
        self.videos: list[Path] = []
        saved = load_settings()

        target = saved.get("target")
        self.target = tk.StringVar(value=language_label(target if target in LANGUAGES else "de"))
        self.source = tk.StringVar(value=AUTO)
        self.backend = tk.StringVar(value=saved.get("backend", "claude"))
        self.api_key = tk.StringVar(value=os.environ.get("ANTHROPIC_API_KEY", ""))
        self.claude_model = tk.StringVar(value=saved.get("claude_model", DEFAULT_CLAUDE_MODEL))
        self.whisper = tk.StringVar(value=WHISPER_HINTS.get(saved.get("whisper"), WHISPER_HINTS["small"]))
        self.device = tk.StringVar(value=saved.get("device", "auto"))
        self.out_dir = tk.StringVar(value=saved.get("out_dir", ""))
        self.bilingual = tk.BooleanVar(value=saved.get("bilingual", False))
        self.soft_video = tk.BooleanVar(value=saved.get("soft_video", True))
        self.burn_video = tk.BooleanVar(value=saved.get("burn_video", False))
        self.dub = tk.BooleanVar(value=saved.get("dub", False))
        self.tts_engine = tk.StringVar(value=saved.get("tts_engine", "edge"))
        self.voice = tk.StringVar(value=GENDER_LABELS.get(saved.get("voice_gender"), GENDER_LABELS["female"]))
        self.original = tk.StringVar(value=ORIGINAL_LABELS.get(saved.get("original_audio"), ORIGINAL_LABELS["keep"]))

        self._build()
        self._refresh_states()
        self.after(100, self._poll)

    # ------------------------------------------------------------ layout

    def _build(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1, uniform="col")
        root.columnconfigure(1, weight=1, uniform="col")
        root.rowconfigure(3, weight=1)

        # videos
        box = ttk.LabelFrame(root, text="1. Videos", padding=8)
        box.grid(row=0, column=0, columnspan=2, sticky="ew")
        box.columnconfigure(0, weight=1)
        self.listbox = tk.Listbox(box, height=3, selectmode="extended", activestyle="none")
        self.listbox.grid(row=0, column=0, rowspan=3, sticky="ew")
        ttk.Button(box, text="Hinzufügen ...", command=self._add_videos).grid(row=0, column=1, padx=(8, 0), sticky="ew")
        ttk.Button(box, text="Entfernen", command=self._remove_videos).grid(row=1, column=1, padx=(8, 0), sticky="ew")
        ttk.Button(box, text="Leeren", command=self._clear_videos).grid(row=2, column=1, padx=(8, 0), sticky="ew")

        left = ttk.Frame(root)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=(8, 0))
        right = ttk.Frame(root)
        right.grid(row=1, column=1, sticky="nsew", padx=(6, 0), pady=(8, 0))
        for column in (left, right):
            column.columnconfigure(0, weight=1)

        # 2. languages
        box = ttk.LabelFrame(left, text="2. Sprachen", padding=8)
        box.grid(row=0, column=0, sticky="ew")
        box.columnconfigure(1, weight=1)
        labels = [language_label(c) for c in LANGUAGES]
        ttk.Label(box, text="Sprache im Video:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(box, textvariable=self.source, values=[AUTO, *labels], state="readonly").grid(
            row=0, column=1, sticky="ew", padx=(6, 0))
        ttk.Label(box, text="Übersetzen nach:").grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Combobox(box, textvariable=self.target, values=labels, state="readonly").grid(
            row=1, column=1, sticky="ew", padx=(6, 0), pady=(4, 0))

        # 3. translator
        box = ttk.LabelFrame(left, text="3. Übersetzer", padding=8)
        box.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        box.columnconfigure(1, weight=1)
        ttk.Radiobutton(box, text="Claude (beste Qualität, API-Schlüssel nötig)", value="claude",
                        variable=self.backend, command=self._refresh_states).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(box, text="API-Schlüssel:").grid(row=1, column=0, sticky="w", padx=(20, 6))
        self.key_entry = ttk.Entry(box, textvariable=self.api_key, show="*")
        self.key_entry.grid(row=1, column=1, sticky="ew")
        ttk.Label(box, text="Modell:").grid(row=2, column=0, sticky="w", padx=(20, 6))
        self.model_entry = ttk.Entry(box, textvariable=self.claude_model)
        self.model_entry.grid(row=2, column=1, sticky="ew")
        ttk.Radiobutton(box, text="Offline (kostenlos, Argos Translate - einfachere Qualität)", value="argos",
                        variable=self.backend, command=self._refresh_states).grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))

        # 4. speech recognition
        box = ttk.LabelFrame(left, text="4. Spracherkennung (läuft lokal)", padding=8)
        box.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        box.columnconfigure(1, weight=1)
        ttk.Label(box, text="Whisper-Modell:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(box, textvariable=self.whisper, values=list(WHISPER_HINTS.values()), state="readonly").grid(
            row=0, column=1, sticky="ew", padx=(6, 0))
        ttk.Label(box, text="Gerät:").grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Combobox(box, textvariable=self.device, values=["auto", "cpu", "cuda"], state="readonly").grid(
            row=1, column=1, sticky="ew", padx=(6, 0), pady=(4, 0))

        # 5. subtitles
        box = ttk.LabelFrame(right, text="5. Untertitel", padding=8)
        box.grid(row=0, column=0, sticky="ew")
        box.columnconfigure(1, weight=1)
        ttk.Label(box, text="Die Untertitel-Datei (.srt) wird immer erstellt.").grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Checkbutton(box, text="Zweisprachig (Original unter der Übersetzung)", variable=self.bilingual).grid(
            row=1, column=0, columnspan=3, sticky="w")
        ttk.Checkbutton(box, text="Video mit abschaltbarer Untertitel-Spur (schnell)",
                        variable=self.soft_video).grid(row=2, column=0, columnspan=3, sticky="w")
        ttk.Checkbutton(box, text="Video mit eingebrannten Untertiteln (langsam)",
                        variable=self.burn_video).grid(row=3, column=0, columnspan=3, sticky="w")

        # 6. dubbing
        box = ttk.LabelFrame(right, text="6. Sprachausgabe (Vertonung)", padding=8)
        box.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        box.columnconfigure(1, weight=1)
        ttk.Checkbutton(box, text="Übersetzung von einer Computerstimme sprechen lassen\n(zusätzliches Video mit neuer Tonspur)",
                        variable=self.dub, command=self._refresh_states).grid(row=0, column=0, columnspan=2, sticky="w")
        self.dub_widgets: list[ttk.Widget] = []
        engines = [("Microsoft-Stimmen (sehr natürlich, braucht Internet)", "edge"),
                   ("Offline-Stimme (Piper, einfacher)", "piper")]
        for row, (text, value) in enumerate(engines, start=1):
            radio = ttk.Radiobutton(box, text=text, value=value, variable=self.tts_engine, command=self._refresh_states)
            radio.grid(row=row, column=0, columnspan=2, sticky="w", padx=(20, 0))
            self.dub_widgets.append(radio)
        ttk.Label(box, text="Sprecher:").grid(row=3, column=0, sticky="w", padx=(20, 6), pady=(4, 0))
        self.voice_box = ttk.Combobox(box, textvariable=self.voice, values=list(GENDER_LABELS.values()), state="readonly")
        self.voice_box.grid(row=3, column=1, sticky="ew", pady=(4, 0))
        ttk.Label(box, text="Originalton:").grid(row=4, column=0, sticky="w", padx=(20, 6), pady=(4, 0))
        self.original_box = ttk.Combobox(box, textvariable=self.original, values=list(ORIGINAL_LABELS.values()), state="readonly")
        self.original_box.grid(row=4, column=1, sticky="ew", pady=(4, 0))

        # output folder
        box = ttk.Frame(root)
        box.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        box.columnconfigure(1, weight=1)
        ttk.Label(box, text="Speichern in:").grid(row=0, column=0, sticky="w")
        ttk.Entry(box, textvariable=self.out_dir).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(box, text="Ordner ...", command=self._choose_out_dir).grid(row=0, column=2)
        ttk.Label(box, text="(leer = neben dem Video)", foreground="gray").grid(row=0, column=3, padx=(6, 0))

        # log (stretches), then progress and buttons
        self.log = scrolledtext.ScrolledText(root, height=7, state="disabled", wrap="word")
        self.log.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        run = ttk.Frame(root)
        run.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        run.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(run, maximum=1.0)
        self.progress.grid(row=0, column=0, sticky="ew")
        self.start_btn = ttk.Button(run, text="Übersetzen", command=self._start)
        self.start_btn.grid(row=0, column=1, padx=(8, 0))
        self.cancel_btn = ttk.Button(run, text="Abbrechen", command=self._cancel, state="disabled")
        self.cancel_btn.grid(row=0, column=2, padx=(6, 0))

    # ------------------------------------------------------------ actions

    def _refresh_states(self) -> None:
        claude = "normal" if self.backend.get() == "claude" else "disabled"
        self.key_entry.configure(state=claude)
        self.model_entry.configure(state=claude)
        dub = self.dub.get()
        for widget in self.dub_widgets:
            widget.configure(state="normal" if dub else "disabled")
        self.voice_box.configure(state="readonly" if dub and self.tts_engine.get() == "edge" else "disabled")
        self.original_box.configure(state="readonly" if dub else "disabled")

    def _add_videos(self) -> None:
        patterns = " ".join(f"*{ext}" for ext in VIDEO_EXTENSIONS)
        paths = filedialog.askopenfilenames(
            title="Videos auswählen", filetypes=[("Videos", patterns), ("Alle Dateien", "*.*")])
        for path in map(Path, paths):
            if path not in self.videos:
                self.videos.append(path)
                self.listbox.insert("end", path.name)

    def _remove_videos(self) -> None:
        for index in reversed(self.listbox.curselection()):
            self.listbox.delete(index)
            del self.videos[index]

    def _clear_videos(self) -> None:
        self.listbox.delete(0, "end")
        self.videos.clear()

    def _choose_out_dir(self) -> None:
        folder = filedialog.askdirectory(title="Ausgabeordner wählen")
        if folder:
            self.out_dir.set(folder)

    def _whisper_choice(self) -> str:
        for name, hint in WHISPER_HINTS.items():
            if hint == self.whisper.get():
                return name
        return "small"

    def _options(self) -> Options:
        return Options(
            target_lang=language_code(self.target.get()) or "de",
            source_lang=language_code(self.source.get()),
            backend=self.backend.get(),
            api_key=self.api_key.get().strip(),
            claude_model=self.claude_model.get().strip() or DEFAULT_CLAUDE_MODEL,
            whisper_model=self._whisper_choice(),
            device=self.device.get(),
            bilingual=self.bilingual.get(),
            soft_video=self.soft_video.get(),
            burn_video=self.burn_video.get(),
            dub=self.dub.get(),
            tts_engine=self.tts_engine.get(),
            voice_gender=label_to_key(GENDER_LABELS, self.voice.get(), "female"),
            original_audio=label_to_key(ORIGINAL_LABELS, self.original.get(), "keep"),
            output_dir=Path(self.out_dir.get()) if self.out_dir.get().strip() else None,
        )

    def _start(self) -> None:
        if not self.videos:
            messagebox.showinfo("Video-Übersetzer", "Bitte zuerst mindestens ein Video hinzufügen.")
            return
        opts = self._options()
        # The API key is deliberately not saved; use the ANTHROPIC_API_KEY environment variable for that.
        save_settings({
            "target": opts.target_lang, "backend": opts.backend, "claude_model": opts.claude_model,
            "whisper": opts.whisper_model, "device": opts.device, "out_dir": self.out_dir.get().strip(),
            "bilingual": opts.bilingual, "soft_video": opts.soft_video, "burn_video": opts.burn_video,
            "dub": opts.dub, "tts_engine": opts.tts_engine, "voice_gender": opts.voice_gender,
            "original_audio": opts.original_audio,
        })
        self.cancel_event.clear()
        self.progress["value"] = 0
        self.start_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.worker = threading.Thread(target=self._run, args=(list(self.videos), opts), daemon=True)
        self.worker.start()

    def _cancel(self) -> None:
        self.cancel_event.set()
        self.cancel_btn.configure(state="disabled")
        self._append_log("Abbruch angefordert ...")

    # ------------------------------------------------------------ worker thread

    def _run(self, videos: list[Path], opts: Options) -> None:
        """Runs in a worker thread; talks to the UI only through the event queue."""
        total = len(videos)
        failures = 0
        try:
            for i, video in enumerate(videos):
                self.events.put(("log", f"\n=== {video.name} ({i + 1}/{total}) ==="))
                try:
                    process_video(
                        video, opts,
                        log=lambda msg: self.events.put(("log", msg)),
                        progress=lambda f, i=i: self.events.put(("progress", (i + f) / total)),
                        cancel=self.cancel_event,
                    )
                except Cancelled:
                    self.events.put(("log", "Abgebrochen."))
                    break
                except Exception as e:  # show the problem, then carry on with the next video
                    failures += 1
                    detail = str(e) if isinstance(e, PipelineError) else f"{type(e).__name__}: {e}"
                    self.events.put(("log", f"FEHLER: {detail}"))
            else:
                done = "Fertig." if not failures else f"Fertig, aber {failures} Video(s) mit Fehler."
                self.events.put(("log", done))
        finally:
            self.events.put(("finished", failures))

    def _poll(self) -> None:
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "log":
                    self._append_log(value)
                elif kind == "progress":
                    self.progress["value"] = value
                elif kind == "finished":
                    self.start_btn.configure(state="normal")
                    self.cancel_btn.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()
