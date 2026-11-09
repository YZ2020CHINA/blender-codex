"""Public CC0 discovery, bounded downloads and provenance. Never scrapes film stills."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import time
import tempfile
from urllib.parse import urlencode, urlparse, quote
from urllib.request import build_opener, ProxyHandler, Request, HTTPRedirectHandler
from urllib.error import URLError

from .common import write_json

LICENSE = "https://creativecommons.org/publicdomain/zero/1.0/"
POLY_LICENSE = "https://polyhaven.com/license"
HOSTS = {"api.polyhaven.com", "dl.polyhaven.org", "ambientcg.com", "polyfork.dev"}


def validate_url(url):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in HOSTS or parsed.port not in (None, 443) or parsed.username or parsed.password:
        raise ValueError("Unapproved asset API/download URL")
    return url


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Assets:
    def __init__(self, config):
        self.root = Path(config["data_dir"]) / "assets"
        self.root.mkdir(parents=True, exist_ok=True)
        self.proxy = config.get("proxy", "")
        self.opener = build_opener(ProxyHandler({"https": config["proxy"]} if config.get("proxy") else {}), SafeRedirect())

    def fetch(self, url, limit=12 * 1024 * 1024):
        validate_url(url)
        request = Request(url, headers={"User-Agent": "BlenderCodexStudio/1.0 (public CC0 asset discovery)"})
        try:
            with self.opener.open(request, timeout=45) as response:
                validate_url(response.url)
                data = response.read(limit + 1)
                if len(data) > limit:
                    raise ValueError("Response exceeds size limit")
                return data
        except URLError as error:
            if os.name != "nt" or not isinstance(error.reason, OSError):
                raise
            from .transport import windows_download
            with tempfile.TemporaryDirectory(prefix="blender-asset-") as temporary:
                path = Path(temporary) / "response"
                windows_download(url, path, limit, self.proxy, validate_url)
                return path.read_bytes()

    def json(self, url):
        return json.loads(self.fetch(url))

    def search(self, query="", kind="models", limit=12, provider="polyhaven"):
        limit = int(limit)
        if not 1 <= limit <= 50:
            raise ValueError("limit must be 1..50")
        if kind not in ("models", "hdris", "textures"):
            raise ValueError("kind must be models, hdris, or textures")
        if provider == "ambientcg":
            # The service silently ignores unknown filters, so also filter returned dataType locally.
            types = {"models": "3DModel", "hdris": "HDRI", "textures": "Material"}
            url = "https://ambientcg.com/api/v2/full_json?" + urlencode({"q": query, "type": types[kind], "limit": 100})
            data = self.json(url)
            found = [a for a in data.get("foundAssets", []) if a.get("dataType") == types[kind]][:limit]
            return {"provider": provider, "results": [{"id": a["assetId"], "name": a.get("displayName", a["assetId"]),
                    "page": "https://ambientcg.com/view?id=" + quote(a["assetId"]), "license": "CC0-1.0",
                    "license_url": "https://docs.ambientcg.com/license/", "commercial_use": True,
                    "download": "Open the source page; automatic download is currently Poly Haven only"} for a in found],
                    "note": "Filtered the returned API page by dataType; empty results do not prove absence. Try the provider search page."}
        if provider != "polyhaven":
            raise ValueError("provider must be polyhaven or ambientcg")
        cache = self.root / ("catalog-" + kind + ".json")
        if cache.exists() and time.time() - cache.stat().st_mtime < 21600:
            data = json.loads(cache.read_text(encoding="utf-8"))
        else:
            data = self.json("https://api.polyhaven.com/assets?" + urlencode({"t": kind}))
            write_json(cache, data)
        terms = query.lower().split()
        results = []
        for identifier, item in data.items():
            haystack = " ".join([identifier, item.get("name", ""), " ".join(item.get("tags", [])),
                                 " ".join(item.get("categories", [])), item.get("description", "")]).lower()
            if not all(term in haystack for term in terms):
                continue
            results.append({"id": identifier, "name": item.get("name", identifier), "provider": provider,
                            "kind": kind, "page": "https://polyhaven.com/a/" + quote(identifier),
                            "license": "CC0-1.0", "license_url": POLY_LICENSE, "commercial_use": True,
                            "authors": item.get("authors", {}), "thumbnail": item.get("thumbnail_url"),
                            "polycount": item.get("polycount")})
            if len(results) == limit:
                break
        return {"provider": provider, "results": results,
                "note": "CC0 covers copyright in these assets; trademark, likeness and other third-party rights may require separate review."}

    def files(self, asset_id):
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,120}", asset_id):
            raise ValueError("Invalid asset id")
        return self.json("https://api.polyhaven.com/files/" + asset_id)

    def download(self, asset_id, kind="models", resolution="1k", max_mb=128):
        if resolution not in ("1k", "2k", "4k", "8k"):
            raise ValueError("Choose 1k, 2k, 4k, or 8k")
        if not 1 <= max_mb <= 1024:
            raise ValueError("max_mb must be 1..1024")
        data = self.files(asset_id)
        if kind == "models":
            entry = data.get("blend", {}).get(resolution, {}).get("blend")
        elif kind == "hdris":
            formats = data.get("hdri", {}).get(resolution, {})
            entry = formats.get("hdr") or formats.get("exr")
        else:
            raise ValueError("Automatic download supports models or hdris; inspect files for texture maps")
        if not entry:
            raise ValueError("Requested format/resolution not available")
        folder = self.root / asset_id / resolution
        folder.mkdir(parents=True, exist_ok=True)
        filename = PurePosixPath(urlparse(entry["url"]).path).name
        plan = [(filename, entry)] + list(entry.get("include", {}).items())
        ceiling = max_mb * 1024 * 1024
        expected = sum(int(value.get("size", 0)) for _, value in plan)
        if expected > ceiling:
            raise ValueError(f"Download size {expected} exceeds budget {ceiling}; choose a lower resolution")
        total, records = 0, []
        for relative, info in plan:
            parts = PurePosixPath(relative)
            if "\\" in relative or parts.is_absolute() or ".." in parts.parts or ":" in relative:
                raise ValueError("Unsafe dependency path")
            path = (folder / relative).resolve()
            if not path.is_relative_to(folder.resolve()):
                raise ValueError("Dependency escapes asset folder")
            content = self.fetch(info["url"], ceiling - total)
            total += len(content)
            if info.get("md5") and hashlib.md5(content).hexdigest() != info["md5"]:
                raise ValueError("Asset checksum mismatch")
            if info.get("size") is not None and len(content) != info["size"]:
                raise ValueError("Asset size mismatch")
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(path.suffix + ".part")
            temporary.write_bytes(content)
            temporary.replace(path)
            records.append({"path": str(path), "url": info["url"], "size": len(content),
                            "sha256": hashlib.sha256(content).hexdigest()})
        record = {"provider": "Poly Haven", "asset": asset_id, "source": "https://polyhaven.com/a/" + asset_id,
                  "license": "CC0-1.0", "license_url": POLY_LICENSE, "legal_code": LICENSE,
                  "retrieved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": records}
        write_json(folder / "provenance.json", record)
        return {"path": str(folder / filename), "provenance": str(folder / "provenance.json"), "bytes": total}

    def polyfork_search(self, query="", limit=10):
        if not 1 <= limit <= 50:
            raise ValueError("limit must be 1..50")
        data = self.json("https://polyfork.dev/api/assets?" + urlencode({"q": query, "free": 1, "per_page": limit}))
        return {"total": data.get("total"), "results": data.get("assets", [])[:limit],
                "license": "Free mesh GLB: CC BY 4.0 with per-asset credit; .mjs and HD excluded",
                "license_url": "https://polyfork.dev/licensing"}

    def polyfork_download(self, asset_id, max_mb=32):
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,120}", asset_id) or not 1 <= max_mb <= 128:
            raise ValueError("Invalid id or download budget")
        info = self.json("https://polyfork.dev/api/assets/" + asset_id)
        if info.get("free") is not True:
            raise ValueError("Only explicitly free low-poly mesh assets can be downloaded")
        credit = info.get("credit")
        if not credit:
            raise ValueError("Source did not supply a credit line; inspect the asset page before download")
        url = "https://polyfork.dev/cdn/" + asset_id + ".glb"
        data = self.fetch(url, max_mb * 1024 * 1024)
        if not data.startswith(b"glTF"):
            raise ValueError("Expected GLB file")
        folder = self.root / "polyfork" / asset_id
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / (asset_id + ".glb")
        path.write_bytes(data)
        record = {"source": "https://polyfork.dev/asset/" + asset_id, "url": url, "license": "CC-BY-4.0",
                  "license_url": "https://creativecommons.org/licenses/by/4.0/", "source_terms": "https://polyfork.dev/licensing",
                  "attribution": credit, "changes_by_user": [], "sha256": hashlib.sha256(data).hexdigest()}
        write_json(folder / "provenance.json", record)
        (folder / "ATTRIBUTION.txt").write_text(str(credit) + "\nCC BY 4.0\n" + record["source"], encoding="utf-8")
        return {"path": str(path), "provenance": str(folder / "provenance.json"), "bytes": len(data)}


COMPOSITIONS = {
    "thirds": {"technique": "Rule of thirds", "lens_mm": 50, "camera": [6, -10, 3], "target": [0, 0, 1.4],
               "notes": "Place subject on a vertical third; preserve lead room toward gaze."},
    "symmetry": {"technique": "Centered symmetry / one-point perspective", "lens_mm": 35, "camera": [0, -12, 1.6],
                 "target": [0, 0, 1.6], "notes": "Align corridor vanishing point; compare The Shining hotel corridors."},
    "low_angle": {"technique": "Low angle", "lens_mm": 28, "camera": [4, -7, .5], "target": [0, 0, 2],
                  "notes": "Keep foreground scale and vertical convergence intentional; compare Citizen Kane."},
    "deep_focus": {"technique": "Deep staging", "lens_mm": 28, "camera": [5, -10, 2], "target": [0, 1, 1.5],
                   "notes": "Stage foreground/midground/background with readable silhouettes; use f/11 or disable DOF."},
    "negative_space": {"technique": "Negative space", "lens_mm": 65, "camera": [7, -12, 3], "target": [0, 0, 1.5],
                       "notes": "Offset the subject and leave breathing room; compare restrained Ozu compositions."},
    "silhouette": {"technique": "Backlit silhouette", "lens_mm": 50, "camera": [0, -9, 1.5], "target": [0, 0, 1.5],
                   "notes": "Separate shape from bright background; compare The Searchers doorway framing."},
}


def film_references(query="", technique="thirds"):
    if technique not in COMPOSITIONS:
        raise ValueError("technique must be one of: " + ", ".join(COMPOSITIONS))
    preset = COMPOSITIONS[technique]
    keywords = (query + " " + preset["technique"] + " cinematography composition").strip()
    encoded = quote(keywords)
    return {"query": keywords, "composition": preset, "links": [
        {"name": "BFI search", "url": "https://www.bfi.org.uk/search?search=" + encoded},
        {"name": "American Cinematographer", "url": "https://www.google.com/search?q=" + quote("site:theasc.com " + keywords)},
        {"name": "FilmGrab film stills", "url": "https://film-grab.com/?s=" + encoded},
        {"name": "Wikimedia Commons", "url": "https://commons.wikimedia.org/w/index.php?search=" + encoded + "&title=Special:MediaSearch&type=image"}],
        "mode": "Curated search links and local composition guidance, not fetched or verified film-still results",
        "rights": "Movie stills are reference material. Do not assume reuse rights. Check each source; Commons licenses vary."}


def asset_sources(query=""):
    q = quote(query)
    return {"sources": [
        {"name": "Poly Haven", "url": "https://polyhaven.com/models", "license": "CC0-1.0",
         "workflow": "asset_search -> asset_download -> import_asset"},
        {"name": "ambientCG", "url": "https://ambientcg.com/list?search=" + q, "license": "CC0-1.0",
         "workflow": "asset_search(provider=ambientcg), download on source website"},
        {"name": "Fab / Quixel Megascans", "url": "https://www.fab.com/search?q=" + quote("Megascans " + query),
         "license": "Fab Standard or item-specific license, NOT CC0", "license_url": "https://www.fab.com/eula",
         "announcement": "https://quixel.com/news/update-megascans-are-going-free-again",
         "announcement_date": "2026-11-05", "announcement_summary": "Full Megascans library free on Fab; verify current item and account entitlement",
         "workflow": "Sign in to Epic/Fab, acquire the item under its displayed terms, download GLB/FBX/OBJ then import_asset. No public unauthenticated download API is assumed.",
         "commercial_use": "Fab Standard permits commercial projects and compatible tools including Blender; no standalone redistribution"},
        {"name": "PLATEAU city tiles / CodePawl", "url": "https://huggingface.co/datasets/codepawl/plateau-city-glb",
         "license": "CC-BY-4.0; original PLATEAU site policy also applies", "workflow": "city_search -> city_download -> city_import"},
        {"name": "Amazon Berkeley Objects / CodePawl", "url": "https://huggingface.co/datasets/codepawl/abo-glb",
         "license": "CC-BY-4.0; Amazon.com attribution and modification notice required",
         "workflow": "abo_search -> abo_download -> import_asset; default web tier needs meshopt support in Blender"},
        {"name": "Scenario 3D Collection", "url": "https://huggingface.co/datasets/scenario-labs/3d-collection",
         "license": "CC-BY-4.0, credit Scenario; AI-generated", "workflow": "scenario_search -> scenario_download -> import_asset; excludes Hunyuan companion"},
        {"name": "Polyfork", "url": "https://polyfork.dev/assets?q=" + q,
         "license": "Free mesh: CC BY 4.0 or Polyfork license; this plugin selects CC BY and preserves credit",
         "workflow": "polyfork_search -> polyfork_download -> import_asset; free low-poly GLB only"},
        {"name": "sand3d", "url": "https://github.com/Sandflow-ai/sand3d", "license": "Apache-2.0 library; linked datasets have separate licenses",
         "workflow": "Procedural Python modeling library, not a model catalog. Optional advanced execute_python integration after local setup; not bundled or automatically executed."}],
         "note": "Only CC0 sources belong in the no-attribution category. Free price does not remove license obligations."}
