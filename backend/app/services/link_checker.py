"""Single-URL availability check.

Odoo does not always answer 404 on a dead appointment link: a mistyped shortcode
can land on a generic page returned with HTTP 200. So a link is considered
broken when the status is >= 400 *or* when the body contains one of the
company's configured error patterns.
"""

import time
from dataclasses import dataclass

import httpx

from app.models.monitoring import (
    REASON_ERROR_PATTERN,
    REASON_HTTP_STATUS,
    REASON_NETWORK,
    REASON_OK,
)


@dataclass(frozen=True)
class CheckOutcome:
    ok: bool
    reason: str
    status_code: int | None = None
    response_time_ms: int | None = None
    final_url: str | None = None
    error: str | None = None


def evaluate_body(body: str, error_patterns: list[str]) -> str | None:
    """Return the pattern that matched, or None."""
    haystack = body.lower()
    for pattern in error_patterns:
        needle = pattern.strip().lower()
        if needle and needle in haystack:
            return pattern
    return None


async def check_url(
    client: httpx.AsyncClient,
    url: str,
    error_patterns: list[str],
    body_read_bytes: int = 200_000,
) -> CheckOutcome:
    started = time.perf_counter()
    try:
        response = await client.get(url)
    except httpx.HTTPError as exc:
        elapsed = int((time.perf_counter() - started) * 1000)
        return CheckOutcome(
            ok=False,
            reason=REASON_NETWORK,
            response_time_ms=elapsed,
            error=f"{type(exc).__name__}: {exc}".strip(": "),
        )

    elapsed = int((time.perf_counter() - started) * 1000)
    final_url = str(response.url)

    if response.status_code >= 400:
        return CheckOutcome(
            ok=False,
            reason=REASON_HTTP_STATUS,
            status_code=response.status_code,
            response_time_ms=elapsed,
            final_url=final_url,
            error=f"HTTP {response.status_code}",
        )

    matched = None
    if error_patterns:
        try:
            matched = evaluate_body(response.text[:body_read_bytes], error_patterns)
        except UnicodeDecodeError:
            matched = None

    if matched:
        return CheckOutcome(
            ok=False,
            reason=REASON_ERROR_PATTERN,
            status_code=response.status_code,
            response_time_ms=elapsed,
            final_url=final_url,
            error=f"Page d'erreur détectée (motif « {matched} »)",
        )

    return CheckOutcome(
        ok=True,
        reason=REASON_OK,
        status_code=response.status_code,
        response_time_ms=elapsed,
        final_url=final_url,
    )
