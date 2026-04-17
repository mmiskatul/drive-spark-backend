from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_car_service
from app.schemas.car import CarCreate, CarRead, CarUpdate
from app.schemas.common import PaginatedResponse
from app.services.car_service import CarService

router = APIRouter()
CarServiceDep = Annotated[CarService, Depends(get_car_service)]


@router.get("", response_model=PaginatedResponse[CarRead])
async def list_cars(
    service: CarServiceDep,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=12, ge=1, le=100),
    search: str | None = Query(default=None, min_length=2),
) -> PaginatedResponse[CarRead]:
    return await service.list_cars(page=page, limit=limit, search=search)


@router.post("", response_model=CarRead, status_code=status.HTTP_201_CREATED)
async def create_car(payload: CarCreate, service: CarServiceDep) -> CarRead:
    return await service.create_car(payload)


@router.get("/{car_id}", response_model=CarRead)
async def get_car(car_id: str, service: CarServiceDep) -> CarRead:
    return await service.get_car(car_id)


@router.patch("/{car_id}", response_model=CarRead)
async def update_car(car_id: str, payload: CarUpdate, service: CarServiceDep) -> CarRead:
    return await service.update_car(car_id, payload)


@router.delete("/{car_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_car(car_id: str, service: CarServiceDep) -> None:
    await service.delete_car(car_id)
