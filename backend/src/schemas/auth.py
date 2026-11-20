"""Схемы авторизации."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    login: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=200)


class MeResponse(BaseModel):
    login: str


class LogoutResponse(BaseModel):
    success: bool = True
