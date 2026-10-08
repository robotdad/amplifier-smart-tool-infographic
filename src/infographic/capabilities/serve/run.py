"""Private loopback dashboard. No arbitrary paths, remote binding or model-owned tools."""

import base64
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
from typing import Any
from urllib.parse import urlsplit

from pydantic import ValidationError

from infographic.models import Brief
from infographic.schemas import InfographicError


class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, store: Path, port: int) -> None:
        self.store = store
        self.token = secrets.token_urlsafe(32)
        self.admission = threading.Lock()
        super().__init__(("127.0.0.1", port), Handler)
        self.origin = f"http://127.0.0.1:{self.server_port}"
        self.url = self.origin + "/#token=" + self.token


class Handler(BaseHTTPRequestHandler):
    server: DashboardServer

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def _reply(self, code: int, data: Any, mime: str = "application/json", cookie: bool = False) -> None:
        body = data if isinstance(data, bytes) else json.dumps(data, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
        )
        if cookie:
            self.send_header("Set-Cookie", f"infographic={self.server.token}; HttpOnly; SameSite=Strict; Path=/")
        self.end_headers()
        self.wfile.write(body)

    def _host(self) -> bool:
        return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

    def _authenticated(self) -> bool:
        cookies = SimpleCookie()
        try:
            cookies.load(self.headers.get("Cookie", ""))
        except Exception:
            return False
        value = cookies.get("infographic")
        return value is not None and secrets.compare_digest(value.value, self.server.token)

    def do_GET(self) -> None:
        from infographic import lib

        if not self._host():
            self._reply(403, {"error": "Unrecognized host."})
            return
        path = urlsplit(self.path).path
        static = {
            "/": ("index.html", "text/html"),
            "/app.js": ("app.js", "text/javascript"),
            "/style.css": ("style.css", "text/css"),
        }
        if path in static:
            name, mime = static[path]
            self._reply(200, (Path(__file__).parent / name).read_bytes(), mime)
            return
        if not self._authenticated():
            self._reply(401, {"error": "Open the full URL printed by infographic serve to connect."})
            return
        try:
            if path == "/api/results":
                self._reply(200, lib.list_results(self.server.store))
            elif path == "/api/check":
                self._reply(200, lib.check())
            elif path.startswith("/api/result/"):
                self._reply(200, lib.inspect(path.removeprefix("/api/result/"), self.server.store))
            elif path.startswith("/artifact/"):
                parts = path.split("/")
                if len(parts) != 4:
                    raise InfographicError("Unknown artifact.")
                self._reply(200, lib.artifact(parts[2], parts[3], self.server.store), "image/png")
            else:
                self._reply(404, {"error": "Not found."})
        except InfographicError as exc:
            self._reply(400, {"error": str(exc)})

    def do_POST(self) -> None:
        from infographic import lib

        if not self._host() or self.headers.get("Origin") != self.server.origin:
            self._reply(403, {"error": "Same-origin local requests only."})
            return
        path = urlsplit(self.path).path
        if path == "/api/session":
            if secrets.compare_digest(self.headers.get("X-Infographic-Token", ""), self.server.token):
                self._reply(200, {"connected": True}, cookie=True)
            else:
                self._reply(401, {"error": "Invalid launch token."})
            return
        if not self._authenticated() or self.headers.get("X-Infographic") != "1":
            self._reply(403, {"error": "Authenticated dashboard request required."})
            return
        if path not in {"/api/generate", "/api/refine", "/api/select", "/api/close-interrupted"}:
            self._reply(404, {"error": "Not found."})
            return
        if not self.server.admission.acquire(blocking=False):
            self._reply(409, {"error": "Another request is being admitted. Try again."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 32 * 1024 * 1024:
                raise InfographicError("Request exceeds 32 MiB. Use smaller reference uploads.")
            if self.headers.get("Content-Type") != "application/json":
                raise InfographicError("Use application/json.")
            self.connection.settimeout(20)
            payload = json.loads(self.rfile.read(length))
            request_id = payload.get("request_id")

            def uploads(key: str, limit: int) -> list[bytes] | None:
                if key not in payload:
                    return None
                encoded = payload[key]
                if not isinstance(encoded, list) or len(encoded) > limit:
                    raise InfographicError(f"Use at most {limit} {key}.")
                result = [base64.b64decode(value, validate=True) for value in encoded]
                if any(len(value) > 4 * 1024 * 1024 for value in result):
                    raise InfographicError("Each browser reference must be at most 4 MiB.")
                return result

            if path != "/api/close-interrupted" and not isinstance(request_id, str):
                raise InfographicError("A stable request_id is required for every submitted operation.")
            if path == "/api/generate":
                result = lib.generate(
                    Brief.model_validate(payload["brief"]),
                    self.server.store,
                    request_id=request_id,
                    background=True,
                    references=uploads("references", 3),
                    style_references=uploads("style_references", 2),
                )
            elif path == "/api/refine":
                result = lib.refine(
                    payload["id"],
                    payload["feedback"],
                    self.server.store,
                    changes=payload.get("changes"),
                    request_id=request_id,
                    background=True,
                    references=uploads("references", 3),
                    style_references=uploads("style_references", 2),
                )
            elif path == "/api/select":
                if not isinstance(payload["candidate"], int):
                    raise InfographicError("Candidate must be an integer.")
                result = lib.select(payload["id"], payload["candidate"], self.server.store, request_id, background=True)
            else:
                result = lib.close_interrupted(payload["id"], self.server.store)
            self._reply(202, {"id": result["id"], "status": result["status"]})
        except (ValueError, KeyError, TypeError, ValidationError):
            self._reply(400, {"error": "Invalid request fields. Check the brief and provider settings."})
        except InfographicError as exc:
            self._reply(409, {"error": str(exc)})
        finally:
            self.server.admission.release()


def dashboard(store: Path, port: int = 8765) -> DashboardServer:
    if not 0 <= port <= 65535:
        raise InfographicError("Port must be 0 to 65535.")
    return DashboardServer(store, port)
