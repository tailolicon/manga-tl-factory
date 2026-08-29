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
    def _base_dirs(self, root):
        lane_dir = root / "work" / "chapter_lanes"
        lane_dir.mkdir(parents=True)
        (root / "projects" / "project-x").mkdir(parents=True)
        (root / "work" / "imports" / "source-x").mkdir(parents=True)
        (lane_dir / "active.json").write_text(json.dumps({
            "schema": 1,
            "active_lane": "x-ch1",
            "lane_path": "work/chapter_lanes/x-ch1.json",
        }), encoding="utf-8")
        return lane_dir

    def _write_parallel_lane(self, root, units=None, final_state="blocked"):
        lane_dir = self._base_dirs(root)
        if units is None:
            units = [
                {"id":"r001-006","page_start":1,"page_end":6,"state":"ready","generation":1,"phase":"redraw_typeset","resume_page":1,"claim":None,"checkpoint_commit":None,"result":None},
                {"id":"r007-012","page_start":7,"page_end":12,"state":"ready","generation":1,"phase":"redraw_typeset","resume_page":7,"claim":None,"checkpoint_commit":None,"result":None},
            ]
        lane = {
            "schema": 1,
            "lane_id": "x-ch1",
            "mode": "chapter_pipeline",
            "coordination_mode": "parallel_ranges",
            "project_id": "project-x",
            "series_key": "x",
            "chapter": {"id": "ch-1", "name": "Chapter 1"},
            "page_count": 12,
            "source_handoff": {"path": "work/imports/source-x/source_handoff.json", "blob_sha": "abcdef1234567890"},
            "state": "ready",
            "generation": 4,
            "phase": "redraw_typeset",
            "resume_page": 1,
            "progress": {"translated_pages": 12, "rendered_pages": 0, "qa_pages": 0, "published": False},
            "parallel": {
                "max_active_claims": 4,
                "lease_minutes": 35,
                "base_commit": "deadbeefcafefeed",
                "units": units,
                "finalization": {"state": final_state, "generation": 1, "claim": None, "result": None},
            },
            "next_task": {"task_type": "localize_chapter", "goal": "finish chapter", "scope": {"page_start": 1, "page_end": 12}},
            "claim": None,
            "last_result": None,
        }
        (lane_dir / "x-ch1.json").write_text(json.dumps(lane), encoding="utf-8")

    def test_parallel_envelope_selects_first_free_range(self):
        from manga_factory.standalone import build_chapter_envelope
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_parallel_lane(root)
            env = build_chapter_envelope(root)
            self.assertEqual(env["execution_mode"], "chapter_pipeline")
            self.assertEqual(env["task_type"], "localize_chapter")
            self.assertEqual(env["work_unit"]["id"], "r001-006")
            self.assertEqual(env["scope"], {"page_start": 1, "page_end": 6})
            self.assertEqual(env["task_branch"], "chapter/x-ch1/r001-006/g1")
            self.assertEqual(env["checkpoint_base_commit"], "deadbeefcafefeed")
            self.assertFalse(env["chapter_constraints"]["global_chapter_claim_is_used"])
            self.assertTrue(env["chapter_constraints"]["worker_owns_only_claimed_page_range"])
            self.assertTrue(env["chapter_constraints"]["range_completion_requires_qa"])
            self.assertTrue(env["chapter_constraints"]["worker_may_claim_another_range_if_time_remains"])
            self.assertTrue(env["chapter_constraints"]["parallel_blob_creation_when_supported"])

    def test_parallel_envelope_skips_active_claim(self):
        from manga_factory.standalone import build_chapter_envelope
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            units = [
                {"id":"r001-006","page_start":1,"page_end":6,"state":"claimed","generation":1,"phase":"redraw_typeset","resume_page":1,"claim":{"expires_at":"2999-01-01T00:00:00+00:00"},"checkpoint_commit":None,"result":None},
                {"id":"r007-012","page_start":7,"page_end":12,"state":"ready","generation":1,"phase":"redraw_typeset","resume_page":7,"claim":None,"checkpoint_commit":None,"result":None},
            ]
            self._write_parallel_lane(root, units=units)
            env = build_chapter_envelope(root)
            self.assertEqual(env["work_unit"]["id"], "r007-012")

    def test_parallel_envelope_reclaims_expired_range(self):
        from manga_factory.standalone import build_chapter_envelope
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            units = [
                {"id":"r001-006","page_start":1,"page_end":6,"state":"claimed","generation":2,"phase":"qa","resume_page":3,"claim":{"expires_at":"2000-01-01T00:00:00+00:00"},"checkpoint_commit":"feedface1234567","result":None},
            ]
            self._write_parallel_lane(root, units=units)
            env = build_chapter_envelope(root)
            self.assertEqual(env["work_unit"]["id"], "r001-006")
            self.assertTrue(env["work_unit"]["reclaim_expired_claim"])
            self.assertEqual(env["fencing_token"], 3)
            self.assertEqual(env["checkpoint_base_commit"], "feedface1234567")

    def test_parallel_envelope_finalizes_after_all_ranges_complete(self):
        from manga_factory.standalone import build_chapter_envelope
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            units = [
                {"id":"r001-006","page_start":1,"page_end":6,"state":"completed","generation":1,"phase":"done","resume_page":6,"claim":None,"checkpoint_commit":"a"*40,"result":{"path":"work/results/a.json"}},
                {"id":"r007-012","page_start":7,"page_end":12,"state":"completed","generation":1,"phase":"done","resume_page":12,"claim":None,"checkpoint_commit":"b"*40,"result":{"path":"work/results/b.json"}},
            ]
            self._write_parallel_lane(root, units=units, final_state="ready")
            env = build_chapter_envelope(root)
            self.assertEqual(env["work_unit"]["kind"], "finalize")
            self.assertEqual(env["phase"], "publish")
            self.assertTrue(env["chapter_constraints"]["all_ranges_must_be_completed_before_publish"])
            self.assertTrue(env["chapter_constraints"]["finalizer_is_generalist_worker"])


if __name__ == "__main__":
    unittest.main()
