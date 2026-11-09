"""Pinned public Hugging Face datasets, selective GLB download and attribution."""
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import urlparse
from urllib.request import build_opener, ProxyHandler, HTTPRedirectHandler, Request
from urllib.error import URLError

from .common import write_json

DATASETS = {
    "scenario": {"repo": "scenario-labs/3d-collection", "revision": "55b4c002b4c1529fc48da3dff98516c3069bfa3f",
                 "credit": "Scenario, Scenario 3D Collection, CC BY 4.0. All assets AI-generated. Record further user modifications.",
                 "policy": "https://creativecommons.org/licenses/by/4.0/"},
    "city": {"repo": "codepawl/plateau-city-glb", "revision": "1737d033c81e17cfd9b8ddf586825a178bb97982",
             "credit": "Source: MLIT Project PLATEAU 3D city models (https://www.mlit.go.jp/plateau/), 2020 releases; copyright: respective local governments. Modified and packed by CodePawl: city tiling, texture atlases, compression, LODs and collision meshes. Further project changes must be recorded by the user.",
             "policy": "https://www.mlit.go.jp/plateau/site-policy/"},
    "abo": {"repo": "codepawl/abo-glb", "revision": "11517bd633d927f9e78e4614973e07f7819122e4",
            "credit": "3D models, images and listing text: Amazon.com, Amazon Berkeley Objects (ABO), CC BY 4.0. Converted, texture-resized and compressed by CodePawl. Not endorsed by Amazon. Further changes must be recorded by the user; brand/product rights may apply.",
            "policy": "https://creativecommons.org/licenses/by/4.0/"},
}


def hf_url(url):
    p = urlparse(url)
    host = p.hostname or ""
    if p.scheme != "https" or p.username or p.password or p.port not in (None, 443) or not (
            host == "huggingface.co" or host.endswith(".huggingface.co") or host.endswith(".hf.co")):
        raise ValueError("Unexpected Hugging Face download host")
    return url


class Redirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        hf_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Datasets:
    def __init__(self, config):
        self.root = Path(config["data_dir"]) / "datasets"
        self.root.mkdir(parents=True, exist_ok=True)
        self.proxy = config.get("proxy", "")
        self.opener = build_opener(ProxyHandler({"https": config["proxy"]} if config.get("proxy") else {}), Redirect())

    def url(self, dataset, relative):
        d = DATASETS[dataset]
        if not re.fullmatch(r"[A-Za-z0-9_./-]+", relative) or ".." in relative.split("/") or relative.startswith("/"):
            raise ValueError("Invalid dataset path")
        return f"https://huggingface.co/datasets/{d['repo']}/resolve/{d['revision']}/{relative}"

    def fetch_to(self, url, path, max_mb):
        hf_url(url)
        limit = int(max_mb * 1024 * 1024)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".part")
        digest, size = hashlib.sha256(), 0
        try:
            with self.opener.open(Request(url, headers={"User-Agent": "BlenderCodexStudio/1.0"}), timeout=60) as response:
                hf_url(response.url)
                if int(response.headers.get("Content-Length", 0)) > limit:
                    raise ValueError("File exceeds download budget")
                with temporary.open("wb") as stream:
                    while True:
                        chunk = response.read(min(1024 * 1024, limit - size + 1))
                        if not chunk:
                            break
                        size += len(chunk)
                        if size > limit:
                            raise ValueError("File exceeds download budget")
                        digest.update(chunk)
                        stream.write(chunk)
            temporary.replace(path)
        except URLError as error:
            if os.name != "nt" or not isinstance(error.reason, OSError):
                raise
            from .transport import windows_download
            windows_download(url, temporary, limit, self.proxy, hf_url)
            size = temporary.stat().st_size
            digest = hashlib.sha256(temporary.read_bytes())
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        return {"bytes": size, "sha256": digest.hexdigest()}

    def index(self, dataset):
        relative = "tiles.json" if dataset == "city" else "metadata.jsonl"
        path = self.root / dataset / DATASETS[dataset]["revision"] / relative
        if not path.exists():
            self.fetch_to(self.url(dataset, relative), path, 32)
        if dataset == "city":
            return json.loads(path.read_text(encoding="utf-8"))
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def city_search(self, city="tokyo", query="", limit=10, textured_only=False):
        if not 1 <= limit <= 50:
            raise ValueError("limit must be 1..50")
        cities = self.index("city")["cities"]
        if city not in cities:
            raise ValueError("Available cities: " + ", ".join(cities))
        info = cities[city]
        tiles = [t for t in info["tiles"] if query.lower() in t["id"].lower() and (not textured_only or t.get("textured"))]
        return {"city": city, "city_name": info["name"], "total": len(tiles), "source": info["source_dataset"],
                "license": "CC-BY-4.0", "attribution": DATASETS["city"]["credit"], "results": tiles[:limit],
                "revision": DATASETS["city"]["revision"]}

    def abo_search(self, query="chair", limit=10):
        if not 1 <= limit <= 50:
            raise ValueError("limit must be 1..50")
        terms = query.lower().split()
        matches = []
        for item in self.index("abo"):
            text = " ".join(str(item.get(key) or "") for key in ("id", "name", "product_type", "brand", "material", "style")).lower()
            if all(t in text for t in terms):
                matches.append({k: item.get(k) for k in ("id", "name", "product_type", "brand", "size_metres", "triangles", "pack_bytes")})
                if len(matches) >= limit:
                    break
        return {"results": matches, "license": "CC-BY-4.0", "attribution": DATASETS["abo"]["credit"],
                "revision": DATASETS["abo"]["revision"]}

    def download(self, dataset, identifier, max_mb=64):
        if not 1 <= max_mb <= 512:
            raise ValueError("max_mb must be 1..512")
        if dataset != "scenario" and not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", identifier):
            raise ValueError("Invalid model/tile id")
        extra = {}
        if dataset == "city":
            found = [(key, info, t) for key, info in self.index("city")["cities"].items()
                     for t in info["tiles"] if t["id"] == identifier]
            if not found:
                raise ValueError("Unknown city tile")
            city, info, tile = found[0]
            relative = tile["files"]["engine"]
            extra = {"city": city, "tile": tile, "source_dataset": info["source_dataset"],
                     "blender_offset": [tile["offset_m"][0], -tile["offset_m"][2], tile["offset_m"][1]]}
        elif dataset == "scenario":
            relative = identifier
            if not re.fullmatch(r"assets/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+\.(glb|blend|fbx)", relative):
                raise ValueError("Expected assets/<id>/<file>.glb|blend|fbx")
            if relative not in self.scenario_search(query=relative, limit=1)["results"]:
                raise ValueError("File not present in pinned dataset")
            identifier = relative.split("/")[-1].rsplit(".", 1)[0]
            extra = {"ai_generated": True}
        elif dataset == "abo":
            item = next((i for i in self.index("abo") if i["id"] == identifier), None)
            if item is None:
                raise ValueError("Unknown ABO model")
            # Actual 5.2 sample import includes meshopt geometry and both WebP textures.
            relative = item["file"]
            extra = {"model": item, "format_note": "Web tier uses meshopt + WebP; Blender 5.2 tested. Older versions may need a compatible importer."}
        else:
            raise ValueError("Unknown dataset")
        folder = self.root / dataset / DATASETS[dataset]["revision"] / identifier
        path = folder / Path(relative).name
        url = self.url(dataset, relative)
        result = self.fetch_to(url, path, max_mb)
        # Check GLB magic before treating it as a model (reject HTML/error responses).
        with path.open("rb") as stream:
            if path.suffix == ".glb" and stream.read(4) != b"glTF":
                path.unlink()
                raise ValueError("Download is not a GLB file")
        d = DATASETS[dataset]
        record = {"dataset": dataset, "id": identifier, "path": str(path), "url": url, "revision": d["revision"],
                  "license": "CC-BY-4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/",
                  "source_policy": d["policy"], "attribution": d["credit"], "changes_by_user": [],
                  "retrieved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **result, **extra}
        write_json(folder / "provenance.json", record)
        (folder / "ATTRIBUTION.txt").write_text(d["credit"] + "\n" + d["policy"] + "\nModified source: " + url + "\n", encoding="utf-8")
        return {"path": str(path), "provenance": str(folder / "provenance.json"), **result, **extra}

    def scenario_search(self, query="", limit=10):
        if not 1 <= limit <= 50:
            raise ValueError("limit must be 1..50")
        path = self.root / "scenario" / DATASETS["scenario"]["revision"] / "manifest.json"
        if not path.exists():
            url = "https://huggingface.co/api/datasets/scenario-labs/3d-collection/revision/" + DATASETS["scenario"]["revision"]
            self.fetch_to(url, path, 8)
        data = json.loads(path.read_text(encoding="utf-8"))
        matches = [i["rfilename"] for i in data["siblings"] if i["rfilename"].endswith((".glb", ".blend", ".fbx")) and query.lower() in i["rfilename"].lower()]
        return {"results": matches[:limit], "total": len(matches), "license": "CC-BY-4.0", "credit": "Scenario",
                "ai_generated": True, "search_mode": "Path/id substring only; prompt search not implemented",
                "semantic_browse": "https://huggingface.co/datasets/scenario-labs/3d-collection/viewer/default/train"}
