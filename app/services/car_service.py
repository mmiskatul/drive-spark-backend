import re

from fastapi import HTTPException, status

from app.repositories.car_repository import CarRepository
from app.schemas.car import CarCreate, CarRead, CarUpdate
from app.schemas.common import PaginatedResponse


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return value or "car"


class CarService:
    def __init__(self, repository: CarRepository) -> None:
        self.repository = repository

    async def list_cars(
        self,
        *,
        page: int,
        limit: int,
        search: str | None,
    ) -> PaginatedResponse[CarRead]:
        filter_query: dict[str, object] = {}
        if search:
            filter_query["$text"] = {"$search": search}

        total = await self.repository.count(filter_query)
        documents = await self.repository.list(
            filter_query,
            skip=(page - 1) * limit,
            limit=limit,
        )
        return PaginatedResponse[CarRead](
            items=[self._to_read_model(document) for document in documents],
            total=total,
            page=page,
            limit=limit,
        )

    async def get_car(self, car_id: str) -> CarRead:
        document = await self.repository.get_by_id(car_id)
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Car not found")
        return self._to_read_model(document)

    async def create_car(self, payload: CarCreate) -> CarRead:
        data = payload.model_dump()
        base_slug = slugify(f"{payload.brand}-{payload.model}-{payload.year}")
        slug = base_slug
        suffix = 1
        while await self.repository.get_by_slug(slug):
            suffix += 1
            slug = f"{base_slug}-{suffix}"
        data["slug"] = slug
        document = await self.repository.create(data)
        return self._to_read_model(document)

    async def update_car(self, car_id: str, payload: CarUpdate) -> CarRead:
        data = payload.model_dump(exclude_unset=True)
        if "brand" in data or "model" in data or "year" in data:
            current = await self.repository.get_by_id(car_id)
            if current is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Car not found")
            brand = data.get("brand", current["brand"])
            model = data.get("model", current["model"])
            year = data.get("year", current["year"])
            data["slug"] = slugify(f"{brand}-{model}-{year}")

        document = await self.repository.update(car_id, data)
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Car not found")
        return self._to_read_model(document)

    async def delete_car(self, car_id: str) -> None:
        deleted = await self.repository.delete(car_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Car not found")

    @staticmethod
    def _to_read_model(document: dict) -> CarRead:
        document = {**document, "id": str(document["_id"])}
        return CarRead.model_validate(document)
