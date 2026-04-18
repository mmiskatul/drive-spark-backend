from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

Role = Literal["customer", "partner", "admin"]


class UserRead(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: Role
    email_verified_at: datetime | None = None


class UserProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: Literal["customer", "partner"] = "customer"

    @field_validator("password")
    @classmethod
    def password_must_fit_bcrypt(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be 72 bytes or fewer.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyEmailRequest(BaseModel):
    token: str | None = Field(default=None, min_length=6)
    email: EmailStr | None = None
    code: str | None = Field(default=None, min_length=6, max_length=6)


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class AuthResponse(BaseModel):
    user: UserRead
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str


class RegisterResponse(MessageResponse):
    email: EmailStr
    role: Literal["customer", "partner"]
