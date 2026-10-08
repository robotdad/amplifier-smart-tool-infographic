"""Real public Agent 0.22 + engine against a local simulated Responses service.

This exercises installed SDK plumbing, not live OpenAI service/model quality.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from typing import Any

import pytest
from test_product import png

from infographic.intelligence.agent import AgentIntelligence
from infographic.intelligence.schemas import AgentRequest


@pytest.mark.parametrize("failed", [False, True])
def test_real_public_agent_worker_text_and_image_wire(monkeypatch: pytest.MonkeyPatch, failed: bool) -> None:
    requests: list[dict[str, Any]] = []

    class Endpoint(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            pass

        def do_POST(self) -> None:
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(payload)
            if failed:
                body = json.dumps(
                    {
                        "error": {
                            "message": "secret-token-must-not-leak",
                            "type": "invalid_request_error",
                            "code": "invalid_api_key",
                        }
                    }
                ).encode()
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            message = {
                "id": "msg_local",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "text": '{"ok":true}', "annotations": []}],
            }
            response = {
                "id": "resp_local",
                "object": "response",
                "created_at": 1,
                "model": payload["model"],
                "status": "completed",
                "output": [message],
                "usage": {
                    "input_tokens": 20,
                    "output_tokens": 5,
                    "total_tokens": 25,
                    "input_tokens_details": {"cached_tokens": 0},
                    "output_tokens_details": {"reasoning_tokens": 0},
                },
            }
            if payload.get("stream"):
                events = [
                    {"type": "response.created", "response": {**response, "status": "in_progress", "output": []}},
                    {
                        "type": "response.output_item.added",
                        "output_index": 0,
                        "item": {**message, "status": "in_progress", "content": []},
                    },
                    {
                        "type": "response.content_part.added",
                        "item_id": "msg_local",
                        "output_index": 0,
                        "content_index": 0,
                        "part": {"type": "output_text", "text": "", "annotations": []},
                    },
                    {
                        "type": "response.output_text.delta",
                        "item_id": "msg_local",
                        "output_index": 0,
                        "content_index": 0,
                        "delta": '{"ok":true}',
                    },
                    {
                        "type": "response.output_text.done",
                        "item_id": "msg_local",
                        "output_index": 0,
                        "content_index": 0,
                        "text": '{"ok":true}',
                    },
                    {
                        "type": "response.content_part.done",
                        "item_id": "msg_local",
                        "output_index": 0,
                        "content_index": 0,
                        "part": message["content"][0],
                    },
                    {"type": "response.output_item.done", "output_index": 0, "item": message},
                    {"type": "response.completed", "response": response},
                ]
                body = "".join(f"event: {event['type']}\ndata: {json.dumps(event)}\n\n" for event in events).encode()
                mime = "text/event-stream"
            else:
                body = json.dumps(response).encode()
                mime = "application/json"
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Endpoint)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-not-a-real-key")
    monkeypatch.setenv("OPENAI_BASE_URL", f"http://127.0.0.1:{server.server_port}/v1")
    monkeypatch.setenv("AMPLIFIER_AGENT_CONFIG", "/host/config-must-not-be-read.json")
    monkeypatch.setenv("AMPLIFIER_AGENT_MODEL", "host-model-must-not-be-used")
    try:
        result = AgentIntelligence().run(
            AgentRequest(
                prompt="Inspect these actual fixture pixels.",
                provider="openai",
                model="gpt-6-astra",
                images=[png()],
                output_schema={
                    "type": "object",
                    "required": ["ok"],
                    "properties": {"ok": {"type": "boolean"}},
                    "additionalProperties": False,
                },
                timeout_seconds=30,
            )
        )
        if failed:
            assert result.error
            assert "secret-token" not in result.error
            assert result.output is None
        else:
            assert result.error is None, result.error
            assert result.output == {"ok": True}
        assert len(requests) == 1
        wire = requests[0]
        assert wire["model"] == "gpt-6-astra"
        assert not wire.get("tools")
        assert wire["reasoning"]["effort"] == "medium"
        assert "data:image/png;base64," in json.dumps(wire)
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
