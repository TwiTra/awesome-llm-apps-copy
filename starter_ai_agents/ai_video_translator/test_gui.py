"""Tests that really click through the window. They need tkinter and a display, and skip without them."""

import sys
import time
import unittest
from pathlib import Path
from unittest import mock

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    import app
    import core
except ImportError as e:  # no tkinter installed
    raise unittest.SkipTest(f"tkinter not available: {e}")


def make_app():
    try:
        return app.App()
    except tk.TclError as e:
        raise unittest.SkipTest(f"no display available: {e}")


def walk(widget):
    yield widget
    for child in widget.winfo_children():
        yield from walk(child)


class WindowTests(unittest.TestCase):
    def setUp(self):
        self.settings = mock.patch.object(app, "SETTINGS_FILE", Path("nonexistent-dir") / "settings.json")
        self.settings.start()
        self.addCleanup(self.settings.stop)
        self.app = make_app()
        self.addCleanup(self.destroy_app)
        self.timers = []

    def destroy_app(self):
        for timer in getattr(self, "timers", []):
            try:
                self.app.after_cancel(timer)
            except tk.TclError:
                pass
        try:
            self.app.destroy()
        except tk.TclError:  # a test already closed it
            pass

    def test_no_accidental_override_of_tkinter_internals(self):
        """tkinter's own dialogs call methods such as `_options` on the window; shadowing one breaks them."""
        own = {name for name in vars(app.App) if not (name.startswith("__") and name.endswith("__"))}
        clashes = {name for name in own if hasattr(tk.Tk, name)}
        self.assertEqual(clashes, {"report_callback_exception", "destroy"})  # the deliberate overrides

    def dismiss_tk_dialogs_soon(self):
        """The Tk-drawn file dialogs (Linux) block until closed; close them from a timer."""
        def close():
            for name in (".__tk_filedialog", ".__tk_choosedir"):
                try:
                    self.app.tk.call("destroy", name)
                except tk.TclError:
                    pass
        for delay in (300, 700, 1200):
            self.timers.append(self.app.after(delay, close))

    def test_file_dialog_buttons_open_real_dialogs(self):
        if not sys.platform.startswith("linux"):
            self.skipTest("native file dialogs cannot be closed from a test")
        self.dismiss_tk_dialogs_soon()
        self.app._add_videos()  # raised "TypeError: App._options() takes 1 positional argument" before the fix
        self.dismiss_tk_dialogs_soon()
        self.app._choose_out_dir()
        self.assertEqual(self.app.videos, [])

    def test_every_button_can_be_clicked(self):
        self.dismiss_tk_dialogs_soon()
        buttons = [w for w in walk(self.app) if isinstance(w, (ttk.Button, ttk.Checkbutton, ttk.Radiobutton))]
        self.assertGreater(len(buttons), 8)
        started = []
        with mock.patch.object(messagebox, "showinfo") as info, \
                mock.patch.object(app, "process_video", side_effect=lambda *a, **k: started.append(a)), \
                mock.patch.object(filedialog, "askopenfilenames", return_value=("a.mp4", "b.mkv")), \
                mock.patch.object(filedialog, "askdirectory", return_value="/some/where"):
            for button in buttons:
                if str(button.cget("state")) != "disabled":
                    button.invoke()
        info.assert_called()  # "Übersetzen" with no video asked for one
        self.assertEqual(self.app.out_dir.get(), "/some/where")

    def test_adding_and_removing_videos(self):
        with mock.patch.object(filedialog, "askopenfilenames", return_value=("a.mp4", "b.mkv", "a.mp4")):
            self.app._add_videos()
        self.assertEqual([p.name for p in self.app.videos], ["a.mp4", "b.mkv"])
        self.app.listbox.selection_set(0)
        self.app._remove_videos()
        self.assertEqual([p.name for p in self.app.videos], ["b.mkv"])
        self.app._clear_videos()
        self.assertEqual(self.app.videos, [])

    def test_translate_runs_in_a_worker_and_reports_errors(self):
        def fake(video, opts, log, progress, cancel):
            log("working on " + video.name)
            progress(0.5)
            if video.name.startswith("bad"):
                raise core.PipelineError("kaputt")

        self.app.videos = [Path("ok.mp4"), Path("bad.mp4")]
        with mock.patch.object(app, "process_video", side_effect=fake):
            self.app._start()
            deadline = time.time() + 10
            while str(self.app.start_btn.cget("state")) == "disabled" and time.time() < deadline:
                self.app.update()
                time.sleep(0.02)
        log = self.app.log.get("1.0", "end")
        self.assertIn("working on ok.mp4", log)
        self.assertIn("FEHLER: kaputt", log)
        self.assertIn("1 Video(s) mit Fehler", log)
        self.assertEqual(str(self.app.start_btn.cget("state")), "normal")

    def test_options_follow_the_widgets(self):
        self.app.dub.set(True)
        self.app.tts_engine.set("edge")
        self.app.voice.set(app.GENDER_LABELS["male"])
        self.app.original.set(app.ORIGINAL_LABELS["drop"])
        self.app.target.set(app.language_label("fr"))
        opts = self.app._build_options()
        self.assertEqual((opts.dub, opts.voice_gender, opts.original_audio, opts.target_lang),
                         (True, "male", "drop", "fr"))

    def test_packaged_build_keeps_offline_translation_but_greys_out_the_offline_voice(self):
        self.app.destroy()
        with mock.patch.object(app, "is_frozen", return_value=True):
            frozen = make_app()
            try:
                frozen.backend.set("offline")
                frozen.tts_engine.set("piper")
                frozen._refresh_states()
                self.assertEqual(frozen.backend.get(), "offline")  # built into the .exe
                self.assertEqual(str(frozen.offline_radio.cget("state")), "normal")
                self.assertEqual(frozen.tts_engine.get(), "edge")  # Piper is not part of the .exe
                self.assertEqual(str(frozen.piper_radio.cget("state")), "disabled")
            finally:
                frozen.destroy()
        self.app = make_app()  # the cleanup destroys whatever self.app is now

    def test_old_saved_backend_name_still_works(self):
        self.app.destroy()
        with mock.patch.object(app, "load_settings", return_value={"backend": "argos"}):
            old = make_app()
        try:
            self.assertEqual(old.backend.get(), "offline")
            self.assertEqual(old._build_options().backend, "offline")
        finally:
            old.destroy()
        self.app = make_app()


if __name__ == "__main__":
    unittest.main()
