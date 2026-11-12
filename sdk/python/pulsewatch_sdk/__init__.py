"""Dependency-free Python error reporting client for PulseWatch."""
from __future__ import annotations
import asyncio
import json
import os
import traceback
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Any


class PulseWatch:
    def __init__(self, dsn: str | None = None, environment: str | None = None, timeout: float = 3.0):
        self.dsn = (dsn or os.getenv("PULSEWATCH_DSN", "")).rstrip("/")
        if not self.dsn:
            raise ValueError("PulseWatch requires a DSN (or PULSEWATCH_DSN environment variable)")
        self.environment = environment or os.getenv("PULSEWATCH_ENVIRONMENT", "production")
        self.timeout = max(0.2, min(float(timeout), 15.0))
        self.tags: dict[str, Any] = {}
        self.breadcrumbs: list[dict[str, Any]] = []
        self.user_id: str | None = None

    def set_user(self, user_id: str | None) -> None:
        self.user_id = user_id

    def set_tag(self, key: str, value: Any) -> None:
        self.tags[key] = value

    def add_breadcrumb(self, category: str, message: str, data: dict[str, Any] | None = None, level: str = "info") -> None:
        self.breadcrumbs.append({"category": category, "message": message, "data": data or {}, "level": level,
                                 "timestamp": datetime.now(timezone.utc).isoformat()})
        self.breadcrumbs = self.breadcrumbs[-20:]

    def capture_exception(self, error: BaseException, context: dict[str, Any] | None = None) -> str:
        event_id = str(uuid.uuid4())
        payload = {
            "event_id": event_id, "message": str(error) or type(error).__name__,
            "exception_type": type(error).__name__,
            "stacktrace": "".join(traceback.format_exception(type(error), error, error.__traceback__)),
            "severity": "error", "environment": self.environment,
            "timestamp": datetime.now(timezone.utc).isoformat(), "user_id": self.user_id,
            "context": context or {}, "tags": dict(self.tags), "breadcrumbs": list(self.breadcrumbs),
        }
        self._send(payload)
        return event_id

    def capture_message(self, message: str, severity: str = "info", context: dict[str, Any] | None = None) -> str:
        event_id = str(uuid.uuid4())
        payload = {
            "event_id": event_id, "message": message, "exception_type": "Message", "stacktrace": "",
            "severity": severity, "environment": self.environment,
            "timestamp": datetime.now(timezone.utc).isoformat(), "user_id": self.user_id,
            "context": context or {}, "tags": dict(self.tags), "breadcrumbs": list(self.breadcrumbs),
        }
        self._send(payload)
        return event_id

    def _send(self, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        request = urllib.request.Request(self.dsn, data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                if response.status >= 400:
                    raise RuntimeError(f"PulseWatch returned HTTP {response.status}")
        except (urllib.error.URLError, TimeoutError, OSError):
            # Monitoring failures must not mask the application's original failure.
            return


_default: PulseWatch | None = None


class PulseWatchASGIMiddleware:
    """Capture unhandled ASGI request exceptions, then re-raise for normal server handling."""
    def __init__(self, app, client: PulseWatch):
        self.app = app
        self.client = client

    async def __call__(self, scope, receive, send):
        try:
            await self.app(scope, receive, send)
        except Exception as exc:
            if scope.get("type") == "http":
                await asyncio.to_thread(self.client.capture_exception, exc, {
                    "path": scope.get("path"), "method": scope.get("method"),
                    "http_version": scope.get("http_version"),
                })
            raise


def integrate_fastapi(app, client: PulseWatch | None = None):
    """Attach the dependency-free ASGI middleware to a FastAPI/Starlette app."""
    selected = client or _default
    if selected is None:
        raise RuntimeError("Call pulsewatch_sdk.init() before integrate_fastapi()")
    app.add_middleware(PulseWatchASGIMiddleware, client=selected)
    return app


def init(dsn: str | None = None, environment: str | None = None, timeout: float = 3.0) -> PulseWatch:
    global _default
    _default = PulseWatch(dsn, environment, timeout)
    return _default


def capture_exception(error: BaseException, context: dict[str, Any] | None = None) -> str:
    if _default is None:
        raise RuntimeError("Call pulsewatch_sdk.init() before capturing events")
    return _default.capture_exception(error, context)


def capture_message(message: str, severity: str = "info", context: dict[str, Any] | None = None) -> str:
    if _default is None:
        raise RuntimeError("Call pulsewatch_sdk.init() before capturing events")
    return _default.capture_message(message, severity, context)


def add_breadcrumb(category: str, message: str, data: dict[str, Any] | None = None, level: str = "info") -> None:
    if _default is not None:
        _default.add_breadcrumb(category, message, data, level)


def set_user(user_id: str | None) -> None:
    if _default is not None:
        _default.set_user(user_id)

__all__ = ["PulseWatch", "PulseWatchASGIMiddleware", "init", "integrate_fastapi", "capture_exception", "capture_message", "add_breadcrumb", "set_user"]
