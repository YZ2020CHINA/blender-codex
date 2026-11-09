import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_codex.assets import Assets, validate_url, film_references
from blender_codex.datasets import Datasets, hf_url
from blender_codex.common import write_json
from blender_codex import web, authoring, production
from server import Server, TOOLS, validate, VEC3


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.config = {"data_dir": self.tmp.name, "blender_executable": "", "config_path": "", "request_timeout": 5}

    def tearDown(self):
        self.tmp.cleanup()

    def test_mcp_negotiation_and_errors(self):
        server = Server(self.config)
        response = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
        self.assertEqual(response["result"]["protocolVersion"], "2025-06-18")
        self.assertIsNone(server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        self.assertEqual(server.handle([])["error"]["code"], -32600)
        self.assertTrue(server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "unknown"}})["result"]["isError"])

    def test_stdio_real_process(self):
        config = Path(self.tmp.name) / "config.json"
        write_json(config, self.config)
        requests = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25"}},
                    {"jsonrpc": "2.0", "method": "notifications/initialized"},
                    {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                    {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "film_reference_search", "arguments": {"query": "黑泽明", "technique": "thirds"}}}]
        result = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "server.py"), "--config", str(config)],
                                input="\n".join(json.dumps(r, ensure_ascii=False) for r in requests) + "\n", text=True,
                                encoding="utf-8", capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        replies = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(replies), 3)
        self.assertEqual(len(replies[1]["result"]["tools"]), len(TOOLS))
        self.assertFalse(replies[2]["result"].get("isError"))

    def test_schema_rejects_unknown_and_bad_vector(self):
        with self.assertRaises(ValueError):
            validate([1, 2], VEC3)
        server = Server(self.config)
        with self.assertRaises(ValueError):
            server.call("create_camera", {"shell": "bad"})
        self.assertEqual(len({t["name"] for t in TOOLS}), len(TOOLS))

    def test_download_host_boundaries(self):
        for url in ("http://api.polyhaven.com/x", "https://polyfork.dev.evil/x", "https://localhost/x", "https://api.polyhaven.com:8443/x"):
            with self.assertRaises(ValueError):
                validate_url(url)
        for url in ("https://evil-hf.co/x", "http://huggingface.co/x", "https://huggingface.co@evil.test/x"):
            with self.assertRaises(ValueError):
                hf_url(url)
        self.assertEqual(hf_url("https://cas-bridge.xethub.hf.co/x"), "https://cas-bridge.xethub.hf.co/x")

    def test_polyhaven_dependencies_and_provenance(self):
        assets = Assets(self.config)
        payload = b"example blend"
        import hashlib
        entry = {"url": "https://dl.polyhaven.org/model.blend", "size": len(payload), "md5": hashlib.md5(payload).hexdigest(),
                 "include": {"textures/color.jpg": {"url": "https://dl.polyhaven.org/color.jpg", "size": 3}}}
        with patch.object(assets, "files", return_value={"blend": {"1k": {"blend": entry}}}), patch.object(assets, "fetch", side_effect=[payload, b"jpg"]):
            result = assets.download("chair")
        record = json.loads(Path(result["provenance"]).read_text(encoding="utf-8"))
        self.assertEqual(record["license"], "CC0-1.0")
        self.assertEqual(len(record["files"]), 2)
        self.assertTrue((Path(result["path"]).parent / "textures/color.jpg").exists())

    def test_dependency_traversal_rejected(self):
        assets = Assets(self.config)
        entry = {"url": "https://dl.polyhaven.org/x.blend", "include": {"../escape": {"url": "https://dl.polyhaven.org/x"}}}
        with patch.object(assets, "files", return_value={"blend": {"1k": {"blend": entry}}}), patch.object(assets, "fetch", return_value=b"a"):
            with self.assertRaises(ValueError):
                assets.download("chair")
        self.assertFalse((Path(self.tmp.name) / "assets/chair/escape").exists())

    def test_download_budget_before_fetch(self):
        assets = Assets(self.config)
        entry = {"url": "https://dl.polyhaven.org/x.blend", "size": 2 * 1024 * 1024}
        with patch.object(assets, "files", return_value={"blend": {"1k": {"blend": entry}}}), patch.object(assets, "fetch") as fetch:
            with self.assertRaises(ValueError):
                assets.download("chair", max_mb=1)
            fetch.assert_not_called()

    def test_polyfork_requires_free_and_credit(self):
        assets = Assets(self.config)
        with patch.object(assets, "json", return_value={"free": False}):
            with self.assertRaises(ValueError):
                assets.polyfork_download("chair")
        with patch.object(assets, "json", return_value={"free": True}):
            with self.assertRaises(ValueError):
                assets.polyfork_download("chair")

    def test_city_coordinate_conversion(self):
        datasets = Datasets(self.config)
        tile = {"id": "tokyo-123", "offset_m": [10, 20, 30], "files": {"engine": "engine/tokyo-123/tokyo-123.glb"}}
        def download(url, path, max_mb):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"glTFexample")
            return {"bytes": 11, "sha256": "test"}
        with patch.object(datasets, "index", return_value={"cities": {"tokyo": {"tiles": [tile], "source_dataset": "https://example.test"}}}), patch.object(datasets, "fetch_to", side_effect=download):
            result = datasets.download("city", "tokyo-123")
        self.assertEqual(result["blender_offset"], [10, -30, 20])
        self.assertIn("MLIT", Path(result["provenance"]).read_text(encoding="utf-8"))

    def test_reference_links_are_disclosed(self):
        result = film_references("The Searchers", "silhouette")
        self.assertIn("not fetched", result["mode"])
        self.assertEqual(len(result["links"]), 4)

    def test_web_bundle_no_upload(self):
        source = Path(self.tmp.name) / "model.glb"
        source.write_bytes(b"glTFtest")
        result = web.build(source, Path(self.tmp.name) / "web")
        self.assertTrue(Path(result["html"]).is_file())
        self.assertTrue((Path(result["directory"]) / "scene.glb").is_file())
        self.assertIn("0.180.0", Path(result["html"]).read_text(encoding="utf-8"))

    def test_production_layout_never_implies_approval(self):
        folder = Path(self.tmp.name) / "new-production"
        result = production.initialize(folder, "测试工程")
        self.assertTrue((Path(result["delivery"]) / "交付说明.md").is_file())
        review = json.loads((folder / "production-review.json").read_text(encoding="utf-8"))
        self.assertFalse(review["delivery_approved"])
        self.assertEqual(review["stage_confirmations"], [])
        with self.assertRaises(ValueError):
            production.initialize(folder)

    def test_authoring_preserves_existing_work(self):
        folder = Path(self.tmp.name) / "authoring"
        authoring.scaffold(folder, "reference brief")
        (folder / "model.js").write_text("user edit", encoding="utf-8")
        with self.assertRaises(ValueError):
            authoring.scaffold(folder)
        self.assertEqual((folder / "model.js").read_text(), "user edit")
        with self.assertRaises(ValueError):
            validate([float("nan"), 1, 2], VEC3)


if __name__ == "__main__":
    unittest.main()
