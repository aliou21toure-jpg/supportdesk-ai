import hmac
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from app.config import Settings, get_settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_agent(
    key: Annotated[str | None, Depends(_api_key_header)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Agent-only endpoints. compare_digest avoids leaking the key through timing."""
    if not key or not hmac.compare_digest(key.encode(), settings.agent_api_key.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing API key")
