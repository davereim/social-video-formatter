from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from social_video_formatter.core.config import settings

bearer = HTTPBearer(auto_error=False)


def require_api_key(credentials: HTTPAuthorizationCredentials | None = Security(bearer)) -> None:
    if not credentials or credentials.credentials != settings.app_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
