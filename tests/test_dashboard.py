from __future__ import annotations

import base64

import pytest
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from dashboard.middleware import AuthMiddleware, RateLimitMiddleware


def _scope(path: str, headers: list | None = None):
    return {
        "type": "http",
        "method": "GET",
        "path": path,
        "query_string": b"",
        "headers": headers or [],
        "client": ("1.2.3.4", 0),
    }


async def _ok(request: Request):
    return PlainTextResponse("ok")


@pytest.mark.asyncio
async def test_rate_limit_allows_under_cap() -> None:
    mw = RateLimitMiddleware(_ok)
    req = Request(_scope("/api/stats"))
    resp = await mw.dispatch(req, _ok)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_blocks_over_cap(monkeypatch) -> None:
    monkeypatch.setattr("dashboard.middleware._RATE_LIMIT", 1)
    mw = RateLimitMiddleware(_ok)
    await mw.dispatch(Request(_scope("/api/stats")), _ok)
    resp = await mw.dispatch(Request(_scope("/api/stats")), _ok)
    assert resp.status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_skips_health(monkeypatch) -> None:
    monkeypatch.setattr("dashboard.middleware._RATE_LIMIT", 0)
    mw = RateLimitMiddleware(_ok)
    resp = await mw.dispatch(Request(_scope("/api/health")), _ok)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_auth_passes_when_no_password(monkeypatch) -> None:
    monkeypatch.setattr("dashboard.middleware.settings.dashboard_password", "")
    mw = AuthMiddleware(_ok)
    resp = await mw.dispatch(Request(_scope("/api/stats")), _ok)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_auth_blocks_without_header(monkeypatch) -> None:
    monkeypatch.setattr("dashboard.middleware.settings.dashboard_password", "secret")
    mw = AuthMiddleware(_ok)
    resp = await mw.dispatch(Request(_scope("/api/stats")), _ok)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_auth_passes_with_valid_header(monkeypatch) -> None:
    monkeypatch.setattr("dashboard.middleware.settings.dashboard_password", "secret")
    mw = AuthMiddleware(_ok)
    creds = base64.b64encode(b"user:secret").decode()
    req = Request(_scope("/api/stats", [(b"authorization", f"Basic {creds}".encode())]))
    resp = await mw.dispatch(req, _ok)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_auth_skips_health(monkeypatch) -> None:
    monkeypatch.setattr("dashboard.middleware.settings.dashboard_password", "secret")
    mw = AuthMiddleware(_ok)
    resp = await mw.dispatch(Request(_scope("/api/health")), _ok)
    assert resp.status_code == 200
