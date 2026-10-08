"""Offline tests: run with `python -m unittest` from this folder (ffmpeg tests need ffmpeg)."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import core
from core import Cue


def fake_response(payload, stop_reason="end_turn"):
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return SimpleNamespace(stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=text)])


class FakeClient:
    """Stands in for anthropic.Anthropic; `handler(kwargs)` returns the fake response."""

    def __init__(self, handler):
        self.calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))
        self.messages = SimpleNamespace(create=self._create)
        self.models = SimpleNamespace(retrieve=lambda model: SimpleNamespace(id=model))
        self._handler = handler

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return self._handler(kwargs)


def echo_upper(kwargs):
    lines = json.loads(kwargs["messages"][0]["content"])["lines"]
    return fake_response({"translations": [{"id": l["id"], "text": l["text"].upper()} for l in lines]})


class SrtTests(unittest.TestCase):
    def test_timestamp(self):
        self.assertEqual(core.format_timestamp(0), "00:00:00,000")
        self.assertEqual(core.format_timestamp(3661.5), "01:01:01,500")

    def test_short_cue_is_untouched(self):
        cue = Cue(1.0, 3.0, "Hallo Welt")
        self.assertEqual(core.split_cue(cue), [cue])

    def test_long_cue_is_split_and_timing_is_contiguous(self):
        text = " ".join(["wort"] * 60)  # 299 characters
        parts = core.split_cue(Cue(10.0, 20.0, text))
        self.assertGreater(len(parts), 1)
        self.assertEqual(" ".join(p.text for p in parts), text)
        self.assertAlmostEqual(parts[0].start, 10.0)
        self.assertAlmostEqual(parts[-1].end, 20.0)
        for a, b in zip(parts, parts[1:]):
            self.assertAlmostEqual(a.end, b.start)
        self.assertTrue(all(len(p.text) <= 84 for p in parts))

    def test_long_duration_alone_triggers_split(self):
        parts = core.split_cue(Cue(0, 30, "ein paar Worte die sehr langsam gesprochen werden"))
        self.assertGreaterEqual(len(parts), 5)

    def test_cjk_without_spaces_is_split(self):
        parts = core.split_cue(Cue(0, 4, "これは長い日本語の文章です" * 5))
        self.assertGreater(len(parts), 1)
        self.assertEqual("".join(p.text for p in parts), "これは長い日本語の文章です" * 5)

    def test_build_srt_numbering_and_wrapping(self):
        srt = core.build_srt([Cue(0, 2, "Eins"), Cue(2, 4, "Zwei " * 12)])
        blocks = srt.strip().split("\n\n")
        self.assertEqual(blocks[0], "1\n00:00:00,000 --> 00:00:02,000\nEins")
        self.assertTrue(blocks[1].startswith("2\n00:00:02,000 --> 00:00:04,000\nZwei"))
        for line in srt.splitlines():
            self.assertLessEqual(len(line), 42 if not line.startswith("00:") else 99)

    def test_bilingual_adds_italic_original(self):
        srt = core.build_srt([Cue(0, 2, "Hallo", original="Hello")], bilingual=True)
        self.assertIn("Hallo\n<i>Hello</i>", srt)

    def test_unique_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "a.srt"
            self.assertEqual(core.unique_path(first), first)
            first.write_text("x")
            self.assertEqual(core.unique_path(first), Path(tmp) / "a (2).srt")


class ClaudeTranslatorTests(unittest.TestCase):
    def make(self, handler, model="claude-opus-5-5"):
        client = FakeClient(handler)
        return core.ClaudeTranslator("de", model, client=client, log=lambda m: None), client

    def test_translates_in_batches_and_keeps_order(self):
        tr, client = self.make(echo_upper)
        texts = [f"line {i}" for i in range(95)]
        self.assertEqual(tr.translate(texts, "en"), [t.upper() for t in texts])
        self.assertEqual(len(client.calls), 3)  # 40 + 40 + 15

    def test_request_shape_for_current_models(self):
        tr, client = self.make(echo_upper)
        tr.translate(["hi"], "en")
        call = client.calls[0]
        self.assertEqual(call["model"], "claude-opus-5-5")
        self.assertEqual(call["fallbacks"], "default")
        self.assertEqual(call["output_config"]["effort"], "low")
        self.assertEqual(call["output_config"]["format"]["type"], "json_schema")
        self.assertIn("Deutsch", call["system"])

    def test_older_model_gets_no_new_parameters(self):
        tr, client = self.make(echo_upper, model="claude-haiku-4-5")
        tr.translate(["hi"], "en")
        call = client.calls[0]
        self.assertNotIn("fallbacks", call)
        self.assertNotIn("betas", call)
        self.assertNotIn("effort", call["output_config"])

    def test_bad_batch_is_halved_until_it_works(self):
        def handler(kwargs):
            lines = json.loads(kwargs["messages"][0]["content"])["lines"]
            if len(lines) > 2:  # pretend big answers come back broken
                return fake_response("not json")
            return echo_upper(kwargs)

        tr, client = self.make(handler)
        texts = [f"l{i}" for i in range(8)]
        self.assertEqual(tr.translate(texts, "en"), [t.upper() for t in texts])

    def test_missing_ids_count_as_bad(self):
        def handler(kwargs):
            lines = json.loads(kwargs["messages"][0]["content"])["lines"]
            if len(lines) > 1:
                return fake_response({"translations": [{"id": 0, "text": "x"}]})
            return echo_upper(kwargs)

        tr, _ = self.make(handler)
        self.assertEqual(tr.translate(["a", "b", "c"], "en"), ["A", "B", "C"])

    def test_refusal_keeps_original_text(self):
        tr, _ = self.make(lambda kwargs: fake_response("", stop_reason="refusal"))
        self.assertEqual(tr.translate(["secret"], "en"), ["secret"])

    def test_missing_credentials_give_friendly_error(self):
        def handler(kwargs):
            raise TypeError('"Could not resolve authentication method. Expected one of api_key, auth_token ..."')

        tr, _ = self.make(handler)
        with self.assertRaisesRegex(core.PipelineError, "API-Schlüssel"):
            tr.translate(["hi"], "en")

    @staticmethod
    def api_error(cls, status, message, **extra):
        import anthropic
        import httpx2

        request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
        if cls is anthropic.APIConnectionError:
            return cls(request=request)
        response = httpx2.Response(status, request=request)
        return cls(message, response=response, body={"error": {"message": message}})

    def test_empty_credit_balance_is_explained(self):
        import anthropic

        error = self.api_error(anthropic.BadRequestError, 400,
                               "Your credit balance is too low to access the Anthropic API.")

        def handler(kwargs):
            raise error

        tr, _ = self.make(handler)
        with self.assertRaisesRegex(core.PipelineError, "kein Guthaben"):
            tr.translate(["hi"], "en")

    def test_other_api_problems_are_explained_or_left_alone(self):
        import anthropic

        cases = [
            (self.api_error(anthropic.RateLimitError, 429, "slow down"), "Rate-Limit"),
            (self.api_error(anthropic.PermissionDeniedError, 403, "no"), "keinen Zugriff"),
            (self.api_error(anthropic.APIConnectionError, 0, ""), "Keine Verbindung"),
        ]
        for error, expected in cases:
            tr, _ = self.make(lambda kwargs, e=error: (_ for _ in ()).throw(e))
            with self.assertRaisesRegex(core.PipelineError, expected):
                tr.translate(["hi"], "en")
        # a plain bad request (not about credit) and a server error are shown as they are
        for error in (self.api_error(anthropic.BadRequestError, 400, "max_tokens too large"),
                      self.api_error(anthropic.InternalServerError, 500, "oops")):
            tr, _ = self.make(lambda kwargs, e=error: (_ for _ in ()).throw(e))
            with self.assertRaises(type(error)):
                tr.translate(["hi"], "en")

    def test_preflight_sends_one_tiny_request(self):
        tr, client = self.make(echo_upper)
        tr.preflight("en")
        self.assertEqual(len(client.calls), 1)
        self.assertIn("Hello.", client.calls[0]["messages"][0]["content"])

    def test_preflight_catches_an_empty_balance_before_any_work(self):
        import anthropic

        error = self.api_error(anthropic.BadRequestError, 400, "Your credit balance is too low")

        def handler(kwargs):
            raise error

        tr, _ = self.make(handler)
        with self.assertRaisesRegex(core.PipelineError, "kein Guthaben"):
            tr.preflight("en")

    def test_preflight_ignores_an_odd_answer_to_the_test_line(self):
        tr, _ = self.make(lambda kwargs: fake_response("not json"))
        tr.preflight("en")  # must not raise

    def test_unrelated_type_errors_are_not_disguised(self):
        def handler(kwargs):
            raise TypeError("something else entirely")

        tr, _ = self.make(handler)
        with self.assertRaises(TypeError):
            tr.translate(["hi"], "en")

    def test_cancel(self):
        import threading

        tr, _ = self.make(echo_upper)
        cancel = threading.Event()
        cancel.set()
        with self.assertRaises(core.Cancelled):
            tr.translate(["a"], "en", cancel=cancel)


def _ffmpeg():
    try:
        return core.find_ffmpeg()
    except core.PipelineError:
        return None


@unittest.skipUnless(_ffmpeg(), "ffmpeg not available")
class FfmpegTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.ffmpeg = _ffmpeg()
        cls.video = cls.dir / "clip.mp4"
        subprocess.run(
            [cls.ffmpeg, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=2",
             "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-shortest",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(cls.video)], check=True)
        cls.srt = cls.dir / "clip.de.srt"
        cls.srt.write_text(core.build_srt([Cue(0, 1.5, "Hallo Welt")]), encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def streams(self, path):
        return subprocess.run([self.ffmpeg, "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr

    def test_duration(self):
        self.assertAlmostEqual(core.probe_duration(self.ffmpeg, self.video), 2.0, delta=0.2)

    def test_extract_audio(self):
        wav = self.dir / "a.wav"
        core.extract_audio(self.ffmpeg, self.video, wav)
        self.assertGreater(wav.stat().st_size, 1000)

    def test_video_without_audio_gives_friendly_error(self):
        silent = self.dir / "silent.mp4"
        subprocess.run([self.ffmpeg, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=red:s=64x64:d=1",
                        "-pix_fmt", "yuv420p", str(silent)], check=True)
        with self.assertRaisesRegex(core.PipelineError, "keine Tonspur"):
            core.extract_audio(self.ffmpeg, silent, self.dir / "none.wav")

    def test_soft_subtitles(self):
        out = self.dir / "soft.mp4"
        core.embed_soft_subtitles(self.ffmpeg, self.video, self.srt, out, "de", 2.0, lambda f: None, None)
        info = self.streams(out)
        self.assertIn("Subtitle: mov_text", info)
        self.assertIn("(deu)", info)

    def test_soft_subtitles_into_mkv(self):
        out = self.dir / "soft.mkv"
        core.embed_soft_subtitles(self.ffmpeg, self.video, self.srt, out, "de", 2.0, lambda f: None, None)
        self.assertIn("Subtitle:", self.streams(out))

    @unittest.skipUnless(_ffmpeg() and core._ffmpeg_has_filter(_ffmpeg(), "subtitles"), "ffmpeg without libass")
    def test_burned_subtitles_report_progress(self):
        out = self.dir / "burned.mp4"
        seen = []
        core.burn_subtitles(self.ffmpeg, self.video, self.srt, out, 2.0, seen.append, None)
        self.assertTrue(out.exists())
        self.assertTrue(seen and max(seen) > 0.5)
        self.assertNotIn("Subtitle:", self.streams(out))


if __name__ == "__main__":
    unittest.main()
