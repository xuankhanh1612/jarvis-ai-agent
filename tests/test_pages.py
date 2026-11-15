"""Smoke tests for the static site and its deployment configuration."""

import json
import shutil
import tempfile
import threading
import unittest
from functools import partial
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "pages"


class SiteParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.duplicate_ids = set()
        self.references = []
        self.label_references = []
        self.text = []
        self.language = None
        self.viewport = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html":
            self.language = attrs.get("lang")
        if tag == "meta" and attrs.get("name") == "viewport":
            self.viewport = True
        if "id" in attrs:
            if attrs["id"] in self.ids:
                self.duplicate_ids.add(attrs["id"])
            self.ids.add(attrs["id"])
        for attr in ("href", "src"):
            if attrs.get(attr):
                self.references.append(attrs[attr])
        if attrs.get("aria-labelledby"):
            self.label_references.extend(attrs["aria-labelledby"].split())

    def handle_data(self, data):
        self.text.append(data)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


class PagesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parser = SiteParser()
        cls.parser.feed((SITE / "index.html").read_text(encoding="utf-8"))

    def test_page_has_language_viewport_and_unique_accessibility_targets(self):
        self.assertEqual(self.parser.language, "vi")
        self.assertTrue(self.parser.viewport)
        self.assertFalse(self.parser.duplicate_ids)
        for target in self.parser.label_references:
            self.assertIn(target, self.parser.ids)

    def test_links_and_assets_work_from_a_repository_subpath(self):
        for reference in self.parser.references:
            with self.subTest(reference=reference):
                parsed = urlparse(reference)
                if parsed.scheme or parsed.netloc:
                    self.assertEqual(parsed.scheme, "https")
                    continue
                if not parsed.path:
                    self.assertIn(unquote(parsed.fragment), self.parser.ids)
                    continue
                self.assertFalse(parsed.path.startswith("/"), "root-relative URLs break on project Pages")
                target = (SITE / unquote(parsed.path)).resolve()
                self.assertTrue(target.is_relative_to(SITE.resolve()))
                self.assertTrue(target.is_file(), f"missing site asset: {target}")

    def test_explains_that_static_hosts_do_not_run_the_windows_app(self):
        content = " ".join(self.parser.text)
        self.assertIn("Windows", content)
        self.assertIn("không chạy trực tiếp trên GitHub Pages hoặc Vercel", content)
        self.assertIn("không có xác thực", content)
        self.assertTrue((SITE / ".nojekyll").is_file())

    def test_vercel_publishes_the_web_app_not_the_repository_root(self):
        config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
        self.assertIsNone(config["framework"])
        self.assertIsNone(config["buildCommand"])
        self.assertIsNone(config["installCommand"])
        self.assertEqual(config["outputDirectory"], "web")
        self.assertTrue((ROOT / config["outputDirectory"] / "index.html").is_file())
        self.assertIn("api/chat.py", config["functions"])

    def test_site_is_served_at_root_and_under_the_repository_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copytree(SITE, tmp, dirs_exist_ok=True)
            shutil.copytree(SITE, Path(tmp) / "jarvis-ai-agent")
            handler = partial(QuietHandler, directory=tmp)
            with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    for prefix in ("", "jarvis-ai-agent/"):
                        root = f"http://127.0.0.1:{server.server_port}/{prefix}"
                        for path, content_type in (
                            ("", "text/html"),
                            ("./styles.css", "text/css"),
                            ("./favicon.svg", "image/svg+xml"),
                        ):
                            with self.subTest(prefix=prefix, path=path), urlopen(urljoin(root, path), timeout=5) as response:
                                self.assertEqual(response.status, 200)
                                self.assertEqual(response.headers.get_content_type(), content_type)
                                self.assertTrue(response.read())
                finally:
                    server.shutdown()
                    thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
