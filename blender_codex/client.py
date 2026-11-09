"""Client and owned-process launcher; never kills a user's Blender session."""
import json
from pathlib import Path
import subprocess
import time
from urllib.parse import urlparse
from urllib.request import build_opener, ProxyHandler, Request


class Client:
    def __init__(self, config):
        self.config = config
        self.root = Path(config["data_dir"])
        self.root.mkdir(parents=True, exist_ok=True)
        self.endpoint = self.root / "endpoint.json"
        self.opener = build_opener(ProxyHandler({}))
        self.process = None

    def call(self, action, params=None):
        try:
            endpoint = json.loads(self.endpoint.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise ConnectionError("Blender is disconnected. Call blender_launch or connect the add-on in Blender") from None
        parsed = urlparse(endpoint["url"])
        if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.path != "/rpc" or parsed.username:
            raise ValueError("Invalid local bridge endpoint")
        payload = json.dumps({"action": action, "params": params or {}}, ensure_ascii=False).encode("utf-8")
        request = Request(endpoint["url"], data=payload,
                          headers={"Authorization": "Bearer " + endpoint["token"], "Content-Type": "application/json"})
        try:
            with self.opener.open(request, timeout=self.config["request_timeout"] + 10) as response:
                result = json.load(response)
        except OSError as error:
            raise ConnectionError(f"Blender bridge request failed: {error}. A timed-out command may still be running; inspect state before retrying") from None
        if not result.get("ok"):
            raise RuntimeError(result.get("error", "Unknown Blender error"))
        return result["result"]

    def launch(self, background=False):
        try:
            return {"reused": True, "status": self.call("status")}
        except ConnectionError:
            pass
        executable = Path(self.config["blender_executable"])
        if not executable.is_file():
            raise ValueError("Blender executable not found; set blender_executable in config.json")
        source = Path(__file__).resolve().parents[1]
        args = [str(executable)]
        if background:
            args += ["--background"]
        args += ["--disable-autoexec", "--python", str(source / "bootstrap.py"), "--", "--config", self.config["config_path"]]
        with (self.root / "blender.log").open("a", encoding="utf-8") as log:
            self.process = subprocess.Popen(args, stdout=log, stderr=log,
                                            creationflags=subprocess.CREATE_NO_WINDOW if background and hasattr(subprocess, "CREATE_NO_WINDOW") else 0)
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError("Blender exited during startup. Inspect .state/blender.log")
            try:
                return {"reused": False, "pid": self.process.pid, "status": self.call("status")}
            except ConnectionError:
                time.sleep(.25)
        raise TimeoutError("Blender did not connect within 45 seconds; inspect the log before launching again")
