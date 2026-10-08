"""Real local HTTP transport with simulated external services."""

from http.client import HTTPConnection
import json
from pathlib import Path
import threading
import time
from typing import Any

import pytest
from test_product import Reasoner, Renderer

from infographic import lib


def test_local_create_refine_download_and_authority_boundaries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    actual_generate = lib.generate

    def generate(*args: Any, **kwargs: Any) -> Any:
        kwargs["intelligence"] = Reasoner(1)
        kwargs["image_service"] = Renderer()
        return actual_generate(*args, **kwargs)

    monkeypatch.setattr(lib, "generate", generate)
    server = lib.dashboard(tmp_path, 0)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=10)
    headers = {"Origin": server.origin, "X-Infographic": "1", "Content-Type": "application/json"}

    def request(
        method: str, path: str, payload: Any = None, extra: dict[str, str] | None = None
    ) -> tuple[int, bytes, Any]:
        connection.request(
            method,
            path,
            body=json.dumps(payload) if payload is not None else None,
            headers={**headers, **(extra or {})},
        )
        response = connection.getresponse()
        return response.status, response.read(), response.headers

    def finish(run_id: str) -> dict[str, Any]:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            code, body, _ = request("GET", f"/api/result/{run_id}")
            assert code == 200
            record = json.loads(body)
            if record["status"] in {"completed", "failed"}:
                return record
            time.sleep(0.02)
        raise AssertionError("Fixture work did not finish")

    try:
        assert request("GET", "/")[0] == 200
        assert request("GET", "/api/results")[0] == 401
        assert request("GET", "/", extra={"Host": "evil.example"})[0] == 403
        assert (
            request(
                "POST", "/api/session", extra={"X-Infographic-Token": server.token, "Origin": "https://evil.example"}
            )[0]
            == 403
        )
        code, _, received = request("POST", "/api/session", extra={"X-Infographic-Token": server.token})
        assert code == 200
        assert "HttpOnly" in received["Set-Cookie"]
        headers["Cookie"] = received["Set-Cookie"].split(";")[0]
        assert request("POST", "/api/generate", {}, {"X-Infographic": ""})[0] == 403
        assert request("POST", "/api/generate", {}, {"Origin": "https://evil.example"})[0] == 403
        request_id = "d" * 32
        payload = {"brief": {"topic": "Heat"}, "request_id": request_id}
        assert request("POST", "/api/generate", payload)[0] == 202
        first = finish(request_id)
        assert first["status"] == "completed"
        code, body, _ = request("GET", f"/artifact/{request_id}/{first['composite']}")
        assert code == 200
        assert body == lib.artifact(request_id, first["composite"], tmp_path)
        assert request("GET", f"/artifact/{request_id}/result.json")[0] == 400
        assert request("GET", "/../../etc/passwd")[0] == 404
        assert request("POST", "/api/generate", payload)[0] == 202
        assert lib.inspect(request_id, tmp_path) == first
        child_id = "e" * 32
        assert (
            request("POST", "/api/refine", {"id": request_id, "feedback": "Bigger labels", "request_id": child_id})[0]
            == 202
        )
        child = finish(child_id)
        assert child["status"] == "completed"
        assert child["parent_id"] == request_id
        assert lib.inspect(request_id, tmp_path) == first
    finally:
        connection.close()
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_port_bounds(tmp_path: Path) -> None:
    from infographic.schemas import InfographicError

    with pytest.raises(InfographicError, match="Port"):
        lib.dashboard(tmp_path, -1)
