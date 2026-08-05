import httpx

from app.models.monitoring import (
    REASON_ERROR_PATTERN,
    REASON_HTTP_STATUS,
    REASON_NETWORK,
    REASON_OK,
)
from app.services.link_checker import check_url

PATTERNS = ["page introuvable", "404 not found"]


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_200_without_error_pattern_is_ok():
    async def handler(request):
        return httpx.Response(200, text="<html>Prendre rendez-vous</html>")

    async with _client(handler) as client:
        outcome = await check_url(client, "https://o.example/r/abc", PATTERNS)

    assert outcome.ok is True
    assert outcome.reason == REASON_OK
    assert outcome.status_code == 200


async def test_404_is_broken():
    async def handler(request):
        return httpx.Response(404, text="not found")

    async with _client(handler) as client:
        outcome = await check_url(client, "https://o.example/r/abc", PATTERNS)

    assert outcome.ok is False
    assert outcome.reason == REASON_HTTP_STATUS
    assert outcome.status_code == 404


async def test_soft_404_is_broken():
    """Odoo answers 200 with an error page — the pattern catches it."""

    async def handler(request):
        return httpx.Response(200, text="<h1>Page introuvable</h1>")

    async with _client(handler) as client:
        outcome = await check_url(client, "https://o.example/r/abc", PATTERNS)

    assert outcome.ok is False
    assert outcome.reason == REASON_ERROR_PATTERN
    assert "page introuvable" in (outcome.error or "").lower()


async def test_no_pattern_configured_keeps_a_200_ok():
    async def handler(request):
        return httpx.Response(200, text="<h1>Page introuvable</h1>")

    async with _client(handler) as client:
        outcome = await check_url(client, "https://o.example/r/abc", [])

    assert outcome.ok is True


async def test_network_error_is_broken():
    async def handler(request):
        raise httpx.ConnectError("connexion refusée", request=request)

    async with _client(handler) as client:
        outcome = await check_url(client, "https://o.example/r/abc", PATTERNS)

    assert outcome.ok is False
    assert outcome.reason == REASON_NETWORK
    assert outcome.status_code is None
