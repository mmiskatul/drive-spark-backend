from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request, Response, status
from pymongo.errors import DuplicateKeyError

from app.api.dependencies import DatabaseDep
from app.core.config import settings
from app.core.email import send_verification_email
from app.core.security import (
    create_access_token,
    create_email_verification_code,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    RegisterResponse,
    RegisterRequest,
    ResendVerificationRequest,
    UserRead,
    VerifyEmailRequest,
)

router = APIRouter()
ACCESS_TOKEN_COOKIE_NAME = "drive_spark_access"
REFRESH_TOKEN_COOKIE_NAME = "drive_spark_refresh"


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def serialize_user(user: dict[str, Any]) -> UserRead:
    return UserRead(
        id=str(user["_id"]),
        name=user["name"],
        email=user["email"],
        role=user["role"],
        email_verified_at=user.get("email_verified_at"),
    )


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        access_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        REFRESH_TOKEN_COOKIE_NAME,
        refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )


async def issue_tokens(db: DatabaseDep, response: Response, user: dict[str, Any]) -> str:
    user_id = str(user["_id"])
    access_token = create_access_token(user_id, {"role": user["role"]})
    refresh_token, refresh_token_hash, refresh_expires_at = create_refresh_token()
    await db.refresh_tokens.insert_one(
        {
            "token_hash": refresh_token_hash,
            "user_id": user["_id"],
            "expires_at": refresh_expires_at,
            "revoked_at": None,
            "created_at": utc_now(),
        }
    )
    set_auth_cookies(response, access_token, refresh_token)
    return access_token


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: DatabaseDep) -> RegisterResponse:
    now = utc_now()
    email = payload.email.lower()

    if await db.users.find_one({"email": email}):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    try:
        password_hash = hash_password(payload.password)
        code, code_hash, expires_at = create_email_verification_code()
        await db.pending_registrations.update_one(
            {"email": email},
            {
                "$set": {
                    "name": payload.name.strip(),
                    "email": email,
                    "password_hash": password_hash,
                    "role": payload.role,
                    "code_hash": code_hash,
                    "expires_at": expires_at,
                    "created_at": now,
                    "updated_at": now,
                }
            },
            upsert=True,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from exc

    send_verification_email(email, payload.name, code)

    return RegisterResponse(
        message="Verification code sent. Complete verification to create your account.",
        email=email,
        role=payload.role,
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, response: Response, db: DatabaseDep) -> AuthResponse:
    user = await db.users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.get("email_verified_at"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before signing in.",
        )

    access_token = await issue_tokens(db, response, user)
    return AuthResponse(user=serialize_user(user), access_token=access_token)


@router.get("/verify-email", response_model=AuthResponse)
async def verify_email_get(token: str, response: Response, db: DatabaseDep) -> AuthResponse:
    return await verify_email_token(token, response, db)


@router.post("/verify-email", response_model=AuthResponse)
async def verify_email_post(
    payload: VerifyEmailRequest,
    response: Response,
    db: DatabaseDep,
) -> AuthResponse:
    if payload.email and payload.code:
        return await verify_email_code(payload.email, payload.code, response, db)

    if payload.token:
        return await verify_email_token(payload.token, response, db)

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Email and verification code are required.",
    )


async def verify_email_token(token: str, response: Response, db: DatabaseDep) -> AuthResponse:
    token_document = await db.email_verification_tokens.find_one({"token_hash": hash_token(token)})
    now = utc_now()

    if (
        not token_document
        or token_document.get("used_at")
        or token_document["expires_at"] < now
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification link is invalid or expired.",
        )

    user = await db.users.find_one({"_id": token_document["user_id"]})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification link is invalid or expired.",
        )

    await db.email_verification_tokens.update_one(
        {"_id": token_document["_id"]},
        {"$set": {"used_at": now}},
    )
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"email_verified_at": user.get("email_verified_at") or now, "updated_at": now}},
    )
    user = await db.users.find_one({"_id": user["_id"]})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    access_token = await issue_tokens(db, response, user)
    return AuthResponse(user=serialize_user(user), access_token=access_token)


async def verify_email_code(
    email: str,
    code: str,
    response: Response,
    db: DatabaseDep,
) -> AuthResponse:
    pending_registration = await db.pending_registrations.find_one({"email": email.lower()})
    if not pending_registration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code is invalid or expired.",
        )

    now = utc_now()

    if (
        pending_registration["code_hash"] != hash_token(code)
        or pending_registration["expires_at"] < now
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code is invalid or expired.",
        )

    try:
        result = await db.users.insert_one(
            {
                "name": pending_registration["name"],
                "email": pending_registration["email"],
                "password_hash": pending_registration["password_hash"],
                "role": pending_registration["role"],
                "email_verified_at": now,
                "created_at": now,
                "updated_at": now,
            }
        )
    except DuplicateKeyError as exc:
        await db.pending_registrations.delete_one({"_id": pending_registration["_id"]})
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from exc

    await db.pending_registrations.delete_one({"_id": pending_registration["_id"]})
    user = await db.users.find_one({"_id": result.inserted_id})
    if not user:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User was not created.")

    access_token = await issue_tokens(db, response, user)
    return AuthResponse(user=serialize_user(user), access_token=access_token)


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    payload: ResendVerificationRequest,
    db: DatabaseDep,
) -> MessageResponse:
    if await db.users.find_one({"email": payload.email.lower()}):
        return MessageResponse(
            message="If this account needs verification, a new email will be sent."
        )

    pending_registration = await db.pending_registrations.find_one({"email": payload.email.lower()})
    if not pending_registration:
        return MessageResponse(
            message="If this account needs verification, a new email will be sent."
        )

    code, code_hash, expires_at = create_email_verification_code()
    await db.pending_registrations.update_one(
        {"_id": pending_registration["_id"]},
        {
            "$set": {
                "code_hash": code_hash,
                "expires_at": expires_at,
                "updated_at": utc_now(),
            }
        }
    )
    send_verification_email(pending_registration["email"], pending_registration["name"], code)
    return MessageResponse(message="Verification email sent.")


@router.post("/refresh", response_model=AuthResponse)
async def refresh(request: Request, response: Response, db: DatabaseDep) -> AuthResponse:
    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token.")

    token_document = await db.refresh_tokens.find_one({"token_hash": hash_token(refresh_token)})
    if (
        not token_document
        or token_document.get("revoked_at")
        or token_document["expires_at"] < utc_now()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid or expired.",
        )

    user = await db.users.find_one({"_id": token_document["user_id"]})
    if not user or not user.get("email_verified_at"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid or expired.",
        )

    access_token = create_access_token(str(user["_id"]), {"role": user["role"]})
    response.set_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        access_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    return AuthResponse(user=serialize_user(user), access_token=access_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(request: Request, response: Response, db: DatabaseDep) -> MessageResponse:
    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if refresh_token:
        await db.refresh_tokens.update_many(
            {"token_hash": hash_token(refresh_token), "revoked_at": None},
            {"$set": {"revoked_at": utc_now()}},
        )

    response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME, path="/")
    response.delete_cookie(REFRESH_TOKEN_COOKIE_NAME, path="/")
    return MessageResponse(message="Signed out.")
