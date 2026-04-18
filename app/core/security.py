from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import randbelow, token_urlsafe
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES = 24 * 60
EMAIL_VERIFICATION_URL_PATH = "/api/v1/auth/verify-email"


def hash_password(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must be 72 bytes or fewer.")
    return password_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, claims: dict[str, Any] | None = None) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {"sub": subject, "exp": expire, "type": "access"}
    if claims:
        payload.update(claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token() -> tuple[str, str, datetime]:
    token = token_urlsafe(48)
    expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    return token, hash_token(token), expires_at


def create_email_verification_token() -> tuple[str, str, datetime]:
    token = token_urlsafe(48)
    expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(
        minutes=EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES
    )
    return token, hash_token(token), expires_at


def create_email_verification_code() -> tuple[str, str, datetime]:
    code = f"{randbelow(1_000_000):06d}"
    expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(
        minutes=EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES
    )
    return code, hash_token(code), expires_at


def hash_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()
