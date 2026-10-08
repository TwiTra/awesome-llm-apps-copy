"""Tests of the offline translator without any real model: fakes stand in for ctranslate2 and the download."""

import hashlib
import http.server
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import core
import offline
import pipeline


class FakeEngine:
    """Stands in for ctranslate2 + sentencepiece: tags every sentence with its direction."""

    def __init__(self, tag):
        self.tag, self.calls = tag, []

    def translate(self, sentences):
        self.calls.append(list(sentences))
        return [f"{s}<{self.tag}>" for s in sentences]


def fake_factory(log):
    def make(folder):
        tag = folder.name
        log.append(tag)
        return FakeEngine(tag)
    return make


def make_archive(path: Path, name="translate-en_de-1_3", skip=(), extra=()):
    """A package shaped like Argos', including files we must not use."""
    with zipfile.ZipFile(path, "w") as z:
        for member, data in {
            "README.md": b"readme", "metadata.json": b"{}", "sentencepiece.model": b"spm",
            "model/config.json": b"{}", "model/model.bin": b"weights", "model/shared_vocabulary.json": b"[]",
            "stanza/resources.json": b"{}", "stanza/en/tokenize/ewt.pt": b"stanza",
        }.items():
            if member not in skip:
                z.writestr(f"{name}/{member}", data)
        for member, data in extra:
            z.writestr(member, data)
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RouteTests(unittest.TestCase):
    def test_direct_and_through_english(self):
        self.assertEqual(offline.route("en", "de"), [("en", "de")])
        self.assertEqual(offline.route("ru", "en"), [("ru", "en")])
        self.assertEqual(offline.route("de", "ru"), [("de", "en"), ("en", "ru")])
        self.assertEqual(offline.route("ru", "de"), [("ru", "en"), ("en", "de")])

    def test_other_languages_are_refused_with_a_useful_message(self):
        with self.assertRaisesRegex(core.PipelineError, "Deutsch, Russisch und Englisch"):
            offline.route("fr", "de")

    def test_all_four_packages_are_pinned(self):
        self.assertEqual(set(offline.PACKAGES), {("en", "de"), ("de", "en"), ("en", "ru"), ("ru", "en")})
        for url, sha in offline.PACKAGES.values():
            self.assertTrue(url.startswith("https://"))
            self.assertRegex(sha, r"^[0-9a-f]{64}$")


class SentenceTests(unittest.TestCase):
    def test_splits_at_sentence_ends_only_before_a_new_sentence(self):
        self.assertEqual(offline.split_sentences("Hello there. How are you? Fine!"),
                         ["Hello there.", "How are you?", "Fine!"])
        self.assertEqual(offline.split_sentences("Das kostet 3.5 Millionen, z.B. heute."), ["Das kostet 3.5 Millionen, z.B. heute."])
        self.assertEqual(offline.split_sentences("Привет. Как дела?"), ["Привет.", "Как дела?"])
        self.assertEqual(offline.split_sentences("  one line  "), ["one line"])
        self.assertEqual(offline.split_sentences("..."), ["..."])


class LocalTranslatorTests(unittest.TestCase):
    def make(self, target, log=None):
        log = log if log is not None else []
        folders = {pair: Path(f"{pair[0]}-{pair[1]}") for pair in offline.PACKAGES}
        translator = offline.LocalTranslator(target, engine_factory=fake_factory(log))
        translator._folders = lambda src, cancel=None: [(p, folders[p]) for p in offline.route(src, target)]
        return translator, log

    def test_lines_are_split_translated_and_put_back_together(self):
        tr, _ = self.make("de")
        out = tr.translate(["One. Two!", "Three", "♪"], "en")
        self.assertEqual(out, ["One.<en-de> Two!<en-de>", "Three<en-de>", "♪"])

    def test_russian_to_german_goes_through_english_in_order(self):
        tr, log = self.make("de")
        out = tr.translate(["Привет"], "ru")
        self.assertEqual(log, ["ru-en", "en-de"])
        self.assertEqual(out, ["Привет<ru-en><en-de>"])

    def test_progress_never_goes_backwards_and_ends_at_one(self):
        tr, _ = self.make("ru")
        seen = []
        tr.translate([f"Line {i}." for i in range(150)], "de", progress=seen.append)  # two hops, three chunks each
        self.assertEqual(seen, sorted(seen))
        self.assertAlmostEqual(seen[-1], 1.0)

    def test_cancel(self):
        tr, _ = self.make("de")
        cancel = threading.Event()
        cancel.set()
        with self.assertRaises(core.Cancelled):
            tr.translate(["x"], "en", cancel=cancel)

    def test_unknown_source_language_is_reported(self):
        tr, _ = self.make("de")
        with self.assertRaises(core.PipelineError):
            tr.translate(["x"], None)

    def test_empty_translation_keeps_the_original_line(self):
        class Silent(FakeEngine):
            def translate(self, sentences):
                return ["" for _ in sentences]

        tr = offline.LocalTranslator("de", engine_factory=lambda folder: Silent("x"))
        tr._folders = lambda src, cancel=None: [(("en", "de"), Path("en-de"))]
        self.assertEqual(tr.translate(["Keep me"], "en"), ["Keep me"])


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.models = self.dir / "models"
        self.archive = self.dir / "translate-en_de-1_3.argosmodel"

    def packages(self, sha):
        return {("en", "de"): (self.archive.as_uri(), sha)}

    def test_installs_only_the_files_we_use(self):
        sha = make_archive(self.archive)
        folder = offline.ensure_model(("en", "de"), self.models, self.packages(sha))
        self.assertEqual(folder, self.models / "translate-en_de-1_3")
        installed = sorted(str(p.relative_to(folder)).replace("\\", "/") for p in folder.rglob("*") if p.is_file())
        self.assertEqual(installed, sorted(offline._KEEP))
        self.assertEqual(sorted(p.name for p in self.models.iterdir()), ["translate-en_de-1_3"])  # no leftovers

    def test_is_not_downloaded_twice(self):
        sha = make_archive(self.archive)
        offline.ensure_model(("en", "de"), self.models, self.packages(sha))
        self.archive.unlink()  # a second download would now fail
        offline.ensure_model(("en", "de"), self.models, self.packages(sha))

    def test_wrong_checksum_installs_nothing(self):
        make_archive(self.archive)
        with self.assertRaisesRegex(core.PipelineError, "Prüfsumme"):
            offline.ensure_model(("en", "de"), self.models, self.packages("0" * 64))
        self.assertEqual(list(self.models.iterdir()), [])

    def test_paths_inside_the_archive_cannot_escape(self):
        sha = make_archive(self.archive, extra=[("translate-en_de-1_3/../../escaped.txt", b"x"),
                                                ("../outside.txt", b"x"), ("/absolute.txt", b"x")])
        offline.ensure_model(("en", "de"), self.models, self.packages(sha))
        self.assertFalse((self.dir / "escaped.txt").exists())
        self.assertFalse((self.dir.parent / "outside.txt").exists())
        self.assertFalse(Path("/absolute.txt").exists())

    def test_incomplete_package_is_refused(self):
        sha = make_archive(self.archive, skip=("model/model.bin",))
        with self.assertRaisesRegex(core.PipelineError, "unbekanntes Format"):
            offline.ensure_model(("en", "de"), self.models, self.packages(sha))
        self.assertEqual(list(self.models.iterdir()), [])

    def test_unreachable_server_gives_a_hint(self):
        packages = {("en", "de"): ((self.dir / "missing.argosmodel").as_uri(), "0" * 64)}
        with self.assertRaisesRegex(core.PipelineError, "Internetverbindung"):
            offline.ensure_model(("en", "de"), self.models, packages)
        self.assertEqual(list(self.models.iterdir()), [])

    def test_cancelled_download_leaves_nothing_behind(self):
        sha = make_archive(self.archive)
        cancel = threading.Event()
        cancel.set()
        with self.assertRaises(core.Cancelled):
            offline.ensure_model(("en", "de"), self.models, self.packages(sha), cancel=cancel)
        self.assertEqual(list(self.models.iterdir()), [])

    def test_download_over_http_identifies_itself(self):
        """Like the real server: Python's default User-Agent is turned away with 403."""
        sha = make_archive(self.archive)
        payload = self.archive.read_bytes()
        seen = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                agent = self.headers.get("User-Agent", "")
                seen.append(agent)
                if agent.startswith("Python-urllib"):
                    self.send_error(403)
                    return
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        url = f"http://127.0.0.1:{server.server_address[1]}/v1/translate-en_de-1_3.argosmodel"
        folder = offline.ensure_model(("en", "de"), self.models, {("en", "de"): (url, sha)})
        self.assertTrue(offline._installed(folder))
        self.assertEqual(seen, [offline.USER_AGENT])

    def test_progress_is_logged(self):
        sha = make_archive(self.archive)
        lines = []
        offline.ensure_model(("en", "de"), self.models, self.packages(sha), log=lines.append)
        self.assertTrue(any("Lade Übersetzungsmodell" in line for line in lines))


class OfflineTranslatorTests(unittest.TestCase):
    class Recorder:
        def __init__(self, name):
            self.name, self.calls = name, []

        def preflight(self, src):
            self.calls.append(("preflight", src))

        def translate(self, texts, src, progress=lambda f: None, cancel=None):
            self.calls.append(("translate", src))
            return [f"{t}<{self.name}>" for t in texts]

    def test_supported_languages_use_the_built_in_models(self):
        local = self.Recorder("local")
        tr = offline.OfflineTranslator("de", local=local, argos=self.Recorder("argos"))
        tr.preflight("ru")
        self.assertEqual(tr.translate(["x"], "ru"), ["x<local>"])
        self.assertEqual(local.calls, [("preflight", "ru"), ("translate", "ru")])

    def test_other_languages_use_argos_when_it_is_there(self):
        argos = self.Recorder("argos")
        tr = offline.OfflineTranslator("de", local=self.Recorder("local"), argos=argos)
        self.assertEqual(tr.translate(["x"], "fr"), ["x<argos>"])
        tr = offline.OfflineTranslator("fr", local=self.Recorder("local"), argos=argos)
        self.assertEqual(tr.translate(["x"], "en"), ["x<argos>"])

    def without_argos(self, target, frozen=False):
        patches = [mock.patch.object(offline.importlib.util, "find_spec", return_value=None),
                   mock.patch.object(offline, "is_frozen", return_value=frozen)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        return offline.OfflineTranslator(target, local=self.Recorder("local"))

    def test_other_languages_without_argos_are_refused_early(self):
        tr = self.without_argos("fr")
        with self.assertRaisesRegex(core.PipelineError, "argostranslate"):
            tr.preflight(None)  # the target alone is enough to know
        with self.assertRaisesRegex(core.PipelineError, "Deutsch, Russisch und Englisch"):
            tr.preflight("en")

    def test_the_packaged_program_points_to_claude_instead_of_pip(self):
        tr = self.without_argos("fr", frozen=True)
        with self.assertRaises(core.PipelineError) as caught:
            tr.preflight("en")
        self.assertIn("Claude", str(caught.exception))
        self.assertNotIn("pip install", str(caught.exception))

    def test_unknown_source_with_supported_target_waits_for_detection(self):
        tr = self.without_argos("de")
        tr.preflight(None)  # fine for now
        with self.assertRaisesRegex(core.PipelineError, "Deutsch, Russisch und Englisch"):
            tr.translate(["x"], "fr")  # detected later: French cannot be done offline

    def test_backend_names_in_the_pipeline(self):
        for name in ("offline", "argos"):
            translator = pipeline.make_translator(pipeline.Options(backend=name, target_lang="ru"))
            self.assertIsInstance(translator, offline.OfflineTranslator)
        self.assertIsInstance(pipeline.make_translator(pipeline.Options(api_key="x")), core.ClaudeTranslator)


if __name__ == "__main__":
    unittest.main()
