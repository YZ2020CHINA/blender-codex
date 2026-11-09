"""Production layout; actual user confirmation remains required by the skill."""
import json
from pathlib import Path


def initialize(directory, title="Untitled production"):
    root = Path(directory).resolve()
    if root.exists() and any(root.iterdir()):
        raise ValueError("Choose a new or empty folder to avoid mixing projects")
    for relative in ("source/blender", "source/threejs", "assets/models", "assets/textures", "assets/references",
                     "previews", "renders", "licenses", "delivery/成品交付"):
        (root / relative).mkdir(parents=True, exist_ok=True)
    review = {"title": title, "current_stage": 1, "requirements": {}, "stage_confirmations": [],
              "selected_assets": [], "open_questions": [], "previews": [], "revisions": [], "delivery_approved": False}
    (root / "production-review.json").write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "README.md").write_text(f"# {title}\n\nsource/：可编辑工程。assets/：素材和参考。licenses/：许可与署名。\n\n"
        "previews/：小样。renders/：中间渲染。delivery/成品交付/：成品与说明。\n\n"
        "production-review.json：六阶段确认记录。当前待用户确认，尚未交付。\n", encoding="utf-8")
    delivery = root / "delivery/成品交付/交付说明.md"
    delivery.write_text(f"# {title} · 交付说明\n\n状态：待制作、待用户验收。请在正式交付前填写。\n\n"
        "## 成品清单\n\n文件名、用途、版本、格式、分辨率/帧率/时长和校验值。\n\n"
        "## 打开使用\n\n软件版本、打开步骤；网页 HTTP 启动方法和联网依赖。\n\n"
        "## 可编辑工程\n\nsource/ 路径、贴图依赖及是否打包、相机和动画范围。\n\n"
        "## 素材授权\n\n来源链接、许可、署名与修改说明，附 licenses/ 清单。\n\n"
        "## 验收和限制\n\n用户确认记录、播放/导入测试、已知限制和未完成项。\n", encoding="utf-8")
    return {"directory": str(root), "delivery": str(delivery.parent), "status": "requirements_pending_confirmation"}
