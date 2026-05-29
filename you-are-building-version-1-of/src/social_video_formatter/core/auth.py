from fastapi import Header, HTTPException


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    from social_video_formatter.core.config import settings
    if not x_api_key or x_api_key != settings.app_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
