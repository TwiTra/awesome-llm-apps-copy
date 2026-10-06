"""Offline tests for dubbing and the pipeline wiring: run with `python -m unittest` from this folder."""

import subprocess
import tempfile
import threading
import unittest
import wave
from pathlib import Path
from unittest import mock

import numpy as np

import core
import dubbing
import pipeline
from core import Cue


def write_tone(path: Path, seconds: float, rate: int = 22050) -> None:
    t = np.arange(int(seconds * rate)) / rate
    samples = (0.5 * np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(samples.tobytes())


class FakeTts:
    """Speaks every line as a tone of the given length (seconds, one per line)."""

    def __init__(self, lengths):
        self.lengths = lengths
        self.preflighted = False

    def preflight(self):
        self.preflighted = True

    def synthesize_all(self, texts, work_dir, progress, cancel):
        out = []
        for i, text in enumerate(texts):
            if not text.strip():
                out.append(None)
                continue
            path = Path(work_dir) / f"fake_{i}.wav"
            write_tone(path, self.lengths[i])
            out.append(path)
        progress(1.0)
        return out


def load(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)


def loud(track: np.ndarray, start: float, end: float) -> bool:
    window = track[int(start * dubbing.DUB_RATE):int(end * dubbing.DUB_RATE)].astype(np.float64)
    return float(np.sqrt(np.mean(window ** 2))) > 3000


class PlanClipTests(unittest.TestCase):
    def test_fits_without_speedup(self):
        self.assertEqual(dubbing.plan_clip(1.0, 5.0, 2.0, cursor=0.0), (1.0, 1.0))

    def test_never_slowed_down(self):
        self.assertEqual(dubbing.plan_clip(1.0, 10.0, 0.5, cursor=0.0)[1], 1.0)

    def test_too_long_is_sped_up_to_fit(self):
        start, rate = dubbing.plan_clip(0.0, 2.0, 2.4, cursor=0.0)
        self.assertEqual(start, 0.0)
        self.assertAlmostEqual(rate, 1.2)

    def test_speedup_is_capped(self):
        _, rate = dubbing.plan_clip(0.0, 1.0, 5.0, cursor=0.0)
        self.assertEqual(rate, dubbing.MAX_SPEEDUP)

    def test_late_previous_clip_pushes_start_back(self):
        start, _ = dubbing.plan_clip(2.0, 6.0, 1.0, cursor=3.5)
        self.assertEqual(start, 3.5)

    def test_empty_clip(self):
        self.assertEqual(dubbing.plan_clip(0.0, 1.0, 0.0, cursor=0.0), (0.0, 1.0))


class VoiceTests(unittest.TestCase):
    VOICES = [
        {"ShortName": "de-DE-KatjaNeural", "Gender": "Female"},
        {"ShortName": "de-DE-ConradNeural", "Gender": "Male"},
        {"ShortName": "de-AT-IngridNeural", "Gender": "Female"},
        {"ShortName": "de-DE-SeraphinaMultilingualNeural", "Gender": "Female"},
    ]

    def test_preferred_voice(self):
        self.assertEqual(dubbing.pick_edge_voice(self.VOICES, "de", "female"), "de-DE-KatjaNeural")
        self.assertEqual(dubbing.pick_edge_voice(self.VOICES, "de", "male"), "de-DE-ConradNeural")

    def test_fallback_when_preferred_voice_is_gone(self):
        voices = [v for v in self.VOICES if "Katja" not in v["ShortName"]]
        # same region first, and plain voices before multilingual ones
        self.assertEqual(dubbing.pick_edge_voice(voices, "de", "female"), "de-AT-IngridNeural")

    def test_no_voice_for_language(self):
        with self.assertRaises(core.PipelineError):
            dubbing.pick_edge_voice(self.VOICES, "fr", "female")

    def test_every_ui_language_has_a_voice_in_both_engines(self):
        self.assertEqual(set(dubbing.EDGE_VOICES), set(core.LANGUAGES))
        self.assertEqual(set(dubbing.PIPER_VOICES), set(core.LANGUAGES))
        for lang, (female, male) in dubbing.EDGE_VOICES.items():
            self.assertTrue(female.startswith(lang + "-") and male.startswith(lang + "-"))

    def test_missing_packages_give_install_hint(self):
        with mock.patch.dict("sys.modules", {"edge_tts": None}):
            with self.assertRaisesRegex(core.PipelineError, "pip install edge-tts"):
                dubbing.EdgeTts("de").preflight()
        with mock.patch.dict("sys.modules", {"piper": None}):
            with self.assertRaisesRegex(core.PipelineError, "pip install piper-tts"):
                dubbing.PiperTts("de").preflight()


def _ffmpeg():
    try:
        return core.find_ffmpeg()
    except core.PipelineError:
        return None


@unittest.skipUnless(_ffmpeg(), "ffmpeg not available")
class DubTrackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ffmpeg = _ffmpeg()

    def build(self, cues, lengths, total=10.0):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "dub.wav"
            silent = dubbing.build_dub_track(self.ffmpeg, cues, FakeTts(lengths), total, Path(tmp), out)
            return load(out), silent

    def test_clips_land_on_their_cue_times(self):
        track, silent = self.build([Cue(1, 2, "a"), Cue(5, 6, "b")], [1.0, 1.0])
        self.assertEqual(silent, 0)
        self.assertAlmostEqual(len(track) / dubbing.DUB_RATE, 10.0, delta=0.1)
        self.assertTrue(loud(track, 1.1, 1.9))
        self.assertFalse(loud(track, 2.2, 4.8))
        self.assertTrue(loud(track, 5.1, 5.9))

    def test_long_clip_is_sped_up_instead_of_overlapping(self):
        # 3 s of speech, but only 2 s until the next line: 1.35x makes it ~2.2 s, the next line is pushed back
        track, _ = self.build([Cue(0, 2, "a"), Cue(2, 4, "b")], [3.0, 1.0])
        self.assertTrue(loud(track, 0.1, 2.1))
        self.assertTrue(loud(track, 2.4, 3.1))
        self.assertFalse(loud(track, 3.4, 9.0))

    def test_empty_and_unspoken_lines_stay_silent(self):
        track, silent = self.build([Cue(1, 2, "a"), Cue(3, 4, "  ")], [1.0, 1.0])
        self.assertEqual(silent, 0)  # an empty text is not a failure
        self.assertFalse(loud(track, 3.0, 4.5))

    def test_failed_line_is_counted(self):
        class Failing(FakeTts):
            def synthesize_all(self, texts, work_dir, progress, cancel):
                return [None for _ in texts]

        with tempfile.TemporaryDirectory() as tmp:
            silent = dubbing.build_dub_track(self.ffmpeg, [Cue(0, 1, "a")], Failing([]), 5.0, Path(tmp), Path(tmp) / "d.wav")
        self.assertEqual(silent, 1)

    def test_cancel(self):
        cancel = threading.Event()
        cancel.set()
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(core.Cancelled):
                dubbing.build_dub_track(self.ffmpeg, [Cue(0, 1, "a")], FakeTts([1.0]), 5.0, Path(tmp),
                                        Path(tmp) / "d.wav", cancel=cancel)


@unittest.skipUnless(_ffmpeg(), "ffmpeg not available")
class MuxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.ffmpeg = _ffmpeg()
        cls.video = cls.dir / "clip.mp4"
        subprocess.run(
            [cls.ffmpeg, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=3",
             "-f", "lavfi", "-i", "sine=frequency=220:duration=3", "-shortest",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(cls.video)], check=True)
        cls.dub = cls.dir / "dub.wav"
        write_tone(cls.dub, 3.0, rate=dubbing.DUB_RATE)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def audio_streams(self, name):
        out = self.dir / name
        info = subprocess.run([self.ffmpeg, "-hide_banner", "-i", str(out)], capture_output=True, text=True).stderr
        return [line for line in info.splitlines() if "Audio:" in line], info

    def mux(self, mode):
        out = self.dir / f"{mode}.mp4"
        dubbing.mux_dub(self.ffmpeg, self.video, self.dub, out, mode, "de", 3.0)
        return out.name

    def test_keep_original_as_second_track(self):
        streams, info = self.audio_streams(self.mux("keep"))
        self.assertEqual(len(streams), 2)
        self.assertIn("(deu)", streams[0])
        self.assertIn("(default)", streams[0])
        self.assertNotIn("(default)", streams[1])
        self.assertIn("Originalton", info)

    def test_drop_original(self):
        streams, _ = self.audio_streams(self.mux("drop"))
        self.assertEqual(len(streams), 1)
        self.assertIn("(deu)", streams[0])

    def test_mix_keeps_one_track(self):
        streams, _ = self.audio_streams(self.mux("mix"))
        self.assertEqual(len(streams), 1)


@unittest.skipUnless(_ffmpeg(), "ffmpeg not available")
class PipelineWiringTests(unittest.TestCase):
    """process_video with Whisper, the translator and the voice replaced by fakes."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.ffmpeg = _ffmpeg()
        cls.video = cls.dir / "talk.mp4"
        subprocess.run(
            [cls.ffmpeg, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=red:s=320x240:d=4",
             "-f", "lavfi", "-i", "sine=frequency=330:duration=4", "-shortest",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(cls.video)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_pipeline(self, opts, source="en", tts=None):
        class Translator:
            def preflight(self, src):
                pass

            def translate(self, texts, src, progress=lambda f: None, cancel=None):
                progress(1.0)
                return [t.upper() for t in texts]

        cues = [Cue(0.5, 1.5, "hello"), Cue(2.0, 3.0, "world")]
        seen = []
        out_dir = self.dir / f"out_{len(list(self.dir.iterdir()))}"
        opts.output_dir = out_dir
        with mock.patch.object(pipeline, "transcribe", return_value=(cues, source)), \
                mock.patch.object(pipeline, "make_translator", return_value=Translator()), \
                mock.patch.object(pipeline, "make_tts", return_value=tts):
            files = pipeline.process_video(self.video, opts, log=lambda m: seen.append(m), progress=seen.append)
        return files, seen

    def test_subtitles_only(self):
        files, seen = self.run_pipeline(pipeline.Options(soft_video=False))
        self.assertEqual([f.name for f in files], ["talk.de.srt"])
        self.assertIn("HELLO", files[0].read_text(encoding="utf-8"))
        progress = [x for x in seen if isinstance(x, float)]
        self.assertEqual(progress[-1], 1.0)
        self.assertEqual(progress, sorted(progress))  # never goes backwards

    def test_everything_at_once(self):
        tts = FakeTts([0.8, 0.8])
        files, seen = self.run_pipeline(pipeline.Options(soft_video=True, dub=True, original_audio="drop"), tts=tts)
        self.assertTrue(tts.preflighted)
        self.assertEqual([f.name for f in files], ["talk.de.srt", "talk.de.vertont.mp4", "talk.de.mp4"])
        self.assertTrue(all(f.stat().st_size > 0 for f in files))
        progress = [x for x in seen if isinstance(x, float)]
        self.assertEqual(progress, sorted(progress))

    def test_dubbing_is_skipped_when_video_is_already_in_target_language(self):
        files, seen = self.run_pipeline(pipeline.Options(soft_video=False, dub=True), source="de", tts=FakeTts([1, 1]))
        self.assertEqual([f.name for f in files], ["talk.de.srt"])
        self.assertTrue(any("Vertonung übersprungen" in m for m in seen if isinstance(m, str)))
        self.assertIn("hello", files[0].read_text(encoding="utf-8"))  # untranslated


if __name__ == "__main__":
    unittest.main()
