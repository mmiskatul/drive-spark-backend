from typing import Annotated

from bson import ObjectId
from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.db.mongodb import get_database
from app.repositories.car_repository import CarRepository
from app.schemas.auth import UserRead
from app.services.car_service import CarService

DatabaseDep = Annotated[AsyncIOMotorDatabase, Depends(get_database)]
ACCESS_TOKEN_COOKIE_NAME = "drive_spark_access"


def get_car_repository(db: DatabaseDep) -> CarRepository:
    return CarRepository(db)


def get_car_service(
    repository: Annotated[CarRepository, Depends(get_car_repository)],
) -> CarService:
    return CarService(repository)


async def get_current_user(request: Request, db: DatabaseDep) -> UserRead:
    token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        token_type = payload.get("type")
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is invalid or expired.",
        ) from exc

    if token_type != "access" or not isinstance(user_id, str) or not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is invalid or expired.",
        )

    user = await db.users.find_one({"_id": ObjectId(user_id)})

    if not user or not user.get("email_verified_at"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")

    return UserRead(
        id=str(user["_id"]),
        name=user["name"],
        email=user["email"],
        role=user["role"],
        email_verified_at=user.get("email_verified_at"),
    )


CurrentUserDep = Annotated[UserRead, Depends(get_current_user)]


def require_partner_or_admin(user: CurrentUserDep) -> UserRead:
    if user.role not in {"partner", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only partners and admins can manage cars.",
        )

    return user


PartnerOrAdminDep = Annotated[UserRead, Depends(require_partner_or_admin)]
