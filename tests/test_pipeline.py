import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from blender_codex import pipeline, transfer
from server import Server


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        pipeline.init(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def passed_pipeline(self):
        pipeline.record_reference(self.root, "https://example.test/photo", notes="Composition reference only")
        pipeline.record_stage(self.root, "references", "passed", evidence=["user selected source"])
        for stage in pipeline.STAGES[1:]:
            (self.root / (stage + ".txt")).write_text("test artifact", encoding="utf-8")
            pipeline.record_stage(self.root, stage, "passed", artifacts=[stage + ".txt"], evidence=["test review"])

    def test_delivery_readonly_and_explicit_approval(self):
        self.assertFalse(pipeline.delivery_check(self.root)["passed"])
        self.passed_pipeline()
        before = (self.root / "production-pipeline.json").read_bytes()
        check = pipeline.delivery_check(self.root)
        self.assertTrue(check["ready_for_user_review"])
        self.assertFalse(check["delivery_approved"])
        self.assertEqual(before, (self.root / "production-pipeline.json").read_bytes())
        pipeline.approve(self.root, "用户：确认这版成品可以交付")
        self.assertTrue(pipeline.status(self.root)["delivery_approved"])
        pipeline.record_reference(self.root, "https://example.test/revised")
        state = pipeline.status(self.root)
        self.assertFalse(state["delivery_approved"])
        self.assertEqual(state["stages"]["delivery"]["status"], "review")

    def test_missing_artifact_recheck_absolute_and_relative(self):
        self.passed_pipeline()
        (self.root / "delivery.txt").unlink()
        self.assertFalse(pipeline.delivery_check(self.root)["passed"])
        with self.assertRaises(ValueError):
            pipeline.approve(self.root, "Approved")
        with self.assertRaises(ValueError):
            pipeline.record_stage(self.root, "delivery", "passed", artifacts=[str(self.root / "missing.txt")])

    def test_no_empty_pass_and_prerequisites(self):
        for stage in pipeline.STAGES:
            with self.assertRaises(ValueError):
                pipeline.record_stage(self.root, stage, "passed")
        self.assertEqual(pipeline.status(self.root)["stages"]["references"]["status"], "pending")

    def test_reference_same_name_preserves_both(self):
        for folder in ("a", "b"):
            (self.root / folder).mkdir()
            (self.root / folder / "photo.png").write_bytes(folder.encode())
        first = pipeline.record_reference(self.root, "source-a", local_path="a/photo.png")
        second = pipeline.record_reference(self.root, "source-b", local_path="b/photo.png")
        self.assertNotEqual(first["local_path"], second["local_path"])
        self.assertEqual((self.root / first["local_path"]).read_bytes(), b"a")

    def test_scaffold_backward_compatible_and_optin_root(self):
        server = Server({"data_dir": str(self.root / "state")})
        server.call("create_threejs_project", {"directory": str(self.root / "standalone")})
        server.call("create_threejs_project", {"directory": str(self.root / "source/threejs"), "project_directory": str(self.root)})
        self.assertEqual(pipeline.status(self.root)["stages"]["threejs"]["status"], "review")
        with patch.object(server.client, "call") as call:
            with self.assertRaises((ValueError, FileNotFoundError)):
                server.call("import_threejs_scene", {"glb_path": str(self.root / "missing.glb"), "manifest_path": "missing.json", "checkpoint_path": "backup.blend"})
            call.assert_not_called()

    def test_transfer_checksum_and_units(self):
        glb = self.root / "asset.glb"
        glb.write_bytes(struct.pack("<4sII", b"glTF", 2, 12))
        manifest = self.root / "asset.transfer.json"
        record = {"schema": "blender-studio-transfer/1", "glb": glb.name, "up": "Y", "units": "meters", "resolution": [480, 270], "sha256": hashlib.sha256(glb.read_bytes()).hexdigest(), "camera_projection": {"type": "perspective", "vertical_fov": 40, "aspect": 480/270}}
        manifest.write_text(json.dumps(record), encoding="utf-8")
        self.assertEqual(transfer.inspect_bundle(glb, manifest)["resolution"], [480, 270])
        record["up"] = "Z"
        manifest.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaises(ValueError):
            transfer.inspect_bundle(glb, manifest)
        record.update(up="Y", sha256="0" * 64)
        manifest.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaises(ValueError):
            transfer.inspect_bundle(glb, manifest)


if __name__ == "__main__":
    unittest.main()
