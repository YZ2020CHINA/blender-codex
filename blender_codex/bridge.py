"""Authenticated loopback HTTP bridge. All bpy work stays on the main thread."""
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import queue
import secrets
import threading
import time
from pathlib import Path

from .common import write_json

MAX_REQUEST = 2 * 1024 * 1024


class Bridge:
    def __init__(self, config):
        self.config = config
        self.pending = queue.Queue(maxsize=32)
        self.token = secrets.token_urlsafe(32)
        self.stopped = False
        self.endpoint = Path(config["data_dir"]) / "endpoint.json"
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                if self.path != "/rpc":
                    self.send_error(404)
                    return
                if not hmac.compare_digest(self.headers.get("Authorization", ""), "Bearer " + bridge.token):
                    self.send_error(401)
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= MAX_REQUEST:
                        raise ValueError("Invalid request size")
                    self.connection.settimeout(10)
                    request = json.loads(self.rfile.read(length))
                    if not isinstance(request, dict):
                        raise ValueError("Expected a JSON object")
                    job = {"request": request, "event": threading.Event(), "cancelled": False}
                    bridge.pending.put_nowait(job)
                    if not job["event"].wait(bridge.config["request_timeout"]):
                        job["cancelled"] = True
                        self.send_error(504, "Timed out; inspect scene before retrying")
                        return
                    body = json.dumps(job["response"], ensure_ascii=False).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except (ValueError, queue.Full) as error:
                    self.send_error(400, str(error))
                except (OSError, TimeoutError):
                    pass

        self.http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.http.daemon_threads = True

    def start(self):
        import os
        threading.Thread(target=self.http.serve_forever, daemon=True, name="BlenderCodexHTTP").start()
        write_json(self.endpoint, {"url": f"http://127.0.0.1:{self.http.server_port}/rpc",
                                  "token": self.token, "pid": os.getpid(), "started": time.time()})

    def drain(self):
        if self.stopped:
            return None
        from . import scene
        # One command per tick gives the editor time to redraw and handle user input.
        try:
            job = self.pending.get_nowait()
        except queue.Empty:
            return 0.05
        if not job["cancelled"]:
            try:
                value = scene.dispatch(job["request"]["action"], job["request"].get("params", {}), self.config)
                job["response"] = {"ok": True, "result": value}
            except Exception as error:
                import traceback
                traceback.print_exc()
                job["response"] = {"ok": False, "error": f"{type(error).__name__}: {error}"}
            finally:
                job["event"].set()
        return 0.05

    def stop(self):
        self.stopped = True
        self.http.shutdown()
        self.http.server_close()
        try:
            current = json.loads(self.endpoint.read_text(encoding="utf-8"))
            if current.get("token") == self.token:
                self.endpoint.unlink()
        except (OSError, ValueError):
            pass


def start(config):
    import bpy
    bridge = Bridge(config)
    bridge.start()
    if bpy.app.background:
        # Blender background mode does not run the interactive timer event loop.
        try:
            while not bridge.stopped:
                bridge.drain()
                time.sleep(0.025)
        finally:
            bridge.stop()
    else:
        bpy.app.timers.register(bridge.drain, persistent=True)
    return bridge
