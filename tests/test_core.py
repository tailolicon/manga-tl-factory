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


class StandaloneTests(unittest.TestCase):
    def test_standalone_envelope_from_pending_request(self):
        from manga_factory.standalone import build_standalone_test_envelope
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "requests").mkdir()
            (root / "projects").mkdir()
            import shutil
            shutil.copytree(ROOT / "projects" / "_template", root / "projects" / "_template")
            req = submit(root, "https://example.com/series/test")
            env = build_standalone_test_envelope(root, request_id=req["request_id"])
            self.assertEqual(env["execution_mode"], "standalone_test")
            self.assertEqual(env["task_type"], "bootstrap")
            self.assertEqual(env["fencing_token"], 1)
            self.assertIn(req["project_id"], env["allowed_write_paths"][0])

    def _write_lane(self, root, *, task_type="acquire_source", scope=None, relay=None):
        lane_dir = root / "work" / "test_lanes"
        lane_dir.mkdir(parents=True)
        (root / "projects" / "project-x").mkdir(parents=True)
        (root / "work" / "imports" / "source-x").mkdir(parents=True)
        (lane_dir / "active.json").write_text(json.dumps({
            "schema": 1,
            "active_lane": "x-ch1",
            "lane_path": "work/test_lanes/x-ch1.json",
        }), encoding="utf-8")
        next_task = {"task_type": task_type, "goal": "test step"}
        if scope is not None:
            next_task["scope"] = scope
        lane = {
            "schema": 1,
            "lane_id": "x-ch1",
            "mode": "standalone_chapter_test",
            "project_id": "project-x",
            "series_key": "x",
            "chapter": {"id": "ch-1", "name": "Chapter 1"},
            "source_handoff": {
                "path": "work/imports/source-x/source_handoff.json",
                "blob_sha": "abcdef1234567890",
            },
            "workflow": {
                "predeclared": True,
                "steps": [{"ordinal": 1, "task_type": task_type, "status": "ready"}],
            },
            "state": "ready",
            "generation": 3,
            "next_task": next_task,
            "claim": None,
            "last_result": None,
        }
        if relay is not None:
            lane["relay"] = relay
        (lane_dir / "x-ch1.json").write_text(json.dumps(lane), encoding="utf-8")

    def test_standalone_chapter_lane_envelope(self):
        from manga_factory.standalone import build_standalone_chapter_test_envelope
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_lane(root)
            env = build_standalone_chapter_test_envelope(root)
            self.assertEqual(env["execution_mode"], "standalone_chapter_test")
            self.assertEqual(env["task_id"], "standalone-x-ch1-g3-acquire_source")
            self.assertEqual(env["lease_id"], "standalone-lane-x-ch1-g3")
            self.assertEqual(env["fencing_token"], 3)
            self.assertEqual(env["task_branch"], "test/x-ch1/acquire_source/g3")
            self.assertEqual(env["coordination_write_path"], "work/test_lanes/x-ch1.json")
            self.assertEqual(env["runtime_budget_minutes"], 25)
            self.assertEqual(env["drain_after_minutes"], 21)
            self.assertEqual(env["checkpoint_by_minutes"], 23)
            self.assertEqual(env["safety_stop_minutes"], 24)

    def test_translation_chunk_allows_multi_page_artifacts_and_relay(self):
        from manga_factory.standalone import build_standalone_chapter_test_envelope
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scope = {"page_start": 1, "page_end": 41, "resume_from": 1, "soft_target_pages": 10}
            relay = {"status": "ready", "artifact_id": 123, "artifact_name": "chapter-relay-x"}
            self._write_lane(root, task_type="translation_chunk_test", scope=scope, relay=relay)
            env = build_standalone_chapter_test_envelope(root)
            self.assertEqual(env["scope"], scope)
            self.assertEqual(env["relay"], relay)
            self.assertIn("projects/project-x/translations/smoke/**", env["allowed_write_paths"])
            self.assertTrue(env["standalone_constraints"]["translation_chunk_is_time_budgeted"])
            self.assertEqual(env["standalone_constraints"]["translation_atomic_unit"], "page")
            self.assertEqual(env["standalone_constraints"]["translation_remote_checkpoint_strategy"], "batched")
            self.assertFalse(env["standalone_constraints"]["translation_soft_target_is_stop_condition"])
            self.assertTrue(env["standalone_constraints"]["worker_owns_single_chapter_until_drain"])


if __name__ == "__main__":
    unittest.main()
