"""Isolated HTTP/session tests with a fake provider; these are not Gemini E2E tests."""

import json
from threading import Thread
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener
from uuid import uuid4

import pytest

from emporio_music.browser import create_server
from emporio_music.config import Settings


class FakeSession:
    """Expose per-session state so HTTP isolation can be verified without a model."""

    def __init__(self, settings):
        self.messages = []
        self.closed = False

    def send(self, message):
        assert not self.closed
        self.messages.append(message)
        return SimpleNamespace(
            text=" | ".join(self.messages),
            tool_calls=[{
                "name": "get_policy_pages",
                "arguments": {"internal": "not-for-browser"},
                "result": {"source": "synthetic.pdf", "pages": [{"page": 2, "text": "untrusted source text"}]},
            }],
        )

    def close(self):
        self.closed = True


@pytest.fixture
def chat_server(tmp_path):
    servers = []

    def start(factory=FakeSession):
        settings = Settings(tmp_path / "raw", tmp_path / "test.sqlite3", tmp_path / "policies.pdf", tmp_path)
        server = create_server(settings, port=0, session_factory=factory)
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        servers.append((server, thread))
        origin = server.url
        opener = build_opener(ProxyHandler({}))

        def request(path, payload=None, *, raw=None, headers=None):
            body = raw if raw is not None else json.dumps(payload).encode("utf-8") if payload is not None else None
            defaults = {"Content-Type": "application/json", "X-Emporio-Client": "browser"} if body is not None else {}
            operation = Request(origin + path, data=body, headers={**defaults, **(headers or {})})
            try:
                response = opener.open(operation, timeout=5)
            except HTTPError as error:
                response = error
            with response:
                return response.status, json.loads(response.read().decode("utf-8"))

        return request, server

    yield start
    for server, thread in servers:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_isolated_browser_sessions_preserve_followups_without_sharing_context(chat_server):
    request, _ = chat_server()
    status, configuration = request("/api/chat/status")
    assert status == 200 and configuration["configured"] is True
    assert configuration["model"] == "isolated-test"

    status, first = request("/api/chat", {"message": "First customer context"})
    assert status == 200
    first_id = first["session_id"]
    status, second = request("/api/chat", {"message": "Independent customer context"})
    assert status == 200 and second["session_id"] != first_id
    assert second["reply"] == "Independent customer context"

    status, followup = request("/api/chat", {"session_id": first_id, "message": "Follow-up"})
    assert status == 200 and followup["reply"] == "First customer context | Follow-up"
    assert followup["tool_calls"] == [{"name": "get_policy_pages", "sources": ["synthetic.pdf, page 2"]}]
    assert "not-for-browser" not in json.dumps(followup)
    assert "untrusted source text" not in json.dumps(followup)

    status, reset = request("/api/chat/reset", {"session_id": first_id})
    assert status == 200 and reset == {"reset": True}
    status, expired = request("/api/chat", {"session_id": first_id, "message": "Try old context"})
    assert status == 404 and expired["code"] == "session_not_found"
    status, untouched = request("/api/chat", {"session_id": second["session_id"], "message": "Another turn"})
    assert status == 200 and untouched["reply"] == "Independent customer context | Another turn"


@pytest.mark.parametrize(("code", "expected_status"), [
    ("model_not_configured", 503), ("rate_limited", 429), ("unrecognized_provider_error", 502),
    ("provider_access_denied", 503), ("model_unavailable", 503), ("session_limit", 409),
])
def test_isolated_provider_errors_are_explicit_and_never_leak_details(chat_server, code, expected_status):
    class FakeProviderError(Exception):
        pass

    def blocked_factory(settings):
        error = FakeProviderError("sensitive-provider-request-value")
        error.code = code
        raise error

    request, server = chat_server(blocked_factory)
    status, payload = request("/api/chat", {"message": "A free-form question"})
    assert status == expected_status
    assert "sensitive-provider-request-value" not in json.dumps(payload)
    assert not server.conversations


@pytest.mark.parametrize("payload", [
    [], {"message": ""}, {"message": 42}, {"message": "x" * 4001},
    {"message": "Valid text", "session_id": ["invalid"]},
])
def test_browser_chat_rejects_invalid_messages_and_identifiers(chat_server, payload):
    request, _ = chat_server()
    status, result = request("/api/chat", payload)
    assert status == 400 and result["code"] == "invalid_request"


def test_browser_chat_rejects_unknown_sessions_unsafe_requests_and_large_bodies(chat_server):
    request, _ = chat_server()
    status, result = request("/api/chat", {"message": "Hello", "session_id": str(uuid4())})
    assert status == 404 and result["code"] == "session_not_found"
    status, result = request("/api/chat", {"message": "Hello"}, headers={"Origin": "https://another.example"})
    assert status == 403
    status, result = request("/api/chat", raw=b"not-json")
    assert status == 400 and result["code"] == "invalid_request"
    status, result = request("/api/chat", raw=b"x" * 8193)
    assert status == 400 and result["code"] == "invalid_request"
    status, result = request("/api/chat", raw=b"message=hello", headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert status == 400 and result["code"] == "invalid_request"
