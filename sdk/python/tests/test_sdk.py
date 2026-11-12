import json
import urllib.request
from unittest.mock import Mock

from pulsewatch_sdk import PulseWatch


def test_capture_exception_builds_payload_and_preserves_breadcrumbs(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        response = Mock()
        response.status = 202
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        return response

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    client = PulseWatch("http://localhost:8000/api/v1/ingest/pw_pub_test", environment="test")
    client.set_user("user-17")
    client.add_breadcrumb("checkout", "Opened checkout", {"cart_items": 2})

    try:
        raise RuntimeError("payment timeout")
    except RuntimeError as exc:
        event_id = client.capture_exception(exc, {"route": "/checkout"})

    payload = captured["payload"]
    assert captured["url"].endswith("pw_pub_test")
    assert captured["timeout"] == 3.0
    assert payload["event_id"] == event_id
    assert payload["exception_type"] == "RuntimeError"
    assert "payment timeout" in payload["stacktrace"]
    assert payload["environment"] == "test"
    assert payload["user_id"] == "user-17"
    assert payload["context"]["route"] == "/checkout"
    assert payload["breadcrumbs"][0]["message"] == "Opened checkout"


def test_transport_failure_does_not_escape_to_monitored_application(monkeypatch):
    def fail_urlopen(*_args, **_kwargs):
        raise OSError("network unavailable")

    monkeypatch.setattr(urllib.request, "urlopen", fail_urlopen)
    client = PulseWatch("http://localhost:8000/api/v1/ingest/pw_pub_test")
    event_id = client.capture_message("checkout started")
    assert event_id
