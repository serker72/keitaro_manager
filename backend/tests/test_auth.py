"""Unit tests for the stateless AuthService (JWT)."""

import time

import jwt
import pytest

from src.core.config import Settings
from src.services.auth import ALGORITHM, AuthError, AuthService


@pytest.fixture
def settings() -> Settings:
    return Settings(
        USER_LOGIN="admin",
        USER_PASSWORD="s3cret",
        AUTH_SECRET_KEY="x" * 32,
        AUTH_TOKEN_TTL_MINUTES=5,
    )


@pytest.fixture
def service(settings: Settings) -> AuthService:
    return AuthService(settings)


class TestVerifyCredentials:
    def test_valid_credentials_return_token(self, service: AuthService) -> None:
        token = service.verify_credentials("admin", "s3cret")
        assert isinstance(token, str) and token.count(".") == 2

    def test_wrong_password(self, service: AuthService) -> None:
        with pytest.raises(AuthError):
            service.verify_credentials("admin", "wrong")

    def test_wrong_login(self, service: AuthService) -> None:
        with pytest.raises(AuthError):
            service.verify_credentials("root", "s3cret")

    def test_empty_credentials(self, service: AuthService) -> None:
        with pytest.raises(AuthError):
            service.verify_credentials("", "")


class TestDecodeToken:
    def test_roundtrip(self, service: AuthService) -> None:
        token = service.verify_credentials("admin", "s3cret")
        assert service.decode_token(token) == "admin"

    def test_garbage_token(self, service: AuthService) -> None:
        with pytest.raises(AuthError):
            service.decode_token("not-a-token")

    def test_token_signed_with_other_key(self, service: AuthService) -> None:
        token = jwt.encode({"sub": "admin", "exp": int(time.time()) + 60}, "y" * 32, algorithm=ALGORITHM)
        with pytest.raises(AuthError):
            service.decode_token(token)

    def test_expired_token(self, settings: Settings, service: AuthService) -> None:
        expired = jwt.encode(
            {"sub": "admin", "exp": int(time.time()) - 10},
            settings.AUTH_SECRET_KEY,
            algorithm=ALGORITHM,
        )
        with pytest.raises(AuthError):
            service.decode_token(expired)

    def test_token_without_subject(self, settings: Settings, service: AuthService) -> None:
        token = jwt.encode({"exp": int(time.time()) + 60}, settings.AUTH_SECRET_KEY, algorithm=ALGORITHM)
        with pytest.raises(AuthError):
            service.decode_token(token)
