import asyncio
from datetime import UTC, datetime

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings
from app.core.security import hash_password


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def seed_admin(db: AsyncIOMotorDatabase | None = None) -> None:
    client = None

    if db is None:
        client = AsyncIOMotorClient(settings.MONGODB_URI)
        db = client[settings.MONGODB_DB_NAME]

    try:
        email = settings.ADMIN_EMAIL.strip().lower()
        now = utc_now()
        existing_admin = await db.users.find_one({"email": email})

        if existing_admin:
            await db.users.update_one(
                {"_id": existing_admin["_id"]},
                {
                    "$set": {
                        "name": settings.ADMIN_NAME,
                        "role": "admin",
                        "email_verified_at": existing_admin.get("email_verified_at") or now,
                        "updated_at": now,
                    }
                },
            )
            print(f"Admin user already exists: {email}")
            return

        await db.users.insert_one(
            {
                "name": settings.ADMIN_NAME,
                "email": email,
                "password_hash": hash_password(settings.ADMIN_PASSWORD),
                "role": "admin",
                "email_verified_at": now,
                "created_at": now,
                "updated_at": now,
            }
        )
        print(f"Admin user created: {email}")
    finally:
        if client:
            client.close()


if __name__ == "__main__":
    asyncio.run(seed_admin())
