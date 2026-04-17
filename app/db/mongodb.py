from typing import cast

from fastapi import FastAPI, Request
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, TEXT

from app.core.config import settings


async def connect_to_mongo(app: FastAPI) -> None:
    client: AsyncIOMotorClient = AsyncIOMotorClient(settings.MONGODB_URI)
    app.state.mongo_client = client
    app.state.mongo_db = client[settings.MONGODB_DB_NAME]
    await app.state.mongo_db.command("ping")


async def create_indexes(app: FastAPI) -> None:
    db = cast(AsyncIOMotorDatabase, app.state.mongo_db)
    await db.cars.create_index([("slug", ASCENDING)], unique=True)
    await db.cars.create_index([("title", TEXT), ("brand", TEXT), ("location", TEXT)])
    await db.cars.create_index([("status", ASCENDING), ("price_per_day", ASCENDING)])
    await db.users.create_index([("email", ASCENDING)], unique=True)


async def close_mongo_connection(app: FastAPI) -> None:
    client = cast(AsyncIOMotorClient, app.state.mongo_client)
    client.close()


def get_database(request: Request) -> AsyncIOMotorDatabase:
    return cast(AsyncIOMotorDatabase, request.app.state.mongo_db)
