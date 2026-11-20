"""Stateless authentication service: credentials check + JWT issue/verify.

Пароль и логин сравниваются через secrets.compare_digest() — защита от timing-атак.
Состояние не хранится: подписанный JWT самодостаточен, БД не требуется.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

import jwt

from src.core.config import Settings

ALGORITHM = "HS256"


class AuthError(Exception):
    """Raised when credentials are invalid or a token cannot be verified."""

    def __init__(self, message: str = "Неверный логин или пароль") -> None:
        self.message = message
        super().__init__(message)


class AuthService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def verify_credentials(self, login: str, password: str) -> str:
        """Check login/password against Settings; return a signed JWT on success."""
        login_ok = secrets.compare_digest(login.encode(), self._settings.USER_LOGIN.encode())
        password_ok = secrets.compare_digest(password.encode(), self._settings.USER_PASSWORD.encode())
        if not (login_ok and password_ok):
            raise AuthError
        return self._create_token(login)

    def decode_token(self, token: str) -> str:
        """Verify JWT signature/expiry; return the subject (login)."""
        try:
            payload = jwt.decode(token, self._settings.AUTH_SECRET_KEY, algorithms=[ALGORITHM])
        except jwt.PyJWTError as e:
            raise AuthError("Сессия недействительна или истекла") from e
        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject:
            raise AuthError("Сессия недействительна или истекла")
        return subject

    def _create_token(self, login: str) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": login,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=self._settings.AUTH_TOKEN_TTL_MINUTES)).timestamp()),
        }
        return jwt.encode(payload, self._settings.AUTH_SECRET_KEY, algorithm=ALGORITHM)
