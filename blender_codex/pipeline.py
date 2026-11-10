"""Reference -> Three.js -> Blender -> delivery pipeline records.

This module records decisions and evidence beside a user project. It does not
download images or silently approve a production stage.
"""
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

STAGES = ("references", "threejs", "blender_import", "blender_optimization", "delivery")
STATUSES = ("pending", "in_progress", "review", "passed", "blocked")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _root(directory):
    root = Path(directory).resolve()
    if not root.is_dir():
        raise ValueError("Pipeline directory must be an existing project folder")
    return root


def _path(root):
    return root / "production-pipeline.json"


def _write(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _read(root):
    path = _path(root)
    if not path.exists():
        raise ValueError("No production-pipeline.json; call pipeline_init first")
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != 1 or set(value.get("stages", {})) != set(STAGES):
        raise ValueError("Unsupported production pipeline record")
    return value


def _relative(root, value):
    candidate = Path(value)
    candidate = (candidate if candidate.is_absolute() else root / candidate).resolve()
    try:
        return candidate.relative_to(root).as_posix()
    except ValueError:
        return str(candidate)


def init(directory, title="Untitled production"):
    root = _root(directory)
    path = _path(root)
    if path.exists():
        raise ValueError("production-pipeline.json already exists; use pipeline_status or pipeline_stage")
    stages = {name: {"status": "pending", "artifacts": [], "evidence": [], "notes": []} for name in STAGES}
    value = {"schema": 1, "title": title, "project_root": str(root), "created_at": _now(),
             "updated_at": _now(), "references": [], "stages": stages,
             "quality_gates": ["reference source and license recorded", "Three.js preview reviewed",
                               "GLB import checked in Blender", "Blender render and saved reopen checked",
                               "final export and delivery manifest reviewed"],
             "delivery_approved": False}
    _write(path, value)
    return {"path": str(path), "stages": list(STAGES), "status": "initialized"}


def record_reference(directory, source, role="reference", license_name="unverified", verified=False,
                     local_path="", notes=""):
    root = _root(directory)
    value = _read(root)
    record = {"source": source, "role": role, "license": license_name, "verified": bool(verified),
              "notes": notes, "recorded_at": _now()}
    if local_path:
        source_path = Path(local_path)
        source_path = (source_path if source_path.is_absolute() else root / source_path).resolve(strict=True)
        if source_path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp", ".avif"):
            raise ValueError("Reference preview must be PNG, JPEG, WebP or AVIF")
        target_dir = root / "assets" / "references"
        target_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
        target = target_dir / (digest + source_path.suffix.lower())
        if source_path != target:
            shutil.copy2(source_path, target)
        record.update({"local_path": _relative(root, target), "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                       "bytes": target.stat().st_size})
    value["references"].append(record)
    _invalidate(value, "references")
    value["stages"]["references"]["status"] = "review"
    value["stages"]["references"]["evidence"].append(record.get("local_path", source))
    value["updated_at"] = _now()
    _write(_path(root), value)
    return record


def _invalidate(value, stage):
    for name in STAGES[STAGES.index(stage) + 1:]:
        if value["stages"][name]["status"] == "passed":
            value["stages"][name]["status"] = "review"
    value["delivery_approved"] = False
    value.pop("approval", None)


def record_stage(directory, stage, status, artifacts=(), evidence=(), notes=""):
    root = _root(directory)
    if stage not in STAGES:
        raise ValueError("Unknown pipeline stage: " + stage)
    if status not in STATUSES:
        raise ValueError("Unknown pipeline status: " + status)
    value = _read(root)
    current = value["stages"][stage]
    current["updated_at"] = _now()
    for item in artifacts:
        relative = _relative(root, item)
        if relative not in current["artifacts"]:
            current["artifacts"].append(relative)
    for item in evidence:
        if item not in current["evidence"]:
            current["evidence"].append(item)
    if notes:
        current["notes"].append(notes)
    if status == "passed":
        previous = STAGES[:STAGES.index(stage)]
        if any(value["stages"][name]["status"] != "passed" for name in previous):
            raise ValueError("Previous pipeline stages must pass first")
        if not current["evidence"]:
            raise ValueError("Passing a stage requires recorded review/test evidence")
        if stage == "references" and not value["references"]:
            raise ValueError("Record at least one reference source first")
        if stage != "references" and not current["artifacts"]:
            raise ValueError("Passing a stage requires existing artifacts")
        for item in current["artifacts"]:
            if not (root / item).is_file():
                raise ValueError("Artifact must be an existing file: " + item)
    _invalidate(value, stage)
    current["status"] = status
    value["updated_at"] = _now()
    _write(_path(root), value)
    return {"stage": stage, "status": status, "artifacts": current["artifacts"], "evidence": current["evidence"]}


def status(directory):
    root = _root(directory)
    value = _read(root)
    return {"path": str(_path(root)), "title": value["title"], "updated_at": value["updated_at"],
            "references": len(value["references"]), "stages": value["stages"],
            "delivery_approved": value["delivery_approved"]}


def delivery_check(directory):
    root = _root(directory)
    value = _read(root)
    missing = []
    for stage in STAGES:
        if value["stages"][stage]["status"] != "passed":
            missing.append(f"{stage}: status is {value['stages'][stage]['status']}")
        entry = value["stages"][stage]
        if not entry["evidence"]:
            missing.append(stage + ": missing evidence")
        if stage != "references" and not entry["artifacts"]:
            missing.append(stage + ": missing artifacts")
        for item in entry["artifacts"]:
            if not (root / item).is_file():
                missing.append(f"missing artifact: {item}")
    if not value["references"]:
        missing.append("missing reference sources")
    return {"passed": not missing, "ready_for_user_review": not missing, "missing": missing,
            "delivery_approved": value["delivery_approved"]}


def approve(directory, user_confirmation):
    """The caller must supply an actual user's approval, never a tool result."""
    if not user_confirmation.strip():
        raise ValueError("Record the user's explicit final approval")
    result = delivery_check(directory)
    if not result["passed"]:
        raise ValueError("Delivery technical checks have not passed: " + "; ".join(result["missing"]))
    root = _root(directory)
    value = _read(root)
    value["delivery_approved"] = True
    value["approval"] = {"user_confirmation": user_confirmation, "recorded_at": _now()}
    value["updated_at"] = _now()
    _write(_path(root), value)
    return {"delivery_approved": True, "approval": value["approval"]}


def auto_stage(directory, stage, artifacts=(), notes=""):
    """Record an observed integration event without marking it user-approved."""
    return record_stage(directory, stage, "review", artifacts=artifacts, evidence=["tool result"], notes=notes)
