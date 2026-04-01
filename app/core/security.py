import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def verify_password(plain_password: str, stored_password: str) -> bool:
    if stored_password.startswith("sha256$"):
        expected_hash = stored_password.split("$", 1)[1]
        return hmac.compare_digest(expected_hash, _sha256(plain_password))

    return hmac.compare_digest(stored_password, plain_password)


def create_access_token(username: str, role: str) -> str:
    expires_delta = timedelta(minutes=settings.JWT_EXPIRES_MINUTES)
    expires_at = datetime.now(timezone.utc) + expires_delta

    payload = {
        "sub": username,
        "role": role,
        "exp": expires_at,
    }

    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    username = payload.get("sub")
    role = payload.get("role")
    if not username or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    return payload


def get_current_token_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )

    return decode_access_token(credentials.credentials)


def require_admin(payload: dict[str, Any] = Depends(get_current_token_payload)) -> dict[str, Any]:
    if payload.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return payload


def require_client(payload: dict[str, Any] = Depends(get_current_token_payload)) -> dict[str, Any]:
    if payload.get("role") != "client":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Client access required")
    return payload
