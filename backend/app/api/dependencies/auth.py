import os
import logging
from fastapi import Header, HTTPException, status

logger = logging.getLogger(__name__)

_API_KEY = os.getenv("API_KEY")

if not _API_KEY:
    logger.warning(
        "API_KEY environment variable is not set. "
        "Authentication is DISABLED — do not use this in production."
    )


async def verify_api_key(x_api_key: str = Header(default=None)) -> None:
    """FastAPI dependency that validates the X-API-Key header.

    When API_KEY env var is unset (dev mode), all requests are allowed.
    """
    if not _API_KEY:
        return
    if x_api_key != _API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
