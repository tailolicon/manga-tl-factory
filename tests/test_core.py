import json
import tempfile
import unittest
from pathlib import Path

from manga_factory.context import canonical_snapshot
from manga_factory.core import task_fingerprint
from manga_factory.intake import submit
from manga_factory.publication import build_publication_manifest
from manga_factory.validate import validate_repo


ROOT = Path(__file__).resolve().parents[1]


class FactoryTests(unittest.TestCase):
    def test_repo_validates(self):
        self.assertEqual(validate_repo(ROOT), [])

    def test_task_fingerprint_is_deterministic(self):
        a = task_fingerprint(project_id="x", task_type="translate_chunk", scope={"pages": [1, 5]}, input_hashes=["b", "a"], context_version="ctx:1")
        b = task_fingerprint(project_id="x", task_type="translate_chunk", scope={"pages": [1, 5]}, input_hashes=["a", "b"], context_version="ctx:1")
        self.assertEqual(a, b)

    def test_submit_initializes_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "requests").mkdir()
            (root / "projects").mkdir()
            import shutil
            shutil.copytree(ROOT / "projects" / "_template", root / "projects" / "_template")
            result = submit(root, "https://example.com/series/foo")
            self.assertTrue((root / "projects" / result["project_id"] / "project.json").exists())
            self.assertTrue((root / "requests" / f'{result["request_id"]}.json').exists())

    def test_context_version_changes_with_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            for d in ["characters", "speech", "terminology", "evidence", "chapters", "style"]:
                (p / "context" / d).mkdir(parents=True, exist_ok=True)
            (p / "context" / "style" / "style.json").write_text("{}", encoding="utf-8")
            v1 = canonical_snapshot(p)["context_version"]
            (p / "context" / "characters" / "x.json").write_text(json.dumps({"id":"character:x"}), encoding="utf-8")
            v2 = canonical_snapshot(p)["context_version"]
            self.assertNotEqual(v1, v2)

    def test_publication_manifest_sorts_pages(self):
        manifest = build_publication_manifest(series_id="x", chapter_id="1", pages=[
            {"index": 2, "url": "b", "width": 10, "height": 20, "sha256": "bb"},
            {"index": 1, "url": "a", "width": 10, "height": 20, "sha256": "aa"},
        ])
        self.assertEqual([p["index"] for p in manifest["pages"]], [1, 2])


if __name__ == "__main__":
    unittest.main()
