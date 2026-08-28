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
        a = task_fingerprint(project_id="x", task_type="localize_chapter", scope={"pages": [1, 5]}, input_hashes=["b", "a"], context_version="ctx:1")
        b = task_fingerprint(project_id="x", task_type="localize_chapter", scope={"pages": [1, 5]}, input_hashes=["a", "b"], context_version="ctx:1")
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


class ChapterPipelineTests(unittest.TestCase):
    def _write_lane(self, root, phase="translate", resume_page=1, last_result=None):
        lane_dir = root / "work" / "chapter_lanes"
        lane_dir.mkdir(parents=True)
        (root / "projects" / "project-x").mkdir(parents=True)
        (root / "work" / "imports" / "source-x").mkdir(parents=True)
        (lane_dir / "active.json").write_text(json.dumps({
            "schema": 1,
            "active_lane": "x-ch1",
            "lane_path": "work/chapter_lanes/x-ch1.json",
        }), encoding="utf-8")
        lane = {
            "schema": 1,
            "lane_id": "x-ch1",
            "mode": "chapter_pipeline",
            "project_id": "project-x",
            "series_key": "x",
            "chapter": {"id": "ch-1", "name": "Chapter 1"},
            "page_count": 41,
            "source_handoff": {"path": "work/imports/source-x/source_handoff.json", "blob_sha": "abcdef1234567890"},
            "state": "ready",
            "generation": 3,
            "phase": phase,
            "resume_page": resume_page,
            "progress": {"translated_pages": 0, "rendered_pages": 0, "qa_pages": 0, "published": False},
            "next_task": {"task_type": "localize_chapter", "goal": "finish chapter", "scope": {"page_start": 1, "page_end": 41}},
            "claim": None,
            "last_result": last_result,
        }
        (lane_dir / "x-ch1.json").write_text(json.dumps(lane), encoding="utf-8")

    def test_chapter_envelope(self):
        from manga_factory.standalone import build_chapter_envelope
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            previous = {"status": "partial", "commit": "deadbeefcafefeed", "branch": "chapter/x-ch1/g2"}
            self._write_lane(root, phase="redraw_typeset", resume_page=7, last_result=previous)
            env = build_chapter_envelope(root)
            self.assertEqual(env["execution_mode"], "chapter_pipeline")
            self.assertEqual(env["task_type"], "localize_chapter")
            self.assertEqual(env["phase"], "redraw_typeset")
            self.assertEqual(env["resume_page"], 7)
            self.assertEqual(env["fencing_token"], 3)
            self.assertEqual(env["task_branch"], "chapter/x-ch1/g3")
            self.assertEqual(env["checkpoint_base_commit"], "deadbeefcafefeed")
            self.assertEqual(env["runtime_budget_minutes"], 25)
            self.assertEqual(env["drain_after_minutes"], 21)
            self.assertIn("projects/project-x/chapters/ch-1/rendered/**", env["allowed_write_paths"])
            self.assertIn("projects/project-x/publication/ch-1/**", env["allowed_write_paths"])
            c = env["chapter_constraints"]
            self.assertTrue(c["generalist_worker"])
            self.assertFalse(c["phase_boundaries_are_handoffs"])
            self.assertTrue(c["worker_may_advance_phase"])
            self.assertTrue(c["worker_may_translate"])
            self.assertTrue(c["worker_may_correct_translation"])
            self.assertTrue(c["worker_may_redraw_and_typeset"])
            self.assertTrue(c["worker_may_qa"])
            self.assertTrue(c["worker_may_fix_qa_issues"])
            self.assertTrue(c["worker_may_publish_after_qa"])
            self.assertFalse(c["soft_page_target_is_stop_condition"])
            self.assertEqual(c["remote_checkpoint_strategy"], "adaptive_batched")
            self.assertEqual(c["default_checkpoint_pages"], 6)
            self.assertEqual(c["min_checkpoint_pages"], 4)
            self.assertEqual(c["max_checkpoint_pages"], 10)
            self.assertEqual(c["max_uncommitted_minutes"], 7)
            self.assertEqual(c["force_flush_from_minute"], 18)
            self.assertTrue(c["parallel_blob_creation_when_supported"])
            self.assertTrue(c["one_tree_commit_ref_update_per_batch"])
            self.assertFalse(c["main_lane_updates_per_page"])
            self.assertTrue(c["inherit_previous_checkpoint_commit"])
            self.assertEqual(c["binary_persistence_strategy"], "github_create_blob_base64_then_tree_commit")
            self.assertTrue(c["binary_base64_is_transport_only"])
            self.assertTrue(c["rendered_progress_requires_remote_commit"])
            self.assertEqual(c["preferred_render_format"], "webp")
            self.assertEqual(c["target_render_bytes_per_page"], 1048576)


if __name__ == "__main__":
    unittest.main()
