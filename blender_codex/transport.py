"""Windows system-TLS fallback; validate every redirect and enforce a file budget."""
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import urljoin


def windows_download(url, destination, limit, proxy, validator):
    curl = Path("C:/Windows/System32/curl.exe")
    if not curl.is_file():
        raise OSError("Windows system curl is unavailable")
    destination = Path(destination)
    with tempfile.TemporaryDirectory(prefix="blender-tls-") as temporary:
        headers = Path(temporary) / "headers.txt"
        for _ in range(8):
            validator(url)
            # No -L: redirects are individually validated before the next request.
            args = [str(curl), "--silent", "--show-error", "--ssl-revoke-best-effort", "--retry", "2", "--retry-all-errors", "--max-time", "90",
                    "--max-filesize", str(limit), "--dump-header", str(headers), "--output", str(destination),
                    "--write-out", "%{http_code}", "--user-agent", "BlenderCodexStudio/1.0", url]
            if proxy:
                args += ["--proxy", proxy]
            result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if result.returncode:
                raise OSError(f"System TLS download failed (curl {result.returncode}); check connectivity")
            status = int(result.stdout[-3:])
            if status in (301, 302, 303, 307, 308):
                locations = [line.split(":", 1)[1].strip() for line in headers.read_text(errors="replace").splitlines()
                             if line.lower().startswith("location:")]
                if not locations:
                    raise OSError("Redirect has no Location")
                url = urljoin(url, locations[-1])
                continue
            if status != 200:
                raise OSError(f"Asset server returned HTTP {status}")
            if destination.stat().st_size > limit:
                raise ValueError("Download exceeds budget")
            return
    raise OSError("Too many asset redirects")
