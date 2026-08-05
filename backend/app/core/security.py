import hmac

from fastapi import Header, HTTPException, status

from app.core.config import get_settings


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Guard every write and read route.

    When ``API_KEY`` is unset the guard is a no-op so a local `docker compose up`
    works out of the box; set it in any deployed environment.
    """
    expected = get_settings().api_key
    if not expected:
        return
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Clé d'API invalide"
        )
