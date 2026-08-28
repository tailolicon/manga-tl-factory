import base64
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from manga_factory.acquisition.browser_bootstrap import BrowserSession
from manga_factory.acquisition.fetcher import fetch_source
from manga_factory.acquisition.models import SourceHandoff
from manga_factory.acquisition.verify import verify_image


PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class ImageHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/protected" and self.headers.get("Cookie") != "session=ok":
            self.send_response(403)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(PNG)))
        self.end_headers()
        self.wfile.write(PNG)

    def log_message(self, format, *args):
        pass


class AcquisitionTests(unittest.TestCase):
    def test_png_verification_records_dimensions_and_hash(self):
        verified = verify_image(PNG, "image/png")
        self.assertEqual((verified.width, verified.height), (1, 1))
        self.assertEqual(verified.extension, "png")
        self.assertEqual(len(verified.sha256), 64)

    def test_handoff_rejects_sensitive_headers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source_handoff.json"
            path.write_text(json.dumps(self._handoff("http://example.com/page.png", {"Authorization": "secret"})))
            with self.assertRaisesRegex(ValueError, "sensitive header"):
                SourceHandoff.load(path)

    def test_direct_fetch_verifies_image_and_deletes_temp(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), ImageHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                handoff = root / "source_handoff.json"
                image_url = f"http://127.0.0.1:{server.server_port}/page.png"
                handoff.write_text(json.dumps(self._handoff(image_url, {})), encoding="utf-8")
                scratch = root / "scratch"
                result = fetch_source(
                    handoff,
                    output_root=scratch,
                    allow_private_hosts=True,
                    concurrency=2,
                )
                self.assertEqual(result["status"], "success")
                self.assertEqual(result["chapters"][0]["downloaded"], 1)
                self.assertEqual(result["chapters"][0]["fetch_mode"], "direct_http")
                self.assertFalse((scratch / "test-project").exists())
                self.assertTrue((root / "fetch_result.json").exists())
        finally:
            server.shutdown()
            server.server_close()

    def test_browser_session_retries_http_without_persisting_cookie(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), ImageHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                handoff = root / "source_handoff.json"
                image_url = f"http://127.0.0.1:{server.server_port}/protected"
                handoff.write_text(json.dumps(self._handoff(image_url, {})), encoding="utf-8")

                def bootstrap(url, timeout_ms):
                    return BrowserSession(headers={"Cookie": "session=ok"})

                result = fetch_source(
                    handoff,
                    output_root=root / "scratch",
                    allow_private_hosts=True,
                    browser_bootstrap=bootstrap,
                    retries=0,
                )
                self.assertEqual(result["status"], "success")
                self.assertEqual(result["chapters"][0]["fetch_mode"], "browser_bootstrap")
                serialized = (root / "fetch_result.json").read_text(encoding="utf-8")
                self.assertNotIn("session=ok", serialized)
        finally:
            server.shutdown()
            server.server_close()

    @staticmethod
    def _handoff(page_url, headers):
        return {
            "schema": 1,
            "provider": "kotori",
            "project_id": "test-project",
            "source": {
                "source_id": 1,
                "source_name": "Test",
                "manga_url": "http://example.com/manga",
            },
            "chapters": [
                {
                    "id": "chapter-1",
                    "name": "Chapter 1",
                    "source_url": "http://example.com/chapter-1",
                    "pages_resolved": True,
                    "pages": [{"index": 1, "url": page_url, "headers": headers}],
                }
            ],
        }


if __name__ == "__main__":
    unittest.main()
