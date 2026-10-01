from fastapi import Header, HTTPException

from app.config import get_settings


def require_api_key(x_api_key: str = Header(default="")) -> None:
    """Every non-health endpoint requires this header. A single shared key
    is deliberately simple — this is a single-tenant internal tool (no
    per-user accounts), not a multi-tenant product; see the project plan's
    scope notes."""
    settings = get_settings()
    if x_api_key != settings.aegis_api_key:
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key header")
