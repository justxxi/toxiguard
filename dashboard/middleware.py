from __future__ import annotations

import base64
import secrets
import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from core import redis as _redis
from core.config import settings

_RATE_WINDOW = 60
_RATE_LIMIT = 60
_request_log: dict[str, list[float]] = defaultdict(list)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api/") or request.url.path == "/api/health":
            return await call_next(request)

        host = request.client.host if request.client else "unknown"
        key = f"rl:{host}"
        count = await _redis.incr(key, _RATE_WINDOW)
        if count and count > _RATE_LIMIT:
            return Response("Too Many Requests", status_code=429)
        if not count:
            now = time.monotonic()
            window = [t for t in _request_log[host] if now - t < _RATE_WINDOW]
            if not window:
                _request_log.pop(host, None)
            else:
                _request_log[host] = window
            if len(window) >= _RATE_LIMIT:
                return Response("Too Many Requests", status_code=429)
            _request_log[host].append(now)
        return await call_next(request)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api/") or request.url.path == "/api/health":
            return await call_next(request)
        if not settings.dashboard_password:
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Basic "):
            return _unauthorized()
        try:
            decoded = base64.b64decode(auth[6:]).decode()
            _, pwd = decoded.split(":", 1)
        except Exception:
            return _unauthorized()
        if not secrets.compare_digest(pwd, settings.dashboard_password):
            return _unauthorized()
        return await call_next(request)


def _unauthorized() -> Response:
    return Response(
        "Unauthorized",
        status_code=401,
        headers={"WWW-Authenticate": "Basic"},
    )
