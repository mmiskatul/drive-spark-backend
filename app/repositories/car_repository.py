from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


class CarRepository:
    collection_name = "cars"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection = db[self.collection_name]

    async def count(self, filter_query: dict[str, Any]) -> int:
        return await self.collection.count_documents(filter_query)

    async def list(
        self,
        filter_query: dict[str, Any],
        *,
        skip: int,
        limit: int,
    ) -> list[dict[str, Any]]:
        cursor = (
            self.collection.find(filter_query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def get_by_id(self, car_id: str) -> dict[str, Any] | None:
        if not ObjectId.is_valid(car_id):
            return None
        return await self.collection.find_one({"_id": ObjectId(car_id)})

    async def get_by_slug(self, slug: str) -> dict[str, Any] | None:
        return await self.collection.find_one({"slug": slug})

    async def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(UTC)
        document = {**payload, "created_at": now, "updated_at": now}
        result = await self.collection.insert_one(document)
        created = await self.collection.find_one({"_id": result.inserted_id})
        if created is None:
            raise RuntimeError("Car was inserted but could not be loaded")
        return created

    async def update(self, car_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        if not ObjectId.is_valid(car_id):
            return None
        payload["updated_at"] = datetime.now(UTC)
        await self.collection.update_one({"_id": ObjectId(car_id)}, {"$set": payload})
        return await self.get_by_id(car_id)

    async def delete(self, car_id: str) -> bool:
        if not ObjectId.is_valid(car_id):
            return False
        result = await self.collection.delete_one({"_id": ObjectId(car_id)})
        return result.deleted_count == 1
